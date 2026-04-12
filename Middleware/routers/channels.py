from fastapi import APIRouter, HTTPException
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.backend_client import call_channels, call_health, call_train

router = APIRouter()

@router.get("/channels")
async def get_channels():
    try:
        return await call_channels()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backend/health")
async def backend_health():
    try:
        return await call_health()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/train")
async def trigger_training():
    try:
        return await call_train()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))