# ==============================================================================
# Project ARGUS-INT - Resilience & Circuit Breakers (Tenacity)
# ==============================================================================

import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from neo4j.exceptions import ServiceUnavailable, SessionExpired

logger = logging.getLogger(__name__)

# Retry decorator for Neo4j connections
neo4j_retry = retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((ServiceUnavailable, SessionExpired, ConnectionError, TimeoutError)),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        f"[Resilience] Neo4j query failed. Retrying in {retry_state.next_action.sleep}s... "
        f"Attempt {retry_state.attempt_number}/4"
    )
)

@neo4j_retry
def execute_neo4j_query_with_retry(driver, cypher_query: str, params: dict = None):
    """
    Executes a Cypher query on Neo4j with automatic retries and exponential backoff.
    """
    props = params or {}
    with driver.session() as session:
        result = session.run(cypher_query, **props)
        # Consume the result to force database roundtrip while within retry block
        return list(result)
