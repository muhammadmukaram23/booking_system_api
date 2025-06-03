from pydantic import BaseModel, Field, validator, condecimal
from typing import Optional, List, Dict, Any
from datetime import datetime, time
from enum import Enum
from decimal import Decimal

class CategoryBase(BaseModel):
    category_name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0
    parent_category_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    category_name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    parent_category_id: Optional[int] = None

class CategoryResponse(CategoryBase):
    category_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class ServiceBase(BaseModel):
    service_name: str
    description: Optional[str] = None
    duration_minutes: int = 60
    base_price: condecimal(max_digits=10, decimal_places=2)
    max_capacity: int = 1
    advance_booking_hours: int = 24
    cancellation_hours: int = 24
    image_url: Optional[str] = None
    is_active: bool = True
    requires_approval: bool = False
    category_id: Optional[int] = None

class ServiceCreate(ServiceBase):
    business_id: int

class ServiceUpdate(BaseModel):
    service_name: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    base_price: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    max_capacity: Optional[int] = None
    advance_booking_hours: Optional[int] = None
    cancellation_hours: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    requires_approval: Optional[bool] = None
    category_id: Optional[int] = None

class ServiceResponse(ServiceBase):
    service_id: int
    business_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class ServicePricingBase(BaseModel):
    pricing_name: str
    price: condecimal(max_digits=10, decimal_places=2)
    duration_minutes: Optional[int] = None
    max_participants: int = 1
    description: Optional[str] = None
    is_default: bool = False

class ServicePricingCreate(ServicePricingBase):
    service_id: int

class ServicePricingUpdate(BaseModel):
    pricing_name: Optional[str] = None
    price: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    duration_minutes: Optional[int] = None
    max_participants: Optional[int] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None

class ServicePricingResponse(ServicePricingBase):
    pricing_id: int
    service_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class ResourceTypeEnum(str, Enum):
    room = "room"
    table = "table"
    equipment = "equipment"
    vehicle = "vehicle"
    person = "person"
    other = "other"

class ResourceBase(BaseModel):
    resource_name: str
    resource_type: ResourceTypeEnum
    capacity: int = 1
    description: Optional[str] = None
    hourly_rate: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    daily_rate: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    features: Optional[Dict[str, Any]] = None
    is_active: bool = True

class ResourceCreate(ResourceBase):
    business_id: int

class ResourceUpdate(BaseModel):
    resource_name: Optional[str] = None
    resource_type: Optional[ResourceTypeEnum] = None
    capacity: Optional[int] = None
    description: Optional[str] = None
    hourly_rate: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    daily_rate: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    features: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class ResourceResponse(ResourceBase):
    resource_id: int
    business_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class DayOfWeekEnum(str, Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"

class AvailabilityTemplateBase(BaseModel):
    day_of_week: DayOfWeekEnum
    start_time: time
    end_time: time
    slot_duration: int = 60
    max_bookings: int = 1
    is_active: bool = True
    service_id: Optional[int] = None
    resource_id: Optional[int] = None
    
    @validator('resource_id')
    def validate_resource_service(cls, v, values):
        if v is None and values.get('service_id') is None:
            raise ValueError('Either service_id or resource_id must be provided')
        if v is not None and values.get('service_id') is not None:
            raise ValueError('Only one of service_id or resource_id should be provided')
        return v

class AvailabilityTemplateCreate(AvailabilityTemplateBase):
    pass

class AvailabilityTemplateUpdate(BaseModel):
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    slot_duration: Optional[int] = None
    max_bookings: Optional[int] = None
    is_active: Optional[bool] = None

class AvailabilityTemplateResponse(AvailabilityTemplateBase):
    template_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class AvailabilitySlotBase(BaseModel):
    start_datetime: datetime
    end_datetime: datetime
    available_spots: int = 1
    booked_spots: int = 0
    price_override: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    status: str = "available"
    notes: Optional[str] = None
    service_id: Optional[int] = None
    resource_id: Optional[int] = None
    
    @validator('resource_id')
    def validate_resource_service(cls, v, values):
        if v is None and values.get('service_id') is None:
            raise ValueError('Either service_id or resource_id must be provided')
        if v is not None and values.get('service_id') is not None:
            raise ValueError('Only one of service_id or resource_id should be provided')
        return v

class AvailabilitySlotCreate(AvailabilitySlotBase):
    pass

class AvailabilitySlotUpdate(BaseModel):
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    available_spots: Optional[int] = None
    booked_spots: Optional[int] = None
    price_override: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class AvailabilitySlotResponse(AvailabilitySlotBase):
    slot_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class BlockedTimeBase(BaseModel):
    start_datetime: datetime
    end_datetime: datetime
    reason: Optional[str] = None
    block_type: str = "other"
    business_id: Optional[int] = None
    service_id: Optional[int] = None
    resource_id: Optional[int] = None

class BlockedTimeCreate(BlockedTimeBase):
    created_by: int

class BlockedTimeUpdate(BaseModel):
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    reason: Optional[str] = None
    block_type: Optional[str] = None

class BlockedTimeResponse(BlockedTimeBase):
    block_id: int
    created_by: int
    created_at: datetime
    
    class Config:
        orm_mode = True 