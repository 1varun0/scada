#!/usr/bin/env python3
"""
Computes SHA-256 hashes of all existing tracked files (plus data/scada_ids.db and checkpoints/*)
outside results_v2/ to establish the baseline in results_v2/_audit/hashes_before.txt.
"""

import subprocess
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_FILE = REPO_ROOT / "results_v2" / "_audit" / "hashes_before.txt"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# 1. Get tracked files
raw_files = subprocess.check_output(["git", "ls-files"], cwd=REPO_ROOT, text=True).splitlines()

# Filter out anything in results_v2/
tracked_files = [f for f in raw_files if not f.startswith("results_v2/")]

# Ensure data/scada_ids.db and checkpoints/* are included if present
extra_candidates = ["data/scada_ids.db"] + [str(p.relative_to(REPO_ROOT)).replace("\\", "/") for p in (REPO_ROOT / "checkpoints").glob("*") if p.is_file()]
for ec in extra_candidates:
    if ec not in tracked_files and (REPO_ROOT / ec).exists():
        tracked_files.append(ec)

tracked_files = sorted(list(set(tracked_files)))
print(f"Hashing {len(tracked_files)} files outside results_v2/...")

lines = []
for rel_path in tracked_files:
    file_path = REPO_ROOT / rel_path
    if not file_path.exists():
        print(f"WARNING: File does not exist: {rel_path}")
        continue
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    file_hash = hasher.hexdigest()
    lines.append(f"{file_hash}  {rel_path}")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"Successfully recorded {len(lines)} file hashes to: {OUTPUT_FILE}")
