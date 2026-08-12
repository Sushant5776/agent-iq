from dotenv import load_dotenv
from google.genai.types import GenerateContentConfig, ModelContent, Part, UserContent

from agent_iq.connections.genai import GenAI

load_dotenv()

genai_client = GenAI.get_client()

def update_history(history, text, role):
    match role:
        case "user":
            message = UserContent(parts=[Part(text=text)])
        case "model":
            message = ModelContent(parts=[Part(text=text)])
        case _:
            message = None

    if not message:
        raise ValueError("Message is not correct.")

    history.append(message)

def main():
    config = GenerateContentConfig(
        system_instruction="You are a helpful assistant named AgentIQ. You will assist users in friendly manner to answer their queries based data retrieved as part of RAG system.",
    )
    history = [ModelContent(parts=[Part(text="Hello, I'm AgentIQ! How can I help you?", )])]

    first_turn = True

    while True:
        print(history[-1].parts[-1].text)

        if first_turn:
            print("When you are done type exit to close the session!")
            first_turn = False
        
        text = input("====>>>> ")

        if text == "exit":
            print("Thanks for the time!")
            exit()
        
        update_history(history=history, text=text, role="user")

        response = genai_client.models.generate_content(model="gemini-3.5-flash", contents=history, config=config)
        update_history(history=history, text=response.text, role="model")


if __name__ == "__main__":
    main()
