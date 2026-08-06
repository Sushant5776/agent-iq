import math
import os

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

chunk_size = int(os.environ.get("EMBEDDING_CHUNK_SIZE", 700))
overlap_size = int(os.environ.get("EMBEDDING_OVERLAP_SIZE", 140))

def estimate_gemini_tokens(text: str) -> int:
    text = text.strip()

    if not text:
        return 0
    else:
        return math.ceil(len(text) / 3)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=overlap_size,
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