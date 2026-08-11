from agent_iq.embeddings.chunking import chunk_text_from_file
from agent_iq.embeddings.embed import create_jsonl


def main(file_path: str):
    chunk_obj = chunk_text_from_file(file_path=file_path)
    create_jsonl(chunk_obj=chunk_obj)


if __name__ == "__main__":
    file_path = input("Enter file path: ")
    main(file_path=file_path)
