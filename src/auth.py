from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
import uuid
from .config import settings
from .database import firebase_manager
from .models import UserData, UserRole

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()

class AuthManager:
    def __init__(self):
        self.pwd_context = pwd_context
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except JWTError:
            return None
    
    def generate_verification_token(self) -> str:
        """Generate a random verification token"""
        return secrets.token_urlsafe(32)
    
    async def authenticate_user(self, email: str, password: str) -> Optional[UserData]:
        """Authenticate a user with email and password"""
        user = await firebase_manager.get_user_by_email(email)
        if not user:
            return None
        
        if not self.verify_password(password, user.password_hash):
            return None
        
        # Update last login
        await firebase_manager.update_user(user.uid, {
            'last_login': datetime.utcnow()
        })
        
        return user
    
    async def register_user(self, email: str, password: str, full_name: str, language: str = "tr") -> Optional[UserData]:
        """Register a new user"""
        # Check if user already exists
        existing_user = await firebase_manager.get_user_by_email(email)
        if existing_user:
            return None
        
        # Create new user
        uid = str(uuid.uuid4())
        password_hash = self.get_password_hash(password)
        verification_token = self.generate_verification_token()
        
        user_data = UserData(
            uid=uid,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            language=language,
            email_verification_token=verification_token,
            created_at=datetime.utcnow(),
            trial_end_date=datetime.utcnow() + timedelta(days=settings.TRIAL_DAYS)
        )
        
        success = await firebase_manager.create_user(user_data)
        if success:
            return user_data
        return None
    
    async def verify_email(self, token: str) -> bool:
        """Verify user email with token"""
        try:
            # Find user by verification token
            users_ref = firebase_manager.db_ref.child('users')
            users_data = users_ref.order_by_child('email_verification_token').equal_to(token).get()
            
            if not users_data:
                return False
            
            uid = list(users_data.keys())[0]
            
            # Update user as verified
            await firebase_manager.update_user(uid, {
                'email_verified': True,
                'email_verification_token': None
            })
            
            return True
            
        except Exception as e:
            print(f"❌ Error verifying email: {e}")
            return False
    
    async def request_password_reset(self, email: str) -> Optional[str]:
        """Request password reset and return reset token"""
        user = await firebase_manager.get_user_by_email(email)
        if not user:
            return None
        
        reset_token = self.generate_verification_token()
        reset_expires = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        
        await firebase_manager.update_user(user.uid, {
            'password_reset_token': reset_token,
            'password_reset_expires': reset_expires
        })
        
        return reset_token
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password with token"""
        try:
            # Find user by reset token
            users_ref = firebase_manager.db_ref.child('users')
            users_data = users_ref.order_by_child('password_reset_token').equal_to(token).get()
            
            if not users_data:
                return False
            
            uid = list(users_data.keys())[0]
            user_data = users_data[uid]
            
            # Check if token is expired
            if user_data.get('password_reset_expires'):
                expires = datetime.fromisoformat(user_data['password_reset_expires'])
                if expires <= datetime.utcnow():
                    return False
            
            # Update password
            new_password_hash = self.get_password_hash(new_password)
            await firebase_manager.update_user(uid, {
                'password_hash': new_password_hash,
                'password_reset_token': None,
                'password_reset_expires': None
            })
            
            return True
            
        except Exception as e:
            print(f"❌ Error resetting password: {e}")
            return False

# Global instance
auth_manager = AuthManager()

# Dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserData:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = auth_manager.verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        uid: str = payload.get("sub")
        if uid is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    user = await firebase_manager.get_user(uid)
    if user is None:
        raise credentials_exception
    
    # Check if user is blocked
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked"
        )
    
    return user

async def get_current_admin(current_user: UserData = Depends(get_current_user)) -> UserData:
    """Get current authenticated admin user"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_active_user(current_user: UserData = Depends(get_current_user)) -> UserData:
    """Get current user with active subscription"""
    from .models import SubscriptionStatus
    
    # Check subscription status
    if current_user.subscription_status == SubscriptionStatus.EXPIRED:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription expired. Please renew your subscription."
        )
    
    # Check trial expiration
    if current_user.subscription_status == SubscriptionStatus.TRIAL:
        if current_user.trial_end_date and current_user.trial_end_date <= datetime.utcnow():
            # Update user status to expired
            await firebase_manager.update_user(current_user.uid, {
                'subscription_status': SubscriptionStatus.EXPIRED.value
            })
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Trial period expired. Please subscribe to continue."
            )
    
    return current_user