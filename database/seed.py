"""
Seeds MongoDB with initial store, camera, and sample analytics data
Run once on fresh deployment: python seed.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import random

MONGODB_URL = "mongodb://localhost:27017"
DB_NAME = "store_intelligence"

STORES = [
    {
        "store_id": "store_1",
        "name": "Purplle Store - Andheri West",
        "location": "Mumbai, Maharashtra",
        "max_occupancy": 80,
        "cameras": ["entry_cam", "zone_cam_1", "zone_cam_2", "billing_cam", "layout_cam_1"],
        "zones": ["entrance", "shelves_a", "shelves_b", "billing", "restricted"],
        "is_active": True,
        "created_at": datetime.utcnow()
    },
    {
        "store_id": "store_2",
        "name": "Purplle Store - Koramangala",
        "location": "Bangalore, Karnataka",
        "max_occupancy": 50,
        "cameras": ["entry_1", "entry_2", "billing_area", "layout_cam_2", "zone_s2"],
        "zones": ["entrance", "shelves_main", "billing_area", "restricted"],
        "is_active": True,
        "created_at": datetime.utcnow()
    }
]

CAMERAS = [
    {"camera_id": "entry_cam", "store_id": "store_1", "zone": "entrance", "status": "active"},
    {"camera_id": "zone_cam_1", "store_id": "store_1", "zone": "shelves_a", "status": "active"},
    {"camera_id": "zone_cam_2", "store_id": "store_1", "zone": "shelves_b", "status": "active"},
    {"camera_id": "billing_cam", "store_id": "store_1", "zone": "billing", "status": "active"},
    {"camera_id": "layout_cam_1", "store_id": "store_1", "zone": "overview", "status": "active"},
    {"camera_id": "entry_1", "store_id": "store_2", "zone": "entrance", "status": "active"},
    {"camera_id": "entry_2", "store_id": "store_2", "zone": "entrance", "status": "active"},
    {"camera_id": "billing_area", "store_id": "store_2", "zone": "billing_area", "status": "active"},
    {"camera_id": "layout_cam_2", "store_id": "store_2", "zone": "overview", "status": "offline"},
    {"camera_id": "zone_s2", "store_id": "store_2", "zone": "shelves_main", "status": "active"},
]


async def seed():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]

    print("Seeding stores...")
    await db.stores.drop()
    await db.stores.insert_many(STORES)

    print("Seeding cameras...")
    await db.cameras.drop()
    await db.cameras.insert_many(CAMERAS)

    print("Seeding analytics snapshots...")
    await db.analytics.drop()
    snapshots = []
    for store_id in ["store_1", "store_2"]:
        max_occ = 80 if store_id == "store_1" else 50
        for h in range(8, 22):
            footfall = random.randint(10, 80) if 10 <= h <= 21 else random.randint(2, 10)
            purchases = int(footfall * random.uniform(0.25, 0.42))
            occupancy = int(footfall * random.uniform(0.5, 0.85))
            snapshots.append({
                "store_id": store_id,
                "timestamp": datetime.utcnow().replace(hour=h, minute=0, second=0),
                "hour": h,
                "occupancy": min(occupancy, max_occ),
                "footfall": footfall,
                "transactions": purchases,
                "conversion_rate": round(purchases / footfall, 3) if footfall else 0,
                "avg_dwell_time": round(random.uniform(10, 25), 1),
                "queue_length": random.randint(0, 8),
                "revenue": round(purchases * random.uniform(500, 800), 2),
            })
    await db.analytics.insert_many(snapshots)

    print(f"✅ Seeded: {len(STORES)} stores, {len(CAMERAS)} cameras, {len(snapshots)} analytics snapshots")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
