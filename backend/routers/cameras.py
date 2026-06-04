"""
Camera management and event endpoints
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import random

router = APIRouter()

CAMERAS = {
    "entry_cam":    {"camera_id": "entry_cam",    "store_id": "store_1", "zone": "entrance",    "status": "active"},
    "zone_cam_1":   {"camera_id": "zone_cam_1",   "store_id": "store_1", "zone": "shelves_a",   "status": "active"},
    "zone_cam_2":   {"camera_id": "zone_cam_2",   "store_id": "store_1", "zone": "shelves_b",   "status": "active"},
    "billing_cam":  {"camera_id": "billing_cam",  "store_id": "store_1", "zone": "billing",     "status": "active"},
    "layout_cam_1": {"camera_id": "layout_cam_1", "store_id": "store_1", "zone": "overview",    "status": "active"},
    "billing_area": {"camera_id": "billing_area", "store_id": "store_2", "zone": "billing_area","status": "active"},
    "entry_1":      {"camera_id": "entry_1",      "store_id": "store_2", "zone": "entrance",    "status": "active"},
    "entry_2":      {"camera_id": "entry_2",      "store_id": "store_2", "zone": "entrance",    "status": "active"},
    "layout_cam_2": {"camera_id": "layout_cam_2", "store_id": "store_2", "zone": "overview",    "status": "offline"},
    "zone_s2":      {"camera_id": "zone_s2",      "store_id": "store_2", "zone": "shelves_main","status": "active"},
}


@router.get("/", summary="List all cameras")
async def get_cameras(store_id: Optional[str] = Query(default=None)):
    cams = list(CAMERAS.values())
    if store_id:
        cams = [c for c in cams if c["store_id"] == store_id]
    return {
        "cameras": cams,
        "total": len(cams),
        "active": sum(1 for c in cams if c["status"] == "active"),
        "offline": sum(1 for c in cams if c["status"] == "offline"),
    }


@router.get("/{camera_id}", summary="Camera details")
async def get_camera(camera_id: str):
    if camera_id not in CAMERAS:
        raise HTTPException(status_code=404, detail="Camera not found")
    cam = CAMERAS[camera_id].copy()
    cam.update({
        "fps": 30,
        "resolution": "1920x1080",
        "last_seen": datetime.utcnow().isoformat(),
        "detection_count_today": random.randint(50, 300),
        "uptime_hours": round(random.uniform(10, 24), 1),
    })
    return cam


@router.get("/{camera_id}/events", summary="Events from a specific camera")
async def get_camera_events(
    camera_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    event_type: Optional[str] = Query(default=None)
):
    if camera_id not in CAMERAS:
        raise HTTPException(status_code=404, detail="Camera not found")

    cam = CAMERAS[camera_id]
    event_types = ["customer_entered", "customer_exited", "queue_started",
                   "purchase_completed", "zone_entered", "suspicious_activity"]
    now = datetime.utcnow()
    events = []
    for i in range(limit):
        et = event_type or random.choice(event_types)
        events.append({
            "event_id": f"evt_{camera_id}_{i:04d}",
            "timestamp": (now - timedelta(minutes=i * 5)).isoformat(),
            "store_id": cam["store_id"],
            "camera_id": camera_id,
            "person_id": f"track_{random.randint(1,200):03d}",
            "event_type": et,
            "zone": cam["zone"],
            "confidence": round(random.uniform(0.75, 0.99), 2),
        })

    return {"camera_id": camera_id, "events": events, "total": len(events)}
