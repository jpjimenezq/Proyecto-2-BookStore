"""
gRPC client for Order Service
Optional - for validating orders before processing payment
"""
import os
import sys
import grpc
import structlog

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'contracts', 'gen', 'python'))
from contracts.gen.python import order_pb2, order_pb2_grpc

from payment.config import config


logger = structlog.get_logger()


def get_order_client():
    """Get Order Service gRPC client"""
    order_service_url = config.order_service_url
    channel = grpc.insecure_channel(order_service_url)
    return order_pb2_grpc.OrderServiceStub(channel)


def validate_order(order_id: str, expected_amount: float = None) -> bool:
    """
    Validate that the order exists and optionally check amount
    
    Args:
        order_id: Order identifier
        expected_amount: Expected order amount in dollars (optional)
        
    Returns:
        True if order is valid, False otherwise
    """
    try:
        client = get_order_client()
        response = client.GetOrder(order_pb2.GetOrderRequest(order_id=order_id))
        
        if not response or not response.order_id:
            logger.warning("Order not found", order_id=order_id)
            return False
        
        # Verify amount if provided
        if expected_amount is not None:
            actual_amount = response.total_amount.amount / 100.0
            if abs(actual_amount - expected_amount) > 0.01:
                logger.warning(
                    "Order amount mismatch",
                    order_id=order_id,
                    expected=expected_amount,
                    actual=actual_amount
                )
                return False
        
        logger.info("Order validated", order_id=order_id)
        return True
        
    except grpc.RpcError as e:
        logger.error("Failed to validate order", order_id=order_id, error=str(e))
        return False
    except Exception as e:
        logger.error("Unexpected error validating order", order_id=order_id, error=str(e))
        return False


def update_order_status(order_id: str, status: str) -> bool:
    """
    Update the status of an order
    
    Args:
        order_id: The order ID to update
        status: The new status (e.g., "COMPLETED", "CANCELLED")
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        client = get_order_client()
        
        request = order_pb2.UpdateOrderStatusRequest(
            order_id=order_id,
            status=status
        )
        
        response = client.UpdateOrderStatus(request)
        
        if response.success:
            logger.info("Order status updated", order_id=order_id, status=status)
            return True
        else:
            logger.warning(
                "Order status update failed",
                order_id=order_id,
                status=status,
                message=response.message
            )
            return False
            
    except grpc.RpcError as e:
        logger.error(
            "gRPC error updating order status",
            order_id=order_id,
            code=e.code(),
            details=e.details()
        )
        return False
    except Exception as e:
        logger.error("Error updating order status", order_id=order_id, error=str(e))
        return False
