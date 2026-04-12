from fastapi import APIRouter
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.alert_store import get_all_alerts, clear_alerts

router = APIRouter()

@router.get("/alerts")
def get_alerts():
    return get_all_alerts()

@router.delete("/alerts")
def delete_alerts():
    return clear_alerts()