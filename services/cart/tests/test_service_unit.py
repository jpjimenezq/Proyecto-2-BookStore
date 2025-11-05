"""
Unit tests for cart service business logic
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from cart.models import Cart, CartItem
from cart.service import CartService
from cart.db import CartRepository


class TestCartModel:
    """Test Cart model logic"""
    
    def test_calculate_total(self):
        """Test total calculation"""
        cart = Cart(user_id="test_user")
        cart.items = [
            CartItem(sku="BOOK-001", qty=2, price=19.99, currency="USD", title="Book 1"),
            CartItem(sku="BOOK-002", qty=1, price=29.99, currency="USD", title="Book 2"),
        ]
        
        total = cart.calculate_total()
        assert total == 69.97  # 2*19.99 + 1*29.99
    
    def test_add_new_item(self):
        """Test adding new item to cart"""
        cart = Cart(user_id="test_user")
        cart.add_or_update_item("BOOK-001", 2, 19.99, "USD", "Test Book")
        
        assert len(cart.items) == 1
        assert cart.items[0].sku == "BOOK-001"
        assert cart.items[0].qty == 2
        assert cart.total == 39.98
    
    def test_update_existing_item(self):
        """Test updating quantity of existing item"""
        cart = Cart(user_id="test_user")
        cart.add_or_update_item("BOOK-001", 2, 19.99, "USD", "Test Book")
        cart.add_or_update_item("BOOK-001", 3, 19.99, "USD", "Test Book")
        
        assert len(cart.items) == 1
        assert cart.items[0].qty == 5  # 2 + 3
        assert cart.total == 99.95
    
    def test_remove_item(self):
        """Test removing item from cart"""
        cart = Cart(user_id="test_user")
        cart.add_or_update_item("BOOK-001", 2, 19.99, "USD", "Book 1")
        cart.add_or_update_item("BOOK-002", 1, 29.99, "USD", "Book 2")
        
        removed = cart.remove_item("BOOK-001")
        
        assert removed is True
        assert len(cart.items) == 1
        assert cart.items[0].sku == "BOOK-002"
        assert cart.total == 29.99
    
    def test_remove_nonexistent_item(self):
        """Test removing item that doesn't exist"""
        cart = Cart(user_id="test_user")
        cart.add_or_update_item("BOOK-001", 2, 19.99, "USD", "Book 1")
        
        removed = cart.remove_item("BOOK-999")
        
        assert removed is False
        assert len(cart.items) == 1
    
    def test_clear_items(self):
        """Test clearing all items"""
        cart = Cart(user_id="test_user")
        cart.add_or_update_item("BOOK-001", 2, 19.99, "USD", "Book 1")
        cart.add_or_update_item("BOOK-002", 1, 29.99, "USD", "Book 2")
        
        cart.clear_items()
        
        assert len(cart.items) == 0
        assert cart.total == 0.0
    
    def test_update_item_price(self):
        """Test updating price for an item"""
        cart = Cart(user_id="test_user")
        cart.add_or_update_item("BOOK-001", 2, 19.99, "USD", "Book 1")
        
        updated = cart.update_item_price("BOOK-001", 24.99, "USD")
        
        assert updated is True
        assert cart.items[0].price == 24.99
        assert cart.total == 49.98  # 2 * 24.99


class TestCartService:
    """Test CartService business logic"""
    
    @pytest.fixture
    def mock_repo(self):
        """Create mock repository"""
        repo = Mock(spec=CartRepository)
        return repo
    
    @pytest.fixture
    def cart_service(self, mock_repo):
        """Create cart service with mock repo"""
        return CartService(mock_repo)
    
    def test_get_existing_cart(self, cart_service, mock_repo):
        """Test getting existing cart"""
        # Setup mock
        mock_repo.get_cart.return_value = {
            "user_id": "user123",
            "items": [
                {"sku": "BOOK-001", "qty": 2, "price": 19.99, "currency": "USD", "title": "Book 1"}
            ],
            "total": 39.98,
            "updated_at": datetime.utcnow()
        }
        
        cart = cart_service.get_cart("user123")
        
        assert cart.user_id == "user123"
        assert len(cart.items) == 1
        assert cart.total == 39.98
        mock_repo.get_cart.assert_called_once_with("user123")
    
    def test_get_nonexistent_cart(self, cart_service, mock_repo):
        """Test getting non-existent cart creates empty one"""
        mock_repo.get_cart.return_value = None
        
        cart = cart_service.get_cart("user123")
        
        assert cart.user_id == "user123"
        assert len(cart.items) == 0
        assert cart.total == 0.0
    
    def test_add_item_to_cart(self, cart_service, mock_repo):
        """Test adding item to cart"""
        mock_repo.get_cart.return_value = None
        mock_repo.upsert_cart.return_value = None
        
        cart, was_new = cart_service.add_item(
            "user123",
            "BOOK-001",
            2,
            19.99,
            "USD",
            "Test Book"
        )
        
        assert cart.user_id == "user123"
        assert len(cart.items) == 1
        assert cart.items[0].sku == "BOOK-001"
        assert cart.items[0].qty == 2
        assert was_new is True
        mock_repo.upsert_cart.assert_called_once()
    
    def test_add_item_without_price(self, cart_service, mock_repo):
        """Test adding item without price raises error"""
        with pytest.raises(ValueError, match="Price is required"):
            cart_service.add_item("user123", "BOOK-001", 2)
    
    def test_add_item_with_invalid_quantity(self, cart_service, mock_repo):
        """Test adding item with invalid quantity"""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            cart_service.add_item("user123", "BOOK-001", 0, 19.99)
    
    def test_remove_item_from_cart(self, cart_service, mock_repo):
        """Test removing item from cart"""
        mock_repo.get_cart.return_value = {
            "user_id": "user123",
            "items": [
                {"sku": "BOOK-001", "qty": 2, "price": 19.99, "currency": "USD", "title": "Book 1"}
            ],
            "total": 39.98,
            "updated_at": datetime.utcnow()
        }
        mock_repo.upsert_cart.return_value = None
        
        cart, was_removed = cart_service.remove_item("user123", "BOOK-001")
        
        assert len(cart.items) == 0
        assert was_removed is True
        mock_repo.upsert_cart.assert_called_once()
    
    def test_clear_cart(self, cart_service, mock_repo):
        """Test clearing cart"""
        mock_repo.delete_cart.return_value = True
        
        success = cart_service.clear_cart("user123")
        
        assert success is True
        mock_repo.delete_cart.assert_called_once_with("user123")
    
    def test_update_item_price(self, cart_service, mock_repo):
        """Test updating item price across carts"""
        mock_repo.update_item_price.return_value = 5
        
        count = cart_service.update_item_price("BOOK-001", 24.99, "USD")
        
        assert count == 5
        mock_repo.update_item_price.assert_called_once_with("BOOK-001", 24.99, "USD")
    
    def test_idempotency_check(self, cart_service, mock_repo):
        """Test event idempotency checking"""
        mock_repo.check_event_processed.return_value = True
        
        is_processed = cart_service.is_event_processed("event-123")
        
        assert is_processed is True
        mock_repo.check_event_processed.assert_called_once_with("event-123")
    
    def test_mark_event_processed(self, cart_service, mock_repo):
        """Test marking event as processed"""
        mock_repo.mark_event_processed.return_value = True
        
        success = cart_service.mark_event_processed("event-123", "catalog.updated")
        
        assert success is True
        mock_repo.mark_event_processed.assert_called_once_with("event-123", "catalog.updated")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])




