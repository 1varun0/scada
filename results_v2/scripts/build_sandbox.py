#!/usr/bin/env python3
"""
Builds an isolated sandbox copy of the project repository at %TEMP%/p1_sandbox
using tracked files from git ls-files, plus data/scada_ids.db and checkpoints/.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SANDBOX_DIR = Path(tempfile.gettempdir()) / "p1_sandbox"

print(f"=== Building Sandbox Copy ===")
print(f"Source Repository : {REPO_ROOT}")
print(f"Destination Sandbox: {SANDBOX_DIR}")

# 1. Clean existing sandbox if exists
if SANDBOX_DIR.exists():
    print(f"Removing pre-existing sandbox directory: {SANDBOX_DIR}")
    shutil.rmtree(SANDBOX_DIR)

SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

# 2. Get tracked files
raw_files = subprocess.check_output(["git", "ls-files"], cwd=REPO_ROOT, text=True).splitlines()
tracked_files = [f for f in raw_files if not f.startswith("results_v2/")]

# Ensure db and checkpoints are copied
if "data/scada_ids.db" not in tracked_files and (REPO_ROOT / "data" / "scada_ids.db").exists():
    tracked_files.append("data/scada_ids.db")

for cp in (REPO_ROOT / "checkpoints").glob("*"):
    rel_cp = str(cp.relative_to(REPO_ROOT)).replace("\\", "/")
    if rel_cp not in tracked_files and cp.is_file():
        tracked_files.append(rel_cp)

tracked_files = sorted(list(set(tracked_files)))
print(f"Copying {len(tracked_files)} files into sandbox...")

copied_count = 0
for rel_path in tracked_files:
    src_file = REPO_ROOT / rel_path
    dst_file = SANDBOX_DIR / rel_path
    if not src_file.exists():
        print(f"WARNING: Source file does not exist: {src_file}")
        continue
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_file, dst_file)
    copied_count += 1

print(f"Successfully copied {copied_count} files to: {SANDBOX_DIR}")

# 3. Save sandbox info
info = {
    "sandbox_dir": str(SANDBOX_DIR),
    "source_dir": str(REPO_ROOT),
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "files_copied": copied_count
}

info_path = REPO_ROOT / "results_v2" / "_env" / "sandbox_info.json"
with open(info_path, "w", encoding="utf-8") as f:
    json.dump(info, f, indent=2)

print(f"Recorded sandbox metadata to: {info_path}")
