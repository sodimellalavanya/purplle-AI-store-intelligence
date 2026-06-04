"""
Configuration management using Pydantic Settings v2
All values can be overridden via environment variables or a .env file
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # App
    APP_NAME: str = "Store Intelligence System"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database (MongoDB)
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "store_intelligence"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP: str = "store-intelligence-group"
    KAFKA_TOPICS: List[str] = [
        "store-events",
        "cv-detections",
        "anomaly-alerts",
        "pos-transactions"
    ]

    # Redis (for caching)
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 60

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    # CV Pipeline
    CV_SERVICE_URL: str = "http://localhost:8001"
    YOLO_MODEL: str = "yolov8n.pt"
    CONFIDENCE_THRESHOLD: float = 0.5

    # Anomaly Detection
    ANOMALY_SERVICE_URL: str = "http://localhost:8002"
    OCCUPANCY_MAX_STORE_1: int = 80
    OCCUPANCY_MAX_STORE_2: int = 50
    QUEUE_THRESHOLD: int = 5
    LOW_CONVERSION_THRESHOLD: float = 0.2

    # JWT
    SECRET_KEY: str = "purplle-store-intelligence-secret-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
