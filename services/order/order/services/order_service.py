from order.db import SessionLocal
from order.models.order_model import Order
from order.models.order_item_model import OrderItem
import uuid
from datetime import datetime

class OrderServiceLogic:
    def __init__(self):
        self.db = SessionLocal()

    def create_order(self, user_id, items, payment_method, address):
        print(f"[ServicioOrden] Iniciando creacion de orden para usuario: {user_id}", flush=True)

        total_amount = 0.0

        # Calcular total y validar items
        normalized_items = []
        for it in items:
            unit_price = it.get('unit_price', it.get('price', 0.0))
            try:
                unit_price = float(unit_price)
            except Exception:
                unit_price = 0.0
            try:
                quantity = int(it.get('quantity', 0))
            except Exception:
                quantity = 0

            normalized_item = {
                "product_id": it.get('product_id'),
                "quantity": quantity,
                "unit_price": unit_price
            }
            normalized_items.append(normalized_item)
            total_amount += unit_price * quantity

        order_id = str(uuid.uuid4())

        # Crear la orden
        order_obj = Order(
            order_id=order_id,
            user_id=user_id,
            payment_method=payment_method,
            address=address,
            status="CREATED",
            total_amount=total_amount,
            created_at=datetime.now()
        )

        self.db.add(order_obj)
        self.db.flush()  # Para obtener el order_id antes del commit

        # Crear los items de la orden
        for item_data in normalized_items:
            order_item = OrderItem(
                order_id=order_id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"]
            )
            self.db.add(order_item)

        self.db.commit()
        self.db.refresh(order_obj)

        print(f"[ServicioOrden] Orden guardada en BD: {order_obj.order_id}, total: ${total_amount}", flush=True)

        # Convertir items a formato dict para respuesta
        items_list = []
        for item in order_obj.order_items:
            items_list.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price
            })

        return {
            "order_id": order_obj.order_id,
            "status": order_obj.status,
            "total_amount": order_obj.total_amount,
            "items": items_list,
            "user_id": order_obj.user_id,
            "payment_method": order_obj.payment_method,
            "address": order_obj.address,
            "created_at": order_obj.created_at
        }

    def get_order(self, order_id):
        print(f"[ServicioOrden] Consultando orden en BD: {order_id}", flush=True)

        order = self.db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            print(f"[ServicioOrden] Orden no existe en BD: {order_id}", flush=True)
            return None

        # Convertir items a formato dict
        items_list = []
        for item in order.order_items:
            items_list.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price
            })

        return {
            "order_id": order.order_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "items": items_list,
            "user_id": order.user_id,
            "payment_method": order.payment_method,
            "address": order.address,
            "created_at": order.created_at
        }

    def update_order_status(self, order_id, new_status):
        print(f"[ServicioOrden] Actualizando estado de orden: {order_id} -> {new_status}", flush=True)

        # Validar estados permitidos
        valid_statuses = ["CREATED", "CONFIRMED", "CANCELLED"]
        if new_status not in valid_statuses:
            print(f"[ServicioOrden] Estado inválido: {new_status}", flush=True)
            return {"success": False, "message": f"Estado inválido: {new_status}"}

        order = self.db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            print(f"[ServicioOrden] Orden no existe para actualizar: {order_id}", flush=True)
            return {"success": False, "message": "Orden no encontrada"}

        old_status = order.status
        order.status = new_status

        try:
            self.db.commit()
            self.db.refresh(order)
            print(f"[ServicioOrden] Estado actualizado: {order_id} ({old_status} -> {new_status})", flush=True)
            return {
                "success": True,
                "message": "Estado actualizado correctamente",
                "order_id": order.order_id,
                "status": order.status
            }
        except Exception as e:
            self.db.rollback()
            print(f"[ServicioOrden] Error al actualizar estado: {e}", flush=True)
            return {"success": False, "message": f"Error al actualizar: {str(e)}"}

    def list_orders(self, page=1, page_size=10):
        """Listar todas las órdenes con paginación"""
        print(f"[ServicioOrden] Listando órdenes - página {page}, tamaño {page_size}", flush=True)

        offset = (page - 1) * page_size

        # Contar total de órdenes
        total_count = self.db.query(Order).count()

        # Obtener órdenes con paginación
        orders = self.db.query(Order).order_by(Order.created_at.desc()).offset(offset).limit(page_size).all()

        orders_list = []
        for order in orders:
            # Incluir items de la orden
            items_list = []
            for item in order.order_items:
                items_list.append({
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price
                })
            
            orders_list.append({
                "order_id": order.order_id,
                "user_id": order.user_id,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at,
                "items": items_list
            })

        print(f"[ServicioOrden] Encontradas {len(orders_list)} órdenes de {total_count} totales", flush=True)
        return {
            "orders": orders_list,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }

    def get_orders_by_user(self, user_id, page=1, page_size=10):
        """Obtener órdenes de un usuario específico"""
        print(f"[ServicioOrden] Consultando órdenes del usuario: {user_id}", flush=True)

        offset = (page - 1) * page_size

        # Contar órdenes del usuario
        total_count = self.db.query(Order).filter(Order.user_id == user_id).count()

        # Obtener órdenes del usuario con paginación
        orders = self.db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).offset(offset).limit(page_size).all()

        orders_list = []
        for order in orders:
            # Incluir items de la orden
            items_list = []
            for item in order.order_items:
                items_list.append({
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price
                })
            
            orders_list.append({
                "order_id": order.order_id,
                "user_id": order.user_id,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at,
                "items": items_list
            })

        print(f"[ServicioOrden] Usuario {user_id} tiene {len(orders_list)} órdenes de {total_count} totales", flush=True)
        return {
            "orders": orders_list,
            "total_count": total_count,
            "user_id": user_id
        }