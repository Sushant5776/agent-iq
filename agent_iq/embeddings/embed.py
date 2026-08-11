import json
import os
import time
from uuid import uuid4

from google.genai.types import UploadFileConfig, CreateEmbeddingsBatchJobConfig

# sys.path.append("/Users/sushant/Projects/agent_iq")
from agent_iq.connections.genai import GenAI

genai_client = GenAI.get_client()

output_file_name = os.environ.get("JSON_REQUESTS_FILE_NAME", "chunks.jsonl")
embedding_model = os.environ.get("EMBEDDING_MODEL", "gemini-embedding-2")


def create_jsonl(chunk_obj) -> None:
    original_file_name = chunk_obj["file_name"]
    chunks = chunk_obj["chunks"]

    with open(output_file_name, "w") as file:
        for chunk in chunks:
            unique_id = str(uuid4())

            request_obj = {
                "key": unique_id,
                "request": {
                    "model": f"models/{embedding_model}",
                    "content": {"parts": [{"text": chunk}]},
                    "embed_content_config": {
                        "task_type": "RETRIEVAL_DOCUMENT",
                        "title": original_file_name,
                        "output_dimensionality": 768,  # firestore only supports upto 2048
                    },
                },
            }

            jsonl_row = json.dumps(request_obj) + "\n"

            file.write(jsonl_row)

    return original_file_name


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
        config=CreateEmbeddingsBatchJobConfig(display_name="generate_embeddings_batch_job")
    )

    while True:
        if batch_job.state and batch_job.state.name in (
            "JOB_STATE_SUCCEEDED",
            "JOB_STATE_FAILED",
            "JOB_STATE_CANCELLED",
        ):
            break

        print(f"Job status: {batch_job.state.name if batch_job.state else 'NO_STATE'}")
        time.sleep(30)

    print(f"Job finished with status: {batch_job.state.name}")

    return batch_job
