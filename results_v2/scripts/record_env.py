#!/usr/bin/env python3
"""
Records the execution environment specifications for results_v2/_env/
"""

import sys
import os
import platform
import subprocess
import json
import warnings
import pickle
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_DIR = REPO_ROOT / "results_v2" / "_env"
ENV_DIR.mkdir(parents=True, exist_ok=True)

print(f"Recording environment specifications to: {ENV_DIR}")

# 1. Git Information
git_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
git_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT, text=True).strip()
git_status = subprocess.check_output(["git", "status", "--short"], cwd=REPO_ROOT, text=True)

with open(ENV_DIR / "git_info.txt", "w", encoding="utf-8") as f:
    f.write(f"Commit Hash : {git_hash}\n")
    f.write(f"Branch      : {git_branch}\n")
    f.write(f"Git Status --short:\n{git_status}\n")

# 2. Python Version & Interpreter
py_ver = sys.version
py_exec = sys.executable

# 3. Pip Freeze
pip_freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
with open(ENV_DIR / "pip_freeze.txt", "w", encoding="utf-8") as f:
    f.write(pip_freeze)

# 4. Hardware Specs
import psutil
ram_bytes = psutil.virtual_memory().total
ram_gb = round(ram_bytes / (1024**3), 2)
cpu_cores_logical = psutil.cpu_count(logical=True)
cpu_cores_physical = psutil.cpu_count(logical=False)
cpu_model = platform.processor()

# 5. Libraries & GPU Presence
import torch
import numpy as np
import pandas as pd
import sklearn

gpu_available = torch.cuda.is_available()
gpu_device_name = torch.cuda.get_device_name(0) if gpu_available else "None (CPU only)"

lib_versions = {
    "python": sys.version.split()[0],
    "platform": platform.platform(),
    "cpu_model": cpu_model,
    "cpu_cores_physical": cpu_cores_physical,
    "cpu_cores_logical": cpu_cores_logical,
    "ram_gb": ram_gb,
    "gpu_available": gpu_available,
    "gpu_device": gpu_device_name,
    "torch": torch.__version__,
    "numpy": np.__version__,
    "pandas": pd.__version__,
    "scikit-learn": sklearn.__version__
}

with open(ENV_DIR / "system_info.json", "w", encoding="utf-8") as f:
    json.dump(lib_versions, f, indent=2)

with open(ENV_DIR / "system_info.txt", "w", encoding="utf-8") as f:
    for k, v in lib_versions.items():
        f.write(f"{k}: {v}\n")

# 6. Scaler Pickle Version Warning Check
scaler_path = REPO_ROOT / "checkpoints" / "scaler_v1.pkl"
scaler_warning_text = ""
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    try:
        with open(scaler_path, "rb") as sf:
            scaler = pickle.load(sf)
        if len(w) > 0:
            scaler_warning_text = "\n".join([str(item.message) for item in w])
        else:
            scaler_warning_text = "No warnings encountered when loading checkpoints/scaler_v1.pkl"
    except Exception as e:
        scaler_warning_text = f"Error loading scaler: {e}"

with open(ENV_DIR / "scaler_pickle_warning.txt", "w", encoding="utf-8") as f:
    f.write(scaler_warning_text + "\n")

print("Environment recording complete:")
print(f"  OS: {platform.platform()}")
print(f"  Python: {sys.version.split()[0]}")
print(f"  RAM: {ram_gb} GB, Cores: {cpu_cores_physical} physical / {cpu_cores_logical} logical")
print(f"  Torch: {torch.__version__}, GPU: {gpu_device_name}")
print(f"  Scaler check: {scaler_warning_text.strip()}")
