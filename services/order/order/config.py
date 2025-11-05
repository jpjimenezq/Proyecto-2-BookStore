"""
Configuration management for Order service
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Order service configuration"""
    
    # Service info
    service_name: str = "order"
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://bookstore:changeme@localhost:5433/orderdb"
    )
    
    # gRPC
    grpc_port: int = int(os.getenv("GRPC_PORT", "50053"))
    
    # HTTP Health
    http_health_port: int = int(os.getenv("HTTP_HEALTH_PORT", "8082"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


def load_config() -> Config:
    """Load configuration from environment"""
    return Config()


