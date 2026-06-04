# MongoDB Schema Reference

Database: `store_intelligence`

---

## Collection: `stores`
```json
{
  "_id": "ObjectId",
  "store_id": "store_1",
  "name": "Purplle Store - Andheri West",
  "location": "Mumbai, Maharashtra",
  "max_occupancy": 80,
  "cameras": ["entry_cam", "zone_cam_1", "zone_cam_2", "billing_cam", "layout_cam_1"],
  "zones": ["entrance", "shelves_a", "shelves_b", "billing", "restricted"],
  "is_active": true,
  "created_at": "ISODate"
}
```
**Indexes:** `store_id` (unique)

---

## Collection: `cameras`
```json
{
  "_id": "ObjectId",
  "camera_id": "entry_cam",
  "store_id": "store_1",
  "zone": "entrance",
  "stream_url": "rtsp://...",
  "is_active": true,
  "last_seen": "ISODate",
  "resolution": "1920x1080",
  "fps": 30
}
```
**Indexes:** `store_id`, `camera_id` (unique)

---

## Collection: `events`
```json
{
  "_id": "ObjectId",
  "event_id": "uuid-string",
  "timestamp": "ISODate",
  "store_id": "store_1",
  "camera_id": "entry_cam",
  "person_id": "track_042",
  "event_type": "customer_entered",
  "zone": "entrance",
  "confidence": 0.94,
  "metadata": { "dwell_time": 1250 },
  "processed": false,
  "created_at": "ISODate"
}
```
**Indexes:** `[store_id, timestamp]` (desc), `event_type`, `person_id`

---

## Collection: `transactions`
```json
{
  "_id": "ObjectId",
  "transaction_id": "TXN001",
  "store_id": "store_1",
  "timestamp": "ISODate",
  "cashier_id": "staff_01",
  "customer_id": "cust_101",
  "items_count": 3,
  "total_amount": 450.50,
  "payment_method": "upi",
  "duration_seconds": 120,
  "zone": "billing"
}
```
**Indexes:** `[store_id, timestamp]` (desc), `transaction_id`

---

## Collection: `alerts`
```json
{
  "_id": "ObjectId",
  "alert_id": "alert_001",
  "store_id": "store_1",
  "camera_id": "billing_cam",
  "alert_type": "staff_missing",
  "severity": "high",
  "message": "No staff at billing for 15 min during peak hours",
  "details": { "duration_minutes": 15, "zone": "billing" },
  "is_acknowledged": false,
  "acknowledged_by": null,
  "acknowledged_at": null,
  "created_at": "ISODate"
}
```
**Indexes:** `[store_id, is_acknowledged]`, `created_at` (desc), `severity`

---

## Collection: `analytics`
```json
{
  "_id": "ObjectId",
  "store_id": "store_1",
  "timestamp": "ISODate",
  "hour": 19,
  "day": 1,
  "occupancy": 62,
  "footfall": 185,
  "transactions": 63,
  "conversion_rate": 0.341,
  "avg_dwell_time": 18.4,
  "queue_length": 4,
  "revenue": 41000.0
}
```
**Indexes:** `[store_id, timestamp]` (desc), `hour`
