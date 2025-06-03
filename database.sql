-- =====================================================
-- COMPLETE BOOKING SYSTEM DATABASE
-- =====================================================

-- Drop existing database if exists and create new one
DROP DATABASE IF EXISTS booking_system;
CREATE DATABASE booking_system;
USE booking_system;

-- =====================================================
-- USER MANAGEMENT TABLES
-- =====================================================

-- Users table for authentication and basic info
CREATE TABLE user_tb (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    gender ENUM('M', 'F', 'Other') DEFAULT 'Other',
    profile_image VARCHAR(255),
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);

-- User addresses for billing and delivery
CREATE TABLE user_addresses (
    address_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    address_type ENUM('home', 'work', 'billing', 'other') DEFAULT 'home',
    street_address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_tb(user_id) ON DELETE CASCADE
);

-- User roles and permissions
CREATE TABLE roles (
    role_id INT PRIMARY KEY AUTO_INCREMENT,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_roles (
    user_id INT,
    role_id INT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES user_tb(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE
);

-- =====================================================
-- BUSINESS/VENDOR MANAGEMENT
-- =====================================================

-- Business/Service providers
CREATE TABLE businesses (
    business_id INT PRIMARY KEY AUTO_INCREMENT,
    owner_id INT NOT NULL,
    business_name VARCHAR(100) NOT NULL,
    business_type ENUM('hotel', 'restaurant', 'spa', 'event_venue', 'transport', 'tour', 'other') NOT NULL,
    description TEXT,
    phone VARCHAR(20),
    email VARCHAR(100),
    website VARCHAR(255),
    tax_id VARCHAR(50),
    license_number VARCHAR(100),
    rating DECIMAL(3,2) DEFAULT 0.00,
    total_reviews INT DEFAULT 0,
    status ENUM('active', 'pending', 'suspended', 'closed') DEFAULT 'pending',
    featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES user_tb(user_id) ON DELETE CASCADE
);

-- Business addresses and locations
CREATE TABLE business_addresses (
    address_id INT PRIMARY KEY AUTO_INCREMENT,
    business_id INT NOT NULL,
    street_address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE
);

-- Business operating hours
CREATE TABLE business_hours (
    hours_id INT PRIMARY KEY AUTO_INCREMENT,
    business_id INT NOT NULL,
    day_of_week ENUM('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday') NOT NULL,
    open_time TIME,
    close_time TIME,
    is_open BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE,
    UNIQUE KEY unique_business_day (business_id, day_of_week)
);

-- =====================================================
-- SERVICES AND RESOURCES
-- =====================================================

-- Categories for services
CREATE TABLE categories (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL,
    parent_category_id INT NULL,
    description TEXT,
    image_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_category_id) REFERENCES categories(category_id) ON DELETE SET NULL
);

-- Services offered by businesses
CREATE TABLE services (
    service_id INT PRIMARY KEY AUTO_INCREMENT,
    business_id INT NOT NULL,
    category_id INT,
    service_name VARCHAR(100) NOT NULL,
    description TEXT,
    duration_minutes INT NOT NULL DEFAULT 60,
    base_price DECIMAL(10, 2) NOT NULL,
    max_capacity INT DEFAULT 1,
    advance_booking_hours INT DEFAULT 24,
    cancellation_hours INT DEFAULT 24,
    image_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    requires_approval BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL
);

-- Service pricing tiers and variations
CREATE TABLE service_pricing (
    pricing_id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT NOT NULL,
    pricing_name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    duration_minutes INT,
    max_participants INT DEFAULT 1,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(service_id) ON DELETE CASCADE
);

-- Resources/Assets that can be booked (rooms, tables, equipment, etc.)
CREATE TABLE resources (
    resource_id INT PRIMARY KEY AUTO_INCREMENT,
    business_id INT NOT NULL,
    resource_name VARCHAR(100) NOT NULL,
    resource_type ENUM('room', 'table', 'equipment', 'vehicle', 'person', 'other') NOT NULL,
    capacity INT DEFAULT 1,
    description TEXT,
    hourly_rate DECIMAL(10, 2),
    daily_rate DECIMAL(10, 2),
    features JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE
);

-- =====================================================
-- AVAILABILITY AND SCHEDULING
-- =====================================================

-- Service availability templates
CREATE TABLE availability_templates (
    template_id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT,
    resource_id INT,
    day_of_week ENUM('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday') NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_duration INT DEFAULT 60,
    max_bookings INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(service_id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE,
    CHECK ((service_id IS NOT NULL AND resource_id IS NULL) OR (service_id IS NULL AND resource_id IS NOT NULL))
);

-- Specific availability slots
CREATE TABLE availability_slots (
    slot_id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT,
    resource_id INT,
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME NOT NULL,
    available_spots INT DEFAULT 1,
    booked_spots INT DEFAULT 0,
    price_override DECIMAL(10, 2),
    status ENUM('available', 'blocked', 'maintenance') DEFAULT 'available',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(service_id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE,
    CHECK ((service_id IS NOT NULL AND resource_id IS NULL) OR (service_id IS NULL AND resource_id IS NOT NULL))
);

-- Blocked dates/times
CREATE TABLE blocked_times (
    block_id INT PRIMARY KEY AUTO_INCREMENT,
    business_id INT,
    service_id INT,
    resource_id INT,
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME NOT NULL,
    reason VARCHAR(255),
    block_type ENUM('maintenance', 'holiday', 'private_event', 'other') DEFAULT 'other',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(service_id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES user_tb(user_id) ON DELETE CASCADE
);

-- =====================================================
-- BOOKING SYSTEM
-- =====================================================

-- Main bookings table
CREATE TABLE bookings (
    booking_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_reference VARCHAR(50) UNIQUE NOT NULL,
    user_id INT NOT NULL,
    business_id INT NOT NULL,
    service_id INT,
    resource_id INT,
    slot_id INT,
    booking_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME NOT NULL,
    participants INT DEFAULT 1,
    total_amount DECIMAL(10, 2) NOT NULL,
    deposit_amount DECIMAL(10, 2) DEFAULT 0.00,
    tax_amount DECIMAL(10, 2) DEFAULT 0.00,
    discount_amount DECIMAL(10, 2) DEFAULT 0.00,
    final_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status ENUM('pending', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show') DEFAULT 'pending',
    payment_status ENUM('pending', 'partial', 'paid', 'refunded', 'failed') DEFAULT 'pending',
    special_requests TEXT,
    internal_notes TEXT,
    confirmation_code VARCHAR(20),
    reminder_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    cancelled_at TIMESTAMP NULL,
    cancelled_by INT NULL,
    cancellation_reason TEXT,
    FOREIGN KEY (user_id) REFERENCES user_tb(user_id) ON DELETE CASCADE,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(service_id) ON DELETE SET NULL,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE SET NULL,
    FOREIGN KEY (slot_id) REFERENCES availability_slots(slot_id) ON DELETE SET NULL,
    FOREIGN KEY (cancelled_by) REFERENCES user_tb(user_id) ON DELETE SET NULL
);

-- Booking participants/guests
CREATE TABLE booking_participants (
    participant_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    age INT,
    special_requirements TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
);

-- Booking history/status changes
CREATE TABLE booking_history (
    history_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    changed_by INT NOT NULL,
    change_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES user_tb(user_id) ON DELETE CASCADE
);

-- =====================================================
-- PAYMENT SYSTEM
-- =====================================================

-- Payment methods
CREATE TABLE payment_methods (
    method_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    method_type ENUM('credit_card', 'debit_card', 'paypal', 'bank_transfer', 'cash', 'other') NOT NULL,
    card_last_four CHAR(4),
    card_brand VARCHAR(20),
    card_expiry_month INT,
    card_expiry_year INT,
    billing_address_id INT,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_tb(user_id) ON DELETE CASCADE,
    FOREIGN KEY (billing_address_id) REFERENCES user_addresses(address_id) ON DELETE SET NULL
);

-- Payment transactions
CREATE TABLE payments (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    payment_reference VARCHAR(100) UNIQUE NOT NULL,
    payment_method_id INT,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    payment_type ENUM('booking', 'deposit', 'balance', 'refund', 'penalty') DEFAULT 'booking',
    status ENUM('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded') DEFAULT 'pending',
    gateway VARCHAR(50),
    gateway_transaction_id VARCHAR(255),
    gateway_response JSON,
    processed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    FOREIGN KEY (payment_method_id) REFERENCES payment_methods(method_id) ON DELETE SET NULL
);

-- Refunds
CREATE TABLE refunds (
    refund_id INT PRIMARY KEY AUTO_INCREMENT,
    payment_id INT NOT NULL,
    refund_reference VARCHAR(100) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    reason TEXT,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    gateway_refund_id VARCHAR(255),
    processed_by INT,
    processed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id) ON DELETE CASCADE,
    FOREIGN KEY (processed_by) REFERENCES user_tb(user_id) ON DELETE SET NULL
);

-- =====================================================
-- REVIEWS AND RATINGS
-- =====================================================

-- Reviews
CREATE TABLE reviews (
    review_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    user_id INT NOT NULL,
    business_id INT NOT NULL,
    service_id INT,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    comment TEXT,
    pros TEXT,
    cons TEXT,
    would_recommend BOOLEAN,
    is_verified BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    status ENUM('pending', 'approved', 'rejected', 'hidden') DEFAULT 'pending',
    helpful_votes INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user_tb(user_id) ON DELETE CASCADE,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(service_id) ON DELETE SET NULL
);

-- Review responses from businesses
CREATE TABLE review_responses (
    response_id INT PRIMARY KEY AUTO_INCREMENT,
    review_id INT NOT NULL,
    business_id INT NOT NULL,
    response_text TEXT NOT NULL,
    responded_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (review_id) REFERENCES reviews(review_id) ON DELETE CASCADE,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE,
    FOREIGN KEY (responded_by) REFERENCES user_tb(user_id) ON DELETE CASCADE
);

-- =====================================================
-- PROMOTIONS AND DISCOUNTS
-- =====================================================

-- Discount codes and promotions
CREATE TABLE promotions (
    promotion_id INT PRIMARY KEY AUTO_INCREMENT,
    business_id INT,
    code VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    discount_type ENUM('percentage', 'fixed_amount', 'free_service') NOT NULL,
    discount_value DECIMAL(10, 2) NOT NULL,
    minimum_amount DECIMAL(10, 2) DEFAULT 0.00,
    maximum_discount DECIMAL(10, 2),
    usage_limit INT,
    usage_count INT DEFAULT 0,
    per_user_limit INT DEFAULT 1,
    valid_from DATETIME NOT NULL,
    valid_until DATETIME NOT NULL,
    applicable_services JSON,
    applicable_days JSON,
    status ENUM('active', 'inactive', 'expired') DEFAULT 'active',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES user_tb(user_id) ON DELETE CASCADE
);

-- Promotion usage tracking
CREATE TABLE promotion_usage (
    usage_id INT PRIMARY KEY AUTO_INCREMENT,
    promotion_id INT NOT NULL,
    user_id INT NOT NULL,
    booking_id INT NOT NULL,
    discount_amount DECIMAL(10, 2) NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (promotion_id) REFERENCES promotions(promotion_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user_tb(user_id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
);

-- =====================================================
-- NOTIFICATIONS AND COMMUNICATIONS
-- =====================================================

-- Notification templates
CREATE TABLE notification_templates (
    template_id INT PRIMARY KEY AUTO_INCREMENT,
    template_name VARCHAR(100) UNIQUE NOT NULL,
    template_type ENUM('email', 'sms', 'push', 'in_app') NOT NULL,
    subject VARCHAR(255),
    body_template TEXT NOT NULL,
    variables JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- User notifications
CREATE TABLE notifications (
    notification_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    type ENUM('booking_confirmation', 'booking_reminder', 'booking_cancelled', 'payment_received', 'review_request', 'promotion', 'system') NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSON,
    is_read BOOLEAN DEFAULT FALSE,
    is_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_tb(user_id) ON DELETE CASCADE
);

-- Email/SMS logs
CREATE TABLE communication_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    type ENUM('email', 'sms', 'push') NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(255),
    content TEXT,
    template_id INT,
    booking_id INT,
    status ENUM('pending', 'sent', 'delivered', 'failed', 'bounced') DEFAULT 'pending',
    provider VARCHAR(50),
    provider_response JSON,
    sent_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_tb(user_id) ON DELETE SET NULL,
    FOREIGN KEY (template_id) REFERENCES notification_templates(template_id) ON DELETE SET NULL,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE SET NULL
);

-- =====================================================
-- SYSTEM SETTINGS AND CONFIGURATION
-- =====================================================

-- System settings
CREATE TABLE system_settings (
    setting_id INT PRIMARY KEY AUTO_INCREMENT,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type ENUM('string', 'number', 'boolean', 'json') DEFAULT 'string',
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    updated_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES user_tb(user_id) ON DELETE SET NULL
);

-- Audit logs
CREATE TABLE audit_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(100),
    record_id INT,
    old_values JSON,
    new_values JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_tb(user_id) ON DELETE SET NULL
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- User table indexes
CREATE INDEX idx_user_email ON user_tb(email);
CREATE INDEX idx_user_username ON user_tb(username);
CREATE INDEX idx_user_status ON user_tb(status);
CREATE INDEX idx_user_created_at ON user_tb(created_at);

-- Business indexes
CREATE INDEX idx_business_owner ON businesses(owner_id);
CREATE INDEX idx_business_type ON businesses(business_type);
CREATE INDEX idx_business_status ON businesses(status);
CREATE INDEX idx_business_rating ON businesses(rating);

-- Service indexes
CREATE INDEX idx_service_business ON services(business_id);
CREATE INDEX idx_service_category ON services(category_id);
CREATE INDEX idx_service_active ON services(is_active);
CREATE INDEX idx_service_price ON services(base_price);

-- Booking indexes
CREATE INDEX idx_booking_user ON bookings(user_id);
CREATE INDEX idx_booking_business ON bookings(business_id);
CREATE INDEX idx_booking_service ON bookings(service_id);
CREATE INDEX idx_booking_date ON bookings(booking_date);
CREATE INDEX idx_booking_datetime ON bookings(start_datetime, end_datetime);
CREATE INDEX idx_booking_status ON bookings(status);
CREATE INDEX idx_booking_reference ON bookings(booking_reference);
CREATE INDEX idx_booking_created_at ON bookings(created_at);

-- Availability indexes
CREATE INDEX idx_availability_service ON availability_slots(service_id);
CREATE INDEX idx_availability_resource ON availability_slots(resource_id);
CREATE INDEX idx_availability_datetime ON availability_slots(start_datetime, end_datetime);
CREATE INDEX idx_availability_status ON availability_slots(status);

-- Payment indexes
CREATE INDEX idx_payment_booking ON payments(booking_id);
CREATE INDEX idx_payment_status ON payments(status);
CREATE INDEX idx_payment_created_at ON payments(created_at);
CREATE INDEX idx_payment_reference ON payments(payment_reference);

-- Review indexes
CREATE INDEX idx_review_business ON reviews(business_id);
CREATE INDEX idx_review_service ON reviews(service_id);
CREATE INDEX idx_review_user ON reviews(user_id);
CREATE INDEX idx_review_rating ON reviews(rating);
CREATE INDEX idx_review_status ON reviews(status);

-- Notification indexes
CREATE INDEX idx_notification_user ON notifications(user_id);
CREATE INDEX idx_notification_type ON notifications(type);
CREATE INDEX idx_notification_read ON notifications(is_read);
CREATE INDEX idx_notification_created_at ON notifications(created_at);

-- =====================================================
-- SAMPLE DATA INSERTION
-- =====================================================

-- Insert default roles
INSERT INTO roles (role_name, description) VALUES
('admin', 'System administrator with full access'),
('business_owner', 'Business owner who can manage their business'),
('staff', 'Staff member who can manage bookings'),
('customer', 'Regular customer who can make bookings');

-- Insert sample system settings
INSERT INTO system_settings (setting_key, setting_value, setting_type, description, is_public) VALUES
('site_name', 'BookingPro', 'string', 'Site name', TRUE),
('site_url', 'https://bookingpro.com', 'string', 'Site URL', TRUE),
('default_currency', 'USD', 'string', 'Default currency', TRUE),
('booking_confirmation_required', 'true', 'boolean', 'Whether bookings require confirmation', FALSE),
('default_cancellation_hours', '24', 'number', 'Default cancellation hours', TRUE),
('max_advance_booking_days', '365', 'number', 'Maximum days in advance for booking', TRUE),
('default_time_zone', 'UTC', 'string', 'Default time zone', TRUE),
('payment_gateway', 'stripe', 'string', 'Default payment gateway', FALSE),
('email_notifications_enabled', 'true', 'boolean', 'Enable email notifications', FALSE),
('sms_notifications_enabled', 'true', 'boolean', 'Enable SMS notifications', FALSE);

-- Insert sample categories
INSERT INTO categories (category_name, description) VALUES
('Hotels & Accommodation', 'Hotels, resorts, and accommodation services'),
('Restaurants & Dining', 'Restaurants, cafes, and dining experiences'),
('Health & Wellness', 'Spa, massage, and wellness services'),
('Events & Entertainment', 'Event venues and entertainment services'),
('Transportation & Travel', 'Car rentals, tours, and travel services'),
('Sports & Recreation', 'Sports facilities and recreational activities'),
('Beauty & Personal Care', 'Salons, barbershops, and personal care'),
('Professional Services', 'Consulting, legal, and professional services');

-- Insert notification templates
INSERT INTO notification_templates (template_name, template_type, subject, body_template, variables) VALUES
('booking_confirmation_email', 'email', 'Booking Confirmation - {{booking_reference}}', 
 'Dear {{customer_name}},\n\nYour booking has been confirmed!\n\nBooking Details:\nReference: {{booking_reference}}\nService: {{service_name}}\nDate: {{booking_date}}\nTime: {{booking_time}}\nLocation: {{business_name}}\n\nTotal Amount: {{total_amount}}\n\nThank you for choosing us!', 
 '["customer_name", "booking_reference", "service_name", "booking_date", "booking_time", "business_name", "total_amount"]'),
 
('booking_reminder_email', 'email', 'Booking Reminder - {{booking_reference}}', 
 'Dear {{customer_name}},\n\nThis is a reminder for your upcoming booking:\n\nService: {{service_name}}\nDate: {{booking_date}}\nTime: {{booking_time}}\nLocation: {{business_name}}\n\nSee you soon!', 
 '["customer_name", "booking_reference", "service_name", "booking_date", "booking_time", "business_name"]'),
 
('booking_cancelled_email', 'email', 'Booking Cancelled - {{booking_reference}}', 
 'Dear {{customer_name}},\n\nYour booking has been cancelled.\n\nBooking Reference: {{booking_reference}}\nReason: {{cancellation_reason}}\n\nIf you have any questions, please contact us.', 
 '["customer_name", "booking_reference", "cancellation_reason"]');

-- =====================================================
-- STORED PROCEDURES AND FUNCTIONS
-- =====================================================

DELIMITER //

-- Function to generate booking reference
CREATE FUNCTION generate_booking_reference() 
RETURNS VARCHAR(50) 
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE ref VARCHAR(50);
    DECLARE counter INT DEFAULT 0;
    
    REPEAT
        SET ref = CONCAT('BK', DATE_FORMAT(NOW(), '%Y%m%d'), LPAD(FLOOR(RAND() * 10000), 4, '0'));
        SELECT COUNT(*) INTO counter FROM bookings WHERE booking_reference = ref;
    UNTIL counter = 0 END REPEAT;
    
    RETURN ref;
END//

-- Procedure to create a booking
CREATE PROCEDURE create_booking(
    IN p_user_id INT,
    IN p_business_id INT,
    IN p_service_id INT,
    IN p_resource_id INT,
    IN p_start_datetime DATETIME,
    IN p_end_datetime DATETIME,
    IN p_participants INT,
    IN p_total_amount DECIMAL(10,2),
    IN p_special_requests TEXT
)
BEGIN
    DECLARE v_booking_id INT;
    DECLARE v_booking_ref VARCHAR(50);
    DECLARE v_final_amount DECIMAL(10,2);
    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    SET v_booking_ref = generate_booking_reference();
    SET v_final_amount = p_total_amount;
    
    INSERT INTO bookings (
        booking_reference, user_id, business_id, service_id, resource_id,
        booking_date, start_time, end_time, start_datetime, end_datetime,
        participants, total_amount, final_amount, special_requests,
        confirmation_code
    ) VALUES (
        v_booking_ref, p_user_id, p_business_id, p_service_id, p_resource_id,
        DATE(p_start_datetime), TIME(p_start_datetime), TIME(p_end_datetime),
        p_start_datetime, p_end_datetime, p_participants, p_total_amount,
        v_final_amount, p_special_requests, UPPER(SUBSTRING(MD5(RAND()), 1, 8))
    );
    
    SET v_booking_id = LAST_INSERT_ID();
    
    -- Log booking creation
    INSERT INTO booking_history (booking_id, new_status, changed_by, change_reason)
    VALUES (v_booking_id, 'pending', p_user_id, 'Booking created');
    
    -- Update availability if slot-based booking
    IF p_service_id IS NOT NULL THEN
        UPDATE availability_slots 
        SET booked_spots = booked_spots + p_participants
        WHERE service_id = p_service_id 
        AND start_datetime = p_start_datetime 
        AND end_datetime = p_end_datetime;
    END IF;
    
    COMMIT;
    
    SELECT v_booking_id as booking_id, v_booking_ref as booking_reference;
END//

-- Procedure to cancel booking
CREATE PROCEDURE cancel_booking(
    IN p_booking_id INT,
    IN p_cancelled_by INT,
    IN p_reason TEXT
)
BEGIN
    DECLARE v_service_id INT;
    DECLARE v_start_datetime DATETIME;
    DECLARE v_end_datetime DATETIME;
    DECLARE v_participants INT;
    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    -- Get booking details
    SELECT service_id, start_datetime, end_datetime, participants
    INTO v_service_id, v_start_datetime, v_end_datetime, v_participants
    FROM bookings WHERE booking_id = p_booking_id;
    
    -- Update booking status
    UPDATE bookings 
    SET status = 'cancelled', 
        cancelled_at = NOW(), 
        cancelled_by = p_cancelled_by,
        cancellation_reason = p_reason
    WHERE booking_id = p_booking_id;
    
    -- Log status change
    INSERT INTO booking_history (booking_id, old_status, new_status, changed_by, change_reason)
    VALUES (p_booking_id, 'confirmed', 'cancelled', p_cancelled_by, p_reason);
    
    -- Free up availability
    IF v_service_id IS NOT NULL THEN
        UPDATE availability_slots 
        SET booked_spots = booked_spots - v_participants
        WHERE service_id = v_service_id 
        AND start_datetime = v_start_datetime 
        AND end_datetime = v_end_datetime;
    END IF;
    
    COMMIT;
END//

-- Function to calculate business rating
CREATE FUNCTION calculate_business_rating(p_business_id INT) 
RETURNS DECIMAL(3,2) 
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE avg_rating DECIMAL(3,2) DEFAULT 0.00;
    
    SELECT COALESCE(AVG(rating), 0.00) 
    INTO avg_rating 
    FROM reviews 
    WHERE business_id = p_business_id AND status = 'approved';
    
    RETURN avg_rating;
END//

-- Procedure to update business rating
CREATE PROCEDURE update_business_rating(IN p_business_id INT)
BEGIN
    DECLARE v_rating DECIMAL(3,2);
    DECLARE v_count INT;
    
    SELECT COALESCE(AVG(rating), 0.00), COUNT(*)
    INTO v_rating, v_count
    FROM reviews 
    WHERE business_id = p_business_id AND status = 'approved';
    
    UPDATE businesses 
    SET rating = v_rating, total_reviews = v_count
    WHERE business_id = p_business_id;
END//

-- Function to check availability
CREATE FUNCTION check_availability(
    p_service_id INT,
    p_resource_id INT,
    p_start_datetime DATETIME,
    p_end_datetime DATETIME,
    p_participants INT
) 
RETURNS BOOLEAN 
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE available_spots INT DEFAULT 0;
    DECLARE blocked_count INT DEFAULT 0;
    DECLARE booking_conflicts INT DEFAULT 0;
    
    -- Check for blocked times
    SELECT COUNT(*) INTO blocked_count
    FROM blocked_times 
    WHERE (service_id = p_service_id OR resource_id = p_resource_id)
    AND (p_start_datetime < end_datetime AND p_end_datetime > start_datetime);
    
    IF blocked_count > 0 THEN
        RETURN FALSE;
    END IF;
    
    -- Check availability slots
    IF p_service_id IS NOT NULL THEN
        SELECT (available_spots - booked_spots) INTO available_spots
        FROM availability_slots
        WHERE service_id = p_service_id
        AND start_datetime = p_start_datetime
        AND end_datetime = p_end_datetime
        AND status = 'available';
        
        IF available_spots >= p_participants THEN
            RETURN TRUE;
        ELSE
            RETURN FALSE;
        END IF;
    END IF;
    
    -- Check for booking conflicts
    SELECT COUNT(*) INTO booking_conflicts
    FROM bookings
    WHERE (service_id = p_service_id OR resource_id = p_resource_id)
    AND status IN ('pending', 'confirmed')
    AND (p_start_datetime < end_datetime AND p_end_datetime > start_datetime);
    
    RETURN booking_conflicts = 0;
END//

DELIMITER ;

-- =====================================================
-- TRIGGERS
-- =====================================================

DELIMITER //

-- Trigger to update business rating after review insert
CREATE TRIGGER after_review_insert
AFTER INSERT ON reviews
FOR EACH ROW
BEGIN
    IF NEW.status = 'approved' THEN
        CALL update_business_rating(NEW.business_id);
    END IF;
END//

-- Trigger to update business rating after review update
CREATE TRIGGER after_review_update
AFTER UPDATE ON reviews
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status OR OLD.rating != NEW.rating THEN
        CALL update_business_rating(NEW.business_id);
    END IF;
END//

-- Trigger to log booking status changes
CREATE TRIGGER after_booking_status_update
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO booking_history (booking_id, old_status, new_status, changed_by, change_reason)
        VALUES (NEW.booking_id, OLD.status, NEW.status, NEW.user_id, 'Status updated');
    END IF;
END//

-- Trigger to update payment status based on booking status
CREATE TRIGGER after_booking_completion
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        UPDATE payments 
        SET status = 'completed' 
        WHERE booking_id = NEW.booking_id AND status = 'pending';
    END IF;
END//

DELIMITER ;

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- View for booking details with related information
CREATE VIEW booking_details AS
SELECT 
    b.booking_id,
    b.booking_reference,
    b.booking_date,
    b.start_time,
    b.end_time,
    b.participants,
    b.total_amount,
    b.final_amount,
    b.status,
    b.payment_status,
    b.created_at,
    u.first_name as customer_first_name,
    u.last_name as customer_last_name,
    u.email as customer_email,
    u.phone as customer_phone,
    bus.business_name,
    bus.phone as business_phone,
    bus.email as business_email,
    s.service_name,
    s.duration_minutes,
    r.resource_name,
    c.category_name
FROM bookings b
JOIN user_tb u ON b.user_id = u.user_id
JOIN businesses bus ON b.business_id = bus.business_id
LEFT JOIN services s ON b.service_id = s.service_id
LEFT JOIN resources r ON b.resource_id = r.resource_id
LEFT JOIN categories c ON s.category_id = c.category_id;

-- View for business dashboard
CREATE VIEW business_dashboard AS
SELECT 
    b.business_id,
    b.business_name,
    b.rating,
    b.total_reviews,
    COUNT(DISTINCT bk.booking_id) as total_bookings,
    COUNT(DISTINCT CASE WHEN bk.status = 'completed' THEN bk.booking_id END) as completed_bookings,
    COUNT(DISTINCT CASE WHEN bk.status = 'pending' THEN bk.booking_id END) as pending_bookings,
    COUNT(DISTINCT CASE WHEN bk.status = 'cancelled' THEN bk.booking_id END) as cancelled_bookings,
    COALESCE(SUM(CASE WHEN bk.status = 'completed' THEN bk.final_amount END), 0) as total_revenue,
    COUNT(DISTINCT s.service_id) as total_services,
    COUNT(DISTINCT r.resource_id) as total_resources
FROM businesses b
LEFT JOIN bookings bk ON b.business_id = bk.business_id
LEFT JOIN services s ON b.business_id = s.business_id AND s.is_active = 1
LEFT JOIN resources r ON b.business_id = r.business_id AND r.is_active = 1
GROUP BY b.business_id, b.business_name, b.rating, b.total_reviews;

-- View for user booking history
CREATE VIEW user_booking_history AS
SELECT 
    b.booking_id,
    b.booking_reference,
    b.booking_date,
    b.start_time,
    b.end_time,
    b.status,
    b.final_amount,
    b.created_at,
    bus.business_name,
    s.service_name,
    CASE 
        WHEN b.booking_date > CURDATE() THEN 'upcoming'
        WHEN b.booking_date = CURDATE() THEN 'today'
        ELSE 'past'
    END as booking_period
FROM bookings b
JOIN businesses bus ON b.business_id = bus.business_id
LEFT JOIN services s ON b.service_id = s.service_id;

-- View for service availability
CREATE VIEW service_availability AS
SELECT 
    s.service_id,
    s.service_name,
    b.business_name,
    avs.start_datetime,
    avs.end_datetime,
    (avs.available_spots - avs.booked_spots) as available_spots,
    avs.price_override,
    COALESCE(avs.price_override, s.base_price) as current_price
FROM services s
JOIN businesses b ON s.business_id = b.business_id
JOIN availability_slots avs ON s.service_id = avs.service_id
WHERE s.is_active = 1 
AND b.status = 'active'
AND avs.status = 'available'
AND avs.start_datetime > NOW()
AND (avs.available_spots - avs.booked_spots) > 0;

-- View for popular services
CREATE VIEW popular_services AS
SELECT 
    s.service_id,
    s.service_name,
    b.business_name,
    b.business_id,
    c.category_name,
    s.base_price,
    COUNT(bk.booking_id) as total_bookings,
    AVG(r.rating) as average_rating,
    COUNT(r.review_id) as total_reviews
FROM services s
JOIN businesses b ON s.business_id = b.business_id
LEFT JOIN bookings bk ON s.service_id = bk.service_id
LEFT JOIN reviews r ON s.service_id = r.service_id AND r.status = 'approved'
LEFT JOIN categories c ON s.category_id = c.category_id
WHERE s.is_active = 1 AND b.status = 'active'
GROUP BY s.service_id, s.service_name, b.business_name, b.business_id, c.category_name, s.base_price
ORDER BY total_bookings DESC, average_rating DESC;

-- =====================================================
-- SAMPLE DATA INSERTION (EXTENDED)
-- =====================================================

-- Insert sample users
INSERT INTO user_tb (username, email, password_hash, first_name, last_name, phone, status) VALUES
('admin', 'admin@bookingpro.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'System', 'Admin', '+1234567890', 'active'),
('john_doe', 'john@example.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'John', 'Doe', '+1234567891', 'active'),
('jane_smith', 'jane@example.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'Jane', 'Smith', '+1234567892', 'active'),
('hotel_owner', 'hotel@example.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'Hotel', 'Owner', '+1234567893', 'active'),
('spa_owner', 'spa@example.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'Spa', 'Owner', '+1234567894', 'active');

-- Assign roles to users
INSERT INTO user_roles (user_id, role_id) VALUES
(1, 1), -- admin role
(2, 4), -- customer role
(3, 4), -- customer role
(4, 2), -- business_owner role
(5, 2); -- business_owner role

-- Insert sample businesses
INSERT INTO businesses (owner_id, business_name, business_type, description, phone, email, status, rating, total_reviews) VALUES
(4, 'Grand Plaza Hotel', 'hotel', 'Luxury hotel in the heart of the city with modern amenities and exceptional service.', '+1234567800', 'info@grandplaza.com', 'active', 4.5, 150),
(5, 'Serenity Spa & Wellness', 'spa', 'Full-service spa offering massage, facial, and wellness treatments.', '+1234567801', 'info@serenityspa.com', 'active', 4.8, 89),
(4, 'Bella Vista Restaurant', 'restaurant', 'Fine dining restaurant serving contemporary cuisine with a beautiful city view.', '+1234567802', 'reservations@bellavista.com', 'active', 4.3, 78),
(5, 'Elite Conference Center', 'event_venue', 'Modern conference center with state-of-the-art facilities for corporate events.', '+1234567803', 'events@elitecc.com', 'active', 4.6, 45);

-- Insert business addresses
INSERT INTO business_addresses (business_id, street_address, city, state, postal_code, country, latitude, longitude, is_primary) VALUES
(1, '123 Main Street', 'New York', 'NY', '10001', 'USA', 40.7589, -73.9851, TRUE),
(2, '456 Wellness Ave', 'Los Angeles', 'CA', '90210', 'USA', 34.0522, -118.2437, TRUE),
(3, '789 Gourmet Blvd', 'Chicago', 'IL', '60601', 'USA', 41.8781, -87.6298, TRUE),
(4, '321 Business Park', 'San Francisco', 'CA', '94102', 'USA', 37.7749, -122.4194, TRUE);

-- Insert business hours
INSERT INTO business_hours (business_id, day_of_week, open_time, close_time, is_open) VALUES
-- Grand Plaza Hotel (24/7)
(1, 'monday', '00:00:00', '23:59:59', TRUE),
(1, 'tuesday', '00:00:00', '23:59:59', TRUE),
(1, 'wednesday', '00:00:00', '23:59:59', TRUE),
(1, 'thursday', '00:00:00', '23:59:59', TRUE),
(1, 'friday', '00:00:00', '23:59:59', TRUE),
(1, 'saturday', '00:00:00', '23:59:59', TRUE),
(1, 'sunday', '00:00:00', '23:59:59', TRUE),
-- Serenity Spa (9 AM - 8 PM)
(2, 'monday', '09:00:00', '20:00:00', TRUE),
(2, 'tuesday', '09:00:00', '20:00:00', TRUE),
(2, 'wednesday', '09:00:00', '20:00:00', TRUE),
(2, 'thursday', '09:00:00', '20:00:00', TRUE),
(2, 'friday', '09:00:00', '20:00:00', TRUE),
(2, 'saturday', '08:00:00', '21:00:00', TRUE),
(2, 'sunday', '10:00:00', '18:00:00', TRUE);

-- Insert services
INSERT INTO services (business_id, category_id, service_name, description, duration_minutes, base_price, max_capacity, advance_booking_hours, cancellation_hours, is_active) VALUES
(1, 1, 'Deluxe Room', 'Spacious deluxe room with city view, king bed, and modern amenities', 1440, 299.00, 2, 24, 24, TRUE),
(1, 1, 'Presidential Suite', 'Luxury presidential suite with separate living area and premium services', 1440, 899.00, 4, 48, 48, TRUE),
(2, 3, 'Swedish Massage', 'Relaxing full-body Swedish massage therapy', 60, 120.00, 1, 12, 4, TRUE),
(2, 3, 'Deep Tissue Massage', 'Therapeutic deep tissue massage for muscle tension relief', 90, 180.00, 1, 12, 4, TRUE),
(2, 3, 'Couples Massage', 'Romantic couples massage in private suite', 60, 240.00, 2, 24, 12, TRUE),
(3, 2, 'Dinner Reservation', 'Fine dining experience with contemporary cuisine', 120, 0.00, 8, 4, 2, TRUE),
(4, 4, 'Conference Room A', 'Small conference room for up to 20 people', 480, 500.00, 20, 48, 24, TRUE),
(4, 4, 'Grand Ballroom', 'Large ballroom for events up to 300 people', 480, 2000.00, 300, 168, 48, TRUE);

-- Insert resources
INSERT INTO resources (business_id, resource_name, resource_type, capacity, description, hourly_rate, daily_rate, is_active) VALUES
(1, 'Room 101', 'room', 2, 'Standard room with queen bed', 25.00, 199.00, TRUE),
(1, 'Room 201', 'room', 2, 'Deluxe room with king bed', 35.00, 299.00, TRUE),
(1, 'Presidential Suite', 'room', 4, 'Luxury suite with living area', 100.00, 899.00, TRUE),
(2, 'Massage Room 1', 'room', 1, 'Private massage room', 60.00, NULL, TRUE),
(2, 'Massage Room 2', 'room', 1, 'Private massage room', 60.00, NULL, TRUE),
(2, 'Couples Suite', 'room', 2, 'Private couples massage suite', 120.00, NULL, TRUE),
(3, 'Table 1', 'table', 4, 'Window table for 4 guests', NULL, NULL, TRUE),
(3, 'Table 2', 'table', 6, 'Round table for 6 guests', NULL, NULL, TRUE),
(4, 'Projector System', 'equipment', 1, 'HD projector with sound system', 50.00, NULL, TRUE);

-- Insert availability slots for next 30 days
INSERT INTO availability_slots (service_id, start_datetime, end_datetime, available_spots, status) VALUES
-- Swedish Massage slots for next week
(3, '2025-06-04 09:00:00', '2025-06-04 10:00:00', 1, 'available'),
(3, '2025-06-04 10:30:00', '2025-06-04 11:30:00', 1, 'available'),
(3, '2025-06-04 14:00:00', '2025-06-04 15:00:00', 1, 'available'),
(3, '2025-06-04 15:30:00', '2025-06-04 16:30:00', 1, 'available'),
(3, '2025-06-05 09:00:00', '2025-06-05 10:00:00', 1, 'available'),
(3, '2025-06-05 10:30:00', '2025-06-05 11:30:00', 1, 'available'),
-- Deep Tissue Massage slots
(4, '2025-06-04 11:00:00', '2025-06-04 12:30:00', 1, 'available'),
(4, '2025-06-04 13:00:00', '2025-06-04 14:30:00', 1, 'available'),
(4, '2025-06-05 11:00:00', '2025-06-05 12:30:00', 1, 'available'),
-- Conference Room slots
(7, '2025-06-04 09:00:00', '2025-06-04 17:00:00', 1, 'available'),
(7, '2025-06-05 09:00:00', '2025-06-05 17:00:00', 1, 'available'),
(7, '2025-06-06 09:00:00', '2025-06-06 17:00:00', 1, 'available');

-- Insert sample bookings
INSERT INTO bookings (booking_reference, user_id, business_id, service_id, booking_date, start_time, end_time, start_datetime, end_datetime, participants, total_amount, final_amount, status, payment_status, confirmation_code) VALUES
('BK20250604001', 2, 2, 3, '2025-06-05', '10:30:00', '11:30:00', '2025-06-05 10:30:00', '2025-06-05 11:30:00', 1, 120.00, 120.00, 'confirmed', 'paid', 'A1B2C3D4'),
('BK20250604002', 3, 1, 1, '2025-06-06', '15:00:00', '11:00:00', '2025-06-06 15:00:00', '2025-06-07 11:00:00', 2, 299.00, 299.00, 'confirmed', 'paid', 'E5F6G7H8'),
('BK20250604003', 2, 4, 7, '2025-06-07', '09:00:00', '17:00:00', '2025-06-07 09:00:00', '2025-06-07 17:00:00', 15, 500.00, 500.00, 'pending', 'pending', 'I9J0K1L2');

-- Insert sample payments
INSERT INTO payments (booking_id, payment_reference, amount, payment_type, status, gateway, processed_at) VALUES
(1, 'PAY20250604001', 120.00, 'booking', 'completed', 'stripe', '2025-06-04 08:30:00'),
(2, 'PAY20250604002', 299.00, 'booking', 'completed', 'paypal', '2025-06-04 09:15:00');

-- Insert sample reviews
INSERT INTO reviews (booking_id, user_id, business_id, service_id, rating, title, comment, would_recommend, status, created_at) VALUES
(1, 2, 2, 3, 5, 'Amazing massage experience!', 'The Swedish massage was incredibly relaxing. The therapist was professional and the atmosphere was perfect. Highly recommend!', TRUE, 'approved', '2025-06-05 12:00:00'),
(2, 3, 1, 1, 4, 'Great hotel stay', 'Beautiful room with excellent amenities. Staff was friendly and helpful. Only minor issue was the wifi speed.', TRUE, 'approved', '2025-06-07 12:30:00');

-- Insert sample promotions
INSERT INTO promotions (business_id, code, title, description, discount_type, discount_value, minimum_amount, usage_limit, valid_from, valid_until, status, created_by) VALUES
(2, 'SPA20', 'New Customer Spa Discount', '20% off for first-time spa customers', 'percentage', 20.00, 100.00, 100, '2025-06-01 00:00:00', '2025-12-31 23:59:59', 'active', 5),
(1, 'SUMMER25', 'Summer Hotel Special', '$25 off hotel bookings over $200', 'fixed_amount', 25.00, 200.00, 50, '2025-06-01 00:00:00', '2025-08-31 23:59:59', 'active', 4),
(4, 'CORP15', 'Corporate Event Discount', '15% off conference room bookings', 'percentage', 15.00, 300.00, 25, '2025-06-01 00:00:00', '2025-12-31 23:59:59', 'active', 5);

-- =====================================================
-- FINAL NOTES AND USAGE EXAMPLES
-- =====================================================

/*
USAGE EXAMPLES:

1. Create a new booking:
CALL create_booking(2, 2, 3, NULL, '2025-06-10 14:00:00', '2025-06-10 15:00:00', 1, 120.00, 'Please use essential oils');

2. Cancel a booking:
CALL cancel_booking(1, 2, 'Customer requested cancellation');

3. Check availability:
SELECT check_availability(3, NULL, '2025-06-10 14:00:00', '2025-06-10 15:00:00', 1);

4. Get business dashboard data:
SELECT * FROM business_dashboard WHERE business_id = 2;

5. Get user booking history:
SELECT * FROM user_booking_history WHERE booking_id IN (SELECT booking_id FROM bookings WHERE user_id = 2);

6. Find available services:
SELECT * FROM service_availability WHERE start_datetime >= '2025-06-10 00:00:00' AND start_datetime <= '2025-06-10 23:59:59';

7. Get popular services:
SELECT * FROM popular_services LIMIT 10;

8. Update business rating after new review:
CALL update_business_rating(2);

SECURITY CONSIDERATIONS:
- All passwords should be hashed using bcrypt or similar
- Implement proper input validation and sanitization
- Use prepared statements to prevent SQL injection
- Add rate limiting for booking creation
- Implement proper authentication and authorization
- Add audit logging for sensitive operations
- Use SSL/TLS for all connections
- Regularly backup the database

PERFORMANCE OPTIMIZATION:
- Indexes are already created for common queries
- Consider partitioning large tables by date
- Monitor and optimize slow queries
- Implement caching for frequently accessed data
- Use connection pooling
- Regular database maintenance and optimization

BACKUP STRATEGY:
- Daily full backups
- Transaction log backups every 15 minutes
- Test restore procedures regularly
- Store backups in multiple locations
- Document recovery procedures
*/