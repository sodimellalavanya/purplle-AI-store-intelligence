"""
Backend API tests using pytest + httpx (async)
Run: pytest tests/backend/test_api.py -v
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch

BASE_URL = "http://localhost:8000"

# ── Fixtures ───────────────────────────────────────────────────────────────────
@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=10.0)


# ── Health ─────────────────────────────────────────────────────────────────────
class TestHealth:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "operational"
        assert "version" in data

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "services" in data


# ── Stores ─────────────────────────────────────────────────────────────────────
class TestStores:
    def test_list_stores(self, client):
        r = client.get("/stores/")
        assert r.status_code == 200
        data = r.json()
        assert "stores" in data
        assert data["total"] == 2
        ids = [s["store_id"] for s in data["stores"]]
        assert "store_1" in ids
        assert "store_2" in ids

    def test_get_store_1(self, client):
        r = client.get("/stores/store_1")
        assert r.status_code == 200
        data = r.json()
        assert data["store_id"] == "store_1"
        assert data["max_occupancy"] == 80
        assert len(data["cameras"]) > 0

    def test_get_store_2(self, client):
        r = client.get("/stores/store_2")
        assert r.status_code == 200
        data = r.json()
        assert data["store_id"] == "store_2"
        assert data["max_occupancy"] == 50

    def test_store_not_found(self, client):
        r = client.get("/stores/store_99")
        assert r.status_code == 404

    def test_store_metrics(self, client):
        r = client.get("/stores/store_1/metrics")
        assert r.status_code == 200
        data = r.json()
        assert "live" in data
        assert "today" in data
        assert "occupancy" in data["live"]
        assert "footfall" in data["today"]
        assert "conversion_rate" in data["today"]
        assert 0.0 <= data["today"]["conversion_rate"] <= 1.0

    def test_store_occupancy_default(self, client):
        r = client.get("/stores/store_1/occupancy")
        assert r.status_code == 200
        data = r.json()
        assert "timeline" in data
        assert len(data["timeline"]) == 24  # default 24 hours
        assert data["max_occupancy"] == 80

    def test_store_occupancy_custom_hours(self, client):
        r = client.get("/stores/store_1/occupancy?hours=12")
        assert r.status_code == 200
        data = r.json()
        assert len(data["timeline"]) == 12

    def test_store_footfall_today(self, client):
        r = client.get("/stores/store_1/footfall?period=today")
        assert r.status_code == 200
        data = r.json()
        assert data["period"] == "today"
        assert len(data["data"]) > 0

    def test_store_footfall_week(self, client):
        r = client.get("/stores/store_2/footfall?period=week")
        assert r.status_code == 200
        data = r.json()
        assert data["period"] == "week"
        assert len(data["data"]) == 7

    def test_store_metrics_invalid(self, client):
        r = client.get("/stores/invalid_store/metrics")
        assert r.status_code == 404


# ── Cameras ────────────────────────────────────────────────────────────────────
class TestCameras:
    def test_list_all_cameras(self, client):
        r = client.get("/cameras/")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 10
        assert "active" in data
        assert "offline" in data

    def test_list_cameras_store_1(self, client):
        r = client.get("/cameras/?store_id=store_1")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 5
        for cam in data["cameras"]:
            assert cam["store_id"] == "store_1"

    def test_get_camera_detail(self, client):
        r = client.get("/cameras/entry_cam")
        assert r.status_code == 200
        data = r.json()
        assert data["camera_id"] == "entry_cam"
        assert data["store_id"] == "store_1"
        assert "fps" in data
        assert "resolution" in data

    def test_camera_not_found(self, client):
        r = client.get("/cameras/nonexistent_cam")
        assert r.status_code == 404

    def test_camera_events(self, client):
        r = client.get("/cameras/billing_cam/events?limit=10")
        assert r.status_code == 200
        data = r.json()
        assert "events" in data
        assert len(data["events"]) == 10
        for evt in data["events"]:
            assert "event_id" in evt
            assert "timestamp" in evt
            assert "event_type" in evt
            assert evt["camera_id"] == "billing_cam"

    def test_camera_events_filter(self, client):
        r = client.get("/cameras/entry_cam/events?event_type=customer_entered&limit=5")
        assert r.status_code == 200
        data = r.json()
        for evt in data["events"]:
            assert evt["event_type"] == "customer_entered"


# ── Analytics ──────────────────────────────────────────────────────────────────
class TestAnalytics:
    def test_heatmap(self, client):
        r = client.get("/analytics/heatmap?store_id=store_1")
        assert r.status_code == 200
        data = r.json()
        assert data["store_id"] == "store_1"
        assert data["grid_size"] == "20x20"
        assert len(data["grid"]) == 20
        assert len(data["grid"][0]) == 20
        # All values 0–1
        for row in data["grid"]:
            for val in row:
                assert 0.0 <= val <= 1.0

    def test_conversion_rate(self, client):
        r = client.get("/analytics/conversion-rate?store_id=store_1")
        assert r.status_code == 200
        data = r.json()
        assert "store_1" in data
        store_data = data["store_1"]
        assert "overall_conversion" in store_data
        assert "hourly_breakdown" in store_data
        assert 0.0 <= store_data["overall_conversion"] <= 1.0

    def test_conversion_rate_both_stores(self, client):
        r = client.get("/analytics/conversion-rate")
        assert r.status_code == 200
        data = r.json()
        assert "store_1" in data
        assert "store_2" in data

    def test_queue_analysis(self, client):
        r = client.get("/analytics/queue?store_id=store_1&hours=8")
        assert r.status_code == 200
        data = r.json()
        assert data["store_id"] == "store_1"
        assert len(data["timeline"]) == 8
        assert "avg_queue_length" in data
        assert "max_queue_length" in data

    def test_sales_correlation(self, client):
        r = client.get("/analytics/sales-correlation?store_id=store_2")
        assert r.status_code == 200
        data = r.json()
        assert "correlation" in data
        assert "anomalies_detected" in data
        assert "total_revenue" in data
        assert data["total_revenue"] >= 0

    def test_dwell_time(self, client):
        r = client.get("/analytics/dwell-time?store_id=store_1")
        assert r.status_code == 200
        data = r.json()
        assert "zones" in data
        assert "total_avg_dwell_minutes" in data
        assert data["total_avg_dwell_minutes"] > 0

    def test_staff_activity(self, client):
        r = client.get("/analytics/staff-activity?store_id=store_1")
        assert r.status_code == 200
        data = r.json()
        assert "staff_summary" in data
        assert "active_count" in data
        assert "missing_count" in data


# ── Alerts ─────────────────────────────────────────────────────────────────────
class TestAlerts:
    def test_list_alerts(self, client):
        r = client.get("/alerts/")
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data
        assert "total" in data
        assert "by_severity" in data

    def test_alerts_filter_by_store(self, client):
        r = client.get("/alerts/?store_id=store_1")
        assert r.status_code == 200
        data = r.json()
        for alert in data["alerts"]:
            assert alert["store_id"] == "store_1"

    def test_alerts_filter_by_severity(self, client):
        r = client.get("/alerts/?severity=critical")
        assert r.status_code == 200
        data = r.json()
        for alert in data["alerts"]:
            assert alert["severity"] == "critical"

    def test_alert_summary(self, client):
        r = client.get("/alerts/summary")
        assert r.status_code == 200
        data = r.json()
        assert "total_alerts" in data
        assert "unacknowledged" in data
        assert "by_store" in data

    def test_acknowledge_alert(self, client):
        r = client.post("/alerts/alert_001/acknowledge",
                        json={"acknowledged_by": "test_manager", "note": "Checked, resolved"})
        # May already be acknowledged in some test orders — accept 200 or 400
        assert r.status_code in (200, 400)

    def test_acknowledge_nonexistent(self, client):
        r = client.post("/alerts/alert_999/acknowledge",
                        json={"acknowledged_by": "test_manager"})
        assert r.status_code == 404

    def test_create_alert(self, client):
        r = client.post("/alerts/",
                        params={"store_id": "store_1", "alert_type": "test_alert",
                                "severity": "low", "message": "Test alert from pytest"})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["alert"]["alert_type"] == "test_alert"


# ── Events ─────────────────────────────────────────────────────────────────────
class TestEvents:
    def test_recent_events(self, client):
        r = client.get("/events/recent?limit=10")
        assert r.status_code == 200
        data = r.json()
        assert "events" in data
        assert len(data["events"]) == 10
        for evt in data["events"]:
            assert "event_id" in evt
            assert "event_type" in evt
            assert "store_id" in evt

    def test_event_stats(self, client):
        r = client.get("/events/stats")
        assert r.status_code == 200
        data = r.json()
        assert "event_counts" in data
        assert "total_events" in data
        assert data["total_events"] > 0


# ── Dashboard ──────────────────────────────────────────────────────────────────
class TestDashboard:
    def test_overview(self, client):
        r = client.get("/dashboard/overview")
        assert r.status_code == 200
        data = r.json()
        assert "stores" in data
        assert "store_1" in data["stores"]
        assert "store_2" in data["stores"]
        assert "charts" in data
        assert "system_status" in data
        s1 = data["stores"]["store_1"]
        assert "occupancy" in s1
        assert "footfall_today" in s1
        assert "conversion_rate" in s1
        assert 0.0 <= s1["conversion_rate"] <= 1.0
