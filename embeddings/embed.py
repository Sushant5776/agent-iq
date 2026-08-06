import json
import os
from uuid import uuid4

from connections.genai import GenAI

genai_client = GenAI.get_client()

output_file_name = os.environ.get("JSON_REQUESTS_FILE_NAME", "embeddings.jsonl")
embedding_model = os.environ.get("EMBEDDING_MODEL", "gemini-embedding-2")


def create_jsonl(chunk_obj) -> None:
    file_name = chunk_obj["file_name"]
    chunks = chunk_obj["chunks"]

    with open(output_file_name, "w") as file:
        for chunk in chunks:
            unique_id = str(uuid4())

            request_obj = {
                "key": unique_id,
                "request": {
                    "model": f"models/{embedding_model}",
                    "content": {"parts": [{"text": chunk}]},
                    "taskType": "RETRIEVAL_DOCUMENT",
                    "title": file_name,
                },
            }

            jsonl_row = json.dumps(request_obj) + "\n"

            file.write(jsonl_row)
