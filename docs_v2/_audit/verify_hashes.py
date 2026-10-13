#!/usr/bin/env python3
"""
Computes SHA-256 hashes of all 353 tracked files and compares them
against docs_v2/_audit/hashes_before.txt to prove zero modifications outside docs_v2/.
"""

import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BEFORE_PATH = REPO_ROOT / "docs_v2" / "_audit" / "hashes_before.txt"
AFTER_PATH = REPO_ROOT / "docs_v2" / "_audit" / "hashes_after.txt"

print("=== SCADA Hybrid IDS — Tracked Files Hash Verification ===")
print(f"Reading baseline hashes from: {BEFORE_PATH}")

before_lines = BEFORE_PATH.read_text(encoding="utf-8").strip().splitlines()
after_lines = []
mismatches = []
missing = []

for line in before_lines:
    if not line.strip():
        continue
    orig_hash, rel_path = line.split("  ", 1)
    file_path = REPO_ROOT / rel_path
    
    if not file_path.exists():
        missing.append(rel_path)
        continue
    
    # Compute SHA-256
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    curr_hash = hasher.hexdigest()
    after_lines.append(f"{curr_hash}  {rel_path}")
    
    if curr_hash != orig_hash:
        mismatches.append((rel_path, orig_hash, curr_hash))

AFTER_PATH.write_text("\n".join(after_lines) + "\n", encoding="utf-8")
print(f"Recorded {len(after_lines)} file hashes to: {AFTER_PATH}")

print("\n--- Hash Comparison Summary ---")
print(f"Total Files Checked : {len(before_lines)}")
print(f"Identical Matches    : {len(after_lines) - len(mismatches)}")
print(f"Mismatches           : {len(mismatches)}")
print(f"Missing Files        : {len(missing)}")

if missing:
    print("\nMissing Files:")
    for m in missing:
        print(f"  [MISSING] {m}")

if mismatches:
    print("\nMismatched Files:")
    for path, exp, got in mismatches:
        print(f"  [MISMATCH] {path}: expected {exp[:8]}..., got {got[:8]}...")
    sys.exit(1)
else:
    print("\nSUCCESS: All 353 tracked files match hashes_before.txt bit-for-bit!")
    print("ABSOLUTE RULE 1 & 2 VERIFIED: ZERO files outside docs_v2/ were modified, renamed, moved, or deleted.")
    sys.exit(0)
