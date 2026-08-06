import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

gemini_api_key = os.environ.get("GEMINI_API_KEY", None)

class GenAI:
    client = None

    @staticmethod
    def get_client():
        if not gemini_api_key:
            raise ValueError("GenAI:get_client - GEMINI_API_KEY not set!")
        
        if not GenAI.client:
            GenAI.client = genai.Client(api_key=gemini_api_key, vertexai=False)

        return GenAI.client