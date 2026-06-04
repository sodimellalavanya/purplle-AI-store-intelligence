"""
Event streaming endpoints including SSE for real-time dashboard
"""
import asyncio
import json
import random
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

router = APIRouter()

EVENT_TYPES = [
    "customer_entered", "customer_exited", "queue_started", "queue_increased",
    "purchase_completed", "suspicious_activity", "crowd_detected",
    "staff_missing", "low_conversion_alert", "occupancy_warning", "zone_entered"
]

ZONES = {
    "store_1": ["entrance", "shelves_a", "shelves_b", "billing", "restricted"],
    "store_2": ["entrance", "shelves_main", "billing_area", "restricted"]
}


def generate_event(store_id: Optional[str] = None) -> dict:
    sid = store_id or random.choice(["store_1", "store_2"])
    camera_map = {
        "store_1": ["entry_cam", "zone_cam_1", "zone_cam_2", "billing_cam"],
        "store_2": ["entry_1", "entry_2", "billing_area", "zone_s2"]
    }
    zone = random.choice(ZONES[sid])
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "store_id": sid,
        "camera_id": random.choice(camera_map[sid]),
        "person_id": f"track_{random.randint(1, 300):03d}",
        "event_type": random.choice(EVENT_TYPES),
        "zone": zone,
        "confidence": round(random.uniform(0.70, 0.99), 2),
        "metadata": {"simulated": True}
    }


@router.get("/stream", summary="SSE event stream for real-time dashboard")
async def stream_events(
    store_id: Optional[str] = Query(default=None),
    interval_ms: int = Query(default=2000, ge=500, le=10000)
):
    """
    Server-Sent Events stream of store events.
    Connect from dashboard for live updates.
    """
    async def event_generator():
        while True:
            event = generate_event(store_id)
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(interval_ms / 1000)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/recent", summary="Recent events across stores")
async def get_recent_events(
    store_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20),
    event_type: Optional[str] = Query(default=None)
):
    """Latest N events from event log"""
    events = [generate_event(store_id) for _ in range(limit)]
    if event_type:
        events = [e for e in events if e["event_type"] == event_type]
    return {"events": events, "total": len(events)}


@router.get("/stats", summary="Event type frequency stats")
async def get_event_stats(store_id: Optional[str] = Query(default=None)):
    """Count of each event type for today"""
    stats = {}
    for et in EVENT_TYPES:
        stats[et] = random.randint(5, 120)
    return {
        "store_id": store_id or "all",
        "period": "today",
        "event_counts": stats,
        "total_events": sum(stats.values())
    }
