import tempfile
from pathlib import Path

from agent_iq.embeddings.chunking import chunk_text_from_file
from agent_iq.embeddings.embed import (
    create_embeddings,
    process_chunks,
    process_embeddings,
)


def main(file_path: str):
    chunk_obj = chunk_text_from_file(file_path=file_path)
    with tempfile.TemporaryDirectory(prefix="agent-iq-embedding-") as directory:
        request_file_path = Path(directory) / "chunks.jsonl"
        manifest = process_chunks(
            chunk_obj=chunk_obj, request_file_path=request_file_path
        )
        batch_job_name = create_embeddings(request_file_path=request_file_path)
        process_embeddings(batch_job_name=batch_job_name, manifest=manifest)
        return manifest.collection_name


if __name__ == "__main__":
    file_path = input("Enter file path: ")
    main(file_path=file_path)
