from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from main import get_db
from models.models import Promotion, PromotionUsage, User, Business, Booking
from schemas.promotion_schemas import (
    PromotionBase, PromotionCreate, PromotionUpdate, PromotionResponse,
    PromotionUsageBase, PromotionUsageResponse,
    PromotionValidationRequest, PromotionValidationResponse,
    PromotionStatusEnum, DiscountTypeEnum
)

router = APIRouter(
    prefix="/api/promotions",
    tags=["Promotions"],
    responses={404: {"description": "Not found"}},
)

# Create a new promotion
@router.post("/", response_model=PromotionResponse)
def create_promotion(
    promotion: PromotionCreate,
    db: Session = Depends(get_db)
):
    """Create a new promotion"""
    # Check if code already exists
    existing_promotion = db.query(Promotion).filter(Promotion.code == promotion.code).first()
    if existing_promotion:
        raise HTTPException(status_code=400, detail="Promotion code already exists")
    
    # Create promotion
    db_promotion = Promotion(
        business_id=promotion.business_id,
        code=promotion.code,
        title=promotion.title,
        description=promotion.description,
        discount_type=promotion.discount_type,
        discount_value=promotion.discount_value,
        minimum_amount=promotion.minimum_amount,
        maximum_discount=promotion.maximum_discount,
        usage_limit=promotion.usage_limit,
        per_user_limit=promotion.per_user_limit,
        valid_from=promotion.valid_from,
        valid_until=promotion.valid_until,
        applicable_services=promotion.applicable_services,
        applicable_days=promotion.applicable_days,
        status=promotion.status,
        created_by=promotion.created_by
    )
    
    db.add(db_promotion)
    db.commit()
    db.refresh(db_promotion)
    
    return db_promotion

# Get all promotions for a business
@router.get("/business/{business_id}", response_model=List[PromotionResponse])
def get_business_promotions(
    business_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[PromotionStatusEnum] = None,
    db: Session = Depends(get_db)
):
    """Get all promotions for a business"""
    # Query promotions
    query = db.query(Promotion).filter(Promotion.business_id == business_id)
    
    # Apply status filter if provided
    if status:
        query = query.filter(Promotion.status == status)
    
    # Order by most recent first
    query = query.order_by(Promotion.created_at.desc())
    
    promotions = query.offset(skip).limit(limit).all()
    return promotions

# Get active promotions for a business (public endpoint)
@router.get("/business/{business_id}/active", response_model=List[PromotionResponse])
def get_active_business_promotions(
    business_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get active promotions for a business (public endpoint)"""
    # Verify the business exists
    business = db.query(Business).filter(Business.business_id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get current date
    now = datetime.now()
    
    # Query active promotions
    promotions = db.query(Promotion).filter(
        Promotion.business_id == business_id,
        Promotion.status == "active",
        Promotion.valid_from <= now,
        Promotion.valid_until >= now
    ).order_by(Promotion.created_at.desc()).offset(skip).limit(limit).all()
    
    return promotions

# Get a specific promotion
@router.get("/{promotion_id}", response_model=PromotionResponse)
def get_promotion(
    promotion_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific promotion"""
    promotion = db.query(Promotion).filter(Promotion.promotion_id == promotion_id).first()
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    return promotion

# Update a promotion
@router.put("/{promotion_id}", response_model=PromotionResponse)
def update_promotion(
    promotion_id: int,
    promotion_update: PromotionUpdate,
    db: Session = Depends(get_db)
):
    """Update a promotion"""
    db_promotion = db.query(Promotion).filter(Promotion.promotion_id == promotion_id).first()
    if not db_promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    # Update promotion fields
    update_data = promotion_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_promotion, key, value)
    
    db_promotion.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_promotion)
    
    return db_promotion

# Delete a promotion
@router.delete("/{promotion_id}")
def delete_promotion(
    promotion_id: int,
    db: Session = Depends(get_db)
):
    """Delete a promotion"""
    db_promotion = db.query(Promotion).filter(Promotion.promotion_id == promotion_id).first()
    if not db_promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    # Check if promotion has been used
    usage_count = db.query(PromotionUsage).filter(PromotionUsage.promotion_id == promotion_id).count()
    if usage_count > 0:
        # Instead of deleting, set status to inactive
        db_promotion.status = "inactive"
        db_promotion.updated_at = datetime.now()
        db.commit()
        return {"message": "Promotion has been used and cannot be deleted. Status set to inactive."}
    
    db.delete(db_promotion)
    db.commit()
    
    return {"message": "Promotion deleted successfully"}

# Validate a promotion code
@router.post("/validate", response_model=PromotionValidationResponse)
def validate_promotion(
    validation_request: PromotionValidationRequest,
    db: Session = Depends(get_db)
):
    """Validate a promotion code"""
    # Get the promotion by code
    promotion = db.query(Promotion).filter(Promotion.code == validation_request.code).first()
    
    # If promotion not found
    if not promotion:
        return PromotionValidationResponse(
            is_valid=False,
            error_message="Invalid promotion code"
        )
    
    # Check if promotion is active
    now = datetime.now()
    if promotion.status != "active" or promotion.valid_from > now or promotion.valid_until < now:
        return PromotionValidationResponse(
            is_valid=False,
            error_message="Promotion is not active or has expired"
        )
    
    # Check if business_id matches if provided
    if validation_request.business_id and promotion.business_id != validation_request.business_id:
        return PromotionValidationResponse(
            is_valid=False,
            error_message="Promotion not valid for this business"
        )
    
    # Check if promotion has reached usage limit
    if promotion.usage_limit and promotion.usage_count >= promotion.usage_limit:
        return PromotionValidationResponse(
            is_valid=False,
            error_message="Promotion usage limit reached"
        )
    
    # Check if user has reached per-user limit
    user_usage_count = db.query(PromotionUsage).filter(
        PromotionUsage.promotion_id == promotion.promotion_id,
        PromotionUsage.user_id == validation_request.user_id
    ).count()
    
    if promotion.per_user_limit and user_usage_count >= promotion.per_user_limit:
        return PromotionValidationResponse(
            is_valid=False,
            error_message="You have already used this promotion the maximum number of times"
        )
    
    # Check minimum amount
    if promotion.minimum_amount and validation_request.amount < promotion.minimum_amount:
        return PromotionValidationResponse(
            is_valid=False,
            error_message=f"Minimum amount required: {promotion.minimum_amount}"
        )
    
    # Calculate discount amount
    discount_amount = 0
    if promotion.discount_type == "percentage":
        discount_amount = (validation_request.amount * promotion.discount_value) / 100
        # Apply maximum discount if set
        if promotion.maximum_discount and discount_amount > promotion.maximum_discount:
            discount_amount = promotion.maximum_discount
    elif promotion.discount_type == "fixed_amount":
        discount_amount = promotion.discount_value
        # Ensure discount doesn't exceed the amount
        if discount_amount > validation_request.amount:
            discount_amount = validation_request.amount
    
    # Promotion is valid
    return PromotionValidationResponse(
        is_valid=True,
        promotion=promotion,
        discount_amount=discount_amount
    )

# Apply a promotion to a booking
@router.post("/apply", response_model=PromotionUsageResponse)
def apply_promotion(
    promotion_usage: PromotionUsageBase,
    db: Session = Depends(get_db)
):
    """Apply a promotion to a booking"""
    # Check if promotion exists
    promotion = db.query(Promotion).filter(Promotion.promotion_id == promotion_usage.promotion_id).first()
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    # Check if booking exists
    booking = db.query(Booking).filter(Booking.booking_id == promotion_usage.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check if booking already has a promotion applied
    existing_usage = db.query(PromotionUsage).filter(
        PromotionUsage.booking_id == promotion_usage.booking_id
    ).first()
    
    if existing_usage:
        raise HTTPException(status_code=400, detail="A promotion has already been applied to this booking")
    
    # Create promotion usage
    db_usage = PromotionUsage(
        promotion_id=promotion_usage.promotion_id,
        user_id=promotion_usage.user_id,
        booking_id=promotion_usage.booking_id,
        discount_amount=promotion_usage.discount_amount
    )
    
    db.add(db_usage)
    
    # Update promotion usage count
    promotion.usage_count += 1
    
    db.commit()
    db.refresh(db_usage)
    
    return db_usage

# Get promotion usage history for a business
@router.get("/usage/business/{business_id}", response_model=List[PromotionUsageResponse])
def get_business_promotion_usage(
    business_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get promotion usage history for a business"""
    # Get all promotions for the business
    promotions = db.query(Promotion).filter(Promotion.business_id == business_id).all()
    promotion_ids = [p.promotion_id for p in promotions]
    
    # Get usage records for these promotions
    usages = db.query(PromotionUsage).filter(
        PromotionUsage.promotion_id.in_(promotion_ids)
    ).order_by(PromotionUsage.used_at.desc()).offset(skip).limit(limit).all()
    
    return usages

# Get promotion usage history for a user
@router.get("/usage/user/{user_id}", response_model=List[PromotionUsageResponse])
def get_user_promotion_usage(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get promotion usage history for a user"""
    usages = db.query(PromotionUsage).filter(
        PromotionUsage.user_id == user_id
    ).order_by(PromotionUsage.used_at.desc()).offset(skip).limit(limit).all()
    
    return usages 