import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv('.env')
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
try:
    models = genai.list_models()
    print("Available models supporting generateContent:")
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error: {e}")
