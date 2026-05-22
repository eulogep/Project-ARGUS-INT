# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Milvus Vision Bootstrap : Création des collections optimisées Phase 5b
scripts/milvus_vision_bootstrap.py

Collections créées :
  - phynx_face_vectors (512d COSINE HNSW M=32) — InsightFace ArcFace
  - argus_clip_vectors (512d COSINE HNSW M=32) — OpenCLIP ViT-B/32
  - argus_agent_memory (768d COSINE HNSW M=32) — Mémoire LTM agents

Usage :
  python scripts/milvus_vision_bootstrap.py [--benchmark]
"""
from __future__ import annotations

import argparse
import random
import time
from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)


MILVUS_HOST = "localhost"
MILVUS_PORT = 19530
HNSW_M = 32
HNSW_EF_CONSTRUCTION = 400
SEARCH_EF = 128

COLLECTIONS_SPEC: list[dict[str, Any]] = [
    {
        "name": "phynx_face_vectors",
        "description": "InsightFace ArcFace embeddings — 512d facial recognition",
        "dim": 512,
        "fields": [
            FieldSchema("id",               DataType.INT64,   is_primary=True, auto_id=True),
            FieldSchema("entity_uid",       DataType.VARCHAR, max_length=200),
            FieldSchema("image_hash",       DataType.VARCHAR, max_length=64),
            FieldSchema("source_url",       DataType.VARCHAR, max_length=500),
            FieldSchema("platform",         DataType.VARCHAR, max_length=100),
            FieldSchema("investigation_id", DataType.VARCHAR, max_length=100),
            FieldSchema("vector",           DataType.FLOAT_VECTOR, dim=512),
        ],
    },
    {
        "name": "argus_clip_vectors",
        "description": "OpenCLIP ViT-B/32 image embeddings — semantic search",
        "dim": 512,
        "fields": [
            FieldSchema("id",               DataType.INT64,   is_primary=True, auto_id=True),
            FieldSchema("image_hash",       DataType.VARCHAR, max_length=64),
            FieldSchema("source_url",       DataType.VARCHAR, max_length=500),
            FieldSchema("investigation_id", DataType.VARCHAR, max_length=100),
            FieldSchema("vector",           DataType.FLOAT_VECTOR, dim=512),
        ],
    },
    {
        "name": "argus_agent_memory",
        "description": "Agent long-term semantic memory — sentence-transformers 768d",
        "dim": 768,
        "fields": [
            FieldSchema("id",               DataType.INT64,   is_primary=True, auto_id=True),
            FieldSchema("agent_id",         DataType.VARCHAR, max_length=100),
            FieldSchema("investigation_id", DataType.VARCHAR, max_length=100),
            FieldSchema("observation_type", DataType.VARCHAR, max_length=50),
            FieldSchema("content_hash",     DataType.VARCHAR, max_length=64),
            FieldSchema("content_snippet",  DataType.VARCHAR, max_length=1000),
            FieldSchema("vector",           DataType.FLOAT_VECTOR, dim=768),
        ],
    },
]

HNSW_INDEX = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {"M": HNSW_M, "efConstruction": HNSW_EF_CONSTRUCTION},
}


def create_collection(spec: dict[str, Any]) -> Collection:
    name = spec["name"]
    if utility.has_collection(name):
        print(f"  [SKIP] {name} — déjà existant")
        return Collection(name)

    schema = CollectionSchema(spec["fields"], description=spec["description"])
    col = Collection(name, schema)
    col.create_index("vector", HNSW_INDEX)
    col.load()
    print(f"  [OK]   {name} ({spec['dim']}d HNSW M={HNSW_M})")
    return col


def benchmark_collection(col: Collection, dim: int, n_queries: int = 1000) -> dict[str, float]:
    """Benchmark latence p50/p99 sur N requêtes aléatoires."""
    vectors = [[random.gauss(0, 1) for _ in range(dim)] for _ in range(n_queries)]
    latencies: list[float] = []
    for vec in vectors:
        norm = (sum(v**2 for v in vec) ** 0.5)
        normed = [v / norm for v in vec]
        t0 = time.perf_counter()
        col.search(
            data=[normed],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"ef": SEARCH_EF}},
            limit=10,
        )
        latencies.append((time.perf_counter() - t0) * 1000)
    latencies.sort()
    p50 = latencies[int(n_queries * 0.50)]
    p99 = latencies[int(n_queries * 0.99)]
    return {"p50_ms": round(p50, 2), "p99_ms": round(p99, 2)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Milvus Vision Collections Bootstrap")
    parser.add_argument("--host",      default=MILVUS_HOST)
    parser.add_argument("--port",      default=MILVUS_PORT, type=int)
    parser.add_argument("--benchmark", action="store_true", help="Lancer le benchmark de latence")
    args = parser.parse_args()

    print(f"\n🔌 Connexion à Milvus {args.host}:{args.port}...")
    connections.connect("default", host=args.host, port=args.port)
    print("✓ Connecté\n")

    print("📦 Création des collections Phase 5b...")
    created_collections = []
    for spec in COLLECTIONS_SPEC:
        col = create_collection(spec)
        created_collections.append((col, spec["dim"]))

    if args.benchmark:
        print(f"\n⚡ Benchmark ({1000} requêtes par collection)...")
        for col, dim in created_collections:
            # Ne bencher que les collections avec au moins 1 entité
            stats = col.num_entities
            if stats == 0:
                print(f"  [SKIP] {col.name} — vide (0 vecteurs)")
                continue
            metrics = benchmark_collection(col, dim)
            print(f"  {col.name}: p50={metrics['p50_ms']}ms | p99={metrics['p99_ms']}ms")

    print("\n✅ Bootstrap Phase 5b terminé.")


if __name__ == "__main__":
    main()
