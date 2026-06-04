"""
Alerts management endpoints
"""
import uuid
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory alert store (replace with MongoDB in full production)
_alerts_store = [
    {
        "alert_id": "alert_001",
        "store_id": "store_1",
        "camera_id": "billing_cam",
        "alert_type": "staff_missing",
        "severity": "high",
        "message": "No staff detected at billing counter for 15+ minutes during peak hours",
        "details": {"duration_minutes": 15, "zone": "billing", "peak_hour": True},
        "is_acknowledged": False,
        "created_at": "2024-01-15T11:00:00Z"
    },
    {
        "alert_id": "alert_002",
        "store_id": "store_1",
        "camera_id": "billing_cam",
        "alert_type": "low_conversion",
        "severity": "medium",
        "message": "High footfall (45 customers) but only 18% conversion rate between 13:00-14:00",
        "details": {"footfall": 45, "transactions": 8, "conversion_rate": 0.18, "hour": 13},
        "is_acknowledged": False,
        "created_at": "2024-01-15T13:00:00Z"
    },
    {
        "alert_id": "alert_003",
        "store_id": "store_2",
        "camera_id": "zone",
        "alert_type": "crowd_congestion",
        "severity": "high",
        "message": "Crowd congestion detected in main shelves area — 12 customers, threshold 10",
        "details": {"count": 12, "threshold": 10, "zone": "shelves_main"},
        "is_acknowledged": True,
        "acknowledged_by": "manager_01",
        "created_at": "2024-01-15T11:15:00Z"
    },
    {
        "alert_id": "alert_004",
        "store_id": "store_2",
        "camera_id": "billing_area",
        "alert_type": "occupancy_warning",
        "severity": "critical",
        "message": "Store 2 at 96% occupancy — approaching maximum capacity (48/50)",
        "details": {"current": 48, "max": 50, "percentage": 96},
        "is_acknowledged": False,
        "created_at": "2024-01-15T14:30:00Z"
    },
    {
        "alert_id": "alert_005",
        "store_id": "store_1",
        "camera_id": "zone_cam_1",
        "alert_type": "suspicious_activity",
        "severity": "medium",
        "message": "Suspicious loitering detected in shelves_a zone — person stationary for 15+ minutes",
        "details": {"person_id": "track_006", "duration_seconds": 900, "zone": "shelves_a"},
        "is_acknowledged": False,
        "created_at": "2024-01-15T10:35:00Z"
    },
    {
        "alert_id": "alert_006",
        "store_id": "store_1",
        "camera_id": "billing_cam",
        "alert_type": "queue_overflow",
        "severity": "medium",
        "message": "Queue length reached 8 at billing — estimated 12 min wait",
        "details": {"queue_length": 8, "wait_time_minutes": 12},
        "is_acknowledged": False,
        "created_at": "2024-01-15T19:00:00Z"
    }
]


@router.get("/", summary="List all alerts")
async def get_alerts(
    store_id: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None, enum=["low", "medium", "high", "critical"]),
    acknowledged: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200)
):
    """Get all alerts with optional filtering"""
    alerts = _alerts_store.copy()

    if store_id:
        alerts = [a for a in alerts if a["store_id"] == store_id]
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]
    if acknowledged is not None:
        alerts = [a for a in alerts if a["is_acknowledged"] == acknowledged]

    alerts = sorted(alerts, key=lambda x: x["created_at"], reverse=True)[:limit]

    return {
        "alerts": alerts,
        "total": len(alerts),
        "unacknowledged": sum(1 for a in alerts if not a["is_acknowledged"]),
        "by_severity": {
            "critical": sum(1 for a in alerts if a["severity"] == "critical"),
            "high": sum(1 for a in alerts if a["severity"] == "high"),
            "medium": sum(1 for a in alerts if a["severity"] == "medium"),
            "low": sum(1 for a in alerts if a["severity"] == "low"),
        }
    }


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str
    note: Optional[str] = None


@router.post("/{alert_id}/acknowledge", summary="Acknowledge an alert")
async def acknowledge_alert(alert_id: str, body: AcknowledgeRequest):
    """Mark an alert as acknowledged with staff ID"""
    for alert in _alerts_store:
        if alert["alert_id"] == alert_id:
            if alert["is_acknowledged"]:
                raise HTTPException(status_code=400, detail="Alert already acknowledged")
            alert["is_acknowledged"] = True
            alert["acknowledged_by"] = body.acknowledged_by
            alert["acknowledged_at"] = datetime.utcnow().isoformat()
            if body.note:
                alert["note"] = body.note
            return {"success": True, "alert": alert}

    raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")


@router.post("/", summary="Create manual alert")
async def create_alert(
    store_id: str,
    alert_type: str,
    severity: str,
    message: str
):
    """Manually create an alert (for testing or manual reporting)"""
    alert = {
        "alert_id": f"alert_{uuid.uuid4().hex[:6]}",
        "store_id": store_id,
        "camera_id": None,
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
        "details": {"manual": True},
        "is_acknowledged": False,
        "created_at": datetime.utcnow().isoformat()
    }
    _alerts_store.append(alert)
    return {"success": True, "alert": alert}


@router.get("/summary", summary="Alert summary stats")
async def get_alert_summary():
    """Summary of alerts across all stores"""
    return {
        "total_alerts": len(_alerts_store),
        "unacknowledged": sum(1 for a in _alerts_store if not a["is_acknowledged"]),
        "by_store": {
            "store_1": sum(1 for a in _alerts_store if a["store_id"] == "store_1"),
            "store_2": sum(1 for a in _alerts_store if a["store_id"] == "store_2"),
        },
        "by_type": {
            t: sum(1 for a in _alerts_store if a["alert_type"] == t)
            for t in set(a["alert_type"] for a in _alerts_store)
        }
    }
