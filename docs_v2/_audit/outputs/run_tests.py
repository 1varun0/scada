import subprocess
import sys
import os

def run_suite(cmd, output_path):
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(res.stdout)
    print(f"Saved to {output_path} (exit code {res.returncode})")
    lines = res.stdout.strip().split("\n")
    for line in lines[-5:]:
        print("  " + line)

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Root batch tests
    cmd1 = [sys.executable, "-m", "pytest", "tests/"]
    run_suite(cmd1, os.path.join(out_dir, "pytest_batch_output.txt"))
    
    # 2. scada_live tests
    cmd2 = [sys.executable, "-m", "pytest", "scada_live/tests/"]
    run_suite(cmd2, os.path.join(out_dir, "pytest_live_output.txt"))
