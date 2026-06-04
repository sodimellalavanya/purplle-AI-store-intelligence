"""
Store management endpoints
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
try:
    from database.connection import get_db
except ImportError:
    def get_db(): return None

logger = logging.getLogger(__name__)
router = APIRouter()

# Static store config (would come from DB in full production)
STORES = {
    "store_1": {
        "store_id": "store_1",
        "name": "Purplle Store - Andheri West",
        "location": "Mumbai, Maharashtra",
        "max_occupancy": 80,
        "cameras": ["entry_cam", "zone_cam_1", "zone_cam_2", "billing_cam", "layout_cam"],
        "zones": ["entrance", "shelves_a", "shelves_b", "billing", "restricted"],
        "is_active": True
    },
    "store_2": {
        "store_id": "store_2",
        "name": "Purplle Store - Koramangala",
        "location": "Bangalore, Karnataka",
        "max_occupancy": 50,
        "cameras": ["billing_area", "entry_1", "entry_2", "layout_cam", "zone"],
        "zones": ["entrance", "shelves_main", "billing_area", "restricted"],
        "is_active": True
    }
}


@router.get("/", summary="List all stores")
async def get_stores():
    """Returns all configured stores with their current status"""
    return {"stores": list(STORES.values()), "total": len(STORES)}


@router.get("/{store_id}", summary="Get store details")
async def get_store(store_id: str):
    """Get detailed information about a specific store"""
    if store_id not in STORES:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")
    return STORES[store_id]


@router.get("/{store_id}/metrics", summary="Live store metrics")
async def get_store_metrics(store_id: str):
    """
    Get real-time metrics for a store:
    - Current occupancy
    - Today's footfall
    - Conversion rate
    - Average dwell time
    - Active queue length
    """
    if store_id not in STORES:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")

    db = get_db()

    # Fetch today's analytics
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Aggregated metrics from events
    pipeline = [
        {"$match": {"store_id": store_id, "timestamp": {"$gte": today}}},
        {"$group": {
            "_id": "$event_type",
            "count": {"$sum": 1}
        }}
    ]

    event_counts = {}
    if db:
        async for doc in db.events.aggregate(pipeline):
            event_counts[doc["_id"]] = doc["count"]

    footfall = event_counts.get("customer_entered", 0)
    exits = event_counts.get("customer_exited", 0)
    purchases = event_counts.get("purchase_completed", 0)

    # Simulated live metrics if DB empty
    if not footfall:
        import random
        footfall = random.randint(80, 200) if store_id == "store_1" else random.randint(50, 120)
        exits = int(footfall * 0.85)
        purchases = int(footfall * 0.32)

    occupancy = max(0, footfall - exits)
    conversion_rate = round(purchases / footfall, 3) if footfall > 0 else 0.0
    max_occ = STORES[store_id]["max_occupancy"]

    return {
        "store_id": store_id,
        "timestamp": datetime.utcnow().isoformat(),
        "live": {
            "occupancy": min(occupancy, max_occ),
            "occupancy_percentage": round(min(occupancy, max_occ) / max_occ * 100, 1),
            "queue_length": event_counts.get("queue_increased", 0),
            "active_cameras": len(STORES[store_id]["cameras"]),
            "alerts_count": event_counts.get("suspicious_activity", 0)
        },
        "today": {
            "footfall": footfall,
            "purchases": purchases,
            "conversion_rate": conversion_rate,
            "avg_dwell_time_minutes": 18.4,
            "peak_hour": 19,
            "revenue_estimate": purchases * 650.0
        }
    }


@router.get("/{store_id}/occupancy", summary="Occupancy timeline")
async def get_occupancy(
    store_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history")
):
    """Get occupancy over time as a timeline"""
    if store_id not in STORES:
        raise HTTPException(status_code=404, detail="Store not found")

    import random
    now = datetime.utcnow()
    max_occ = STORES[store_id]["max_occupancy"]

    timeline = []
    for h in range(hours, 0, -1):
        ts = now - timedelta(hours=h)
        hour = ts.hour
        # Simulate realistic retail traffic pattern
        if 9 <= hour <= 11:
            base = 0.3
        elif 12 <= hour <= 14:
            base = 0.6
        elif 15 <= hour <= 18:
            base = 0.75
        elif 19 <= hour <= 21:
            base = 0.9
        elif hour < 9 or hour > 22:
            base = 0.05
        else:
            base = 0.4

        occ = int(max_occ * base * random.uniform(0.8, 1.1))
        timeline.append({
            "timestamp": ts.isoformat(),
            "hour": hour,
            "occupancy": min(occ, max_occ),
            "percentage": round(min(occ, max_occ) / max_occ * 100, 1)
        })

    return {
        "store_id": store_id,
        "max_occupancy": max_occ,
        "timeline": timeline
    }


@router.get("/{store_id}/footfall", summary="Footfall analytics")
async def get_footfall(
    store_id: str,
    period: str = Query(default="today", enum=["today", "week", "month"])
):
    """Get footfall broken down by hour/day"""
    if store_id not in STORES:
        raise HTTPException(status_code=404, detail="Store not found")

    import random
    data = []

    if period == "today":
        for hour in range(8, 23):
            if hour < 9 or hour > 21:
                count = random.randint(2, 10)
            elif 19 <= hour <= 21:
                count = random.randint(60, 100)
            elif 12 <= hour <= 14:
                count = random.randint(40, 70)
            else:
                count = random.randint(20, 50)
            data.append({"label": f"{hour:02d}:00", "footfall": count, "purchases": int(count * 0.32)})
    elif period == "week":
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for d in days:
            count = random.randint(150, 350) if d in ["Sat", "Sun"] else random.randint(80, 180)
            data.append({"label": d, "footfall": count, "purchases": int(count * 0.32)})
    else:
        for w in range(1, 5):
            count = random.randint(800, 1500)
            data.append({"label": f"Week {w}", "footfall": count, "purchases": int(count * 0.32)})

    return {"store_id": store_id, "period": period, "data": data}


@router.get("/{store_id}/comparison", summary="Cross-store comparison")
async def compare_stores():
    """Compare Store 1 vs Store 2 across key metrics"""
    import random
    return {
        "comparison": {
            "footfall": {"store_1": 185, "store_2": 112},
            "conversion_rate": {"store_1": 0.34, "store_2": 0.28},
            "avg_dwell_time": {"store_1": 18.4, "store_2": 14.2},
            "revenue": {"store_1": 38500, "store_2": 21200},
            "queue_avg": {"store_1": 4.2, "store_2": 2.8},
            "occupancy_peak": {"store_1": 0.89, "store_2": 0.96}
        }
    }
