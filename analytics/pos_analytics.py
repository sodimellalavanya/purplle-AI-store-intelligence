"""
POS Transaction Analytics Engine
Reads CSV, generates store-level sales insights, correlates with CCTV footfall
"""
import pandas as pd
import json
from datetime import datetime
from pathlib import Path


def load_transactions(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df["date"] = df["timestamp"].dt.date
    return df


def hourly_summary(df: pd.DataFrame, store_id: str) -> dict:
    store_df = df[df["store_id"] == store_id]
    hourly = store_df.groupby("hour").agg(
        transactions=("transaction_id", "count"),
        revenue=("total_amount", "sum"),
        avg_basket=("total_amount", "mean"),
        avg_items=("items_count", "mean"),
        avg_duration=("duration_seconds", "mean"),
    ).reset_index()
    return hourly.to_dict(orient="records")


def payment_breakdown(df: pd.DataFrame, store_id: str) -> dict:
    store_df = df[df["store_id"] == store_id]
    breakdown = store_df.groupby("payment_method").agg(
        count=("transaction_id", "count"),
        revenue=("total_amount", "sum"),
    ).reset_index()
    return breakdown.to_dict(orient="records")


def top_hours(df: pd.DataFrame, store_id: str, top_n: int = 3) -> list:
    store_df = df[df["store_id"] == store_id]
    hourly = store_df.groupby("hour")["total_amount"].sum().sort_values(ascending=False)
    return hourly.head(top_n).index.tolist()


def overall_summary(df: pd.DataFrame) -> dict:
    return {
        "total_transactions": len(df),
        "total_revenue": round(df["total_amount"].sum(), 2),
        "avg_basket_size": round(df["total_amount"].mean(), 2),
        "avg_items_per_txn": round(df["items_count"].mean(), 2),
        "store_1": {
            "transactions": len(df[df["store_id"] == "store_1"]),
            "revenue": round(df[df["store_id"] == "store_1"]["total_amount"].sum(), 2),
        },
        "store_2": {
            "transactions": len(df[df["store_id"] == "store_2"]),
            "revenue": round(df[df["store_id"] == "store_2"]["total_amount"].sum(), 2),
        }
    }


if __name__ == "__main__":
    base = Path(__file__).parent.parent / "sample_data"
    df = load_transactions(str(base / "pos_transactions.csv"))
    summary = overall_summary(df)
    print("=== Overall Summary ===")
    print(json.dumps(summary, indent=2))
    print("\n=== Store 1 Peak Hours ===", top_hours(df, "store_1"))
    print("\n=== Store 2 Payment Mix ===")
    print(json.dumps(payment_breakdown(df, "store_2"), indent=2))
