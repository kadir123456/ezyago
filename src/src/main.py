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
    
    print

@app.post("/api/bot/start")
async def start_bot(request: BotControl, current_user: UserData = Depends(get_active_user)):
    """Start bot for authenticated user"""
    try:
        print(f"🔐 API keys save request from user: {current_user.email}")
        
        print(f"🔄 Bot start request from user: {current_user.email} for symbol: {request.symbol}")
        
        # Validate symbol
        if not request.symbol:
            print(f"❌ No symbol provided by user: {current_user.email}")
            raise HTTPException(status_code=400, detail="Symbol gereklidir")
        
        symbol = request.symbol.upper()
        print(f"📊 Processing symbol: {symbol} for user: {current_user.email}")
        
        # Check if user has API keys
        if not current_user.encrypted_api_key or not current_user.encrypted_api_secret:
            print(f"❌ User {current_user.email} has no API keys configured")
            raise HTTPException(
                status_code=400, 
                detail="Önce API anahtarlarınızı kaydetmelisiniz. Ayarlar > API Anahtarları bölümünden ekleyebilirsiniz."
            )
        
        # Check subscription status
        if current_user.subscription_status == SubscriptionStatus.EXPIRED:
            print(f"❌ User {current_user.email} has expired subscription")
            raise HTTPException(
                status_code=402,
                detail="Aboneliğinizin süresi dolmuş. Lütfen aboneliğinizi yenileyin."
            )
        
        # Check if bot is already running
        if current_user.bot_status == BotStatus.RUNNING:
            print(f"⚠️ Bot already running for user: {current_user.email}")
            raise HTTPException(
                status_code=400,
                detail="Bot zaten çalışıyor. Önce durdurun, sonra yeni sembol ile başlatın."
            )
        
        print(f"✅ All checks passed for user: {current_user.email}, starting bot...")
        
        # TODO: Start bot with bot_manager
        # success = await bot_manager.start_user_bot(current_user, symbol)
        # For now, simulate success
        success = True
        
        if success:
            # Update user status
            await firebase_manager.update_user(current_user.uid, {
                'bot_status': BotStatus.RUNNING.value,
                'current_symbol': symbol,
                'bot_started_at': datetime.utcnow()
            })
            
            success_message = f"Bot {symbol} sembolü için başarıyla başlatıldı!"
            print(f"✅ Bot started successfully for user {current_user.email}: {success_message}")
            
            return {
                "success": True,
                "message": success_message,
                "status": "running",
                "symbol": symbol
            }
            success_message = "API anahtarları başarıyla kaydedildi ve şifrelendi."
            print(f"✅ API keys saved successfully for user {current_user.email}")
        else:
            error_message = f"Bot {symbol} için başlatılamadı. Lütfen API anahtarlarınızı kontrol edin."
                "message": success_message
            print(f"❌ Encryption manager not ready for user: {current_user.email}")
            print(f"❌ Failed to encrypt API keys for user: {current_user.email}")
            error_message = "API anahtarları kaydedilemedi. Lütfen tekrar deneyin."
            print(f"❌ Failed to save API keys for user: {current_user.email}")
            raise HTTPException(
                status_code=500,
                detail=error_message
            )
            
    except HTTPException:
        raise
    except Exception as e:
        error_message = f"API anahtarları kaydedilirken beklenmeyen hata: {str(e)}"
        print(f"❌ Unexpected error saving API keys for user {current_user.email}: {error_message}")
        print(f"❌ Full error details: {repr(e)}")
        error_message = f"Bot başlatılırken beklenmeyen hata: {str(e)}"
        print(f"❌ Unexpected error starting bot for user {current_user.email}: {error_message}")
        print(f"❌ Full error details: {repr(e)}")
        raise HTTPException(
            status_code=500,
            detail=error_message
        )
