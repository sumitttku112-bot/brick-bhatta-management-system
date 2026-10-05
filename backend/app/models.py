from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
from .database import Base
from datetime import datetime

class UserRole(str, enum.Enum):
    worker = "worker"
    supervisor = "supervisor"
    manager = "manager"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    name_hindi = Column(String, nullable=False)
    role = Column(String, nullable=False) # Store enum as string for flexibility
    role_hindi = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    initials = Column(String, nullable=False)
    
    # Optional extended details
    contact_person = Column(String, nullable=True)
    phone_number = Column(String, nullable=True, index=True) # Indexed for login lookup
    address = Column(String, nullable=True)
    party_type = Column(String, nullable=True)
    gst_number = Column(String, nullable=True)
    opening_balance = Column(Float, nullable=True)
    opening_balance_type = Column(String, nullable=True) # 'Dr' or 'Cr'
    credit_limit = Column(Float, nullable=True)
    password_hash = Column(String, nullable=True)

    sales = relationship("Sale", back_populates="creator")
    work_entries = relationship("Work", back_populates="creator")
    transactions = relationship("Transaction", foreign_keys="Transaction.party_id", back_populates="party")

class Sale(Base):
    __tablename__ = "sales"

    id = Column(String, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    customer_name_hindi = Column(String, nullable=False)
    customer_address = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    date = Column(DateTime, nullable=False)
    time = Column(DateTime, nullable=False)
    advance_payment = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    final_amount = Column(Float, default=0.0)
    remarks = Column(String, nullable=True)
    otp = Column(String, nullable=True)
    created_by = Column(String, ForeignKey("users.id"))

    creator = relationship("User", back_populates="sales")
    brick_entries = relationship("BrickEntry", back_populates="sale", cascade="all, delete-orphan")
    freight_details = relationship("FreightDetails", back_populates="sale", uselist=False, cascade="all, delete-orphan")

class BrickEntry(Base):
    __tablename__ = "brick_entries"

    id = Column(String, primary_key=True, index=True)
    sale_id = Column(String, ForeignKey("sales.id"))
    brick_type = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)

    sale = relationship("Sale", back_populates="brick_entries")

class FreightDetails(Base):
    __tablename__ = "freight_details"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sale_id = Column(String, ForeignKey("sales.id"), unique=True)
    type = Column(String, nullable=False)
    vehicle_number = Column(String, nullable=True)
    vehicle_name = Column(String, nullable=True)
    driver_name = Column(String, nullable=True)
    driver_phone = Column(String, nullable=True)
    rate_per_1000 = Column(Float, default=0.0)

    sale = relationship("Sale", back_populates="freight_details")

class Work(Base):
    __tablename__ = "work"

    id = Column(String, primary_key=True, index=True)
    labour_name = Column(String, nullable=False)
    labour_category = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    percentage = Column(Float, nullable=True)
    rate = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=True) # Optional link to creator

    creator = relationship("User", back_populates="work_entries")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    party_id = Column(String, ForeignKey("users.id"), nullable=True) # Link to Party (User) if registered
    party_name = Column(String, nullable=False) # Store name even if linked, or for unregistered parties
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False) # 'credit' or 'debit'
    category = Column(String, nullable=False) # 'Sales', 'Purchase', 'Labor Payment', etc.
    date = Column(DateTime, nullable=False)
    description = Column(String, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)

    party = relationship("User", foreign_keys=[party_id], back_populates="transactions")
    creator = relationship("User", foreign_keys=[created_by])

    # Relationships
    # user = relationship("User", back_populates="work_entries") # If we want to link directly to a User who IS the labour

class Name(Base):
    __tablename__ = "names"

    server_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    value = Column(String, nullable=True)
    group = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    gstin = Column(String, nullable=True)
    commission_percent = Column(Float, nullable=True)
