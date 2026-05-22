# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — MemoryManager : Redis (court terme) + Milvus (long terme) + PostgreSQL (épisodique)
backend/app/cognitive/memory.py
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = structlog.get_logger(__name__)


# ==============================================================================
#  SHORT TERM MEMORY — Redis
# ==============================================================================

class ShortTermMemory:
    """
    Mémoire court terme d'un agent via Redis.
    Clé : argus:agent:{agent_id}:stm:{key}
    TTL global configurable (AGENT_MEMORY_TTL_S).
    """

    def __init__(self, agent_id: str, redis_client: Any) -> None:
        self.agent_id = agent_id
        self._redis = redis_client
        self._prefix = f"argus:agent:{agent_id}:stm"

    def _key(self, name: str) -> str:
        return f"{self._prefix}:{name}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.1))
    async def set(self, name: str, value: Any, ttl: Optional[int] = None) -> None:
        payload = json.dumps(value, default=str)
        await self._redis.set(self._key(name), payload, ex=ttl or settings.AGENT_MEMORY_TTL_S)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.1))
    async def get(self, name: str, default: Any = None) -> Any:
        raw = await self._redis.get(self._key(name))
        if raw:
            return json.loads(raw)
        return default

    async def delete(self, name: str) -> None:
        await self._redis.delete(self._key(name))

    async def append_observation(self, observation: dict[str, Any]) -> None:
        """Ajoute une observation à la liste des 50 dernières."""
        key = self._key("observations")
        observation["ts"] = time.time()
        await self._redis.lpush(key, json.dumps(observation, default=str))
        await self._redis.ltrim(key, 0, 49)          # Garde seulement les 50 dernières
        await self._redis.expire(key, settings.AGENT_MEMORY_TTL_S)

    async def get_recent_observations(self, limit: int = 20) -> list[dict[str, Any]]:
        key = self._key("observations")
        items = await self._redis.lrange(key, 0, limit - 1)
        return [json.loads(item) for item in items]

    async def flush(self) -> None:
        """Vide toute la mémoire court terme de cet agent."""
        pattern = f"{self._prefix}:*"
        keys = await self._redis.keys(pattern)
        if keys:
            await self._redis.delete(*keys)


# ==============================================================================
#  LONG TERM MEMORY — Milvus
# ==============================================================================

class LongTermMemory:
    """
    Mémoire sémantique long terme via Milvus.
    Collection : argus_agent_memory (768d, partitionnée par investigation_id)
    """

    COLLECTION_NAME = "argus_agent_memory"
    VECTOR_DIM = 768

    def __init__(self, investigation_id: str) -> None:
        self.investigation_id = investigation_id
        self._connected = False

    def _connect(self) -> bool:
        try:
            from pymilvus import connections, utility, Collection, CollectionSchema, FieldSchema, DataType
            connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
            self._connected = True
            self._ensure_collection()
            return True
        except Exception as exc:
            logger.warning("ltm.milvus_connect_failed", error=str(exc))
            return False

    def _ensure_collection(self) -> None:
        from pymilvus import utility, Collection, CollectionSchema, FieldSchema, DataType
        if utility.has_collection(self.COLLECTION_NAME):
            return
        fields = [
            FieldSchema("id",               DataType.INT64,        is_primary=True, auto_id=True),
            FieldSchema("agent_id",         DataType.VARCHAR,      max_length=100),
            FieldSchema("investigation_id", DataType.VARCHAR,      max_length=100),
            FieldSchema("observation_type", DataType.VARCHAR,      max_length=50),
            FieldSchema("content_hash",     DataType.VARCHAR,      max_length=64),
            FieldSchema("content_snippet",  DataType.VARCHAR,      max_length=1000),
            FieldSchema("vector",           DataType.FLOAT_VECTOR, dim=self.VECTOR_DIM),
        ]
        schema = CollectionSchema(fields, description="Agent long-term semantic memory")
        col = Collection(self.COLLECTION_NAME, schema)
        col.create_index("vector", {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {
                "M": settings.MILVUS_HNSW_M,
                "efConstruction": settings.MILVUS_HNSW_EF_CONSTRUCTION,
            },
        })
        col.load()
        logger.info("ltm.collection_created", name=self.COLLECTION_NAME)

    def _embed(self, text: str) -> Optional[list[float]]:
        """Embedding local via sentence-transformers (singleton)."""
        try:
            from sentence_transformers import SentenceTransformer
            import os
            # Mode offline : modèle lu depuis le cache local
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
            vec = model.encode(text[:512], normalize_embeddings=True)
            return vec.tolist()
        except Exception as exc:
            logger.warning("ltm.embed_failed", error=str(exc))
            return None

    async def store_observation(
        self,
        agent_id: str,
        content: str,
        observation_type: str = "general",
    ) -> bool:
        """Indexe une observation dans Milvus."""
        import asyncio
        import hashlib
        loop = asyncio.get_event_loop()

        if not self._connected:
            connected = await loop.run_in_executor(None, self._connect)
            if not connected:
                return False

        vector = await loop.run_in_executor(None, self._embed, content)
        if vector is None:
            return False

        content_hash = hashlib.sha256(content.encode()).hexdigest()
        try:
            from pymilvus import Collection
            col = Collection(self.COLLECTION_NAME)
            col.insert([{
                "agent_id":          agent_id,
                "investigation_id":  self.investigation_id,
                "observation_type":  observation_type,
                "content_hash":      content_hash,
                "content_snippet":   content[:900],
                "vector":            vector,
            }])
            col.flush()
            return True
        except Exception as exc:
            logger.error("ltm.store_failed", error=str(exc))
            return False

    async def search_similar(
        self,
        query: str,
        top_k: int = 10,
        min_similarity: float = 0.70,
    ) -> list[dict[str, Any]]:
        """Recherche sémantique dans la mémoire long terme (filtré par investigation)."""
        import asyncio
        loop = asyncio.get_event_loop()

        if not self._connected:
            connected = await loop.run_in_executor(None, self._connect)
            if not connected:
                return []

        vector = await loop.run_in_executor(None, self._embed, query)
        if vector is None:
            return []

        try:
            from pymilvus import Collection
            col = Collection(self.COLLECTION_NAME)
            results = col.search(
                data=[vector],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"ef": settings.MILVUS_SEARCH_EF}},
                limit=top_k,
                expr=f'investigation_id == "{self.investigation_id}"',
                output_fields=["agent_id", "observation_type", "content_snippet", "content_hash"],
            )
            matches = []
            for hits in results:
                for hit in hits:
                    if hit.score >= min_similarity:
                        matches.append({
                            "score":            round(hit.score, 4),
                            "agent_id":         hit.entity.get("agent_id"),
                            "observation_type": hit.entity.get("observation_type"),
                            "content":          hit.entity.get("content_snippet"),
                            "hash":             hit.entity.get("content_hash"),
                        })
            return matches
        except Exception as exc:
            logger.error("ltm.search_failed", error=str(exc))
            return []


# ==============================================================================
#  EPISODIC MEMORY — PostgreSQL
# ==============================================================================

class EpisodicMemory:
    """
    Journal épisodique structuré des actions et décisions de l'agent.
    Table : agent_memory (créée par la migration 003_ai_engine.sql)
    """

    def __init__(self, agent_id: str, investigation_id: str) -> None:
        self.agent_id = agent_id
        self.investigation_id = investigation_id

    async def record(
        self,
        action: str,
        state_from: str,
        state_to: str,
        payload: Optional[dict[str, Any]] = None,
        result: Optional[str] = None,
    ) -> None:
        """Enregistre une action/décision dans le journal épisodique."""
        try:
            from app.database import get_db_session
            async with get_db_session() as db:
                await db.execute(
                    """
                    INSERT INTO agent_memory
                        (id, agent_id, investigation_id, action, state_from, state_to, payload, result, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    str(uuid4()),
                    self.agent_id,
                    self.investigation_id,
                    action,
                    state_from,
                    state_to,
                    json.dumps(payload or {}),
                    result,
                    datetime.now(timezone.utc),
                )
        except Exception as exc:
            logger.error("episodic.record_failed", agent_id=self.agent_id, error=str(exc))

    async def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Récupère le journal des dernières actions de cet agent."""
        try:
            from app.database import get_db_session
            async with get_db_session() as db:
                rows = await db.fetch(
                    """
                    SELECT action, state_from, state_to, payload, result, created_at
                    FROM agent_memory
                    WHERE agent_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    self.agent_id, limit,
                )
                return [dict(r) for r in rows]
        except Exception as exc:
            logger.error("episodic.get_history_failed", error=str(exc))
            return []


# ==============================================================================
#  MEMORY MANAGER — Interface unifiée
# ==============================================================================

class MemoryManager:
    """
    Interface unifiée pour les 3 couches de mémoire d'un agent.

    Usage :
        mem = MemoryManager(agent_id="agt-001", investigation_id="inv-abc", redis=redis_client)
        await mem.stm.set("last_target", "user@example.com")
        await mem.ltm.store_observation(agent_id, "L'email existe sur Telegram")
        await mem.episodic.record("scrape_darkweb", "COLLECTING", "ANALYZING", result="found_3_hits")
        context = await mem.build_context_for_llm("Quels liens existent entre les pseudos ?")
    """

    def __init__(
        self,
        agent_id: str,
        investigation_id: str,
        redis_client: Any,
    ) -> None:
        self.agent_id = agent_id
        self.investigation_id = investigation_id
        self.stm = ShortTermMemory(agent_id, redis_client)
        self.ltm = LongTermMemory(investigation_id)
        self.episodic = EpisodicMemory(agent_id, investigation_id)

    async def build_context_for_llm(self, query: str) -> str:
        """
        Construit un bloc de contexte enrichi pour injection dans le prompt LLM.
        Combine : observations récentes (STM) + mémoire sémantique (LTM).
        Le texte est pré-sanitisé pour l'AI Firewall.
        """
        from app.services.input_sanitizer import sanitize

        parts: list[str] = []

        # 1. Observations récentes (STM)
        recent = await self.stm.get_recent_observations(limit=10)
        if recent:
            obs_text = "\n".join(
                f"- [{o.get('type', 'obs')}] {o.get('content', '')}"
                for o in recent
            )
            parts.append(f"## Observations récentes\n{sanitize(obs_text, source='stm')}")

        # 2. Mémoire sémantique (LTM) — top-K pertinent
        semantic_hits = await self.ltm.search_similar(
            query, top_k=settings.AGENT_MEMORY_TOP_K
        )
        if semantic_hits:
            sem_text = "\n".join(
                f"- [score={h['score']}] {h['content']}"
                for h in semantic_hits
            )
            parts.append(f"## Contexte d'investigation (mémoire long terme)\n{sanitize(sem_text, source='ltm')}")

        if not parts:
            return ""

        return "\n\n".join(parts)

    async def store_observation(
        self,
        content: str,
        observation_type: str = "general",
        persist_long_term: bool = True,
    ) -> None:
        """Stocke une observation en STM et optionnellement en LTM."""
        await self.stm.append_observation({
            "type": observation_type,
            "content": content[:500],
        })
        if persist_long_term:
            await self.ltm.store_observation(self.agent_id, content, observation_type)
