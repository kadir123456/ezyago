/* Reset and Base Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    /* Colors */
    --primary-color: #6366f1;
    --primary-dark: #4f46e5;
    --primary-light: #a5b4fc;
    --secondary-color: #10b981;
    --danger-color: #ef4444;
    --warning-color: #f59e0b;
    --info-color: #3b82f6;
    
    /* Backgrounds */
    --bg-primary: #ffffff;
    --bg-secondary: #f8fafc;
    --bg-tertiary: #f1f5f9;
    --bg-dark: #0f172a;
    --bg-card: #ffffff;
    
    /* Text Colors */
    --text-primary: #0f172a;
    --text-secondary: #64748b;
    --text-muted: #94a3b8;
    --text-white: #ffffff;
    
    /* Borders */
    --border-color: #e2e8f0;
    --border-light: #f1f5f9;
    
    /* Shadows */
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
    --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
    
    /* Spacing */
    --spacing-xs: 0.25rem;
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 1.5rem;
    --spacing-xl: 2rem;
    --spacing-2xl: 3rem;
    
<<<<<<< HEAD
    /* Border Radius */
    --radius-sm: 0.375rem;
    --radius-md: 0.5rem;
    --radius-lg: 0.75rem;
    --radius-xl: 1rem;
=======
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
        print(f"🔄 Registration request received for: {user_data.email}")
        
        # Validate input
        if not user_data.email or not user_data.password or not user_data.full_name:
            print(f"❌ Missing required fields for: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email, password, and full name are required"
            )
        
        # Validate password strength
        if len(user_data.password) < 6:
            print(f"❌ Password too short for: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        
        # Validate email format
        if "@" not in user_data.email or "." not in user_data.email:
            print(f"❌ Invalid email format: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please enter a valid email address"
            )
        
        # Check if user already exists
        existing_user = await firebase_manager.get_user_by_email(user_data.email)
        if existing_user:
            print(f"❌ User already exists: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Register new user
        print(f"🔄 Calling auth_manager.register_user for: {user_data.email}")
        new_user = await auth_manager.register_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            language=user_data.language
        )
        
        if not new_user:
            print(f"❌ Registration failed for: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user account. Please check your email and password."
            )
        
        # Create access token
        print(f"🔄 Creating access token for: {user_data.email}")
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
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
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
>>>>>>> 9f5158eeaf1884997cb70daa5e67dad8225b8e74
    
    /* Fonts */
    --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-size-xs: 0.75rem;
    --font-size-sm: 0.875rem;
    --font-size-base: 1rem;
    --font-size-lg: 1.125rem;
    --font-size-xl: 1.25rem;
    --font-size-2xl: 1.5rem;
    --font-size-3xl: 1.875rem;
    --font-size-4xl: 2.25rem;
    
    /* Transitions */
    --transition-fast: 150ms ease-in-out;
    --transition-normal: 300ms ease-in-out;
    --transition-slow: 500ms ease-in-out;
}

body {
    font-family: var(--font-family);
    font-size: var(--font-size-base);
    line-height: 1.6;
    color: var(--text-primary);
    background-color: var(--bg-primary);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Loading Screen */
.loading-screen {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: var(--bg-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.loading-spinner {
    text-align: center;
}

.spinner {
    width: 40px;
    height: 40px;
    border: 4px solid var(--border-color);
    border-top: 4px solid var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto var(--spacing-md);
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Utility Classes */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 var(--spacing-md);
}

.gradient-text {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }

.hidden { display: none !important; }
.visible { display: block !important; }

/* Buttons */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    transition: all var(--transition-fast);
    white-space: nowrap;
}

.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn-primary {
    background-color: var(--primary-color);
    color: var(--text-white);
    border-color: var(--primary-color);
}

.btn-primary:hover:not(:disabled) {
    background-color: var(--primary-dark);
    border-color: var(--primary-dark);
}

.btn-secondary {
    background-color: var(--secondary-color);
    color: var(--text-white);
    border-color: var(--secondary-color);
}

.btn-success {
    background-color: var(--secondary-color);
    color: var(--text-white);
    border-color: var(--secondary-color);
}

.btn-danger {
    background-color: var(--danger-color);
    color: var(--text-white);
    border-color: var(--danger-color);
}

.btn-outline {
    background-color: transparent;
    color: var(--primary-color);
    border-color: var(--primary-color);
}

.btn-outline:hover:not(:disabled) {
    background-color: var(--primary-color);
    color: var(--text-white);
}

.btn-sm {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: var(--font-size-xs);
}

.btn-large {
    padding: var(--spacing-md) var(--spacing-xl);
    font-size: var(--font-size-lg);
}

.btn-full {
    width: 100%;
}

/* Forms */
.form-group {
    margin-bottom: var(--spacing-lg);
}

.form-group label {
    display: block;
    margin-bottom: var(--spacing-sm);
    font-weight: 500;
    color: var(--text-primary);
}

.form-input {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
    transition: border-color var(--transition-fast);
}

.form-input:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgb(99 102 241 / 0.1);
}

.form-input:read-only {
    background-color: var(--bg-tertiary);
    color: var(--text-muted);
}

.form-help {
    display: block;
    margin-top: var(--spacing-xs);
    font-size: var(--font-size-sm);
    color: var(--text-muted);
}

.form-actions {
    display: flex;
    gap: var(--spacing-md);
    margin-top: var(--spacing-xl);
}

/* Checkbox */
.checkbox-label {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    cursor: pointer;
    font-weight: normal;
}

.checkbox-label input[type="checkbox"] {
    display: none;
}

.checkmark {
    width: 20px;
    height: 20px;
    border: 2px solid var(--border-color);
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all var(--transition-fast);
    flex-shrink: 0;
    margin-top: 2px;
}

.checkbox-label input[type="checkbox"]:checked + .checkmark {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
}

.checkbox-label input[type="checkbox"]:checked + .checkmark::after {
    content: '✓';
    color: white;
    font-size: var(--font-size-sm);
    font-weight: bold;
}

/* Cards */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
}

.card-header {
    padding: var(--spacing-lg);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.card-header h3 {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--text-primary);
}

.card-content {
    padding: var(--spacing-lg);
}

/* Navigation */
.navbar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border-light);
    z-index: 1000;
}

.nav-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 var(--spacing-md);
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 70px;
}

.nav-brand {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: var(--primary-color);
    text-decoration: none;
}

.nav-menu {
    display: flex;
    align-items: center;
    gap: var(--spacing-xl);
}

.nav-link {
    color: var(--text-secondary);
    text-decoration: none;
    font-weight: 500;
    transition: color var(--transition-fast);
}

.nav-link:hover {
    color: var(--primary-color);
}

.nav-toggle {
    display: none;
    flex-direction: column;
    gap: 4px;
    cursor: pointer;
}

.nav-toggle span {
    width: 25px;
    height: 3px;
    background: var(--text-primary);
    border-radius: 2px;
    transition: all var(--transition-fast);
}

/* Hero Section */
.hero {
    padding: 140px 0 80px;
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}

.hero-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 var(--spacing-md);
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-2xl);
    align-items: center;
}

.hero-title {
    font-size: var(--font-size-4xl);
    font-weight: 800;
    line-height: 1.2;
    margin-bottom: var(--spacing-lg);
    color: var(--text-primary);
}

.hero-subtitle {
    font-size: var(--font-size-xl);
    color: var(--text-secondary);
    margin-bottom: var(--spacing-2xl);
    line-height: 1.6;
}

.hero-stats {
    display: flex;
    gap: var(--spacing-xl);
    margin-bottom: var(--spacing-2xl);
}

.stat {
    text-align: center;
}

.stat-number {
    display: block;
    font-size: var(--font-size-2xl);
    font-weight: 700;
    color: var(--primary-color);
}

.stat-label {
    font-size: var(--font-size-sm);
    color: var(--text-muted);
}

.hero-actions {
    display: flex;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-xl);
}

.hero-notice {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: var(--font-size-sm);
    color: var(--text-muted);
}

.hero-visual {
    display: flex;
    justify-content: center;
}

.trading-card {
    background: var(--bg-card);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-xl);
    padding: var(--spacing-lg);
    width: 100%;
    max-width: 400px;
}

.trading-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-lg);
}

.trading-symbol {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--text-primary);
}

.trading-status {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: var(--font-size-sm);
    color: var(--secondary-color);
}

.trading-status.active i {
    color: var(--secondary-color);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.trading-chart {
    height: 200px;
    background: var(--bg-secondary);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-lg);
    display: flex;
    align-items: center;
    justify-content: center;
}

.trading-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--spacing-md);
}

.stat-item {
    text-align: center;
}

.stat-item .label {
    display: block;
    font-size: var(--font-size-xs);
    color: var(--text-muted);
    margin-bottom: var(--spacing-xs);
}

.stat-item .value {
    display: block;
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--text-primary);
}

.stat-item .value.success {
    color: var(--secondary-color);
}

.stat-item .value.profit {
    color: var(--secondary-color);
}

/* Features Section */
.features {
    padding: 80px 0;
    background: var(--bg-primary);
}

.section-header {
    text-align: center;
    margin-bottom: var(--spacing-2xl);
}

.section-header h2 {
    font-size: var(--font-size-3xl);
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: var(--spacing-md);
}

.section-header p {
    font-size: var(--font-size-lg);
    color: var(--text-secondary);
}

.features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: var(--spacing-xl);
}

.feature-card {
    text-align: center;
    padding: var(--spacing-xl);
    border-radius: var(--radius-lg);
    transition: transform var(--transition-normal);
}

.feature-card:hover {
    transform: translateY(-5px);
}

.feature-icon {
    width: 60px;
    height: 60px;
    background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
    border-radius: var(--radius-xl);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto var(--spacing-lg);
}

.feature-icon i {
    font-size: var(--font-size-xl);
    color: var(--text-white);
}

.feature-card h3 {
    font-size: var(--font-size-xl);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-md);
}

.feature-card p {
    color: var(--text-secondary);
    line-height: 1.6;
}

/* Pricing Section */
.pricing {
    padding: 80px 0;
    background: var(--bg-secondary);
}

.pricing-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: var(--spacing-xl);
    max-width: 800px;
    margin: 0 auto;
}

.pricing-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-xl);
    padding: var(--spacing-2xl);
    text-align: center;
    position: relative;
    transition: transform var(--transition-normal), box-shadow var(--transition-normal);
}

.pricing-card:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-xl);
}

.pricing-card.featured {
    border-color: var(--primary-color);
    box-shadow: var(--shadow-lg);
}

.pricing-badge {
    position: absolute;
    top: -12px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--primary-color);
    color: var(--text-white);
    padding: var(--spacing-xs) var(--spacing-md);
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
    font-weight: 500;
}

.pricing-header h3 {
    font-size: var(--font-size-xl);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-lg);
}

.price {
    display: flex;
    align-items: baseline;
    justify-content: center;
    margin-bottom: var(--spacing-xl);
}

.price .currency {
    font-size: var(--font-size-lg);
    color: var(--text-secondary);
}

.price .amount {
    font-size: 3rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 var(--spacing-xs);
}

.price .period {
    font-size: var(--font-size-lg);
    color: var(--text-secondary);
}

.pricing-features {
    list-style: none;
    margin-bottom: var(--spacing-xl);
}

.pricing-features li {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
    color: var(--text-secondary);
}

.pricing-features i {
    color: var(--secondary-color);
    font-size: var(--font-size-sm);
}

/* FAQ Section */
.faq {
    padding: 80px 0;
    background: var(--bg-primary);
}

.faq-list {
    max-width: 800px;
    margin: 0 auto;
}

.faq-item {
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    margin-bottom: var(--spacing-md);
    overflow: hidden;
}

.faq-question {
    padding: var(--spacing-lg);
    background: var(--bg-card);
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: background-color var(--transition-fast);
}

.faq-question:hover {
    background: var(--bg-secondary);
}

.faq-question h3 {
    font-size: var(--font-size-lg);
    font-weight: 500;
    color: var(--text-primary);
}

.faq-question i {
    color: var(--text-muted);
    transition: transform var(--transition-fast);
}

.faq-item.active .faq-question i {
    transform: rotate(180deg);
}

.faq-answer {
    padding: 0 var(--spacing-lg);
    max-height: 0;
    overflow: hidden;
    transition: all var(--transition-normal);
}

.faq-item.active .faq-answer {
    padding: var(--spacing-lg);
    max-height: 200px;
}

.faq-answer p {
    color: var(--text-secondary);
    line-height: 1.6;
}

/* Footer */
.footer {
    background: var(--bg-dark);
    color: var(--text-white);
    padding: 60px 0 30px;
}

.footer-content {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: var(--spacing-2xl);
    margin-bottom: var(--spacing-2xl);
}

.footer-brand .brand {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: var(--primary-light);
    margin-bottom: var(--spacing-md);
}

.footer-brand p {
    color: #94a3b8;
    line-height: 1.6;
}

.footer-links {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--spacing-xl);
}

.footer-section h4 {
    font-size: var(--font-size-lg);
    font-weight: 600;
    margin-bottom: var(--spacing-md);
    color: var(--text-white);
}

.footer-section a {
    display: block;
    color: #94a3b8;
    text-decoration: none;
    margin-bottom: var(--spacing-sm);
    transition: color var(--transition-fast);
}

.footer-section a:hover {
    color: var(--primary-light);
}

.footer-bottom {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: var(--spacing-xl);
    border-top: 1px solid #334155;
}

.footer-bottom p {
    color: #94a3b8;
}

.footer-social {
    display: flex;
    gap: var(--spacing-md);
}

.footer-social a {
    width: 40px;
    height: 40px;
    background: #334155;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    text-decoration: none;
    transition: all var(--transition-fast);
}

.footer-social a:hover {
    background: var(--primary-color);
    color: var(--text-white);
}

/* Dashboard */
.dashboard {
    display: flex;
    height: 100vh;
    background: var(--bg-secondary);
}

/* Sidebar */
.sidebar {
    width: 280px;
    background: var(--bg-card);
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
}

.sidebar-header {
    padding: var(--spacing-lg);
    border-bottom: 1px solid var(--border-color);
}

.sidebar-header .brand {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: var(--primary-color);
}

.sidebar-nav {
    flex: 1;
    padding: var(--spacing-lg) 0;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-md) var(--spacing-lg);
    color: var(--text-secondary);
    text-decoration: none;
    transition: all var(--transition-fast);
    border-left: 3px solid transparent;
}

.nav-item:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
}

.nav-item.active {
    background: var(--bg-secondary);
    color: var(--primary-color);
    border-left-color: var(--primary-color);
}

.nav-item i {
    width: 20px;
    text-align: center;
}

.sidebar-footer {
    padding: var(--spacing-lg);
    border-top: 1px solid var(--border-color);
}

/* Dashboard Main */
.dashboard-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.dashboard-header {
    background: var(--bg-card);
    border-bottom: 1px solid var(--border-color);
    padding: var(--spacing-lg) var(--spacing-xl);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.dashboard-header h1 {
    font-size: var(--font-size-2xl);
    font-weight: 600;
    color: var(--text-primary);
}

.user-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.user-avatar {
    width: 40px;
    height: 40px;
    background: var(--primary-color);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-white);
}

.user-details {
    display: flex;
    flex-direction: column;
}

.user-name {
    font-weight: 500;
    color: var(--text-primary);
}

.user-email {
    font-size: var(--font-size-sm);
    color: var(--text-muted);
}

.dashboard-content {
    flex: 1;
    padding: var(--spacing-xl);
    overflow-y: auto;
}

/* Pages */
.page {
    display: none;
}

.page.active {
    display: block;
}

/* Stats Grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-xl);
}

.stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.stat-icon {
    width: 50px;
    height: 50px;
    background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
    border-radius: var(--radius-lg);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-white);
}

.stat-content h3 {
    font-size: var(--font-size-xl);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-xs);
}

.stat-content p {
    font-size: var(--font-size-sm);
    color: var(--text-muted);
}

/* Cards Grid */
.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: var(--spacing-lg);
}

/* Status Indicator */
.status-indicator {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--danger-color);
}

.status-indicator.running .status-dot {
    background: var(--secondary-color);
    animation: pulse 2s infinite;
}

.status-text {
    font-size: var(--font-size-sm);
    font-weight: 500;
}

/* Bot Info */
.bot-info {
    display: grid;
    gap: var(--spacing-md);
}

.info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--border-light);
}

.info-item:last-child {
    border-bottom: none;
}

.info-item .label {
    font-weight: 500;
    color: var(--text-secondary);
}

.info-item .value {
    font-weight: 500;
    color: var(--text-primary);
}

/* Stats List */
.stats-list {
    display: grid;
    gap: var(--spacing-md);
}

.stat-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--border-light);
}

.stat-item:last-child {
    border-bottom: none;
}

.stat-item .label {
    font-weight: 500;
    color: var(--text-secondary);
}

.stat-item .value {
    font-weight: 500;
    color: var(--text-primary);
}

.stat-item .value.success {
    color: var(--secondary-color);
}

.stat-item .value.danger {
    color: var(--danger-color);
}

/* Bot Control */
.bot-control {
    display: grid;
    gap: var(--spacing-xl);
}

.control-section {
    display: grid;
    gap: var(--spacing-sm);
}

.control-buttons {
    display: flex;
    gap: var(--spacing-md);
}

.bot-settings {
    padding: var(--spacing-lg);
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
}

.bot-settings h4 {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-md);
}

.settings-form {
    display: grid;
    gap: var(--spacing-md);
}

.settings-row {
    display: flex;
    gap: var(--spacing-md);
}

.settings-row .form-group {
    flex: 1;
    margin-bottom: 0;
}

.settings-actions {
    display: flex;
    gap: var(--spacing-md);
    margin-top: var(--spacing-lg);
    padding-top: var(--spacing-lg);
    border-top: 1px solid var(--border-light);
}

/* IP Whitelist Section */
.ip-whitelist-section {
    margin-top: var(--spacing-xl);
    padding: var(--spacing-lg);
    background: #f0f9ff;
    border: 1px solid #0ea5e9;
    border-radius: var(--radius-lg);
}

.ip-whitelist-section h4 {
    color: #0369a1;
    margin-bottom: var(--spacing-md);
}

.ip-list {
    display: grid;
    gap: var(--spacing-sm);
    margin: var(--spacing-md) 0;
}

.ip-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm);
    background: var(--bg-card);
    border-radius: var(--radius-md);
    flex-direction: column;
    align-items: stretch;
}

.ip-item .ip-description {
    color: var(--text-muted);
    font-size: var(--font-size-xs);
    margin-top: var(--spacing-xs);
}

.ip-item code {
    flex: 1;
    font-family: 'Monaco', 'Menlo', monospace;
    font-weight: 600;
    color: var(--primary-color);
}

.api-guide-link {
    margin-top: var(--spacing-md);
    text-align: center;
}

/* API Keys Form */
.api-keys-form {
    display: grid;
    gap: var(--spacing-lg);
}

.api-help {
    margin-top: var(--spacing-xl);
    padding: var(--spacing-lg);
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
}

.api-help h4 {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-md);
}

.api-help ol {
    margin-bottom: var(--spacing-md);
    padding-left: var(--spacing-lg);
}

.api-help li {
    margin-bottom: var(--spacing-sm);
    color: var(--text-secondary);
}

.security-note {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
}

.security-note i {
    color: var(--secondary-color);
    margin-top: 2px;
}

.security-note span {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
}

/* Subscription */
.subscription-status {
    text-align: center;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-md) var(--spacing-lg);
    background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
    color: var(--text-white);
    border-radius: var(--radius-lg);
    font-weight: 600;
    margin-bottom: var(--spacing-lg);
}

.status-details {
    display: grid;
    gap: var(--spacing-md);
}

.detail-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--border-light);
}

.detail-item:last-child {
    border-bottom: none;
}

.detail-item .label {
    font-weight: 500;
    color: var(--text-secondary);
}

.detail-item .value {
    font-weight: 500;
    color: var(--text-primary);
}

/* Payment Info */
.payment-info {
    text-align: center;
}

.price-display {
    display: flex;
    align-items: baseline;
    justify-content: center;
    margin-bottom: var(--spacing-xl);
}

.price-display .currency {
    font-size: var(--font-size-lg);
    color: var(--text-secondary);
}

.price-display .amount {
    font-size: 3rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 var(--spacing-xs);
}

.price-display .period {
    font-size: var(--font-size-lg);
    color: var(--text-secondary);
}

.payment-details {
    margin-bottom: var(--spacing-xl);
}

.wallet-address {
    display: flex;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-sm);
}

.payment-actions {
    margin-bottom: var(--spacing-lg);
}

.payment-note {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
    background: #fef3c7;
    border: 1px solid #f59e0b;
    border-radius: var(--radius-md);
    text-align: left;
}

.payment-note i {
    color: #d97706;
    margin-top: 2px;
    flex-shrink: 0;
}

.payment-note span {
    font-size: var(--font-size-sm);
    color: #92400e;
}

/* Settings Form */
.settings-form {
    margin-bottom: var(--spacing-2xl);
}

.danger-zone {
    padding: var(--spacing-lg);
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: var(--radius-lg);
}

.danger-zone h4 {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--danger-color);
    margin-bottom: var(--spacing-sm);
}

.danger-zone p {
    color: var(--text-secondary);
    margin-bottom: var(--spacing-md);
}

/* Modals */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
    opacity: 0;
    visibility: hidden;
    transition: all var(--transition-normal);
}

.modal.active {
    opacity: 1;
    visibility: visible;
}

.modal-content {
    background: var(--bg-card);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-xl);
    width: 100%;
    max-width: 500px;
    max-height: 90vh;
    overflow-y: auto;
    transform: scale(0.9);
    transition: transform var(--transition-normal);
}

.modal.active .modal-content {
    transform: scale(1);
}

.modal-header {
    padding: var(--spacing-lg);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-header h3 {
    font-size: var(--font-size-xl);
    font-weight: 600;
    color: var(--text-primary);
}

.modal-close {
    width: 32px;
    height: 32px;
    border: none;
    background: none;
    color: var(--text-muted);
    cursor: pointer;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all var(--transition-fast);
}

.modal-close:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
}

.modal-body {
    padding: var(--spacing-lg);
}

.modal-footer {
    text-align: center;
    margin-top: var(--spacing-lg);
    padding-top: var(--spacing-lg);
    border-top: 1px solid var(--border-light);
}

.modal-footer a {
    color: var(--primary-color);
    text-decoration: none;
    font-weight: 500;
}

.modal-footer a:hover {
    text-decoration: underline;
}

/* Notifications */
.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    padding: var(--spacing-md) var(--spacing-lg);
    z-index: 3000;
    transform: translateX(400px);
    transition: transform var(--transition-normal);
}

.notification.show {
    transform: translateX(0);
}

.notification-content {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.notification-icon {
    font-size: var(--font-size-lg);
}

.notification.success .notification-icon {
    color: var(--secondary-color);
}

.notification.error .notification-icon {
    color: var(--danger-color);
}

.notification.info .notification-icon {
    color: var(--info-color);
}

.notification-message {
    font-weight: 500;
    color: var(--text-primary);
}

/* Responsive Design */
@media (max-width: 1024px) {
    .container {
        padding: 0 var(--spacing-md);
    }
<<<<<<< HEAD
=======

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
        "network": "TRC-20",
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
>>>>>>> 9f5158eeaf1884997cb70daa5e67dad8225b8e74
    
    .hero-container {
        grid-template-columns: 1fr;
        text-align: center;
    }
    
    .hero-visual {
        order: -1;
    }
    
    .features-grid {
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    }
    
    .cards-grid {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 768px) {
    .container {
        padding: 0 var(--spacing-sm);
    }
    
    .nav-menu {
        display: none;
    }
    
    .nav-toggle {
        display: flex;
    }
    
    .navbar {
        padding: 0 var(--spacing-sm);
    }
    
    .nav-container {
        padding: 0;
    }
    
    .hero {
        padding: 120px 0 60px;
    }
    
    .hero-title {
        font-size: var(--font-size-3xl);
    }
    
    .hero-actions {
        flex-direction: column;
    }
    
    .hero-stats {
        justify-content: center;
    }
    
    .features,
    .pricing,
    .faq {
        padding: 60px 0;
    }
    
    .footer-content {
        grid-template-columns: 1fr;
        text-align: center;
    }
    
    .footer-links {
        grid-template-columns: 1fr;
        gap: var(--spacing-lg);
    }
    
    .footer-bottom {
        flex-direction: column;
        gap: var(--spacing-md);
        text-align: center;
    }
    
    .dashboard {
        flex-direction: column;
    }
    
    .sidebar {
        width: 100%;
        height: auto;
    }
    
    .sidebar-nav {
        display: flex;
        overflow-x: auto;
        padding: var(--spacing-md);
    }
    
    .nav-item {
        white-space: nowrap;
        border-left: none;
        border-bottom: 3px solid transparent;
    }
    
    .nav-item.active {
        border-left: none;
        border-bottom-color: var(--primary-color);
    }
    
    .dashboard-header {
        flex-direction: column;
        gap: var(--spacing-md);
        text-align: center;
    }
    
    .stats-grid {
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    }
    
    .control-buttons {
        flex-direction: column;
    }
    
    .settings-row {
        flex-direction: column;
    }
    
    .settings-actions {
        flex-direction: column;
    }
    
    .ip-item {
        flex-direction: column;
        align-items: stretch;
        text-align: center;
    }
    
    .form-actions {
        flex-direction: column;
    }
    
    .modal-content {
        margin: var(--spacing-md);
        max-width: none;
    }
}

@media (max-width: 480px) {
    .container {
        padding: 0 var(--spacing-xs);
    }
    
    .navbar {
        padding: 0 var(--spacing-xs);
    }
    
    .hero-title {
        font-size: var(--font-size-2xl);
    }
    
    .hero-subtitle {
        font-size: var(--font-size-lg);
    }
    
    .hero-stats {
        flex-direction: column;
        gap: var(--spacing-md);
    }
    
    .features-grid {
        grid-template-columns: 1fr;
    }
    
    .feature-card {
        padding: var(--spacing-lg);
    }
    
    .pricing-cards {
        grid-template-columns: 1fr;
    }
    
    .dashboard-content {
        padding: var(--spacing-md);
    }
    
    .stats-grid {
        grid-template-columns: 1fr;
    }
    
    .settings-grid {
        grid-template-columns: 1fr;
    }
    
    .wallet-address {
        flex-direction: column;
    }
}