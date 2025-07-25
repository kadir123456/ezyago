import asyncio
import os
from contextlib import asynccontextmanager
<<<<<<< HEAD
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, status
=======
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uuid

# Import our modules
from .config import settings
from .database import firebase_manager
from .auth import auth_manager, get_current_user, get_current_admin, get_active_user
from .models import *
from .middleware import SecurityMiddleware, LoggingMiddleware, ErrorHandlerMiddleware
from .rate_limiter import start_rate_limiter_cleanup
from .encryption import encryption_manager

# Background tasks
background_tasks = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("🚀 Starting Ezyago Multi-User Trading Bot Platform...")
    
    # Startup validation
    startup_checks = {
        "Firebase": firebase_manager.is_ready(),
        "Encryption": encryption_manager.is_ready(),
    }
    
<<<<<<< HEAD
    print("🔍 Startup Checks:")
=======
    print("🔍 Startup validation:")
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
    for service, status in startup_checks.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {service}: {'Ready' if status else 'Not Ready'}")
    
    # Start background tasks
<<<<<<< HEAD
    print("🔄 Starting background tasks...")
    background_tasks.append(asyncio.create_task(start_rate_limiter_cleanup()))
    
    yield
    
    # Cleanup
    print("🛑 Shutting down...")
    for task in background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

# Create FastAPI app
app = FastAPI(
    title="Ezyago Trading Bot Platform",
    description="Multi-user automated trading bot platform",
    version="1.0.0",
=======
    cleanup_task = asyncio.create_task(start_rate_limiter_cleanup())
    background_tasks.append(cleanup_task)
    
    print("✅ Application startup complete!")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down application...")
    for task in background_tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    print("✅ Application shutdown complete!")

# Create FastAPI app
app = FastAPI(
    title="Ezyago Multi-User Trading Bot",
    description="Advanced cryptocurrency trading bot platform",
    version="2.0.0",
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityMiddleware)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
<<<<<<< HEAD
    return {
=======
    checks = {
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "firebase": firebase_manager.is_ready(),
<<<<<<< HEAD
            "encryption": encryption_manager.is_ready()
        }
    }

# Authentication endpoints
@app.post("/api/auth/register")
async def register_user(user_data: UserRegister):
=======
            "encryption": encryption_manager.is_ready(),
        }
    }
    
    # If any service is down, return 503
    if not all(checks["services"].values()):
        return JSONResponse(
            status_code=503,
            content=checks
        )
    
    return checks

# Authentication endpoints
@app.post("/api/auth/register", response_model=dict)
async def register(user_data: UserRegister):
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
    """Register a new user"""
    try:
        print(f"🔄 Registration attempt for: {user_data.email}")
        
<<<<<<< HEAD
        # Validate input
        if not user_data.email or not user_data.password or not user_data.full_name:
            print(f"❌ Missing required fields for: {user_data.email}")
            raise HTTPException(
                status_code=400,
                detail="Tüm alanlar gereklidir"
            )
        
        if len(user_data.password) < 6:
            print(f"❌ Password too short for: {user_data.email}")
            raise HTTPException(
                status_code=400,
                detail="Şifre en az 6 karakter olmalıdır"
            )
        
        # Register user
=======
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        user = await auth_manager.register_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        
        if not user:
<<<<<<< HEAD
            print(f"❌ Registration failed for: {user_data.email}")
            raise HTTPException(
                status_code=400,
                detail="Bu e-posta adresi zaten kullanılıyor"
=======
            raise HTTPException(
                status_code=400,
                detail="Kayıt işlemi başarısız. E-posta zaten kullanılıyor olabilir."
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
            )
        
        # Create access token
        access_token = auth_manager.create_access_token(
            data={"sub": user.uid, "email": user.email}
        )
        
<<<<<<< HEAD
        print(f"✅ Registration successful for: {user_data.email}")
        
=======
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "uid": user.uid,
                "email": user.email,
                "full_name": user.full_name,
<<<<<<< HEAD
                "role": user.role,
                "subscription_status": user.subscription_status,
                "trial_end_date": user.trial_end_date.isoformat() if user.trial_end_date else None
=======
                "role": user.role.value,
                "subscription_status": user.subscription_status.value
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Registration error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kayıt işlemi sırasında bir hata oluştu."
        )

@app.post("/api/auth/login", response_model=dict)
async def login(user_data: UserLogin):
    """Login user"""
    try:
        print(f"🔄 Login attempt for: {user_data.email}")
        
        user = await auth_manager.authenticate_user(user_data.email, user_data.password)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="E-posta veya şifre hatalı."
            )
        
        # Create access token
        access_token = auth_manager.create_access_token(
            data={"sub": user.uid, "email": user.email}
        )
        
        print(f"✅ Login successful for: {user_data.email} (Role: {user.role.value})")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "uid": user.uid,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "subscription_status": user.subscription_status.value
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Registration error for {user_data.email}: {e}")
        raise HTTPException(
            status_code=500,
<<<<<<< HEAD
            detail="Kayıt işlemi sırasında hata oluştu"
        )

@app.post("/api/auth/login")
async def login_user(user_data: UserLogin):
    """Login user"""
    try:
        print(f"🔄 Login attempt for: {user_data.email}")
        
        # Validate input
        if not user_data.email or not user_data.password:
            print(f"❌ Missing credentials for: {user_data.email}")
            raise HTTPException(
                status_code=400,
                detail="E-posta ve şifre gereklidir"
            )
        
        # Authenticate user
        user = await auth_manager.authenticate_user(
            email=user_data.email,
            password=user_data.password
        )
        
        if not user:
            print(f"❌ Authentication failed for: {user_data.email}")
            raise HTTPException(
                status_code=401,
                detail="E-posta veya şifre hatalı"
            )
        
        # Check if user is blocked
        if user.is_blocked:
            print(f"❌ Blocked user login attempt: {user_data.email}")
            raise HTTPException(
                status_code=403,
                detail="Hesabınız engellenmiş. Lütfen destek ile iletişime geçin."
            )
        
        # Create access token
        access_token = auth_manager.create_access_token(
            data={"sub": user.uid, "email": user.email}
        )
        
        print(f"✅ Login successful for: {user_data.email} (Role: {user.role})")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "uid": user.uid,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "subscription_status": user.subscription_status,
                "trial_end_date": user.trial_end_date.isoformat() if user.trial_end_date else None,
                "subscription_end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None
            }
=======
            detail="Giriş işlemi sırasında bir hata oluştu."
        )

@app.post("/api/auth/forgot-password")
async def forgot_password(request: PasswordReset):
    """Request password reset"""
    try:
        reset_token = await auth_manager.request_password_reset(request.email)
        if not reset_token:
            # Don't reveal if email exists or not
            pass
        
        return {"message": "Şifre sıfırlama bağlantısı e-posta adresinize gönderildi."}
        
    except Exception as e:
        print(f"❌ Password reset error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Şifre sıfırlama isteği gönderilirken hata oluştu."
        )

# User endpoints
@app.get("/api/user/profile", response_model=UserProfile)
async def get_profile(current_user: UserData = Depends(get_current_user)):
    """Get user profile"""
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

@app.put("/api/user/profile")
async def update_profile(
    profile_data: dict,
    current_user: UserData = Depends(get_current_user)
):
    """Update user profile"""
    try:
        allowed_fields = ['full_name', 'language']
        updates = {k: v for k, v in profile_data.items() if k in allowed_fields}
        
        if not updates:
            raise HTTPException(status_code=400, detail="Güncellenecek alan bulunamadı.")
        
        success = await firebase_manager.update_user(current_user.uid, updates)
        if not success:
            raise HTTPException(status_code=500, detail="Profil güncellenirken hata oluştu.")
        
        return {"message": "Profil başarıyla güncellendi."}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Profile update error: {e}")
        raise HTTPException(status_code=500, detail="Profil güncellenirken hata oluştu.")

@app.post("/api/user/api-keys")
async def save_api_keys(
    api_data: APIKeysUpdate,
    current_user: UserData = Depends(get_active_user)
):
    """Save encrypted API keys"""
    try:
        # Encrypt API credentials
        encrypted_key = encryption_manager.encrypt_api_key(api_data.api_key)
        encrypted_secret = encryption_manager.encrypt_api_secret(api_data.api_secret)
        
        if not encrypted_key or not encrypted_secret:
            raise HTTPException(
                status_code=500,
                detail="API anahtarları şifrelenirken hata oluştu."
            )
        
        # Save to database
        updates = {
            'encrypted_api_key': encrypted_key,
            'encrypted_api_secret': encrypted_secret,
            'is_testnet': api_data.is_testnet
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error for {user_data.email}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Giriş işlemi sırasında hata oluştu"
        )

# User profile endpoints
@app.get("/api/user/profile")
async def get_user_profile(current_user: UserData = Depends(get_current_user)):
    """Get current user profile"""
    try:
        print(f"📊 Profile request from: {current_user.email}")
        
        return {
            "uid": current_user.uid,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "subscription_status": current_user.subscription_status,
            "trial_end_date": current_user.trial_end_date.isoformat() if current_user.trial_end_date else None,
            "subscription_end_date": current_user.subscription_end_date.isoformat() if current_user.subscription_end_date else None,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "email_verified": current_user.email_verified,
            "language": current_user.language
        }
        
    except Exception as e:
        print(f"❌ Profile error for {current_user.email}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Profil bilgileri alınırken hata oluştu"
        )

@app.put("/api/user/profile")
async def update_user_profile(profile_data: dict, current_user: UserData = Depends(get_current_user)):
    """Update user profile"""
    try:
        print(f"🔄 Profile update for: {current_user.email}")
        
        # Update user profile
        updates = {}
        if "full_name" in profile_data:
            updates["full_name"] = profile_data["full_name"]
        if "language" in profile_data:
            updates["language"] = profile_data["language"]
        
        if updates:
            await firebase_manager.update_user(current_user.uid, updates)
            print(f"✅ Profile updated for: {current_user.email}")
        
        return {"message": "Profil başarıyla güncellendi"}
        
    except Exception as e:
        print(f"❌ Profile update error for {current_user.email}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Profil güncellenirken hata oluştu"
        )

# API Keys endpoints
@app.post("/api/user/api-keys")
async def save_api_keys(api_data: APIKeysUpdate, current_user: UserData = Depends(get_current_user)):
    """Save user API keys"""
    try:
        print(f"🔄 API keys update for: {current_user.email}")
        
        # Encrypt API keys
        encrypted_key = encryption_manager.encrypt_api_key(api_data.api_key)
        encrypted_secret = encryption_manager.encrypt_api_secret(api_data.api_secret)
        
        if not encrypted_key or not encrypted_secret:
            print(f"❌ Encryption failed for: {current_user.email}")
            raise HTTPException(
                status_code=500,
<<<<<<< HEAD
                detail="API anahtarları şifrelenirken hata oluştu"
            )
        
        # Update user
        await firebase_manager.update_user(current_user.uid, {
            "encrypted_api_key": encrypted_key,
            "encrypted_api_secret": encrypted_secret,
            "is_testnet": api_data.is_testnet
        })
        
        print(f"✅ API keys saved for: {current_user.email}")
        return {"message": "API anahtarları başarıyla kaydedildi"}
=======
                detail="API anahtarları kaydedilirken hata oluştu."
            )
        
        return {"message": "API anahtarları başarıyla kaydedildi."}
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ API keys save error for {current_user.email}: {e}")
        raise HTTPException(
            status_code=500,
<<<<<<< HEAD
            detail="API anahtarları kaydedilirken hata oluştu"
=======
            detail="API anahtarları kaydedilirken hata oluştu."
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        )

@app.delete("/api/user/api-keys")
async def delete_api_keys(current_user: UserData = Depends(get_current_user)):
<<<<<<< HEAD
    """Delete user API keys"""
    try:
        print(f"🔄 API keys deletion for: {current_user.email}")
        
        await firebase_manager.update_user(current_user.uid, {
            "encrypted_api_key": None,
            "encrypted_api_secret": None,
            "is_testnet": False
        })
        
        print(f"✅ API keys deleted for: {current_user.email}")
        return {"message": "API anahtarları silindi"}
        
    except Exception as e:
        print(f"❌ API keys deletion error for {current_user.email}: {e}")
        raise HTTPException(
            status_code=500,
            detail="API anahtarları silinirken hata oluştu"
        )

# Bot control endpoints
@app.post("/api/bot/start")
async def start_bot(request: BotControl, current_user: UserData = Depends(get_active_user)):
    """Start bot for authenticated user"""
    try:
        print(f"🔄 Bot start request from user: {current_user.email}")
        print(f"📊 Request data: action={request.action}, symbol={request.symbol}")
        
        # Validate symbol
        if not request.symbol:
            print(f"❌ No symbol provided by user: {current_user.email}")
            raise HTTPException(status_code=400, detail="Symbol gereklidir")
        
        symbol = request.symbol.upper()
        print(f"📊 Processing symbol: {symbol} for user: {current_user.email}")
        
        # Check if user has API keys
=======
    """Delete API keys"""
    try:
        updates = {
            'encrypted_api_key': None,
            'encrypted_api_secret': None,
            'is_testnet': False
        }
        
        success = await firebase_manager.update_user(current_user.uid, updates)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="API anahtarları silinirken hata oluştu."
            )
        
        return {"message": "API anahtarları başarıyla silindi."}
        
    except Exception as e:
        print(f"❌ API keys delete error: {e}")
        raise HTTPException(
            status_code=500,
            detail="API anahtarları silinirken hata oluştu."
        )

@app.delete("/api/user/account")
async def delete_account(current_user: UserData = Depends(get_current_user)):
    """Delete user account"""
    try:
        success = await firebase_manager.delete_user(current_user.uid)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Hesap silinirken hata oluştu."
            )
        
        return {"message": "Hesabınız başarıyla silindi."}
        
    except Exception as e:
        print(f"❌ Account delete error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Hesap silinirken hata oluştu."
        )

# Bot endpoints
@app.get("/api/bot/status", response_model=BotStatusResponse)
async def get_bot_status(current_user: UserData = Depends(get_active_user)):
    """Get bot status"""
    try:
        # Get fresh user data for updated stats
        fresh_user = await firebase_manager.get_user(current_user.uid)
        if not fresh_user:
            fresh_user = current_user
        
        return BotStatusResponse(
            status=fresh_user.bot_status,
            symbol=fresh_user.current_symbol,
            position_side=None,  # Will be implemented with actual bot
            last_signal=None,    # Will be implemented with actual bot
            uptime=0,           # Will be implemented with actual bot
            total_trades=fresh_user.total_trades,
            winning_trades=fresh_user.winning_trades,
            losing_trades=fresh_user.losing_trades,
            total_pnl=fresh_user.total_pnl,
            message=f"Bot durumu: {fresh_user.bot_status.value}"
        )
        
    except Exception as e:
        print(f"❌ Bot status error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Bot durumu alınırken hata oluştu."
        )

@app.post("/api/bot/start")
async def start_bot(
    request: BotControl,
    current_user: UserData = Depends(get_active_user)
):
    """Start bot"""
    try:
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        if not current_user.encrypted_api_key or not current_user.encrypted_api_secret:
            print(f"❌ User {current_user.email} has no API keys configured")
            raise HTTPException(
<<<<<<< HEAD
                status_code=400, 
                detail="Önce API anahtarlarınızı kaydetmelisiniz. Ayarlar > API Anahtarları bölümünden ekleyebilirsiniz."
            )
        
        # Check if bot is already running
        if current_user.bot_status == BotStatus.RUNNING:
            print(f"⚠️ Bot already running for user: {current_user.email}")
            raise HTTPException(
                status_code=400,
                detail="Bot zaten çalışıyor. Önce durdurun, sonra yeni sembol ile başlatın."
            )
        
        print(f"✅ All checks passed for user: {current_user.email}, starting bot...")
        
        # Update user status (simulated for now)
        await firebase_manager.update_user(current_user.uid, {
            'bot_status': BotStatus.RUNNING.value,
            'current_symbol': symbol,
            'bot_started_at': datetime.utcnow()
        })
        
        success_message = f"Bot {symbol} sembolü için başarıyla başlatıldı!"
        print(f"✅ Bot started successfully for user {current_user.email}: {success_message}")
=======
                status_code=400,
                detail="Önce API anahtarlarınızı kaydetmelisiniz."
            )
        
        if not request.symbol:
            raise HTTPException(
                status_code=400,
                detail="Trading sembolü gereklidir."
            )
        
        symbol = request.symbol.upper()
        
        # Update user status
        updates = {
            'bot_status': BotStatus.RUNNING.value,
            'current_symbol': symbol,
            'bot_started_at': datetime.utcnow()
        }
        
        success = await firebase_manager.update_user(current_user.uid, updates)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Bot başlatılırken hata oluştu."
            )
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        
        print(f"✅ Bot started for user {current_user.email} with symbol {symbol}")
        
        return {
            "success": True,
<<<<<<< HEAD
            "message": success_message,
            "status": "running",
            "symbol": symbol
=======
            "message": f"Bot {symbol} için başarıyla başlatıldı!",
            "symbol": symbol,
            "status": "running"
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        }
            
    except HTTPException:
        raise
    except Exception as e:
<<<<<<< HEAD
        error_message = f"Bot başlatılırken beklenmeyen hata: {str(e)}"
        print(f"❌ Unexpected error starting bot for user {current_user.email}: {error_message}")
        raise HTTPException(status_code=500, detail=error_message)

@app.post("/api/bot/stop")
async def stop_bot(current_user: UserData = Depends(get_current_user)):
    """Stop bot for authenticated user"""
    try:
        print(f"🔄 Bot stop request from user: {current_user.email}")
        
        if current_user.bot_status != BotStatus.RUNNING:
            print(f"⚠️ Bot not running for user: {current_user.email}")
            raise HTTPException(status_code=400, detail="Bot zaten durdurulmuş")
        
        # Update user status
        await firebase_manager.update_user(current_user.uid, {
            'bot_status': BotStatus.STOPPED.value,
            'current_symbol': None,
            'bot_started_at': None
        })
        
        success_message = "Bot başarıyla durduruldu"
        print(f"✅ Bot stopped for user: {current_user.email}")
=======
        print(f"❌ Bot start error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Bot başlatılırken hata oluştu."
        )

@app.post("/api/bot/stop")
async def stop_bot(current_user: UserData = Depends(get_active_user)):
    """Stop bot"""
    try:
        updates = {
            'bot_status': BotStatus.STOPPED.value,
            'current_symbol': None,
            'bot_started_at': None
        }
        
        success = await firebase_manager.update_user(current_user.uid, updates)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Bot durdurulurken hata oluştu."
            )
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        
        print(f"✅ Bot stopped for user {current_user.email}")
        
        return {
            "success": True,
<<<<<<< HEAD
            "message": success_message,
=======
            "message": "Bot başarıyla durduruldu.",
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
            "status": "stopped"
        }
        
    except Exception as e:
<<<<<<< HEAD
        print(f"❌ Bot stop error for {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Bot durdurulurken hata oluştu")

@app.get("/api/bot/status")
async def get_bot_status(current_user: UserData = Depends(get_current_user)):
    """Get bot status for authenticated user"""
    try:
        # Get fresh user data
        fresh_user = await firebase_manager.get_user(current_user.uid)
        if not fresh_user:
            fresh_user = current_user
        
        return {
            "status": fresh_user.bot_status.value if fresh_user.bot_status else "stopped",
            "symbol": fresh_user.current_symbol,
            "position_side": None,
            "last_signal": None,
            "uptime": 0,
            "total_trades": fresh_user.total_trades,
            "winning_trades": fresh_user.winning_trades,
            "losing_trades": fresh_user.losing_trades,
            "total_pnl": fresh_user.total_pnl,
            "message": f"Bot durumu: {fresh_user.bot_status.value if fresh_user.bot_status else 'stopped'}"
        }
        
    except Exception as e:
        print(f"❌ Bot status error for {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Bot durumu alınırken hata oluştu")

@app.get("/api/bot/settings")
async def get_bot_settings(current_user: UserData = Depends(get_current_user)):
    """Get bot settings for authenticated user"""
    try:
        return {
            "order_size_usdt": current_user.bot_order_size_usdt,
            "leverage": current_user.bot_leverage,
            "stop_loss_percent": current_user.bot_stop_loss_percent,
            "take_profit_percent": current_user.bot_take_profit_percent,
            "timeframe": current_user.bot_timeframe
        }
        
    except Exception as e:
        print(f"❌ Bot settings error for {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Bot ayarları alınırken hata oluştu")

@app.post("/api/bot/settings")
async def update_bot_settings(settings_data: BotSettings, current_user: UserData = Depends(get_current_user)):
    """Update bot settings for authenticated user"""
    try:
        print(f"🔄 Bot settings update for: {current_user.email}")
        
        # Update settings
        await firebase_manager.update_user(current_user.uid, {
            "bot_order_size_usdt": settings_data.order_size_usdt,
            "bot_leverage": settings_data.leverage,
            "bot_stop_loss_percent": settings_data.stop_loss_percent,
            "bot_take_profit_percent": settings_data.take_profit_percent,
            "bot_timeframe": settings_data.timeframe
        })
        
        print(f"✅ Bot settings updated for: {current_user.email}")
        return {"message": "Bot ayarları başarıyla güncellendi"}
        
    except Exception as e:
        print(f"❌ Bot settings update error for {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Bot ayarları güncellenirken hata oluştu")

# Payment endpoints
@app.get("/api/payment/wallet")
async def get_wallet_info(current_user: UserData = Depends(get_current_user)):
    """Get wallet information"""
    try:
        return {
            "wallet_address": settings.USDT_WALLET_ADDRESS,
            "amount": settings.SUBSCRIPTION_PRICE_USDT,
            "currency": "USDT"
        }
        
    except Exception as e:
        print(f"❌ Wallet info error for {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Cüzdan bilgileri alınırken hata oluştu")

@app.post("/api/payment/request")
async def request_payment(payment_data: PaymentNotification, current_user: UserData = Depends(get_current_user)):
    """Request payment notification"""
    try:
        print(f"🔄 Payment request from: {current_user.email}")
=======
        print(f"❌ Bot stop error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Bot durdurulurken hata oluştu."
        )

@app.get("/api/bot/settings")
async def get_bot_settings(current_user: UserData = Depends(get_current_user)):
    """Get bot settings"""
    return {
        "order_size_usdt": current_user.bot_order_size_usdt,
        "leverage": current_user.bot_leverage,
        "stop_loss_percent": current_user.bot_stop_loss_percent,
        "take_profit_percent": current_user.bot_take_profit_percent,
        "timeframe": current_user.bot_timeframe
    }

@app.post("/api/bot/settings")
async def update_bot_settings(
    settings_data: BotSettings,
    current_user: UserData = Depends(get_current_user)
):
    """Update bot settings"""
    try:
        updates = {
            'bot_order_size_usdt': settings_data.order_size_usdt,
            'bot_leverage': settings_data.leverage,
            'bot_stop_loss_percent': settings_data.stop_loss_percent,
            'bot_take_profit_percent': settings_data.take_profit_percent,
            'bot_timeframe': settings_data.timeframe
        }
        
        success = await firebase_manager.update_user(current_user.uid, updates)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Bot ayarları kaydedilirken hata oluştu."
            )
        
        return {"message": "Bot ayarları başarıyla kaydedildi."}
        
    except Exception as e:
        print(f"❌ Bot settings update error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Bot ayarları kaydedilirken hata oluştu."
        )

# Payment endpoints
@app.get("/api/payment/wallet")
async def get_payment_wallet():
    """Get USDT wallet address for payments"""
    return {
        "wallet_address": settings.USDT_WALLET_ADDRESS,
        "currency": "USDT",
        "network": "TRC-20/BEP-20/ERC-20",
        "amount": settings.SUBSCRIPTION_PRICE_USDT,
        "note": "Ödeme yaptıktan sonra aşağıdaki formu doldurun"
    }

@app.post("/api/payment/request")
async def request_payment(
    payment_data: PaymentNotification,
    current_user: UserData = Depends(get_current_user)
):
    """Submit payment notification"""
    try:
        # Verify email matches current user
        if payment_data.user_email.lower() != current_user.email.lower():
            raise HTTPException(
                status_code=400,
                detail="E-posta adresi hesabınızla eşleşmiyor."
            )
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        
        # Create payment request
        payment_request = PaymentRequest(
            payment_id=str(uuid.uuid4()),
            user_id=current_user.uid,
            user_email=current_user.email,
            amount=settings.SUBSCRIPTION_PRICE_USDT,
<<<<<<< HEAD
=======
            currency="USDT",
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
            message=payment_data.message,
            status="pending",
            created_at=datetime.utcnow()
        )
        
<<<<<<< HEAD
        await firebase_manager.create_payment_request(payment_request)
        
        print(f"✅ Payment request created for: {current_user.email}")
        return {"message": "Ödeme bildirimi gönderildi. 24 saat içinde onaylanacaktır."}
=======
        success = await firebase_manager.create_payment_request(payment_request)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Ödeme bildirimi gönderilirken hata oluştu."
            )
        
        return {
            "message": "Ödeme bildirimi başarıyla gönderildi. Ekran görüntüsünü bilwininc@gmail.com adresine e-posta ile gönderin. 24 saat içinde onaylanacaktır."
        }
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
        
    except Exception as e:
<<<<<<< HEAD
        print(f"❌ Payment request error for {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Ödeme bildirimi gönderilirken hata oluştu")
=======
        print(f"❌ Payment request error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ödeme bildirimi gönderilirken hata oluştu."
        )
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3

# Admin endpoints
@app.get("/api/admin/stats")
async def get_admin_stats(current_admin: UserData = Depends(get_current_admin)):
    """Get admin statistics"""
    try:
        stats = await firebase_manager.get_admin_stats()
        return stats
        
    except Exception as e:
        print(f"❌ Admin stats error: {e}")
<<<<<<< HEAD
        raise HTTPException(status_code=500, detail="İstatistikler alınırken hata oluştu")

# Account deletion
@app.delete("/api/user/account")
async def delete_account(current_user: UserData = Depends(get_current_user)):
    """Delete user account"""
    try:
        print(f"🔄 Account deletion for: {current_user.email}")
        
        await firebase_manager.delete_user(current_user.uid)
        
        print(f"✅ Account deleted for: {current_user.email}")
        return {"message": "Hesabınız başarıyla silindi"}
        
    except Exception as e:
        print(f"❌ Account deletion error for {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Hesap silinirken hata oluştu")

# Static files and routes
=======
        raise HTTPException(
            status_code=500,
            detail="İstatistikler alınırken hata oluştu."
        )

@app.get("/api/admin/users")
async def get_all_users(current_admin: UserData = Depends(get_current_admin)):
    """Get all users for admin"""
    try:
        users = await firebase_manager.get_all_users()
        return users
        
    except Exception as e:
        print(f"❌ Admin users error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kullanıcılar alınırken hata oluştu."
        )

@app.get("/api/admin/payments/pending")
async def get_pending_payments(current_admin: UserData = Depends(get_current_admin)):
    """Get pending payment requests"""
    try:
        payments = await firebase_manager.get_pending_payments()
        return [payment.dict() for payment in payments]
        
    except Exception as e:
        print(f"❌ Admin payments error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Bekleyen ödemeler alınırken hata oluştu."
        )

@app.post("/api/admin/payments/{payment_id}/approve")
async def approve_payment(
    payment_id: str,
    current_admin: UserData = Depends(get_current_admin)
):
    """Approve a payment request"""
    try:
        success = await firebase_manager.approve_payment(payment_id, current_admin.uid)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Ödeme bulunamadı veya onaylanamadı."
            )
        
        return {"message": "Ödeme onaylandı ve kullanıcının aboneliği uzatıldı."}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Payment approval error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ödeme onaylanırken hata oluştu."
        )

@app.post("/api/admin/users/{user_id}/block")
async def block_user(
    user_id: str,
    current_admin: UserData = Depends(get_current_admin)
):
    """Block a user"""
    try:
        success = await firebase_manager.update_user(user_id, {
            'is_blocked': True,
            'bot_status': BotStatus.STOPPED.value
        })
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Kullanıcı bulunamadı."
            )
        
        return {"message": "Kullanıcı engellendi."}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ User block error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kullanıcı engellenirken hata oluştu."
        )

@app.post("/api/admin/users/{user_id}/unblock")
async def unblock_user(
    user_id: str,
    current_admin: UserData = Depends(get_current_admin)
):
    """Unblock a user"""
    try:
        success = await firebase_manager.update_user(user_id, {'is_blocked': False})
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Kullanıcı bulunamadı."
            )
        
        return {"message": "Kullanıcı engeli kaldırıldı."}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ User unblock error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kullanıcı engeli kaldırılırken hata oluştu."
        )

# Static files and frontend
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/admin")
async def admin_panel():
<<<<<<< HEAD
    """Admin panel page"""
=======
    """Serve admin panel"""
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
    return FileResponse('static/admin.html')

@app.get("/api-guide")
async def api_guide():
<<<<<<< HEAD
    """API guide page"""
=======
    """Serve API guide"""
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
    return FileResponse('static/api-guide.html')

@app.get("/about")
async def about_page():
<<<<<<< HEAD
    """About page"""
=======
    """Serve about page"""
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
    return FileResponse('static/about.html')

@app.get("/contact")
async def contact_page():
<<<<<<< HEAD
    """Contact page"""
=======
    """Serve contact page"""
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
    return FileResponse('static/contact.html')

@app.get("/privacy")
async def privacy_page():
<<<<<<< HEAD
    """Privacy policy page"""
=======
    """Serve privacy page"""
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
    return FileResponse('static/privacy.html')

@app.get("/terms")
async def terms_page():
<<<<<<< HEAD
    """Terms of service page"""
=======
    """Serve terms page"""
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
    return FileResponse('static/terms.html')

@app.get("/risk")
async def risk_page():
<<<<<<< HEAD
    """Risk disclosure page"""
    return FileResponse('static/risk.html')

@app.get("/")
async def read_index():
    """Main page"""
    return FileResponse('static/index.html')
=======
    """Serve risk page"""
    return FileResponse('static/risk.html')

@app.get("/")
async def read_index():
    """Serve main page"""
    return FileResponse('static/index.html')

# Catch-all route for SPA
@app.get("/{path:path}")
async def catch_all(path: str):
    """Catch-all route for single page application"""
    # If it's an API route that doesn't exist, return 404
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Otherwise serve the main page (for client-side routing)
    return FileResponse('static/index.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True if settings.ENVIRONMENT == "development" else False
    )
>>>>>>> 6aefa7d6c4b534d4cb92a79096ca1e84eba060e3
