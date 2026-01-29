import os
import subprocess
from pathlib import Path

def test_launch():
    app_data = os.environ.get('LOCALAPPDATA', '')
    arc_path = Path(app_data) / "Microsoft" / "WindowsApps" / "Arc.exe"
    
    print(f"Testing launch of: {arc_path}")
    
    if not arc_path.exists():
        print("Path does not exist.")
        return

    try:
        # Method 1: os.startfile (Standard Windows way to open associated app/alias)
        print("Attempting os.startfile...")
        os.startfile(str(arc_path))
        print("os.startfile call completed. Did a browser open for you?")
    except Exception as e:
        print(f"os.startfile failed: {e}")

    try:
        # Method 2: subprocess.Popen
        print("Attempting subprocess.Popen...")
        subprocess.Popen([str(arc_path), "https://google.com"])
        print("subprocess.Popen call completed.")
    except Exception as e:
        print(f"subprocess.Popen failed: {e}")

if __name__ == "__main__":
    test_launch()
