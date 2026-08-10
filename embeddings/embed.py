import json
import os
import time
from uuid import uuid4

from google.genai.types import UploadFileConfig

# sys.path.append("/Users/sushant/Projects/agent_iq")
from connections.genai import GenAI

genai_client = GenAI.get_client()

output_file_name = os.environ.get("JSON_REQUESTS_FILE_NAME", "chunks.jsonl")
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


def upload_chunks_and_create_embeddings():
    uploaded_file = genai_client.files.upload(
        file=output_file_name,
        config=UploadFileConfig(
            display_name="generate-embeddings-batch-file", mime_type="jsonl"
        ),
    )
    batch_job = genai_client.batches.create_embeddings(
        model=embedding_model,
        src={"file_name": uploaded_file.name},
        config={"display_name": "generate_embeddings_batch-job"},
    )

    while True:
        if batch_job.state.name in (
            "JOB_STATE_SUCCEEDED",
            "JOB_STATE_FAILED",
            "JOB_STATE_CANCELLED",
        ):
            break
        print(f"Job status: {batch_job.state.name}")
        time.sleep(30)

    print(f"Job finished with status: {batch_job.state.name}")

    return batch_job
