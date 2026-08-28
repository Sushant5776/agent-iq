import asyncio
import json
import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx

from agent_iq.api import MAX_PROXIED_UPLOAD_BYTES, app
from agent_iq.embeddings import ingest
from agent_iq.embeddings.embed import (
    ChunkDocument,
    EmbeddingManifest,
    _parse_embedding_results,
    process_chunks,
    process_embeddings,
)

TEST_ENVIRONMENT = {
    "GEMINI_API_KEY": "test-gemini-key",
    "FIRESTORE_COLLECTION_NAME": "test-collection",
    "EMBEDDING_MODEL": "test-embedding-model",
    "OUTPUT_DIMENSIONALITY": "3",
}


class IngestionStorageTests(unittest.TestCase):
    @patch.dict(os.environ, TEST_ENVIRONMENT, clear=False)
    def test_process_chunks_writes_only_to_explicit_request_path(self):
        shared_paths = [Path("chunks.jsonl"), Path("embeddings_result.jsonl")]
        before = {
            path: path.read_bytes() if path.exists() else None for path in shared_paths
        }
        with tempfile.TemporaryDirectory() as directory:
            request_path = Path(directory) / "request" / "chunks.jsonl"
            manifest = process_chunks(
                chunk_obj={"file_name": "Example.txt", "chunks": ["one", "two"]},
                request_file_path=request_path,
            )

            rows = [json.loads(line) for line in request_path.read_text().splitlines()]
            self.assertEqual(manifest.collection_name, "Example_txt")
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                {row["key"] for row in rows},
                {document.document_id for document in manifest.documents},
            )
        after = {
            path: path.read_bytes() if path.exists() else None for path in shared_paths
        }
        self.assertEqual(after, before)

    def test_two_ingestions_use_distinct_temporary_manifests(self):
        barrier = threading.Barrier(2)
        paths: list[Path] = []
        paths_lock = threading.Lock()

        def fake_process_chunks(*, chunk_obj, request_file_path):
            request_file_path.write_text("request", encoding="utf-8")
            with paths_lock:
                paths.append(request_file_path)
            return SimpleNamespace(collection_name=request_file_path.parent.name)

        def fake_create_embeddings(*, request_file_path):
            self.assertTrue(request_file_path.exists())
            barrier.wait(timeout=5)
            return str(request_file_path)

        with (
            patch.object(
                ingest,
                "chunk_text_from_file",
                return_value={"file_name": "same.txt", "chunks": ["text"]},
            ),
            patch.object(ingest, "process_chunks", side_effect=fake_process_chunks),
            patch.object(
                ingest, "create_embeddings", side_effect=fake_create_embeddings
            ),
            patch.object(ingest, "process_embeddings"),
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            results = list(executor.map(ingest.main, ["one.txt", "two.txt"]))

        self.assertEqual(len(set(paths)), 2)
        self.assertEqual(len(set(results)), 2)
        self.assertTrue(all(not path.exists() for path in paths))


class EmbeddingResultTests(unittest.TestCase):
    def test_incomplete_embedding_result_is_rejected(self):
        manifest = EmbeddingManifest(
            collection_name="document_txt",
            file_name="document.txt",
            documents=(
                ChunkDocument(document_id="one", text="first", index=0),
                ChunkDocument(document_id="two", text="second", index=1),
            ),
        )
        content = (
            json.dumps(
                {
                    "key": "one",
                    "response": {
                        "embedding": {"values": [0.1, 0.2, 0.3]},
                        "usageMetadata": {"promptTokenCount": 1},
                    },
                }
            )
            + "\n"
        ).encode()

        with self.assertRaisesRegex(RuntimeError, "omitted 1"):
            _parse_embedding_results(content, manifest)

    def test_downloaded_result_is_processed_without_a_shared_output_file(self):
        manifest = EmbeddingManifest(
            collection_name="document_txt",
            file_name="document.txt",
            documents=(ChunkDocument(document_id="one", text="first", index=0),),
        )
        content = (
            json.dumps(
                {
                    "key": "one",
                    "response": {
                        "embedding": {"values": [0.1, 0.2, 0.3]},
                        "usageMetadata": {"promptTokenCount": 1},
                    },
                }
            )
            + "\n"
        ).encode()
        client = SimpleNamespace(
            batches=SimpleNamespace(
                get=lambda **_kwargs: SimpleNamespace(
                    dest=SimpleNamespace(file_name="result-file")
                )
            ),
            files=SimpleNamespace(download=lambda **_kwargs: content),
        )
        database = MagicMock()
        shared_path = Path("embeddings_result.jsonl")
        before = shared_path.read_bytes() if shared_path.exists() else None

        with (
            patch("agent_iq.embeddings.embed.GenAI.get_client", return_value=client),
            patch("agent_iq.embeddings.embed._database", return_value=database),
        ):
            process_embeddings(batch_job_name="batch", manifest=manifest)

        after = shared_path.read_bytes() if shared_path.exists() else None
        self.assertEqual(after, before)
        database.bulk_writer.return_value.set.assert_called_once()
        database.bulk_writer.return_value.close.assert_called_once()


class UploadValidationTests(unittest.TestCase):
    async def _post_file(self, file_name: str, content: bytes) -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.post(
                "/ingest",
                headers={"Authorization": "Bearer test-api-token"},
                files={"file": (file_name, content, "text/plain")},
            )

    @patch.dict(os.environ, {"API_ACCESS_TOKEN": "test-api-token"}, clear=False)
    def test_oversized_upload_returns_structured_413(self):
        response = asyncio.run(
            self._post_file(
                "large.txt",
                b"x" * (MAX_PROXIED_UPLOAD_BYTES + 1),
            )
        )

        self.assertEqual(response.status_code, 413)
        payload = response.json()
        self.assertEqual(payload["code"], "http_413")
        self.assertEqual(payload["request_id"], response.headers["X-Request-ID"])
        self.assertIn("4 MiB", payload["detail"])

    @patch.dict(os.environ, {"API_ACCESS_TOKEN": "test-api-token"}, clear=False)
    @patch("agent_iq.api.ingest_document", side_effect=TimeoutError("too slow"))
    def test_ingestion_timeout_returns_structured_504(self, _ingest_document):
        response = asyncio.run(self._post_file("valid.txt", b"text"))

        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()["code"], "ingestion_timeout")
        self.assertEqual(
            response.json()["request_id"], response.headers["X-Request-ID"]
        )

    @patch.dict(os.environ, {"API_ACCESS_TOKEN": "test-api-token"}, clear=False)
    @patch("agent_iq.api.ingest_document", side_effect=RuntimeError("private detail"))
    def test_unexpected_failure_returns_sanitized_500(self, _ingest_document):
        response = asyncio.run(self._post_file("valid.txt", b"text"))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "internal_error")
        self.assertNotIn("private detail", response.text)


if __name__ == "__main__":
    unittest.main()
