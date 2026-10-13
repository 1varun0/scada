#!/usr/bin/env python3
"""
Reusable execution utility to run commands in the isolated sandbox,
capture stdout/stderr verbatim to results_v2/raw/<name>.log,
and save exact command, working dir, timestamps, duration, and exit code
in results_v2/raw/<name>.json.
"""

import sys
import os
import subprocess
import time
import json
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SANDBOX_DIR = Path(tempfile.gettempdir()) / "p1_sandbox"
RAW_DIR = REPO_ROOT / "results_v2" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

def run_in_sandbox(cmd_list, output_name, cwd=None, env=None, timeout=None):
    if cwd is None:
        cwd = SANDBOX_DIR
    else:
        cwd = Path(cwd)

    log_path = RAW_DIR / f"{output_name}.log"
    sidecar_path = RAW_DIR / f"{output_name}.json"

    print(f"\n[RUNNER] Executing: {' '.join(cmd_list)}")
    print(f"[RUNNER] Working Directory: {cwd}")
    print(f"[RUNNER] Log Destination: {log_path}")

    start_time_iso = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    t0 = time.perf_counter()

    # Merge environment if provided
    run_env = os.environ.copy()
    # Ensure sandbox root is in PYTHONPATH
    run_env["PYTHONPATH"] = str(SANDBOX_DIR) + os.pathsep + run_env.get("PYTHONPATH", "")
    if env:
        run_env.update(env)

    try:
        proc = subprocess.run(
            cmd_list,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=run_env,
            timeout=timeout
        )
        duration_s = round(time.perf_counter() - t0, 4)
        exit_code = proc.returncode
        output_text = proc.stdout
    except subprocess.TimeoutExpired as te:
        duration_s = round(time.perf_counter() - t0, 4)
        exit_code = -1
        output_text = (te.stdout or "") + f"\n\n[RUNNER ERROR] Command timed out after {timeout} seconds."
    except Exception as e:
        duration_s = round(time.perf_counter() - t0, 4)
        exit_code = -2
        output_text = f"[RUNNER ERROR] Execution failed: {e}\n"

    # Write log verbatim (UTF-8 without BOM)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(output_text)

    # Write sidecar JSON
    sidecar_data = {
        "command": cmd_list,
        "command_str": " ".join(cmd_list),
        "cwd": str(cwd),
        "start_time": start_time_iso,
        "duration_s": duration_s,
        "exit_code": exit_code,
        "log_file": str(log_path.relative_to(REPO_ROOT)).replace("\\", "/")
    }

    with open(sidecar_path, "w", encoding="utf-8") as f:
        json.dump(sidecar_data, f, indent=2)

    print(f"[RUNNER] Completed in {duration_s}s with exit code {exit_code}")
    return exit_code, output_text, duration_s

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python runner_util.py <output_name> <command...>")
        sys.exit(1)
    out_name = sys.argv[1]
    command = sys.argv[2:]
    code, out, dur = run_in_sandbox(command, out_name)
    sys.exit(code)
