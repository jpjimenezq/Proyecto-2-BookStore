"""
Business logic for cart operations
"""
import time
from typing import Optional, Tuple
import structlog

from cart.models import Cart, CartItem
from cart.db import CartRepository


logger = structlog.get_logger()


class CartService:
    """Service layer for cart business logic"""
    
    def __init__(self, repository: CartRepository):
        self.repo = repository
        self.logger = structlog.get_logger().bind(component="cart_service")
    
    def get_cart(self, user_id: str) -> Cart:
        """
        Get cart for a user. Creates empty cart if doesn't exist.
        
        Args:
            user_id: User identifier
            
        Returns:
            Cart instance
        """
        try:
            cart_data = self.repo.get_cart(user_id)
            
            if cart_data:
                cart = Cart.from_dict(cart_data)
            else:
                # Create empty cart
                cart = Cart(user_id=user_id)
            
            return cart
            
        except Exception as e:
            self.logger.error("Error getting cart", user_id=user_id, error=str(e))
            raise
    
    def add_item(
        self, 
        user_id: str, 
        sku: str, 
        qty: int, 
        price: float = None,
        currency: str = "USD",
        title: str = ""
    ) -> Tuple[Cart, bool]:
        """
        Add item to cart or update quantity if already exists.
        
        Args:
            user_id: User identifier
            sku: Stock Keeping Unit
            qty: Quantity to add
            price: Price per unit (if None, must be provided by caller from catalog)
            currency: Currency code
            title: Book title
            
        Returns:
            Tuple of (updated cart, was_new_item)
            
        Raises:
            ValueError: If price is None (caller must fetch from catalog first)
        """
        try:
            if price is None:
                raise ValueError("Price is required to add item")
            
            if qty <= 0:
                raise ValueError("Quantity must be positive")
            
            # Get current cart
            cart = self.get_cart(user_id)
            
            # Check if item already exists
            existing_item = cart.get_item(sku)
            was_new_item = existing_item is None
            
            # Add or update item
            cart.add_or_update_item(sku, qty, price, currency, title)
            
            # Save to database
            self.repo.upsert_cart(cart.to_dict())
            
            return cart, was_new_item
            
        except ValueError as e:
            self.logger.warning("Invalid add item request", user_id=user_id, error=str(e))
            raise
        except Exception as e:
            self.logger.error("Error adding item to cart", user_id=user_id, error=str(e))
            raise
    
    def remove_item(self, user_id: str, sku: str) -> Tuple[Cart, bool]:
        """
        Remove item from cart.
        
        Args:
            user_id: User identifier
            sku: Stock Keeping Unit to remove
            
        Returns:
            Tuple of (updated cart, was_removed)
        """
        try:
            cart = self.get_cart(user_id)
            
            # Remove item
            was_removed = cart.remove_item(sku)
            
            if was_removed:
                # Save to database
                self.repo.upsert_cart(cart.to_dict())
            
            return cart, was_removed
            
        except Exception as e:
            self.logger.error("Error removing item from cart", user_id=user_id, error=str(e))
            raise
    
    def clear_cart(self, user_id: str) -> bool:
        """
        Clear all items from cart (or delete cart).
        
        Args:
            user_id: User identifier
            
        Returns:
            True if cart was cleared/deleted
        """
        try:
            # Delete cart from database
            deleted = self.repo.delete_cart(user_id)
            
            return deleted
            
        except Exception as e:
            self.logger.error("Error clearing cart", user_id=user_id, error=str(e))
            raise
    
    def update_item_price(self, sku: str, price: float, currency: str) -> int:
        """
        Update price for an item across all carts (triggered by catalog.updated event).
        
        Args:
            sku: Stock Keeping Unit
            price: New price
            currency: Currency code
            
        Returns:
            Number of carts updated
        """
        try:
            updated_count = self.repo.update_item_price(sku, price, currency)
            return updated_count
            
        except Exception as e:
            self.logger.error("Error updating item price", sku=sku, error=str(e))
            raise
    
    def is_event_processed(self, event_id: str) -> bool:
        """Check if event was already processed (idempotency)"""
        return self.repo.check_event_processed(event_id)
    
    def mark_event_processed(self, event_id: str, event_type: str) -> bool:
        """Mark event as processed"""
        return self.repo.mark_event_processed(event_id, event_type)




