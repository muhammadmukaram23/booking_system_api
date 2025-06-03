from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from main import get_db
from models.models import Review, ReviewResponse as ReviewResponseModel, User, Booking, Business, Service
from schemas.review_schemas import (
    ReviewBase, ReviewResponse, ReviewResponseBase, 
    ReviewResponseResponse, ReviewStatusEnum
)
from auth.auth import get_current_user, get_current_active_user, check_business_owner_permission

router = APIRouter(
    prefix="/api/reviews",
    tags=["Reviews"],
    responses={404: {"description": "Not found"}},
)

# Create a new review
@router.post("/", response_model=ReviewResponse)
def create_review(
    review: ReviewBase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new review for a booking"""
    # Verify the booking exists and belongs to the user
    booking = db.query(Booking).filter(
        Booking.booking_id == review.booking_id,
        Booking.user_id == current_user.user_id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found or doesn't belong to you")
    
    # Check if the booking status is completed
    if booking.status != "completed":
        raise HTTPException(status_code=400, detail="Can only review completed bookings")
    
    # Check if user already reviewed this booking
    existing_review = db.query(Review).filter(
        Review.booking_id == review.booking_id,
        Review.user_id == current_user.user_id
    ).first()
    
    if existing_review:
        raise HTTPException(status_code=400, detail="You have already reviewed this booking")
    
    # Create the review
    db_review = Review(
        booking_id=review.booking_id,
        user_id=current_user.user_id,
        business_id=review.business_id,
        service_id=review.service_id,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        pros=review.pros,
        cons=review.cons,
        would_recommend=review.would_recommend
    )
    
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    # Update business average rating
    update_business_rating(db, review.business_id)
    
    return db_review

# Get all reviews for a business
@router.get("/business/{business_id}", response_model=List[ReviewResponse])
def get_business_reviews(
    business_id: int,
    skip: int = 0,
    limit: int = 100,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get all reviews for a specific business"""
    # Verify the business exists
    business = db.query(Business).filter(Business.business_id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Query reviews
    query = db.query(Review).filter(Review.business_id == business_id)
    
    # Apply filters
    if min_rating:
        query = query.filter(Review.rating >= min_rating)
    if max_rating:
        query = query.filter(Review.rating <= max_rating)
    
    # Apply status filter - only show approved reviews to general public
    query = query.filter(Review.status == "approved")
    
    # Order by most recent first
    query = query.order_by(Review.created_at.desc())
    
    reviews = query.offset(skip).limit(limit).all()
    return reviews

# Get all reviews for a service
@router.get("/service/{service_id}", response_model=List[ReviewResponse])
def get_service_reviews(
    service_id: int,
    skip: int = 0,
    limit: int = 100,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get all reviews for a specific service"""
    # Verify the service exists
    service = db.query(Service).filter(Service.service_id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Query reviews
    query = db.query(Review).filter(Review.service_id == service_id)
    
    # Apply filters
    if min_rating:
        query = query.filter(Review.rating >= min_rating)
    if max_rating:
        query = query.filter(Review.rating <= max_rating)
    
    # Apply status filter - only show approved reviews to general public
    query = query.filter(Review.status == "approved")
    
    # Order by most recent first
    query = query.order_by(Review.created_at.desc())
    
    reviews = query.offset(skip).limit(limit).all()
    return reviews

# Get all reviews by current user
@router.get("/my-reviews", response_model=List[ReviewResponse])
def get_user_reviews(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all reviews by the current user"""
    reviews = db.query(Review).filter(
        Review.user_id == current_user.user_id
    ).order_by(Review.created_at.desc()).offset(skip).limit(limit).all()
    
    return reviews

# Get a specific review
@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific review by ID"""
    review = db.query(Review).filter(Review.review_id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Only show approved reviews to general public unless it's admin or business owner
    if review.status != "approved":
        raise HTTPException(status_code=404, detail="Review not found")
    
    return review

# Update a review
@router.put("/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: int,
    review_update: ReviewBase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a review by the current user"""
    db_review = db.query(Review).filter(
        Review.review_id == review_id,
        Review.user_id == current_user.user_id
    ).first()
    
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found or doesn't belong to you")
    
    # Update review fields
    db_review.rating = review_update.rating
    db_review.title = review_update.title
    db_review.comment = review_update.comment
    db_review.pros = review_update.pros
    db_review.cons = review_update.cons
    db_review.would_recommend = review_update.would_recommend
    db_review.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_review)
    
    # Update business average rating
    update_business_rating(db, db_review.business_id)
    
    return db_review

# Delete a review
@router.delete("/{review_id}")
def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a review by the current user"""
    db_review = db.query(Review).filter(
        Review.review_id == review_id,
        Review.user_id == current_user.user_id
    ).first()
    
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found or doesn't belong to you")
    
    business_id = db_review.business_id
    
    db.delete(db_review)
    db.commit()
    
    # Update business average rating
    update_business_rating(db, business_id)
    
    return {"message": "Review deleted successfully"}

# Business owner endpoints for reviews

# Get all reviews for a business (including pending/rejected) for business owner
@router.get("/business/{business_id}/all", response_model=List[ReviewResponse])
def get_all_business_reviews(
    business_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[ReviewStatusEnum] = None,
    current_user: User = Depends(check_business_owner_permission),
    db: Session = Depends(get_db)
):
    """Get all reviews for a business (for business owner)"""
    # Query reviews
    query = db.query(Review).filter(Review.business_id == business_id)
    
    # Apply status filter if provided
    if status:
        query = query.filter(Review.status == status)
    
    # Order by most recent first
    query = query.order_by(Review.created_at.desc())
    
    reviews = query.offset(skip).limit(limit).all()
    return reviews

# Update review status (approve/reject/hide)
@router.patch("/{review_id}/status", response_model=ReviewResponse)
def update_review_status(
    review_id: int,
    status: ReviewStatusEnum,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update review status (for business owner)"""
    # Get the review
    review = db.query(Review).filter(Review.review_id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Check if current user is the business owner
    check_business_owner_permission(review.business_id, current_user)
    
    # Update status
    review.status = status
    review.updated_at = datetime.now()
    
    db.commit()
    db.refresh(review)
    
    return review

# Create a response to a review
@router.post("/response", response_model=ReviewResponseResponse)
def create_review_response(
    response: ReviewResponseBase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a response to a review (for business owner)"""
    # Check if review exists
    review = db.query(Review).filter(Review.review_id == response.review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Check if current user is the business owner
    check_business_owner_permission(response.business_id, current_user)
    
    # Check if response already exists
    existing_response = db.query(ReviewResponseModel).filter(
        ReviewResponseModel.review_id == response.review_id
    ).first()
    
    if existing_response:
        raise HTTPException(status_code=400, detail="A response already exists for this review")
    
    # Create response
    db_response = ReviewResponseModel(
        review_id=response.review_id,
        business_id=response.business_id,
        response_text=response.response_text,
        responded_by=current_user.user_id
    )
    
    db.add(db_response)
    db.commit()
    db.refresh(db_response)
    
    return db_response

# Update a review response
@router.put("/response/{response_id}", response_model=ReviewResponseResponse)
def update_review_response(
    response_id: int,
    response_update: ReviewResponseBase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a response to a review (for business owner)"""
    # Get the response
    db_response = db.query(ReviewResponseModel).filter(ReviewResponseModel.response_id == response_id).first()
    if not db_response:
        raise HTTPException(status_code=404, detail="Response not found")
    
    # Check if current user is the business owner
    check_business_owner_permission(db_response.business_id, current_user)
    
    # Update response
    db_response.response_text = response_update.response_text
    db_response.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_response)
    
    return db_response

# Delete a review response
@router.delete("/response/{response_id}")
def delete_review_response(
    response_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a response to a review (for business owner)"""
    # Get the response
    db_response = db.query(ReviewResponseModel).filter(ReviewResponseModel.response_id == response_id).first()
    if not db_response:
        raise HTTPException(status_code=404, detail="Response not found")
    
    # Check if current user is the business owner
    check_business_owner_permission(db_response.business_id, current_user)
    
    db.delete(db_response)
    db.commit()
    
    return {"message": "Response deleted successfully"}

# Helper function to update business average rating
def update_business_rating(db: Session, business_id: int):
    """Update the average rating for a business"""
    # Get all approved reviews for the business
    reviews = db.query(Review).filter(
        Review.business_id == business_id,
        Review.status == "approved"
    ).all()
    
    # Calculate average rating
    if reviews:
        total_rating = sum(review.rating for review in reviews)
        avg_rating = total_rating / len(reviews)
    else:
        avg_rating = 0
    
    # Update business rating
    business = db.query(Business).filter(Business.business_id == business_id).first()
    if business:
        business.rating = avg_rating
        business.review_count = len(reviews)
        db.commit() 