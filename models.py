from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Seller(Base):
    __tablename__ = "sellers"

    id = Column(Integer, primary_key=True, index=True)
    shop_name = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    password = Column(String)
    logo_url = Column(String, default="https://placehold.co/100x100?text=Logo")
    
    fulfillment_plan = Column(String, default="Biz_Gonderirik")
    billing_plan = Column(String, default="Faiz_7")

    products = relationship("Product", back_populates="seller")
    alerts = relationship("StockAlert", back_populates="seller")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    address = Column(Text)
    password = Column(String)

    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    title = Column(String)
    description = Column(Text)
    price = Column(Float)
    stock_quantity = Column(Integer, default=0)
    location = Column(String, default="Gozlemede")
    seller_id = Column(Integer, ForeignKey("sellers.id"))

    seller = relationship("Seller", back_populates="products")
    orders = relationship("Order", back_populates="product")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    status = Column(String, default="Gozleyir")
    delivery_note = Column(String, default="Biz Catdiririq")
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")
    product = relationship("Product", back_populates="orders")

class StockAlert(Base):
    __tablename__ = "stock_alerts"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"))
    sku = Column(String)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    seller = relationship("Seller", back_populates="alerts")