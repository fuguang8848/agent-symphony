"""
Test subprocess spawn
"""
import sys, os, subprocess, time

python_exe = sys.executable
print(f"Python: {python_exe}")

# Test: spawn a simple script that writes to a file
test_dir = os.path.expanduser("~/.openclaw/symphony/")
os.makedirs(test_dir, exist_ok=True)

test_script = os.path.join(test_dir, "test_spawn.py")
with open(test_script, 'w') as f:
    f.write('import time, os\ntime.sleep(1)\nopen(os.path.expanduser("~/.openclaw/symphony/test_result.txt"),"w").write("OK")')

result_file = os.path.expanduser("~/.openclaw/symphony/test_result.txt")

print("Spawning test subprocess...")
proc = subprocess.Popen(
    [python_exe, test_script],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True
)
print(f"Process spawned, pid={proc.pid}")

time.sleep(5)

print(f"Result file exists: {os.path.exists(result_file)}")
if os.path.exists(result_file):
    with open(result_file) as f:
        print(f"Result: {f.read()}")
else:
    print("Result file NOT found!")
    try:
        proc.wait(timeout=1)
        print(f"Process exited with code: {proc.returncode}")
    except subprocess.TimeoutExpired:
        print("Process still running")
