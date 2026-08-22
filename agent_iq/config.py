import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is not configured")
    return value


def _positive_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    embedding_model: str
    generation_model: str
    firestore_collection_name: str
    firebase_credentials_path: Path | None
    embedding_chunk_size: int
    embedding_overlap_size: int
    json_requests_file_name: Path
    output_dimensionality: int
    top_k_matching_results: int

    @classmethod
    def from_environment(cls) -> "Settings":
        chunk_size = _positive_int("EMBEDDING_CHUNK_SIZE", 700)
        overlap_size = _positive_int("EMBEDDING_OVERLAP_SIZE", 140)
        if overlap_size >= chunk_size:
            raise ValueError(
                "EMBEDDING_OVERLAP_SIZE must be smaller than EMBEDDING_CHUNK_SIZE"
            )

        credentials_value = os.environ.get("FIREBASE_CREDENTIALS_PATH")
        credentials_path = (
            Path(credentials_value).expanduser() if credentials_value else None
        )

        return cls(
            gemini_api_key=_required("GEMINI_API_KEY"),
            embedding_model=os.environ.get("EMBEDDING_MODEL", "gemini-embedding-2"),
            generation_model=os.environ.get("LANGUAGE_MODEL", "gemini-3.5-flash"),
            firestore_collection_name=_required("FIRESTORE_COLLECTION_NAME"),
            firebase_credentials_path=credentials_path,
            embedding_chunk_size=chunk_size,
            embedding_overlap_size=overlap_size,
            json_requests_file_name=Path(
                os.environ.get("JSON_REQUESTS_FILE_NAME", "chunks.jsonl")
            ),
            output_dimensionality=_positive_int("OUTPUT_DIMENSIONALITY", 512),
            top_k_matching_results=_positive_int("TOP_K_MATCHING_RESULTS", 10),
        )
