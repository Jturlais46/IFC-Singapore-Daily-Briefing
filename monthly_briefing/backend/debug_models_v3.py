import asyncio
import os
from google import genai
from config import GEMINI_API_KEY
import sys

# Force encoding to utf-8 for console output
sys.stdout.reconfigure(encoding='utf-8')

async def list_models():
    print(f"--- Debugging Gemini Models (Attempt 3 - Filtered) ---")
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set.")
        return

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("Attempting to list models...")
        try:
            pager = client.models.list() 
            print("Available 'flash' models:")
            found = False
            for model in pager:
                if 'flash' in model.name.lower() or 'pro' in model.name.lower():
                     print(f" - {model.name}")
                     found = True
            
            if not found:
                print("No 'flash' or 'pro' models found. Listing ALL:")
                for model in client.models.list():
                    print(f" - {model.name}")

        except Exception as e:
            print(f"Error listing models: {e}")

    except Exception as e:
        print(f"Client initialization error: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
