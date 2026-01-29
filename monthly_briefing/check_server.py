import requests
import time

def check_server():
    print("Checking server health at http://127.0.0.1:8000/docs ...")
    start = time.time()
    try:
        r = requests.get("http://127.0.0.1:8000/docs", timeout=5)
        duration = time.time() - start
        print(f"Status: {r.status_code}")
        print(f"Time: {duration:.2f}s")
        if r.status_code == 200:
            print("[PASS] Server is responsive.")
        else:
            print("[FAIL] Server returned error.")
    except Exception as e:
        print(f"[FAIL] Server check failed: {e}")

if __name__ == "__main__":
    check_server()
