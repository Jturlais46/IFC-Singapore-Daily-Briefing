
import os
from dotenv import load_dotenv
from google import genai

# Load environment
env_path = os.path.join(os.getcwd(), 'daily_briefing', 'backend', '.env')
print(f"Loading .env from {env_path}")
load_dotenv(env_path)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found.")
    exit(1)

client = genai.Client(api_key=api_key)

print("Listing models...")
try:
    # The SDK might have different ways to list models depending on version.
    # Trying standard expected method for google-genai package
    for m in client.models.list():
        print(f"Model: {m}")
        # Try to inspect standard attributes if available
        if hasattr(m, 'name'): print(f"Name: {m.name}")
        if hasattr(m, 'supported_generation_methods'): print(f"Methods: {m.supported_generation_methods}")
        print("-" * 20)
except Exception as e:
    print(f"Error listing models: {e}")
