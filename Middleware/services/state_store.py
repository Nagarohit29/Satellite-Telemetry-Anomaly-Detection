"""Abstracted state store for rate limiter and alerts — supports in-memory (default) and Redis."""
import json
import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "")


def _get_redis():
    """Lazy Redis connection. Returns None if unavailable."""
    if not REDIS_URL:
        return None
    try:
        import redis
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


_redis = None


def _r():
    global _redis
    if _redis is None:
        _redis = _get_redis()
    return _redis


# ── Rate Limiter State ──

class RateLimiterStore:
    """Token bucket rate limiter with pluggable backend."""

    def __init__(self, prefix: str = "rl"):
        self._prefix = prefix
        self._local: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_refill)
        self._max_buckets = 10_000

    def _key(self, ip: str) -> str:
        return f"{self._prefix}:{ip}"

    def check(self, ip: str, rate: int, window: int) -> bool:
        """Returns True if request is allowed."""
        r = _r()
        if r is not None:
            return self._check_redis(r, ip, rate, window)
        return self._check_local(ip, rate, window)

    def _check_local(self, ip: str, rate: int, window: int) -> bool:
        now = time.monotonic()
        key = self._key(ip)
        tokens, last = self._local.get(key, (float(rate), now))
        elapsed = now - last
        tokens = min(float(rate), tokens + elapsed * (rate / window))
        if tokens >= 1.0:
            self._local[key] = (tokens - 1.0, now)
            self._evict_if_needed()
            return True
        self._local[key] = (tokens, now)
        return False

    def _check_redis(self, r, ip: str, rate: int, window: int) -> bool:
        key = self._key(ip)
        try:
            pipe = r.pipeline()
            pipe.get(key)
            pipe.ttl(key)
            tokens_str, ttl = pipe.execute()
            tokens = float(tokens_str) if tokens_str else float(rate)
            if tokens >= 1.0:
                pipe.set(key, str(tokens - 1.0), ex=window)
                pipe.execute()
                return True
            return False
        except Exception:
            return self._check_local(ip, rate, window)

    def _evict_if_needed(self):
        if len(self._local) > self._max_buckets:
            cutoff = int(self._max_buckets * 0.8)
            sorted_keys = sorted(self._local, key=lambda k: self._local[k][1])
            for k in sorted_keys[: len(self._local) - cutoff]:
                del self._local[k]


# ── Alert State ──

class AlertStore:
    """Persistent alert store with Redis or file fallback."""

    def __init__(self, file_path: Optional[str] = None, max_alerts: int = 100):
        self._max = max_alerts
        self._file = file_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), '..', 'config', 'alerts.json'
        )
        self._alerts: list[dict] = []
        self._load()

    def _load(self):
        r = _r()
        if r is not None:
            try:
                data = r.get("alerts:store")
                if data:
                    self._alerts = json.loads(data)
                    return
            except Exception:
                pass
        try:
            if os.path.exists(self._file):
                with open(self._file, 'r') as f:
                    self._alerts = json.load(f)
        except Exception:
            self._alerts = []

    def _persist(self):
        data = self._alerts[-self._max:]
        r = _r()
        if r is not None:
            try:
                r.set("alerts:store", json.dumps(data))
                return
            except Exception:
                pass
        try:
            os.makedirs(os.path.dirname(self._file), exist_ok=True)
            with open(self._file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def add(self, alert: dict):
        self._alerts.append(alert)
        if len(self._alerts) > self._max:
            self._alerts.pop(0)
        self._persist()

    def get_all(self) -> list[dict]:
        return list(reversed(self._alerts))

    def clear(self):
        self._alerts.clear()
        self._persist()
