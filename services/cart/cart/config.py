"""
Configuration management for cart service
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Service configuration loaded from environment variables"""
    
    # Service
    service_name: str = "cart"
    grpc_port: int = 50052
    http_health_port: int = 8081
    log_level: str = "INFO"
    
    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "cartdb"
    mongo_timeout_ms: int = 5000
    
    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "bookstore.events"
    rabbitmq_cart_exchange: str = "cart.events"
    rabbitmq_prefetch_count: int = 10
    rabbitmq_retry_max_attempts: int = 3
    rabbitmq_retry_initial_delay: float = 0.1
    rabbitmq_retry_max_delay: float = 5.0
    
    # Event processing
    event_ttl_seconds: int = 86400  # 24 hours for idempotency tracking
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create configuration singleton"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def load_config() -> Config:
    """Load configuration from environment"""
    return get_config()





