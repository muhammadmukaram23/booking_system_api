from pydantic import BaseModel, EmailStr, Field, validator, condecimal
from typing import Optional, List, Dict, Any
from datetime import datetime, time
from enum import Enum
from decimal import Decimal

class BusinessTypeEnum(str, Enum):
    hotel = "hotel"
    restaurant = "restaurant"
    spa = "spa"
    event_venue = "event_venue"
    transport = "transport"
    tour = "tour"
    other = "other"

class BusinessStatusEnum(str, Enum):
    active = "active"
    pending = "pending"
    suspended = "suspended"
    closed = "closed"

class DayOfWeekEnum(str, Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"

class BusinessBase(BaseModel):
    business_name: str
    business_type: BusinessTypeEnum
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    license_number: Optional[str] = None

class BusinessCreate(BusinessBase):
    pass

class BusinessUpdate(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[BusinessTypeEnum] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    license_number: Optional[str] = None
    status: Optional[BusinessStatusEnum] = None
    featured: Optional[bool] = None

class BusinessResponse(BusinessBase):
    business_id: int
    owner_id: int
    rating: condecimal(max_digits=3, decimal_places=2)
    total_reviews: int
    status: BusinessStatusEnum
    featured: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class BusinessAddressBase(BaseModel):
    street_address: str
    city: str
    state: str
    postal_code: str
    country: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_primary: bool = False

class BusinessAddressCreate(BusinessAddressBase):
    pass

class BusinessAddressUpdate(BaseModel):
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_primary: Optional[bool] = None

class BusinessAddressResponse(BusinessAddressBase):
    address_id: int
    business_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class BusinessHoursBase(BaseModel):
    day_of_week: DayOfWeekEnum
    open_time: Optional[time] = None
    close_time: Optional[time] = None
    is_open: bool = True

class BusinessHoursCreate(BusinessHoursBase):
    pass

class BusinessHoursUpdate(BaseModel):
    open_time: Optional[time] = None
    close_time: Optional[time] = None
    is_open: Optional[bool] = None

class BusinessHoursResponse(BusinessHoursBase):
    hours_id: int
    business_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class BusinessWithDetails(BusinessResponse):
    addresses: List[BusinessAddressResponse] = []
    hours: List[BusinessHoursResponse] = []
    
    class Config:
        orm_mode = True 