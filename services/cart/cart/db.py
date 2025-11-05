"""
MongoDB connection and database operations
"""
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, IndexModel
from pymongo.errors import ConnectionFailure, OperationFailure, DuplicateKeyError
from pymongo.collection import Collection
from pymongo.database import Database
import structlog

from cart.config import Config


logger = structlog.get_logger()


class MongoDB:
    """MongoDB connection manager"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        
    def connect(self) -> None:
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(
                self.config.mongo_uri,
                serverSelectionTimeoutMS=self.config.mongo_timeout_ms,
                connectTimeoutMS=self.config.mongo_timeout_ms,
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            self.db = self.client[self.config.mongo_db]
            
            # Create indexes
            self._create_indexes()
            
            logger.info("Connected to MongoDB", 
                       uri=self.config.mongo_uri,
                       database=self.config.mongo_db)
            
        except ConnectionFailure as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise
    
    def _create_indexes(self) -> None:
        """Create necessary indexes on collections"""
        try:
            # Carts collection indexes
            carts = self.db.carts
            carts.create_index([("user_id", ASCENDING)], unique=True)
            carts.create_index([("updated_at", ASCENDING)])
            
            # Event offsets collection for idempotency (with TTL)
            event_offsets = self.db.event_offsets
            event_offsets.create_index([("event_id", ASCENDING)], unique=True)
            event_offsets.create_index(
                [("created_at", ASCENDING)], 
                expireAfterSeconds=self.config.event_ttl_seconds
            )
            
            logger.info("Database indexes created")
            
        except Exception as e:
            logger.warning("Error creating indexes", error=str(e))
    
    def close(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def is_healthy(self) -> bool:
        """Check if MongoDB connection is healthy"""
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
        except Exception as e:
            logger.error("MongoDB health check failed", error=str(e))
        return False
    
    @property
    def carts(self) -> Collection:
        """Get carts collection"""
        return self.db.carts
    
    @property
    def event_offsets(self) -> Collection:
        """Get event_offsets collection"""
        return self.db.event_offsets


class CartRepository:
    """Repository for cart operations"""
    
    def __init__(self, mongodb: MongoDB):
        self.db = mongodb
        self.logger = structlog.get_logger().bind(component="cart_repository")
    
    def get_cart(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cart for a user"""
        start_time = time.time()
        try:
            cart = self.db.carts.find_one({"user_id": user_id})
            
            duration = time.time() - start_time
            db_operation_duration.labels(operation="get_cart").observe(duration)
            db_operations_total.labels(operation="get_cart", status="success").inc()
            
            self.logger.debug("Get cart", user_id=user_id, found=cart is not None)
            return cart
            
        except Exception as e:
            db_operations_total.labels(operation="get_cart", status="error").inc()
            self.logger.error("Error getting cart", user_id=user_id, error=str(e))
            raise
    
    def upsert_cart(self, cart: Dict[str, Any]) -> None:
        """Create or update a cart"""
        start_time = time.time()
        try:
            cart["updated_at"] = datetime.utcnow()
            
            self.db.carts.update_one(
                {"user_id": cart["user_id"]},
                {"$set": cart},
                upsert=True
            )
            
            duration = time.time() - start_time
            db_operation_duration.labels(operation="upsert_cart").observe(duration)
            db_operations_total.labels(operation="upsert_cart", status="success").inc()
            
            self.logger.info("Cart upserted", user_id=cart["user_id"])
            
        except Exception as e:
            db_operations_total.labels(operation="upsert_cart", status="error").inc()
            self.logger.error("Error upserting cart", user_id=cart.get("user_id"), error=str(e))
            raise
    
    def delete_cart(self, user_id: str) -> bool:
        """Delete a cart"""
        start_time = time.time()
        try:
            result = self.db.carts.delete_one({"user_id": user_id})
            
            duration = time.time() - start_time
            db_operation_duration.labels(operation="delete_cart").observe(duration)
            db_operations_total.labels(operation="delete_cart", status="success").inc()
            
            deleted = result.deleted_count > 0
            self.logger.info("Cart deleted", user_id=user_id, deleted=deleted)
            return deleted
            
        except Exception as e:
            db_operations_total.labels(operation="delete_cart", status="error").inc()
            self.logger.error("Error deleting cart", user_id=user_id, error=str(e))
            raise
    
    def update_item_price(self, sku: str, price: float, currency: str) -> int:
        """Update price for items with a specific SKU across all carts"""
        start_time = time.time()
        try:
            result = self.db.carts.update_many(
                {"items.sku": sku},
                {
                    "$set": {
                        "items.$[elem].price": price,
                        "items.$[elem].currency": currency,
                        "updated_at": datetime.utcnow()
                    }
                },
                array_filters=[{"elem.sku": sku}]
            )
            
            duration = time.time() - start_time
            db_operation_duration.labels(operation="update_item_price").observe(duration)
            db_operations_total.labels(operation="update_item_price", status="success").inc()
            
            updated_count = result.modified_count
            self.logger.info("Item price updated", sku=sku, carts_updated=updated_count)
            return updated_count
            
        except Exception as e:
            db_operations_total.labels(operation="update_item_price", status="error").inc()
            self.logger.error("Error updating item price", sku=sku, error=str(e))
            raise
    
    def check_event_processed(self, event_id: str) -> bool:
        """Check if an event has already been processed (idempotency)"""
        try:
            return self.db.event_offsets.find_one({"event_id": event_id}) is not None
        except Exception as e:
            self.logger.error("Error checking event processed", event_id=event_id, error=str(e))
            return False
    
    def mark_event_processed(self, event_id: str, event_type: str) -> bool:
        """Mark an event as processed for idempotency"""
        try:
            self.db.event_offsets.insert_one({
                "event_id": event_id,
                "event_type": event_type,
                "created_at": datetime.utcnow()
            })
            self.logger.debug("Event marked as processed", event_id=event_id)
            return True
        except DuplicateKeyError:
            # Event already processed
            self.logger.debug("Event already processed", event_id=event_id)
            return False
        except Exception as e:
            self.logger.error("Error marking event processed", event_id=event_id, error=str(e))
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get cart statistics for metrics"""
        try:
            total_carts = self.db.carts.count_documents({})
            
            # Calculate total items across all carts
            pipeline = [
                {"$unwind": "$items"},
                {"$group": {"_id": None, "total": {"$sum": "$items.qty"}}}
            ]
            result = list(self.db.carts.aggregate(pipeline))
            total_items = result[0]["total"] if result else 0
            
            return {
                "total_carts": total_carts,
                "total_items": total_items
            }
        except Exception as e:
            self.logger.error("Error getting stats", error=str(e))
            return {"total_carts": 0, "total_items": 0}




