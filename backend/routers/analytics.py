"""
Analytics endpoints - heatmap, conversion rate, queue analysis, sales correlation
"""
import random
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/heatmap", summary="Customer movement heatmap")
async def get_heatmap(
    store_id: str = Query(..., description="Store ID"),
    date: Optional[str] = Query(default=None, description="Date YYYY-MM-DD")
):
    """
    Returns heatmap data showing customer density across store zones.
    Grid is 20x20 normalized to store floor plan.
    """
    # Generate realistic heatmap grid (20x20)
    grid = []
    for row in range(20):
        row_data = []
        for col in range(20):
            # Entrance area (top)
            if row < 3:
                val = random.uniform(0.6, 0.95)
            # Billing area (bottom right)
            elif row > 15 and col > 14:
                val = random.uniform(0.7, 0.99)
            # Main shelves (middle)
            elif 5 <= row <= 15 and 3 <= col <= 17:
                val = random.uniform(0.2, 0.8)
            # Restricted areas (corners)
            elif (row > 17 and col < 3) or (row > 17 and col > 17):
                val = random.uniform(0.0, 0.1)
            else:
                val = random.uniform(0.05, 0.3)
            row_data.append(round(val, 3))
        grid.append(row_data)

    zone_engagement = {
        "entrance": round(random.uniform(0.75, 0.95), 2),
        "shelves_a": round(random.uniform(0.55, 0.80), 2),
        "shelves_b": round(random.uniform(0.45, 0.70), 2),
        "billing": round(random.uniform(0.60, 0.85), 2),
        "promotional_display": round(random.uniform(0.30, 0.55), 2),
    }

    return {
        "store_id": store_id,
        "date": date or datetime.utcnow().strftime("%Y-%m-%d"),
        "grid_size": "20x20",
        "grid": grid,
        "zone_engagement": zone_engagement,
        "peak_zones": ["entrance", "billing", "shelves_a"],
        "dead_zones": ["restricted", "storage"],
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/conversion-rate", summary="Sales conversion analysis")
async def get_conversion_rate(
    store_id: Optional[str] = Query(default=None),
    period: str = Query(default="today", enum=["today", "week", "month"])
):
    """
    Correlate CCTV footfall with POS transactions.
    Identifies high-traffic low-conversion periods.
    """
    stores = ["store_1", "store_2"] if not store_id else [store_id]
    result = {}

    for sid in stores:
        if period == "today":
            hourly = []
            for h in range(8, 23):
                footfall = random.randint(15, 80) if 10 <= h <= 20 else random.randint(2, 15)
                conv_rate = random.uniform(0.15, 0.45)
                if 13 <= h <= 15:
                    conv_rate = random.uniform(0.10, 0.22)  # Post-lunch low conversion
                elif h >= 19:
                    conv_rate = random.uniform(0.35, 0.50)   # Evening high conversion
                purchases = int(footfall * conv_rate)
                hourly.append({
                    "hour": f"{h:02d}:00",
                    "footfall": footfall,
                    "purchases": purchases,
                    "conversion_rate": round(conv_rate, 3),
                    "anomaly": conv_rate < 0.18
                })
            result[sid] = {
                "period": period,
                "overall_conversion": round(sum(h["conversion_rate"] for h in hourly) / len(hourly), 3),
                "total_footfall": sum(h["footfall"] for h in hourly),
                "total_purchases": sum(h["purchases"] for h in hourly),
                "low_conversion_periods": [h for h in hourly if h["anomaly"]],
                "hourly_breakdown": hourly
            }

    return result


@router.get("/queue", summary="Queue analysis")
async def get_queue_analysis(
    store_id: str = Query(...),
    hours: int = Query(default=12, ge=1, le=48)
):
    """
    Queue length and wait time analysis across billing zones
    """
    now = datetime.utcnow()
    timeline = []
    for h in range(hours, 0, -1):
        ts = now - timedelta(hours=h)
        hour = ts.hour
        # Simulate queue buildup during peak hours
        if 12 <= hour <= 14 or 19 <= hour <= 21:
            queue_len = random.randint(4, 12)
            wait_time = random.uniform(8, 20)
        elif 9 <= hour <= 11:
            queue_len = random.randint(1, 5)
            wait_time = random.uniform(2, 8)
        else:
            queue_len = random.randint(0, 3)
            wait_time = random.uniform(0, 5)

        timeline.append({
            "timestamp": ts.isoformat(),
            "hour": hour,
            "queue_length": queue_len,
            "avg_wait_minutes": round(wait_time, 1),
            "alert": queue_len > 6
        })

    peak_queues = [t for t in timeline if t["alert"]]
    return {
        "store_id": store_id,
        "avg_queue_length": round(sum(t["queue_length"] for t in timeline) / len(timeline), 1),
        "max_queue_length": max(t["queue_length"] for t in timeline),
        "avg_wait_minutes": round(sum(t["avg_wait_minutes"] for t in timeline) / len(timeline), 1),
        "peak_queue_events": len(peak_queues),
        "timeline": timeline
    }


@router.get("/sales-correlation", summary="CCTV footfall vs POS sales")
async def get_sales_correlation(
    store_id: str = Query(...)
):
    """
    Correlates camera-detected footfall with actual POS transactions.
    Highlights anomalies like busy store with no billing.
    """
    correlation = []
    for h in range(8, 22):
        footfall = random.randint(10, 90)
        # Afternoon anomaly: high footfall, low billing
        if 13 <= h <= 15:
            billing_active = random.choice([True, False, False])
        else:
            billing_active = random.choice([True, True, True, False])

        revenue = random.uniform(2000, 12000) if billing_active else random.uniform(0, 500)
        txn_count = int(footfall * (0.35 if billing_active else 0.05))

        correlation.append({
            "hour": f"{h:02d}:00",
            "footfall": footfall,
            "transactions": txn_count,
            "revenue": round(revenue, 2),
            "avg_basket": round(revenue / txn_count, 2) if txn_count > 0 else 0,
            "billing_active": billing_active,
            "anomaly": footfall > 40 and not billing_active,
            "anomaly_type": "busy_no_billing" if (footfall > 40 and not billing_active) else None
        })

    anomalies = [c for c in correlation if c["anomaly"]]
    return {
        "store_id": store_id,
        "correlation": correlation,
        "anomalies_detected": len(anomalies),
        "anomaly_details": anomalies,
        "total_revenue": round(sum(c["revenue"] for c in correlation), 2),
        "total_footfall": sum(c["footfall"] for c in correlation),
        "overall_conversion": round(
            sum(c["transactions"] for c in correlation) / sum(c["footfall"] for c in correlation), 3
        )
    }


@router.get("/dwell-time", summary="Customer dwell time by zone")
async def get_dwell_time(store_id: str = Query(...)):
    """Average time customers spend in each zone"""
    zones = {
        "entrance": {"avg_minutes": 1.2, "visits": 185},
        "shelves_a": {"avg_minutes": 8.4, "visits": 142},
        "shelves_b": {"avg_minutes": 6.1, "visits": 118},
        "promotional_display": {"avg_minutes": 3.8, "visits": 95},
        "billing": {"avg_minutes": 5.6, "visits": 68},
    }
    return {
        "store_id": store_id,
        "zones": zones,
        "total_avg_dwell_minutes": 18.4,
        "top_engagement_zone": "shelves_a"
    }


@router.get("/staff-activity", summary="Staff monitoring summary")
async def get_staff_activity(store_id: str = Query(...)):
    """Staff presence and activity status across zones"""
    staff = [
        {"staff_id": "staff_01", "zone": "billing", "status": "active", "hours_on_floor": 6.2},
        {"staff_id": "staff_02", "zone": "shelves_a", "status": "active", "hours_on_floor": 5.8},
        {"staff_id": "staff_03", "zone": "entrance", "status": "idle", "idle_minutes": 28},
        {"staff_id": "staff_04", "zone": "billing", "status": "active", "hours_on_floor": 4.1},
        {"staff_id": "staff_05", "zone": "unknown", "status": "missing", "last_seen_minutes_ago": 45},
    ]
    return {
        "store_id": store_id,
        "staff_summary": staff,
        "active_count": sum(1 for s in staff if s["status"] == "active"),
        "idle_count": sum(1 for s in staff if s["status"] == "idle"),
        "missing_count": sum(1 for s in staff if s["status"] == "missing"),
        "alerts": [s for s in staff if s["status"] in ("idle", "missing")]
    }
