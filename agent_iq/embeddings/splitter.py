import math

from langchain_text_splitters import RecursiveCharacterTextSplitter

from agent_iq.config import Settings


def estimate_gemini_tokens(text: str) -> int:
    text = text.strip()

    if not text:
        return 0
    else:
        return math.ceil(len(text) / 3)


def split_text(text: str) -> list[str]:
    settings = Settings.from_environment()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.embedding_chunk_size,
        chunk_overlap=settings.embedding_overlap_size,
        separators=[
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            "; ",
            ", ",
            " ",
            "",
        ],
        keep_separator=True,
        strip_whitespace=True,
        length_function=estimate_gemini_tokens,
    )
    return splitter.split_text(text)
