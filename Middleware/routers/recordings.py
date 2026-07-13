from fastapi import APIRouter, HTTPException
import sys
import os
import logging

_recordings_logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.backend_client import (
    call_list_recordings,
    call_save_recording,
    call_get_recording,
    call_delete_recording
)

router = APIRouter()

@router.get("/recordings")
async def list_recordings():
    try:
        return await call_list_recordings()
    except Exception as e:
        _recordings_logger.error("List recordings error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/recordings")
async def save_recording(req: dict):
    try:
        return await call_save_recording(req)
    except Exception as e:
        _recordings_logger.error("Save recording error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/recordings/{rec_id}")
async def get_recording(rec_id: str):
    try:
        return await call_get_recording(rec_id)
    except Exception as e:
        _recordings_logger.error("Get recording error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/recordings/{rec_id}")
async def delete_recording(rec_id: str):
    try:
        return await call_delete_recording(rec_id)
    except Exception as e:
        _recordings_logger.error("Delete recording error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
