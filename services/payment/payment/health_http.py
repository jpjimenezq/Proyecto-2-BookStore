"""
HTTP health check endpoint
"""
import threading
from flask import Flask, jsonify
import structlog

from payment.config import config


logger = structlog.get_logger()
app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': config.service_name,
        'version': '1.0.0'
    }), 200


@app.route('/ready', methods=['GET'])
def ready():
    """Readiness check endpoint"""
    # TODO: Add checks for RabbitMQ connection
    return jsonify({
        'status': 'ready',
        'service': config.service_name
    }), 200


def start_health_http_server():
    """Start HTTP server for health checks in a separate thread"""
    def run():
        logger.info("Starting HTTP health server", port=config.http_health_port)
        app.run(
            host='0.0.0.0',
            port=config.http_health_port,
            debug=False,
            use_reloader=False
        )
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    logger.info("HTTP health server started", port=config.http_health_port)
