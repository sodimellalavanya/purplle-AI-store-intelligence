"""
Unit tests for the CV pipeline components
Run: pytest tests/cv/test_processor.py -v
"""
import pytest
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../cv_pipeline"))

from processor import (
    Detection, TrackedPerson, HeatmapAccumulator,
    QueueEstimator, PersonCounter, StoreVideoProcessor,
    get_zone_for_point, point_in_zone, mock_detect
)


# ── Zone detection ─────────────────────────────────────────────────────────────
class TestZoneDetection:
    def test_point_in_zone_true(self):
        assert point_in_zone(500, 100, [(0, 0), (1920, 200)]) is True

    def test_point_in_zone_false(self):
        assert point_in_zone(500, 500, [(0, 0), (1920, 200)]) is False

    def test_get_zone_entrance(self):
        zone = get_zone_for_point(960, 100, "store_1")
        assert zone == "entrance"

    def test_get_zone_billing(self):
        zone = get_zone_for_point(1600, 800, "store_1")
        assert zone == "billing"

    def test_get_zone_shelves_a(self):
        zone = get_zone_for_point(400, 400, "store_1")
        assert zone == "shelves_a"

    def test_get_zone_unknown(self):
        zone = get_zone_for_point(100, 900, "store_1")
        # Restricted zone or floor
        assert zone in ("restricted", "floor")

    def test_store_2_entrance(self):
        zone = get_zone_for_point(960, 100, "store_2")
        assert zone == "entrance"

    def test_store_2_billing(self):
        zone = get_zone_for_point(1500, 850, "store_2")
        assert zone == "billing_area"


# ── Heatmap accumulator ────────────────────────────────────────────────────────
class TestHeatmapAccumulator:
    def test_initial_zero(self):
        hm = HeatmapAccumulator()
        norm = hm.get_normalized()
        assert all(v == 0.0 for row in norm for v in row)

    def test_update_increments(self):
        hm = HeatmapAccumulator(width=1920, height=1080, grid_size=20)
        hm.update(100, 100)
        assert hm.grid.max() == 1.0

    def test_normalized_max_is_one(self):
        hm = HeatmapAccumulator()
        hm.update(100, 100)
        hm.update(100, 100)
        hm.update(500, 400)
        norm = hm.get_normalized()
        flat = [v for row in norm for v in row]
        assert max(flat) == 1.0
        assert all(0.0 <= v <= 1.0 for v in flat)

    def test_reset(self):
        hm = HeatmapAccumulator()
        hm.update(100, 100)
        hm.reset()
        assert hm.grid.max() == 0.0

    def test_grid_shape(self):
        hm = HeatmapAccumulator(grid_size=20)
        norm = hm.get_normalized()
        assert len(norm) == 20
        assert len(norm[0]) == 20

    def test_boundary_clamp(self):
        hm = HeatmapAccumulator(width=1920, height=1080, grid_size=20)
        # Points at edge should not crash
        hm.update(0, 0)
        hm.update(1919, 1079)
        hm.update(1920, 1080)  # out-of-bounds clamped


# ── Queue estimator ────────────────────────────────────────────────────────────
class TestQueueEstimator:
    def make_detections(self, n, zone="billing"):
        return [Detection(track_id=i, bbox=(100, 100, 150, 250),
                          confidence=0.9, class_id=0, zone=zone) for i in range(n)]

    def test_no_queue(self):
        qe = QueueEstimator()
        result = qe.estimate([])
        assert result["queue_length"] == 0
        assert result["alert"] is False

    def test_small_queue(self):
        qe = QueueEstimator()
        result = qe.estimate(self.make_detections(3))
        assert result["queue_length"] == 3
        assert result["alert"] is False

    def test_alert_threshold(self):
        qe = QueueEstimator()
        result = qe.estimate(self.make_detections(6))
        assert result["alert"] is True

    def test_non_billing_not_counted(self):
        qe = QueueEstimator()
        detections = self.make_detections(10, zone="entrance")
        result = qe.estimate(detections)
        assert result["queue_length"] == 0

    def test_wait_time_estimate(self):
        qe = QueueEstimator()
        result = qe.estimate(self.make_detections(4))
        assert result["estimated_wait_minutes"] == pytest.approx(6.0)


# ── Person counter ─────────────────────────────────────────────────────────────
class TestPersonCounter:
    def test_initial_zero(self):
        pc = PersonCounter(line_y=180)
        assert pc.entries == 0
        assert pc.exits == 0
        assert pc.occupancy == 0

    def test_entry_detected(self):
        pc = PersonCounter(line_y=180)
        pc.update(1, 150)  # above line
        pc.update(1, 200)  # crosses line → entry
        assert pc.entries == 1
        assert pc.occupancy == 1

    def test_exit_detected(self):
        pc = PersonCounter(line_y=180)
        pc.update(1, 200)  # below line
        pc.update(1, 150)  # crosses up → exit
        assert pc.exits == 1

    def test_occupancy_cannot_go_negative(self):
        pc = PersonCounter(line_y=180)
        pc.update(1, 200)
        pc.update(1, 150)  # exit without entry
        assert pc.occupancy == 0

    def test_multiple_people(self):
        pc = PersonCounter(line_y=180)
        for tid in range(5):
            pc.update(tid, 150)
            pc.update(tid, 200)
        assert pc.entries == 5
        assert pc.occupancy == 5


# ── Store video processor ──────────────────────────────────────────────────────
class TestStoreVideoProcessor:
    def make_detection(self, track_id, cx=960, cy=100):
        x1, y1 = cx - 40, cy - 90
        return Detection(track_id=track_id, bbox=(x1, y1, x1+80, y1+180),
                         confidence=0.9, class_id=0)

    def test_processor_init(self):
        proc = StoreVideoProcessor("store_1", "entry_cam")
        stats = proc.get_stats()
        assert stats["store_id"] == "store_1"
        assert stats["camera_id"] == "entry_cam"
        assert stats["frames_processed"] == 0

    def test_process_empty_frame(self):
        proc = StoreVideoProcessor("store_1", "entry_cam")
        result = proc.process_frame(None, [])
        assert result["detections"] == 0
        assert result["frame"] == 1

    def test_new_person_tracked(self):
        proc = StoreVideoProcessor("store_1", "entry_cam")
        det = self.make_detection(track_id=1)
        proc.process_frame(None, [det])
        assert 1 in proc.tracked_persons

    def test_events_fired(self):
        events = []
        proc = StoreVideoProcessor("store_1", "entry_cam",
                                   event_callback=lambda e: events.append(e))
        det = self.make_detection(track_id=10)
        proc.process_frame(None, [det])
        # Should fire customer_entered
        assert any(e["event_type"] == "customer_entered" for e in events)

    def test_zone_tracking(self):
        proc = StoreVideoProcessor("store_1", "entry_cam")
        det = self.make_detection(track_id=5, cx=960, cy=100)
        proc.process_frame(None, [det])
        assert "entrance" in proc.tracked_persons[5].zones_visited

    def test_multi_frame_tracking(self):
        proc = StoreVideoProcessor("store_1", "entry_cam")
        for i in range(10):
            det = self.make_detection(track_id=99, cx=960, cy=100+i*10)
            proc.process_frame(None, [det])
        assert proc.frame_count == 10
        assert 99 in proc.tracked_persons

    def test_mock_detect_returns_list(self):
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detections = mock_detect(frame)
        assert isinstance(detections, list)
        for d in detections:
            assert isinstance(d, Detection)
            assert 0.0 <= d.confidence <= 1.0
