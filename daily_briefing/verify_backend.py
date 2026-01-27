import sys
import os
import traceback

print("--- Verifying Backend Modules ---")

# Add backend dir to path so we can import config
backend_path = os.path.join(os.getcwd(), 'backend')
sys.path.append(backend_path)
print(f"Path added: {backend_path}")

try:
    print("1. Importing parser...")
    from backend.processing import parser
    print("   [OK] Parser imported.")
except Exception:
    print("   [FAIL] Parser import failed:")
    traceback.print_exc()

try:
    print("2. Importing categorizer...")
    from backend.processing import categorizer
    print("   [OK] Categorizer imported.")
except Exception:
    print("   [FAIL] Categorizer import failed:")
    traceback.print_exc()

try:
    print("3. Importing main...")
    from backend import main
    print("   [OK] Main imported.")
except Exception:
    print("   [FAIL] Main import failed:")
    traceback.print_exc()

print("--- Verification Complete ---")
