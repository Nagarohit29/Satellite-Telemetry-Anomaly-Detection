import json
import os
import uuid
from datetime import datetime
from typing import List
from schemas.models import AlertResponse

_alerts: List[dict] = []
_ALERTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'config', 'alerts.json')
_MAX_ALERTS = 100


def _persist():
    """Write alerts to disk for durability across restarts."""
    try:
        os.makedirs(os.path.dirname(_ALERTS_FILE), exist_ok=True)
        with open(_ALERTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(_alerts[-_MAX_ALERTS:], f)
    except Exception:
        pass  # Best-effort persistence


def _load():
    """Load alerts from disk on startup."""
    global _alerts
    try:
        if os.path.exists(_ALERTS_FILE):
            with open(_ALERTS_FILE, 'r', encoding='utf-8') as f:
                _alerts = json.load(f)
    except Exception:
        _alerts = []


# Load on import
_load()


def add_alert(
    channel: str,
    score: float,
    report: str,
    severity: str
) -> AlertResponse:
    alert = {
        "id": str(uuid.uuid4()),
        "channel": channel,
        "severity": severity,
        "score": round(score, 6),
        "report": report,
        "timestamp": datetime.utcnow().isoformat()
    }
    _alerts.append(alert)
    if len(_alerts) > _MAX_ALERTS:
        _alerts.pop(0)
    _persist()
    return AlertResponse(**alert)


def get_all_alerts() -> List[AlertResponse]:
    return [AlertResponse(**a) for a in reversed(_alerts)]


def clear_alerts():
    _alerts.clear()
    _persist()
    return {"message": "All alerts cleared"}
