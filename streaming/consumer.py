"""
Kafka Consumer — gracefully skips if Kafka is not running locally.
"""
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = "localhost:9092"
TOPICS = ["store-events", "cv-detections", "anomaly-alerts", "pos-transactions"]


async def start_consumer():
    """
    Tries to connect to Kafka. If unavailable (local dev without Kafka),
    logs a warning and exits silently — the API keeps running fine.
    """
    try:
        from aiokafka import AIOKafkaConsumer

        consumer = AIOKafkaConsumer(
            *TOPICS,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            group_id="store-intelligence-group",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
        )
        await asyncio.wait_for(consumer.start(), timeout=5.0)
        logger.info(f"✅ Kafka consumer started: {TOPICS}")

        async for msg in consumer:
            try:
                event = msg.value
                logger.debug(f"[Kafka] {event.get('store_id')} | {event.get('event_type')}")
            except Exception as e:
                logger.error(f"Error processing Kafka message: {e}")

    except ImportError:
        logger.warning("⚠️  aiokafka not installed — Kafka consumer disabled")
    except asyncio.TimeoutError:
        logger.warning("⚠️  Kafka not reachable — consumer disabled (API works without it)")
    except Exception as e:
        logger.warning(f"⚠️  Kafka consumer skipped: {e}")
