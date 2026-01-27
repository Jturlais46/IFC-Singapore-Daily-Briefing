import os
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from google import genai
from config import GEMINI_API_KEY

async def list_models():
    print(f"--- Debugging Gemini Models ---")
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set.")
        return

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("Attempting to list models...")
        # The new SDK might use a different way to list, but let's try the suspected method or inspect errors
        try:
            # Pager object
            pager = client.models.list() 
            print("Available models:")
            for model in pager:
                print(f" - {model.name} (Supported actions: {model.supported_generation_methods})")
        except Exception as e:
            print(f"Error listing models with client.models.list(): {e}")

    except Exception as e:
        print(f"Client initialization error: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
