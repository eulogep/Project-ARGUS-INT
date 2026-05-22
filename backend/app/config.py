# ==============================================================================
# Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
# ==============================================================================
# Copyright (C) 2026 eulogep
#
# This file is part of Project ARGUS-INT.
#
# Project ARGUS-INT is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Project ARGUS-INT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Project ARGUS-INT. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================

"""
PHYNX — Configuration centralisée
backend/app/config.py
"""
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme_secret_key_32chars"
    ENCRYPTION_KEY: str = "changeme_aes_key_32bytes!!!"  # 32 bytes AES-256

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "phynx"
    POSTGRES_USER: str = "phynx"
    POSTGRES_PASSWORD: str = "changeme"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "changeme"

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # ─── Inference Backend ───────────────────────────────────────
    # Valeurs : "vllm" (production GPU) | "ollama" (dev/fallback CPU)
    INFERENCE_BACKEND: str = "ollama"

    # Ollama (dev / fallback CPU)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # ─── vLLM (production GPU) ───────────────────────────────────
    VLLM_HEAVY_URL: str = "http://vllm-heavy:8100/v1"
    VLLM_HEAVY_MODEL: str = "argus-heavy"       # Llama-3-70B-AWQ
    VLLM_LIGHT_URL: str = "http://vllm-light:8101/v1"
    VLLM_LIGHT_MODEL: str = "argus-light"       # Llama-3-8B-AWQ
    VLLM_VISION_URL: str = "http://vllm-vision:8102/v1"
    VLLM_VISION_MODEL: str = "argus-vision"     # LLaVA-1.6-Mistral-7B

    # ─── GPU Router ──────────────────────────────────────────────
    # Seuil tokens/requête au-dessus duquel on envoie sur le modèle heavy
    GPU_HEAVY_TOKEN_THRESHOLD: int = 512
    MAX_CONCURRENT_LLM_REQUESTS: int = 16
    LLM_REQUEST_TIMEOUT_S: int = 120

    # ─── HuggingFace Local Cache (air-gapped) ────────────────────
    HF_HOME: str = "/models/classifiers"
    HF_HUB_OFFLINE: bool = True
    TRANSFORMERS_OFFLINE: bool = True

    # ─── AI Firewall (DeBERTa) ───────────────────────────────────
    AI_FIREWALL_ENABLED: bool = True
    AI_FIREWALL_MODEL_PATH: str = "/models/classifiers/deberta-prompt-injection"
    # Seuil d'injection (0-100) au-dessus duquel on bloque
    AI_FIREWALL_THRESHOLD: int = 70
    # Seuil Layer 1 (regex rapide) — indépendant du modèle
    AI_FIREWALL_REGEX_THRESHOLD: int = 3

    # ─── Milvus Sparse / Hybrid Search ──────────────────────────
    MILVUS_SPARSE_ENABLED: bool = True
    MILVUS_HNSW_M: int = 32
    MILVUS_HNSW_EF_CONSTRUCTION: int = 400
    MILVUS_SEARCH_EF: int = 128

    # ─── Cognitive Swarm ─────────────────────────────────────────
    SWARM_MAX_AGENTS: int = 8
    # TTL (en secondes) de la mémoire court-terme agent dans Redis
    AGENT_MEMORY_TTL_S: int = 86400   # 24h
    # Timeout d'un état de la State Machine (en secondes)
    AGENT_STATE_TIMEOUT_S: int = 1800  # 30 min
    # Taille du contexte injecté depuis la mémoire long-terme
    AGENT_MEMORY_TOP_K: int = 10

    # Tor
    TOR_PROXY: str = "socks5h://localhost:9050"
    TOR_CONTROL_PASSWORD: str = "changeme"

    # Proxies
    PROXY_LIST: Optional[List[dict]] = []

    # ArchiveBox
    ARCHIVEBOX_URL: str = "http://localhost:8080"

    # ─── FinOps — Monero ───────────────────────────────────────
    MONERO_RPC_URL: str = "http://monero-wallet-rpc:18082/json_rpc"
    MONERO_RPC_USER: str = "phynx"
    MONERO_RPC_PASSWORD: str = "changeme"
    XMR_CONFIRMATION_WAIT_SECONDS: int = 120

    # ─── FinOps — Lightning Network ────────────────────────────
    LND_REST_URL: str = "https://lnd:8080"
    LND_MACAROON_HEX: str = ""

    # ─── FinOps — Bitcoin Core ────────────────────────────────
    BITCOIN_RPC_USER: str = "phynx"
    BITCOIN_RPC_PASSWORD: str = "changeme"

    # ─── FinOps — Providers payants ────────────────────────────
    DEHASHED_LN_INVOICE: str = ""
    PROXY_PROVIDER_API: str = ""
    PROXY_PROVIDER_LN_INVOICE: str = ""
    INTELX_XMR_ADDRESS: str = ""

    # ─── Crypto Tracing ─────────────────────────────────────────
    ETHERSCAN_API_KEY: str = ""

    # ─── Vector DB — Milvus ────────────────────────────────────
    MILVUS_HOST: str = "milvus-standalone"
    MILVUS_PORT: int = 19530

    # ─── IPFS — Kubo/Local Node ───────────────────────────────
    IPFS_API_URL: str = "http://ipfs:5001/api/v0"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
