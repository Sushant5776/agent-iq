from google import genai

from agent_iq.config import Settings


class GenAI:
    __client = None

    @staticmethod
    def get_client():
        if not GenAI.__client:
            settings = Settings.from_environment()
            GenAI.__client = genai.Client(
                api_key=settings.gemini_api_key,
                vertexai=False,
            )

        return GenAI.__client
