import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def verify_arc():
    # Try the absolute path we found
    arc_path = Path(r"C:\Program Files\WindowsApps\TheBrowserCompany.Arc_1.89.1.3_x64__ttt1ap7aakyb4\Arc.exe")
    
    print(f"Checking path: {arc_path}")
    if arc_path.exists():
        print("[SUCCESS] Path exists.")
    else:
        # Fallback to checking the folder first or trying the alias again
        print("[FAIL] Absolute path does not exist or access denied.")
        app_data = os.environ.get('LOCALAPPDATA', '')
        arc_path = Path(app_data) / "Microsoft" / "WindowsApps" / "Arc.exe"
        print(f"Falling back to alias: {arc_path}")

    print("Attempting to launch Arc via Playwright...")
    try:
        with sync_playwright() as p:
            # Note: Many App Execution Aliases require shell=True or are better handled via channel="chrome"
            # but Arc is unique. Let's try executable_path first.
            browser = p.chromium.launch(
                executable_path=str(arc_path),
                headless=False
            )
            page = browser.new_page()
            page.goto("https://www.google.com")
            print(f"[SUCCESS] Launched Arc. Title: {page.title()}")
            browser.close()
    except Exception as e:
        print(f"[FAIL] Error launching Arc: {e}")

if __name__ == "__main__":
    verify_arc()
