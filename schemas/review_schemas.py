from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ReviewStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    hidden = "hidden"

class ReviewBase(BaseModel):
    booking_id: int
    business_id: int
    service_id: Optional[int] = None
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    pros: Optional[str] = None
    cons: Optional[str] = None
    would_recommend: Optional[bool] = None
    
    @validator('rating')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

class ReviewCreate(ReviewBase):
    user_id: int

class ReviewUpdate(BaseModel):
    title: Optional[str] = None
    comment: Optional[str] = None
    pros: Optional[str] = None
    cons: Optional[str] = None
    would_recommend: Optional[bool] = None
    is_featured: Optional[bool] = None
    status: Optional[ReviewStatusEnum] = None

class ReviewResponse(ReviewBase):
    review_id: int
    user_id: int
    is_verified: bool
    is_featured: bool
    status: ReviewStatusEnum
    helpful_votes: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class ReviewResponseBase(BaseModel):
    review_id: int
    business_id: int
    response_text: str

class ReviewResponseCreate(ReviewResponseBase):
    responded_by: int

class ReviewResponseUpdate(BaseModel):
    response_text: str

class ReviewResponseResponse(ReviewResponseBase):
    response_id: int
    responded_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class ReviewWithResponsesResponse(ReviewResponse):
    responses: List[ReviewResponseResponse] = []
    
    class Config:
        orm_mode = True 