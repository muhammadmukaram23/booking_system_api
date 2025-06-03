from pydantic import BaseModel, Field, validator, condecimal
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time
from enum import Enum
from decimal import Decimal

class BookingStatusEnum(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"

class PaymentStatusEnum(str, Enum):
    pending = "pending"
    partial = "partial"
    paid = "paid"
    refunded = "refunded"
    failed = "failed"

class BookingBase(BaseModel):
    service_id: Optional[int] = None
    resource_id: Optional[int] = None
    slot_id: Optional[int] = None
    booking_date: date
    start_time: time
    end_time: time
    participants: int = 1
    special_requests: Optional[str] = None
    
    @validator('resource_id')
    def validate_resource_service(cls, v, values):
        if v is None and values.get('service_id') is None and values.get('slot_id') is None:
            raise ValueError('Either service_id, resource_id, or slot_id must be provided')
        return v

class BookingCreate(BookingBase):
    business_id: int
    total_amount: condecimal(max_digits=10, decimal_places=2)
    
    @validator('total_amount')
    def validate_total_amount(cls, v):
        if v <= 0:
            raise ValueError('Total amount must be greater than zero')
        return v

class BookingUpdate(BaseModel):
    booking_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    participants: Optional[int] = None
    total_amount: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    status: Optional[BookingStatusEnum] = None
    payment_status: Optional[PaymentStatusEnum] = None
    special_requests: Optional[str] = None
    internal_notes: Optional[str] = None

class BookingResponse(BaseModel):
    booking_id: int
    booking_reference: str
    user_id: int
    business_id: int
    service_id: Optional[int] = None
    resource_id: Optional[int] = None
    slot_id: Optional[int] = None
    booking_date: date
    start_time: time
    end_time: time
    start_datetime: datetime
    end_datetime: datetime
    participants: int
    total_amount: condecimal(max_digits=10, decimal_places=2)
    deposit_amount: condecimal(max_digits=10, decimal_places=2)
    tax_amount: condecimal(max_digits=10, decimal_places=2)
    discount_amount: condecimal(max_digits=10, decimal_places=2)
    final_amount: condecimal(max_digits=10, decimal_places=2)
    currency: str
    status: BookingStatusEnum
    payment_status: PaymentStatusEnum
    special_requests: Optional[str] = None
    confirmation_code: Optional[str] = None
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[int] = None
    cancellation_reason: Optional[str] = None
    
    class Config:
        orm_mode = True

class BookingCancellation(BaseModel):
    cancellation_reason: str

class BookingParticipantBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    special_requirements: Optional[str] = None

class BookingParticipantCreate(BookingParticipantBase):
    booking_id: int

class BookingParticipantUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    special_requirements: Optional[str] = None

class BookingParticipantResponse(BookingParticipantBase):
    participant_id: int
    booking_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class BookingHistoryBase(BaseModel):
    old_status: Optional[str] = None
    new_status: str
    change_reason: Optional[str] = None

class BookingHistoryCreate(BookingHistoryBase):
    booking_id: int
    changed_by: int

class BookingHistoryResponse(BookingHistoryBase):
    history_id: int
    booking_id: int
    changed_by: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class BookingDetailResponse(BookingResponse):
    participants_list: List[BookingParticipantResponse] = []
    history: List[BookingHistoryResponse] = []
    
    class Config:
        orm_mode = True 