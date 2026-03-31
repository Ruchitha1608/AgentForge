"""
memory.py — Redis-backed cache for agent results.
Degrades gracefully: if Redis is unavailable, all cache operations
are no-ops and the system continues without caching.
"""

import hashlib
import logging
import redis as redis_lib
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Client setup ──────────────────────────────────────────────────────────────

_client: redis_lib.Redis | None = None
_redis_available = False


def _init_redis() -> None:
    global _client, _redis_available
    try:
        _client = redis_lib.from_url(
            settings.redis_url,
            socket_timeout=1,
            socket_connect_timeout=1,
            decode_responses=True,
        )
        _client.ping()
        _redis_available = True
        logger.info("Redis connected at %s", settings.redis_url)
    except Exception as exc:
        _redis_available = False
        logger.warning("Redis unavailable (%s) — running without cache", exc)


_init_redis()


# ── Public API ────────────────────────────────────────────────────────────────

def is_available() -> bool:
    return _redis_available


def cache_key(text: str) -> str:
    """Deterministic cache key: SHA-256 of the subtask text."""
    return "agentforge:" + hashlib.sha256(text.encode()).hexdigest()


def get_cached(key: str) -> str | None:
    """Return cached value or None if missing / Redis unavailable."""
    if not _redis_available or _client is None:
        return None
    try:
        return _client.get(key)
    except Exception as exc:
        logger.warning("Redis GET failed: %s", exc)
        return None


def set_cached(key: str, value: str, ttl: int = 3600) -> None:
    """Store value in Redis with a TTL (default 1 hour)."""
    if not _redis_available or _client is None:
        return
    try:
        _client.setex(key, ttl, value)
    except Exception as exc:
        logger.warning("Redis SET failed: %s", exc)
