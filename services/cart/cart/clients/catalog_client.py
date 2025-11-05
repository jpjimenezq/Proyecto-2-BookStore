"""
Simple gRPC client for Catalog service
"""
import grpc
import os
import sys
import structlog

# Add contracts path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'contracts', 'gen', 'python'))

from contracts.gen.python import catalog_pb2, catalog_pb2_grpc

logger = structlog.get_logger()


class CatalogClient:
    """Simple client to communicate with Catalog service"""
    
    def __init__(self, catalog_url=None):
        """
        Initialize Catalog client
        
        Args:
            catalog_url: Catalog service URL (default: from env or localhost:50051)
        """
        self.catalog_url = catalog_url or os.getenv('CATALOG_SERVICE_URL', 'localhost:50051')
        self.channel = None
        self.stub = None
        self._connect()
    
    def _connect(self):
        """Establish gRPC connection to Catalog service"""
        try:
            self.channel = grpc.insecure_channel(self.catalog_url)
            self.stub = catalog_pb2_grpc.CatalogServiceStub(self.channel)
            logger.info("Catalog client connected", url=self.catalog_url)
        except Exception as e:
            logger.error("Failed to connect to Catalog service", error=str(e), url=self.catalog_url)
            raise
    
    def get_book(self, sku: str):
        """
        Get book details from Catalog
        
        Args:
            sku: Book SKU
            
        Returns:
            Book details or None if not found
        """
        try:
            request = catalog_pb2.GetBookRequest(sku=sku)
            response = self.stub.GetBook(request, timeout=5.0)
            
            book = response.book
            logger.info("Book fetched from catalog", sku=sku, title=book.title)
            
            return {
                'sku': book.sku,
                'title': book.title,
                'author': book.author,
                'price': book.price.amount / 100.0,  # Convert from cents
                'currency': book.price.currency,
                'category': book.category,
                'active': book.active
            }
            
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                logger.warning("Book not found in catalog", sku=sku)
                return None
            else:
                logger.error("Error fetching book from catalog", 
                           sku=sku, 
                           error=str(e), 
                           code=e.code())
                raise
        except Exception as e:
            logger.error("Unexpected error fetching book", sku=sku, error=str(e))
            raise
    
    def close(self):
        """Close gRPC connection"""
        if self.channel:
            self.channel.close()
            logger.info("Catalog client connection closed")


# Singleton instance
_catalog_client = None


def get_catalog_client():
    """Get or create catalog client singleton"""
    global _catalog_client
    if _catalog_client is None:
        _catalog_client = CatalogClient()
    return _catalog_client

