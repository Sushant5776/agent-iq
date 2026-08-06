import os

from dotenv import load_dotenv
from google.genai.types import Part

from connections.genai import GenAI

load_dotenv()
genai_client = GenAI.get_client()
model = os.environ.get("LANGUAGE_MODEL", "None")


def main():
    print("Hello from agent-iq!")
    response = genai_client.models.generate_content(
        model=model, contents=[Part(text="Hi, How are you?")]
    )
    print(response.text)


if __name__ == "__main__":
    main()
