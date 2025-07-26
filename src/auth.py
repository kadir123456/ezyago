# GÜNCELLENMİŞ VE TAM auth.py DOSYASI

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
import uuid
from .config import settings
from .database import firebase_manager
from .models import UserData, UserRole, SubscriptionStatus
import firebase_admin
from firebase_admin import auth as firebase_auth

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
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    async def authenticate_user(self, email: str, password: str) -> Optional[UserData]:
        """Authenticate a user with email and password"""
        try:
            user = await firebase_manager.get_user_by_email(email)
            if not user:
                print(f"❌ User not found in database: {email}")
                return None
            
            if not self.verify_password(password, user.password_hash):
                print(f"❌ Invalid password for user: {email}")
                return None
            
            await firebase_manager.update_user(user.uid, {
                'last_login': datetime.now(timezone.utc).isoformat()
            })
            
            print(f"✅ User authenticated successfully: {email}")
            return user
            
        except Exception as e:
            print(f"❌ Authentication error for {email}: {e}")
            return None
    
    async def register_user(self, email: str, password: str, full_name: str) -> Optional[UserData]:
        """Register a new user in Firebase Auth and Realtime DB"""
        try:
            # 1. Create user in Firebase Authentication
            firebase_user = firebase_auth.create_user(
                email=email,
                password=password,
                display_name=full_name,
                email_verified=False
            )
            print(f"✅ Firebase Auth user created: {firebase_user.uid}")

            # 2. Create user data for Realtime Database
            password_hash = self.get_password_hash(password)
            user_data_dict = {
                "uid": firebase_user.uid,
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "role": UserRole.USER.value,
                "subscription_status": SubscriptionStatus.TRIAL.value,
                "subscription_end_date": None,
                "trial_end_date": (datetime.now(timezone.utc) + timedelta(days=settings.TRIAL_DAYS)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_login": None,
                "email_verified": False,
                "language": "tr",
                "is_blocked": False,
                "bot_status": "stopped",
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0.0,
                # Varsayılan bot ayarlarını en başta ekliyoruz
                "bot_order_size_usdt": 25.0,
                "bot_leverage": 10,
                "bot_stop_loss_percent": 4.0,
                "bot_take_profit_percent": 8.0,
                "bot_timeframe": "15m"
            }
            
            # 3. Save user to Realtime Database
            success = await firebase_manager.create_user(user_data_dict)
            if not success:
                # If DB write fails, delete the auth user to prevent orphaned accounts
                firebase_auth.delete_user(firebase_user.uid)
                print(f"🧹 Cleaned up Firebase Auth user after database failure: {email}")
                return None

            print(f"✅ User created successfully in database: {email}")
            return await firebase_manager.get_user(firebase_user.uid)

        except firebase_auth.EmailAlreadyExistsError:
            print(f"❌ Email already exists in Firebase Auth: {email}")
            return None
        except Exception as e:
            print(f"❌ Registration error for {email}: {e}")
            return None

# Global instance
auth_manager = AuthManager()

# Dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserData:
    """Get current authenticated user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        uid: str = payload.get("sub")
        if uid is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # database.py'deki GÜNCELLENMİŞ get_user fonksiyonunu çağırıyoruz
    user = await firebase_manager.get_user(uid)
    if user is None:
        raise credentials_exception
    
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
    now = datetime.now(timezone.utc)
    is_expired = False

    if current_user.subscription_status == SubscriptionStatus.TRIAL and current_user.trial_end_date and current_user.trial_end_date <= now:
        is_expired = True
    elif current_user.subscription_status == SubscriptionStatus.ACTIVE and current_user.subscription_end_date and current_user.subscription_end_date <= now:
        is_expired = True

    if is_expired:
        await firebase_manager.update_user(current_user.uid, {
            'subscription_status': SubscriptionStatus.EXPIRED.value
        })
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription expired. Please renew your subscription."
        )
    
    return current_user
