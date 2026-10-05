from sqlalchemy.orm import Session
from . import models, schemas, security
import uuid
from typing import List, Optional
from datetime import datetime, timedelta
import secrets
import hashlib

# --- User CRUD ---
def get_users_for_role(db: Session, user_id: str, role: str, skip: int = 0, limit: int = 100):
    """
    Get users based on role:
    - Admin: Returns all users
    - Kaccha/Pakka Muneem: Returns only the current user (themselves)
    """
    query = db.query(models.User)
    
    # Admin sees all users
    if role == "Admin":
        return query.offset(skip).limit(limit).all()
    
    # Muneems only see themselves
    return query.filter(models.User.id == user_id).offset(skip).limit(limit).all()

# --- Name CRUD ---
def get_name(db: Session, server_id: str):
    return db.query(models.Name).filter(models.Name.server_id == server_id).first()

def get_names(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Name).offset(skip).limit(limit).all()

def get_names_for_user(db: Session, user_id: str, role: str, skip: int = 0, limit: int = 100):
    """
    Get names based on user role:
    - Admin: Returns all names EXCEPT Admin itself
    - Kaccha/Pakka Muneem: Returns ONLY names they created (starts with clean slate)
    """
    query = db.query(models.Name)
    
    # Admin sees everything except themselves
    if role == "Admin":
        # Filter out Admin user from ledger
        admin_users = db.query(models.User).filter(models.User.role == "Admin").all()
        admin_phones = [u.phone_number for u in admin_users if u.phone_number]
        
        if admin_phones:
            query = query.filter(~models.Name.phone.in_(admin_phones))
        
        return query.offset(skip).limit(limit).all()
    
    # For Muneems, only show names they created (if Name has created_by field)
    # This means they start with a clean ledger
    if hasattr(models.Name, 'created_by'):
        return query.filter(models.Name.created_by == user_id).offset(skip).limit(limit).all()
    else:
        # If no created_by field, return empty list for Muneems (clean slate)
        # They will create their own ledger entries
        return []



def create_name(db: Session, name: schemas.NameCreate):
    # Map display_name to name if needed
    name_value = name.name if name.name else (name.display_name if name.display_name else "")
    
    # Ensure name_value is not empty
    if not name_value or not name_value.strip():
        raise ValueError("Name or display_name must be provided and cannot be empty")
    
    # Generate server_id if not provided
    server_id = str(uuid.uuid4())
    
    db_name = models.Name(
        server_id=server_id,
        name=name_value.strip(),
        value=name.value,
        group=name.group,
        phone=name.phone,
        gstin=name.gstin,
        commission_percent=name.commission_percent
    )
    db.add(db_name)
    
    # AUTO-CREATE USER: If this is a Kaccha/Pakka Muneem with phone number, also create user account
    if name.group in ["Kaccha Muneem", "Pakka Muneem"] and name.phone:
        # Check if user already exists
        existing_user = get_user_by_phone(db, name.phone)
        
        if not existing_user:
            # Create new user for authentication
            user_id = str(uuid.uuid4())
            role_hindi = "कच्चा मुनीम" if name.group == "Kaccha Muneem" else "पक्का मुनीम"
            
            # Get initials from name
            initials = name_value.strip()[0:2].upper() if len(name_value.strip()) >= 2 else name_value.strip()[0].upper()
            
            db_user = models.User(
                id=user_id,
                name=name_value.strip(),
                name_hindi=name_value.strip(),  # Can be enhanced with actual Hindi name if provided
                role=name.group,
                role_hindi=role_hindi,
                initials=initials,
                phone_number=name.phone,
                is_active=True
            )
            db.add(db_user)
            print(f"✅ Auto-created user account for {name.group}: {name_value.strip()} ({name.phone})")
    
    try:
        db.commit()
        db.refresh(db_name)
    except Exception as e:
        db.rollback()
        # Log the error for debugging
        import traceback
        print(f"Error creating name: {str(e)}")
        print(traceback.format_exc())
        raise e
    return db_name


# Work
def get_work(db: Session, work_id: str):
    return db.query(models.Work).filter(models.Work.id == work_id).first()

def get_works(db: Session, skip: int = 0, limit: int = 1000): # Increased limit for sync
    return db.query(models.Work).order_by(models.Work.date.desc()).offset(skip).limit(limit).all()

def get_works_for_user(db: Session, user_id: str, role: str, skip: int = 0, limit: int = 1000):
    """
    Get work entries based on user role:
    - Admin: Returns all work entries
    - Kaccha/Pakka Muneem: Returns only work entries created by this user
    """
    query = db.query(models.Work)
    
    # Admin sees everything
    if role == "Admin":
        return query.order_by(models.Work.date.desc()).offset(skip).limit(limit).all()
    
    # Muneems see only their own data
    return query.filter(models.Work.created_by == user_id).order_by(models.Work.date.desc()).offset(skip).limit(limit).all()


def create_work(db: Session, work: schemas.WorkCreate, user_id: str):
    # Use provided ID or generate DB logic one (though UUID is preferred for sync)
    # Since existing logic uses string IDs from Flutter, use that if provided
    
    # Check if user exists in database
    # If user doesn't exist with that ID, set created_by to None (foreign key allows null)
    db_user = get_user(db, user_id)
    created_by_id = db_user.id if db_user else None
    
    db_work = models.Work(
        id=work.id if work.id else str(uuid.uuid4()), # Fallback if no ID
        labour_name=work.labour_name,
        labour_category=work.labour_category,
        quantity=work.quantity,
        percentage=work.percentage,
        rate=work.rate,
        total_amount=work.total_amount,
        date=work.date,
        created_by=created_by_id  # Use backend user ID or None if user doesn't exist
    )
    db.add(db_work)
    try:
        db.commit()
        db.refresh(db_work)
    except Exception as e:
        db.rollback()
        raise e
    return db_work

# Transactions
def get_transaction(db: Session, transaction_id: str):
    return db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()

def get_transactions(db: Session, skip: int = 0, limit: int = 1000):
    return db.query(models.Transaction).order_by(models.Transaction.date.desc()).offset(skip).limit(limit).all()

def get_transactions_for_user(db: Session, user_id: str, role: str, skip: int = 0, limit: int = 1000):
    """
    Get transactions based on user role:
    - Admin: Returns all transactions
    - Kaccha/Pakka Muneem: Returns only transactions created by this user
    """
    query = db.query(models.Transaction)
    
    # Admin sees everything
    if role == "Admin":
        return query.order_by(models.Transaction.date.desc()).offset(skip).limit(limit).all()
    
    # Muneems see only their own data
    return query.filter(models.Transaction.created_by == user_id).order_by(models.Transaction.date.desc()).offset(skip).limit(limit).all()


def create_transaction(db: Session, transaction: schemas.TransactionCreate, user_id: str):
    # Check if user exists in database
    # If user doesn't exist with that ID, set created_by to None (foreign key allows null)
    db_user = get_user(db, user_id)
    created_by_id = db_user.id if db_user else None
    
    db_txn = models.Transaction(
        id=transaction.id if transaction.id else str(uuid.uuid4()),
        party_name=transaction.party_name,
        party_id=transaction.party_id,
        amount=transaction.amount,
        type=transaction.type,
        category=transaction.category,
        date=transaction.date,
        description=transaction.description,
        created_by=created_by_id  # Use backend user ID or None if user doesn't exist
    )
    db.add(db_txn)
    try:
        db.commit()
        db.refresh(db_txn)
    except Exception as e:
        db.rollback()
        raise e
    return db_txn


def update_name(db: Session, server_id: str, name: schemas.NameCreate):
    db_name = get_name(db, server_id)
    if db_name:
        # Map display_name to name if needed
        name_value = name.name if name.name else (name.display_name if name.display_name else db_name.name)
        db_name.name = name_value
        db_name.value = name.value
        db_name.group = name.group
        db_name.phone = name.phone
        db_name.gstin = name.gstin
        db_name.commission_percent = name.commission_percent
        db.commit()
        db.refresh(db_name)
    return db_name

def delete_name(db: Session, server_id: str):
    db_name = get_name(db, server_id)
    if db_name:
        db.delete(db_name)
        db.commit()
        return True
    return False

# --- User CRUD ---
def get_user(db: Session, user_id: str):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_phone(db: Session, phone_number: str):
    """
    Get user by phone number, tolerant to formatting differences.
    Checks both User table and Name table (for Kaccha/Pakka Muneem).
    """
    # Normalize input
    normalized = (
        phone_number
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    # Generate possible variants
    candidates = {
        normalized,
        normalized.lstrip("+"),
        f"+{normalized.lstrip('+')}",
    }

    # First check User table
    user = db.query(models.User).filter(
        models.User.phone_number.in_(candidates)
    ).first()

    if user:
        return user

    # If not found in User table, check Name table for Kaccha/Pakka Muneem
    name = db.query(models.Name).filter(
        models.Name.phone.in_(candidates)
    ).first()

    if name:
            # Convert Name to User-like object for compatibility
        # Create a temporary User object with Name data
        user_obj = models.User(
            id=name.server_id,
            name=name.name,
            phone_number=name.phone,
            role=name.group,  # group field contains the role (Kaccha Muneem, Pakka Muneem, etc.)
            is_active=True
        )
        return user_obj

    return None



def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    data = user.model_dump(exclude={'password'})
    db_user = models.User(**data)
    if user.password:
        db_user.password_hash = security.hash_password(user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: str, user: schemas.UserCreate):
    db_user = get_user(db, user_id)
    if db_user:
        user_data = user.model_dump(exclude_unset=True, exclude={'password'})
        for key, value in user_data.items():
            if key != 'id': # Prevent ID change
                 setattr(db_user, key, value)
        if user.password:
            db_user.password_hash = security.hash_password(user.password)
        db.commit()
        db.refresh(db_user)
    return db_user

# --- Sale CRUD ---
def get_sale(db: Session, sale_id: str):
    return db.query(models.Sale).filter(models.Sale.id == sale_id).first()

def get_sales(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Sale).offset(skip).limit(limit).all()

def get_sales_for_user(db: Session, user_id: str, role: str, skip: int = 0, limit: int = 100):
    """
    Get sales based on user role:
    - Admin: Returns all sales
    - Kaccha/Pakka Muneem: Returns only sales created by this user
    """
    query = db.query(models.Sale)
    
    # Admin sees everything
    if role == "Admin":
        return query.offset(skip).limit(limit).all()
    
    # Muneems see only their own data
    return query.filter(models.Sale.created_by == user_id).offset(skip).limit(limit).all()


def create_sale(db: Session, sale: schemas.SaleCreate):
    # Generate ID if not provided
    sale_id = sale.id if sale.id else str(uuid.uuid4())
    
    # 1. Create Sale
    db_sale = models.Sale(
        id=sale_id,
        customer_name=sale.customer_name,
        customer_name_hindi=sale.customer_name_hindi,
        customer_address=sale.customer_address,
        customer_phone=sale.customer_phone,
        date=sale.date,
        time=sale.time,
        advance_payment=sale.advance_payment,
        total_amount=sale.total_amount,
        final_amount=sale.final_amount,
        remarks=sale.remarks,
        otp=sale.otp,
        created_by=sale.created_by
    )
    db.add(db_sale)
    db.flush() # Flush to get the ID ready for relations

    # 2. Create Brick Entries
    for entry in sale.brick_entries:
        entry_id = entry.id if entry.id else str(uuid.uuid4())
        db_entry = models.BrickEntry(
            id=entry_id,
            sale_id=sale_id,
            brick_type=entry.brick_type,
            quantity=entry.quantity,
            price=entry.price
        )
        db.add(db_entry)

    # 3. Create Freight Details (if any)
    if sale.freight_details:
        db_freight = models.FreightDetails(
            sale_id=sale_id,
            type=sale.freight_details.type,
            vehicle_number=sale.freight_details.vehicle_number,
            vehicle_name=sale.freight_details.vehicle_name,
            driver_name=sale.freight_details.driver_name,
            driver_phone=sale.freight_details.driver_phone,
            rate_per_1000=sale.freight_details.rate_per_1000
        )
        db.add(db_freight)

    db.commit()
    db.refresh(db_sale)
    return db_sale
