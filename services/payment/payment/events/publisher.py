"""
RabbitMQ event publisher for payment events
"""
import json
import uuid
import time
from typing import Optional, Dict, Any
import pika
import structlog

from payment.config import config
from payment.models import Payment


logger = structlog.get_logger()


class EventPublisher:
    """Publish payment events to RabbitMQ"""
    
    def __init__(self, rabbitmq_url: str = None, exchange_name: str = None):
        self.rabbitmq_url = rabbitmq_url or config.rabbitmq_url
        self.exchange_name = exchange_name or config.rabbitmq_exchange
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self.logger = structlog.get_logger().bind(component="event_publisher")
    
    def connect(self):
        """Connect to RabbitMQ and declare exchange"""
        try:
            self.logger.info("Connecting to RabbitMQ", url=self.rabbitmq_url)
            
            parameters = pika.URLParameters(self.rabbitmq_url)
            parameters.heartbeat = 600
            parameters.blocked_connection_timeout = 300
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare topic exchange
            self.channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='topic',
                durable=True
            )
            
            self.logger.info(
                "Connected to RabbitMQ",
                exchange=self.exchange_name
            )
            
        except Exception as e:
            self.logger.error("Failed to connect to RabbitMQ", error=str(e))
            raise
    
    def disconnect(self):
        """Disconnect from RabbitMQ"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            self.logger.error("Error disconnecting from RabbitMQ", error=str(e))
    
    def publish_event(self, routing_key: str, event_data: Dict[str, Any]):
        """
        Publish an event to RabbitMQ
        
        Args:
            routing_key: Routing key for the event
            event_data: Event payload
        """
        try:
            if not self.channel or self.connection.is_closed:
                self.connect()
            
            message = json.dumps(event_data, default=str)
            
            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=routing_key,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            self.logger.info(
                "Event published",
                routing_key=routing_key,
                event_id=event_data.get('event_id')
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to publish event",
                routing_key=routing_key,
                error=str(e)
            )
            # Try to reconnect for next publish
            try:
                self.connect()
            except:
                pass
            raise
    
    def publish_payment_succeeded(self, payment: Payment):
        """
        Publish payment.succeeded event
        
        Event consumers: User Service, Notification Service, Order Service
        """
        event_data = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'payment.succeeded',
            'order_id': payment.order_id,
            'payment_id': payment.payment_id,
            'user_id': payment.user_id,
            'amount': {
                'amount': payment.amount.amount,
                'currency': payment.amount.currency,
                'decimal_places': payment.amount.decimal_places
            },
            'status': payment.status.value,
            'payment_method': payment.method.type.value,
            'transaction_id': payment.transaction_id,
            'at': payment.captured_at or int(time.time())
        }
        
        self.publish_event('payment.succeeded', event_data)
    
    def publish_payment_failed(self, payment: Payment, reason: str):
        """
        Publish payment.failed event
        
        Event consumers: User Service, Order Service, Notification Service
        """
        event_data = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'payment.failed',
            'order_id': payment.order_id,
            'payment_id': payment.payment_id,
            'user_id': payment.user_id,
            'status': payment.status.value,
            'reason': reason,
            'at': int(time.time())
        }
        
        self.publish_event('payment.failed', event_data)
    
    def publish_payment_receipt(self, payment: Payment):
        """
        Publish payment.receipt event
        
        Event consumers: Notification Service
        """
        event_data = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'payment.receipt',
            'order_id': payment.order_id,
            'payment_id': payment.payment_id,
            'user_id': payment.user_id,
            'receipt_data': {
                'payment_method_type': payment.method.type.value,
                'payment_method_last4': payment.method.last4,
                'amount': payment.amount.amount,
                'currency': payment.amount.currency,
                'transaction_id': payment.transaction_id,
                'captured_at': payment.captured_at
            },
            'at': int(time.time())
        }
        
        self.publish_event('payment.receipt', event_data)
