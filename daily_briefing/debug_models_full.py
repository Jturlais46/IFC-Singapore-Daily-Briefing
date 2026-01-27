
import os
from dotenv import load_dotenv
from google import genai
import sys

# Load env
env_path = os.path.join(os.getcwd(), 'backend', '.env')
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Listing models...")
try:
    for m in client.models.list():
        print(f"Name: {m.name}")
        print(f"DisplayName: {m.display_name}")
        print("-" * 20)
except Exception as e:
    print(f"Error listing models: {e}")
