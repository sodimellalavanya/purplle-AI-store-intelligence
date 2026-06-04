"""
CV Pipeline Main — Processes video streams with YOLOv8 + ByteTrack
Produces detection events to Kafka
"""
import cv2
import json
import uuid
import logging
import asyncio
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Data Classes ───────────────────────────────────────────────────────────────
@dataclass
class Detection:
    track_id: int
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    class_id: int  # 0=person
    zone: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TrackedPerson:
    track_id: int
    entry_time: datetime
    last_seen: datetime
    zones_visited: List[str] = field(default_factory=list)
    trajectory: List[Tuple[int, int]] = field(default_factory=list)
    is_staff: bool = False


# ── Zone Definitions ───────────────────────────────────────────────────────────
STORE_ZONES = {
    "store_1": {
        "entrance":   [(0, 0), (1920, 200)],        # top strip
        "shelves_a":  [(0, 200), (960, 700)],        # left mid
        "shelves_b":  [(960, 200), (1920, 700)],     # right mid
        "billing":    [(1400, 700), (1920, 1080)],   # bottom right
        "restricted": [(0, 700), (400, 1080)],       # bottom left
    },
    "store_2": {
        "entrance":   [(0, 0), (1920, 200)],
        "shelves_main": [(200, 200), (1720, 700)],
        "billing_area": [(1200, 700), (1920, 1080)],
        "restricted": [(0, 700), (400, 1080)],
    }
}


def point_in_zone(cx: int, cy: int, zone_rect: List[Tuple[int, int]]) -> bool:
    """Check if center point falls within zone rectangle"""
    (x1, y1), (x2, y2) = zone_rect
    return x1 <= cx <= x2 and y1 <= cy <= y2


def get_zone_for_point(cx: int, cy: int, store_id: str) -> str:
    zones = STORE_ZONES.get(store_id, {})
    for zone_name, rect in zones.items():
        if point_in_zone(cx, cy, rect):
            return zone_name
    return "floor"


# ── Heatmap Accumulator ────────────────────────────────────────────────────────
class HeatmapAccumulator:
    def __init__(self, width: int = 1920, height: int = 1080, grid_size: int = 20):
        self.grid_size = grid_size
        self.cell_w = width // grid_size
        self.cell_h = height // grid_size
        self.grid = np.zeros((grid_size, grid_size), dtype=np.float32)

    def update(self, cx: int, cy: int):
        col = min(cx // self.cell_w, self.grid_size - 1)
        row = min(cy // self.cell_h, self.grid_size - 1)
        self.grid[row][col] += 1

    def get_normalized(self) -> List[List[float]]:
        max_val = self.grid.max()
        if max_val == 0:
            return self.grid.tolist()
        return (self.grid / max_val).tolist()

    def reset(self):
        self.grid = np.zeros((self.grid_size, self.grid_size), dtype=np.float32)


# ── Queue Estimator ────────────────────────────────────────────────────────────
class QueueEstimator:
    def __init__(self, billing_zone: str = "billing"):
        self.billing_zone = billing_zone
        self.queue_history: List[int] = []

    def estimate(self, detections: List[Detection]) -> Dict:
        billing_count = sum(1 for d in detections if d.zone == self.billing_zone)
        self.queue_history.append(billing_count)
        if len(self.queue_history) > 60:
            self.queue_history.pop(0)

        avg = sum(self.queue_history) / len(self.queue_history)
        wait_minutes = billing_count * 1.5  # ~1.5 min per person

        return {
            "queue_length": billing_count,
            "avg_queue_1min": round(avg, 1),
            "estimated_wait_minutes": round(wait_minutes, 1),
            "alert": billing_count >= 5
        }


# ── Person Counter ─────────────────────────────────────────────────────────────
class PersonCounter:
    """Tracks entry/exit via virtual line crossing"""

    def __init__(self, line_y: int = 180):
        self.line_y = line_y
        self.tracked: Dict[int, int] = {}  # track_id -> last_y
        self.entries = 0
        self.exits = 0

    def update(self, track_id: int, cy: int):
        if track_id in self.tracked:
            prev_y = self.tracked[track_id]
            if prev_y < self.line_y <= cy:
                self.entries += 1
            elif prev_y > self.line_y >= cy:
                self.exits += 1
        self.tracked[track_id] = cy

    @property
    def occupancy(self) -> int:
        return max(0, self.entries - self.exits)


# ── Main CV Processor ──────────────────────────────────────────────────────────
class StoreVideoProcessor:
    """
    Processes a single camera stream.
    Uses YOLOv8 for detection + simple IoU-based tracking (ByteTrack-style).
    In production: use ultralytics with ByteTrack integration.
    """

    def __init__(self, store_id: str, camera_id: str, event_callback=None):
        self.store_id = store_id
        self.camera_id = camera_id
        self.event_callback = event_callback
        self.counter = PersonCounter()
        self.heatmap = HeatmapAccumulator()
        self.queue = QueueEstimator()
        self.tracked_persons: Dict[int, TrackedPerson] = {}
        self.frame_count = 0

        logger.info(f"[{camera_id}] CV Processor initialized for {store_id}")

    def process_frame(self, frame: np.ndarray, detections: List[Detection]) -> Dict:
        """Process detections from one frame and emit events"""
        self.frame_count += 1
        events = []

        for det in detections:
            cx = (det.bbox[0] + det.bbox[2]) // 2
            cy = (det.bbox[1] + det.bbox[3]) // 2
            det.zone = get_zone_for_point(cx, cy, self.store_id)

            # Update heatmap
            self.heatmap.update(cx, cy)

            # Update entry/exit counter
            self.counter.update(det.track_id, cy)

            # Track person
            if det.track_id not in self.tracked_persons:
                self.tracked_persons[det.track_id] = TrackedPerson(
                    track_id=det.track_id,
                    entry_time=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    zones_visited=[det.zone]
                )
                events.append(self._make_event("customer_entered", det, {"zone": det.zone}))
            else:
                person = self.tracked_persons[det.track_id]
                person.last_seen = datetime.utcnow()
                person.trajectory.append((cx, cy))
                if det.zone not in person.zones_visited:
                    person.zones_visited.append(det.zone)
                    events.append(self._make_event("zone_entered", det, {"zone": det.zone}))

        # Queue analysis every 30 frames
        if self.frame_count % 30 == 0:
            q_info = self.queue.estimate(detections)
            if q_info["alert"]:
                events.append({
                    "event_id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat(),
                    "store_id": self.store_id,
                    "camera_id": self.camera_id,
                    "person_id": None,
                    "event_type": "queue_increased",
                    "zone": "billing",
                    "confidence": 0.88,
                    "metadata": q_info
                })

        # Fire events
        if self.event_callback:
            for evt in events:
                self.event_callback(evt)

        return {
            "frame": self.frame_count,
            "detections": len(detections),
            "occupancy": self.counter.occupancy,
            "entries": self.counter.entries,
            "exits": self.counter.exits,
            "events_produced": len(events),
        }

    def _make_event(self, event_type: str, det: Detection, metadata: dict) -> dict:
        return {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "person_id": f"track_{det.track_id:03d}",
            "event_type": event_type,
            "zone": det.zone,
            "confidence": round(det.confidence, 3),
            "metadata": metadata
        }

    def get_stats(self) -> Dict:
        return {
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "frames_processed": self.frame_count,
            "total_tracked": len(self.tracked_persons),
            "current_occupancy": self.counter.occupancy,
            "entries": self.counter.entries,
            "exits": self.counter.exits,
            "heatmap": self.heatmap.get_normalized(),
        }


# ── YOLO Mock (for environments without GPU) ───────────────────────────────────
def mock_detect(frame: np.ndarray) -> List[Detection]:
    """
    Mock detector — in production replace with:
        from ultralytics import YOLO
        model = YOLO('yolov8n.pt')
        results = model.track(frame, persist=True, tracker='bytetrack.yaml')
    """
    import random
    count = random.randint(0, 8)
    h, w = frame.shape[:2] if frame is not None else (1080, 1920)
    detections = []
    for i in range(count):
        x1 = random.randint(0, w - 100)
        y1 = random.randint(0, h - 200)
        detections.append(Detection(
            track_id=random.randint(1, 50),
            bbox=(x1, y1, x1 + 80, y1 + 180),
            confidence=round(random.uniform(0.65, 0.98), 2),
            class_id=0
        ))
    return detections


def run_on_video(video_path: str, store_id: str, camera_id: str, max_frames: int = 300):
    """
    Process a video file through the CV pipeline.
    Writes events to stdout (pipe to Kafka producer in production).
    """
    processor = StoreVideoProcessor(store_id, camera_id,
                                     event_callback=lambda e: print(json.dumps(e)))

    cap = cv2.VideoCapture(video_path) if video_path else None

    for i in range(max_frames):
        frame = None
        if cap and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

        detections = mock_detect(frame)
        stats = processor.process_frame(frame, detections)

        if i % 100 == 0:
            logger.info(f"[{camera_id}] Frame {i}: {stats}")

    if cap:
        cap.release()

    return processor.get_stats()


if __name__ == "__main__":
    import sys
    video = sys.argv[1] if len(sys.argv) > 1 else None
    stats = run_on_video(video, "store_1", "entry_cam", max_frames=100)
    print(json.dumps(stats, indent=2))
