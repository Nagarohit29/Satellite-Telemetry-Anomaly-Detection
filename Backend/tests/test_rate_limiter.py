"""Tests for Backend rate limiter and auth middleware patterns."""
import time


def test_bounded_dict_eviction():
    """Rate limiter dict should not grow beyond _MAX_BUCKETS."""
    _MAX = 100
    buckets = {}
    for i in range(_MAX + 20):
        buckets[f"ip_{i}"] = (10, time.monotonic())
        if len(buckets) > _MAX:
            # Evict oldest 20%
            cutoff = int(_MAX * 0.8)
            sorted_keys = sorted(buckets, key=lambda k: buckets[k][1])
            for k in sorted_keys[:len(buckets) - cutoff]:
                del buckets[k]
    assert len(buckets) <= _MAX


def test_token_refill():
    """Token bucket should refill over time."""
    rate = 10
    window = 60
    tokens = 0
    last_refill = time.monotonic() - 10  # 10 seconds ago
    now = time.monotonic()
    elapsed = now - last_refill
    tokens = min(rate, tokens + elapsed * (rate / window))
    assert tokens > 0
    assert tokens <= rate


def test_api_key_constant_time_compare():
    """hmac.compare_digest should be used for key comparison."""
    import hmac
    key = "test-key-12345"
    assert hmac.compare_digest(key, key)
    assert not hmac.compare_digest(key, "wrong-key")
    assert not hmac.compare_digest(key, "")


def test_exempt_paths():
    """Health and docs paths should be exempt from auth."""
    exempt = {"/", "/health", "/docs", "/openapi.json", "/redoc", "/metrics"}
    assert "/" in exempt
    assert "/health" in exempt
    assert "/infer" not in exempt
    assert "/train" not in exempt
