# R01: Environment & Provenance Specification

## 1. Provenance Baseline

To ensure absolute repeatability and eliminate hidden host-dependent artifacts, all experimental executions documented in this study were anchored to the git state of the host repository and executed within an isolated external sandbox copy:
- **Baseline Git Commit Hash**: [`27d13c2`](file:///c:/projects/p1/New%20folder/results_v2/_env/commit_hash.txt)
- **Baseline Git Tree Status**: 100% Clean (`git status --porcelain` returned 0 modified, added, or deleted files outside `results_v2/` at initiation).
- **Tracked Files Inventory**: Exactly 434 git-tracked files (353 core repository files + 81 audit/documentation files in `docs_v2/`).
- **Baseline SHA-256 Manifest**: 434 cryptographic hashes recorded in [`results_v2/_audit/hashes_before.txt`](file:///c:/projects/p1/New%20folder/results_v2/_audit/hashes_before.txt).

---

## 2. Host Hardware Platform

Specifications captured directly via Python hardware inspection utilities ([`results_v2/_env/host_info.txt`](file:///c:/projects/p1/New%20folder/results_v2/_env/host_info.txt)):

| Hardware Component | Reported System Attribute | Measurement Detail |
| :--- | :--- | :--- |
| **Operating System** | Microsoft Windows 11 Home (64-bit) | Version 10.0.26100 (Build 26100) |
| **Processor (CPU)** | Intel(R) Core(TM) i5-10300H CPU @ 2.50GHz | 4 Physical Cores, 8 Logical Processors (x86_64) |
| **System Memory (RAM)** | 16,220 MB Total Physical RAM | 15.84 GB Available, ~6.4 GB In Use during idle |
| **Graphics Accelerator (GPU)** | NVIDIA GeForce GTX 1650 (Notebook) | 4,096 MB Dedicated GDDR6 VRAM, Driver 576.06 |
| **CUDA Acceleration** | CUDA Version 12.1 Supported | `torch.cuda.is_available() == True`, Device: `cuda:0` |

---

## 3. Python Runtime & Core Library Stack

Recorded in [`results_v2/_env/python_version.txt`](file:///c:/projects/p1/New%20folder/results_v2/_env/python_version.txt) and [`results_v2/_env/key_packages.txt`](file:///c:/projects/p1/New%20folder/results_v2/_env/key_packages.txt):

| Package / Runtime Component | Installed Version | Role in Architecture |
| :--- | :---: | :--- |
| **Python Interpreter** | `3.12.6` (64-bit) | Core execution runtime |
| **PyTorch (`torch`)** | `2.5.1+cu121` | Deep learning LSTM autoencoder inference |
| **CUDA Runtime** | `cu121` (CUDA 12.1) | GPU acceleration of tensor matrix operations |
| **NumPy** | `2.3.3` | Numerical matrix manipulations & vector math |
| **Pandas** | `2.3.2` | Telemetry dataframe manipulation & evaluation reporting |
| **Scikit-Learn (`sklearn`)** | `1.7.2` | Metric evaluation, ROC/PR curves, MinMaxScaler |
| **Pytest** | `9.1.1` | Automated test suite execution & verification harness |
| **Flask** | `3.1.0` | Gateway REST API server & SSE streaming hub |
| **PyYAML (`yaml`)** | `6.0.2` | Configuration parameter parsing |

The complete environment package listing is archived in [`results_v2/_env/pip_freeze.txt`](file:///c:/projects/p1/New%20folder/results_v2/_env/pip_freeze.txt).

---

## 4. Scaler Checkpoint Validation

The pre-trained MinMaxScaler checkpoint located at `checkpoints/scaler_v1.pkl` was loaded and audited using Python `pickle` ([`results_v2/_env/scaler_check.txt`](file:///c:/projects/p1/New%20folder/results_v2/_env/scaler_check.txt)):
- **Status**: Successfully deserialized without corruption or deprecation errors under Python 3.12.
- **Scaler Type**: `sklearn.preprocessing._data.MinMaxScaler`
- **Feature Count**: 5 features (`tank_level_observed`, `q_in`, `q_out`, `pump_state`, `valve_state`).
- **Feature Ranges**:
  - `data_min_`: `[0.4897, 0.0, 0.0, 0.0, 0.0]`
  - `data_max_`: `[1.7125, 0.0055, 0.0041, 1.0, 100.0]`
- **Scaling Range**: Scaled onto $[0.0, 1.0]$ interval for input to the PyTorch LSTM Autoencoder.

---

## 5. Execution Sandbox Isolation Architecture

All processes were executed in an isolated filesystem sandbox:
- **Sandbox Root**: `C:\Users\varun\AppData\Local\Temp\p1_sandbox`
- **Replication Mechanism**: Created via [`results_v2/scripts/build_sandbox.py`](file:///c:/projects/p1/New%20folder/results_v2/scripts/build_sandbox.py), mirroring all 434 git-tracked files.
- **Runner Wrapper**: Every command was launched through [`results_v2/scripts/runner_util.py`](file:///c:/projects/p1/New%20folder/results_v2/scripts/runner_util.py), which explicitly sets `cwd` to the sandbox directory, injects `PYTHONPATH`, records execution start/duration, captures stdout/stderr verbatim to `results_v2/raw/<name>.log`, and emits a machine-readable sidecar JSON `results_v2/raw/<name>.json`.
- **Integrity Guarantee**: The primary working directory `C:\projects\p1\New folder` received **zero writes, file touches, or database edits** during any evaluation run.
