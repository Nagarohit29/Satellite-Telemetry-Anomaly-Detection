from pydantic import BaseModel
from typing import List, Optional

class PredictRequest(BaseModel):
    channel: str = "T-1"
    data: List[float]

class AnomalyPoint(BaseModel):
    index: int
    score: float
    anomaly: bool

class PredictResponse(BaseModel):
    channel: str
    scores: List[float]
    anomalies: List[AnomalyPoint]
    threshold: float
    anomaly_count: int
    total_windows: int
    device: str

class AlertResponse(BaseModel):
    id: str
    channel: str
    severity: str
    score: float
    report: str
    timestamp: str

class ChannelListResponse(BaseModel):
    channels: List[str]