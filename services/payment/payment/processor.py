"""
Payment processor implementations
Mock processor for testing and development
"""
import time
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any
import structlog

from payment.models import PaymentMethod
from payment.config import config


logger = structlog.get_logger()


class PaymentProcessor(ABC):
    """Abstract payment processor interface"""
    
    @abstractmethod
    def authorize(self, amount: int, method: PaymentMethod, order_id: str) -> Dict[str, Any]:
        """
        Authorize a payment (reserve funds)
        
        Args:
            amount: Amount in cents
            method: Payment method details
            order_id: Order identifier
            
        Returns:
            dict with keys: success (bool), transaction_id (str), message (str)
        """
        pass
    
    @abstractmethod
    def capture(self, transaction_id: str, amount: int) -> Dict[str, Any]:
        """
        Capture an authorized payment (charge funds)
        
        Args:
            transaction_id: Transaction identifier from authorization
            amount: Amount to capture in cents
            
        Returns:
            dict with keys: success (bool), message (str)
        """
        pass


class MockPaymentProcessor(PaymentProcessor):
    """
    Mock payment processor for testing/development
    
    Rules:
    - Approves payments < config.mock_processor_max_amount (default 100000 cents = $1000)
    - Rejects payments >= max_amount
    - Simulates network latency
    - Always succeeds capture if transaction exists
    """
    
    def __init__(self):
        self.logger = structlog.get_logger().bind(component="mock_processor")
        self.authorized_transactions: Dict[str, int] = {}  # transaction_id -> amount
        self.max_amount = config.mock_processor_max_amount
        self.latency = config.mock_processor_latency
    
    def authorize(self, amount: int, method: PaymentMethod, order_id: str) -> Dict[str, Any]:
        """
        Simulate payment authorization
        """
        self.logger.info(
            "Processing authorization",
            amount=amount,
            method_type=method.type.value,
            order_id=order_id
        )
        
        # Simulate network latency
        time.sleep(self.latency)
        
        # Check amount limit
        if amount >= self.max_amount:
            self.logger.warning(
                "Authorization rejected - amount too high",
                amount=amount,
                max_amount=self.max_amount
            )
            return {
                'success': False,
                'transaction_id': None,
                'message': f'Amount exceeds limit of ${self.max_amount/100:.2f}'
            }
        
        # Check for invalid payment methods
        if method.type.value == "UNSPECIFIED":
            self.logger.warning("Authorization rejected - invalid payment method")
            return {
                'success': False,
                'transaction_id': None,
                'message': 'Invalid payment method'
            }
        
        # Generate transaction ID
        transaction_id = f'TXN-{uuid.uuid4().hex[:12].upper()}'
        
        # Store authorized transaction
        self.authorized_transactions[transaction_id] = amount
        
        self.logger.info(
            "Authorization approved",
            transaction_id=transaction_id,
            amount=amount
        )
        
        return {
            'success': True,
            'transaction_id': transaction_id,
            'message': 'Authorized successfully'
        }
    
    def capture(self, transaction_id: str, amount: int) -> Dict[str, Any]:
        """
        Simulate payment capture
        """
        self.logger.info(
            "Processing capture",
            transaction_id=transaction_id,
            amount=amount
        )
        
        # Simulate network latency (shorter than authorization)
        time.sleep(self.latency * 0.6)
        
        # Check if transaction was authorized
        if transaction_id not in self.authorized_transactions:
            self.logger.error(
                "Capture failed - transaction not found",
                transaction_id=transaction_id
            )
            return {
                'success': False,
                'message': f'Transaction {transaction_id} not found or not authorized'
            }
        
        # Check amount matches
        authorized_amount = self.authorized_transactions[transaction_id]
        if amount != authorized_amount:
            self.logger.error(
                "Capture failed - amount mismatch",
                transaction_id=transaction_id,
                authorized_amount=authorized_amount,
                capture_amount=amount
            )
            return {
                'success': False,
                'message': f'Amount mismatch: authorized ${authorized_amount/100:.2f}, capture ${amount/100:.2f}'
            }
        
        # Remove from authorized (captured transactions can't be captured again)
        del self.authorized_transactions[transaction_id]
        
        self.logger.info(
            "Capture successful",
            transaction_id=transaction_id,
            amount=amount
        )
        
        return {
            'success': True,
            'message': 'Captured successfully'
        }


def get_payment_processor() -> PaymentProcessor:
    """
    Factory function to get the configured payment processor
    """
    processor_type = config.payment_processor.lower()
    
    if processor_type == 'mock':
        return MockPaymentProcessor()
    # Future: Add real processors
    # elif processor_type == 'stripe':
    #     return StripePaymentProcessor()
    # elif processor_type == 'paypal':
    #     return PayPalPaymentProcessor()
    else:
        logger.warning(
            "Unknown processor type, defaulting to mock",
            processor_type=processor_type
        )
        return MockPaymentProcessor()
