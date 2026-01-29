
import os
from dotenv import load_dotenv
from google import genai
import sys

# Load env from backend/.env or just parent
# The app structure seems to be daily_briefing/backend/.env
# But usually we run from root.
# Let's try to load from backend/.env
env_path = os.path.join(os.getcwd(), 'backend', '.env')
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in env")
    sys.exit(1)

print(f"Using API Key: {api_key[:5]}...{api_key[-5:]}")

client = genai.Client(api_key=api_key)

try:
    print("Listing available models...")
    # The SDK might have a different way to list, but typically models.list()
    # verify syntax for google-genai library
    # If this fails, we'll try the requests fallback
    for m in client.models.list():
        print(f" - {m.name}")
        
except Exception as e:
    print(f"Error using SDK: {e}")
    # Fallback to requests if SDK list is obscure
    import requests
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        print("\nRaw API List:")
        for m in data.get('models', []):
            print(f" - {m.get('name')}")
    else:
        print(f"Raw API failed: {resp.status_code} {resp.text}")
