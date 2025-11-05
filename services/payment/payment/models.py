"""
Payment domain models
"""
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


class PaymentStatus(str, Enum):
    """Payment status enum"""
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentMethodType(str, Enum):
    """Payment method type enum"""
    UNSPECIFIED = "UNSPECIFIED"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    PAYPAL = "PAYPAL"
    BANK_TRANSFER = "BANK_TRANSFER"


@dataclass
class PaymentMethod:
    """Payment method details"""
    type: PaymentMethodType
    last4: str
    token: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'type': self.type.value,
            'last4': self.last4,
            'token': self.token
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaymentMethod':
        """Create from dictionary"""
        return cls(
            type=PaymentMethodType(data.get('type', 'UNSPECIFIED')),
            last4=data.get('last4', ''),
            token=data.get('token', '')
        )


@dataclass
class Money:
    """Money representation"""
    amount: int  # Amount in smallest currency unit (cents)
    currency: str = "USD"
    decimal_places: int = 2
    
    def to_float(self) -> float:
        """Convert to float representation"""
        return self.amount / (10 ** self.decimal_places)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'amount': self.amount,
            'currency': self.currency,
            'decimal_places': self.decimal_places
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Money':
        """Create from dictionary"""
        return cls(
            amount=data.get('amount', 0),
            currency=data.get('currency', 'USD'),
            decimal_places=data.get('decimal_places', 2)
        )


@dataclass
class Payment:
    """Payment entity"""
    payment_id: str
    order_id: str
    user_id: str
    amount: Money
    method: PaymentMethod
    status: PaymentStatus
    created_at: int = field(default_factory=lambda: int(time.time()))
    captured_at: Optional[int] = None
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'payment_id': self.payment_id,
            'order_id': self.order_id,
            'user_id': self.user_id,
            'amount': self.amount.to_dict(),
            'method': self.method.to_dict(),
            'status': self.status.value,
            'created_at': self.created_at,
            'captured_at': self.captured_at,
            'transaction_id': self.transaction_id,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Payment':
        """Create from dictionary"""
        return cls(
            payment_id=data['payment_id'],
            order_id=data['order_id'],
            user_id=data['user_id'],
            amount=Money.from_dict(data['amount']),
            method=PaymentMethod.from_dict(data['method']),
            status=PaymentStatus(data['status']),
            created_at=data.get('created_at', int(time.time())),
            captured_at=data.get('captured_at'),
            transaction_id=data.get('transaction_id'),
            error_message=data.get('error_message')
        )
