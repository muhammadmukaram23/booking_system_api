from pydantic import BaseModel, Field, validator, condecimal
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal

class PaymentMethodTypeEnum(str, Enum):
    credit_card = "credit_card"
    debit_card = "debit_card"
    paypal = "paypal"
    bank_transfer = "bank_transfer"
    cash = "cash"
    other = "other"

class PaymentMethodBase(BaseModel):
    method_type: PaymentMethodTypeEnum
    card_last_four: Optional[str] = None
    card_brand: Optional[str] = None
    card_expiry_month: Optional[int] = None
    card_expiry_year: Optional[int] = None
    billing_address_id: Optional[int] = None
    is_default: bool = False
    is_active: bool = True
    
    @validator('card_last_four')
    def validate_card_last_four(cls, v, values):
        if values.get('method_type') in ['credit_card', 'debit_card'] and not v:
            raise ValueError('Card last four digits are required for credit/debit cards')
        return v
    
    @validator('card_expiry_month')
    def validate_expiry_month(cls, v, values):
        if values.get('method_type') in ['credit_card', 'debit_card']:
            if v is None:
                raise ValueError('Expiry month is required for credit/debit cards')
            if v < 1 or v > 12:
                raise ValueError('Expiry month must be between 1 and 12')
        return v
    
    @validator('card_expiry_year')
    def validate_expiry_year(cls, v, values):
        if values.get('method_type') in ['credit_card', 'debit_card'] and not v:
            raise ValueError('Expiry year is required for credit/debit cards')
        return v

class PaymentMethodCreate(PaymentMethodBase):
    user_id: int

class PaymentMethodUpdate(BaseModel):
    card_expiry_month: Optional[int] = None
    card_expiry_year: Optional[int] = None
    billing_address_id: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None

class PaymentMethodResponse(PaymentMethodBase):
    method_id: int
    user_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class PaymentTypeEnum(str, Enum):
    booking = "booking"
    deposit = "deposit"
    balance = "balance"
    refund = "refund"
    penalty = "penalty"

class PaymentStatusEnum(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    refunded = "refunded"

class PaymentBase(BaseModel):
    booking_id: int
    payment_reference: str
    payment_method_id: Optional[int] = None
    amount: condecimal(max_digits=10, decimal_places=2)
    currency: str = "USD"
    payment_type: PaymentTypeEnum = PaymentTypeEnum.booking
    gateway: Optional[str] = None
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Payment amount must be greater than zero')
        return v

class PaymentCreate(PaymentBase):
    pass

class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatusEnum] = None
    gateway_transaction_id: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None
    processed_at: Optional[datetime] = None

class PaymentResponse(PaymentBase):
    payment_id: int
    status: PaymentStatusEnum
    gateway_transaction_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class RefundStatusEnum(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class RefundBase(BaseModel):
    payment_id: int
    refund_reference: str
    amount: condecimal(max_digits=10, decimal_places=2)
    reason: Optional[str] = None
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Refund amount must be greater than zero')
        return v

class RefundCreate(RefundBase):
    processed_by: Optional[int] = None

class RefundUpdate(BaseModel):
    status: Optional[RefundStatusEnum] = None
    gateway_refund_id: Optional[str] = None
    processed_at: Optional[datetime] = None

class RefundResponse(RefundBase):
    refund_id: int
    status: RefundStatusEnum
    gateway_refund_id: Optional[str] = None
    processed_by: Optional[int] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        orm_mode = True 