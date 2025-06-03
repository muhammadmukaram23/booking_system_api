from pydantic import BaseModel, Field, validator, condecimal
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal

class DiscountTypeEnum(str, Enum):
    percentage = "percentage"
    fixed_amount = "fixed_amount"
    free_service = "free_service"

class PromotionStatusEnum(str, Enum):
    active = "active"
    inactive = "inactive"
    expired = "expired"

class PromotionBase(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    discount_type: DiscountTypeEnum
    discount_value: condecimal(max_digits=10, decimal_places=2)
    minimum_amount: condecimal(max_digits=10, decimal_places=2) = Decimal('0.00')
    maximum_discount: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    usage_limit: Optional[int] = None
    per_user_limit: int = 1
    valid_from: datetime
    valid_until: datetime
    applicable_services: Optional[Dict[str, Any]] = None
    applicable_days: Optional[Dict[str, Any]] = None
    business_id: Optional[int] = None
    
    @validator('discount_value')
    def validate_discount_value(cls, v, values):
        if values.get('discount_type') == DiscountTypeEnum.percentage and v > 100:
            raise ValueError('Percentage discount cannot be greater than 100%')
        if v <= 0:
            raise ValueError('Discount value must be greater than zero')
        return v
    
    @validator('valid_until')
    def validate_valid_until(cls, v, values):
        if 'valid_from' in values and v <= values['valid_from']:
            raise ValueError('End date must be after start date')
        return v

class PromotionCreate(PromotionBase):
    created_by: int

class PromotionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[DiscountTypeEnum] = None
    discount_value: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    minimum_amount: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    maximum_discount: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    usage_limit: Optional[int] = None
    per_user_limit: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    applicable_services: Optional[Dict[str, Any]] = None
    applicable_days: Optional[Dict[str, Any]] = None
    status: Optional[PromotionStatusEnum] = None

class PromotionResponse(PromotionBase):
    promotion_id: int
    usage_count: int
    status: PromotionStatusEnum
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class PromotionUsageBase(BaseModel):
    promotion_id: int
    user_id: int
    booking_id: int
    discount_amount: condecimal(max_digits=10, decimal_places=2)
    
    @validator('discount_amount')
    def validate_discount_amount(cls, v):
        if v <= 0:
            raise ValueError('Discount amount must be greater than zero')
        return v

class PromotionUsageCreate(PromotionUsageBase):
    pass

class PromotionUsageResponse(PromotionUsageBase):
    usage_id: int
    used_at: datetime
    
    class Config:
        orm_mode = True

class PromotionValidationRequest(BaseModel):
    code: str
    user_id: int
    business_id: Optional[int] = None
    amount: condecimal(max_digits=10, decimal_places=2)

class PromotionValidationResponse(BaseModel):
    is_valid: bool
    promotion: Optional[PromotionResponse] = None
    discount_amount: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    error_message: Optional[str] = None 