"""
RabbitMQ event consumer with idempotency and DLQ support
"""
import json
import time
import threading
from typing import Callable, Dict, Any
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError
import structlog

from cart.config import Config
from cart.service import CartService


logger = structlog.get_logger()


class EventConsumer:
    """Consumer for catalog and inventory events"""
    
    def __init__(self, config: Config, cart_service: CartService):
        self.config = config
        self.cart_service = cart_service
        self.connection: pika.BlockingConnection = None
        self.channel: pika.channel.Channel = None
        self.logger = structlog.get_logger().bind(component="event_consumer")
        self._should_stop = False
        self._consumer_thread: threading.Thread = None
    
    def _connect(self) -> None:
        """Establish connection to RabbitMQ"""
        try:
            parameters = pika.URLParameters(self.config.rabbitmq_url)
            parameters.heartbeat = 30
            parameters.blocked_connection_timeout = 300
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Set QoS
            self.channel.basic_qos(prefetch_count=self.config.rabbitmq_prefetch_count)
            
            # Declare exchange (ensure it exists)
            self.channel.exchange_declare(
                exchange=self.config.rabbitmq_exchange,
                exchange_type='topic',
                durable=True
            )
            
            # Declare DLQ
            dlq_name = 'cart.dlq'
            self.channel.queue_declare(queue=dlq_name, durable=True)
            
            # Declare main queue with DLQ
            queue_name = 'cart.events.queue'
            self.channel.queue_declare(
                queue=queue_name,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': '',
                    'x-dead-letter-routing-key': dlq_name,
                    'x-message-ttl': 86400000  # 24 hours
                }
            )
            
            # Bind to catalog.updated events
            self.channel.queue_bind(
                exchange=self.config.rabbitmq_exchange,
                queue=queue_name,
                routing_key='catalog.updated'
            )
            
            # Bind to inventory.updated events (if inventory service exists)
            self.channel.queue_bind(
                exchange=self.config.rabbitmq_exchange,
                queue=queue_name,
                routing_key='inventory.updated'
            )
            
            self.logger.info("Connected to RabbitMQ for consuming",
                           queue=queue_name,
                           routing_keys=['catalog.updated', 'inventory.updated'])
            
        except AMQPConnectionError as e:
            self.logger.error("Failed to connect to RabbitMQ", error=str(e))
            raise
    
    def _handle_catalog_updated(self, event: Dict[str, Any]) -> None:
        """
        Handle catalog.updated event - update item prices in carts
        
        Args:
            event: Event payload
        """
        payload = event.get('payload', {})
        sku = payload.get('sku')
        fields_changed = payload.get('fields_changed', [])
        
        # Only process if price or currency changed
        if 'price' in fields_changed or 'currency' in fields_changed:
            price_cents = payload.get('price')
            currency = payload.get('currency', 'USD')
            
            if price_cents is not None:
                price = price_cents / 100.0  # Convert from cents
                
                updated_count = self.cart_service.update_item_price(sku, price, currency)
                
                self.logger.info(
                    "Processed catalog.updated event",
                    event_id=event.get('event_id'),
                    sku=sku,
                    carts_updated=updated_count
                )
    
    def _handle_inventory_updated(self, event: Dict[str, Any]) -> None:
        """
        Handle inventory.updated event - could update stock levels or remove out-of-stock items
        
        Args:
            event: Event payload
        """
        payload = event.get('payload', {})
        sku = payload.get('sku')
        stock = payload.get('stock', 0)
        
        # TODO: Implement logic to handle out-of-stock items
        # For example, remove items from carts if stock becomes 0
        # Or notify users about low stock
        
        self.logger.info(
            "Processed inventory.updated event",
            event_id=event.get('event_id'),
            sku=sku,
            stock=stock
        )
    
    def _process_message(self, ch, method, properties, body) -> None:
        """
        Process incoming message with idempotency
        
        Args:
            ch: Channel
            method: Delivery method
            properties: Message properties
            body: Message body
        """
        start_time = time.time()
        event_type = None
        
        try:
            # Parse event
            event = json.loads(body)
            event_id = event.get('event_id')
            event_type = event.get('event_type')
            
            self.logger.debug("Received event", event_id=event_id, event_type=event_type)
            
            # Check idempotency
            if self.cart_service.is_event_processed(event_id):
                self.logger.info("Event already processed (idempotent)", event_id=event_id)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                cart_events_consumed_total.labels(
                    event_type=event_type,
                    status='duplicate'
                ).inc()
                return
            
            # Process based on event type
            if event_type == 'catalog.updated':
                self._handle_catalog_updated(event)
            elif event_type == 'inventory.updated':
                self._handle_inventory_updated(event)
            else:
                self.logger.warning("Unknown event type", event_type=event_type)
            
            # Mark as processed (idempotency)
            self.cart_service.mark_event_processed(event_id, event_type)
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
            # Record metrics
            duration = time.time() - start_time
            event_consume_duration.labels(event_type=event_type).observe(duration)
            cart_events_consumed_total.labels(
                event_type=event_type,
                status='success'
            ).inc()
            
            self.logger.info("Event processed successfully", event_id=event_id)
            
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON in message", error=str(e))
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            cart_events_consumed_total.labels(
                event_type=event_type or 'unknown',
                status='invalid_json'
            ).inc()
            
        except Exception as e:
            self.logger.error("Error processing event", error=str(e))
            # Nack and requeue (will go to DLQ after retries)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            cart_events_consumed_total.labels(
                event_type=event_type or 'unknown',
                status='error'
            ).inc()
    
    def start_consuming(self) -> None:
        """Start consuming messages (blocking)"""
        try:
            self._connect()
            
            self.channel.basic_consume(
                queue='cart.events.queue',
                on_message_callback=self._process_message,
                auto_ack=False
            )
            
            self.logger.info("Started consuming events")
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            self.logger.info("Consumer interrupted")
            self.stop()
        except Exception as e:
            self.logger.error("Consumer error", error=str(e))
            if not self._should_stop:
                # Attempt to reconnect
                self.logger.info("Attempting to reconnect...")
                time.sleep(5)
                self.start_consuming()
    
    def start_in_thread(self) -> threading.Thread:
        """Start consumer in a separate thread"""
        self._consumer_thread = threading.Thread(
            target=self.start_consuming,
            daemon=True,
            name="EventConsumer"
        )
        self._consumer_thread.start()
        self.logger.info("Consumer thread started")
        return self._consumer_thread
    
    def stop(self) -> None:
        """Stop consuming messages"""
        self._should_stop = True
        try:
            if self.channel and self.channel.is_open:
                self.channel.stop_consuming()
                self.channel.close()
            if self.connection and self.connection.is_open:
                self.connection.close()
            self.logger.info("Event consumer stopped")
        except Exception as e:
            self.logger.error("Error stopping consumer", error=str(e))
    
    def is_alive(self) -> bool:
        """Check if consumer thread is alive"""
        return self._consumer_thread is not None and self._consumer_thread.is_alive()




