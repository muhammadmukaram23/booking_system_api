from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, ForeignKey, Enum, DECIMAL, JSON, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, date
import enum

Base = declarative_base()

# Enums
class GenderEnum(str, enum.Enum):
    M = "M"
    F = "F"
    Other = "Other"

class UserStatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"

class AddressTypeEnum(str, enum.Enum):
    home = "home"
    work = "work"
    billing = "billing"
    other = "other"

class BusinessTypeEnum(str, enum.Enum):
    hotel = "hotel"
    restaurant = "restaurant"
    spa = "spa"
    event_venue = "event_venue"
    transport = "transport"
    tour = "tour"
    other = "other"

class BusinessStatusEnum(str, enum.Enum):
    active = "active"
    pending = "pending"
    suspended = "suspended"
    closed = "closed"

class DayOfWeekEnum(str, enum.Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"

class ResourceTypeEnum(str, enum.Enum):
    room = "room"
    table = "table"
    equipment = "equipment"
    vehicle = "vehicle"
    person = "person"
    other = "other"

class BookingStatusEnum(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"

class PaymentStatusEnum(str, enum.Enum):
    pending = "pending"
    partial = "partial"
    paid = "paid"
    refunded = "refunded"
    failed = "failed"

# Models
class User(Base):
    __tablename__ = "user_tb"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(20))
    date_of_birth = Column(Date)
    gender = Column(Enum(GenderEnum), default=GenderEnum.Other)
    profile_image = Column(String(255))
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    status = Column(Enum(UserStatusEnum), default=UserStatusEnum.active)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)
    
    addresses = relationship("UserAddress", back_populates="user")
    user_roles = relationship("UserRole", back_populates="user")
    businesses = relationship("Business", back_populates="owner")
    bookings = relationship("Booking", foreign_keys="Booking.user_id", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    payment_methods = relationship("PaymentMethod", back_populates="user")

class UserAddress(Base):
    __tablename__ = "user_addresses"
    
    address_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_tb.user_id", ondelete="CASCADE"), nullable=False)
    address_type = Column(Enum(AddressTypeEnum), default=AddressTypeEnum.home)
    street_address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="addresses")
    payment_methods = relationship("PaymentMethod", back_populates="billing_address")

class Role(Base):
    __tablename__ = "roles"
    
    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    user_roles = relationship("UserRole", back_populates="role")

class UserRole(Base):
    __tablename__ = "user_roles"
    
    user_id = Column(Integer, ForeignKey("user_tb.user_id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")

class Business(Base):
    __tablename__ = "businesses"
    
    business_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("user_tb.user_id", ondelete="CASCADE"), nullable=False)
    business_name = Column(String(100), nullable=False)
    business_type = Column(Enum(BusinessTypeEnum), nullable=False)
    description = Column(Text)
    phone = Column(String(20))
    email = Column(String(100))
    website = Column(String(255))
    tax_id = Column(String(50))
    license_number = Column(String(100))
    rating = Column(DECIMAL(3, 2), default=0.00)
    total_reviews = Column(Integer, default=0)
    status = Column(Enum(BusinessStatusEnum), default=BusinessStatusEnum.pending)
    featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    owner = relationship("User", back_populates="businesses")
    addresses = relationship("BusinessAddress", back_populates="business")
    hours = relationship("BusinessHours", back_populates="business")
    services = relationship("Service", back_populates="business")
    resources = relationship("Resource", back_populates="business")
    bookings = relationship("Booking", back_populates="business")
    reviews = relationship("Review", back_populates="business")
    promotions = relationship("Promotion", back_populates="business")

class BusinessAddress(Base):
    __tablename__ = "business_addresses"
    
    address_id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.business_id", ondelete="CASCADE"), nullable=False)
    street_address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False)
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    business = relationship("Business", back_populates="addresses")

class BusinessHours(Base):
    __tablename__ = "business_hours"
    
    hours_id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.business_id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Enum(DayOfWeekEnum), nullable=False)
    open_time = Column(Time)
    close_time = Column(Time)
    is_open = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    business = relationship("Business", back_populates="hours")

class Category(Base):
    __tablename__ = "categories"
    
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False)
    parent_category_id = Column(Integer, ForeignKey("categories.category_id", ondelete="SET NULL"))
    description = Column(Text)
    image_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    
    services = relationship("Service", back_populates="category")
    subcategories = relationship("Category", foreign_keys=[parent_category_id])
    parent_category = relationship("Category", remote_side=[category_id], foreign_keys=[parent_category_id])

class Service(Base):
    __tablename__ = "services"
    
    service_id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.business_id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.category_id", ondelete="SET NULL"))
    service_name = Column(String(100), nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer, nullable=False, default=60)
    base_price = Column(DECIMAL(10, 2), nullable=False)
    max_capacity = Column(Integer, default=1)
    advance_booking_hours = Column(Integer, default=24)
    cancellation_hours = Column(Integer, default=24)
    image_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    business = relationship("Business", back_populates="services")
    category = relationship("Category", back_populates="services")
    pricing_tiers = relationship("ServicePricing", back_populates="service")
    availability_templates = relationship("AvailabilityTemplate", back_populates="service")
    availability_slots = relationship("AvailabilitySlot", back_populates="service")
    bookings = relationship("Booking", back_populates="service")
    reviews = relationship("Review", back_populates="service")

class ServicePricing(Base):
    __tablename__ = "service_pricing"
    
    pricing_id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.service_id", ondelete="CASCADE"), nullable=False)
    pricing_name = Column(String(100), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    duration_minutes = Column(Integer)
    max_participants = Column(Integer, default=1)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    service = relationship("Service", back_populates="pricing_tiers")

class Resource(Base):
    __tablename__ = "resources"
    
    resource_id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.business_id", ondelete="CASCADE"), nullable=False)
    resource_name = Column(String(100), nullable=False)
    resource_type = Column(Enum(ResourceTypeEnum), nullable=False)
    capacity = Column(Integer, default=1)
    description = Column(Text)
    hourly_rate = Column(DECIMAL(10, 2))
    daily_rate = Column(DECIMAL(10, 2))
    features = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    business = relationship("Business", back_populates="resources")
    availability_templates = relationship("AvailabilityTemplate", back_populates="resource")
    availability_slots = relationship("AvailabilitySlot", back_populates="resource")
    bookings = relationship("Booking", back_populates="resource")

class AvailabilityTemplate(Base):
    __tablename__ = "availability_templates"
    
    template_id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.service_id", ondelete="CASCADE"))
    resource_id = Column(Integer, ForeignKey("resources.resource_id", ondelete="CASCADE"))
    day_of_week = Column(Enum(DayOfWeekEnum), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    slot_duration = Column(Integer, default=60)
    max_bookings = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    service = relationship("Service", back_populates="availability_templates")
    resource = relationship("Resource", back_populates="availability_templates")

class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"
    
    slot_id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.service_id", ondelete="CASCADE"))
    resource_id = Column(Integer, ForeignKey("resources.resource_id", ondelete="CASCADE"))
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    available_spots = Column(Integer, default=1)
    booked_spots = Column(Integer, default=0)
    price_override = Column(DECIMAL(10, 2))
    status = Column(String(20), default="available")
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    service = relationship("Service", back_populates="availability_slots")
    resource = relationship("Resource", back_populates="availability_slots")
    bookings = relationship("Booking", back_populates="slot")

class BlockedTime(Base):
    __tablename__ = "blocked_times"
    
    block_id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.business_id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.service_id", ondelete="CASCADE"))
    resource_id = Column(Integer, ForeignKey("resources.resource_id", ondelete="CASCADE"))
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    reason = Column(String(255))
    block_type = Column(String(20), default="other")
    created_by = Column(Integer, ForeignKey("user_tb.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now())

class Booking(Base):
    __tablename__ = "bookings"
    
    booking_id = Column(Integer, primary_key=True, autoincrement=True)
    booking_reference = Column(String(50), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("user_tb.user_id", ondelete="CASCADE"), nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.business_id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.service_id", ondelete="SET NULL"))
    resource_id = Column(Integer, ForeignKey("resources.resource_id", ondelete="SET NULL"))
    slot_id = Column(Integer, ForeignKey("availability_slots.slot_id", ondelete="SET NULL"))
    booking_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    participants = Column(Integer, default=1)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    deposit_amount = Column(DECIMAL(10, 2), default=0.00)
    tax_amount = Column(DECIMAL(10, 2), default=0.00)
    discount_amount = Column(DECIMAL(10, 2), default=0.00)
    final_amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(Enum(BookingStatusEnum), default=BookingStatusEnum.pending)
    payment_status = Column(Enum(PaymentStatusEnum), default=PaymentStatusEnum.pending)
    special_requests = Column(Text)
    internal_notes = Column(Text)
    confirmation_code = Column(String(20))
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    cancelled_at = Column(DateTime)
    cancelled_by = Column(Integer, ForeignKey("user_tb.user_id", ondelete="SET NULL"))
    cancellation_reason = Column(Text)
    
    user = relationship("User", foreign_keys=[user_id], back_populates="bookings")
    business = relationship("Business", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")
    resource = relationship("Resource", back_populates="bookings")
    slot = relationship("AvailabilitySlot", back_populates="bookings")
    cancelled_by_user = relationship("User", foreign_keys=[cancelled_by])
    participants_list = relationship("BookingParticipant", back_populates="booking")
    history = relationship("BookingHistory", back_populates="booking")
    payments = relationship("Payment", back_populates="booking")
    reviews = relationship("Review", back_populates="booking")
    promotion_usages = relationship("PromotionUsage", back_populates="booking")

class BookingParticipant(Base):
    __tablename__ = "booking_participants"
    
    participant_id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100))
    phone = Column(String(20))
    age = Column(Integer)
    special_requirements = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    booking = relationship("Booking", back_populates="participants_list")

class BookingHistory(Base):
    __tablename__ = "booking_history"
    
    history_id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False)
    old_status = Column(String(50))
    new_status = Column(String(50), nullable=False)
    changed_by = Column(Integer, ForeignKey("user_tb.user_id", ondelete="CASCADE"), nullable=False)
    change_reason = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    booking = relationship("Booking", back_populates="history")

class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    
    method_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_tb.user_id", ondelete="CASCADE"), nullable=False)
    method_type = Column(String(20), nullable=False)
    card_last_four = Column(String(4))
    card_brand = Column(String(20))
    card_expiry_month = Column(Integer)
    card_expiry_year = Column(Integer)
    billing_address_id = Column(Integer, ForeignKey("user_addresses.address_id", ondelete="SET NULL"))
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="payment_methods")
    billing_address = relationship("UserAddress", back_populates="payment_methods")
    payments = relationship("Payment", back_populates="payment_method")

class Payment(Base):
    __tablename__ = "payments"
    
    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False)
    payment_reference = Column(String(100), unique=True, nullable=False)
    payment_method_id = Column(Integer, ForeignKey("payment_methods.method_id", ondelete="SET NULL"))
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    payment_type = Column(String(20), default="booking")
    status = Column(String(20), default="pending")
    gateway = Column(String(50))
    gateway_transaction_id = Column(String(255))
    gateway_response = Column(JSON)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    booking = relationship("Booking", back_populates="payments")
    payment_method = relationship("PaymentMethod", back_populates="payments")
    refunds = relationship("Refund", back_populates="payment")

class Refund(Base):
    __tablename__ = "refunds"
    
    refund_id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(Integer, ForeignKey("payments.payment_id", ondelete="CASCADE"), nullable=False)
    refund_reference = Column(String(100), unique=True, nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    reason = Column(Text)
    status = Column(String(20), default="pending")
    gateway_refund_id = Column(String(255))
    processed_by = Column(Integer, ForeignKey("user_tb.user_id", ondelete="SET NULL"))
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    payment = relationship("Payment", back_populates="refunds")

class Review(Base):
    __tablename__ = "reviews"
    
    review_id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("user_tb.user_id", ondelete="CASCADE"), nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.business_id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.service_id", ondelete="SET NULL"))
    rating = Column(Integer, nullable=False)
    title = Column(String(255))
    comment = Column(Text)
    pros = Column(Text)
    cons = Column(Text)
    would_recommend = Column(Boolean)
    is_verified = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    status = Column(String(20), default="pending")
    helpful_votes = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    booking = relationship("Booking", back_populates="reviews")
    user = relationship("User", back_populates="reviews")
    business = relationship("Business", back_populates="reviews")
    service = relationship("Service", back_populates="reviews")
    responses = relationship("ReviewResponse", back_populates="review")

class ReviewResponse(Base):
    __tablename__ = "review_responses"
    
    response_id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.review_id", ondelete="CASCADE"), nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.business_id", ondelete="CASCADE"), nullable=False)
    response_text = Column(Text, nullable=False)
    responded_by = Column(Integer, ForeignKey("user_tb.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    review = relationship("Review", back_populates="responses")

class Promotion(Base):
    __tablename__ = "promotions"
    
    promotion_id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.business_id", ondelete="CASCADE"))
    code = Column(String(50), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    discount_type = Column(String(20), nullable=False)
    discount_value = Column(DECIMAL(10, 2), nullable=False)
    minimum_amount = Column(DECIMAL(10, 2), default=0.00)
    maximum_discount = Column(DECIMAL(10, 2))
    usage_limit = Column(Integer)
    usage_count = Column(Integer, default=0)
    per_user_limit = Column(Integer, default=1)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    applicable_services = Column(JSON)
    applicable_days = Column(JSON)
    status = Column(String(20), default="active")
    created_by = Column(Integer, ForeignKey("user_tb.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    business = relationship("Business", back_populates="promotions")
    usages = relationship("PromotionUsage", back_populates="promotion")

class PromotionUsage(Base):
    __tablename__ = "promotion_usage"
    
    usage_id = Column(Integer, primary_key=True, autoincrement=True)
    promotion_id = Column(Integer, ForeignKey("promotions.promotion_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("user_tb.user_id", ondelete="CASCADE"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False)
    discount_amount = Column(DECIMAL(10, 2), nullable=False)
    used_at = Column(DateTime, default=func.now())
    
    promotion = relationship("Promotion", back_populates="usages")
    booking = relationship("Booking", back_populates="promotion_usages") 