#!/usr/bin/env python3
"""
Cart Service orchestration - starts gRPC server, Flask HTTP server, and event consumer
"""
import signal
import sys
import threading
import time
from typing import Optional

import structlog

# Add parent directory to path for imports
sys.path.insert(0, '/app')

from cart.config import load_config
from cart.logging import configure_logging
from cart.db import MongoDB, CartRepository
from cart.service import CartService
from cart.grpc_server import create_grpc_server
from cart.health_http import create_health_app
from cart.events.publisher import EventPublisher
from cart.events.consumer import EventConsumer


# Global instances for graceful shutdown
grpc_server = None
flask_thread: Optional[threading.Thread] = None
consumer: Optional[EventConsumer] = None
mongodb: Optional[MongoDB] = None
event_publisher: Optional[EventPublisher] = None
shutdown_event = threading.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal", signal=signum)
    shutdown_event.set()
    shutdown()


def shutdown():
    """Graceful shutdown of all components"""
    logger.info("Starting graceful shutdown...")
    
    # Stop gRPC server
    if grpc_server:
        logger.info("Stopping gRPC server...")
        grpc_server.stop(grace=30)
    
    # Stop event consumer
    if consumer:
        logger.info("Stopping event consumer...")
        consumer.stop()
    
    # Close event publisher
    if event_publisher:
        logger.info("Closing event publisher...")
        event_publisher.close()
    
    # Close MongoDB
    if mongodb:
        logger.info("Closing MongoDB connection...")
        mongodb.close()
    
    logger.info("Shutdown complete")


def run_flask(app, host: str, port: int):
    """Run Flask app in gunicorn-like simple server"""
    try:
        from werkzeug.serving import run_simple
        run_simple(
            host,
            port,
            app,
            use_reloader=False,
            use_debugger=False,
            threaded=True
        )
    except Exception as e:
        logger.error("Flask server error", error=str(e))


def main():
    """Main entry point"""
    global grpc_server, flask_thread, consumer, mongodb, event_publisher, logger
    
    # Load configuration
    config = load_config()
    
    # Configure logging
    logger = configure_logging(config.service_name, config.log_level)
    logger.info("Starting Cart Service", version="1.0.0")
    
    try:
        # Initialize MongoDB
        logger.info("Connecting to MongoDB...")
        mongodb = MongoDB(config)
        mongodb.connect()
        
        # Initialize repository and service
        repository = CartRepository(mongodb)
        cart_service = CartService(repository)
        logger.info("Cart service initialized")
        
        # Initialize event publisher
        logger.info("Connecting to RabbitMQ for publishing...")
        event_publisher = EventPublisher(config)
        
        # Initialize event consumer
        logger.info("Connecting to RabbitMQ for consuming...")
        consumer = EventConsumer(config, cart_service)
        
        # Create and start gRPC server
        logger.info("Starting gRPC server...", port=config.grpc_port)
        grpc_server = create_grpc_server(cart_service, event_publisher, config.grpc_port)
        
        # Define function to run gRPC server with wait_for_termination and exception handling
        def run_grpc_server():
            try:
                grpc_server.start()
                logger.info("gRPC server start() completed, waiting for termination...")
                grpc_server.wait_for_termination()
                logger.info("gRPC server wait_for_termination() completed")
            except Exception as e:
                logger.error("gRPC server exception", error=str(e), exc_info=True)
                raise
        
        # Start gRPC server in a thread
        grpc_thread = threading.Thread(
            target=run_grpc_server,
            daemon=False,
            name="gRPCServer"
        )
        grpc_thread.start()
        logger.info("gRPC server started", port=config.grpc_port)
        
        # Create and start Flask HTTP server for health/metrics
        logger.info("Starting HTTP health server...", port=config.http_health_port)
        flask_app = create_health_app(mongodb, event_publisher)
        
        flask_thread = threading.Thread(
            target=run_flask,
            args=(flask_app, '0.0.0.0', config.http_health_port),
            daemon=False,
            name="FlaskHTTP"
        )
        flask_thread.start()
        logger.info("HTTP health server started", port=config.http_health_port)
        
        # Start event consumer in thread
        logger.info("Starting event consumer...")
        consumer.start_in_thread()
        logger.info("Event consumer started")
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("Cart service is running",
                   grpc_port=config.grpc_port,
                   http_port=config.http_health_port)
        
        # Wait for shutdown signal
        while not shutdown_event.is_set():
            time.sleep(1)
            
            # Check if critical threads are still alive
            if not grpc_thread.is_alive():
                logger.error("gRPC server thread died")
                shutdown_event.set()
            
            if not consumer.is_alive():
                logger.warning("Event consumer thread died, restarting...")
                consumer.start_in_thread()
        
        # Wait for gRPC thread to finish
        logger.info("Waiting for gRPC server to stop...")
        grpc_thread.join(timeout=30)
        
        logger.info("Cart service stopped")
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        shutdown()
        sys.exit(0)
    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        shutdown()
        sys.exit(1)


if __name__ == '__main__':
    main()




