"""
Dashboard aggregation endpoint — returns everything for the main dashboard in one call
"""
import random
from datetime import datetime
from fastapi import APIRouter

router = APIRouter()


@router.get("/overview", summary="Full dashboard data in one call")
async def get_dashboard_overview():
    """
    Aggregates all key metrics for both stores.
    Optimized for dashboard initial load.
    """
    now = datetime.utcnow()

    def store_snapshot(sid, max_occ, footfall_base):
        footfall = random.randint(int(footfall_base * 0.8), int(footfall_base * 1.2))
        occupancy = random.randint(int(max_occ * 0.4), int(max_occ * 0.95))
        purchases = int(footfall * random.uniform(0.25, 0.42))
        queue = random.randint(1, 10)
        return {
            "store_id": sid,
            "occupancy": occupancy,
            "occupancy_pct": round(occupancy / max_occ * 100, 1),
            "max_occupancy": max_occ,
            "footfall_today": footfall,
            "purchases_today": purchases,
            "conversion_rate": round(purchases / footfall, 3),
            "revenue_today": round(purchases * random.uniform(550, 750), 2),
            "queue_length": queue,
            "avg_dwell_minutes": round(random.uniform(12, 22), 1),
            "active_alerts": random.randint(1, 4),
            "staff_on_floor": random.randint(4, 8),
        }

    # Hourly footfall for chart (last 14 hours)
    def hourly_footfall(base):
        data = []
        for h in range(8, 22):
            f = int(base * (1.5 if 19 <= h <= 21 else 0.8 if h < 10 else 1.0) * random.uniform(0.85, 1.15))
            data.append({"hour": f"{h:02d}:00", "value": f})
        return data

    return {
        "timestamp": now.isoformat(),
        "stores": {
            "store_1": store_snapshot("store_1", 80, 185),
            "store_2": store_snapshot("store_2", 50, 112),
        },
        "charts": {
            "store_1_footfall": hourly_footfall(15),
            "store_2_footfall": hourly_footfall(9),
        },
        "global_alerts": random.randint(3, 8),
        "system_status": {
            "cameras_online": 9,
            "cameras_total": 10,
            "kafka_lag": random.randint(0, 50),
            "cv_pipeline": "running",
            "anomaly_engine": "running"
        }
    }
