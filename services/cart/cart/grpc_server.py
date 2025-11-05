"""
gRPC server implementation for cart service
"""
import time
from concurrent import futures
import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp
import structlog

# Import generated proto stubs
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'contracts', 'gen', 'python'))

from contracts.gen.python import cart_pb2
from contracts.gen.python import cart_pb2_grpc
from contracts.gen.python import common_pb2

from cart.service import CartService
from cart.models import Cart
from cart.events.publisher import EventPublisher
from cart.clients.catalog_client import get_catalog_client


logger = structlog.get_logger()


class CartServicer(cart_pb2_grpc.CartServiceServicer):
    """Implementation of CartService gRPC service"""
    
    def __init__(self, cart_service: CartService, event_publisher: EventPublisher):
        self.cart_service = cart_service
        self.event_publisher = event_publisher
        self.logger = structlog.get_logger().bind(component="grpc_server")
    
    def _cart_to_proto(self, cart: Cart) -> cart_pb2.Cart:
        """Convert Cart model to protobuf Cart"""
        items = []
        for item in cart.items:
            items.append(cart_pb2.CartItem(
                user_id=cart.user_id,
                sku=item.sku,
                qty=item.qty,
                price=common_pb2.Money(
                    currency=item.currency,
                    amount=int(item.price * 100),  # Convert to cents
                    decimal_places=2
                ),
                title=item.title
            ))
        
        # Convert datetime to timestamp
        timestamp = Timestamp()
        timestamp.FromDatetime(cart.updated_at)
        
        return cart_pb2.Cart(
            user_id=cart.user_id,
            items=items,
            updated_at=int(cart.updated_at.timestamp()),
            total=common_pb2.Money(
                currency="USD",  # Default currency for total
                amount=int(cart.total * 100),
                decimal_places=2
            )
        )
    
    def AddItem(self, request: cart_pb2.AddItemRequest, context) -> cart_pb2.AddItemResponse:
        """Add item to cart"""
        start_time = time.time()
        method = "AddItem"
        
        try:
            self.logger.info("AddItem request", user_id=request.user_id, sku=request.sku, qty=request.qty)
            
            # Validate request
            if not request.user_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id is required")
                return cart_pb2.AddItemResponse()
            
            if not request.sku:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("sku is required")
                return cart_pb2.AddItemResponse()
            
            if request.qty <= 0:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("qty must be positive")
                return cart_pb2.AddItemResponse()
            
            # Fetch price and title from catalog service
            try:
                catalog_client = get_catalog_client()
                book = catalog_client.get_book(request.sku)
                
                if not book:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Book with SKU {request.sku} not found in catalog")
                    return cart_pb2.AddItemResponse()
                
                if not book['active']:
                    context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                    context.set_details(f"Book {request.sku} is not available")
                    return cart_pb2.AddItemResponse()
                
                price = book['price']
                currency = book['currency']
                title = book['title']
                
                self.logger.info("Book validated from catalog", 
                               sku=request.sku, 
                               title=title, 
                               price=price)
            except Exception as e:
                self.logger.error("Failed to fetch book from catalog", 
                                sku=request.sku, 
                                error=str(e))
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                context.set_details("Catalog service unavailable. Please try again later.")
                return cart_pb2.AddItemResponse()
            
            # Add item to cart
            cart, was_new = self.cart_service.add_item(
                request.user_id,
                request.sku,
                request.qty,
                price,
                currency,
                title
            )
            
            # Publish event asynchronously
            try:
                self.event_publisher.publish_item_added(
                    request.user_id,
                    request.sku,
                    request.qty,
                    price,
                    currency,
                    title
                )
            except Exception as e:
                self.logger.error("Failed to publish item_added event", error=str(e))
                # Don't fail the request if event publishing fails
            
            # Record metrics
            duration = time.time() - start_time
            
            return cart_pb2.AddItemResponse(cart=self._cart_to_proto(cart))
            
        except ValueError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return cart_pb2.AddItemResponse()
        except Exception as e:
            self.logger.error("AddItem error", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return cart_pb2.AddItemResponse()
    
    def RemoveItem(self, request: cart_pb2.RemoveItemRequest, context) -> cart_pb2.RemoveItemResponse:
        """Remove item from cart"""
        start_time = time.time()
        method = "RemoveItem"
        
        try:
            self.logger.info("RemoveItem request", user_id=request.user_id, sku=request.sku)
            
            if not request.user_id or not request.sku:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id and sku are required")
                return cart_pb2.RemoveItemResponse()
            
            # Remove item
            cart, was_removed = self.cart_service.remove_item(request.user_id, request.sku)
            
            # Publish event if item was removed
            if was_removed:
                try:
                    self.event_publisher.publish_item_removed(
                        request.user_id,
                        request.sku,
                        0  # qty after removal (fully removed)
                    )
                except Exception as e:
                    self.logger.error("Failed to publish item_removed event", error=str(e))
            
            # Record metrics
            duration = time.time() - start_time
            
            return cart_pb2.RemoveItemResponse(cart=self._cart_to_proto(cart))
            
        except Exception as e:
            self.logger.error("RemoveItem error", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return cart_pb2.RemoveItemResponse()
    
    def GetCart(self, request: cart_pb2.GetCartRequest, context) -> cart_pb2.GetCartResponse:
        """Get user's cart"""
        start_time = time.time()
        method = "GetCart"
        
        try:
            self.logger.info("GetCart request", user_id=request.user_id)
            
            if not request.user_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id is required")
                return cart_pb2.GetCartResponse()
            
            cart = self.cart_service.get_cart(request.user_id)
            
            # Record metrics
            duration = time.time() - start_time
            
            return cart_pb2.GetCartResponse(cart=self._cart_to_proto(cart))
            
        except Exception as e:
            self.logger.error("GetCart error", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return cart_pb2.GetCartResponse()
    
    def ClearCart(self, request: cart_pb2.ClearCartRequest, context) -> cart_pb2.ClearCartResponse:
        """Clear all items from cart"""
        start_time = time.time()
        method = "ClearCart"
        
        try:
            self.logger.info("ClearCart request", user_id=request.user_id)
            
            if not request.user_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id is required")
                return cart_pb2.ClearCartResponse(success=False)
            
            success = self.cart_service.clear_cart(request.user_id)
            
            # Publish event
            if success:
                try:
                    self.event_publisher.publish_cart_cleared(
                        request.user_id,
                        "user_requested"
                    )
                except Exception as e:
                    self.logger.error("Failed to publish cart_cleared event", error=str(e))
            
            # Record metrics
            duration = time.time() - start_time
            
            return cart_pb2.ClearCartResponse(success=success)
            
        except Exception as e:
            self.logger.error("ClearCart error", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return cart_pb2.ClearCartResponse(success=False)
    
    def Health(self, request: common_pb2.Empty, context) -> common_pb2.HealthStatus:
        """Health check"""
        return common_pb2.HealthStatus(
            status=common_pb2.HealthStatus.SERVING,
            service="cart",
            version="1.0.0",
            timestamp=int(time.time())
        )


def create_grpc_server(cart_service: CartService, event_publisher: EventPublisher, port: int):
    """Create and configure gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Register cart service
    cart_servicer = CartServicer(cart_service, event_publisher)
    cart_pb2_grpc.add_CartServiceServicer_to_server(cart_servicer, server)
    
    # Register health service
    health_servicer = health.HealthServicer()
    health_servicer.set("cart", health_pb2.HealthCheckResponse.SERVING)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    
    # Add port
    server.add_insecure_port(f'[::]:{port}')
    
    logger.info("gRPC server configured", port=port)
    return server

