from pypdf import PdfReader
from agent_iq.embeddings.splitter import splitter


def chunk_text_from_file(file_path: str | None = None):
    if not file_path or not file_path.strip():
        raise AttributeError("ingest:read_file file_path not provided.")

    file_name = file_path.split("/")[-1]

    if not file_path.endswith(".pdf"):
        with open(file_path, "r") as file:
            content = file.read()
    else:
        pdf_reader = PdfReader(file_path)
        content = ""

        for page in pdf_reader.pages:
            text = page.extract_text()

            if text:
                content += text + "\n"

    chunks = splitter.split_text(content)

    return {
        "file_name": file_name,
        "chunks": chunks,
    }
