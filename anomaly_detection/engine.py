"""
Anomaly Detection Engine
Uses Isolation Forest for unsupervised anomaly detection on store metrics.
Also includes rule-based detectors for specific retail scenarios.
"""
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


# ── Alert Dataclass ────────────────────────────────────────────────────────────
@dataclass
class AnomalyAlert:
    alert_type: str
    severity: str  # low, medium, high, critical
    store_id: str
    message: str
    details: dict
    timestamp: datetime = None
    confidence: float = 0.0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "store_id": self.store_id,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence
        }


# ── Isolation Forest Detector ──────────────────────────────────────────────────
class IsolationForestDetector:
    """
    Detects multivariate anomalies in store metrics using Isolation Forest.
    Features: [footfall, transactions, occupancy, queue_length, revenue]
    """

    def __init__(self, contamination: float = 0.1, n_estimators: int = 100):
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names = ["footfall", "transactions", "occupancy", "queue_length", "revenue"]

    def fit(self, historical_data: pd.DataFrame):
        """Train on historical store metrics"""
        X = historical_data[self.feature_names].values
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True
        logger.info(f"✅ Isolation Forest trained on {len(historical_data)} samples")

    def fit_synthetic(self):
        """Train on synthetic normal retail patterns for demo"""
        np.random.seed(42)
        n = 500
        # Simulate normal retail day patterns
        hours = np.random.randint(0, 24, n)
        footfall = np.where(
            (hours >= 10) & (hours <= 21),
            np.random.normal(50, 15, n),
            np.random.normal(5, 3, n)
        ).clip(0, 100)
        transactions = (footfall * np.random.uniform(0.25, 0.45, n)).astype(int)
        occupancy = (footfall * np.random.uniform(0.6, 0.9, n)).astype(int)
        queue = np.where(footfall > 60, np.random.normal(6, 2, n), np.random.normal(2, 1, n)).clip(0, 20)
        revenue = transactions * np.random.normal(650, 150, n)

        df = pd.DataFrame({
            "footfall": footfall,
            "transactions": transactions,
            "occupancy": occupancy.clip(0, 80),
            "queue_length": queue,
            "revenue": revenue.clip(0)
        })
        self.fit(df)

    def predict(self, metrics: Dict) -> Tuple[bool, float]:
        """
        Returns (is_anomaly, anomaly_score)
        anomaly_score: higher = more anomalous (0 to 1)
        """
        if not self.is_fitted:
            self.fit_synthetic()

        X = np.array([[
            metrics.get("footfall", 0),
            metrics.get("transactions", 0),
            metrics.get("occupancy", 0),
            metrics.get("queue_length", 0),
            metrics.get("revenue", 0)
        ]])
        X_scaled = self.scaler.transform(X)
        pred = self.model.predict(X_scaled)[0]  # 1=normal, -1=anomaly
        score_raw = self.model.score_samples(X_scaled)[0]
        # Convert to 0-1 anomaly score (higher = more anomalous)
        anomaly_score = max(0.0, min(1.0, (-score_raw + 0.5)))

        return pred == -1, round(anomaly_score, 3)


# ── Rule-Based Detectors ───────────────────────────────────────────────────────
class RuleBasedDetector:
    """Fast rule-based anomaly detection for known retail patterns"""

    def __init__(self, store_id: str, max_occupancy: int = 80):
        self.store_id = store_id
        self.max_occupancy = max_occupancy

    def check_all(self, metrics: Dict) -> List[AnomalyAlert]:
        alerts = []
        checks = [
            self.check_occupancy,
            self.check_queue,
            self.check_low_conversion,
            self.check_busy_no_billing,
            self.check_staff_coverage,
            self.check_sudden_traffic_drop,
        ]
        for check in checks:
            alert = check(metrics)
            if alert:
                alerts.append(alert)
        return alerts

    def check_occupancy(self, m: Dict) -> Optional[AnomalyAlert]:
        occ = m.get("occupancy", 0)
        pct = occ / self.max_occupancy
        if pct >= 0.95:
            return AnomalyAlert(
                alert_type="occupancy_critical",
                severity="critical",
                store_id=self.store_id,
                message=f"Store at {pct*100:.0f}% capacity ({occ}/{self.max_occupancy})",
                details={"occupancy": occ, "max": self.max_occupancy, "pct": pct},
                confidence=0.99
            )
        elif pct >= 0.85:
            return AnomalyAlert(
                alert_type="occupancy_warning",
                severity="high",
                store_id=self.store_id,
                message=f"Store at {pct*100:.0f}% capacity — approaching limit",
                details={"occupancy": occ, "max": self.max_occupancy, "pct": pct},
                confidence=0.95
            )
        return None

    def check_queue(self, m: Dict) -> Optional[AnomalyAlert]:
        q = m.get("queue_length", 0)
        wait = m.get("avg_wait_minutes", 0)
        if q >= 8:
            return AnomalyAlert(
                alert_type="queue_overflow",
                severity="high",
                store_id=self.store_id,
                message=f"Long queue at billing: {q} customers, ~{wait:.0f} min wait",
                details={"queue_length": q, "wait_minutes": wait},
                confidence=0.92
            )
        return None

    def check_low_conversion(self, m: Dict) -> Optional[AnomalyAlert]:
        footfall = m.get("footfall", 0)
        conv = m.get("conversion_rate", 1.0)
        if footfall > 30 and conv < 0.15:
            return AnomalyAlert(
                alert_type="low_conversion",
                severity="medium",
                store_id=self.store_id,
                message=f"Low conversion: {footfall} visitors but only {conv*100:.0f}% purchased",
                details={"footfall": footfall, "conversion_rate": conv},
                confidence=0.85
            )
        return None

    def check_busy_no_billing(self, m: Dict) -> Optional[AnomalyAlert]:
        footfall = m.get("footfall", 0)
        transactions = m.get("transactions", 0)
        billing_active = m.get("billing_active", True)
        if footfall > 40 and transactions < 3 and not billing_active:
            return AnomalyAlert(
                alert_type="busy_store_no_billing",
                severity="critical",
                store_id=self.store_id,
                message=f"🚨 Busy store ({footfall} customers) but billing counter appears inactive!",
                details={"footfall": footfall, "transactions": transactions},
                confidence=0.91
            )
        return None

    def check_staff_coverage(self, m: Dict) -> Optional[AnomalyAlert]:
        missing = m.get("staff_missing_count", 0)
        billing_staffed = m.get("billing_staffed", True)
        if not billing_staffed and m.get("footfall", 0) > 15:
            return AnomalyAlert(
                alert_type="staff_missing",
                severity="high",
                store_id=self.store_id,
                message="No staff detected at billing counter during active hours",
                details={"billing_staffed": billing_staffed, "missing_count": missing},
                confidence=0.87
            )
        return None

    def check_sudden_traffic_drop(self, m: Dict) -> Optional[AnomalyAlert]:
        footfall = m.get("footfall", 0)
        prev_footfall = m.get("prev_hour_footfall", footfall)
        if prev_footfall > 30 and footfall < prev_footfall * 0.3:
            return AnomalyAlert(
                alert_type="sudden_traffic_drop",
                severity="medium",
                store_id=self.store_id,
                message=f"Sudden traffic drop: {prev_footfall}→{footfall} customers",
                details={"current": footfall, "previous": prev_footfall},
                confidence=0.78
            )
        return None


# ── Combined Detector ──────────────────────────────────────────────────────────
class StoreAnomalyEngine:
    """
    Combines ML (Isolation Forest) + Rule-based detection
    for comprehensive anomaly coverage
    """

    def __init__(self, store_id: str, max_occupancy: int = 80):
        self.store_id = store_id
        self.ml_detector = IsolationForestDetector()
        self.rule_detector = RuleBasedDetector(store_id, max_occupancy)
        self.ml_detector.fit_synthetic()
        logger.info(f"✅ Anomaly engine ready for {store_id}")

    def analyze(self, metrics: Dict) -> Dict:
        """Run both detectors and return combined results"""
        # ML detection
        is_anomaly, ml_score = self.ml_detector.predict(metrics)

        # Rule-based detection
        rule_alerts = self.rule_detector.check_all(metrics)

        # ML alert if high score
        ml_alerts = []
        if is_anomaly and ml_score > 0.65:
            ml_alerts.append(AnomalyAlert(
                alert_type="ml_anomaly",
                severity="medium" if ml_score < 0.80 else "high",
                store_id=self.store_id,
                message=f"ML model detected unusual store pattern (score: {ml_score})",
                details={"ml_score": ml_score, "metrics": metrics},
                confidence=ml_score
            ))

        all_alerts = rule_alerts + ml_alerts

        return {
            "store_id": self.store_id,
            "timestamp": datetime.utcnow().isoformat(),
            "is_anomalous": is_anomaly or len(rule_alerts) > 0,
            "ml_score": ml_score,
            "alert_count": len(all_alerts),
            "alerts": [a.to_dict() for a in all_alerts],
            "metrics_analyzed": metrics
        }


# ── Demo ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = StoreAnomalyEngine("store_1", max_occupancy=80)

    # Normal scenario
    normal = {"footfall": 45, "transactions": 15, "occupancy": 30, "queue_length": 2, "revenue": 9750, "conversion_rate": 0.33, "billing_active": True, "billing_staffed": True}
    print("Normal:", json.dumps(engine.analyze(normal), indent=2))

    # Anomalous scenario
    anomaly = {"footfall": 72, "transactions": 2, "occupancy": 76, "queue_length": 11, "revenue": 1300, "conversion_rate": 0.03, "billing_active": False, "billing_staffed": False, "prev_hour_footfall": 65}
    print("\nAnomalous:", json.dumps(engine.analyze(anomaly), indent=2))
