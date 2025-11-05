"""
RabbitMQ event publisher with retry logic and confirmations
"""
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError
import structlog

from cart.config import Config


logger = structlog.get_logger()


class EventPublisher:
    """Publisher for cart domain events to RabbitMQ"""
    
    def __init__(self, config: Config):
        self.config = config
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self.logger = structlog.get_logger().bind(component="event_publisher")
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to RabbitMQ"""
        try:
            parameters = pika.URLParameters(self.config.rabbitmq_url)
            parameters.heartbeat = 30
            parameters.blocked_connection_timeout = 300
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.config.rabbitmq_cart_exchange,
                exchange_type='topic',
                durable=True
            )
            
            # Enable publisher confirms
            self.channel.confirm_delivery()
            
            self.logger.info("Connected to RabbitMQ for publishing",
                           exchange=self.config.rabbitmq_cart_exchange)
            
        except AMQPConnectionError as e:
            self.logger.error("Failed to connect to RabbitMQ", error=str(e))
            raise
    
    def _reconnect(self) -> None:
        """Reconnect to RabbitMQ"""
        try:
            self.close()
        except:
            pass
        self._connect()
    
    def _publish_with_retry(
        self,
        routing_key: str,
        event: Dict[str, Any]
    ) -> None:
        """
        Publish event with exponential backoff retry
        
        Args:
            routing_key: RabbitMQ routing key
            event: Event payload
            
        Raises:
            Exception if all retries fail
        """
        start_time = time.time()
        
        event_json = json.dumps(event)
        max_attempts = self.config.rabbitmq_retry_max_attempts
        delay = self.config.rabbitmq_retry_initial_delay
        
        for attempt in range(max_attempts):
            try:
                # Ensure connection is alive
                if not self.is_healthy():
                    self._reconnect()
                
                # Publish with confirmation
                self.channel.basic_publish(
                    exchange=self.config.rabbitmq_cart_exchange,
                    routing_key=routing_key,
                    body=event_json,
                    properties=pika.BasicProperties(
                        content_type='application/json',
                        delivery_mode=2,  # Persistent
                        message_id=event['event_id'],
                        timestamp=int(time.time()),
                        headers={
                            'event_type': event['event_type'],
                            'event_version': event.get('event_version', '1.0.0')
                        }
                    ),
                    mandatory=False
                )
                
                # Record success metrics
                duration = time.time() - start_time
                event_publish_duration.observe(duration)
                cart_events_published_total.labels(
                    event_type=event['event_type'],
                    status='success'
                ).inc()
                
                self.logger.info(
                    "Event published",
                    event_id=event['event_id'],
                    event_type=event['event_type'],
                    routing_key=routing_key,
                    attempt=attempt + 1
                )
                return
                
            except (AMQPConnectionError, AMQPChannelError) as e:
                self.logger.warning(
                    "Event publish failed, retrying",
                    event_id=event['event_id'],
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    error=str(e)
                )
                
                if attempt < max_attempts - 1:
                    time.sleep(delay)
                    delay = min(delay * 2, self.config.rabbitmq_retry_max_delay)
                else:
                    # All retries failed
                    cart_events_published_total.labels(
                        event_type=event['event_type'],
                        status='failed'
                    ).inc()
                    self.logger.error(
                        "Event publish failed after all retries",
                        event_id=event['event_id'],
                        event_type=event['event_type']
                    )
                    raise
    
    def publish_item_added(
        self,
        user_id: str,
        sku: str,
        qty: int,
        price: float,
        currency: str,
        title: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Publish cart.item_added event"""
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'cart.item_added',
            'event_version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'correlation_id': correlation_id,
            'payload': {
                'user_id': user_id,
                'sku': sku,
                'qty': qty,
                'price': int(price * 100),  # Convert to cents
                'currency': currency,
                'title': title
            }
        }
        
        self._publish_with_retry('cart.item_added', event)
    
    def publish_item_removed(
        self,
        user_id: str,
        sku: str,
        qty: int,
        correlation_id: Optional[str] = None
    ) -> None:
        """Publish cart.item_removed event"""
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'cart.item_removed',
            'event_version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'correlation_id': correlation_id,
            'payload': {
                'user_id': user_id,
                'sku': sku,
                'qty': qty
            }
        }
        
        self._publish_with_retry('cart.item_removed', event)
    
    def publish_cart_cleared(
        self,
        user_id: str,
        reason: str = "user_requested",
        correlation_id: Optional[str] = None
    ) -> None:
        """Publish cart.cleared event"""
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'cart.cleared',
            'event_version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'correlation_id': correlation_id,
            'payload': {
                'user_id': user_id,
                'reason': reason
            }
        }
        
        self._publish_with_retry('cart.cleared', event)
    
    def publish_checkout_requested(
        self,
        user_id: str,
        items: list,
        total_amount: float,
        currency: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Publish cart.checkout_requested event"""
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'cart.checkout_requested',
            'event_version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'correlation_id': correlation_id,
            'payload': {
                'user_id': user_id,
                'items': items,
                'total_amount': int(total_amount * 100),
                'currency': currency
            }
        }
        
        self._publish_with_retry('cart.checkout_requested', event)
    
    def is_healthy(self) -> bool:
        """Check if publisher connection is healthy"""
        try:
            return (
                self.connection is not None and
                self.connection.is_open and
                self.channel is not None and
                self.channel.is_open
            )
        except:
            return False
    
    def close(self) -> None:
        """Close publisher connection"""
        try:
            if self.channel and self.channel.is_open:
                self.channel.close()
            if self.connection and self.connection.is_open:
                self.connection.close()
            self.logger.info("Event publisher closed")
        except Exception as e:
            self.logger.error("Error closing publisher", error=str(e))




