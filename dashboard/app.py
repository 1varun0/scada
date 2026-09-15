import sqlite3
import pandas as pd
from flask import Flask, render_template, jsonify
import os

# Get absolute path to the directory containing this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Database is in the 'data' directory one level up
DB_PATH = os.path.join(BASE_DIR, "..", "data", "scada_ids.db")

app = Flask(__name__)

def get_db_connection():
    # Adding timeout to wait for lock since WAL mode might have concurrent readers
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scenarios')
def api_scenarios():
    try:
        conn = get_db_connection()
        query = "SELECT DISTINCT scenario_id FROM scada_telemetry ORDER BY scenario_id"
        scenarios = pd.read_sql_query(query, conn)['scenario_id'].tolist()
        conn.close()
        return jsonify(scenarios)
    except Exception as e:
        print(f"Error fetching scenarios: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/<scenario_id>')
def api_telemetry(scenario_id):
    try:
        conn = get_db_connection()
        
        # We need to query evaluation_results from CSV or check if it exists in DB.
        # Wait, run_evaluation.py writes to evaluation_results.csv, not the database directly!
        # Let's read from CSV and merge in pandas.
        
        # Read telemetry from DB
        query = """
            SELECT sequence_id, simulation_time_s, tank_level_observed, pump_state, valve_state,
                   q_in, q_out, attack_type, ground_truth
            FROM scada_telemetry
            WHERE scenario_id = ?
            ORDER BY sequence_id
        """
        df = pd.read_sql_query(query, conn, params=[scenario_id])
        conn.close()
        
        # Attempt to load evaluation results from CSV
        eval_csv_path = os.path.join(BASE_DIR, "..", "data", "evaluation_results.csv")
        if os.path.exists(eval_csv_path):
            df_eval = pd.read_csv(eval_csv_path)
            # Filter for this scenario
            df_eval = df_eval[df_eval['scenario_id'] == scenario_id]
            if not df_eval.empty:
                # Merge on sequence_id
                # Keep relevant columns
                cols_to_keep = ['sequence_id', 'S_p', 'S_l', 'S_c', 'S_a', 'S_hybrid', 'predicted_anomaly']
                # Missing columns might cause KeyError, so check
                cols_present = [c for c in cols_to_keep if c in df_eval.columns]
                df = df.merge(df_eval[cols_present], on='sequence_id', how='left')
        
        # Fill missing values with None for JSON
        df = df.where(pd.notnull(df), None)
        return jsonify(df.to_dict(orient='list'))
    except Exception as e:
        print(f"Error fetching telemetry: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
