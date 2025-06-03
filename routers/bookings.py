from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_, func, desc
from datetime import datetime, date, time, timedelta
import uuid

from main import get_db
from models.models import (
    Booking, BookingParticipant, BookingHistory, 
    Service, Resource, AvailabilitySlot, User, Business
)
from schemas.booking_schemas import (
    BookingCreate, BookingUpdate, BookingResponse, BookingDetailResponse,
    BookingParticipantCreate, BookingParticipantUpdate, BookingParticipantResponse,
    BookingHistoryCreate, BookingHistoryResponse, BookingCancellation
)
from auth.auth import get_current_active_user, check_business_owner_permission, check_admin_permission

router = APIRouter(
    prefix="/api/bookings",
    tags=["Bookings"],
    responses={404: {"description": "Not found"}},
)

# Helper function to generate booking reference
def generate_booking_reference():
    """Generate a unique booking reference"""
    return f"BK{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

# Helper function to check availability
def check_availability(
    db: Session,
    service_id: Optional[int],
    resource_id: Optional[int],
    start_datetime: datetime,
    end_datetime: datetime,
    participants: int
):
    """Check if a service or resource is available for booking"""
    # Check for service availability
    if service_id:
        # Check if there's an availability slot
        slot = db.query(AvailabilitySlot).filter(
            AvailabilitySlot.service_id == service_id,
            AvailabilitySlot.start_datetime <= start_datetime,
            AvailabilitySlot.end_datetime >= end_datetime,
            AvailabilitySlot.status == "available",
            (AvailabilitySlot.available_spots - AvailabilitySlot.booked_spots) >= participants
        ).first()
        
        if not slot:
            return False, "No available slots for this service at the selected time"
    
    # Check for resource availability
    if resource_id:
        # Check if there are conflicting bookings
        conflicting_bookings = db.query(Booking).filter(
            Booking.resource_id == resource_id,
            Booking.status.in_(["pending", "confirmed", "in_progress"]),
            Booking.start_datetime < end_datetime,
            Booking.end_datetime > start_datetime
        ).count()
        
        if conflicting_bookings > 0:
            return False, "Resource is already booked for this time"
    
    return True, "Available"

# Booking endpoints
@router.post("/", response_model=BookingResponse)
def create_booking(
    booking: BookingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new booking"""
    # Check if business exists
    business = db.query(Business).filter(Business.business_id == booking.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Convert booking date and time to datetime objects
    start_datetime = datetime.combine(booking.booking_date, booking.start_time)
    end_datetime = datetime.combine(booking.booking_date, booking.end_time)
    
    # If end time is earlier than start time, assume it's the next day
    if end_datetime <= start_datetime:
        end_datetime += timedelta(days=1)
    
    # Check availability
    is_available, message = check_availability(
        db, booking.service_id, booking.resource_id, 
        start_datetime, end_datetime, booking.participants
    )
    
    if not is_available:
        raise HTTPException(status_code=400, detail=message)
    
    # Create the booking
    booking_reference = generate_booking_reference()
    db_booking = Booking(
        booking_reference=booking_reference,
        user_id=current_user.user_id,
        business_id=booking.business_id,
        service_id=booking.service_id,
        resource_id=booking.resource_id,
        slot_id=booking.slot_id,
        booking_date=booking.booking_date,
        start_time=booking.start_time,
        end_time=booking.end_time,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        participants=booking.participants,
        total_amount=booking.total_amount,
        final_amount=booking.total_amount,  # Initially same as total amount
        special_requests=booking.special_requests,
        confirmation_code=str(uuid.uuid4())[:8].upper()
    )
    
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    
    # Log booking creation in history
    history = BookingHistory(
        booking_id=db_booking.booking_id,
        new_status="pending",
        changed_by=current_user.user_id,
        change_reason="Booking created"
    )
    db.add(history)
    
    # Update availability slot if applicable
    if booking.service_id and booking.slot_id:
        slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.slot_id == booking.slot_id).first()
        if slot:
            slot.booked_spots += booking.participants
            db.commit()
    
    db.commit()
    return db_booking

@router.get("/my-bookings", response_model=List[BookingResponse])
def read_my_bookings(
    status: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all bookings for current user"""
    query = db.query(Booking).filter(Booking.user_id == current_user.user_id)
    
    if status:
        query = query.filter(Booking.status == status)
    
    if from_date:
        query = query.filter(Booking.booking_date >= from_date)
    
    if to_date:
        query = query.filter(Booking.booking_date <= to_date)
    
    # Order by booking date (newest first)
    query = query.order_by(desc(Booking.booking_date), Booking.start_time)
    
    bookings = query.all()
    return bookings

@router.get("/business/{business_id}", response_model=List[BookingResponse])
def read_business_bookings(
    business_id: int,
    status: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all bookings for a business"""
    # Check if user is owner of the business
    check_business_owner_permission(business_id, current_user)
    
    query = db.query(Booking).filter(Booking.business_id == business_id)
    
    if status:
        query = query.filter(Booking.status == status)
    
    if from_date:
        query = query.filter(Booking.booking_date >= from_date)
    
    if to_date:
        query = query.filter(Booking.booking_date <= to_date)
    
    # Order by booking date (newest first)
    query = query.order_by(desc(Booking.booking_date), Booking.start_time)
    
    bookings = query.all()
    return bookings

@router.get("/{booking_id}", response_model=BookingDetailResponse)
def read_booking(
    booking_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific booking with details"""
    db_booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check if user is authorized to view this booking
    is_owner = db_booking.user_id == current_user.user_id
    is_business_owner = any(business.business_id == db_booking.business_id for business in current_user.businesses)
    is_admin = any(role.role.role_name == "admin" for role in current_user.user_roles)
    
    if not (is_owner or is_business_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to view this booking")
    
    return db_booking

@router.put("/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: int,
    booking_update: BookingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a booking"""
    db_booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check if user is authorized to update this booking
    is_owner = db_booking.user_id == current_user.user_id
    is_business_owner = any(business.business_id == db_booking.business_id for business in current_user.businesses)
    is_admin = any(role.role.role_name == "admin" for role in current_user.user_roles)
    
    if not (is_owner or is_business_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to update this booking")
    
    # Check if booking can be updated
    if db_booking.status in ["completed", "cancelled", "no_show"]:
        raise HTTPException(status_code=400, detail=f"Cannot update a booking with status: {db_booking.status}")
    
    update_data = booking_update.dict(exclude_unset=True)
    
    # Handle date and time changes
    if "booking_date" in update_data or "start_time" in update_data or "end_time" in update_data:
        new_booking_date = update_data.get("booking_date", db_booking.booking_date)
        new_start_time = update_data.get("start_time", db_booking.start_time)
        new_end_time = update_data.get("end_time", db_booking.end_time)
        
        new_start_datetime = datetime.combine(new_booking_date, new_start_time)
        new_end_datetime = datetime.combine(new_booking_date, new_end_time)
        
        # If end time is earlier than start time, assume it's the next day
        if new_end_datetime <= new_start_datetime:
            new_end_datetime += timedelta(days=1)
        
        # Check availability for the new time
        is_available, message = check_availability(
            db, db_booking.service_id, db_booking.resource_id, 
            new_start_datetime, new_end_datetime, 
            update_data.get("participants", db_booking.participants)
        )
        
        if not is_available:
            raise HTTPException(status_code=400, detail=message)
        
        update_data["start_datetime"] = new_start_datetime
        update_data["end_datetime"] = new_end_datetime
    
    # Handle status changes
    old_status = db_booking.status
    if "status" in update_data and update_data["status"] != old_status:
        # Log status change in history
        history = BookingHistory(
            booking_id=booking_id,
            old_status=old_status,
            new_status=update_data["status"],
            changed_by=current_user.user_id,
            change_reason="Status updated"
        )
        db.add(history)
    
    for key, value in update_data.items():
        setattr(db_booking, key, value)
    
    db.commit()
    db.refresh(db_booking)
    return db_booking

@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    cancellation: BookingCancellation,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a booking"""
    db_booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check if user is authorized to cancel this booking
    is_owner = db_booking.user_id == current_user.user_id
    is_business_owner = any(business.business_id == db_booking.business_id for business in current_user.businesses)
    is_admin = any(role.role.role_name == "admin" for role in current_user.user_roles)
    
    if not (is_owner or is_business_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")
    
    # Check if booking can be cancelled
    if db_booking.status in ["completed", "cancelled", "no_show"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel a booking with status: {db_booking.status}")
    
    # Update booking
    old_status = db_booking.status
    db_booking.status = "cancelled"
    db_booking.cancelled_at = datetime.now()
    db_booking.cancelled_by = current_user.user_id
    db_booking.cancellation_reason = cancellation.cancellation_reason
    
    # Log status change in history
    history = BookingHistory(
        booking_id=booking_id,
        old_status=old_status,
        new_status="cancelled",
        changed_by=current_user.user_id,
        change_reason=cancellation.cancellation_reason
    )
    db.add(history)
    
    # Update availability slot if applicable
    if db_booking.service_id and db_booking.slot_id:
        slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.slot_id == db_booking.slot_id).first()
        if slot:
            slot.booked_spots -= db_booking.participants
            if slot.booked_spots < 0:
                slot.booked_spots = 0
    
    db.commit()
    db.refresh(db_booking)
    return db_booking

# Booking participant endpoints
@router.post("/participants", response_model=BookingParticipantResponse)
def create_booking_participant(
    participant: BookingParticipantCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a participant to a booking"""
    # Check if booking exists and belongs to user
    db_booking = db.query(Booking).filter(Booking.booking_id == participant.booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if db_booking.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to add participants to this booking")
    
    # Check if booking can be modified
    if db_booking.status in ["completed", "cancelled", "no_show"]:
        raise HTTPException(status_code=400, detail=f"Cannot modify a booking with status: {db_booking.status}")
    
    # Create participant
    db_participant = BookingParticipant(**participant.dict())
    db.add(db_participant)
    db.commit()
    db.refresh(db_participant)
    return db_participant

@router.get("/participants/{booking_id}", response_model=List[BookingParticipantResponse])
def read_booking_participants(
    booking_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all participants for a booking"""
    # Check if booking exists
    db_booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check if user is authorized to view participants
    is_owner = db_booking.user_id == current_user.user_id
    is_business_owner = any(business.business_id == db_booking.business_id for business in current_user.businesses)
    is_admin = any(role.role.role_name == "admin" for role in current_user.user_roles)
    
    if not (is_owner or is_business_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to view participants for this booking")
    
    participants = db.query(BookingParticipant).filter(BookingParticipant.booking_id == booking_id).all()
    return participants

@router.put("/participants/{participant_id}", response_model=BookingParticipantResponse)
def update_booking_participant(
    participant_id: int,
    participant_update: BookingParticipantUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a booking participant"""
    # Get participant with booking
    db_participant = db.query(BookingParticipant).filter(BookingParticipant.participant_id == participant_id).first()
    if db_participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Check if booking belongs to user
    db_booking = db.query(Booking).filter(Booking.booking_id == db_participant.booking_id).first()
    if db_booking.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update participants for this booking")
    
    # Check if booking can be modified
    if db_booking.status in ["completed", "cancelled", "no_show"]:
        raise HTTPException(status_code=400, detail=f"Cannot modify a booking with status: {db_booking.status}")
    
    update_data = participant_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_participant, key, value)
    
    db.commit()
    db.refresh(db_participant)
    return db_participant

@router.delete("/participants/{participant_id}")
def delete_booking_participant(
    participant_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a booking participant"""
    # Get participant with booking
    db_participant = db.query(BookingParticipant).filter(BookingParticipant.participant_id == participant_id).first()
    if db_participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Check if booking belongs to user
    db_booking = db.query(Booking).filter(Booking.booking_id == db_participant.booking_id).first()
    if db_booking.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete participants for this booking")
    
    # Check if booking can be modified
    if db_booking.status in ["completed", "cancelled", "no_show"]:
        raise HTTPException(status_code=400, detail=f"Cannot modify a booking with status: {db_booking.status}")
    
    db.delete(db_participant)
    db.commit()
    
    return {"message": "Participant deleted successfully"} 