"""
Simple gRPC client for Cart service
"""
import grpc
import os
import sys

# Add contracts path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'contracts', 'gen', 'python'))

from contracts.gen.python import cart_pb2, cart_pb2_grpc


class CartClient:
    """Simple client to communicate with Cart service"""
    
    def __init__(self, cart_url=None):
        self.cart_url = cart_url or os.getenv('CART_SERVICE_URL', 'localhost:50052')
        self.channel = None
        self.stub = None
        self._connect()
    
    def _connect(self):
        """Establish gRPC connection"""
        try:
            self.channel = grpc.insecure_channel(self.cart_url)
            self.stub = cart_pb2_grpc.CartServiceStub(self.channel)
            print(f"[CartClient] Connected to {self.cart_url}", flush=True)
        except Exception as e:
            print(f"[CartClient] Failed to connect: {e}", flush=True)
            raise
    
    def clear_cart(self, user_id: str):
        """Clear user's cart after successful order"""
        try:
            request = cart_pb2.ClearCartRequest(user_id=user_id)
            response = self.stub.ClearCart(request, timeout=5.0)
            
            print(f"[CartClient] Cart cleared for user: {user_id}", flush=True)
            return response.success
            
        except grpc.RpcError as e:
            print(f"[CartClient] Error clearing cart: {e.code()} - {e.details()}", flush=True)
            # Don't fail the order if cart clearing fails
            return False
    
    def close(self):
        """Close connection"""
        if self.channel:
            self.channel.close()


# Singleton
_cart_client = None

def get_cart_client():
    global _cart_client
    if _cart_client is None:
        _cart_client = CartClient()
    return _cart_client

