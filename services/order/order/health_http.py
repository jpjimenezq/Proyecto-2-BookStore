"""
Flask HTTP server for health checks
"""
from flask import Flask, Response
import logging
from sqlalchemy import text
from order.db import engine


logger = logging.getLogger("order.health")


def create_health_app() -> Flask:
    """
    Create Flask app with health endpoint
    
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Disable Flask's default logger to avoid duplicate logs
    import logging as flask_logging
    log = flask_logging.getLogger('werkzeug')
    log.setLevel(flask_logging.WARNING)
    
    @app.route('/healthz', methods=['GET'])
    def healthz():
        """
        Health check - checks if service is alive and dependencies are healthy
        
        Returns:
            200 if healthy, 503 if unhealthy
        """
        try:
            # Check PostgreSQL
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            return Response("healthy", status=200, mimetype='text/plain')
        
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return Response(
                f"unhealthy: {str(e)}",
                status=503,
                mimetype='text/plain'
            )
    
    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint"""
        return Response(
            "Order Service - Use /healthz for health check",
            status=200,
            mimetype='text/plain'
        )
    
    logger.info("Flask health app created")
    return app

