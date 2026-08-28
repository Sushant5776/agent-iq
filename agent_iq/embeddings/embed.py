import json
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from firebase_admin import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from google.genai.types import (
    CreateEmbeddingsBatchJobConfig,
    EmbedContentConfig,
    UploadFileConfig,
)

from agent_iq.config import Settings
from agent_iq.connections.firebase import Firebase
from agent_iq.connections.genai import GenAI


@dataclass(frozen=True)
class ChunkDocument:
    document_id: str
    text: str
    index: int


@dataclass(frozen=True)
class EmbeddingManifest:
    collection_name: str
    file_name: str
    documents: tuple[ChunkDocument, ...]


def _database():
    return firestore.client(app=Firebase.get_app())


def _collection_name(file_name: str) -> str:
    return file_name.strip().replace(" ", "_").replace(".", "_").replace("-", "_")


def process_chunks(
    *, chunk_obj: dict[str, object], request_file_path: Path
) -> EmbeddingManifest:
    """Create a request-scoped Gemini JSONL file without touching Firestore."""
    settings = Settings.from_environment()
    original_file_name = str(chunk_obj["file_name"])
    raw_chunks = chunk_obj["chunks"]
    if not isinstance(raw_chunks, list) or not raw_chunks:
        raise ValueError("No chunks were provided for embedding")

    request_file_path.parent.mkdir(parents=True, exist_ok=True)
    documents: list[ChunkDocument] = []
    with request_file_path.open("w", encoding="utf-8") as request_file:
        for index, raw_chunk in enumerate(raw_chunks):
            chunk = str(raw_chunk)
            if not chunk.strip():
                continue

            document = ChunkDocument(document_id=str(uuid4()), text=chunk, index=index)
            documents.append(document)
            request_file.write(
                json.dumps(
                    {
                        "key": document.document_id,
                        "request": {
                            "model": f"models/{settings.embedding_model}",
                            "content": {"parts": [{"text": document.text}]},
                            "embed_content_config": {
                                "task_type": "RETRIEVAL_DOCUMENT",
                                "title": original_file_name,
                                "output_dimensionality": (
                                    settings.output_dimensionality
                                ),
                            },
                        },
                    }
                )
                + "\n"
            )

    if not documents:
        raise ValueError("No non-empty chunks were provided for embedding")

    return EmbeddingManifest(
        collection_name=_collection_name(original_file_name),
        file_name=original_file_name,
        documents=tuple(documents),
    )


def create_embeddings(request_file_path: Path) -> str:
    """Upload one request's batch and wait for it for a bounded amount of time."""
    settings = Settings.from_environment()
    client = GenAI.get_client()
    uploaded_file = client.files.upload(
        file=request_file_path,
        config=UploadFileConfig(
            display_name="generate-embeddings-batch-file",
            mime_type="application/jsonl",
        ),
    )
    if not uploaded_file.name:
        raise RuntimeError("Gemini did not return an uploaded file name")

    batch_job = client.batches.create_embeddings(
        model=settings.embedding_model,
        src={"file_name": uploaded_file.name},
        config=CreateEmbeddingsBatchJobConfig(
            display_name="generate_embeddings_batch_job"
        ),
    )
    if not batch_job.name:
        raise RuntimeError("Gemini did not return an embedding batch job name")

    deadline = time.monotonic() + settings.embedding_batch_timeout_seconds
    while True:
        batch_job = client.batches.get(name=batch_job.name)
        state_name = batch_job.state.name if batch_job.state else "NO_STATE"
        if state_name in {
            "JOB_STATE_SUCCEEDED",
            "JOB_STATE_FAILED",
            "JOB_STATE_CANCELLED",
        }:
            break
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "Embedding processing did not finish before the request deadline"
            )
        time.sleep(settings.embedding_batch_poll_seconds)

    if state_name != "JOB_STATE_SUCCEEDED":
        raise RuntimeError(f"Embedding job failed: {state_name}")
    return str(batch_job.name)


def _parse_embedding_results(
    content: bytes, manifest: EmbeddingManifest
) -> dict[str, tuple[list[float], int]]:
    """Validate Gemini's complete response before any Firestore writes occur."""
    expected_ids = {document.document_id for document in manifest.documents}
    results: dict[str, tuple[list[float], int]] = {}
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError(
            "Gemini returned an invalid embeddings result file"
        ) from error

    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            embedding_obj = json.loads(line)
            document_id = embedding_obj["key"]
            values = embedding_obj["response"]["embedding"]["values"]
            token_count = embedding_obj["response"]["usageMetadata"]["promptTokenCount"]
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"Gemini returned an invalid result on line {line_number}"
            ) from error

        if document_id not in expected_ids:
            raise RuntimeError("Gemini returned a result for an unknown document")
        if document_id in results:
            raise RuntimeError("Gemini returned a duplicate embedding result")
        if not isinstance(values, list) or not values:
            raise RuntimeError("Gemini returned an empty embedding vector")
        if not all(isinstance(value, (int, float)) for value in values):
            raise RuntimeError("Gemini returned a non-numeric embedding vector")
        if not isinstance(token_count, int):
            raise TypeError("Gemini returned an invalid token count")

        results[document_id] = ([float(value) for value in values], token_count)

    missing_ids = expected_ids - results.keys()
    if missing_ids:
        raise RuntimeError(f"Gemini omitted {len(missing_ids)} embedding result(s)")
    return results


def process_embeddings(*, batch_job_name: str, manifest: EmbeddingManifest) -> None:
    """Download results in memory and create only fully embedded documents."""
    client = GenAI.get_client()
    batch_job = client.batches.get(name=batch_job_name)
    if not batch_job.dest or not batch_job.dest.file_name:
        raise RuntimeError("Gemini did not return an embeddings result file")

    content = client.files.download(file=batch_job.dest.file_name)
    results = _parse_embedding_results(content, manifest)

    database = _database()
    bulk_writer = database.bulk_writer()
    for document in manifest.documents:
        embedding, token_count = results[document.document_id]
        document_reference = database.collection(manifest.collection_name).document(
            document.document_id
        )
        bulk_writer.set(
            document_reference,
            {
                "text": document.text,
                "length": len(document.text),
                "file_name": manifest.file_name,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "index": document.index,
                "embedding": Vector(embedding),
                "token_count": token_count,
            },
        )
    bulk_writer.close()


def get_query_embedding(query: str):
    settings = Settings.from_environment()
    embedding_config = EmbedContentConfig(
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=settings.output_dimensionality,
    )
    response = GenAI.get_client().models.embed_content(
        model=settings.embedding_model, contents=query, config=embedding_config
    )
    if not response.embeddings or response.embeddings[0].values is None:
        raise ValueError("The embedding response did not contain a vector")
    return response.embeddings[0].values


def retrieve_top_embeddings(query: str, collection_name: str, limit: int = 10):
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    query_embedding = get_query_embedding(query=query)
    return list(
        _database()
        .collection(collection_name)
        .find_nearest(
            vector_field="embedding",
            query_vector=Vector(query_embedding),
            distance_measure=DistanceMeasure.COSINE,
            limit=limit,
        )
        .stream()
    )


def list_collection_names():
    return sorted(collection.id for collection in _database().collections())
