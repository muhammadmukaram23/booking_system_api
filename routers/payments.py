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
    db: Session = Depends(get_db)
):
    """Create a new payment method"""
    # Handle default payment method
    if payment_method.is_default:
        # Reset all other payment methods to non-default
        existing_methods = db.query(PaymentMethod).filter(
            PaymentMethod.user_id == payment_method.user_id,
            PaymentMethod.is_default == True
        ).all()
        
        for method in existing_methods:
            method.is_default = False
    
    db_payment_method = PaymentMethod(**payment_method.dict())
    db.add(db_payment_method)
    db.commit()
    db.refresh(db_payment_method)
    return db_payment_method

@router.get("/methods/user/{user_id}", response_model=List[PaymentMethodResponse])
def read_user_payment_methods(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all payment methods for a user"""
    payment_methods = db.query(PaymentMethod).filter(
        PaymentMethod.user_id == user_id,
        PaymentMethod.is_active == True
    ).all()
    return payment_methods

@router.get("/methods/{method_id}", response_model=PaymentMethodResponse)
def read_payment_method(
    method_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific payment method"""
    db_payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.method_id == method_id
    ).first()
    
    if db_payment_method is None:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    return db_payment_method

@router.put("/methods/{method_id}", response_model=PaymentMethodResponse)
def update_payment_method(
    method_id: int,
    payment_method_update: PaymentMethodUpdate,
    db: Session = Depends(get_db)
):
    """Update a payment method"""
    db_payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.method_id == method_id
    ).first()
    
    if db_payment_method is None:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    update_data = payment_method_update.dict(exclude_unset=True)
    
    # Handle default payment method
    if "is_default" in update_data and update_data["is_default"]:
        # Reset all other payment methods to non-default
        existing_methods = db.query(PaymentMethod).filter(
            PaymentMethod.user_id == db_payment_method.user_id,
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
    db: Session = Depends(get_db)
):
    """Delete (deactivate) a payment method"""
    db_payment_method = db.query(PaymentMethod).filter(
        PaymentMethod.method_id == method_id
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
            PaymentMethod.user_id == db_payment_method.user_id,
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
    db: Session = Depends(get_db)
):
    """Create a new payment"""
    # Check if booking exists
    db_booking = db.query(Booking).filter(Booking.booking_id == payment.booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
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
        payment_method_id=payment.payment_method_id,
        amount=payment.amount,
        payment_reference=payment_reference,
        payment_date=payment.payment_date or datetime.now(),
        status=payment.status,
        transaction_id=payment.transaction_id,
        payment_provider=payment.payment_provider,
        payment_details=payment.payment_details,
        notes=payment.notes
    )
    
    db.add(db_payment)
    
    # Update booking if payment is successful
    if payment.status == "completed":
        db_booking.payment_status = "paid"
        if payment.update_booking_status:
            db_booking.status = "confirmed"
    
    db.commit()
    db.refresh(db_payment)
    return db_payment

@router.get("/user/{user_id}", response_model=List[PaymentResponse])
def read_user_payments(
    user_id: int,
    booking_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all payments for a user"""
    query = db.query(Payment).join(Booking).filter(Booking.user_id == user_id)
    
    if booking_id:
        query = query.filter(Payment.booking_id == booking_id)
    
    if status:
        query = query.filter(Payment.status == status)
    
    # Order by payment date (newest first)
    query = query.order_by(desc(Payment.payment_date))
    
    payments = query.all()
    return payments

@router.get("/business/{business_id}", response_model=List[PaymentResponse])
def read_business_payments(
    business_id: int,
    booking_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all payments for a business"""
    query = db.query(Payment).join(Booking).filter(Booking.business_id == business_id)
    
    if booking_id:
        query = query.filter(Payment.booking_id == booking_id)
    
    if status:
        query = query.filter(Payment.status == status)
    
    # Order by payment date (newest first)
    query = query.order_by(desc(Payment.payment_date))
    
    payments = query.all()
    return payments

@router.get("/{payment_id}", response_model=PaymentResponse)
def read_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific payment"""
    db_payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return db_payment

@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment(
    payment_id: int,
    payment_update: PaymentUpdate,
    db: Session = Depends(get_db)
):
    """Update a payment"""
    db_payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Check if payment can be updated
    if db_payment.status in ["completed", "refunded"]:
        raise HTTPException(status_code=400, detail=f"Cannot update a payment with status: {db_payment.status}")
    
    update_data = payment_update.dict(exclude_unset=True)
    
    # Handle status changes
    old_status = db_payment.status
    if "status" in update_data and update_data["status"] != old_status:
        # If payment is now completed
        if update_data["status"] == "completed":
            # Update booking payment status
            db_booking = db.query(Booking).filter(Booking.booking_id == db_payment.booking_id).first()
            if db_booking:
                db_booking.payment_status = "paid"
                if payment_update.update_booking_status:
                    db_booking.status = "confirmed"
    
    for key, value in update_data.items():
        setattr(db_payment, key, value)
    
    db.commit()
    db.refresh(db_payment)
    return db_payment

# Refund endpoints
@router.post("/refunds", response_model=RefundResponse)
def create_refund(
    refund: RefundCreate,
    db: Session = Depends(get_db)
):
    """Create a new refund"""
    # Check if payment exists
    db_payment = db.query(Payment).filter(Payment.payment_id == refund.payment_id).first()
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Check if payment can be refunded
    if db_payment.status != "completed":
        raise HTTPException(status_code=400, detail=f"Cannot refund a payment with status: {db_payment.status}")
    
    # Check if payment has already been refunded
    existing_refund = db.query(Refund).filter(Refund.payment_id == refund.payment_id).first()
    if existing_refund and existing_refund.status in ["pending", "completed"]:
        raise HTTPException(status_code=400, detail="Payment has already been refunded or has a pending refund")
    
    # Check if refund amount is valid
    if refund.amount > db_payment.amount:
        raise HTTPException(status_code=400, detail="Refund amount cannot exceed payment amount")
    
    # Generate refund reference
    refund_reference = refund.refund_reference or generate_refund_reference()
    
    # Create refund
    db_refund = Refund(
        payment_id=refund.payment_id,
        amount=refund.amount,
        refund_reference=refund_reference,
        refund_date=refund.refund_date or datetime.now(),
        status=refund.status,
        transaction_id=refund.transaction_id,
        refund_reason=refund.refund_reason,
        notes=refund.notes,
        processed_by=refund.processed_by
    )
    
    db.add(db_refund)
    
    # Update payment status if refund is completed
    if refund.status == "completed":
        # If full refund
        if refund.amount == db_payment.amount:
            db_payment.status = "refunded"
        else:
            db_payment.status = "partially_refunded"
        
        # Update booking if needed
        if refund.update_booking_status:
            db_booking = db.query(Booking).filter(Booking.booking_id == db_payment.booking_id).first()
            if db_booking and refund.amount == db_payment.amount:
                db_booking.payment_status = "refunded"
                if refund.cancel_booking:
                    db_booking.status = "cancelled"
                    db_booking.cancellation_reason = "Refund issued"
    
    db.commit()
    db.refresh(db_refund)
    return db_refund

@router.get("/refunds/user/{user_id}", response_model=List[RefundResponse])
def read_user_refunds(
    user_id: int,
    payment_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all refunds for a user"""
    query = db.query(Refund).join(Payment).join(Booking).filter(Booking.user_id == user_id)
    
    if payment_id:
        query = query.filter(Refund.payment_id == payment_id)
    
    if status:
        query = query.filter(Refund.status == status)
    
    # Order by refund date (newest first)
    query = query.order_by(desc(Refund.refund_date))
    
    refunds = query.all()
    return refunds

@router.get("/refunds/business/{business_id}", response_model=List[RefundResponse])
def read_business_refunds(
    business_id: int,
    payment_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all refunds for a business"""
    query = db.query(Refund).join(Payment).join(Booking).filter(Booking.business_id == business_id)
    
    if payment_id:
        query = query.filter(Refund.payment_id == payment_id)
    
    if status:
        query = query.filter(Refund.status == status)
    
    # Order by refund date (newest first)
    query = query.order_by(desc(Refund.refund_date))
    
    refunds = query.all()
    return refunds

@router.get("/refunds/{refund_id}", response_model=RefundResponse)
def read_refund(
    refund_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific refund"""
    db_refund = db.query(Refund).filter(Refund.refund_id == refund_id).first()
    if db_refund is None:
        raise HTTPException(status_code=404, detail="Refund not found")
    
    return db_refund

@router.put("/refunds/{refund_id}", response_model=RefundResponse)
def update_refund(
    refund_id: int,
    refund_update: RefundUpdate,
    db: Session = Depends(get_db)
):
    """Update a refund"""
    db_refund = db.query(Refund).filter(Refund.refund_id == refund_id).first()
    if db_refund is None:
        raise HTTPException(status_code=404, detail="Refund not found")
    
    # Check if refund can be updated
    if db_refund.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot update a completed refund")
    
    update_data = refund_update.dict(exclude_unset=True)
    
    # Handle status changes
    old_status = db_refund.status
    if "status" in update_data and update_data["status"] != old_status:
        # If refund is now completed
        if update_data["status"] == "completed":
            # Get associated payment
            db_payment = db.query(Payment).filter(Payment.payment_id == db_refund.payment_id).first()
            
            if db_payment:
                # If full refund
                if db_refund.amount == db_payment.amount:
                    db_payment.status = "refunded"
                else:
                    db_payment.status = "partially_refunded"
                
                # Update booking if needed
                if refund_update.update_booking_status:
                    db_booking = db.query(Booking).filter(Booking.booking_id == db_payment.booking_id).first()
                    if db_booking and db_refund.amount == db_payment.amount:
                        db_booking.payment_status = "refunded"
                        if refund_update.cancel_booking:
                            db_booking.status = "cancelled"
                            db_booking.cancellation_reason = "Refund issued"
    
    for key, value in update_data.items():
        setattr(db_refund, key, value)
    
    db.commit()
    db.refresh(db_refund)
    return db_refund 