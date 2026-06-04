# Architecture Decisions

## 1. Microservice-Inspired Design

Each concern is a separate service with its own Dockerfile:

| Service | Responsibility | Language |
|---------|---------------|----------|
| `backend` | REST API, business logic | Python/FastAPI |
| `cv_pipeline` | Frame-by-frame detection | Python/OpenCV/YOLOv8 |
| `event_producer` | Kafka ingestion from JSONL/CCTV | Python/aiokafka |
| `anomaly_detection` | ML anomaly scoring | Python/sklearn |
| `dashboard` | UI | React/Vite |
| `mongodb` | Persistence | MongoDB 7 |
| `kafka` | Event bus | Confluent Kafka 7.6 |
| `redis` | API response cache | Redis 7.2 |

**Trade-off:** Adds deployment complexity vs monolith. Justified because CV pipeline is GPU-bound and needs separate scaling from API.

---

## 2. Kafka over Redis Streams

**Decision:** Apache Kafka  
**Reason:**
- Durable log — events can be replayed if analytics service crashes
- Multiple consumer groups (analytics + anomaly engine) read independently
- Better tooling (Kafka UI, schema registry, connectors)
- Partition model allows parallelism per store or camera

**Trade-off:** Heavier infra (needs Zookeeper). Redis Streams would be simpler for a single consumer.

---

## 3. MongoDB over PostgreSQL

**Decision:** MongoDB  
**Reason:**
- Events have variable `metadata` fields per type — schema-flexible
- Time-series queries on `[store_id, timestamp]` index are fast
- Aggregation pipeline handles hourly rollups natively

**Trade-off:** No ACID joins. Cross-collection queries require `$lookup`. Acceptable since analytics are pre-aggregated.

---

## 4. YOLOv8n for Detection

**Decision:** YOLOv8 nano  
**Reason:**
- Runs at 30+ FPS on CPU for 720p video
- Good enough accuracy for person detection (mAP ~37)
- `yolov8m` available as drop-in upgrade for GPU deployments

**Trade-off:** Nano model has lower accuracy than medium/large. Acceptable for occupancy counting; upgrade for identity/gender estimation.

---

## 5. Isolation Forest for Anomaly Detection

**Decision:** Isolation Forest over Autoencoder  
**Reason:**
- No GPU needed, trains in <1s on 500 samples
- Interpretable anomaly scores
- Works well with 5 tabular features
- scikit-learn makes it production-ready with `.fit()` / `.predict()`

**Trade-off:** Autoencoders would be better if using raw video embeddings as features, but tabular metrics are sufficient for retail anomaly detection at this scale.

---

## 6. FastAPI over Flask/Django

**Decision:** FastAPI  
**Reason:**
- Native async (important for SSE event streaming)
- Pydantic v2 for request validation with near-zero overhead
- Auto-generates OpenAPI/Swagger docs
- Built-in `BackgroundTasks` for Kafka consumer integration

**Trade-off:** Smaller ecosystem than Django. No ORM built-in (use Motor directly).

---

## 7. React + Recharts over Streamlit

**Decision:** React (production dashboard) over Streamlit (prototype)  
**Reason:**
- SSE (`EventSource`) for real-time event streaming without polling
- Custom camera feed simulation with SVG overlays
- Tailwind utility classes for consistent dark-theme UI
- Ships as static files served by Nginx (no Python runtime in prod)

**Trade-off:** More code than Streamlit. Justified for production presentation quality.

---

## 8. SSE over WebSockets for Event Stream

**Decision:** Server-Sent Events (SSE)  
**Reason:**
- Simpler than WebSockets (unidirectional, browser reconnects automatically)
- Works through HTTP/2 multiplexing
- FastAPI's `StreamingResponse` handles it natively

**Trade-off:** Unidirectional only. If dashboard needs to send commands to backend, switch to WebSocket or REST polling.

---

## Scalability Path

```
Current (1 store, demo)
  └── Single Docker Compose node

Scale to 10 stores
  └── Kafka: 1 partition per store (10 partitions)
  └── CV: 1 container per camera (Kubernetes DaemonSet on camera nodes)
  └── Backend: 4 Uvicorn workers behind Nginx load balancer
  └── MongoDB: Replica set (3 nodes)
  └── Redis: Redis Cluster for rate limiting

Scale to 100 stores
  └── Kafka: MSK (managed) with 100 partitions
  └── CV: GPU nodes with TensorRT-optimized YOLOv8
  └── Backend: Kubernetes HPA (scale on CPU/RPS)
  └── MongoDB Atlas: Sharding by store_id
  └── Grafana + Prometheus for observability
```
