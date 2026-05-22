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

    # Ollama (LLM local)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

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
