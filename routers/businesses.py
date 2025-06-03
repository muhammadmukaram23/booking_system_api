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
from auth.auth import get_current_active_user, check_business_owner_permission, check_admin_permission

router = APIRouter(
    prefix="/api/businesses",
    tags=["Businesses"],
    responses={404: {"description": "Not found"}},
)

# Business endpoints
@router.post("/", response_model=BusinessResponse)
def create_business(
    business: BusinessCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new business"""
    db_business = Business(
        owner_id=current_user.user_id,
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

@router.get("/my-businesses", response_model=List[BusinessResponse])
def read_my_businesses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all businesses owned by current user"""
    return current_user.businesses

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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a business"""
    # Check if user is owner or admin
    is_admin = any(role.role.role_name == "admin" for role in current_user.user_roles)
    is_owner = any(business.business_id == business_id for business in current_user.businesses)
    
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Not authorized to update this business")
    
    db_business = db.query(Business).filter(Business.business_id == business_id).first()
    if db_business is None:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Only allow admins to update featured and status fields
    update_data = business_update.dict(exclude_unset=True)
    if not is_admin:
        update_data.pop("featured", None)
        update_data.pop("status", None)
    
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new address for a business"""
    # Check if user is owner
    check_business_owner_permission(business_id, current_user)
    
    db_address = BusinessAddress(
        business_id=business_id,
        **address.dict()
    )
    
    # If this is the first address or set as primary, make it the primary
    business = db.query(Business).filter(Business.business_id == business_id).first()
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a business address"""
    # Check if user is owner
    check_business_owner_permission(business_id, current_user)
    
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a business address"""
    # Check if user is owner
    check_business_owner_permission(business_id, current_user)
    
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create or update business hours for a specific day"""
    # Check if user is owner
    check_business_owner_permission(business_id, current_user)
    
    # Check if hours for this day already exist
    existing_hours = db.query(BusinessHours).filter(
        BusinessHours.business_id == business_id,
        BusinessHours.day_of_week == hours.day_of_week
    ).first()
    
    if existing_hours:
        # Update existing hours
        existing_hours.open_time = hours.open_time
        existing_hours.close_time = hours.close_time
        existing_hours.is_open = hours.is_open
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update business hours for a specific day"""
    # Check if user is owner
    check_business_owner_permission(business_id, current_user)
    
    db_hours = db.query(BusinessHours).filter(
        BusinessHours.business_id == business_id,
        BusinessHours.day_of_week == day_of_week
    ).first()
    
    if db_hours is None:
        raise HTTPException(status_code=404, detail=f"Hours for {day_of_week} not found")
    
    update_data = hours_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_hours, key, value)
    
    db.commit()
    db.refresh(db_hours)
    return db_hours 