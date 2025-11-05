import grpc
from concurrent import futures
import time
import sys
import os

# Add contracts path for proto imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'contracts', 'gen', 'python'))

from contracts.gen.python import order_pb2, order_pb2_grpc, common_pb2
from order.services.order_service import OrderServiceLogic
from order.db import engine, Base
from order.models import order_model
from order.models import order_item_model
from order.clients.catalog_client import get_catalog_client
from order.clients.cart_client import get_cart_client

def create_tables():
    max_retries = 10
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            print(f"Intento {attempt + 1} de crear tablas...", flush=True)
            Base.metadata.create_all(bind=engine)
            print("Tablas creadas exitosamente", flush=True)
            return True
        except Exception as e:
            print(f"Error al crear tablas (intento {attempt + 1}): {e}", flush=True)
            if attempt < max_retries - 1:
                print(f"Reintentando en {retry_delay} segundos...", flush=True)
                time.sleep(retry_delay)
            else:
                print("No se pudieron crear las tablas después de todos los intentos", flush=True)
                return False
    return False

class OrderService(order_pb2_grpc.OrderServiceServicer):
    def __init__(self):
        self.logic = OrderServiceLogic()

    def CreateOrder(self, request, context):
        print(f"[CrearOrden] Recibida solicitud: usuario={request.user_id}, items={len(request.items)}", flush=True)

        # Validate products with Catalog service
        catalog_client = get_catalog_client()
        validated_items = []
        
        for i in request.items:
            product_id = i.product_id
            
            # Get real product info from catalog
            try:
                book = catalog_client.get_book(product_id)
                
                if not book:
                    print(f"[CrearOrden]  Producto no encontrado: {product_id}", flush=True)
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Product {product_id} not found in catalog")
                    return order_pb2.CreateOrderResponse()
                
                if not book['active']:
                    print(f"[CrearOrden]  Producto no disponible: {product_id}", flush=True)
                    context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                    context.set_details(f"Product {product_id} is not available")
                    return order_pb2.CreateOrderResponse()
                
                # Use real price from catalog (prevent price manipulation)
                real_price = book['price']
                requested_price = i.unit_price.amount / 100.0
                
                # Allow small difference due to timing (price updates)
                if abs(real_price - requested_price) > 0.01:
                    print(f"[CrearOrden]  Diferencia de precio: {product_id}, esperado={real_price}, recibido={requested_price}", flush=True)
                    # Use real price from catalog
                    unit_price = real_price
                else:
                    unit_price = requested_price
                
                validated_items.append({
                    "product_id": product_id,
                    "quantity": i.quantity,
                    "unit_price": unit_price
                })
                
                print(f"[CrearOrden]  Producto validado: {product_id}, precio=${unit_price}", flush=True)
                
            except Exception as e:
                print(f"[CrearOrden]  Error validando producto {product_id}: {e}", flush=True)
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                context.set_details(f"Could not validate product {product_id}. Catalog service unavailable.")
                return order_pb2.CreateOrderResponse()

        # Create order with validated items
        order = self.logic.create_order(
            user_id=request.user_id,
            items=validated_items,
            payment_method=request.payment_method,
            address=request.address
        )

        print(f"[CrearOrden] Orden creada exitosamente: id={order['order_id']}, total=${order['total_amount']}", flush=True)
        
        # Clear cart after successful order (async, don't fail if it errors)
        try:
            cart_client = get_cart_client()
            cart_cleared = cart_client.clear_cart(request.user_id)
            if cart_cleared:
                print(f"[CrearOrden]  Carrito limpiado para usuario: {request.user_id}", flush=True)
            else:
                print(f"[CrearOrden]  No se pudo limpiar carrito para usuario: {request.user_id}", flush=True)
        except Exception as e:
            print(f"[CrearOrden]  Error limpiando carrito (no crítico): {e}", flush=True)
            # Continue anyway, order was created successfully

        return order_pb2.CreateOrderResponse(
            order_id=order["order_id"],
            status=order["status"],
            total_amount=common_pb2.Money(
                currency="USD",
                amount=int(order["total_amount"] * 100),  # Convert to cents
                decimal_places=2
            )
        )


    def GetOrder(self, request, context):
        print(f"[ObtenerOrden] Buscando orden: id={request.order_id}", flush=True)

        order = self.logic.get_order(request.order_id)
        if not order:
            print(f"[ObtenerOrden] Orden no encontrada: id={request.order_id}", flush=True)
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('Order not found')
            return order_pb2.GetOrderResponse()

        print(f"[ObtenerOrden] Orden encontrada: id={order['order_id']}, usuario={order['user_id']}, items={len(order['items'])}", flush=True)

        response = order_pb2.GetOrderResponse(
            order_id=order["order_id"],
            user_id=order["user_id"],
            payment_method=order["payment_method"],
            address=order["address"],
            status=order["status"],
            total_amount=common_pb2.Money(
                currency="USD",
                amount=int(order["total_amount"] * 100),  # Convert to cents
                decimal_places=2
            ),
            created_at=int(order["created_at"].timestamp()) if hasattr(order["created_at"], 'timestamp') else 0
        )

        for item in order["items"]:
            order_item = response.items.add()
            order_item.product_id = item["product_id"]
            order_item.quantity = item["quantity"]
            order_item.unit_price.CopyFrom(common_pb2.Money(
                currency="USD",
                amount=int(item["unit_price"] * 100),  # Convert to cents
                decimal_places=2
            ))

        return response

    def UpdateOrderStatus(self, request, context):
        print(f"[ActualizarEstado] Solicitud para orden: {request.order_id} -> {request.status}", flush=True)

        result = self.logic.update_order_status(request.order_id, request.status)

        if result["success"]:
            print(f"[ActualizarEstado] Estado actualizado correctamente: {request.order_id}", flush=True)
            return order_pb2.UpdateOrderStatusResponse(
                order_id=result["order_id"],
                status=result["status"],
                success=True,
                message=result["message"]
            )
        else:
            print(f"[ActualizarEstado] Error: {result['message']}", flush=True)
            return order_pb2.UpdateOrderStatusResponse(
                order_id=request.order_id,
                status="",
                success=False,
                message=result["message"]
            )

    def ListOrders(self, request, context):
        """Listar todas las órdenes con paginación"""
        print(f"[ListarOrdenes] Solicitando página {request.page}, tamaño {request.page_size}", flush=True)
        
        page = request.page if request.page > 0 else 1
        page_size = request.page_size if request.page_size > 0 else 10
        
        result = self.logic.list_orders(page, page_size)
        
        response = order_pb2.ListOrdersResponse(
            total_count=result["total_count"],
            page=result["page"],
            page_size=result["page_size"]
        )
        
        for order in result["orders"]:
            order_summary = response.orders.add()
            order_summary.order_id = order["order_id"]
            order_summary.user_id = order["user_id"]
            order_summary.total_amount.CopyFrom(common_pb2.Money(
                currency="USD",
                amount=int(order["total_amount"] * 100),  # Convert to cents
                decimal_places=2
            ))
            order_summary.status = order["status"]
            order_summary.created_at = int(order["created_at"].timestamp()) if hasattr(order["created_at"], 'timestamp') else 0
            
            # Agregar items de la orden
            for item in order.get("items", []):
                order_item = order_summary.items.add()
                order_item.product_id = item["product_id"]
                order_item.quantity = item["quantity"]
                order_item.unit_price.CopyFrom(common_pb2.Money(
                    currency="USD",
                    amount=int(item["unit_price"] * 100),  # Convert to cents
                    decimal_places=2
                ))
        
        print(f"[ListarOrdenes] Devolviendo {len(result['orders'])} órdenes", flush=True)
        return response

    def GetOrdersByUser(self, request, context):
        """Obtener órdenes de un usuario específico"""
        print(f"[OrdenesPorUsuario] Usuario: {request.user_id}, página {request.page}", flush=True)
        
        page = request.page if request.page > 0 else 1
        page_size = request.page_size if request.page_size > 0 else 10
        
        result = self.logic.get_orders_by_user(request.user_id, page, page_size)
        
        response = order_pb2.GetOrdersByUserResponse(
            total_count=result["total_count"],
            user_id=result["user_id"]
        )
        
        for order in result["orders"]:
            order_summary = response.orders.add()
            order_summary.order_id = order["order_id"]
            order_summary.user_id = order["user_id"]
            order_summary.total_amount.CopyFrom(common_pb2.Money(
                currency="USD",
                amount=int(order["total_amount"] * 100),  # Convert to cents
                decimal_places=2
            ))
            order_summary.status = order["status"]
            order_summary.created_at = int(order["created_at"].timestamp()) if hasattr(order["created_at"], 'timestamp') else 0
            
            # Agregar items de la orden
            for item in order.get("items", []):
                order_item = order_summary.items.add()
                order_item.product_id = item["product_id"]
                order_item.quantity = item["quantity"]
                order_item.unit_price.CopyFrom(common_pb2.Money(
                    currency="USD",
                    amount=int(item["unit_price"] * 100),  # Convert to cents
                    decimal_places=2
                ))
        
        print(f"[OrdenesPorUsuario] Usuario {request.user_id} tiene {len(result['orders'])} órdenes", flush=True)
        return response

def serve():
    print("Iniciando servidor gRPC...", flush=True)
    if not create_tables():
        print("No se pudo inicializar la base de datos. Saliendo...", flush=True)
        sys.exit(1)

    port = os.getenv('GRPC_PORT', '50053')
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    order_pb2_grpc.add_OrderServiceServicer_to_server(OrderService(), server)
    server.add_insecure_port(f'[::]:{port}')
    print(f"Order gRPC server running on port {port}", flush=True)
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()