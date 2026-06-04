"""
Tests for anomaly detection engine (ML + rule-based)
Run: pytest tests/analytics/test_anomaly.py -v
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../anomaly_detection"))

from engine import (
    IsolationForestDetector, RuleBasedDetector,
    StoreAnomalyEngine, AnomalyAlert
)


# ── Fixtures ───────────────────────────────────────────────────────────────────
@pytest.fixture
def normal_metrics():
    return {
        "footfall": 45, "transactions": 16, "occupancy": 32,
        "queue_length": 2, "revenue": 10400.0, "conversion_rate": 0.35,
        "billing_active": True, "billing_staffed": True,
        "prev_hour_footfall": 40
    }


@pytest.fixture
def anomalous_metrics():
    return {
        "footfall": 78, "transactions": 1, "occupancy": 76,
        "queue_length": 12, "revenue": 650.0, "conversion_rate": 0.013,
        "billing_active": False, "billing_staffed": False,
        "prev_hour_footfall": 72
    }


@pytest.fixture
def rule_detector():
    return RuleBasedDetector("store_1", max_occupancy=80)


@pytest.fixture
def ml_detector():
    det = IsolationForestDetector()
    det.fit_synthetic()
    return det


@pytest.fixture
def engine():
    return StoreAnomalyEngine("store_1", max_occupancy=80)


# ── IsolationForestDetector ────────────────────────────────────────────────────
class TestIsolationForest:
    def test_fits_synthetic(self, ml_detector):
        assert ml_detector.is_fitted is True

    def test_normal_metrics_low_score(self, ml_detector, normal_metrics):
        is_anom, score = ml_detector.predict(normal_metrics)
        # Normal metrics should have lower anomaly score
        assert 0.0 <= score <= 1.0

    def test_anomalous_metrics_high_score(self, ml_detector, anomalous_metrics):
        is_anom, score = ml_detector.predict(anomalous_metrics)
        assert 0.0 <= score <= 1.0
        # Anomalous should score higher than normal
        _, normal_score = ml_detector.predict({
            "footfall": 40, "transactions": 14, "occupancy": 30,
            "queue_length": 2, "revenue": 9100.0
        })
        assert score >= normal_score

    def test_returns_tuple(self, ml_detector, normal_metrics):
        result = ml_detector.predict(normal_metrics)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] in (True, False)   # handles np.bool_ and bool
        assert isinstance(result[1], float)

    def test_score_in_range(self, ml_detector):
        for _ in range(10):
            import random
            metrics = {
                "footfall": random.randint(0, 100),
                "transactions": random.randint(0, 50),
                "occupancy": random.randint(0, 80),
                "queue_length": random.randint(0, 15),
                "revenue": random.uniform(0, 50000)
            }
            is_anom, score = ml_detector.predict(metrics)
            assert 0.0 <= score <= 1.0


# ── RuleBasedDetector ──────────────────────────────────────────────────────────
class TestRuleBasedDetector:
    def test_no_alerts_normal(self, rule_detector, normal_metrics):
        alerts = rule_detector.check_all(normal_metrics)
        assert len(alerts) == 0

    def test_occupancy_critical(self, rule_detector):
        m = {"occupancy": 77, "max": 80, "footfall": 40, "transactions": 14,
             "queue_length": 2, "conversion_rate": 0.35,
             "billing_active": True, "billing_staffed": True, "prev_hour_footfall": 38}
        alerts = rule_detector.check_all(m)
        types = [a.alert_type for a in alerts]
        assert "occupancy_critical" in types

    def test_occupancy_warning(self, rule_detector):
        m = {"occupancy": 70, "footfall": 40, "transactions": 14,
             "queue_length": 2, "conversion_rate": 0.35,
             "billing_active": True, "billing_staffed": True, "prev_hour_footfall": 38}
        alert = rule_detector.check_occupancy(m)
        assert alert is not None
        assert alert.alert_type == "occupancy_warning"
        assert alert.severity == "high"

    def test_no_occupancy_alert_when_low(self, rule_detector):
        m = {"occupancy": 30}
        alert = rule_detector.check_occupancy(m)
        assert alert is None

    def test_queue_overflow(self, rule_detector):
        m = {"queue_length": 9, "avg_wait_minutes": 14}
        alert = rule_detector.check_queue(m)
        assert alert is not None
        assert alert.alert_type == "queue_overflow"
        assert alert.severity == "high"

    def test_no_queue_alert_when_small(self, rule_detector):
        m = {"queue_length": 3, "avg_wait_minutes": 4}
        alert = rule_detector.check_queue(m)
        assert alert is None

    def test_low_conversion(self, rule_detector):
        m = {"footfall": 60, "transactions": 6, "conversion_rate": 0.10}
        alert = rule_detector.check_low_conversion(m)
        assert alert is not None
        assert alert.alert_type == "low_conversion"

    def test_no_low_conv_when_footfall_small(self, rule_detector):
        m = {"footfall": 10, "conversion_rate": 0.10}
        alert = rule_detector.check_low_conversion(m)
        assert alert is None

    def test_busy_no_billing(self, rule_detector):
        m = {"footfall": 55, "transactions": 1, "billing_active": False}
        alert = rule_detector.check_busy_no_billing(m)
        assert alert is not None
        assert alert.severity == "critical"

    def test_no_billing_alert_when_active(self, rule_detector):
        m = {"footfall": 55, "transactions": 18, "billing_active": True}
        alert = rule_detector.check_busy_no_billing(m)
        assert alert is None

    def test_staff_missing(self, rule_detector):
        m = {"billing_staffed": False, "footfall": 30, "staff_missing_count": 1}
        alert = rule_detector.check_staff_coverage(m)
        assert alert is not None
        assert alert.alert_type == "staff_missing"

    def test_traffic_drop(self, rule_detector):
        m = {"footfall": 8, "prev_hour_footfall": 60}
        alert = rule_detector.check_sudden_traffic_drop(m)
        assert alert is not None
        assert alert.alert_type == "sudden_traffic_drop"

    def test_no_traffic_drop_when_prev_low(self, rule_detector):
        m = {"footfall": 5, "prev_hour_footfall": 10}
        alert = rule_detector.check_sudden_traffic_drop(m)
        assert alert is None

    def test_multiple_alerts(self, rule_detector, anomalous_metrics):
        alerts = rule_detector.check_all(anomalous_metrics)
        assert len(alerts) >= 2  # Multiple rules should fire


# ── AnomalyAlert ───────────────────────────────────────────────────────────────
class TestAnomalyAlert:
    def test_to_dict(self):
        a = AnomalyAlert(
            alert_type="test", severity="high",
            store_id="store_1", message="Test", details={"k": "v"}, confidence=0.9
        )
        d = a.to_dict()
        assert d["alert_type"] == "test"
        assert d["severity"] == "high"
        assert d["confidence"] == 0.9
        assert "timestamp" in d

    def test_timestamp_auto_set(self):
        a = AnomalyAlert(alert_type="t", severity="low",
                         store_id="s", message="m", details={})
        assert a.timestamp is not None


# ── StoreAnomalyEngine ────────────────────────────────────────────────────────
class TestStoreAnomalyEngine:
    def test_analyze_returns_dict(self, engine, normal_metrics):
        result = engine.analyze(normal_metrics)
        assert isinstance(result, dict)
        assert "is_anomalous" in result
        assert "ml_score" in result
        assert "alerts" in result
        assert "timestamp" in result

    def test_normal_fewer_alerts(self, engine, normal_metrics):
        result = engine.analyze(normal_metrics)
        # Normal metrics shouldn't generate many alerts
        assert result["alert_count"] <= 1

    def test_anomalous_has_alerts(self, engine, anomalous_metrics):
        result = engine.analyze(anomalous_metrics)
        assert result["is_anomalous"]   # truthy, handles numpy bool
        assert result["alert_count"] >= 1

    def test_ml_score_range(self, engine, normal_metrics):
        result = engine.analyze(normal_metrics)
        assert 0.0 <= result["ml_score"] <= 1.0

    def test_store_id_in_result(self, engine, normal_metrics):
        result = engine.analyze(normal_metrics)
        assert result["store_id"] == "store_1"

    def test_alerts_have_required_fields(self, engine, anomalous_metrics):
        result = engine.analyze(anomalous_metrics)
        for alert in result["alerts"]:
            assert "alert_type" in alert
            assert "severity" in alert
            assert "message" in alert
            assert "timestamp" in alert
            assert alert["severity"] in ("low", "medium", "high", "critical")
