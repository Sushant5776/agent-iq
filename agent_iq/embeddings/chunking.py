from pathlib import Path

from pypdf import PdfReader

from agent_iq.embeddings.splitter import split_text


class InvalidDocumentError(ValueError):
    """Raised when a document contains no text that can be embedded."""


def chunk_text_from_file(file_path: str | None = None):
    if not file_path or not file_path.strip():
        raise AttributeError("ingest:read_file file_path not provided.")

    path = Path(file_path)
    file_name = path.name

    if path.suffix.lower() != ".pdf":
        with path.open("r", encoding="utf-8") as file:
            content = file.read()
    else:
        pdf_reader = PdfReader(path)
        content = ""

        for page in pdf_reader.pages:
            text = page.extract_text()

            if text:
                content += text + "\n"

    if not content.strip():
        raise InvalidDocumentError("The document does not contain extractable text")

    chunks = split_text(content)
    if not chunks:
        raise InvalidDocumentError("The document did not produce any text chunks")

    return {
        "file_name": file_name,
        "chunks": chunks,
    }
