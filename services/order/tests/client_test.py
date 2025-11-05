import grpc
import sys
import os

# Agregar el path del proyecto
sys.path.append('/app')

from app.grpc import order_pb2, order_pb2_grpc
import time

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = order_pb2_grpc.OrderServiceStub(channel)

    print(" INICIANDO PRUEBAS DEL MICROSERVICIO ORDER\n")

    # ==================== CREAR PRIMERA ORDEN ====================
    print("1️⃣ CREANDO PRIMERA ORDEN...")
    response1 = stub.CreateOrder(order_pb2.CreateOrderRequest(
        user_id="user_001",
        items=[
            order_pb2.OrderItem(product_id="laptop_gaming", quantity=1, unit_price=1200.99),
            order_pb2.OrderItem(product_id="mouse_rgb", quantity=2, unit_price=45.50)
        ],
        payment_method="credit_card",
        address="Calle Principal 123, Bogotá"
    ))
    print(f" Orden creada: {response1.order_id}")
    print(f"   Estado: {response1.status}")
    print(f"   Total: ${response1.total_amount}\n")

    # ==================== CREAR SEGUNDA ORDEN ====================
    print("2️⃣ CREANDO SEGUNDA ORDEN (OTRO USUARIO)...")
    response2 = stub.CreateOrder(order_pb2.CreateOrderRequest(
        user_id="user_002",
        items=[
            order_pb2.OrderItem(product_id="teclado_mecanico", quantity=1, unit_price=150.00),
            order_pb2.OrderItem(product_id="monitor_4k", quantity=1, unit_price=800.00)
        ],
        payment_method="paypal",
        address="Avenida Siempre Viva 742, Medellín"
    ))
    print(f" Orden creada: {response2.order_id}")
    print(f"   Estado: {response2.status}")
    print(f"   Total: ${response2.total_amount}\n")

    # ==================== OBTENER ORDEN ESPECÍFICA ====================
    print("3️⃣ OBTENIENDO DETALLES DE LA PRIMERA ORDEN...")
    get_response = stub.GetOrder(order_pb2.GetOrderRequest(order_id=response1.order_id))
    print(f" Orden encontrada: {get_response.order_id}")
    print(f"   Usuario: {get_response.user_id}")
    print(f"   Estado: {get_response.status}")
    print(f"   Total: ${get_response.total_amount}")
    print(f"   Items:")
    for item in get_response.items:
        print(f"     - {item.product_id}: {item.quantity} x ${item.unit_price}")
    print()

    # ==================== ACTUALIZAR ESTADO ====================
    print("4️⃣ ACTUALIZANDO ESTADO DE LA PRIMERA ORDEN...")
    update_response = stub.UpdateOrderStatus(order_pb2.UpdateOrderStatusRequest(
        order_id=response1.order_id,
        status="CONFIRMED"
    ))
    print(f" Estado actualizado: {update_response.order_id}")
    print(f"   Nuevo estado: {update_response.status}")
    print(f"   Éxito: {update_response.success}")
    print(f"   Mensaje: {update_response.message}\n")

    # ==================== LISTAR TODAS LAS ÓRDENES ====================
    print("5️⃣ LISTANDO TODAS LAS ÓRDENES...")
    list_response = stub.ListOrders(order_pb2.ListOrdersRequest(
        page=1,
        page_size=10
    ))
    print(f" Total de órdenes: {list_response.total_count}")
    print(f"   Página: {list_response.page}/{list_response.page_size}")
    print("   Órdenes encontradas:")
    for order in list_response.orders:
        print(f"     - {order.order_id}: {order.user_id} | ${order.total_amount} | {order.status}")
    print()

    # ==================== OBTENER ÓRDENES POR USUARIO ====================
    print("6️⃣ OBTENIENDO ÓRDENES DEL USUARIO 'user_001'...")
    user_orders = stub.GetOrdersByUser(order_pb2.GetOrdersByUserRequest(
        user_id="user_001",
        page=1,
        page_size=5
    ))
    print(f" Usuario: {user_orders.user_id}")
    print(f"   Total órdenes: {len(user_orders.orders)}")
    print("   Sus órdenes:")
    for order in user_orders.orders:
        print(f"     - {order.order_id}: ${order.total_amount} | {order.status}")
    print()

    # ==================== PROBAR ACTUALIZACIÓN CON ESTADO INVÁLIDO ====================
    print("7️⃣ PROBANDO ACTUALIZACIÓN CON ESTADO INVÁLIDO...")
    try:
        invalid_update = stub.UpdateOrderStatus(order_pb2.UpdateOrderStatusRequest(
            order_id=response1.order_id,
            status="ESTADO_INEXISTENTE"
        ))
        print(f" Debería haber fallado: {invalid_update.message}")
    except grpc.RpcError as e:
        print(f" Error esperado: {e.details()}")
    print()

    # ==================== PROBAR OBTENER ORDEN INEXISTENTE ====================
    print("8️⃣ PROBANDO OBTENER ORDEN INEXISTENTE...")
    try:
        fake_order = stub.GetOrder(order_pb2.GetOrderRequest(order_id="orden-inexistente-123"))
        print(f" Debería haber fallado")
    except grpc.RpcError as e:
        print(f" Error esperado: {e.details()}")
    print()

    print(" TODAS LAS PRUEBAS COMPLETADAS!")

if __name__ == "__main__":
    run()
