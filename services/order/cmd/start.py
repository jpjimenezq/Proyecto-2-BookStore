#!/usr/bin/env python3
"""
Order Service orchestration - starts gRPC server and Flask HTTP server
"""
import signal
import sys
import threading
import os
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from order.config import load_config
from order.logging_config import configure_logging
from order.health_http import create_health_app
from order.grpc.order_server import serve as start_grpc_server

# Global instances for graceful shutdown
grpc_server_thread: Optional[threading.Thread] = None
flask_thread: Optional[threading.Thread] = None
shutdown_event = threading.Event()
logger = None


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received shutdown signal: {signum}")
    shutdown_event.set()
    sys.exit(0)


def run_flask_server(config):
    """Run Flask server in a thread"""
    app = create_health_app()
    
    logger.info(f"Starting HTTP health server on port {config.http_health_port}")
    # Use Flask's built-in server for simplicity (development mode is OK for health checks)
    app.run(
        host='0.0.0.0',
        port=config.http_health_port,
        debug=False,
        use_reloader=False,
        threaded=True
    )


def run_grpc_server():
    """Run gRPC server in a thread"""
    start_grpc_server()


def main():
    """Main entry point"""
    global logger
    
    # Load configuration
    config = load_config()
    
    # Configure logging
    logger = configure_logging(config.log_level)
    
    logger.info(f"Starting {config.service_name} service")
    logger.info(f"gRPC port: {config.grpc_port}")
    logger.info(f"HTTP health port: {config.http_health_port}")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start Flask HTTP server in a thread
        flask_thread = threading.Thread(
            target=run_flask_server,
            args=(config,),
            daemon=True,
            name="FlaskServer"
        )
        flask_thread.start()
        logger.info("Flask health server thread started")
        
        # Start gRPC server in main thread (blocking)
        logger.info("Starting gRPC server...")
        run_grpc_server()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        shutdown_event.set()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
