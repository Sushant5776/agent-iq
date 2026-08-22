from agent_iq.embeddings.chunking import chunk_text_from_file
from agent_iq.embeddings.embed import (
    create_embeddings,
    process_chunks,
    process_embeddings,
)


def main(file_path: str):
    chunk_obj = chunk_text_from_file(file_path=file_path)
    collection_name = process_chunks(chunk_obj=chunk_obj)
    batch_job_name = create_embeddings()
    process_embeddings(batch_job_name=batch_job_name, collection_name=collection_name)
    return collection_name


if __name__ == "__main__":
    file_path = input("Enter file path: ")
    main(file_path=file_path)
