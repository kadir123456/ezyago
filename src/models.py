from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class SubscriptionStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class BotStatus(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"

# --- Request Models ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    language: str = "tr"  # tr or en

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class APIKeysUpdate(BaseModel):
    api_key: str
    api_secret: str
    is_testnet: bool = False

class BotControl(BaseModel):
    action: str  # "start" or "stop"
    symbol: Optional[str] = None

class BotSettings(BaseModel):
    order_size_usdt: float = 25.0
    leverage: int = 10
    stop_loss_percent: float = 4.0
    take_profit_percent: float = 8.0
    timeframe: str = "15m"

class PaymentNotification(BaseModel):
    transaction_hash: Optional[str] = None
    amount: float
    message: Optional[str] = None

# --- Response Models ---
class UserProfile(BaseModel):
    uid: str
    email: str
    full_name: str
    role: UserRole
    subscription_status: SubscriptionStatus
    subscription_end_date: Optional[datetime]
    trial_end_date: Optional[datetime]
    created_at: datetime
    email_verified: bool
    language: str

class BotStatusResponse(BaseModel):
    status: BotStatus
    symbol: Optional[str]
    position_side: Optional[str]
    last_signal: Optional[str]
    uptime: Optional[int]
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    message: str

class AdminUserInfo(BaseModel):
    uid: str
    email: str
    full_name: str
    subscription_status: SubscriptionStatus
    subscription_end_date: Optional[datetime]
    trial_end_date: Optional[datetime]
    created_at: datetime
    last_login: Optional[datetime]
    bot_status: BotStatus
    total_trades: int
    total_pnl: float
    is_blocked: bool

class AdminStats(BaseModel):
    total_users: int
    trial_users: int
    active_subscribers: int
    expired_users: int
    total_revenue: float
    pending_payments: int
    active_bots: int

class IPWhitelistEntry(BaseModel):
    ip_address: str
    description: str
    is_active: bool = True
    created_at: datetime
    created_by: str  # admin uid

class IPWhitelistCreate(BaseModel):
    ip_address: str
    description: str

class IPWhitelistUpdate(BaseModel):
    description: Optional[str] = None
    is_active: Optional[bool] = None

# --- Database Models ---
class UserData(BaseModel):
    uid: str
    email: str
    password_hash: str
    full_name: str
    role: UserRole = UserRole.USER
    subscription_status: SubscriptionStatus = SubscriptionStatus.TRIAL
    subscription_end_date: Optional[datetime] = None
    trial_end_date: datetime
    created_at: datetime
    last_login: Optional[datetime] = None
    email_verified: bool = False
    email_verification_token: Optional[str] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    language: str = "tr"
    is_blocked: bool = False
    
    # Encrypted API credentials
    encrypted_api_key: Optional[str] = None
    encrypted_api_secret: Optional[str] = None
    is_testnet: bool = False
    
    # Bot configuration
    bot_status: BotStatus = BotStatus.STOPPED
    current_symbol: Optional[str] = None
    bot_started_at: Optional[datetime] = None
    
    # Bot Settings
    bot_order_size_usdt: float = 25.0
    bot_leverage: int = 10
    bot_stop_loss_percent: float = 4.0
    bot_take_profit_percent: float = 8.0
    bot_timeframe: str = "15m"
    
    # Statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0

class TradeData(BaseModel):
    trade_id: str
    user_id: str
    symbol: str
    side: str  # LONG or SHORT
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: float
    status: str  # OPEN, CLOSED, CANCELLED
    entry_time: datetime
    exit_time: Optional[datetime]
    close_reason: str  # SIGNAL, STOP_LOSS, MANUAL

class PaymentRequest(BaseModel):
    payment_id: str
    user_id: str
    amount: float
    currency: str = "USDT"
    transaction_hash: Optional[str]
    message: Optional[str]
    status: str = "pending"  # pending, approved, rejected
    created_at: datetime
    processed_at: Optional[datetime]
    processed_by: Optional[str]  # admin uid