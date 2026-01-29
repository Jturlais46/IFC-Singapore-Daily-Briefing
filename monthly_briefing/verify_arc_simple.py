import subprocess
import os
from pathlib import Path

def test():
    print("Pre-test check...")
    # 1. Check path
    app_data = os.environ.get('LOCALAPPDATA', '')
    arc_exe = Path(app_data) / "Microsoft" / "WindowsApps" / "Arc.exe"
    print(f"Path: {arc_exe}")
    print(f"Exists: {arc_exe.exists()}")
    
    # 2. Try simple call
    try:
        print("Calling 'arc --version'...")
        # Use shell=True for App Execution Aliases
        proc = subprocess.run(["arc", "--version"], capture_output=True, text=True, timeout=10, shell=True)
        print(f"Return code: {proc.returncode}")
        print(f"Stdout: {proc.stdout.strip()}")
        print(f"Stderr: {proc.stderr.strip()}")
    except Exception as e:
        print(f"Call failed: {e}")

    # 3. Try to launch (non-headless)
    try:
        print("Spawning Arc GUI...")
        subprocess.Popen(["arc", "https://google.com"], shell=True)
        print("Spawn command sent. Please check if Arc opened.")
    except Exception as e:
        print(f"Spawn failed: {e}")

if __name__ == "__main__":
    test()
