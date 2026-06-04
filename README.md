# 🛍️ Purplle Store Intelligence System
### AI-Powered Retail Analytics Platform — Tech Challenge 2026 Round 2

---

## 📌 Overview

A production-grade, end-to-end AI retail intelligence platform that processes **CCTV footage**, **POS transaction data**, and **real-time event streams** to generate actionable store insights across **2 stores**.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STORE INTELLIGENCE SYSTEM                        │
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │  CCTV    │───▶│ CV Pipeline  │───▶│   Kafka Event Bus        │  │
│  │ Cameras  │    │ YOLOv8+Track │    │  store-events            │  │
│  └──────────┘    └──────────────┘    │  cv-detections           │  │
│                                      │  anomaly-alerts          │  │
│  ┌──────────┐    ┌──────────────┐    │  pos-transactions        │  │
│  │   POS    │───▶│  Analytics   │───▶└──────────┬───────────────┘  │
│  │   CSV    │    │   Engine     │               │                   │
│  └──────────┘    └──────────────┘    ┌──────────▼───────────────┐  │
│                                      │   Analytics Service      │  │
│  ┌──────────┐    ┌──────────────┐    │   Anomaly Detection      │  │
│  │  JSONL   │───▶│   Streaming  │    │   MongoDB Persistence    │  │
│  │  Events  │    │   Producer   │    └──────────┬───────────────┘  │
│  └──────────┘    └──────────────┘               │                   │
│                                      ┌──────────▼───────────────┐  │
│                                      │   FastAPI REST + SSE     │  │
│                                      │   /stores /analytics     │  │
│                                      │   /alerts /cameras       │  │
│                                      └──────────┬───────────────┘  │
│                                                 │                   │
│                                      ┌──────────▼───────────────┐  │
│                                      │   React Dashboard        │  │
│                                      │   Live Charts · Heatmap  │  │
│                                      │   Alerts · Camera Feeds  │  │
│                                      └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Folder Structure

```
store-intelligence-system/
├── backend/                    # FastAPI REST API
│   ├── main.py                 # App entry point, middleware, lifespan
│   ├── config.py               # Pydantic settings (env-driven)
│   ├── routers/
│   │   ├── stores.py           # GET /stores, /metrics, /occupancy, /footfall
│   │   ├── cameras.py          # GET /cameras, /{id}/events
│   │   ├── analytics.py        # GET /analytics/heatmap, /conversion-rate, /queue
│   │   ├── alerts.py           # GET/POST /alerts, /acknowledge
│   │   ├── events.py           # SSE /events/stream, /recent
│   │   └── dashboard.py        # GET /dashboard/overview
│   ├── models/
│   │   └── schemas.py          # Pydantic models for all entities
│   ├── middleware/
│   │   ├── logging.py          # Request/response logging
│   │   └── rate_limit.py       # In-memory rate limiter
│   ├── database/
│   │   └── connection.py       # Motor async MongoDB client + indexes
│   ├── requirements.txt
│   └── Dockerfile
│
├── cv_pipeline/                # Computer Vision processing
│   ├── processor.py            # YOLOv8 detection + ByteTrack + zones + heatmap
│   ├── requirements.txt
│   └── Dockerfile
│
├── streaming/                  # Kafka event pipeline
│   ├── producers/
│   │   └── event_producer.py   # JSONL replay + real-time synthetic producer
│   ├── consumer.py             # Kafka consumer with event routing
│   ├── requirements.txt
│   └── Dockerfile
│
├── analytics/                  # Offline analytics engines
│   ├── pos_analytics.py        # POS CSV analysis + sales correlation
│   └── reports.py              # Report generation utilities
│
├── anomaly_detection/          # ML anomaly engine
│   ├── engine.py               # Isolation Forest + Rule-based detector
│   ├── requirements.txt
│   └── Dockerfile
│
├── dashboard/                  # React + Tailwind frontend
│   ├── src/
│   │   ├── App.jsx             # Full dashboard (6 tabs, live charts, heatmap)
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── nginx.conf
│   └── Dockerfile
│
├── database/
│   └── seed.py                 # MongoDB seeder (stores, cameras, analytics)
│
├── tests/
│   ├── backend/
│   │   └── test_api.py         # pytest API tests
│   ├── cv/
│   │   └── test_processor.py   # CV pipeline unit tests
│   └── analytics/
│       └── test_anomaly.py     # Anomaly detection tests
│
├── sample_data/
│   ├── pos_transactions.csv    # 40 POS transactions, 2 stores
│   └── event_logs.jsonl        # 30 store events (JSONL)
│
├── docs/
│   ├── api.md                  # API endpoint documentation
│   ├── architecture.md         # Detailed architecture decisions
│   └── schema.md               # MongoDB schema reference
│
├── docker-compose.yml          # Full stack: MongoDB, Kafka, Backend, CV, Dashboard
├── .env.example                # Environment variable template
├── .gitignore
└── README.md                   # This file
```

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose v2+
- (Optional for local dev) Python 3.11+, Node 20+

### 1. Clone & Configure
```bash
git clone <repo-url>
cd store-intelligence-system

cp .env.example .env
# Edit .env if needed (defaults work for local Docker)
```

### 2. Start All Services
```bash
docker compose up --build -d
```

This starts:
| Service | URL |
|---|---|
| Dashboard (React) | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Kafka UI | http://localhost:8080 |
| MongoDB | localhost:27017 |

### 3. Seed the Database
```bash
docker compose exec backend python database/seed.py
```

### 4. Replay Sample Events to Kafka
```bash
docker compose exec event_producer python producers/event_producer.py /app/sample_data/event_logs.jsonl
```

### 5. Run POS Analytics
```bash
docker compose exec backend python analytics/pos_analytics.py
```

---

## 🖥️ Local Development (without Docker)

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Dashboard
```bash
cd dashboard
npm install
npm run dev   # → http://localhost:3000
```

### Run CV Pipeline on a video
```bash
cd cv_pipeline
python processor.py /path/to/store_video.mp4
```

### Run Anomaly Engine Demo
```bash
cd anomaly_detection
python engine.py
```

---

## 🔌 API Reference

### Stores
```
GET  /stores                          — List all stores
GET  /stores/{store_id}               — Store details
GET  /stores/{store_id}/metrics       — Live KPIs (occupancy, footfall, conversion)
GET  /stores/{store_id}/occupancy     — Occupancy timeline (last N hours)
GET  /stores/{store_id}/footfall      — Footfall by hour/day/week
```

### Cameras
```
GET  /cameras                         — List cameras (filter by store_id)
GET  /cameras/{camera_id}             — Camera details + uptime
GET  /cameras/{camera_id}/events      — Recent events from camera
```

### Analytics
```
GET  /analytics/heatmap               — 20×20 movement heatmap grid
GET  /analytics/conversion-rate       — Footfall vs purchase correlation
GET  /analytics/queue                 — Queue length timeline
GET  /analytics/sales-correlation     — Busy-store vs billing anomalies
GET  /analytics/dwell-time            — Avg dwell time per zone
GET  /analytics/staff-activity        — Staff status per zone
```

### Alerts
```
GET  /alerts                          — All alerts (filter: store, severity, ack)
GET  /alerts/summary                  — Count by severity and type
POST /alerts/{alert_id}/acknowledge   — Acknowledge alert
POST /alerts                          — Create manual alert
```

### Events
```
GET  /events/stream                   — SSE stream (real-time, dashboard)
GET  /events/recent                   — Last N events
GET  /events/stats                    — Event type frequency
```

### Dashboard
```
GET  /dashboard/overview              — All KPIs for both stores in one call
GET  /health                          — System health check
```

---

## 🤖 AI/CV Pipeline

### Detection — YOLOv8
- Model: `yolov8n.pt` (nano, fast) — upgradeable to `yolov8m` for accuracy
- Classes: person (0)
- Threshold: 0.5 confidence

### Tracking — ByteTrack
- Maintains unique `track_id` per person across frames
- Handles occlusion and re-identification

### Zone Detection
Each store has polygon zones defined in `cv_pipeline/processor.py`:
- Store 1: `entrance`, `shelves_a`, `shelves_b`, `billing`, `restricted`
- Store 2: `entrance`, `shelves_main`, `billing_area`, `restricted`

### Heatmap
- 20×20 grid accumulator per camera
- Normalized 0–1 per session
- Rendered in dashboard with color gradient

---

## 🚨 Anomaly Detection

### ML Layer — Isolation Forest
- Trained on synthetic normal retail patterns
- Features: `footfall`, `transactions`, `occupancy`, `queue_length`, `revenue`
- Contamination: 10%

### Rule-Based Layer
| Rule | Trigger | Severity |
|---|---|---|
| Occupancy Warning | > 85% capacity | High |
| Occupancy Critical | > 95% capacity | Critical |
| Queue Overflow | ≥ 8 at billing | High |
| Low Conversion | footfall > 30, rate < 15% | Medium |
| Busy No Billing | footfall > 40, 0 transactions | Critical |
| Staff Missing | No staff at billing during hours | High |
| Traffic Drop | footfall drops > 70% vs prev hour | Medium |

---

## 📊 Kafka Topics

| Topic | Producer | Consumer | Schema |
|---|---|---|---|
| `store-events` | CV Pipeline, JSONL producer | Analytics service | StoreEvent |
| `cv-detections` | CV Pipeline | Analytics service | Detection |
| `anomaly-alerts` | Anomaly engine | Backend API | Alert |
| `pos-transactions` | POS ingestion | Analytics service | Transaction |

---

## 🗄️ MongoDB Collections

| Collection | Purpose | Key Indexes |
|---|---|---|
| `stores` | Store config | `store_id` |
| `cameras` | Camera config | `store_id`, `camera_id` |
| `events` | All store events | `store_id+timestamp`, `event_type` |
| `transactions` | POS data | `store_id+timestamp` |
| `alerts` | Anomaly alerts | `store_id`, `is_acknowledged` |
| `analytics` | Hourly snapshots | `store_id+timestamp` |

---

## 🧪 Testing

```bash
# Backend API tests
cd tests/backend
pip install pytest httpx
pytest test_api.py -v

# CV pipeline tests
cd tests/cv
pytest test_processor.py -v

# Anomaly detection tests
cd tests/analytics
pytest test_anomaly.py -v
```

---

## 🏭 Production Notes

### Scaling
- Backend: increase `--workers` in Dockerfile CMD (use `gunicorn` for multi-process)
- Kafka: increase partition count per topic for parallel consumers
- CV: run one container per camera stream; GPU instances recommended for YOLOv8m+
- MongoDB: add replica set for HA

### Real CCTV Integration
Replace `mock_detect()` in `cv_pipeline/processor.py` with:
```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")
results = model.track(frame, persist=True, tracker="bytetrack.yaml")
```

### Security (production checklist)
- [ ] Change `SECRET_KEY` in `.env`
- [ ] Add JWT auth to all API routes
- [ ] Enable Kafka SASL/TLS
- [ ] MongoDB auth credentials
- [ ] Rate limiting via Redis (replace in-memory middleware)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS + Recharts |
| Backend | FastAPI + Uvicorn + Pydantic v2 |
| CV/AI | YOLOv8 (Ultralytics) + OpenCV + ByteTrack |
| Anomaly ML | Scikit-learn Isolation Forest |
| Streaming | Apache Kafka + aiokafka |
| Database | MongoDB + Motor (async) |
| Cache | Redis |
| Deployment | Docker + Docker Compose |
| Testing | pytest + httpx |

---

## 👥 Engineering Decisions

**Why Kafka over Redis Streams?**  
Kafka provides durable log storage, replay capability, and horizontal scale. For a retail system with multiple camera streams and analytics consumers, Kafka's partition model is a better fit than Redis Streams' simpler in-memory model.

**Why MongoDB over PostgreSQL?**  
Store events are schema-flexible (metadata varies per event type). MongoDB's document model fits naturally. Time-series queries (hourly footfall) perform well with compound indexes on `store_id + timestamp`.

**Why Isolation Forest over Autoencoder?**  
Isolation Forest requires no GPU, trains in seconds on CPU, and is interpretable. For a retail context with ~5 features, it outperforms autoencoders without the training complexity. Autoencoders are better if raw video embeddings are used as features.

**Why FastAPI over Django?**  
Async-native, lightweight, auto-generates OpenAPI docs, perfect for SSE streaming endpoints. Django's ORM overhead is unnecessary for a primarily read-heavy analytics API.

---

*Built for Purplle Tech Challenge 2026 — Round 2*
