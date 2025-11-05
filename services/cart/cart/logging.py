"""
Structured logging configuration using structlog
"""
import logging
import sys
import structlog
from typing import Any, Dict


def configure_logging(service_name: str, log_level: str = "INFO") -> structlog.BoundLogger:
    """
    Configure structured logging with JSON output
    
    Args:
        service_name: Name of the service for log context
        log_level: Logging level (DEBUG, INFO, WARN, ERROR)
    
    Returns:
        Configured logger instance
    """
    # Convert log level string to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
    
    # Create and configure logger
    logger = structlog.get_logger()
    logger = logger.bind(service=service_name)
    
    return logger


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a logger instance with optional name binding"""
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(logger=name)
    return logger


def add_correlation_id(logger: structlog.BoundLogger, correlation_id: str) -> structlog.BoundLogger:
    """Add correlation ID to logger context"""
    return logger.bind(correlation_id=correlation_id)




