"""
Logging configuration for payment service
"""
import sys
import logging
import structlog
from payment.config import config


def setup_logging():
    """Configure structured logging with structlog"""
    
    # Set log level
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False
    )
    
    logger = structlog.get_logger()
    logger.info(
        "Logging configured",
        service=config.service_name,
        log_level=config.log_level
    )
