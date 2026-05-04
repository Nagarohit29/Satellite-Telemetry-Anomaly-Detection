from fastapi import APIRouter, HTTPException
import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.models import PredictRequest, PredictResponse, AnomalyPoint
from services.backend_client import call_infer
from services.alert_store import add_alert
from services.llm_service import generate_incident_report, get_severity

import traceback

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Track which (channel, anomaly_count) combos already have a report ──
# This prevents the system from firing an LLM call every 5-second poll cycle.
_reported_anomalies: dict[str, int] = {}


def _build_static_report(
    channel: str,
    severity: str,
    score: float,
    threshold: float,
    anomaly_count: int,
    total_windows: int,
) -> str:
    ratio = round((anomaly_count / total_windows) * 100, 2) if total_windows > 0 else 0
    return (
        f"Incident Summary: Channel {channel} | Severity: {severity}\n"
        f"Score {score:.4f} exceeded threshold {threshold}. "
        f"{anomaly_count}/{total_windows} windows anomalous ({ratio}%). "
        f"Review telemetry and use the AI assistant on demand for deeper analysis."
    )


@router.post("/predict")
async def predict(req: PredictRequest):
    try:
        result = await call_infer(req.channel, req.data)

        scores = result.get("scores", [])
        max_score = max(scores) if scores else 0.0
        anomaly_count = result.get("anomaly_count", 0)
        total_windows = result.get("total_windows", 1)
        threshold = result.get("threshold", 0.5)
        device = result.get("device", "cpu")

        severity = get_severity(max_score, anomaly_count, total_windows)

        # Only generate a report if:
        #  1. There are actual anomalies
        #  2. This specific anomaly count hasn't been reported for this channel yet
        #     (prevents spamming the LLM on every poll cycle with the same data)
        if anomaly_count > 0:
            prev_count = _reported_anomalies.get(req.channel)
            if prev_count != anomaly_count:
                _reported_anomalies[req.channel] = anomaly_count
                if req.model_preference:
                    report = generate_incident_report(
                        channel=req.channel,
                        score=max_score,
                        anomaly_count=anomaly_count,
                        total_windows=total_windows,
                        threshold=threshold,
                        device=device,
                        model_preference=req.model_preference
                    )
                else:
                    report = _build_static_report(
                        channel=req.channel,
                        severity=severity,
                        score=max_score,
                        threshold=threshold,
                        anomaly_count=anomaly_count,
                        total_windows=total_windows,
                    )
                add_alert(
                    channel=req.channel,
                    score=max_score,
                    report=report,
                    severity=severity
                )

        anomalies = [
            AnomalyPoint(
                index=a["index"],
                score=a["score"],
                anomaly=a["anomaly"]
            )
            for a in result.get("anomalies", [])
        ]

        return PredictResponse(
            channel=result.get("channel", req.channel),
            scores=scores,
            anomalies=anomalies,
            threshold=threshold,
            anomaly_count=anomaly_count,
            total_windows=total_windows,
            device=device,
            inference_engine=result.get("inference_engine")
        )

    except Exception as e:
        logger.error(f"Predict endpoint error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
