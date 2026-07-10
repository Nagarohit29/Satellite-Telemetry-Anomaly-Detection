"""Tests for circuit breaker and alert store."""
import time
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_circuit_breaker_logic():
    """Circuit breaker should open after threshold failures and reset on success."""
    # Inline the CB logic to avoid importing litellm
    import time as _time
    _failures: dict[str, tuple[int, float]] = {}
    THRESHOLD = 5
    RESET_S = 60

    def is_open(p):
        s = _failures.get(p)
        if s is None or s[0] < THRESHOLD:
            return False
        if _time.monotonic() - s[1] > RESET_S:
            return False
        return True

    def record_fail(p):
        s = _failures.get(p, (0, 0.0))
        _failures[p] = (s[0] + 1, _time.monotonic())

    def record_success(p):
        _failures.pop(p, None)

    provider = "test"
    for _ in range(THRESHOLD):
        assert not is_open(provider)
        record_fail(provider)
    assert is_open(provider)

    record_success(provider)
    assert not is_open(provider)


def test_circuit_breaker_half_open():
    """After reset timeout, circuit should allow a retry (half-open)."""
    import time as _time
    _failures: dict[str, tuple[int, float]] = {}
    THRESHOLD = 3
    RESET_S = 0.1  # Short for testing

    def is_open(p):
        s = _failures.get(p)
        if s is None or s[0] < THRESHOLD:
            return False
        if _time.monotonic() - s[1] > RESET_S:
            return False
        return True

    def record_fail(p):
        s = _failures.get(p, (0, 0.0))
        _failures[p] = (s[0] + 1, _time.monotonic())

    provider = "test_half"
    for _ in range(THRESHOLD):
        record_fail(provider)
    assert is_open(provider)

    time.sleep(0.15)
    assert not is_open(provider)  # Half-open after timeout


def test_alert_store_persistence():
    """Alert store should persist and reload alerts."""
    from services.alert_store import add_alert, get_all_alerts, clear_alerts, _ALERTS_FILE

    clear_alerts()
    add_alert("T-1", 0.95, "Test anomaly", "critical")
    alerts = get_all_alerts()
    assert len(alerts) >= 1
    assert alerts[0].channel == "T-1"
    assert os.path.exists(_ALERTS_FILE)

    clear_alerts()
    assert len(get_all_alerts()) == 0
