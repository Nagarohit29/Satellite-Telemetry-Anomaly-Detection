from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse
import sys
import os
import logging

_celestrak_logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.backend_client import (
    call_celestrak_constellation,
    call_celestrak_satellite,
    call_celestrak_infer,
    call_export_csv,
    call_satellite_passes
)

router = APIRouter()

class CelestrakInferRequest(BaseModel):
    mode: str
    target: str

class ExportCSVRequest(BaseModel):
    headers: list
    rows: list

@router.get("/celestrak/constellation/{group}")
async def get_celestrak_group(group: str):
    try:
        return await call_celestrak_constellation(group)
    except Exception as e:
        _celestrak_logger.error("Celestrak constellation error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/celestrak/satellite/{catnr}")
async def get_celestrak_sat(catnr: int):
    try:
        return await call_celestrak_satellite(catnr)
    except Exception as e:
        _celestrak_logger.error("Celestrak satellite error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/satellite/{norad_id}/passes")
async def get_satellite_passes(
    norad_id: int,
    observer_lat: float = 0.0,
    observer_lng: float = 0.0,
    observer_alt: float = 0.0,
    days: int = 2,
    min_elevation: float = 10.0
):
    try:
        return await call_satellite_passes(
            norad_id=norad_id,
            observer_lat=observer_lat,
            observer_lng=observer_lng,
            observer_alt=observer_alt,
            days=days,
            min_elevation=min_elevation
        )
    except Exception as e:
        _celestrak_logger.error("Satellite passes error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/celestrak/infer")
async def celestrak_infer(req: CelestrakInferRequest):
    try:
        return await call_celestrak_infer(req.mode, req.target)
    except Exception as e:
        _celestrak_logger.error("Celestrak infer error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/export/csv")
async def export_csv(req: ExportCSVRequest):
    try:
        csv_text = await call_export_csv(req.headers, req.rows)
        return PlainTextResponse(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=telemetry_report.csv"}
        )
    except Exception as e:
        _celestrak_logger.error("Export CSV error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
