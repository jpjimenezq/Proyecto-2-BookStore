"""
Business logic for payment operations
"""
import time
import uuid
from typing import Optional, Dict
import structlog

from payment.models import Payment, PaymentMethod, PaymentStatus, Money
from payment.processor import PaymentProcessor


logger = structlog.get_logger()


class PaymentService:
    """Service layer for payment business logic"""
    
    def __init__(self, processor: PaymentProcessor):
        self.processor = processor
        # In-memory storage (stateless, data lost on restart)
        self.payments: Dict[str, Payment] = {}
        # Track payments by order_id for idempotency
        self.order_to_payment: Dict[str, str] = {}
        self.logger = structlog.get_logger().bind(component="payment_service")
    
    def authorize(
        self,
        order_id: str,
        amount: Money,
        method: PaymentMethod,
        user_id: str
    ) -> Payment:
        """
        Authorize a payment (reserve funds)
        
        Args:
            order_id: Order identifier
            amount: Payment amount
            method: Payment method details
            user_id: User identifier
            
        Returns:
            Payment object
            
        Raises:
            ValueError: If validation fails
            Exception: If processor fails
        """
        try:
            # Validate inputs
            self._validate_authorization_request(order_id, amount, method, user_id)
            
            # Check idempotency - if already authorized for this order, return existing
            if order_id in self.order_to_payment:
                existing_payment_id = self.order_to_payment[order_id]
                existing_payment = self.payments.get(existing_payment_id)
                if existing_payment and existing_payment.status == PaymentStatus.AUTHORIZED:
                    self.logger.info(
                        "Payment already authorized for order",
                        order_id=order_id,
                        payment_id=existing_payment_id
                    )
                    return existing_payment
            
            # Call processor to authorize
            result = self.processor.authorize(
                amount=amount.amount,
                method=method,
                order_id=order_id
            )
            
            # Generate payment ID
            payment_id = f'PAY-{uuid.uuid4().hex[:16].upper()}'
            
            if result['success']:
                # Create payment object
                payment = Payment(
                    payment_id=payment_id,
                    order_id=order_id,
                    user_id=user_id,
                    amount=amount,
                    method=method,
                    status=PaymentStatus.AUTHORIZED,
                    transaction_id=result['transaction_id']
                )
                
                # Store in memory
                self.payments[payment_id] = payment
                self.order_to_payment[order_id] = payment_id
                
                self.logger.info(
                    "Payment authorized",
                    payment_id=payment_id,
                    order_id=order_id,
                    amount=amount.amount,
                    transaction_id=result['transaction_id']
                )
                
                return payment
            else:
                # Authorization failed
                payment = Payment(
                    payment_id=payment_id,
                    order_id=order_id,
                    user_id=user_id,
                    amount=amount,
                    method=method,
                    status=PaymentStatus.FAILED,
                    error_message=result['message']
                )
                
                # Store failed payment
                self.payments[payment_id] = payment
                
                self.logger.warning(
                    "Payment authorization failed",
                    payment_id=payment_id,
                    order_id=order_id,
                    reason=result['message']
                )
                
                raise Exception(f"Authorization failed: {result['message']}")
                
        except ValueError as e:
            self.logger.error("Validation error during authorization", error=str(e))
            raise
        except Exception as e:
            self.logger.error("Error during authorization", error=str(e))
            raise
    
    def capture(self, payment_id: str) -> Payment:
        """
        Capture an authorized payment (charge funds)
        
        Args:
            payment_id: Payment identifier
            
        Returns:
            Updated payment object
            
        Raises:
            ValueError: If payment not found or invalid state
            Exception: If processor fails
        """
        try:
            # Get payment
            payment = self.payments.get(payment_id)
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")
            
            # Validate status
            if payment.status != PaymentStatus.AUTHORIZED:
                raise ValueError(
                    f"Cannot capture payment in status {payment.status}. "
                    f"Must be AUTHORIZED"
                )
            
            # Call processor to capture
            result = self.processor.capture(
                transaction_id=payment.transaction_id,
                amount=payment.amount.amount
            )
            
            if result['success']:
                # Update payment
                payment.status = PaymentStatus.CAPTURED
                payment.captured_at = int(time.time())
                
                self.logger.info(
                    "Payment captured",
                    payment_id=payment_id,
                    order_id=payment.order_id,
                    amount=payment.amount.amount
                )
                
                return payment
            else:
                # Capture failed
                payment.status = PaymentStatus.FAILED
                payment.error_message = result['message']
                
                self.logger.error(
                    "Payment capture failed",
                    payment_id=payment_id,
                    reason=result['message']
                )
                
                raise Exception(f"Capture failed: {result['message']}")
                
        except ValueError as e:
            self.logger.error("Validation error during capture", error=str(e))
            raise
        except Exception as e:
            self.logger.error("Error during capture", error=str(e))
            raise
    
    def get_payment(self, payment_id: str) -> Optional[Payment]:
        """
        Get payment by ID
        
        Args:
            payment_id: Payment identifier
            
        Returns:
            Payment object or None if not found
        """
        payment = self.payments.get(payment_id)
        
        if payment:
            self.logger.debug("Payment retrieved", payment_id=payment_id)
        else:
            self.logger.warning("Payment not found", payment_id=payment_id)
        
        return payment
    
    def _validate_authorization_request(
        self,
        order_id: str,
        amount: Money,
        method: PaymentMethod,
        user_id: str
    ):
        """Validate authorization request parameters"""
        if not order_id or not order_id.strip():
            raise ValueError("order_id is required")
        
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required")
        
        if amount.amount <= 0:
            raise ValueError(f"Invalid amount: {amount.amount}. Must be positive")
        
        if not method.token or not method.token.strip():
            raise ValueError("Payment method token is required")
