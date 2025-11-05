"""
gRPC server implementation for payment service
"""
import time
from concurrent import futures
import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
import structlog

# Import generated proto stubs
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'contracts', 'gen', 'python'))

from contracts.gen.python import payment_pb2
from contracts.gen.python import payment_pb2_grpc
from contracts.gen.python import common_pb2

from payment.service import PaymentService
from payment.models import Payment, PaymentMethod, PaymentMethodType, Money
from payment.events.publisher import EventPublisher
from payment.config import config


logger = structlog.get_logger()


class PaymentServicer(payment_pb2_grpc.PaymentServiceServicer):
    """Implementation of PaymentService gRPC service"""
    
    def __init__(self, payment_service: PaymentService, event_publisher: EventPublisher):
        self.payment_service = payment_service
        self.event_publisher = event_publisher
        self.logger = structlog.get_logger().bind(component="grpc_server")
    
    def _payment_to_proto(self, payment: Payment) -> payment_pb2.GetPaymentResponse:
        """Convert Payment model to protobuf GetPaymentResponse"""
        return payment_pb2.GetPaymentResponse(
            payment_id=payment.payment_id,
            order_id=payment.order_id,
            user_id=payment.user_id,
            amount=common_pb2.Money(
                currency=payment.amount.currency,
                amount=payment.amount.amount,
                decimal_places=payment.amount.decimal_places
            ),
            method=payment_pb2.PaymentMethod(
                type=self._map_payment_method_type(payment.method.type),
                last4=payment.method.last4,
                token=payment.method.token
            ),
            status=self._map_payment_status(payment.status),
            created_at=payment.created_at,
            captured_at=payment.captured_at or 0
        )
    
    def _map_payment_method_type(self, method_type: PaymentMethodType) -> int:
        """Map PaymentMethodType enum to proto enum"""
        mapping = {
            PaymentMethodType.UNSPECIFIED: payment_pb2.PAYMENT_METHOD_TYPE_UNSPECIFIED,
            PaymentMethodType.CREDIT_CARD: payment_pb2.CREDIT_CARD,
            PaymentMethodType.DEBIT_CARD: payment_pb2.DEBIT_CARD,
            PaymentMethodType.PAYPAL: payment_pb2.PAYPAL,
            PaymentMethodType.BANK_TRANSFER: payment_pb2.BANK_TRANSFER
        }
        return mapping.get(method_type, payment_pb2.PAYMENT_METHOD_TYPE_UNSPECIFIED)
    
    def _map_payment_status(self, status) -> int:
        """Map PaymentStatus enum to proto enum"""
        status_str = status.value if hasattr(status, 'value') else str(status)
        mapping = {
            'PENDING': payment_pb2.PENDING,
            'AUTHORIZED': payment_pb2.AUTHORIZED,
            'CAPTURED': payment_pb2.CAPTURED,
            'FAILED': payment_pb2.FAILED,
            'CANCELLED': payment_pb2.CANCELLED
        }
        return mapping.get(status_str, payment_pb2.PAYMENT_STATUS_UNSPECIFIED)
    
    def _proto_to_payment_method_type(self, proto_type: int) -> PaymentMethodType:
        """Map proto enum to PaymentMethodType enum"""
        mapping = {
            payment_pb2.PAYMENT_METHOD_TYPE_UNSPECIFIED: PaymentMethodType.UNSPECIFIED,
            payment_pb2.CREDIT_CARD: PaymentMethodType.CREDIT_CARD,
            payment_pb2.DEBIT_CARD: PaymentMethodType.DEBIT_CARD,
            payment_pb2.PAYPAL: PaymentMethodType.PAYPAL,
            payment_pb2.BANK_TRANSFER: PaymentMethodType.BANK_TRANSFER
        }
        return mapping.get(proto_type, PaymentMethodType.UNSPECIFIED)
    
    def Health(self, request, context):
        """Health check endpoint"""
        return common_pb2.HealthStatus(
            status=common_pb2.HealthStatus.SERVING,
            service=config.service_name,
            version="1.0.0",
            timestamp=int(time.time())
        )
    
    def Authorize(self, request: payment_pb2.AuthorizeRequest, context) -> payment_pb2.AuthorizeResponse:
        """Authorize a payment"""
        start_time = time.time()
        
        try:
            # Validate request
            if not request.order_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("order_id is required")
                return payment_pb2.AuthorizeResponse()
            
            if not request.user_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("user_id is required")
                return payment_pb2.AuthorizeResponse()
            
            if not request.amount or request.amount.amount <= 0:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("amount must be positive")
                return payment_pb2.AuthorizeResponse()
            
            if not request.method or not request.method.token:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("payment method is required")
                return payment_pb2.AuthorizeResponse()
            
            # Convert proto to domain models
            amount = Money(
                amount=request.amount.amount,
                currency=request.amount.currency or "USD",
                decimal_places=request.amount.decimal_places or 2
            )
            
            method = PaymentMethod(
                type=self._proto_to_payment_method_type(request.method.type),
                last4=request.method.last4 or "",
                token=request.method.token
            )
            
            # Authorize payment
            try:
                payment = self.payment_service.authorize(
                    order_id=request.order_id,
                    amount=amount,
                    method=method,
                    user_id=request.user_id
                )
                
                return payment_pb2.AuthorizeResponse(
                    payment_id=payment.payment_id,
                    status=self._map_payment_status(payment.status),
                    message="Payment authorized successfully"
                )
                
            except ValueError as e:
                self.logger.warning("Validation error during authorization", error=str(e))
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(str(e))
                return payment_pb2.AuthorizeResponse()
            
            except Exception as e:
                self.logger.error("Authorization failed", error=str(e))
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(f"Authorization failed: {str(e)}")
                return payment_pb2.AuthorizeResponse()
        
        except Exception as e:
            self.logger.error("Unexpected error in Authorize", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return payment_pb2.AuthorizeResponse()
    
    def Capture(self, request: payment_pb2.CaptureRequest, context) -> payment_pb2.CaptureResponse:
        """Capture an authorized payment"""
        start_time = time.time()
        
        try:
            self.logger.info("Capture request", payment_id=request.payment_id)
            
            # Validate request
            if not request.payment_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("payment_id is required")
                return payment_pb2.CaptureResponse()
            
            # Capture payment
            try:
                payment = self.payment_service.capture(request.payment_id)
                
                # Publish events on successful capture
                try:
                    self.event_publisher.publish_payment_succeeded(payment)
                    self.event_publisher.publish_payment_receipt(payment)
                except Exception as e:
                    self.logger.error("Failed to publish payment events", error=str(e))
                    # Don't fail the request if event publishing fails
                
                # Update order status to CONFIRMED on successful payment
                try:
                    from payment.clients.order_client import update_order_status
                    update_order_status(payment.order_id, "CONFIRMED")
                except Exception as e:
                    self.logger.error("Error updating order status", order_id=payment.order_id, error=str(e))
                    # Don't fail the request if order status update fails
                
                return payment_pb2.CaptureResponse(
                    payment_id=payment.payment_id,
                    status=self._map_payment_status(payment.status),
                    message="Payment captured successfully",
                    captured_at=payment.captured_at
                )
                
            except ValueError as e:
                self.logger.warning("Validation error during capture", error=str(e))
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(str(e))
                return payment_pb2.CaptureResponse()
            
            except Exception as e:
                self.logger.error("Capture failed", error=str(e))
                
                # Try to publish failure event
                try:
                    payment = self.payment_service.get_payment(request.payment_id)
                    if payment:
                        self.event_publisher.publish_payment_failed(payment, str(e))
                except:
                    pass
                
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(f"Capture failed: {str(e)}")
                return payment_pb2.CaptureResponse()
        
        except Exception as e:
            self.logger.error("Unexpected error in Capture", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return payment_pb2.CaptureResponse()
    
    def GetPayment(self, request: payment_pb2.GetPaymentRequest, context) -> payment_pb2.GetPaymentResponse:
        """Get payment by ID"""
        try:
            # Validate request
            if not request.payment_id:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("payment_id is required")
                return payment_pb2.GetPaymentResponse()
            
            # Get payment
            payment = self.payment_service.get_payment(request.payment_id)
            
            if not payment:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Payment {request.payment_id} not found")
                return payment_pb2.GetPaymentResponse()
            
            return self._payment_to_proto(payment)
        
        except Exception as e:
            self.logger.error("Error in GetPayment", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return payment_pb2.GetPaymentResponse()


def create_grpc_server():
    """Create and start gRPC server"""
    from payment.processor import get_payment_processor
    
    # Initialize components
    processor = get_payment_processor()
    payment_service = PaymentService(processor)
    event_publisher = EventPublisher()
    
    # Connect to RabbitMQ
    try:
        event_publisher.connect()
    except Exception as e:
        logger.warning("Failed to connect to RabbitMQ on startup", error=str(e))
    
    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Register payment service
    payment_servicer = PaymentServicer(payment_service, event_publisher)
    payment_pb2_grpc.add_PaymentServiceServicer_to_server(payment_servicer, server)
    
    # Register health service
    health_servicer = health.HealthServicer()
    health_servicer.set("payment.PaymentService", health_pb2.HealthCheckResponse.SERVING)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    
    # Start server
    server.add_insecure_port(f'[::]:{config.grpc_port}')
    server.start()
    
    logger.info(f"Payment Service gRPC server started on port {config.grpc_port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down Payment Service")
        event_publisher.disconnect()
        server.stop(0)
