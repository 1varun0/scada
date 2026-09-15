import pandas as pd
import numpy as np
from evaluation.ablation import AblationRunner
from evaluation.reporter import Reporter

import os

def load_results(filepath="data/evaluation_results.csv"):
    """Load evaluation results saved by run_evaluation.py."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Results file not found at {filepath}. Run run_evaluation.py first.")
    return pd.read_csv(filepath)

def main():
    print("Starting Ablation Study (C1 - C7)...")
    
    # Load df_results from the CSV saved by run_evaluation.py
    df_results = load_results()
    
    # Run ablation
    runner = AblationRunner(df_results=df_results, tau_fusion=0.5)
    df_ablation = runner.run_all()
    
    # Report
    reporter = Reporter()
    filepath = reporter.generate_ablation_markdown(df_ablation)
    
    print(f"Ablation study complete. Results saved to {filepath}")
    print(df_ablation[['precision', 'recall', 'f1', 'latency_median']])

if __name__ == "__main__":
    main()
