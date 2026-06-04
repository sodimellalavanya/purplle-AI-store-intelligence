# API Documentation

Base URL: `http://localhost:8000`  
Interactive Docs: `http://localhost:8000/docs`

---

## Authentication
Currently open (no auth). For production, add Bearer JWT:
```
Authorization: Bearer <token>
```

---

## Endpoints

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info |
| GET | `/health` | System health check |

---

### Stores — `/stores`

#### `GET /stores/`
List all stores.
```json
{
  "stores": [
    { "store_id": "store_1", "name": "...", "max_occupancy": 80, "cameras": [...] }
  ],
  "total": 2
}
```

#### `GET /stores/{store_id}/metrics`
Live KPIs for a store.
```json
{
  "store_id": "store_1",
  "timestamp": "2024-01-15T19:00:00",
  "live": { "occupancy": 62, "occupancy_percentage": 77.5, "queue_length": 4 },
  "today": { "footfall": 185, "purchases": 63, "conversion_rate": 0.341, "revenue_estimate": 41000 }
}
```

#### `GET /stores/{store_id}/occupancy?hours=24`
Occupancy timeline. `hours`: 1–168.

#### `GET /stores/{store_id}/footfall?period=today`
Footfall breakdown. `period`: `today` | `week` | `month`.

---

### Cameras — `/cameras`

#### `GET /cameras/?store_id=store_1`
List cameras, optionally filtered by store.

#### `GET /cameras/{camera_id}/events?limit=20&event_type=customer_entered`
Recent events from a camera.

---

### Analytics — `/analytics`

#### `GET /analytics/heatmap?store_id=store_1&date=2024-01-15`
Returns 20×20 normalized grid (0.0–1.0) + zone engagement scores.

#### `GET /analytics/conversion-rate?store_id=store_1&period=today`
Hourly footfall vs purchase conversion. Flags `anomaly: true` for low-conversion hours.

#### `GET /analytics/queue?store_id=store_1&hours=12`
Queue length and wait-time timeline.

#### `GET /analytics/sales-correlation?store_id=store_1`
Correlates CCTV footfall with POS transactions. Flags `"anomaly_type": "busy_no_billing"`.

#### `GET /analytics/dwell-time?store_id=store_1`
Average dwell time per zone.

#### `GET /analytics/staff-activity?store_id=store_1`
Staff status: `active` | `idle` | `missing`.

---

### Alerts — `/alerts`

#### `GET /alerts/?store_id=store_1&severity=high&acknowledged=false&limit=50`
Filter alerts by store, severity, acknowledgement status.

#### `POST /alerts/{alert_id}/acknowledge`
```json
{ "acknowledged_by": "manager_01", "note": "Checked, resolved" }
```

#### `GET /alerts/summary`
Count of alerts by severity and type.

#### `POST /alerts/?store_id=store_1&alert_type=manual&severity=low&message=...`
Create a manual alert.

---

### Events — `/events`

#### `GET /events/stream?store_id=store_1&interval_ms=2000`
Server-Sent Events (SSE) stream. Connect from EventSource in browser:
```js
const es = new EventSource("http://localhost:8000/events/stream?store_id=store_1");
es.onmessage = (e) => console.log(JSON.parse(e.data));
```

#### `GET /events/recent?store_id=store_1&limit=20&event_type=customer_entered`
Last N events.

#### `GET /events/stats?store_id=store_1`
Event type frequency counts.

---

### Dashboard — `/dashboard`

#### `GET /dashboard/overview`
Single call returning all KPIs for both stores — used by dashboard initial load.

---

## Event Schema

```json
{
  "event_id": "uuid",
  "timestamp": "2024-01-15T19:00:00Z",
  "store_id": "store_1",
  "camera_id": "entry_cam",
  "person_id": "track_042",
  "event_type": "customer_entered",
  "zone": "entrance",
  "confidence": 0.94,
  "metadata": {}
}
```

### Event Types
| Type | Trigger |
|------|---------|
| `customer_entered` | Person crosses entry line inward |
| `customer_exited` | Person crosses entry line outward |
| `zone_entered` | Person detected in new zone |
| `queue_started` | First person detected at billing |
| `queue_increased` | Queue count exceeds threshold |
| `purchase_completed` | Transaction logged at POS |
| `suspicious_activity` | Loitering / unusual movement |
| `crowd_detected` | Zone count exceeds limit |
| `staff_missing` | No staff detected at billing during hours |
| `low_conversion_alert` | High footfall, low purchases |
| `occupancy_warning` | Store > 85% capacity |

---

## Error Responses

| Code | Meaning |
|------|---------|
| 400 | Bad request (e.g. already acknowledged) |
| 404 | Resource not found |
| 422 | Validation error |
| 429 | Rate limit exceeded (100 req/min) |
| 500 | Internal server error |
