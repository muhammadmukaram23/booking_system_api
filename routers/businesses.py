from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_, func

from main import get_db
from models.models import Business, BusinessAddress, BusinessHours, User
from schemas.business_schemas import (
    BusinessCreate, BusinessUpdate, BusinessResponse, BusinessWithDetails,
    BusinessAddressCreate, BusinessAddressUpdate, BusinessAddressResponse,
    BusinessHoursCreate, BusinessHoursUpdate, BusinessHoursResponse
)

router = APIRouter(
    prefix="/api/businesses",
    tags=["Businesses"],
    responses={404: {"description": "Not found"}},
)

# Business endpoints
@router.post("/", response_model=BusinessResponse)
def create_business(
    business: BusinessCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Create a new business"""
    db_business = Business(
        owner_id=user_id,
        **business.dict()
    )
    
    db.add(db_business)
    db.commit()
    db.refresh(db_business)
    return db_business

@router.get("/", response_model=List[BusinessResponse])
def read_businesses(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    business_type: Optional[str] = None,
    featured: Optional[bool] = None,
    min_rating: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Get all businesses with optional filtering"""
    query = db.query(Business).filter(Business.status == "active")
    
    # Apply filters if provided
    if search:
        query = query.filter(
            or_(
                Business.business_name.ilike(f"%{search}%"),
                Business.description.ilike(f"%{search}%")
            )
        )
    
    if business_type:
        query = query.filter(Business.business_type == business_type)
    
    if featured is not None:
        query = query.filter(Business.featured == featured)
    
    if min_rating is not None:
        query = query.filter(Business.rating >= min_rating)
    
    # Order by rating (highest first)
    query = query.order_by(Business.rating.desc())
    
    businesses = query.offset(skip).limit(limit).all()
    return businesses

@router.get("/user/{user_id}", response_model=List[BusinessResponse])
def read_user_businesses(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all businesses owned by a user"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.businesses

@router.get("/{business_id}", response_model=BusinessWithDetails)
def read_business(
    business_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific business with details"""
    db_business = db.query(Business).filter(Business.business_id == business_id).first()
    if db_business is None:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return db_business

@router.put("/{business_id}", response_model=BusinessResponse)
def update_business(
    business_id: int,
    business_update: BusinessUpdate,
    db: Session = Depends(get_db)
):
    """Update a business"""
    db_business = db.query(Business).filter(Business.business_id == business_id).first()
    if db_business is None:
        raise HTTPException(status_code=404, detail="Business not found")
    
    update_data = business_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_business, key, value)
    
    db.commit()
    db.refresh(db_business)
    return db_business

# Business address endpoints
@router.post("/{business_id}/addresses", response_model=BusinessAddressResponse)
def create_business_address(
    business_id: int,
    address: BusinessAddressCreate,
    db: Session = Depends(get_db)
):
    """Create a new address for a business"""
    # Check if business exists
    business = db.query(Business).filter(Business.business_id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    db_address = BusinessAddress(
        business_id=business_id,
        **address.dict()
    )
    
    # If this is the first address or set as primary, make it the primary
    if address.is_primary or len(business.addresses) == 0:
        # Reset all other addresses to non-primary
        for addr in business.addresses:
            addr.is_primary = False
        db_address.is_primary = True
    
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

@router.get("/{business_id}/addresses", response_model=List[BusinessAddressResponse])
def read_business_addresses(
    business_id: int,
    db: Session = Depends(get_db)
):
    """Get all addresses for a business"""
    business = db.query(Business).filter(Business.business_id == business_id).first()
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return business.addresses

@router.put("/{business_id}/addresses/{address_id}", response_model=BusinessAddressResponse)
def update_business_address(
    business_id: int,
    address_id: int,
    address_update: BusinessAddressUpdate,
    db: Session = Depends(get_db)
):
    """Update a business address"""
    db_address = db.query(BusinessAddress).filter(
        BusinessAddress.address_id == address_id,
        BusinessAddress.business_id == business_id
    ).first()
    
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    
    update_data = address_update.dict(exclude_unset=True)
    
    # Handle setting as primary address
    if "is_primary" in update_data and update_data["is_primary"]:
        # Reset all other addresses to non-primary
        business = db.query(Business).filter(Business.business_id == business_id).first()
        for addr in business.addresses:
            addr.is_primary = False
    
    for key, value in update_data.items():
        setattr(db_address, key, value)
    
    db.commit()
    db.refresh(db_address)
    return db_address

@router.delete("/{business_id}/addresses/{address_id}")
def delete_business_address(
    business_id: int,
    address_id: int,
    db: Session = Depends(get_db)
):
    """Delete a business address"""
    db_address = db.query(BusinessAddress).filter(
        BusinessAddress.address_id == address_id,
        BusinessAddress.business_id == business_id
    ).first()
    
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    
    was_primary = db_address.is_primary
    
    db.delete(db_address)
    db.commit()
    
    # If deleted address was primary and there are other addresses, set a new primary
    if was_primary:
        remaining_address = db.query(BusinessAddress).filter(
            BusinessAddress.business_id == business_id
        ).first()
        
        if remaining_address:
            remaining_address.is_primary = True
            db.commit()
    
    return {"message": "Address deleted successfully"}

# Business hours endpoints
@router.post("/{business_id}/hours", response_model=BusinessHoursResponse)
def create_business_hours(
    business_id: int,
    hours: BusinessHoursCreate,
    db: Session = Depends(get_db)
):
    """Create or update business hours for a specific day"""
    # Check if business exists
    business = db.query(Business).filter(Business.business_id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check if hours for this day already exist
    existing_hours = db.query(BusinessHours).filter(
        BusinessHours.business_id == business_id,
        BusinessHours.day_of_week == hours.day_of_week
    ).first()
    
    if existing_hours:
        # Update existing hours
        existing_hours.open_time = hours.open_time
        existing_hours.close_time = hours.close_time
        existing_hours.is_closed = hours.is_closed
        db.commit()
        db.refresh(existing_hours)
        return existing_hours
    else:
        # Create new hours
        db_hours = BusinessHours(
            business_id=business_id,
            **hours.dict()
        )
        db.add(db_hours)
        db.commit()
        db.refresh(db_hours)
        return db_hours

@router.get("/{business_id}/hours", response_model=List[BusinessHoursResponse])
def read_business_hours(
    business_id: int,
    db: Session = Depends(get_db)
):
    """Get all business hours"""
    business = db.query(Business).filter(Business.business_id == business_id).first()
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return business.hours

@router.put("/{business_id}/hours/{day_of_week}", response_model=BusinessHoursResponse)
def update_business_hours(
    business_id: int,
    day_of_week: str,
    hours_update: BusinessHoursUpdate,
    db: Session = Depends(get_db)
):
    """Update business hours for a specific day"""
    db_hours = db.query(BusinessHours).filter(
        BusinessHours.business_id == business_id,
        BusinessHours.day_of_week == day_of_week
    ).first()
    
    if db_hours is None:
        raise HTTPException(status_code=404, detail="Hours not found for this day")
    
    update_data = hours_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_hours, key, value)
    
    db.commit()
    db.refresh(db_hours)
    return db_hours

@router.delete("/{business_id}/hours/{day_of_week}")
def delete_business_hours(
    business_id: int,
    day_of_week: str,
    db: Session = Depends(get_db)
):
    """Delete business hours for a specific day"""
    db_hours = db.query(BusinessHours).filter(
        BusinessHours.business_id == business_id,
        BusinessHours.day_of_week == day_of_week
    ).first()
    
    if db_hours is None:
        raise HTTPException(status_code=404, detail="Hours not found for this day")
    
    db.delete(db_hours)
    db.commit()
    
    return {"message": "Hours deleted successfully"} 