"""
Simple gRPC client for Catalog service
"""
import grpc
import os
import sys

# Add contracts path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'contracts', 'gen', 'python'))

from contracts.gen.python import catalog_pb2, catalog_pb2_grpc


class CatalogClient:
    """Simple client to communicate with Catalog service"""
    
    def __init__(self, catalog_url=None):
        self.catalog_url = catalog_url or os.getenv('CATALOG_SERVICE_URL', 'localhost:50051')
        self.channel = None
        self.stub = None
        self._connect()
    
    def _connect(self):
        """Establish gRPC connection"""
        try:
            self.channel = grpc.insecure_channel(self.catalog_url)
            self.stub = catalog_pb2_grpc.CatalogServiceStub(self.channel)
            print(f"[CatalogClient] Connected to {self.catalog_url}", flush=True)
        except Exception as e:
            print(f"[CatalogClient] Failed to connect: {e}", flush=True)
            raise
    
    def get_book(self, sku: str):
        """Get book details from Catalog"""
        try:
            request = catalog_pb2.GetBookRequest(sku=sku)
            response = self.stub.GetBook(request, timeout=5.0)
            
            book = response.book
            return {
                'sku': book.sku,
                'title': book.title,
                'author': book.author,
                'price': book.price.amount / 100.0,
                'currency': book.price.currency,
                'category': book.category,
                'active': book.active
            }
            
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                print(f"[CatalogClient] Book not found: {sku}", flush=True)
                return None
            else:
                print(f"[CatalogClient] Error: {e.code()} - {e.details()}", flush=True)
                raise
    
    def close(self):
        """Close connection"""
        if self.channel:
            self.channel.close()


# Singleton
_catalog_client = None

def get_catalog_client():
    global _catalog_client
    if _catalog_client is None:
        _catalog_client = CatalogClient()
    return _catalog_client

