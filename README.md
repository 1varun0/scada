# SCADA Digital Twin: Hybrid Intrusion Detection System

## Overview
This project is a hybrid Intrusion Detection System (IDS) for a single-tank water SCADA system. Traditional machine-learning-only IDS systems suffer from high false-positive rates and struggle to detect sophisticated physics-based attacks. 

This project solves this by combining deterministic engineering principles with deep learning. It fuses four independent detection engines—including a deterministic **Physics Digital Twin** and a **Policy Engine**—with an **LSTM Autoencoder** to accurately detect four distinct classes of cyber-physical attacks (FDI, Replay, DoS, and Authorization Misuse).

## Key Features
- **4-Engine Hybrid Detection:** Combines Physics, Policy, Availability, and Temporal (LSTM) anomaly scoring.
- **Max-Vote Fusion Engine:** Achieves 100% precision and 100% recall on all 4 attack categories.
- **Custom SCADA Data Generator:** Simulates physical tank dynamics with realistic hysteresis control, sensor noise, and malicious interventions. Produces 150,000 records across 150 scenarios.
- **Premium Real-Time Dashboard:** A sleek, glassmorphic UI built in Vanilla HTML/CSS/JS and Flask for live telemetry visualization and alerting.

## Installation & Setup

1. **Clone the repository** (or navigate to the project directory).
2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set the Python path** (required for all scripts):
   ```bash
   # Windows (PowerShell)
   $env:PYTHONPATH="."
   # Linux/Mac
   export PYTHONPATH="."
   ```

## Usage Guide

### 1. Generating Data
Data is generated via MATLAB Simulink scripts and imported into the SQLite database:
```bash
python scripts/import_matlab_csv.py
```
This populates `data/scada_ids.db` with 150,000 records across 150 scenarios (60 normal + 90 attack).

### 2. Training the Temporal Model (LSTM-AE)
Train the LSTM Autoencoder using only the normal operating scenarios:
```bash
python scripts/train_lstm.py
```
This saves the model weights to `checkpoints/lstm_ae_v1.pt` and the fitted scaler to `checkpoints/scaler_v1.pkl`.

### 3. Running the Full Evaluation Pipeline
Run the evaluation script to test the 4 engines and the fusion model against the held-out test data. This outputs the per-attack-type metrics and saves the ROC curve to `reports/roc_curve.png`.
```bash
python scripts/run_evaluation.py
```

### 4. Starting the Real-Time Dashboard
To view the live telemetry and the anomaly score visualizations, start the Flask web server:
```bash
python dashboard/app.py
```
Then, open `http://127.0.0.1:5000/` in your web browser.

## Project Structure
```
├── config/          - Frozen system parameters and scenario definitions.
├── digital_twin/    - Physics Digital Twin (mass-balance model).
├── engines/         - 4 anomaly detection engines + Hybrid Fusion Engine.
├── models/          - PyTorch LSTM Autoencoder and data preprocessing.
├── scripts/         - Pipeline scripts (import, training, evaluation, ablation).
├── simulator/       - Physical process simulator (tank, pump, valve, controller).
├── evaluation/      - Metric calculation (F1, FPR, latency) and reporter.
├── storage/         - SQLite database client for data ingestion.
├── dashboard/       - Flask backend and static HTML/CSS/JS frontend.
├── tests/           - Unit tests for simulator components and engines.
├── matlab/          - MATLAB/Simulink source scripts and raw CSV data.
├── data/            - SQLite database and CSV evaluation outputs.
├── checkpoints/     - Trained model weights and scaler artifacts.
├── reports/         - Output graphs (ROC curves) and ablation studies.
└── projectdocs/     - Architecture docs, formulas, and review cheat sheets.
```
