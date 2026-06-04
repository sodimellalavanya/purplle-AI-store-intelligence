"""
Database models using Motor (async MongoDB driver)
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


# ── Store ──────────────────────────────────────────────────
class StoreModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    store_id: str
    name: str
    location: str
    max_occupancy: int
    cameras: List[str] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# ── Camera ─────────────────────────────────────────────────
class CameraModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    camera_id: str
    store_id: str
    zone: str
    stream_url: Optional[str] = None
    is_active: bool = True
    last_seen: Optional[datetime] = None
    resolution: str = "1080p"
    fps: int = 30

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# ── Store Event ────────────────────────────────────────────
class StoreEvent(BaseModel):
    event_id: str
    timestamp: datetime
    store_id: str
    camera_id: str
    person_id: Optional[str] = None
    event_type: str
    zone: str
    confidence: float
    metadata: Dict[str, Any] = {}
    processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Transaction ────────────────────────────────────────────
class Transaction(BaseModel):
    transaction_id: str
    store_id: str
    timestamp: datetime
    cashier_id: str
    customer_id: Optional[str] = None
    items_count: int
    total_amount: float
    payment_method: str
    duration_seconds: int
    zone: str


# ── Alert ──────────────────────────────────────────────────
class Alert(BaseModel):
    alert_id: str
    store_id: str
    camera_id: Optional[str] = None
    alert_type: str
    severity: str  # low, medium, high, critical
    message: str
    details: Dict[str, Any] = {}
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Analytics Snapshot ─────────────────────────────────────
class AnalyticsSnapshot(BaseModel):
    store_id: str
    timestamp: datetime
    occupancy: int
    footfall: int
    transactions: int
    conversion_rate: float
    avg_dwell_time: float
    queue_length: int
    revenue: float
    hour: int = 0
    day: int = 0

    class Config:
        arbitrary_types_allowed = True


# ── Heatmap Data ───────────────────────────────────────────
class HeatmapData(BaseModel):
    store_id: str
    date: str
    zone_counts: Dict[str, int] = {}
    grid_data: List[List[float]] = []
    peak_zones: List[str] = []
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ── Staff Activity ─────────────────────────────────────────
class StaffActivity(BaseModel):
    staff_id: str
    store_id: str
    camera_id: str
    zone: str
    status: str  # active, idle, missing
    last_seen: datetime
    idle_duration: int = 0  # seconds
