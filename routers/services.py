from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_, func
from datetime import datetime, time

from main import get_db
from models.models import (
    Service, ServicePricing, Resource, Category, 
    AvailabilityTemplate, AvailabilitySlot, BlockedTime, User, Business
)
from schemas.service_schemas import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    ServiceCreate, ServiceUpdate, ServiceResponse,
    ServicePricingCreate, ServicePricingUpdate, ServicePricingResponse,
    ResourceCreate, ResourceUpdate, ResourceResponse,
    AvailabilityTemplateCreate, AvailabilityTemplateUpdate, AvailabilityTemplateResponse,
    AvailabilitySlotCreate, AvailabilitySlotUpdate, AvailabilitySlotResponse,
    BlockedTimeCreate, BlockedTimeUpdate, BlockedTimeResponse
)

router = APIRouter(
    prefix="/api/services",
    tags=["Services"],
    responses={404: {"description": "Not found"}},
)

# Category endpoints
@router.post("/categories", response_model=CategoryResponse)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db)
):
    """Create a new category"""
    db_category = Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.get("/categories", response_model=List[CategoryResponse])
def read_categories(
    skip: int = 0,
    limit: int = 100,
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get all categories with optional parent filter"""
    query = db.query(Category).filter(Category.is_active == True)
    
    if parent_id is not None:
        query = query.filter(Category.parent_category_id == parent_id)
    
    categories = query.order_by(Category.sort_order).offset(skip).limit(limit).all()
    return categories

@router.get("/categories/{category_id}", response_model=CategoryResponse)
def read_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific category"""
    db_category = db.query(Category).filter(Category.category_id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category

@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """Update a category"""
    db_category = db.query(Category).filter(Category.category_id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)
    
    db.commit()
    db.refresh(db_category)
    return db_category

# Service endpoints
@router.post("/", response_model=ServiceResponse)
def create_service(
    service: ServiceCreate,
    db: Session = Depends(get_db)
):
    """Create a new service"""
    # Check if business exists
    business = db.query(Business).filter(Business.business_id == service.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    db_service = Service(**service.dict())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

@router.get("/", response_model=List[ServiceResponse])
def read_services(
    skip: int = 0,
    limit: int = 100,
    business_id: Optional[int] = None,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get all services with optional filtering"""
    query = db.query(Service)
    
    if active_only:
        query = query.filter(Service.is_active == True)
    
    if business_id:
        query = query.filter(Service.business_id == business_id)
    
    if category_id:
        query = query.filter(Service.category_id == category_id)
    
    if search:
        query = query.filter(
            or_(
                Service.service_name.ilike(f"%{search}%"),
                Service.description.ilike(f"%{search}%")
            )
        )
    
    if min_price is not None:
        query = query.filter(Service.base_price >= min_price)
    
    if max_price is not None:
        query = query.filter(Service.base_price <= max_price)
    
    services = query.order_by(Service.service_name).offset(skip).limit(limit).all()
    return services

@router.get("/{service_id}", response_model=ServiceResponse)
def read_service(
    service_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific service"""
    db_service = db.query(Service).filter(Service.service_id == service_id).first()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return db_service

@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(
    service_id: int,
    service_update: ServiceUpdate,
    db: Session = Depends(get_db)
):
    """Update a service"""
    # Get the service with its business
    db_service = db.query(Service).filter(Service.service_id == service_id).first()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    
    update_data = service_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_service, key, value)
    
    db.commit()
    db.refresh(db_service)
    return db_service

# Service pricing endpoints
@router.post("/pricing", response_model=ServicePricingResponse)
def create_service_pricing(
    pricing: ServicePricingCreate,
    db: Session = Depends(get_db)
):
    """Create a new pricing tier for a service"""
    # Get the service with its business
    db_service = db.query(Service).filter(Service.service_id == pricing.service_id).first()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    
    db_pricing = ServicePricing(**pricing.dict())
    db.add(db_pricing)
    db.commit()
    db.refresh(db_pricing)
    return db_pricing

@router.get("/pricing/{service_id}", response_model=List[ServicePricingResponse])
def read_service_pricing(
    service_id: int,
    db: Session = Depends(get_db)
):
    """Get all pricing tiers for a service"""
    db_service = db.query(Service).filter(Service.service_id == service_id).first()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    
    pricing = db.query(ServicePricing).filter(ServicePricing.service_id == service_id).all()
    return pricing

@router.put("/pricing/{pricing_id}", response_model=ServicePricingResponse)
def update_service_pricing(
    pricing_id: int,
    pricing_update: ServicePricingUpdate,
    db: Session = Depends(get_db)
):
    """Update a pricing tier"""
    db_pricing = db.query(ServicePricing).filter(ServicePricing.pricing_id == pricing_id).first()
    if db_pricing is None:
        raise HTTPException(status_code=404, detail="Pricing tier not found")
    
    update_data = pricing_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_pricing, key, value)
    
    db.commit()
    db.refresh(db_pricing)
    return db_pricing

@router.delete("/pricing/{pricing_id}")
def delete_service_pricing(
    pricing_id: int,
    db: Session = Depends(get_db)
):
    """Delete a pricing tier"""
    db_pricing = db.query(ServicePricing).filter(ServicePricing.pricing_id == pricing_id).first()
    if db_pricing is None:
        raise HTTPException(status_code=404, detail="Pricing tier not found")
    
    db.delete(db_pricing)
    db.commit()
    
    return {"message": "Pricing tier deleted successfully"}

# Resource endpoints
@router.post("/resources", response_model=ResourceResponse)
def create_resource(
    resource: ResourceCreate,
    db: Session = Depends(get_db)
):
    """Create a new resource"""
    # Check if business exists
    business = db.query(Business).filter(Business.business_id == resource.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    db_resource = Resource(**resource.dict())
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return db_resource

@router.get("/resources", response_model=List[ResourceResponse])
def read_resources(
    skip: int = 0,
    limit: int = 100,
    business_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get all resources with optional filtering"""
    query = db.query(Resource)
    
    if active_only:
        query = query.filter(Resource.is_active == True)
    
    if business_id:
        query = query.filter(Resource.business_id == business_id)
    
    if resource_type:
        query = query.filter(Resource.resource_type == resource_type)
    
    resources = query.order_by(Resource.resource_name).offset(skip).limit(limit).all()
    return resources

@router.get("/resources/{resource_id}", response_model=ResourceResponse)
def read_resource(
    resource_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific resource"""
    db_resource = db.query(Resource).filter(Resource.resource_id == resource_id).first()
    if db_resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return db_resource

@router.put("/resources/{resource_id}", response_model=ResourceResponse)
def update_resource(
    resource_id: int,
    resource_update: ResourceUpdate,
    db: Session = Depends(get_db)
):
    """Update a resource"""
    db_resource = db.query(Resource).filter(Resource.resource_id == resource_id).first()
    if db_resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    update_data = resource_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_resource, key, value)
    
    db.commit()
    db.refresh(db_resource)
    return db_resource

# Availability template endpoints
@router.post("/availability/templates", response_model=AvailabilityTemplateResponse)
def create_availability_template(
    template: AvailabilityTemplateCreate,
    db: Session = Depends(get_db)
):
    """Create a new availability template"""
    # Check if service exists if provided
    if template.service_id:
        service = db.query(Service).filter(Service.service_id == template.service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
    
    # Check if resource exists if provided
    if template.resource_id:
        resource = db.query(Resource).filter(Resource.resource_id == template.resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
    
    db_template = AvailabilityTemplate(**template.dict())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@router.get("/availability/templates", response_model=List[AvailabilityTemplateResponse])
def read_availability_templates(
    service_id: Optional[int] = None,
    resource_id: Optional[int] = None,
    day_of_week: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get availability templates with optional filtering"""
    query = db.query(AvailabilityTemplate)
    
    if active_only:
        query = query.filter(AvailabilityTemplate.is_active == True)
    
    if service_id:
        query = query.filter(AvailabilityTemplate.service_id == service_id)
    
    if resource_id:
        query = query.filter(AvailabilityTemplate.resource_id == resource_id)
    
    if day_of_week:
        query = query.filter(AvailabilityTemplate.day_of_week == day_of_week)
    
    templates = query.all()
    return templates

@router.put("/availability/templates/{template_id}", response_model=AvailabilityTemplateResponse)
def update_availability_template(
    template_id: int,
    template_update: AvailabilityTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update an availability template"""
    db_template = db.query(AvailabilityTemplate).filter(AvailabilityTemplate.template_id == template_id).first()
    if db_template is None:
        raise HTTPException(status_code=404, detail="Availability template not found")
    
    update_data = template_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_template, key, value)
    
    db.commit()
    db.refresh(db_template)
    return db_template

# Availability slot endpoints
@router.post("/availability/slots", response_model=AvailabilitySlotResponse)
def create_availability_slot(
    slot: AvailabilitySlotCreate,
    db: Session = Depends(get_db)
):
    """Create a new availability slot"""
    # Check if service exists if provided
    if slot.service_id:
        service = db.query(Service).filter(Service.service_id == slot.service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
    
    # Check if resource exists if provided
    if slot.resource_id:
        resource = db.query(Resource).filter(Resource.resource_id == slot.resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
    
    db_slot = AvailabilitySlot(**slot.dict())
    db.add(db_slot)
    db.commit()
    db.refresh(db_slot)
    return db_slot

@router.get("/availability/slots", response_model=List[AvailabilitySlotResponse])
def read_availability_slots(
    service_id: Optional[int] = None,
    resource_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = "available",
    db: Session = Depends(get_db)
):
    """Get availability slots with optional filtering"""
    query = db.query(AvailabilitySlot)
    
    if service_id:
        query = query.filter(AvailabilitySlot.service_id == service_id)
    
    if resource_id:
        query = query.filter(AvailabilitySlot.resource_id == resource_id)
    
    if start_date:
        query = query.filter(AvailabilitySlot.start_datetime >= start_date)
    
    if end_date:
        query = query.filter(AvailabilitySlot.end_datetime <= end_date)
    
    if status:
        query = query.filter(AvailabilitySlot.status == status)
    
    # Order by start time
    query = query.order_by(AvailabilitySlot.start_datetime)
    
    slots = query.all()
    return slots

@router.put("/availability/slots/{slot_id}", response_model=AvailabilitySlotResponse)
def update_availability_slot(
    slot_id: int,
    slot_update: AvailabilitySlotUpdate,
    db: Session = Depends(get_db)
):
    """Update an availability slot"""
    db_slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.slot_id == slot_id).first()
    if db_slot is None:
        raise HTTPException(status_code=404, detail="Availability slot not found")
    
    update_data = slot_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_slot, key, value)
    
    db.commit()
    db.refresh(db_slot)
    return db_slot

# Blocked time endpoints
@router.post("/blocked-times", response_model=BlockedTimeResponse)
def create_blocked_time(
    blocked_time: BlockedTimeCreate,
    db: Session = Depends(get_db)
):
    """Create a new blocked time"""
    # Check if business exists
    if blocked_time.business_id:
        business = db.query(Business).filter(Business.business_id == blocked_time.business_id).first()
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
    
    # Check if service exists if provided
    if blocked_time.service_id:
        service = db.query(Service).filter(Service.service_id == blocked_time.service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
    
    # Check if resource exists if provided
    if blocked_time.resource_id:
        resource = db.query(Resource).filter(Resource.resource_id == blocked_time.resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
    
    db_blocked_time = BlockedTime(**blocked_time.dict())
    db.add(db_blocked_time)
    db.commit()
    db.refresh(db_blocked_time)
    return db_blocked_time

@router.get("/blocked-times", response_model=List[BlockedTimeResponse])
def read_blocked_times(
    business_id: Optional[int] = None,
    service_id: Optional[int] = None,
    resource_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get blocked times with optional filtering"""
    query = db.query(BlockedTime)
    
    if business_id:
        query = query.filter(BlockedTime.business_id == business_id)
    
    if service_id:
        query = query.filter(BlockedTime.service_id == service_id)
    
    if resource_id:
        query = query.filter(BlockedTime.resource_id == resource_id)
    
    if start_date:
        query = query.filter(BlockedTime.end_datetime >= start_date)
    
    if end_date:
        query = query.filter(BlockedTime.start_datetime <= end_date)
    
    # Order by start time
    query = query.order_by(BlockedTime.start_datetime)
    
    blocked_times = query.all()
    return blocked_times

@router.put("/blocked-times/{block_id}", response_model=BlockedTimeResponse)
def update_blocked_time(
    block_id: int,
    blocked_time_update: BlockedTimeUpdate,
    db: Session = Depends(get_db)
):
    """Update a blocked time"""
    db_blocked_time = db.query(BlockedTime).filter(BlockedTime.block_id == block_id).first()
    if db_blocked_time is None:
        raise HTTPException(status_code=404, detail="Blocked time not found")
    
    update_data = blocked_time_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_blocked_time, key, value)
    
    db.commit()
    db.refresh(db_blocked_time)
    return db_blocked_time

@router.delete("/blocked-times/{block_id}")
def delete_blocked_time(
    block_id: int,
    db: Session = Depends(get_db)
):
    """Delete a blocked time"""
    db_blocked_time = db.query(BlockedTime).filter(BlockedTime.block_id == block_id).first()
    if db_blocked_time is None:
        raise HTTPException(status_code=404, detail="Blocked time not found")
    
    db.delete(db_blocked_time)
    db.commit()
    
    return {"message": "Blocked time deleted successfully"} 