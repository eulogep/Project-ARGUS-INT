# ==============================================================================
# Project ARGUS-INT - PostgreSQL Database Orchestration
# ==============================================================================

import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
import asyncpg
from app.config import settings

logger = logging.getLogger(__name__)

# Global asyncpg connection pool
_pool = None

async def init_db():
    """Initializes connection pool and creates PostgreSQL database schema if missing."""
    global _pool
    if not _pool:
        try:
            _pool = await asyncpg.create_pool(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                min_size=5,
                max_size=30
            )
            logger.info("[Database] Connection pool created successfully.")
            
            # Execute schemas
            async with _pool.acquire() as conn:
                # Enable UUID extension
                await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
                
                # Create investigations table
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS investigations (
                    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    target              TEXT NOT NULL,
                    target_type         VARCHAR(50) NOT NULL,
                    depth               INTEGER DEFAULT 1,
                    status              VARCHAR(20) DEFAULT 'PENDING',
                    result_count        INTEGER DEFAULT 0,
                    pivot_suggestions   TEXT,
                    llm_summary         TEXT,
                    created_at          TIMESTAMPTZ DEFAULT NOW(),
                    completed_at        TIMESTAMPTZ,
                    created_by          UUID,
                    CONSTRAINT status_check CHECK (
                        status IN ('PENDING', 'COLLECTING', 'CORRELATING', 'COMPLETED', 'DONE', 'FAILED')
                    )
                );
                """)
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_investigations_status ON investigations(status);")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_investigations_created_at ON investigations(created_at DESC);")
                
                # Create raw_results table
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_results (
                    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    investigation_id    UUID REFERENCES investigations(id) ON DELETE CASCADE,
                    module              VARCHAR(100) NOT NULL,
                    source              VARCHAR(200),
                    data                JSONB NOT NULL,
                    confidence          FLOAT DEFAULT 0.5,
                    sha256_hash         CHAR(64),
                    created_at          TIMESTAMPTZ DEFAULT NOW()
                );
                """)
                
                # Create archives table
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS archives (
                    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    investigation_id    UUID REFERENCES investigations(id) ON DELETE SET NULL,
                    original_url        TEXT NOT NULL,
                    archive_url         TEXT,
                    sha256_hash         CHAR(64) NOT NULL,
                    file_size_bytes     BIGINT,
                    captured_at         TIMESTAMPTZ DEFAULT NOW(),
                    diff_from_previous  TEXT
                );
                """)
                
                # Create reports table
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    investigation_id    UUID REFERENCES investigations(id) ON DELETE CASCADE,
                    format              VARCHAR(20) DEFAULT 'JSON',
                    file_path           TEXT,
                    sha256_hash         CHAR(64),
                    generated_at        TIMESTAMPTZ DEFAULT NOW()
                );
                """)
                logger.info("[Database] Core database schema verified.")
        except Exception as e:
            logger.critical(f"[Database] Initialization failed: {e}", exc_info=True)
            raise e

@asynccontextmanager
async def get_db_session():
    """Asynchronous context manager yielding a database connection from the pool."""
    global _pool
    if not _pool:
        await init_db()
    
    conn = await _pool.acquire()
    try:
        yield conn
    finally:
        await _pool.release(conn)

class SyncConnectionWrapper:
    """Wrapper that exposes asyncpg execute/fetch methods synchronously using an event loop."""
    def __init__(self, conn, loop):
        self.conn = conn
        self.loop = loop

    def execute(self, query, *args):
        return self.loop.run_until_complete(self.conn.execute(query, *args))

    def fetch(self, query, *args):
        return self.loop.run_until_complete(self.conn.fetch(query, *args))

    def fetchrow(self, query, *args):
        return self.loop.run_until_complete(self.conn.fetchrow(query, *args))

@contextmanager
def get_db_session_sync():
    """Synchronous context manager yielding a wrapped connection for Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Establish connection pool if needed
    if not _pool:
        loop.run_until_complete(init_db())
        
    conn = loop.run_until_complete(_pool.acquire())
    try:
        yield SyncConnectionWrapper(conn, loop)
    finally:
        loop.run_until_complete(_pool.release(conn))
        loop.close()
