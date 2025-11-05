from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from order.db import Base
import uuid

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    payment_method = Column(String)
    address = Column(String)
    status = Column(String, default="CREATED")
    total_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relación con OrderItems
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
