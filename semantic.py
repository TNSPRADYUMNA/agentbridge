"""Dense retrieval over the policy corpus using local embeddings and Chroma."""
from functools import lru_cache
from hashlib import sha256

import chromadb
from sentence_transformers import SentenceTransformer

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


@lru_cache(maxsize=1)
def index(policies, model_name):
    encoder = SentenceTransformer(model_name, device="cpu", revision=REVISION if model_name == MODEL else None)
    client = chromadb.EphemeralClient(chromadb.config.Settings(anonymized_telemetry=False))
    name = "policies-" + sha256(repr((policies, model_name)).encode()).hexdigest()[:24]
    collection = client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
    ids, texts = zip(*policies)
    vectors = encoder.encode(list(texts), normalize_embeddings=True).tolist()
    collection.upsert(ids=list(ids), documents=list(texts), embeddings=vectors)
    return encoder, collection


def retrieve(query, policies, model_name=MODEL, limit=3, minimum_similarity=0.25):
    encoder, collection = index(tuple(policies.items()), model_name)
    vector = encoder.encode([query], normalize_embeddings=True).tolist()
    result = collection.query(query_embeddings=vector, n_results=min(limit, len(policies)))
    return [{"source": key, "text": text, "score": float(1 - distance)}
            for key, text, distance in zip(result["ids"][0], result["documents"][0], result["distances"][0])
            if 1 - distance >= minimum_similarity]
