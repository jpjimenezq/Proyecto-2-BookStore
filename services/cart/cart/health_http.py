"""
Flask HTTP server for health checks
"""
from flask import Flask, Response
import structlog

from cart.db import MongoDB
from cart.events.publisher import EventPublisher


logger = structlog.get_logger()


def create_health_app(mongodb: MongoDB, event_publisher: EventPublisher) -> Flask:
    """
    Create Flask app with health endpoint
    
    Args:
        mongodb: MongoDB connection instance
        event_publisher: RabbitMQ publisher instance
        
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Disable Flask's default logger to avoid duplicate logs
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)
    
    @app.route('/healthz', methods=['GET'])
    def healthz():
        """
        Health check - checks if service is alive and dependencies are healthy
        
        Returns:
            200 if healthy, 503 if unhealthy
        """
        try:
            # Check MongoDB
            if not mongodb.is_healthy():
                logger.error("Health check failed: MongoDB unhealthy")
                return Response(
                    "unhealthy: mongodb connection failed",
                    status=503,
                    mimetype='text/plain'
                )
            
            # Check RabbitMQ
            if not event_publisher.is_healthy():
                logger.error("Health check failed: RabbitMQ unhealthy")
                return Response(
                    "unhealthy: rabbitmq connection failed",
                    status=503,
                    mimetype='text/plain'
                )
            
            return Response("healthy", status=200, mimetype='text/plain')
            
        except Exception as e:
            logger.error("Health check error", error=str(e))
            return Response(
                f"unhealthy: {str(e)}",
                status=503,
                mimetype='text/plain'
            )
    
    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint"""
        return Response(
            "Cart Service - Use /healthz for health check",
            status=200,
            mimetype='text/plain'
        )
    
    logger.info("Flask health app created")
    return app




