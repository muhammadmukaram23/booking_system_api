from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from main import get_db
from models.models import User, UserAddress, Role, UserRole
from schemas.user_schemas import (
    UserCreate, UserUpdate, UserResponse, UserPasswordUpdate,
    AddressCreate, AddressUpdate, AddressResponse,
    RoleCreate, RoleUpdate, RoleResponse, UserRoleCreate, UserRoleResponse
)
from auth.auth import get_password_hash, verify_password

router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)

# User endpoints
@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if username or email already exists
    db_user_username = db.query(User).filter(User.username == user.username).first()
    if db_user_username:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user_email = db.query(User).filter(User.email == user.email).first()
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        date_of_birth=user.date_of_birth,
        gender=user.gender,
        profile_image=user.profile_image
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Assign default customer role
    customer_role = db.query(Role).filter(Role.role_name == "customer").first()
    if customer_role:
        user_role = UserRole(user_id=db_user.user_id, role_id=customer_role.role_id)
        db.add(user_role)
        db.commit()
    
    return db_user

@router.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Update last login time
    user.last_login = datetime.now()
    db.commit()
    
    return {
        "message": "Login successful",
        "user": UserResponse.from_orm(user)
    }

# User profile endpoints
@router.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """Get user information by ID"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Update user information"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    for key, value in user_update.dict(exclude_unset=True).items():
        setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user

@router.put("/users/{user_id}/password")
def update_password(user_id: int, password_update: UserPasswordUpdate, db: Session = Depends(get_db)):
    """Update user password"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(password_update.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    user.password_hash = get_password_hash(password_update.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}

# User address endpoints
@router.post("/users/{user_id}/addresses", response_model=AddressResponse)
def create_address(user_id: int, address: AddressCreate, db: Session = Depends(get_db)):
    """Create a new address for user"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_address = UserAddress(
        user_id=user_id,
        **address.dict()
    )
    
    # If this is the first address or set as default, make it the default
    existing_addresses = db.query(UserAddress).filter(UserAddress.user_id == user_id).all()
    if address.is_default or len(existing_addresses) == 0:
        # Reset all other addresses to non-default
        for addr in existing_addresses:
            addr.is_default = False
        db_address.is_default = True
    
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

@router.get("/users/{user_id}/addresses", response_model=List[AddressResponse])
def read_addresses(user_id: int, db: Session = Depends(get_db)):
    """Get all addresses for user"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    addresses = db.query(UserAddress).filter(UserAddress.user_id == user_id).all()
    return addresses

@router.get("/users/{user_id}/addresses/{address_id}", response_model=AddressResponse)
def read_address(user_id: int, address_id: int, db: Session = Depends(get_db)):
    """Get a specific address for user"""
    db_address = db.query(UserAddress).filter(
        UserAddress.address_id == address_id,
        UserAddress.user_id == user_id
    ).first()
    
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    
    return db_address

@router.put("/users/{user_id}/addresses/{address_id}", response_model=AddressResponse)
def update_address(user_id: int, address_id: int, address_update: AddressUpdate, db: Session = Depends(get_db)):
    """Update a specific address for user"""
    db_address = db.query(UserAddress).filter(
        UserAddress.address_id == address_id,
        UserAddress.user_id == user_id
    ).first()
    
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    
    update_data = address_update.dict(exclude_unset=True)
    
    # Handle setting as default address
    if "is_default" in update_data and update_data["is_default"]:
        # Reset all other addresses to non-default
        other_addresses = db.query(UserAddress).filter(
            UserAddress.user_id == user_id,
            UserAddress.address_id != address_id
        ).all()
        for addr in other_addresses:
            addr.is_default = False
    
    for key, value in update_data.items():
        setattr(db_address, key, value)
    
    db.commit()
    db.refresh(db_address)
    return db_address

@router.delete("/users/{user_id}/addresses/{address_id}")
def delete_address(user_id: int, address_id: int, db: Session = Depends(get_db)):
    """Delete a specific address for user"""
    db_address = db.query(UserAddress).filter(
        UserAddress.address_id == address_id,
        UserAddress.user_id == user_id
    ).first()
    
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    
    was_default = db_address.is_default
    
    db.delete(db_address)
    db.commit()
    
    # If the deleted address was the default, set a new default if possible
    if was_default:
        new_default = db.query(UserAddress).filter(UserAddress.user_id == user_id).first()
        if new_default:
            new_default.is_default = True
            db.commit()
    
    return {"message": "Address deleted successfully"}

# Admin endpoints - no authentication check
@router.get("/users", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all users"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

# Role management endpoints - no authentication check
@router.post("/roles", response_model=RoleResponse)
def create_role(role: RoleCreate, db: Session = Depends(get_db)):
    """Create a new role"""
    db_role = Role(**role.dict())
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    
    return db_role

@router.get("/roles", response_model=List[RoleResponse])
def read_roles(db: Session = Depends(get_db)):
    """Get all roles"""
    roles = db.query(Role).all()
    return roles

@router.put("/roles/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, role_update: RoleUpdate, db: Session = Depends(get_db)):
    """Update a role"""
    db_role = db.query(Role).filter(Role.role_id == role_id).first()
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    
    for key, value in role_update.dict(exclude_unset=True).items():
        setattr(db_role, key, value)
    
    db.commit()
    db.refresh(db_role)
    
    return db_role

@router.post("/user-roles", response_model=UserRoleResponse)
def assign_role_to_user(user_role: UserRoleCreate, db: Session = Depends(get_db)):
    """Assign a role to a user"""
    # Check if user exists
    user = db.query(User).filter(User.user_id == user_role.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if role exists
    role = db.query(Role).filter(Role.role_id == user_role.role_id).first()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if user already has this role
    existing_role = db.query(UserRole).filter(
        UserRole.user_id == user_role.user_id,
        UserRole.role_id == user_role.role_id
    ).first()
    
    if existing_role:
        raise HTTPException(status_code=400, detail="User already has this role")
    
    db_user_role = UserRole(**user_role.dict())
    db.add(db_user_role)
    db.commit()
    db.refresh(db_user_role)
    
    return db_user_role

@router.delete("/user-roles/{user_id}/{role_id}")
def remove_role_from_user(user_id: int, role_id: int, db: Session = Depends(get_db)):
    """Remove a role from a user"""
    # Check if user role exists
    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id
    ).first()
    
    if user_role is None:
        raise HTTPException(status_code=404, detail="User does not have this role")
    
    db.delete(user_role)
    db.commit()
    
    return {"message": "Role removed from user successfully"} 