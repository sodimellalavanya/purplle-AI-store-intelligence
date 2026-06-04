"""
Async MongoDB connection using Motor.
Gracefully handles missing MongoDB in local dev.
"""
import logging

logger = logging.getLogger(__name__)

client = None
db = None


async def init_db():
    global client, db
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import settings
        client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=3000)
        db = client[settings.MONGODB_DB]
        # Ping to verify connection
        await client.admin.command("ping")
        await create_indexes()
        logger.info(f"✅ MongoDB connected: {settings.MONGODB_URL}")
    except ImportError:
        logger.warning("⚠️  motor not installed — MongoDB disabled")
    except Exception as e:
        logger.warning(f"⚠️  MongoDB not reachable ({e}) — running without DB")
        client = None
        db = None


async def create_indexes():
    if db is None:
        return
    await db.events.create_index([("store_id", 1), ("timestamp", -1)])
    await db.events.create_index([("event_type", 1)])
    await db.transactions.create_index([("store_id", 1), ("timestamp", -1)])
    await db.alerts.create_index([("store_id", 1), ("is_acknowledged", 1)])
    await db.analytics.create_index([("store_id", 1), ("timestamp", -1)])
    logger.info("✅ Database indexes created")


async def close_db():
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed")


def get_db():
    return db
