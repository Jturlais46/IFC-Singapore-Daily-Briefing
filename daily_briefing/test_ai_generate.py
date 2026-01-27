
import os
from dotenv import load_dotenv
from google import genai
import sys

# Load env
env_path = os.path.join(os.getcwd(), 'backend', '.env')
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found")
    sys.exit(1)

client = genai.Client(api_key=api_key)

models_to_test = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro-001",
    "gemini-1.5-pro-002",
    "gemini-2.0-flash-exp",
    "gemini-1.0-pro"
]

print(f"Testing generation with API Key ending in ...{api_key[-5:]}")

for model_name in models_to_test:
    print(f"\n--- Testing model: '{model_name}' ---")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'Hello'"
        )
        print(f"SUCCESS! Response: {response.text}")
        print(f"CONCLUSION: Use '{model_name}'")
        break # Found one that works
    except Exception as e:
        print(f"FAILED: {e}")

