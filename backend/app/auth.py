# ==============================================================================
# Project ARGUS-INT - Authentication Helper Stub
# ==============================================================================

from typing import Optional

async def verify_token_optional(token: Optional[str]) -> Optional[dict]:
    """
    Decodes and verifies a JWT token if supplied.
    Returns None if token is invalid or if in No-Auth mode.
    """
    return None
