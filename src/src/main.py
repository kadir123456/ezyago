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
