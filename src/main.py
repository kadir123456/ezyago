import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
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
    
    print("🔍 Startup validation:")
    for service, status in startup_checks.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {service}: {'Ready' if status else 'Not Ready'}")
    
    # Start background tasks
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
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "firebase": firebase_manager.is_ready(),
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
    """Register a new user"""
    try:
        print(f"🔄 Registration attempt for: {user_data.email}")
        
        user = await auth_manager.register_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            language=user_data.language
        )
        
        if not user:
            raise HTTPException(
                status_code=400,
                detail="Kayıt işlemi başarısız. E-posta zaten kullanılıyor olabilir."
            )
        
        # Create access token
        access_token = auth_manager.create_access_token(
            data={"sub": user.uid, "email": user.email}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "uid": user.uid,
                "email": user.email,
                "full_name": user.full_name,
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
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(
            status_code=500,
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
        }
        
        success = await firebase_manager.update_user(current_user.uid, updates)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="API anahtarları kaydedilirken hata oluştu."
            )
        
        return {"message": "API anahtarları başarıyla kaydedildi."}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ API keys save error: {e}")
        raise HTTPException(
            status_code=500,
            detail="API anahtarları kaydedilirken hata oluştu."
        )

@app.delete("/api/user/api-keys")
async def delete_api_keys(current_user: UserData = Depends(get_current_user)):
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
        if not current_user.encrypted_api_key or not current_user.encrypted_api_secret:
            raise HTTPException(
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
        
        print(f"✅ Bot started for user {current_user.email} with symbol {symbol}")
        
        return {
            "success": True,
            "message": f"Bot {symbol} için başarıyla başlatıldı!",
            "symbol": symbol,
            "status": "running"
        }
        
    except HTTPException:
        raise
    except Exception as e:
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
        
        print(f"✅ Bot stopped for user {current_user.email}")
        
        return {
            "success": True,
            "message": "Bot başarıyla durduruldu.",
            "status": "stopped"
        }
        
    except Exception as e:
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
        
        # Create payment request
        payment_request = PaymentRequest(
            payment_id=str(uuid.uuid4()),
            user_id=current_user.uid,
            user_email=current_user.email,
            amount=settings.SUBSCRIPTION_PRICE_USDT,
            currency="USDT",
            message=payment_data.message,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        success = await firebase_manager.create_payment_request(payment_request)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Ödeme bildirimi gönderilirken hata oluştu."
            )
        
        return {
            "message": "Ödeme bildirimi başarıyla gönderildi. Ekran görüntüsünü bilwininc@gmail.com adresine e-posta ile gönderin. 24 saat içinde onaylanacaktır."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Payment request error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ödeme bildirimi gönderilirken hata oluştu."
        )

# Admin endpoints
@app.get("/api/admin/stats")
async def get_admin_stats(current_admin: UserData = Depends(get_current_admin)):
    """Get admin statistics"""
    try:
        stats = await firebase_manager.get_admin_stats()
        return stats
        
    except Exception as e:
        print(f"❌ Admin stats error: {e}")
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
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/admin")
async def admin_panel():
    """Serve admin panel"""
    return FileResponse('static/admin.html')

@app.get("/api-guide")
async def api_guide():
    """Serve API guide"""
    return FileResponse('static/api-guide.html')

@app.get("/about")
async def about_page():
    """Serve about page"""
    return FileResponse('static/about.html')

@app.get("/contact")
async def contact_page():
    """Serve contact page"""
    return FileResponse('static/contact.html')

@app.get("/privacy")
async def privacy_page():
    """Serve privacy page"""
    return FileResponse('static/privacy.html')

@app.get("/terms")
async def terms_page():
    """Serve terms page"""
    return FileResponse('static/terms.html')

@app.get("/risk")
async def risk_page():
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
