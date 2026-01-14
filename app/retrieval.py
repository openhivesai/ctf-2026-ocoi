# public/app/src/retrieval.py
import os
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "ctf_sobriete_docs")
TOP_K = int(os.getenv("TOP_K", "5"))

_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
_client = QdrantClient(url=QDRANT_URL)


def retrieve(query: str):
    embedding = _model.encode(query).tolist()

    hits = _client.search(
        collection_name=COLLECTION,
        query_vector=embedding,
        limit=TOP_K,
        with_payload=True,
    )

    results = []
    for hit in hits:
        payload = hit.payload or {}
        results.append(
            {
                "doc_id": payload.get("doc_id"),
                "text": payload.get("text"),
                "score": hit.score,
            }
        )

    return results


def retrieve_all():
    results = []
    offset = None

    while True:
        points, offset = _client.scroll(
            collection_name=COLLECTION,
            limit=256,
            with_payload=True,
            offset=offset,
        )
        if not points:
            break

        for point in points:
            payload = point.payload or {}
            results.append(
                {
                    "doc_id": payload.get("doc_id"),
                    "text": payload.get("text"),
                    "score": 0.0,
                }
            )

        if offset is None:
            break

    return results
