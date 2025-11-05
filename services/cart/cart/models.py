"""
Data models and validation using Pydantic
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class CartItem(BaseModel):
    """Represents an item in the shopping cart"""
    sku: str = Field(..., description="Stock Keeping Unit")
    qty: int = Field(..., ge=1, description="Quantity (must be >= 1)")
    price: float = Field(..., ge=0, description="Price per unit")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO 4217 currency code")
    title: str = Field(..., min_length=1, description="Book title")
    
    @validator('currency')
    def currency_uppercase(cls, v):
        return v.upper()
    
    class Config:
        json_schema_extra = {
            "example": {
                "sku": "BOOK-001",
                "qty": 2,
                "price": 19.99,
                "currency": "USD",
                "title": "Example Book"
            }
        }


class Cart(BaseModel):
    """Represents a user's shopping cart"""
    user_id: str = Field(..., description="User identifier")
    items: List[CartItem] = Field(default_factory=list, description="Cart items")
    total: float = Field(default=0.0, ge=0, description="Total cart value")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    def calculate_total(self) -> float:
        """Calculate total cart value"""
        return sum(item.qty * item.price for item in self.items)
    
    def recalculate_total(self) -> None:
        """Recalculate and update total"""
        self.total = self.calculate_total()
        self.updated_at = datetime.utcnow()
    
    def add_or_update_item(self, sku: str, qty: int, price: float, currency: str, title: str) -> None:
        """Add new item or update quantity of existing item"""
        for item in self.items:
            if item.sku == sku:
                # Update existing item
                item.qty += qty
                item.price = price
                item.currency = currency
                item.title = title
                self.recalculate_total()
                return
        
        # Add new item
        self.items.append(CartItem(
            sku=sku,
            qty=qty,
            price=price,
            currency=currency,
            title=title
        ))
        self.recalculate_total()
    
    def remove_item(self, sku: str) -> bool:
        """Remove item from cart. Returns True if item was found and removed."""
        original_length = len(self.items)
        self.items = [item for item in self.items if item.sku != sku]
        
        if len(self.items) < original_length:
            self.recalculate_total()
            return True
        return False
    
    def clear_items(self) -> None:
        """Remove all items from cart"""
        self.items = []
        self.total = 0.0
        self.updated_at = datetime.utcnow()
    
    def get_item(self, sku: str) -> Optional[CartItem]:
        """Get an item by SKU"""
        for item in self.items:
            if item.sku == sku:
                return item
        return None
    
    def update_item_price(self, sku: str, price: float, currency: str) -> bool:
        """Update price for an item. Returns True if item was found."""
        item = self.get_item(sku)
        if item:
            item.price = price
            item.currency = currency
            self.recalculate_total()
            return True
        return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB storage"""
        return {
            "user_id": self.user_id,
            "items": [item.model_dump() for item in self.items],
            "total": self.total,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Cart":
        """Create Cart from MongoDB document"""
        if data is None:
            return None
        
        items = [CartItem(**item) for item in data.get("items", [])]
        return cls(
            user_id=data["user_id"],
            items=items,
            total=data.get("total", 0.0),
            updated_at=data.get("updated_at", datetime.utcnow())
        )
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "items": [
                    {
                        "sku": "BOOK-001",
                        "qty": 2,
                        "price": 19.99,
                        "currency": "USD",
                        "title": "Example Book"
                    }
                ],
                "total": 39.98,
                "updated_at": "2025-10-25T10:00:00Z"
            }
        }


class AddItemRequest(BaseModel):
    """Request to add item to cart"""
    user_id: str
    sku: str
    qty: int = Field(ge=1)
    price: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default="USD", min_length=3, max_length=3)
    title: Optional[str] = Field(default="")


class RemoveItemRequest(BaseModel):
    """Request to remove item from cart"""
    user_id: str
    sku: str


class GetCartRequest(BaseModel):
    """Request to get user's cart"""
    user_id: str


class ClearCartRequest(BaseModel):
    """Request to clear user's cart"""
    user_id: str


class DomainEvent(BaseModel):
    """Base domain event structure"""
    event_id: str
    event_type: str
    event_version: str = "1.0.0"
    timestamp: str
    correlation_id: Optional[str] = None
    payload: dict
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "event_type": "cart.item_added",
                "event_version": "1.0.0",
                "timestamp": "2025-10-25T10:00:00Z",
                "payload": {
                    "user_id": "user123",
                    "sku": "BOOK-001",
                    "qty": 2
                }
            }
        }




