import hmac
import os
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from google.genai.types import GenerateContentConfig, Part, UserContent
from pydantic import BaseModel, Field

from agent_iq.config import Settings
from agent_iq.connections.genai import GenAI
from agent_iq.embeddings.embed import list_collection_names, retrieve_top_embeddings
from agent_iq.embeddings.ingest import main as ingest_document


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    collection_name: str = Field(min_length=1, max_length=200)
    limit: int | None = Field(default=None, ge=1, le=50)


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict[str, object]]


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    expected_token = os.environ.get("API_ACCESS_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_ACCESS_TOKEN is not configured",
        )

    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _query(request: QueryRequest, settings: Settings) -> QueryResponse:
    limit = request.limit or settings.top_k_matching_results
    documents = retrieve_top_embeddings(
        query=request.query,
        collection_name=request.collection_name,
        limit=limit,
    )
    sources = []
    context_parts = []
    for document in documents:
        data = document.to_dict() or {}
        context_parts.append(data.get("text", ""))
        sources.append(
            {
                "document_id": document.id,
                "file_name": data.get("file_name"),
                "index": data.get("index"),
            }
        )

    history = [
        UserContent(
            parts=[
                Part(
                    text=(
                        "Answer using only the retrieved context. If it does not "
                        "contain the answer, say you do not know.\n\n"
                        f"Context:\n{chr(10).join(context_parts)}\n\n"
                        f"Question:\n{request.query}"
                    )
                )
            ]
        )
    ]
    response = GenAI.get_client().models.generate_content(
        model=settings.generation_model,
        contents=history,
        config=GenerateContentConfig(
            system_instruction="You are a helpful assistant named AgentIQ."
        ),
    )
    return QueryResponse(answer=response.text or "", sources=sources)


app = FastAPI(title="AgentIQ API", version="0.1.0")


@app.get("/")
def home() -> dict[str, str]:
    return {"message": "Welcome to the AgentIQ API!"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/collections", dependencies=[Depends(require_api_token)])
async def collections() -> dict[str, list[str]]:
    return {"collections": await run_in_threadpool(list_collection_names)}


@app.post(
    "/query", response_model=QueryResponse, dependencies=[Depends(require_api_token)]
)
async def query(request: QueryRequest) -> QueryResponse:
    settings = Settings.from_environment()
    return await run_in_threadpool(_query, request, settings)


@app.post("/ingest", dependencies=[Depends(require_api_token)])
async def ingest(file: Annotated[UploadFile, File()]) -> dict[str, str]:
    if not file.filename or Path(file.filename).suffix.lower() not in {".pdf", ".txt"}:
        raise HTTPException(
            status_code=400, detail="Only .pdf and .txt files are supported"
        )

    suffix = Path(file.filename).suffix.lower()
    safe_stem = "".join(
        character for character in Path(file.filename).stem if character.isalnum()
    )
    safe_name = f"{safe_stem or 'document'}{suffix}"

    with tempfile.TemporaryDirectory() as directory:
        file_path = Path(directory) / safe_name
        size = 0
        with file_path.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 20 * 1024 * 1024:
                    raise HTTPException(
                        status_code=413, detail="File exceeds 20 MiB limit"
                    )
                output.write(chunk)

        collection_name = await run_in_threadpool(ingest_document, str(file_path))

    return {"status": "completed", "collection_name": collection_name}
