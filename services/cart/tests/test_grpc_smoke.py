"""
Smoke tests for gRPC cart service
"""
import pytest
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'contracts', 'gen', 'python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from contracts.gen.python import cart_pb2
from contracts.gen.python import cart_pb2_grpc
from contracts.gen.python import common_pb2
import grpc
from unittest.mock import Mock, MagicMock

from cart.grpc_server import CartServicer
from cart.service import CartService
from cart.events.publisher import EventPublisher


@pytest.fixture
def mock_cart_service():
    """Create mock cart service"""
    from cart.models import Cart, CartItem
    from datetime import datetime
    
    service = Mock(spec=CartService)
    
    # Mock get_cart to return empty cart
    def get_cart_mock(user_id):
        return Cart(user_id=user_id)
    
    # Mock add_item to return cart with item
    def add_item_mock(user_id, sku, qty, price, currency, title):
        cart = Cart(user_id=user_id)
        cart.add_or_update_item(sku, qty, price, currency, title)
        return cart, True
    
    # Mock remove_item
    def remove_item_mock(user_id, sku):
        cart = Cart(user_id=user_id)
        return cart, True
    
    # Mock clear_cart
    def clear_cart_mock(user_id):
        return True
    
    service.get_cart = Mock(side_effect=get_cart_mock)
    service.add_item = Mock(side_effect=add_item_mock)
    service.remove_item = Mock(side_effect=remove_item_mock)
    service.clear_cart = Mock(side_effect=clear_cart_mock)
    
    return service


@pytest.fixture
def mock_event_publisher():
    """Create mock event publisher"""
    publisher = Mock(spec=EventPublisher)
    publisher.publish_item_added = Mock()
    publisher.publish_item_removed = Mock()
    publisher.publish_cart_cleared = Mock()
    return publisher


@pytest.fixture
def cart_servicer(mock_cart_service, mock_event_publisher):
    """Create cart servicer for testing"""
    return CartServicer(mock_cart_service, mock_event_publisher)


class MockContext:
    """Mock gRPC context"""
    def __init__(self):
        self._code = None
        self._details = None
    
    def set_code(self, code):
        self._code = code
    
    def set_details(self, details):
        self._details = details


class TestCartGRPCSmoke:
    """Smoke tests for cart gRPC service"""
    
    def test_add_item(self, cart_servicer, mock_event_publisher):
        """Test AddItem gRPC method"""
        request = cart_pb2.AddItemRequest(
            user_id="user123",
            sku="BOOK-001",
            qty=2
        )
        context = MockContext()
        
        response = cart_servicer.AddItem(request, context)
        
        assert response.cart.user_id == "user123"
        assert len(response.cart.items) == 1
        assert response.cart.items[0].sku == "BOOK-001"
        assert response.cart.items[0].qty == 2
    
    def test_add_item_invalid_user_id(self, cart_servicer):
        """Test AddItem with missing user_id"""
        request = cart_pb2.AddItemRequest(
            user_id="",
            sku="BOOK-001",
            qty=2
        )
        context = MockContext()
        
        response = cart_servicer.AddItem(request, context)
        
        assert context._code == grpc.StatusCode.INVALID_ARGUMENT
        assert "user_id is required" in context._details
    
    def test_add_item_invalid_sku(self, cart_servicer):
        """Test AddItem with missing sku"""
        request = cart_pb2.AddItemRequest(
            user_id="user123",
            sku="",
            qty=2
        )
        context = MockContext()
        
        response = cart_servicer.AddItem(request, context)
        
        assert context._code == grpc.StatusCode.INVALID_ARGUMENT
        assert "sku is required" in context._details
    
    def test_add_item_invalid_quantity(self, cart_servicer):
        """Test AddItem with invalid quantity"""
        request = cart_pb2.AddItemRequest(
            user_id="user123",
            sku="BOOK-001",
            qty=0
        )
        context = MockContext()
        
        response = cart_servicer.AddItem(request, context)
        
        assert context._code == grpc.StatusCode.INVALID_ARGUMENT
        assert "qty must be positive" in context._details
    
    def test_get_cart(self, cart_servicer):
        """Test GetCart gRPC method"""
        request = cart_pb2.GetCartRequest(user_id="user123")
        context = MockContext()
        
        response = cart_servicer.GetCart(request, context)
        
        assert response.cart.user_id == "user123"
        assert isinstance(response.cart.items, list)
    
    def test_get_cart_invalid_user_id(self, cart_servicer):
        """Test GetCart with missing user_id"""
        request = cart_pb2.GetCartRequest(user_id="")
        context = MockContext()
        
        response = cart_servicer.GetCart(request, context)
        
        assert context._code == grpc.StatusCode.INVALID_ARGUMENT
        assert "user_id is required" in context._details
    
    def test_remove_item(self, cart_servicer, mock_event_publisher):
        """Test RemoveItem gRPC method"""
        request = cart_pb2.RemoveItemRequest(
            user_id="user123",
            sku="BOOK-001"
        )
        context = MockContext()
        
        response = cart_servicer.RemoveItem(request, context)
        
        assert response.cart.user_id == "user123"
        mock_event_publisher.publish_item_removed.assert_called_once()
    
    def test_remove_item_invalid_request(self, cart_servicer):
        """Test RemoveItem with invalid request"""
        request = cart_pb2.RemoveItemRequest(
            user_id="",
            sku="BOOK-001"
        )
        context = MockContext()
        
        response = cart_servicer.RemoveItem(request, context)
        
        assert context._code == grpc.StatusCode.INVALID_ARGUMENT
    
    def test_clear_cart(self, cart_servicer, mock_event_publisher):
        """Test ClearCart gRPC method"""
        request = cart_pb2.ClearCartRequest(user_id="user123")
        context = MockContext()
        
        response = cart_servicer.ClearCart(request, context)
        
        assert response.success is True
        mock_event_publisher.publish_cart_cleared.assert_called_once()
    
    def test_clear_cart_invalid_user_id(self, cart_servicer):
        """Test ClearCart with missing user_id"""
        request = cart_pb2.ClearCartRequest(user_id="")
        context = MockContext()
        
        response = cart_servicer.ClearCart(request, context)
        
        assert context._code == grpc.StatusCode.INVALID_ARGUMENT
        assert response.success is False
    
    def test_health(self, cart_servicer):
        """Test Health check method"""
        request = common_pb2.Empty()
        context = MockContext()
        
        response = cart_servicer.Health(request, context)
        
        assert response.status == common_pb2.HealthStatus.SERVING
        assert response.service == "cart"
        assert response.version == "1.0.0"
    
    def test_full_cart_flow(self, cart_servicer, mock_event_publisher):
        """Test complete cart flow: add, get, remove, clear"""
        context = MockContext()
        
        # Add item
        add_req = cart_pb2.AddItemRequest(
            user_id="user123",
            sku="BOOK-001",
            qty=2
        )
        add_resp = cart_servicer.AddItem(add_req, context)
        assert len(add_resp.cart.items) == 1
        
        # Get cart
        get_req = cart_pb2.GetCartRequest(user_id="user123")
        get_resp = cart_servicer.GetCart(get_req, context)
        assert get_resp.cart.user_id == "user123"
        
        # Remove item
        remove_req = cart_pb2.RemoveItemRequest(
            user_id="user123",
            sku="BOOK-001"
        )
        remove_resp = cart_servicer.RemoveItem(remove_req, context)
        assert remove_resp.cart.user_id == "user123"
        
        # Clear cart
        clear_req = cart_pb2.ClearCartRequest(user_id="user123")
        clear_resp = cart_servicer.ClearCart(clear_req, context)
        assert clear_resp.success is True
        
        # Verify events were published
        assert mock_event_publisher.publish_item_added.called
        assert mock_event_publisher.publish_item_removed.called
        assert mock_event_publisher.publish_cart_cleared.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

