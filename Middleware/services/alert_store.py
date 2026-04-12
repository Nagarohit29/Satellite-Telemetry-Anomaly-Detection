import uuid
from datetime import datetime
from typing import List
from schemas.models import AlertResponse

_alerts: List[dict] = []

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
    if len(_alerts) > 100:
        _alerts.pop(0)
    return AlertResponse(**alert)

def get_all_alerts() -> List[AlertResponse]:
    return [AlertResponse(**a) for a in reversed(_alerts)]

def clear_alerts():
    _alerts.clear()
    return {"message": "All alerts cleared"}