"""
Entry point for Payment Service
"""
import sys
import os

# Add parent directory to path to import payment package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from payment.grpc_server import create_grpc_server
from payment.health_http import start_health_http_server
from payment.logging import setup_logging
import structlog


def main():
    """Main entry point"""
    # Setup logging
    setup_logging()
    logger = structlog.get_logger()
    
    logger.info(" Starting Payment Service")
    
    # Start HTTP health check server in background thread
    try:
        start_health_http_server()
    except Exception as e:
        logger.error("Failed to start HTTP health server", error=str(e))
        sys.exit(1)
    
    # Start gRPC server (blocking)
    try:
        create_grpc_server()
    except KeyboardInterrupt:
        logger.info("Payment Service stopped by user")
    except Exception as e:
        logger.error("Payment Service failed", error=str(e))
        sys.exit(1)


if __name__ == '__main__':
    main()
