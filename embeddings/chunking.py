from pypdf import PdfReader
from splitter import splitter


def chunk_text_from_file(file_path: str | None = None) -> list[str]:
    if not file_path:
        raise AttributeError("ingest:read_file file_path not provided.")

    file_path = file_path.strip()

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

    return chunks
