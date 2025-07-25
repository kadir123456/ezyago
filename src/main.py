from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime, timedelta
import asyncio
import uuid
from typing import List, Optional

from .config import settings
from .models import *
from .database import firebase_manager
from .auth import auth_manager, get_current_user, get_current_admin, get_active_user
from .encryption import encryption_manager
from .bot_manager import bot_manager
from .middleware import SecurityMiddleware, LoggingMiddleware, ErrorHandlerMiddleware
from .rate_limiter import start_rate_limiter_cleanup

# FastAPI app initialization
app = FastAPI(
    title="Ezyago - Multi-User Trading Bot Platform",
    description="Secure, subscription-based cryptocurrency trading bot platform",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None
)

# Security middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(LoggingMiddleware)

# Trusted hosts (production security)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["ezyago.com", "www.ezyago.com", "*.onrender.com"]
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ezyago.com", "https://www.ezyago.com"] if settings.ENVIRONMENT == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 Ezyago platform starting up...")
    
    # Check Firebase connection
    if not firebase_manager.is_ready():
        print("❌ Firebase connection failed!")
        raise Exception("Firebase initialization failed")
    
    # Check encryption manager
    if not encryption_manager.is_ready():
        print("❌ Encryption manager not ready!")
        raise Exception("Encryption manager initialization failed")
    
    # Start subscription checker background task
    asyncio.create_task(subscription_checker())
    
    # Start bot manager cleanup task
    asyncio.create_task(bot_manager.cleanup_inactive_bots())
    
    # Start rate limiter cleanup
    asyncio.create_task(start_rate_limiter_cleanup())
    
    print("✅ Ezyago platform started successfully!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 Ezyago platform shutting down...")
    await bot_manager.stop_all_bots()
    print("✅ Shutdown complete")

# Background task for checking expired subscriptions
async def subscription_checker():
    """Background task to check and update expired subscriptions"""
    while True:
        try:
            expired_users = await firebase_manager.check_expired_subscriptions()
            if expired_users:
                print(f"🔄 Updated {len(expired_users)} expired subscriptions")
        except Exception as e:
            print(f"❌ Error in subscription checker: {e}")
        
        # Check every hour
        await asyncio.sleep(3600)

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/api/auth/register", response_model=dict)
async def register_user(user_data: UserRegister):
    """Register a new user"""
    try:
        # Validate input
        if not user_data.email or not user_data.password or not user_data.full_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email, password, and full name are required"
            )
        
        # Validate password strength
        if len(user_data.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        
        # Check if user already exists
        existing_user = await firebase_manager.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Register new user
        new_user = await auth_manager.register_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            language=user_data.language
        )
        
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user account. Please check your email and password."
            )
        
        # Create access token
        access_token = auth_manager.create_access_token(
            data={"sub": new_user.uid, "email": new_user.email}
        )
        
        print(f"✅ User registration completed successfully: {user_data.email}")
        
        return {
            "message": "User registered successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "uid": new_user.uid,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "subscription_status": new_user.subscription_status.value,
                "trial_end_date": new_user.trial_end_date.isoformat() if new_user.trial_end_date else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )

@app.post("/api/auth/login", response_model=dict)
async def login_user(login_data: UserLogin):
    """Authenticate user and return access token"""
    try:
        # Validate input
        if not login_data.email or not login_data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )
        
        # Authenticate user
        user = await auth_manager.authenticate_user(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is blocked
        if user.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is blocked. Please contact support."
            )
        
        # Create access token
        access_token = auth_manager.create_access_token(
            data={"sub": user.uid, "email": user.email}
        )
        
        print(f"✅ User login completed successfully: {login_data.email}")
        
        return {
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "uid": user.uid,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "subscription_status": user.subscription_status.value,
                "subscription_end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None,
                "trial_end_date": user.trial_end_date.isoformat() if user.trial_end_date else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@app.post("/api/auth/forgot-password", response_model=dict)
async def forgot_password(request: PasswordReset):
    """Request password reset"""
    try:
        reset_token = await auth_manager.request_password_reset(request.email)
        if not reset_token:
            # Don't reveal if email exists or not for security
            return {"message": "If the email exists, a reset link has been sent"}
        
        # TODO: Send email with reset token
        # For now, we'll return success message
        print(f"🔑 Password reset token for {request.email}: {reset_token}")
        
        return {"message": "Password reset instructions sent to your email"}
        
    except Exception as e:
        print(f"❌ Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/api/auth/reset-password", response_model=dict)
async def reset_password(request: PasswordResetConfirm):
    """Reset password with token"""
    try:
        success = await auth_manager.reset_password(request.token, request.new_password)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Password reset confirmation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/api/auth/verify-email/{token}", response_model=dict)
async def verify_email(token: str):
    """Verify user email with token"""
    try:
        success = await auth_manager.verify_email(token)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        return {"message": "Email verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ==================== USER PROFILE ENDPOINTS ====================

@app.get("/api/user/profile", response_model=UserProfile)
async def get_user_profile(current_user: UserData = Depends(get_current_user)):
    """Get current user profile"""
    return UserProfile(
        uid=current_user.uid,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        subscription_status=current_user.subscription_status,
        subscription_end_date=current_user.subscription_end_date,
        trial_end_date=current_user.trial_end_date,
        created_at=current_user.created_at,
        email_verified=current_user.email_verified,
        language=current_user.language
    )

@app.put("/api/user/profile", response_model=dict)
async def update_user_profile(
    updates: dict,
    current_user: UserData = Depends(get_current_user)
):
    """Update user profile"""
    try:
        # Only allow certain fields to be updated
        allowed_fields = ["full_name", "language"]
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not filtered_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )
        
        success = await firebase_manager.update_user(current_user.uid, filtered_updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile"
            )
        
        return {"message": "Profile updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.delete("/api/user/account", response_model=dict)
async def delete_user_account(current_user: UserData = Depends(get_current_user)):
    """Delete user account and all associated data"""
    try:
        # TODO: Stop user's bot if running
        
        success = await firebase_manager.delete_user(current_user.uid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete account"
            )
        
        return {"message": "Account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Account deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ==================== API KEYS MANAGEMENT ====================

@app.post("/api/user/api-keys", response_model=dict)
async def save_api_keys(
    api_keys: APIKeysUpdate,
    current_user: UserData = Depends(get_active_user)
):
    """Save encrypted Binance API keys"""
    try:
        # Encrypt API keys
        encrypted_api_key = encryption_manager.encrypt_api_key(api_keys.api_key)
        encrypted_api_secret = encryption_manager.encrypt_api_secret(api_keys.api_secret)
        
        if not encrypted_api_key or not encrypted_api_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to encrypt API keys"
            )
        
        # Save to database
        updates = {
            "encrypted_api_key": encrypted_api_key,
            "encrypted_api_secret": encrypted_api_secret,
            "is_testnet": api_keys.is_testnet
        }
        
        success = await firebase_manager.update_user(current_user.uid, updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save API keys"
            )
        
        return {"message": "API keys saved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ API keys save error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/api/user/api-keys/status", response_model=dict)
async def get_api_keys_status(current_user: UserData = Depends(get_current_user)):
    """Check if user has API keys configured"""
    has_api_keys = bool(current_user.encrypted_api_key and current_user.encrypted_api_secret)
    
    return {
        "has_api_keys": has_api_keys,
        "is_testnet": current_user.is_testnet
    }

@app.delete("/api/user/api-keys", response_model=dict)
async def delete_api_keys(current_user: UserData = Depends(get_current_user)):
    """Delete user's API keys"""
    try:
        # TODO: Stop user's bot if running
        
        updates = {
            "encrypted_api_key": None,
            "encrypted_api_secret": None,
            "is_testnet": False
        }
        
        success = await firebase_manager.update_user(current_user.uid, updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete API keys"
            )
        
        return {"message": "API keys deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ API keys deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ==================== BOT CONTROL ENDPOINTS ====================

@app.get("/api/bot/settings", response_model=BotSettings)
async def get_bot_settings(current_user: UserData = Depends(get_current_user)):
    """Get user's bot settings"""
    return BotSettings(
        order_size_usdt=current_user.bot_order_size_usdt,
        leverage=current_user.bot_leverage,
        stop_loss_percent=current_user.bot_stop_loss_percent,
        take_profit_percent=current_user.bot_take_profit_percent,
        timeframe=current_user.bot_timeframe
    )

@app.post("/api/bot/settings", response_model=dict)
async def update_bot_settings(
    settings: BotSettings,
    current_user: UserData = Depends(get_current_user)
):
    """Update user's bot settings"""
    try:
        # Validate settings
        if settings.order_size_usdt < 10 or settings.order_size_usdt > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order size must be between 10-1000 USDT"
            )
        
        if settings.leverage < 1 or settings.leverage > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leverage must be between 1-20x"
            )
        
        if settings.stop_loss_percent < 1 or settings.stop_loss_percent > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stop loss must be between 1-10%"
            )
        
        if settings.take_profit_percent < 2 or settings.take_profit_percent > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Take profit must be between 2-20%"
            )
        
        # Update user settings
        updates = {
            "bot_order_size_usdt": settings.order_size_usdt,
            "bot_leverage": settings.leverage,
            "bot_stop_loss_percent": settings.stop_loss_percent,
            "bot_take_profit_percent": settings.take_profit_percent,
            "bot_timeframe": settings.timeframe
        }
        
        success = await firebase_manager.update_user(current_user.uid, updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update bot settings"
            )
        
        return {"message": "Bot settings updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Bot settings update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/api/bot/start", response_model=dict)
async def start_bot(
    request: BotControl,
    current_user: UserData = Depends(get_active_user)
):
    """Start user's trading bot"""
    try:
        # Check if user has API keys
        if not current_user.encrypted_api_key or not current_user.encrypted_api_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please configure your Binance API keys first"
            )
        
        # Check if bot is already running
        if current_user.bot_status == BotStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bot is already running"
            )
        
        # Validate symbol
        if not request.symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trading symbol is required"
            )
        
        # Start bot instance for this user
        success = await bot_manager.start_user_bot(current_user, request.symbol.upper())
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start bot"
            )
        
        return {
            "message": f"Bot started successfully for {request.symbol.upper()}",
            "symbol": request.symbol.upper(),
            "status": "running"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Bot start error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/api/bot/stop", response_model=dict)
async def stop_bot(current_user: UserData = Depends(get_current_user)):
    """Stop user's trading bot"""
    try:
        # Check if bot is running
        if current_user.bot_status != BotStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bot is not currently running"
            )
        
        # Stop bot instance for this user
        success = await bot_manager.stop_user_bot(current_user.uid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop bot"
            )
        
        return {
            "message": "Bot stopped successfully",
            "status": "stopped"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Bot stop error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/api/bot/status", response_model=BotStatusResponse)
async def get_bot_status(current_user: UserData = Depends(get_current_user)):
    """Get user's bot status and statistics"""
    try:
        # Get bot status from bot manager
        bot_status = await bot_manager.get_user_bot_status(current_user.uid)
        
        # Get updated user stats
        updated_user = await firebase_manager.get_user(current_user.uid)
        if updated_user:
            current_user = updated_user
        
        return BotStatusResponse(
            status=BotStatus(bot_status.get('status', 'stopped')),
            symbol=bot_status.get('symbol'),
            position_side=bot_status.get('position_side'),
            last_signal=bot_status.get('last_signal'),
            uptime=bot_status.get('uptime', 0),
            total_trades=current_user.total_trades,
            winning_trades=current_user.winning_trades,
            losing_trades=current_user.losing_trades,
            total_pnl=current_user.total_pnl,
            message=bot_status.get('message', 'Bot status unknown')
        )
        
    except Exception as e:
        print(f"❌ Bot status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ==================== PAYMENT ENDPOINTS ====================

@app.post("/api/payment/request", response_model=dict)
async def request_payment(
    payment_data: PaymentNotification,
    current_user: UserData = Depends(get_current_user)
):
    """Submit payment notification for admin approval"""
    try:
        # Create payment request
        payment_request = PaymentRequest(
            payment_id=str(uuid.uuid4()),
            user_id=current_user.uid,
            amount=payment_data.amount,
            transaction_hash=payment_data.transaction_hash,
            message=payment_data.message,
            created_at=datetime.utcnow()
        )
        
        success = await firebase_manager.create_payment_request(payment_request)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit payment request"
            )
        
        return {
            "message": "Payment notification submitted successfully. Please wait for admin approval.",
            "payment_id": payment_request.payment_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Payment request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/api/payment/wallet", response_model=dict)
async def get_payment_wallet():
    """Get USDT wallet address for payments"""
    return {
        "wallet_address": settings.USDT_WALLET_ADDRESS,
        "currency": "USDT",
        "network": "TRC-20 or BEP-20",
        "amount": settings.SUBSCRIPTION_PRICE_USDT,
        "note": "Please include your email address in the transaction memo"
    }

# ==================== ADMIN ENDPOINTS ====================

@app.get("/api/admin/stats", response_model=AdminStats)
async def get_admin_stats(admin_user: UserData = Depends(get_current_admin)):
    """Get admin dashboard statistics"""
    try:
        stats = await firebase_manager.get_admin_stats()
        
        # Add bot statistics
        bot_stats = bot_manager.get_all_bot_stats()
        stats['active_bots'] = bot_stats['active_bots']
        
        return AdminStats(**stats)
        
    except Exception as e:
        print(f"❌ Admin stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/api/admin/users", response_model=List[AdminUserInfo])
async def get_all_users(admin_user: UserData = Depends(get_current_admin)):
    """Get all users for admin management"""
    try:
        users_data = await firebase_manager.get_all_users()
        
        admin_users = []
        for user_data in users_data:
            admin_users.append(AdminUserInfo(
                uid=user_data.get('uid'),
                email=user_data.get('email'),
                full_name=user_data.get('full_name'),
                subscription_status=SubscriptionStatus(user_data.get('subscription_status', 'trial')),
                subscription_end_date=user_data.get('subscription_end_date'),
                trial_end_date=user_data.get('trial_end_date'),
                created_at=user_data.get('created_at'),
                last_login=user_data.get('last_login'),
                bot_status=BotStatus(user_data.get('bot_status', 'stopped')),
                total_trades=user_data.get('total_trades', 0),
                total_pnl=user_data.get('total_pnl', 0.0),
                is_blocked=user_data.get('is_blocked', False)
            ))
        
        return admin_users
        
    except Exception as e:
        print(f"❌ Admin users list error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/api/admin/payments/pending", response_model=List[PaymentRequest])
async def get_pending_payments(admin_user: UserData = Depends(get_current_admin)):
    """Get all pending payment requests"""
    try:
        payments = await firebase_manager.get_pending_payments()
        return payments
        
    except Exception as e:
        print(f"❌ Admin pending payments error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/api/admin/payments/{payment_id}/approve", response_model=dict)
async def approve_payment(
    payment_id: str,
    admin_user: UserData = Depends(get_current_admin)
):
    """Approve a payment request"""
    try:
        success = await firebase_manager.approve_payment(payment_id, admin_user.uid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment request not found"
            )
        
        return {"message": "Payment approved and subscription extended"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Payment approval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/api/admin/users/{user_id}/block", response_model=dict)
async def block_user(
    user_id: str,
    admin_user: UserData = Depends(get_current_admin)
):
    """Block a user"""
    try:
        success = await firebase_manager.update_user(user_id, {
            "is_blocked": True,
            "bot_status": BotStatus.STOPPED.value
        })
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": "User blocked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ User blocking error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/api/admin/users/{user_id}/unblock", response_model=dict)
async def unblock_user(
    user_id: str,
    admin_user: UserData = Depends(get_current_admin)
):
    """Unblock a user"""
    try:
        success = await firebase_manager.update_user(user_id, {"is_blocked": False})
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": "User unblocked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ User unblocking error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/api/admin/ip-whitelist", response_model=List[dict])
async def admin_get_ip_whitelist(admin_user: UserData = Depends(get_current_admin)):
    """Get all IP whitelist entries for admin"""
    try:
        entries = await firebase_manager.get_ip_whitelist()
        return entries
        
    except Exception as e:
        print(f"❌ Admin IP whitelist error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/api/admin/ip-whitelist", response_model=dict)
async def admin_create_ip_whitelist(
    entry_data: IPWhitelistCreate,
    admin_user: UserData = Depends(get_current_admin)
):
    """Create new IP whitelist entry"""
    try:
        from .models import IPWhitelistEntry
        
        entry = IPWhitelistEntry(
            ip_address=entry_data.ip_address,
            description=entry_data.description,
            created_at=datetime.utcnow(),
            created_by=admin_user.uid
        )
        
        success = await firebase_manager.create_ip_whitelist_entry(entry)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create IP whitelist entry"
            )
        
        return {"message": "IP whitelist entry created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Admin create IP whitelist error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.put("/api/admin/ip-whitelist/{ip_address}", response_model=dict)
async def admin_update_ip_whitelist(
    ip_address: str,
    updates: IPWhitelistUpdate,
    admin_user: UserData = Depends(get_current_admin)
):
    """Update IP whitelist entry"""
    try:
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        success = await firebase_manager.update_ip_whitelist_entry(ip_address, update_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="IP whitelist entry not found"
            )
        
        return {"message": "IP whitelist entry updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Admin update IP whitelist error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.delete("/api/admin/ip-whitelist/{ip_address}", response_model=dict)
async def admin_delete_ip_whitelist(
    ip_address: str,
    admin_user: UserData = Depends(get_current_admin)
):
    """Delete IP whitelist entry"""
    try:
        success = await firebase_manager.delete_ip_whitelist_entry(ip_address)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="IP whitelist entry not found"
            )
        
        return {"message": "IP whitelist entry deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Admin delete IP whitelist error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ==================== STATIC FILES AND FRONTEND ====================

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve frontend
@app.get("/")
async def serve_frontend():
    """Serve the main frontend application"""
    return FileResponse("static/index.html")

@app.get("/api-guide")
async def serve_api_guide():
    """Serve the API guide page"""
    return FileResponse("static/api-guide.html")

@app.get("/about")
async def serve_about():
    """Serve the about page"""
    return FileResponse("static/about.html")

@app.get("/privacy")
async def serve_privacy():
    """Serve the privacy policy page"""
    return FileResponse("static/privacy.html")

@app.get("/terms")
async def serve_terms():
    """Serve the terms of service page"""
    return FileResponse("static/terms.html")

@app.get("/risk")
async def serve_risk():
    """Serve the risk disclosure page"""
    return FileResponse("static/risk.html")

@app.get("/admin")
async def serve_admin():
    """Serve the admin panel"""
    return FileResponse("static/admin.html")

@app.get("/contact")
async def serve_contact():
    """Serve the contact page"""
    return FileResponse("static/contact.html")

@app.get("/sitemap.xml")
async def serve_sitemap():
    """Serve sitemap.xml"""
    return FileResponse("static/sitemap.xml", media_type="application/xml")

@app.get("/robots.txt")
async def serve_robots():
    """Serve robots.txt"""
    return FileResponse("static/robots.txt", media_type="text/plain")

# Catch-all route for SPA routing
@app.get("/{path:path}")
async def serve_spa(path: str):
    """Serve SPA for all frontend routes"""
    # Don't serve SPA for API routes
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Serve admin panel for admin routes
    if path.startswith("admin"):
        return FileResponse("static/admin.html")
    
    return FileResponse("static/index.html")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }