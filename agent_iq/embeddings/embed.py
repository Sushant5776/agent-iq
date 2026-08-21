import json
import os
import time
from uuid import uuid4

from firebase_admin import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from google.genai.types import CreateEmbeddingsBatchJobConfig, UploadFileConfig, EmbedContentConfig

from agent_iq.connections.firebase import Firebase
from agent_iq.connections.genai import GenAI

genai_client = GenAI.get_client()
firebase_app = Firebase.get_app()
db = firestore.client(app=firebase_app)

output_file_name = os.environ.get("JSON_REQUESTS_FILE_NAME", "chunks.jsonl")
embedding_model = os.environ.get("EMBEDDING_MODEL", "gemini-embedding-2")


def process_chunks(chunk_obj):
    original_file_name = chunk_obj["file_name"]
    chunks = chunk_obj["chunks"]
    collection_name = (
        original_file_name.strip().replace(" ", "_").replace(".", "_").replace("-", "_")
    )

    bulk_writer = db.bulk_writer()

    with open(output_file_name, "w") as file:
        for index, chunk in enumerate(chunks):
            unique_id = str(uuid4())

            # write to firebase
            doc_ref = db.collection(collection_name).document(unique_id)
            bulk_writer.set(
                doc_ref,
                {
                    "text": chunk,
                    "length": len(chunk),
                    "file_name": original_file_name,
                    "timestamp": firestore.firestore.SERVER_TIMESTAMP,
                    "index": index,
                },
            )

            embedding_request_obj = {
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

            jsonl_row = json.dumps(embedding_request_obj) + "\n"
            file.write(jsonl_row)

        bulk_writer.close()

    return collection_name


def create_embeddings():
    uploaded_file = genai_client.files.upload(
        file=output_file_name,
        config=UploadFileConfig(
            display_name="generate-embeddings-batch-file", mime_type="application/jsonl"
        ),
    )

    batch_job = genai_client.batches.create_embeddings(
        model=embedding_model,
        src={"file_name": uploaded_file.name},
        config=CreateEmbeddingsBatchJobConfig(
            display_name="generate_embeddings_batch_job"
        ),
    )

    while True:
        batch_job = genai_client.batches.get(name=batch_job.name)

        if batch_job.state and batch_job.state.name in (
            "JOB_STATE_SUCCEEDED",
            "JOB_STATE_FAILED",
            "JOB_STATE_CANCELLED",
        ):
            break

        print(f"Job status: {batch_job.state.name if batch_job.state else 'NO_STATE'}")
        time.sleep(30)

    print(f"Job finished with status: {batch_job.state.name}")

    if batch_job.state.name != "JOB_STATE_SUCCEEDED":
        raise Exception(f"{batch_job.state.name}")
    else:
        return batch_job.name


def process_embeddings(batch_job_name, collection_name):
    batch_job = genai_client.batches.get(name=batch_job_name)
    embedding_result_file = batch_job.dest.file_name
    print(
        f"Fetching results for job: {batch_job_name} from embedding result file: {embedding_result_file}"
    )

    content = genai_client.files.download(file=embedding_result_file)

    with open("embeddings_result.jsonl", "wb") as f:
        f.write(content)

    bulk_writer = db.bulk_writer()

    with open("embeddings_result.jsonl", "r") as f:
        for line in f:
            if not line.strip():
                continue

            embedding_obj = json.loads(line)

            firebase_file_id = embedding_obj["key"]
            embedding_array = embedding_obj["response"]["embedding"]["values"]
            token_count = embedding_obj["response"]["usageMetadata"]["promptTokenCount"]

            doc_ref = db.collection(collection_name).document(firebase_file_id)

            bulk_writer.update(
                doc_ref,
                {
                    "embedding": Vector(embedding_array),
                    "token_count": token_count,
                },
            )

        bulk_writer.close()

def get_query_embedding(query: str):
    embedding_config = EmbedContentConfig(
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=768
    )

    response = genai_client.models.embed_content(
        model=embedding_model, contents=query, config=embedding_config
    )

    if not response.embeddings or response.embeddings[0].values is None:
        raise ValueError("The embedding response did not contain a vector")

    return response.embeddings[0].values


def retrieve_top_embeddings(query: str, collection_name: str, limit: int = 10):
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    query_embedding = get_query_embedding(query=query)

    return list(
        db.collection(collection_name)
        .find_nearest(
            vector_field="embedding",
            query_vector=Vector(query_embedding),
            distance_measure=DistanceMeasure.COSINE,
            limit=limit,
        )
        .stream()
    )