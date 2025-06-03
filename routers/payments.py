from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_, func, desc
from datetime import datetime
import uuid

from main import get_db
from models.models import (
    Payment, Refund, PaymentMethod, Booking, User
)
from schemas.payment_schemas import (
    PaymentCreate, PaymentUpdate, PaymentResponse,
    PaymentMethodCreate, PaymentMethodUpdate, PaymentMethodResponse,
    RefundCreate, RefundUpdate, RefundResponse
)
from auth.auth import get_current_active_user, check_business_owner_permission, check_admin_permission

router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"],
    responses={404: {"description": "Not found"}},
)

# Helper function to generate payment reference
def generate_payment_reference():
    """Generate a unique payment reference"""
    return f"PAY{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

# Helper function to generate refund reference
def generate_refund_reference():
    """Generate a unique refund reference"""
    return f"REF{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

# Payment method endpoints
@router.post("/methods", response_model=PaymentMethodResponse)
def create_payment_method(
    payment_method: PaymentMethodCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new payment method"""
    # Check if user is authorized
    if payment_method.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to create payment method for another user")
    
    # Handle default payment method
    if payment_method.is_default:
        # Reset all other payment methods to non-default
        existing_methods = db.query(PaymentMethod).filter(
            PaymentMethod.user_id == current_user.user_id,
            PaymentMethod.is_default == True
        ).all()
        
        for method in existing_methods:
            method.is_default = False
    
    db_payment_method = PaymentMethod(**payment_method.dict())
    db.add(db_payment_method)
    db.commit()
    db.refresh(db_payment_method)
    return db_payment_method

@router.get("/methods", response_model=List[PaymentMethodResponse])
def read_payment_methods(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all payment methods for current user"""
    payment_methods = db.query(PaymentMethod).filter(
        PaymentMethod.user_id == current_user.user_id,
        PaymentMethod.is_active == True
    ).all()
    return payment_methods

@router.get("/methods/{method_id}", response_model=PaymentMethodResponse)
def read_payment_method(
    method_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific payment method"""
    db_payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.method_id == method_id,
        PaymentMethod.user_id == current_user.user_id
    ).first()
    
    if db_payment_method is None:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    return db_payment_method

@router.put("/methods/{method_id}", response_model=PaymentMethodResponse)
def update_payment_method(
    method_id: int,
    payment_method_update: PaymentMethodUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a payment method"""
    db_payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.method_id == method_id,
        PaymentMethod.user_id == current_user.user_id
    ).first()
    
    if db_payment_method is None:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    update_data = payment_method_update.dict(exclude_unset=True)
    
    # Handle default payment method
    if "is_default" in update_data and update_data["is_default"]:
        # Reset all other payment methods to non-default
        existing_methods = db.query(PaymentMethod).filter(
            PaymentMethod.user_id == current_user.user_id,
            PaymentMethod.is_default == True
        ).all()
        
        for method in existing_methods:
            method.is_default = False
    
    for key, value in update_data.items():
        setattr(db_payment_method, key, value)
    
    db.commit()
    db.refresh(db_payment_method)
    return db_payment_method

@router.delete("/methods/{method_id}")
def delete_payment_method(
    method_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete (deactivate) a payment method"""
    db_payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.method_id == method_id,
        PaymentMethod.user_id == current_user.user_id
    ).first()
    
    if db_payment_method is None:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    # Instead of deleting, mark as inactive
    db_payment_method.is_active = False
    
    # If this was the default method, set another one as default
    if db_payment_method.is_default:
        db_payment_method.is_default = False
        
        # Find another active method to set as default
        another_method = db.query(PaymentMethod).filter(
            PaymentMethod.user_id == current_user.user_id,
            PaymentMethod.is_active == True,
            PaymentMethod.method_id != method_id
        ).first()
        
        if another_method:
            another_method.is_default = True
    
    db.commit()
    return {"message": "Payment method deleted successfully"}

# Payment endpoints
@router.post("/", response_model=PaymentResponse)
def create_payment(
    payment: PaymentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new payment"""
    # Check if booking exists
    db_booking = db.query(Booking).filter(Booking.booking_id == payment.booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check if user is authorized
    is_owner = db_booking.user_id == current_user.user_id
    is_business_owner = any(business.business_id == db_booking.business_id for business in current_user.businesses)
    is_admin = any(role.role.role_name == "admin" for role in current_user.user_roles)
    
    if not (is_owner or is_business_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to create payment for this booking")
    
    # Check if payment method belongs to the booking user
    if payment.payment_method_id:
        db_payment_method = db.query(PaymentMethod).filter(
            PaymentMethod.method_id == payment.payment_method_id
        ).first()
        
        if db_payment_method is None:
            raise HTTPException(status_code=404, detail="Payment method not found")
        
        if db_payment_method.user_id != db_booking.user_id:
            raise HTTPException(status_code=403, detail="Payment method does not belong to the booking user")
    
    # Generate payment reference
    payment_reference = payment.payment_reference or generate_payment_reference()
    
    # Create payment
    db_payment = Payment(
        booking_id=payment.booking_id,
        payment_reference=payment_reference,
        payment_method_id=payment.payment_method_id,
        amount=payment.amount,
        currency=payment.currency,
        payment_type=payment.payment_type,
        gateway=payment.gateway,
        status="pending"  # Initial status
    )
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    # Update booking payment status
    total_paid = db.query(func.sum(Payment.amount)).filter(
        Payment.booking_id == payment.booking_id,
        Payment.status.in_(["completed", "processing"])
    ).scalar() or 0
    
    if total_paid >= db_booking.final_amount:
        db_booking.payment_status = "paid"
    elif total_paid > 0:
        db_booking.payment_status = "partial"
    
    db.commit()
    
    return db_payment

@router.get("/", response_model=List[PaymentResponse])
def read_payments(
    booking_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get payments with optional filtering"""
    # Base query for user's payments
    query = db.query(Payment).join(Booking).filter(
        Booking.user_id == current_user.user_id
    )
    
    # Filter by booking if provided
    if booking_id:
        query = query.filter(Payment.booking_id == booking_id)
    
    # Filter by status if provided
    if status:
        query = query.filter(Payment.status == status)
    
    # Order by created date (newest first)
    query = query.order_by(desc(Payment.created_at))
    
    payments = query.all()
    return payments

@router.get("/business", response_model=List[PaymentResponse])
def read_business_payments(
    business_id: int,
    booking_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get payments for a business"""
    # Check if user is owner of the business
    check_business_owner_permission(business_id, current_user)
    
    # Base query for business payments
    query = db.query(Payment).join(Booking).filter(
        Booking.business_id == business_id
    )
    
    # Filter by booking if provided
    if booking_id:
        query = query.filter(Payment.booking_id == booking_id)
    
    # Filter by status if provided
    if status:
        query = query.filter(Payment.status == status)
    
    # Order by created date (newest first)
    query = query.order_by(desc(Payment.created_at))
    
    payments = query.all()
    return payments

@router.get("/{payment_id}", response_model=PaymentResponse)
def read_payment(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific payment"""
    db_payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Check if user is authorized
    db_booking = db.query(Booking).filter(Booking.booking_id == db_payment.booking_id).first()
    is_owner = db_booking.user_id == current_user.user_id
    is_business_owner = any(business.business_id == db_booking.business_id for business in current_user.businesses)
    is_admin = any(role.role.role_name == "admin" for role in current_user.user_roles)
    
    if not (is_owner or is_business_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to view this payment")
    
    return db_payment

@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment(
    payment_id: int,
    payment_update: PaymentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a payment (usually for status updates)"""
    db_payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Check if user is authorized
    db_booking = db.query(Booking).filter(Booking.booking_id == db_payment.booking_id).first()
    is_business_owner = any(business.business_id == db_booking.business_id for business in current_user.businesses)
    is_admin = any(role.role.role_name == "admin" for role in current_user.user_roles)
    
    if not (is_business_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to update this payment")
    
    update_data = payment_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_payment, key, value)
    
    # If status is updated to completed, update processed_at
    if "status" in update_data and update_data["status"] == "completed" and not db_payment.processed_at:
        db_payment.processed_at = datetime.now()
    
    db.commit()
    db.refresh(db_payment)
    
    # Update booking payment status
    total_paid = db.query(func.sum(Payment.amount)).filter(
        Payment.booking_id == db_payment.booking_id,
        Payment.status.in_(["completed", "processing"])
    ).scalar() or 0
    
    if total_paid >= db_booking.final_amount:
        db_booking.payment_status = "paid"
    elif total_paid > 0:
        db_booking.payment_status = "partial"
    else:
        db_booking.payment_status = "pending"
    
    db.commit()
    
    return db_payment

# Refund endpoints
@router.post("/refunds", response_model=RefundResponse)
def create_refund(
    refund: RefundCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new refund"""
    # Check if payment exists
    db_payment = db.query(Payment).filter(Payment.payment_id == refund.payment_id).first()
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Check if user is authorized
    db_booking = db.query(Booking).filter(Booking.booking_id == db_payment.booking_id).first()
    is_business_owner = any(business.business_id == db_booking.business_id for business in current_user.businesses)
    is_admin = any(role.role.role_name == "admin" for role in current_user.user_roles)
    
    if not (is_business_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to create refund for this payment")
    
    # Check if payment can be refunded
    if db_payment.status not in ["completed", "processing"]:
        raise HTTPException(status_code=400, detail="Only completed or processing payments can be refunded")
    
    # Check if refund amount is valid
    existing_refunds_total = db.query(func.sum(Refund.amount)).filter(
        Refund.payment_id == refund.payment_id,
        Refund.status.in_(["completed", "processing", "pending"])
    ).scalar() or 0
    
    if refund.amount + existing_refunds_total > db_payment.amount:
        raise HTTPException(status_code=400, detail="Refund amount exceeds available payment amount")
    
    # Generate refund reference
    refund_reference = refund.refund_reference or generate_refund_reference()
    
    # Create refund
    db_refund = Refund(
        payment_id=refund.payment_id,
        refund_reference=refund_reference,
        amount=refund.amount,
        reason=refund.reason,
        processed_by=current_user.user_id,
        status="pending"  # Initial status
    )
    
    db.add(db_refund)
    db.commit()
    db.refresh(db_refund)
    
    # If this is a full refund, update payment status
    if refund.amount + existing_refunds_total >= db_payment.amount:
        db_payment.status = "refunded"
        db.commit()
        
        # Update booking payment status
        remaining_paid = db.query(func.sum(Payment.amount)).filter(
            Payment.booking_id == db_booking.booking_id,
            Payment.status.in_(["completed", "processing"]),
            Payment.payment_id != db_payment.payment_id
        ).scalar() or 0
        
        if remaining_paid >= db_booking.final_amount:
            db_booking.payment_status = "paid"
        elif remaining_paid > 0:
            db_booking.payment_status = "partial"
        else:
            db_booking.payment_status = "refunded"
        
        db.commit()
    
    return db_refund

@router.get("/refunds", response_model=List[RefundResponse])
def read_refunds(
    payment_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get refunds with optional filtering"""
    # Base query for user's refunds
    query = db.query(Refund).join(Payment).join(Booking).filter(
        Booking.user_id == current_user.user_id
    )
    
    # Filter by payment if provided
    if payment_id:
        query = query.filter(Refund.payment_id == payment_id)
    
    # Filter by status if provided
    if status:
        query = query.filter(Refund.status == status)
    
    # Order by created date (newest first)
    query = query.order_by(desc(Refund.created_at))
    
    refunds = query.all()
    return refunds

@router.get("/refunds/business", response_model=List[RefundResponse])
def read_business_refunds(
    business_id: int,
    payment_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get refunds for a business"""
    # Check if user is owner of the business
    check_business_owner_permission(business_id, current_user)
    
    # Base query for business refunds
    query = db.query(Refund).join(Payment).join(Booking).filter(
        Booking.business_id == business_id
    )
    
    # Filter by payment if provided
    if payment_id:
        query = query.filter(Refund.payment_id == payment_id)
    
    # Filter by status if provided
    if status:
        query = query.filter(Refund.status == status)
    
    # Order by created date (newest first)
    query = query.order_by(desc(Refund.created_at))
    
    refunds = query.all()
    return refunds

@router.get("/refunds/{refund_id}", response_model=RefundResponse)
def read_refund(
    refund_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific refund"""
    db_refund = db.query(Refund).filter(Refund.refund_id == refund_id).first()
    if db_refund is None:
        raise HTTPException(status_code=404, detail="Refund not found")
    
    # Check if user is authorized
    db_payment = db.query(Payment).filter(Payment.payment_id == db_refund.payment_id).first()
    db_booking = db.query(Booking).filter(Booking.booking_id == db_payment.booking_id).first()
    is_owner = db_booking.user_id == current_user.user_id
    is_business_owner = any(business.business_id == db_booking.business_id for business in current_user.businesses)
    is_admin = any(role.role.role_name == "admin" for role in current_user.user_roles)
    
    if not (is_owner or is_business_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to view this refund")
    
    return db_refund

@router.put("/refunds/{refund_id}", response_model=RefundResponse)
def update_refund(
    refund_id: int,
    refund_update: RefundUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a refund (usually for status updates)"""
    db_refund = db.query(Refund).filter(Refund.refund_id == refund_id).first()
    if db_refund is None:
        raise HTTPException(status_code=404, detail="Refund not found")
    
    # Check if user is authorized
    db_payment = db.query(Payment).filter(Payment.payment_id == db_refund.payment_id).first()
    db_booking = db.query(Booking).filter(Booking.booking_id == db_payment.booking_id).first()
    is_business_owner = any(business.business_id == db_booking.business_id for business in current_user.businesses)
    is_admin = any(role.role.role_name == "admin" for role in current_user.user_roles)
    
    if not (is_business_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to update this refund")
    
    update_data = refund_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_refund, key, value)
    
    # If status is updated to completed, update processed_at
    if "status" in update_data and update_data["status"] == "completed" and not db_refund.processed_at:
        db_refund.processed_at = datetime.now()
    
    db.commit()
    db.refresh(db_refund)
    
    return db_refund 