"""
Kafka Event Producer — publishes store events to Kafka topics
Reads from JSONL file for simulation or receives events from CV pipeline
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = "kafka:9092"
TOPICS = {
    "store_events": "store-events",
    "cv_detections": "cv-detections",
    "anomaly_alerts": "anomaly-alerts",
    "pos_transactions": "pos-transactions",
}


class StoreEventProducer:
    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP):
        self.bootstrap_servers = bootstrap_servers
        self.producer: Optional[AIOKafkaProducer] = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            compression_type="gzip",
            acks="all",           # strong durability
            retry_backoff_ms=200,
            request_timeout_ms=10000,
        )
        await self.producer.start()
        logger.info(f"✅ Kafka producer connected: {self.bootstrap_servers}")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def publish(self, topic: str, event: dict, key: Optional[str] = None):
        """Publish a single event to a Kafka topic"""
        if not self.producer:
            raise RuntimeError("Producer not started")
        try:
            await self.producer.send_and_wait(topic, value=event, key=key)
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            raise

    async def publish_store_event(self, event: dict):
        """Route event to correct topic based on event_type"""
        event_type = event.get("event_type", "")
        store_id = event.get("store_id", "unknown")

        if event_type in ("suspicious_activity", "crowd_detected", "staff_missing",
                          "low_conversion_alert", "occupancy_warning"):
            topic = TOPICS["anomaly_alerts"]
        elif event_type == "purchase_completed":
            topic = TOPICS["pos_transactions"]
        else:
            topic = TOPICS["store_events"]

        await self.publish(topic, event, key=store_id)
        logger.debug(f"Published {event_type} → {topic}")


async def simulate_from_jsonl(jsonl_path: str, speed_multiplier: float = 10.0):
    """
    Read events from JSONL and replay them to Kafka.
    speed_multiplier: 10x means events play back 10x faster than real time.
    """
    producer = StoreEventProducer()
    await producer.start()

    events = []
    with open(jsonl_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    logger.info(f"Loaded {len(events)} events from {jsonl_path}")

    for i, event in enumerate(events):
        await producer.publish_store_event(event)
        logger.info(f"[{i+1}/{len(events)}] Published: {event['event_type']} @ {event['store_id']}")
        await asyncio.sleep(0.5 / speed_multiplier)  # simulated delay

    await producer.stop()
    logger.info("✅ JSONL simulation complete")


async def simulate_realtime(interval_seconds: float = 2.0):
    """
    Generate and stream synthetic events continuously — for demo/dev
    """
    import random, uuid
    producer = StoreEventProducer()

    for attempt in range(5):
        try:
            await producer.start()
            break
        except KafkaConnectionError:
            logger.warning(f"Kafka not ready, retry {attempt+1}/5...")
            await asyncio.sleep(5)

    EVENT_TYPES = [
        "customer_entered", "customer_exited", "zone_entered",
        "queue_started", "queue_increased", "purchase_completed",
        "suspicious_activity", "crowd_detected", "staff_missing"
    ]
    STORES = ["store_1", "store_2"]

    logger.info("📡 Real-time event simulation started")
    count = 0
    while True:
        store = random.choice(STORES)
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "store_id": store,
            "camera_id": random.choice(["entry_cam", "billing_cam", "zone_cam_1"]),
            "person_id": f"track_{random.randint(1, 200):03d}",
            "event_type": random.choice(EVENT_TYPES),
            "zone": random.choice(["entrance", "shelves_a", "billing"]),
            "confidence": round(random.uniform(0.75, 0.99), 2),
            "metadata": {"simulated": True, "seq": count}
        }
        await producer.publish_store_event(event)
        count += 1
        if count % 50 == 0:
            logger.info(f"Published {count} events")
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        asyncio.run(simulate_from_jsonl(sys.argv[1]))
    else:
        asyncio.run(simulate_realtime())
