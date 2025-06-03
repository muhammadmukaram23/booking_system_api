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
    user_id: int,
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
        user_id=user_id,
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
        changed_by=user_id,
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

@router.get("/user/{user_id}", response_model=List[BookingResponse])
def read_user_bookings(
    user_id: int,
    status: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get all bookings for a user"""
    query = db.query(Booking).filter(Booking.user_id == user_id)
    
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
    db: Session = Depends(get_db)
):
    """Get all bookings for a business"""
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
    db: Session = Depends(get_db)
):
    """Get a specific booking with details"""
    db_booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return db_booking

@router.put("/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: int,
    booking_update: BookingUpdate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Update a booking"""
    db_booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Update booking fields
    update_data = booking_update.dict(exclude_unset=True)
    
    # Handle date and time changes
    if "booking_date" in update_data or "start_time" in update_data or "end_time" in update_data:
        booking_date = update_data.get("booking_date", db_booking.booking_date)
        start_time = update_data.get("start_time", db_booking.start_time)
        end_time = update_data.get("end_time", db_booking.end_time)
        
        start_datetime = datetime.combine(booking_date, start_time)
        end_datetime = datetime.combine(booking_date, end_time)
        
        # If end time is earlier than start time, assume it's the next day
        if end_datetime <= start_datetime:
            end_datetime += timedelta(days=1)
        
        # Check availability
        is_available, message = check_availability(
            db, db_booking.service_id, db_booking.resource_id, 
            start_datetime, end_datetime, db_booking.participants
        )
        
        if not is_available:
            raise HTTPException(status_code=400, detail=message)
        
        update_data["start_datetime"] = start_datetime
        update_data["end_datetime"] = end_datetime
    
    # Apply updates
    for key, value in update_data.items():
        setattr(db_booking, key, value)
    
    # Log status change if applicable
    if "status" in update_data and update_data["status"] != db_booking.status:
        history = BookingHistory(
            booking_id=booking_id,
            new_status=update_data["status"],
            changed_by=user_id,
            change_reason=booking_update.change_reason or "Status updated"
        )
        db.add(history)
    
    db.commit()
    db.refresh(db_booking)
    return db_booking

@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    cancellation: BookingCancellation,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Cancel a booking"""
    db_booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check if booking can be cancelled
    if db_booking.status in ["cancelled", "completed", "no_show"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel a booking with status '{db_booking.status}'")
    
    # Update booking status
    db_booking.status = "cancelled"
    db_booking.cancellation_reason = cancellation.cancellation_reason
    
    # Log cancellation in history
    history = BookingHistory(
        booking_id=booking_id,
        new_status="cancelled",
        changed_by=user_id,
        change_reason=cancellation.cancellation_reason or "Booking cancelled"
    )
    db.add(history)
    
    # Update availability slot if applicable
    if db_booking.service_id and db_booking.slot_id:
        slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.slot_id == db_booking.slot_id).first()
        if slot:
            slot.booked_spots -= db_booking.participants
            db.commit()
    
    db.commit()
    db.refresh(db_booking)
    return db_booking

# Booking participants endpoints
@router.post("/participants", response_model=BookingParticipantResponse)
def create_booking_participant(
    participant: BookingParticipantCreate,
    db: Session = Depends(get_db)
):
    """Create a new booking participant"""
    # Check if booking exists
    booking = db.query(Booking).filter(Booking.booking_id == participant.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db_participant = BookingParticipant(**participant.dict())
    db.add(db_participant)
    db.commit()
    db.refresh(db_participant)
    return db_participant

@router.get("/participants/{booking_id}", response_model=List[BookingParticipantResponse])
def read_booking_participants(
    booking_id: int,
    db: Session = Depends(get_db)
):
    """Get all participants for a booking"""
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    participants = db.query(BookingParticipant).filter(BookingParticipant.booking_id == booking_id).all()
    return participants

@router.put("/participants/{participant_id}", response_model=BookingParticipantResponse)
def update_booking_participant(
    participant_id: int,
    participant_update: BookingParticipantUpdate,
    db: Session = Depends(get_db)
):
    """Update a booking participant"""
    db_participant = db.query(BookingParticipant).filter(BookingParticipant.participant_id == participant_id).first()
    if db_participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    update_data = participant_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_participant, key, value)
    
    db.commit()
    db.refresh(db_participant)
    return db_participant

@router.delete("/participants/{participant_id}")
def delete_booking_participant(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Delete a booking participant"""
    db_participant = db.query(BookingParticipant).filter(BookingParticipant.participant_id == participant_id).first()
    if db_participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    db.delete(db_participant)
    db.commit()
    
    return {"message": "Participant deleted successfully"} 