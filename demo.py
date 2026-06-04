#!/usr/bin/env python3
"""
Standalone Demo — runs without Docker/Kafka/MongoDB
Shows all subsystems working: CV pipeline, anomaly detection, analytics, event simulation

Run: python demo.py
"""
import json
import sys
import os
import random
from datetime import datetime, date

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cv_pipeline"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "anomaly_detection"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "analytics"))

DIVIDER = "─" * 60

def section(title):
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


def demo_cv_pipeline():
    section("1. COMPUTER VISION PIPELINE")
    from processor import StoreVideoProcessor, mock_detect
    import numpy as np

    events_produced = []

    def capture_event(evt):
        events_produced.append(evt)

    proc = StoreVideoProcessor("store_1", "entry_cam", event_callback=capture_event)

    print("Processing 50 simulated frames from entry_cam (Store 1)...")
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    for i in range(50):
        detections = mock_detect(frame)
        proc.process_frame(frame, detections)

    stats = proc.get_stats()
    print(f"  Frames processed  : {stats['frames_processed']}")
    print(f"  Unique people tracked: {stats['total_tracked']}")
    print(f"  Current occupancy : {stats['current_occupancy']}")
    print(f"  Entries / Exits   : {stats['entries']} / {stats['exits']}")
    print(f"  Events produced   : {len(events_produced)}")
    if events_produced:
        sample = events_produced[0]
        print(f"\n  Sample event:")
        print(f"    type      : {sample['event_type']}")
        print(f"    zone      : {sample['zone']}")
        print(f"    person_id : {sample['person_id']}")
        print(f"    confidence: {sample['confidence']}")

    # Heatmap summary
    hm = stats["heatmap"]
    flat = [v for row in hm for v in row]
    print(f"\n  Heatmap (20×20) — max density: {max(flat):.3f}, avg: {sum(flat)/len(flat):.3f}")


def demo_anomaly_detection():
    section("2. ANOMALY DETECTION ENGINE")
    from engine import StoreAnomalyEngine

    engine = StoreAnomalyEngine("store_1", max_occupancy=80)

    scenarios = [
        ("Normal afternoon", {
            "footfall": 42, "transactions": 15, "occupancy": 30,
            "queue_length": 2, "revenue": 9750.0, "conversion_rate": 0.36,
            "billing_active": True, "billing_staffed": True, "prev_hour_footfall": 38
        }),
        ("High traffic, low conversion", {
            "footfall": 68, "transactions": 8, "occupancy": 55,
            "queue_length": 3, "revenue": 5200.0, "conversion_rate": 0.12,
            "billing_active": True, "billing_staffed": True, "prev_hour_footfall": 64
        }),
        ("CRITICAL: Busy store, billing inactive", {
            "footfall": 72, "transactions": 0, "occupancy": 71,
            "queue_length": 11, "revenue": 0.0, "conversion_rate": 0.00,
            "billing_active": False, "billing_staffed": False, "prev_hour_footfall": 68
        }),
        ("Store at 96% capacity", {
            "footfall": 55, "transactions": 18, "occupancy": 77,
            "queue_length": 6, "revenue": 11700.0, "conversion_rate": 0.33,
            "billing_active": True, "billing_staffed": True, "prev_hour_footfall": 50
        }),
    ]

    for name, metrics in scenarios:
        result = engine.analyze(metrics)
        status = "🚨 ANOMALY" if result["is_anomalous"] else "✅ Normal"
        print(f"\n  Scenario: {name}")
        print(f"    Status      : {status}")
        print(f"    ML Score    : {result['ml_score']:.3f}")
        print(f"    Alert Count : {result['alert_count']}")
        for alert in result["alerts"]:
            print(f"    [{alert['severity'].upper():8}] {alert['alert_type']}: {alert['message'][:70]}")


def demo_pos_analytics():
    section("3. POS ANALYTICS (CSV Processing)")
    from pos_analytics import load_transactions, overall_summary, top_hours, payment_breakdown

    csv_path = os.path.join(os.path.dirname(__file__), "sample_data", "pos_transactions.csv")
    if not os.path.exists(csv_path):
        print("  sample_data/pos_transactions.csv not found — skipping")
        return

    df = load_transactions(csv_path)
    summary = overall_summary(df)

    print(f"  Total transactions : {summary['total_transactions']}")
    print(f"  Total revenue      : ₹{summary['total_revenue']:,.2f}")
    print(f"  Avg basket size    : ₹{summary['avg_basket_size']:,.2f}")
    print(f"  Avg items/txn      : {summary['avg_items_per_txn']:.1f}")
    print(f"\n  Store 1:")
    print(f"    Transactions: {summary['store_1']['transactions']}")
    print(f"    Revenue     : ₹{summary['store_1']['revenue']:,.2f}")
    print(f"\n  Store 2:")
    print(f"    Transactions: {summary['store_2']['transactions']}")
    print(f"    Revenue     : ₹{summary['store_2']['revenue']:,.2f}")

    s1_peak = top_hours(df, "store_1")
    s2_peak = top_hours(df, "store_2")
    print(f"\n  Store 1 peak revenue hours: {s1_peak}")
    print(f"  Store 2 peak revenue hours: {s2_peak}")

    pay = payment_breakdown(df, "store_1")
    print(f"\n  Store 1 payment methods:")
    for p in pay:
        print(f"    {p['payment_method']:6}: {p['count']} txns, ₹{p['revenue']:,.2f}")


def demo_event_stream():
    section("4. EVENT STREAM SIMULATION (JSONL Replay)")
    jsonl_path = os.path.join(os.path.dirname(__file__), "sample_data", "event_logs.jsonl")
    if not os.path.exists(jsonl_path):
        print("  sample_data/event_logs.jsonl not found — skipping")
        return

    events = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    print(f"  Loaded {len(events)} events from JSONL")
    print(f"  (In production these stream through Kafka topics)\n")

    by_type: dict = {}
    by_store: dict = {}
    for evt in events:
        t = evt.get("event_type", "unknown")
        s = evt.get("store_id", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        by_store[s] = by_store.get(s, 0) + 1

    print("  Event types:")
    for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    {k:<30}: {v}")

    print(f"\n  By store:")
    for s, c in by_store.items():
        print(f"    {s}: {c} events")

    anomaly_types = {"suspicious_activity", "crowd_detected", "staff_missing",
                     "low_conversion_alert", "occupancy_warning"}
    anomalies = [e for e in events if e.get("event_type") in anomaly_types]
    print(f"\n  Anomalous events detected: {len(anomalies)}")
    for a in anomalies[:3]:
        print(f"    [{a['store_id']}] {a['event_type']} @ {a['zone']}")


def demo_daily_report():
    section("5. DAILY REPORT GENERATION")
    from reports import generate_daily_report
    base = os.path.join(os.path.dirname(__file__), "sample_data")
    pos_path = os.path.join(base, "pos_transactions.csv")
    jsonl_path = os.path.join(base, "event_logs.jsonl")

    if not (os.path.exists(pos_path) and os.path.exists(jsonl_path)):
        print("  Sample data not found — skipping")
        return

    report = generate_daily_report(pos_path, jsonl_path, date(2024, 1, 15))
    print(f"  Report date     : {report['report_date']}")
    print(f"  Total revenue   : ₹{report['pos']['total_revenue']:,.2f}")
    print(f"  Total txns      : {report['pos']['total_transactions']}")
    print(f"  CCTV events     : {report['cctv']['total_events']}")
    print(f"  Anomalies found : {report['cctv']['anomalies_count']}")
    print(f"  S1 conversion   : {report['intelligence']['store_1_conversion']:.1%}")
    print(f"  S2 conversion   : {report['intelligence']['store_2_conversion']:.1%}")
    print(f"  Alert types     : {report['intelligence']['top_alert_types']}")


if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("  PURPLLE STORE INTELLIGENCE SYSTEM — DEMO")
    print("  Tech Challenge 2026 · Round 2")
    print("═" * 60)

    demo_cv_pipeline()
    demo_anomaly_detection()
    demo_pos_analytics()
    demo_event_stream()
    demo_daily_report()

    print(f"\n{DIVIDER}")
    print("  ✅ All subsystems demo complete!")
    print(f"  Start full stack: docker compose up --build")
    print(f"  Dashboard:        http://localhost:3000")
    print(f"  API Docs:         http://localhost:8000/docs")
    print(f"  Kafka UI:         http://localhost:8080")
    print(DIVIDER + "\n")
