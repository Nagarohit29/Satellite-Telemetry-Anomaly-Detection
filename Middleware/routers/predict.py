from fastapi import APIRouter, HTTPException
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.models import PredictRequest, PredictResponse, AnomalyPoint
from services.backend_client import call_infer
from services.alert_store import add_alert
from services.llm_service import generate_incident_report, get_severity

router = APIRouter()

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

        if anomaly_count > 0:
            report = generate_incident_report(
                channel=req.channel,
                score=max_score,
                anomaly_count=anomaly_count,
                total_windows=total_windows,
                threshold=threshold,
                device=device
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
            device=device
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))