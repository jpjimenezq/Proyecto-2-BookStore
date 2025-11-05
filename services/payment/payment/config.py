"""
Configuration management for payment service
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Service configuration loaded from environment variables"""
    
    # Service
    service_name: str = "payment"
    grpc_port: int = 50056
    http_health_port: int = 8084
    log_level: str = "INFO"
    
    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "bookstore.events"
    rabbitmq_prefetch_count: int = 10
    rabbitmq_retry_max_attempts: int = 3
    rabbitmq_retry_initial_delay: float = 0.1
    rabbitmq_retry_max_delay: float = 5.0
    
    # External Services
    order_service_url: str = "localhost:50053"
    
    # Payment Processor
    payment_processor: str = "mock"  # mock, stripe, paypal
    mock_processor_latency: float = 0.5  # seconds
    mock_processor_max_amount: int = 100000  # cents (1000 USD)
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
config = Config()
