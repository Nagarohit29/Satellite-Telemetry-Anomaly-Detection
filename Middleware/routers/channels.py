from fastapi import APIRouter, HTTPException
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.backend_client import call_channels, call_health, call_train, call_telemetry

router = APIRouter()

@router.get("/channels")
async def get_channels():
    try:
        return await call_channels()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/telemetry/{channel}")
async def get_telemetry(channel: str, offset: int = 0, length: int = 200, step: int = 50):
    try:
        return await call_telemetry(channel=channel, offset=offset, length=length, step=step)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backend/health")
async def backend_health():
    try:
        return await call_health()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/train")
async def trigger_training(dataset: str = "SMAP", epochs: int = 5):
    try:
        return await call_train(dataset=dataset, epochs=epochs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
