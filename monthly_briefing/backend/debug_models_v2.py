import asyncio
import os
from google import genai
from config import GEMINI_API_KEY

async def list_models():
    print(f"--- Debugging Gemini Models (Attempt 2) ---")
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set.")
        return

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("Attempting to list models...")
        try:
            # The SDK returns an iterator of Model objects
            # Let's just print dir() of the first one to see what we have if documentation is unclear
            pager = client.models.list() 
            print("Available models:")
            for model in pager:
                # specific check for generateContent support if possible, otherwise just list all
                print(f" - {model.name}")
        except Exception as e:
            print(f"Error listing models: {e}")

    except Exception as e:
        print(f"Client initialization error: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
