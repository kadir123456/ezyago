# GÜNCELLENMİŞ VE TAM auth.py DOSYASI

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings
from .database import firebase_manager
from .models import UserData, UserRole, SubscriptionStatus
from firebase_admin import auth as firebase_auth

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class AuthManager:
    # ... (AuthManager sınıfının içeriği doğru, olduğu gibi bırakılabilir) ...
    # Sadece emin olmak için tam halini aşağıya ekliyorum
    def __init__(self):
        self.pwd_context = pwd_context
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    async def authenticate_user(self, email: str, password: str) -> Optional[UserData]:
        user = await firebase_manager.get_user_by_email(email)
        if not user or not self.verify_password(password, user.password_hash):
            return None
        await firebase_manager.update_user(user.uid, {'last_login': datetime.now(timezone.utc).isoformat()})
        return user

    async def register_user(self, email: str, password: str, full_name: str) -> Optional[UserData]:
        try:
            firebase_user = firebase_auth.create_user(email=email, password=password, display_name=full_name)
            user_data_dict = {
                "uid": firebase_user.uid, "email": email, "password_hash": self.get_password_hash(password),
                "full_name": full_name, "role": UserRole.USER.value,
                "subscription_status": SubscriptionStatus.TRIAL.value, "subscription_end_date": None,
                "trial_end_date": (datetime.now(timezone.utc) + timedelta(days=settings.TRIAL_DAYS)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(), "last_login": None,
                "email_verified": False, "language": "tr", "is_blocked": False,
                "bot_status": "stopped", "total_trades": 0, "winning_trades": 0, "losing_trades": 0, "total_pnl": 0.0,
                "bot_order_size_usdt": 25.0, "bot_leverage": 10, "bot_stop_loss_percent": 4.0,
                "bot_take_profit_percent": 8.0, "bot_timeframe": "15m"
            }
            if not await firebase_manager.create_user(user_data_dict):
                firebase_auth.delete_user(firebase_user.uid)
                return None
            return await firebase_manager.get_user(firebase_user.uid)
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return None

auth_manager = AuthManager()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserData:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        uid: str = payload.get("sub")
        if uid is None: raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await firebase_manager.get_user(uid)
    if user is None: raise credentials_exception
    if user.is_blocked: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is blocked")
    
    return user

async def get_current_admin(current_user: UserData = Depends(get_current_user)) -> UserData:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

async def get_active_user(current_user: UserData = Depends(get_current_user)) -> UserData:
    now = datetime.now(timezone.utc)
    is_expired = False
    
    if current_user.subscription_status == SubscriptionStatus.TRIAL and current_user.trial_end_date and current_user.trial_end_date <= now:
        is_expired = True
    elif current_user.subscription_status == SubscriptionStatus.ACTIVE and current_user.subscription_end_date and current_user.subscription_end_date <= now:
        is_expired = True

    if is_expired:
        await firebase_manager.update_user(current_user.uid, {'subscription_status': SubscriptionStatus.EXPIRED.value})
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Aboneliğinizin süresi doldu.")
    
    return current_user
