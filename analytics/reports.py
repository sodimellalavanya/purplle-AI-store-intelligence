"""
Analytics report generation utilities.
Produces daily/weekly summaries from POS CSV and event JSONL.
"""
import json
import pandas as pd
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List


def load_events(jsonl_path: str) -> List[dict]:
    events = []
    with open(jsonl_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def event_summary(events: List[dict]) -> Dict:
    """Count events by type and store"""
    by_type: Dict[str, int] = {}
    by_store: Dict[str, int] = {}
    for evt in events:
        etype = evt.get("event_type", "unknown")
        store = evt.get("store_id", "unknown")
        by_type[etype] = by_type.get(etype, 0) + 1
        by_store[store] = by_store.get(store, 0) + 1
    return {"by_type": by_type, "by_store": by_store, "total": len(events)}


def anomaly_events(events: List[dict]) -> List[dict]:
    """Filter anomalous event types"""
    anomaly_types = {
        "suspicious_activity", "crowd_detected", "staff_missing",
        "low_conversion_alert", "occupancy_warning"
    }
    return [e for e in events if e.get("event_type") in anomaly_types]


def generate_daily_report(pos_path: str, jsonl_path: str, report_date: date = None) -> Dict:
    """Generate a complete daily report combining POS + CCTV events"""
    report_date = report_date or date.today()

    # Load POS
    df = pd.read_csv(pos_path, parse_dates=["timestamp"])
    df_today = df[df["timestamp"].dt.date == report_date] if not df.empty else df

    # Load events
    events = load_events(jsonl_path)

    # POS metrics
    pos_summary = {
        "total_transactions": len(df_today),
        "total_revenue": round(float(df_today["total_amount"].sum()), 2),
        "avg_basket": round(float(df_today["total_amount"].mean()), 2) if len(df_today) > 0 else 0,
        "by_store": {}
    }
    for sid in ["store_1", "store_2"]:
        s = df_today[df_today["store_id"] == sid]
        pos_summary["by_store"][sid] = {
            "transactions": len(s),
            "revenue": round(float(s["total_amount"].sum()), 2),
            "top_payment": s["payment_method"].mode()[0] if len(s) > 0 else "N/A"
        }

    # Event metrics
    evt_summary = event_summary(events)
    anomalies = anomaly_events(events)

    # Footfall from events
    footfall_store1 = sum(1 for e in events
                         if e.get("store_id") == "store_1" and e.get("event_type") == "customer_entered")
    footfall_store2 = sum(1 for e in events
                         if e.get("store_id") == "store_2" and e.get("event_type") == "customer_entered")

    txn_s1 = pos_summary["by_store"]["store_1"]["transactions"]
    txn_s2 = pos_summary["by_store"]["store_2"]["transactions"]

    report = {
        "report_date": str(report_date),
        "generated_at": datetime.utcnow().isoformat(),
        "pos": pos_summary,
        "cctv": {
            "total_events": evt_summary["total"],
            "by_type": evt_summary["by_type"],
            "footfall": {"store_1": footfall_store1, "store_2": footfall_store2},
            "anomalies_count": len(anomalies),
            "anomalies": anomalies,
        },
        "intelligence": {
            "store_1_conversion": round(txn_s1 / footfall_store1, 3) if footfall_store1 else 0,
            "store_2_conversion": round(txn_s2 / footfall_store2, 3) if footfall_store2 else 0,
            "top_alert_types": list({e["event_type"] for e in anomalies}),
        }
    }
    return report


if __name__ == "__main__":
    base = Path(__file__).parent.parent / "sample_data"
    report = generate_daily_report(
        str(base / "pos_transactions.csv"),
        str(base / "event_logs.jsonl"),
        date(2024, 1, 15)
    )
    print(json.dumps(report, indent=2))
