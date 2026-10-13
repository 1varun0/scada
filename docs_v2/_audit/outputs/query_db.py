"""
Read-only query script for data/scada_ids.db
Follows Rule 3: sqlite3.connect("file:data/scada_ids.db?mode=ro", uri=True)
"""
import sqlite3

DB_URI = "file:data/scada_ids.db?mode=ro"

def run_queries():
    conn = sqlite3.connect(DB_URI, uri=True)
    cur = conn.cursor()
    out = []

    out.append("=== TABLES AND INDEXES IN DATABASE ===")
    cur.execute("SELECT name, type, sql FROM sqlite_master ORDER BY type, name;")
    items = cur.fetchall()
    for name, item_type, sql in items:
        out.append(f"\n[{item_type.upper()}] {name}\nSQL: {sql}")

    tables = [row[0] for row in items if row[1] == 'table']

    out.append("\n\n=== PRAGMA TABLE_INFO FOR ALL TABLES ===")
    for t_name in tables:
        out.append(f"\n--- PRAGMA table_info({t_name}) ---")
        cur.execute(f"PRAGMA table_info({t_name});")
        cols = cur.fetchall()
        for c in cols:
            out.append(f"  cid={c[0]} name={c[1]} type={c[2]} notnull={c[3]} dflt={c[4]} pk={c[5]}")

    out.append("\n\n=== SCENARIOS IN ATTACK_SCENARIOS ===")
    cur.execute("SELECT COUNT(*) FROM attack_scenarios;")
    out.append(f"Total rows in attack_scenarios: {cur.fetchone()[0]}")
    cur.execute("SELECT attack_type, COUNT(*) FROM attack_scenarios GROUP BY attack_type ORDER BY attack_type;")
    for row in cur.fetchall():
        out.append(f"  attack_type={row[0]}: {row[1]} scenarios")

    out.append("\nSample 5 rows from attack_scenarios:")
    cur.execute("SELECT * FROM attack_scenarios LIMIT 5;")
    for row in cur.fetchall():
        out.append(f"  {row}")

    out.append("\n=== SCENARIO COUNTS IN SCADA_TELEMETRY ===")
    cur.execute("""
        SELECT 
            CASE 
                WHEN scenario_id LIKE 'N_%' THEN 'Normal (N)'
                WHEN scenario_id LIKE 'A1_%' THEN 'A1 (FDI)'
                WHEN scenario_id LIKE 'A2_%' THEN 'A2 (Replay)'
                WHEN scenario_id LIKE 'A3_%' THEN 'A3 (DoS)'
                WHEN scenario_id LIKE 'A4_%' THEN 'A4 (Auth Misuse)'
                ELSE 'Other'
            END as scen_group,
            COUNT(DISTINCT scenario_id) as num_scenarios,
            COUNT(*) as total_rows
        FROM scada_telemetry
        GROUP BY scen_group
        ORDER BY scen_group;
    """)
    for row in cur.fetchall():
        out.append(f"  {row[0]}: {row[1]} scenarios, {row[2]} total rows")

    cur.execute("SELECT COUNT(DISTINCT scenario_id), COUNT(*) FROM scada_telemetry;")
    tot_scens, tot_rows = cur.fetchone()
    out.append(f"Total distinct scenarios in scada_telemetry: {tot_scens}, total rows: {tot_rows}")

    out.append("\n=== TICKS (SEQUENCE_ID) PER SCENARIO ===")
    cur.execute("""
        SELECT scenario_id, COUNT(*) as cnt, MIN(sequence_id), MAX(sequence_id)
        FROM scada_telemetry
        GROUP BY scenario_id
        HAVING cnt != 1001;
    """)
    abnormal_ticks = cur.fetchall()
    if abnormal_ticks:
        out.append(f"Scenarios with sequence_id count != 1001: {len(abnormal_ticks)}")
        for row in abnormal_ticks:
            out.append(f"  {row}")
    else:
        out.append("All 150 scenarios have exactly 1001 records (sequence_id 0 to 1000, 0.0s to 1000.0s).")

    out.append("\n=== INITIAL LEVELS (AT SEQUENCE_ID=0) PER SCENARIO GROUP ===")
    cur.execute("""
        SELECT 
            CASE 
                WHEN scenario_id LIKE 'N_%' THEN 'N'
                WHEN scenario_id LIKE 'A1_%' THEN 'A1'
                WHEN scenario_id LIKE 'A2_%' THEN 'A2'
                WHEN scenario_id LIKE 'A3_%' THEN 'A3'
                WHEN scenario_id LIKE 'A4_%' THEN 'A4'
                ELSE 'Other'
            END as grp,
            COUNT(*),
            MIN(tank_level_observed), MAX(tank_level_observed), AVG(tank_level_observed)
        FROM scada_telemetry
        WHERE sequence_id = 0
        GROUP BY grp
        ORDER BY grp;
    """)
    for row in cur.fetchall():
        out.append(f"  Group {row[0]}: count={row[1]}, min_level={row[2]:.4f}, max_level={row[3]:.4f}, avg_level={row[4]:.4f}")

    out.append("\n=== OPERATING CONDITIONS / SETPOINTS AT SEQUENCE_ID=0 ===")
    cur.execute("""
        SELECT 
            CASE 
                WHEN scenario_id LIKE 'N_%' THEN 'N'
                WHEN scenario_id LIKE 'A1_%' THEN 'A1'
                WHEN scenario_id LIKE 'A2_%' THEN 'A2'
                WHEN scenario_id LIKE 'A3_%' THEN 'A3'
                WHEN scenario_id LIKE 'A4_%' THEN 'A4'
                ELSE 'Other'
            END as grp,
            operating_condition,
            COUNT(*),
            MIN(tank_level_setpoint), MAX(tank_level_setpoint),
            MIN(q_in), MAX(q_in),
            MIN(q_out), MAX(q_out)
        FROM scada_telemetry
        WHERE sequence_id = 0
        GROUP BY grp, operating_condition
        ORDER BY grp, operating_condition;
    """)
    for row in cur.fetchall():
        out.append(f"  Group {row[0]} [op={row[1]}]: count={row[2]}, sp=[{row[3]:.2f}, {row[4]:.2f}], q_in=[{row[5]:.4f}, {row[6]:.4f}], q_out=[{row[7]:.4f}, {row[8]:.4f}]")

    out.append("\n=== ATTACK WINDOWS FROM SCADA_TELEMETRY (WHERE ground_truth = 1) ===")
    cur.execute("""
        SELECT 
            CASE 
                WHEN scenario_id LIKE 'A1_%' THEN 'A1'
                WHEN scenario_id LIKE 'A2_%' THEN 'A2'
                WHEN scenario_id LIKE 'A3_%' THEN 'A3'
                WHEN scenario_id LIKE 'A4_%' THEN 'A4'
                ELSE 'Other'
            END as grp,
            COUNT(DISTINCT scenario_id) as attack_scenarios_count,
            MIN(tick_start) as min_start, MAX(tick_start) as max_start, AVG(tick_start) as avg_start,
            MIN(tick_end) as min_end, MAX(tick_end) as max_end, AVG(tick_end) as avg_end,
            MIN(duration) as min_dur, MAX(duration) as max_dur, AVG(duration) as avg_dur
        FROM (
            SELECT scenario_id, MIN(sequence_id) as tick_start, MAX(sequence_id) as tick_end, COUNT(*) as duration
            FROM scada_telemetry
            WHERE ground_truth = 1
            GROUP BY scenario_id
        )
        GROUP BY grp
        ORDER BY grp;
    """)
    for row in cur.fetchall():
        out.append(f"  {row[0]}: count={row[1]}, start=[{row[2]}, {row[3]}, avg={row[4]:.1f}], end=[{row[5]}, {row[6]}, avg={row[7]:.1f}], duration=[{row[8]}, {row[9]}, avg={row[10]:.1f}]")

    out.append("\n=== ATTACK_SCENARIOS TABLE TIME AND LEVEL DETAILS ===")
    cur.execute("""
        SELECT attack_type, 
               COUNT(*),
               MIN(attack_start_time_s), MAX(attack_start_time_s), AVG(attack_start_time_s),
               MIN(attack_end_time_s), MAX(attack_end_time_s), AVG(attack_end_time_s),
               MIN(initial_tank_level), MAX(initial_tank_level), AVG(initial_tank_level)
        FROM attack_scenarios
        GROUP BY attack_type
        ORDER BY attack_type;
    """)
    for row in cur.fetchall():
        out.append(f"  {row[0]}: count={row[1]}, start=[{row[2]:.1f}, {row[3]:.1f}, avg={row[4]:.1f}], end=[{row[5]:.1f}, {row[6]:.1f}, avg={row[7]:.1f}], init_level=[{row[8]:.4f}, {row[9]:.4f}, avg={row[10]:.4f}]")

    out.append("\n=== EXPERIMENT_RUNS TABLE DETAILS ===")
    cur.execute("SELECT COUNT(*) FROM experiment_runs;")
    out.append(f"Rows in experiment_runs: {cur.fetchone()[0]}")
    cur.execute("SELECT experiment_id, model_version, feature_version, threshold_version, fusion_version, created_at FROM experiment_runs;")
    for row in cur.fetchall():
        out.append(f"  {row}")

    out.append("\n=== EVALUATION_RESULTS TABLE DETAILS ===")
    cur.execute("SELECT COUNT(*) FROM evaluation_results;")
    out.append(f"Rows in evaluation_results: {cur.fetchone()[0]}")
    cur.execute("SELECT DISTINCT scenario_id FROM evaluation_results ORDER BY scenario_id;")
    eval_scens = [r[0] for r in cur.fetchall()]
    out.append(f"Total distinct scenarios in evaluation_results: {len(eval_scens)}")
    
    # Break down eval_scens by prefix
    prefix_counts = {}
    for s in eval_scens:
        p = s.split('_')[0]
        prefix_counts[p] = prefix_counts.get(p, 0) + 1
    out.append(f"Scenario count breakdown in evaluation_results: {prefix_counts}")

    conn.close()
    return "\n".join(out)

if __name__ == "__main__":
    res = run_queries()
    with open("docs_v2/_audit/outputs/db_queries_output.txt", "w", encoding="utf-8") as f:
        f.write(res)
    print("Database queries successfully run and saved.")
