from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta

from main import get_db
from models.models import User, UserAddress, Role, UserRole
from schemas.user_schemas import (
    UserCreate, UserUpdate, UserResponse, UserPasswordUpdate,
    AddressCreate, AddressUpdate, AddressResponse,
    RoleCreate, RoleUpdate, RoleResponse, UserRoleCreate, UserRoleResponse,
    Token
)
from auth.auth import (
    authenticate_user, create_access_token, get_password_hash,
    get_current_user, get_current_active_user, check_admin_permission,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)

# Authentication endpoints
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

@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Get access token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.user_id)}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

# User endpoints
@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user information"""
    for key, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, key, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/me/password")
def update_password(
    password_update: UserPasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user password"""
    if not authenticate_user(db, current_user.username, password_update.current_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    current_user.password_hash = get_password_hash(password_update.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}

# User address endpoints
@router.post("/me/addresses", response_model=AddressResponse)
def create_address(
    address: AddressCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new address for current user"""
    db_address = UserAddress(
        user_id=current_user.user_id,
        **address.dict()
    )
    
    # If this is the first address or set as default, make it the default
    if address.is_default or len(current_user.addresses) == 0:
        # Reset all other addresses to non-default
        for addr in current_user.addresses:
            addr.is_default = False
        db_address.is_default = True
    
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

@router.get("/me/addresses", response_model=List[AddressResponse])
def read_addresses(current_user: User = Depends(get_current_active_user)):
    """Get all addresses for current user"""
    return current_user.addresses

@router.get("/me/addresses/{address_id}", response_model=AddressResponse)
def read_address(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific address for current user"""
    db_address = db.query(UserAddress).filter(
        UserAddress.address_id == address_id,
        UserAddress.user_id == current_user.user_id
    ).first()
    
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    
    return db_address

@router.put("/me/addresses/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: int,
    address_update: AddressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a specific address for current user"""
    db_address = db.query(UserAddress).filter(
        UserAddress.address_id == address_id,
        UserAddress.user_id == current_user.user_id
    ).first()
    
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    
    update_data = address_update.dict(exclude_unset=True)
    
    # Handle setting as default address
    if "is_default" in update_data and update_data["is_default"]:
        # Reset all other addresses to non-default
        for addr in current_user.addresses:
            addr.is_default = False
    
    for key, value in update_data.items():
        setattr(db_address, key, value)
    
    db.commit()
    db.refresh(db_address)
    return db_address

@router.delete("/me/addresses/{address_id}")
def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a specific address for current user"""
    db_address = db.query(UserAddress).filter(
        UserAddress.address_id == address_id,
        UserAddress.user_id == current_user.user_id
    ).first()
    
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    
    was_default = db_address.is_default
    
    db.delete(db_address)
    db.commit()
    
    # If deleted address was default and there are other addresses, set a new default
    if was_default:
        remaining_address = db.query(UserAddress).filter(
            UserAddress.user_id == current_user.user_id
        ).first()
        
        if remaining_address:
            remaining_address.is_default = True
            db.commit()
    
    return {"message": "Address deleted successfully"}

# Admin endpoints for user management
@router.get("/", response_model=List[UserResponse])
def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: int,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """Get a specific user (admin only)"""
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/{user_id}", response_model=UserResponse)
def update_user_admin(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """Update a specific user (admin only)"""
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    for key, value in user_update.dict(exclude_unset=True).items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

# Role management endpoints (admin only)
@router.post("/roles", response_model=RoleResponse)
def create_role(
    role: RoleCreate,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """Create a new role (admin only)"""
    db_role = Role(**role.dict())
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

@router.get("/roles", response_model=List[RoleResponse])
def read_roles(
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """Get all roles (admin only)"""
    roles = db.query(Role).all()
    return roles

@router.put("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    role_update: RoleUpdate,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """Update a role (admin only)"""
    db_role = db.query(Role).filter(Role.role_id == role_id).first()
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    
    for key, value in role_update.dict(exclude_unset=True).items():
        setattr(db_role, key, value)
    
    db.commit()
    db.refresh(db_role)
    return db_role

@router.post("/user-roles", response_model=UserRoleResponse)
def assign_role_to_user(
    user_role: UserRoleCreate,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """Assign a role to a user (admin only)"""
    # Check if user and role exist
    db_user = db.query(User).filter(User.user_id == user_role.user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_role = db.query(Role).filter(Role.role_id == user_role.role_id).first()
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if assignment already exists
    existing = db.query(UserRole).filter(
        UserRole.user_id == user_role.user_id,
        UserRole.role_id == user_role.role_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User already has this role")
    
    db_user_role = UserRole(**user_role.dict())
    db.add(db_user_role)
    db.commit()
    db.refresh(db_user_role)
    return db_user_role

@router.delete("/user-roles/{user_id}/{role_id}")
def remove_role_from_user(
    user_id: int,
    role_id: int,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """Remove a role from a user (admin only)"""
    db_user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id
    ).first()
    
    if db_user_role is None:
        raise HTTPException(status_code=404, detail="User role assignment not found")
    
    db.delete(db_user_role)
    db.commit()
    
    return {"message": "Role removed from user successfully"} 