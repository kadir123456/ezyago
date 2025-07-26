# GÜNCELLENMİŞ VE TAM database.py DOSYASI

import firebase_admin
from firebase_admin import credentials, db, auth
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from .config import settings
from .models import UserData, TradeData, PaymentRequest, SubscriptionStatus, BotStatus

class FirebaseManager:
    def __init__(self):
        self.db_ref = None
        self.initialized = False
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            if not firebase_admin._apps:
                if settings.FIREBASE_CREDENTIALS_JSON and settings.FIREBASE_DATABASE_URL:
                    cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred, {
                        'databaseURL': settings.FIREBASE_DATABASE_URL
                    })
                    print("✅ Firebase Admin SDK initialized successfully")
                else:
                    raise ValueError("Firebase credentials not found in environment variables")
            
            self.db_ref = db.reference()
            self.initialized = True
            
        except Exception as e:
            print(f"❌ Firebase initialization error: {e}")
            self.initialized = False
    
    def is_ready(self) -> bool:
        return self.initialized and self.db_ref is not None
    
    # --- User Management ---
    async def create_user(self, user_data: dict) -> bool:
        """Create a new user in the database from a dictionary."""
        try:
            if not self.is_ready(): return False
            self.db_ref.child('users').child(user_data['uid']).set(user_data)
            print(f"✅ User {user_data['email']} created successfully")
            return True
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return False

    async def get_user(self, uid: str) -> Optional[UserData]:
        """Get user data by UID and ensure bot settings have default values."""
        try:
            if not self.is_ready():
                return None
            
            user_ref = self.db_ref.child('users').child(uid)
            user_data = user_ref.get()
            
            if not user_data:
                return None
                
            # --- ÖNEMLİ GÜNCELLEME: EKSİK BOT AYARLARINI EKLEME ---
            if 'bot_order_size_usdt' not in user_data:
                user_data['bot_order_size_usdt'] = 25.0
            if 'bot_leverage' not in user_data:
                user_data['bot_leverage'] = 10
            if 'bot_stop_loss_percent' not in user_data:
                user_data['bot_stop_loss_percent'] = 4.0
            if 'bot_take_profit_percent' not in user_data:
                user_data['bot_take_profit_percent'] = 8.0
            if 'bot_timeframe' not in user_data:
                user_data['bot_timeframe'] = "15m"
            # ----------------------------------------------------

            for key, value in user_data.items():
                if key.endswith('_date') or key.endswith('_at') or key.endswith('_expires'):
                    if value and isinstance(value, str):
                        try:
                            user_data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except ValueError:
                            user_data[key] = datetime.fromisoformat(value)
            
            return UserData(**user_data)
            
        except Exception as e:
            print(f"❌ Error getting user {uid}: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[UserData]:
        """Get user data by email"""
        try:
            if not self.is_ready():
                return None
            
            users_ref = self.db_ref.child('users')
            users_data = users_ref.order_by_child('email').equal_to(email).get()
            
            if not users_data:
                return None
            
            uid = list(users_data.keys())[0]
            return await self.get_user(uid)
            
        except Exception as e:
            print(f"❌ Error getting user by email {email}: {e}")
            return None
    
    async def update_user(self, uid: str, updates: Dict[str, Any]) -> bool:
        """Update user data"""
        try:
            if not self.is_ready():
                return False
            
            for key, value in updates.items():
                if isinstance(value, datetime):
                    updates[key] = value.isoformat()
            
            self.db_ref.child('users').child(uid).update(updates)
            return True
            
        except Exception as e:
            print(f"❌ Error updating user {uid}: {e}")
            return False
    
    async def delete_user(self, uid: str) -> bool:
        """Delete user and all associated data"""
        try:
            if not self.is_ready(): return False
            auth.delete_user(uid)
            self.db_ref.child('users').child(uid).delete()
            self.db_ref.child('trades').child(uid).delete()
            payments = self.db_ref.child('payments').order_by_child('user_id').equal_to(uid).get()
            if payments:
                for payment_id in payments:
                    self.db_ref.child('payments').child(payment_id).delete()
            print(f"✅ User {uid} and all associated data deleted successfully.")
            return True
        except Exception as e:
            print(f"❌ Error deleting user {uid}: {e}")
            return False

    # --- Payment Management ---
    async def create_payment_request(self, payment_data: Dict[str, Any]) -> bool:
        """Create a payment request using a dictionary."""
        try:
            if not self.is_ready(): return False
            self.db_ref.child('payments').child(payment_data['payment_id']).set(payment_data)
            return True
        except Exception as e:
            print(f"❌ Error creating payment request: {e}")
            return False

    async def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get a single payment by its ID."""
        try:
            if not self.is_ready(): return None
            return self.db_ref.child('payments').child(payment_id).get()
        except Exception as e:
            print(f"❌ Error getting payment {payment_id}: {e}")
            return None

    async def update_payment(self, payment_id: str, updates: Dict[str, Any]) -> bool:
        """Update a payment record."""
        try:
            if not self.is_ready(): return False
            self.db_ref.child('payments').child(payment_id).update(updates)
            return True
        except Exception as e:
            print(f"❌ Error updating payment {payment_id}: {e}")
            return False
            
    # --- Admin Functions ---
    async def get_admin_stats(self) -> dict:
        """Get statistics for admin dashboard."""
        try:
            if not self.is_ready(): return {}
            
            all_users_raw = self.db_ref.child('users').get() or {}
            all_users = list(all_users_raw.values())
            
            pending_payments_raw = self.db_ref.child('payments').order_by_child('status').equal_to('pending').get() or {}
            pending_payments = list(pending_payments_raw.values())

            stats = {
                'total_users': len(all_users),
                'active_subscribers': len([u for u in all_users if u.get('subscription_status') == 'active']),
                'pending_payments': len(pending_payments),
                'active_bots': len([u for u in all_users if u.get('bot_status') == 'running']),
                'total_revenue': len([u for u in all_users if u.get('subscription_status') == 'active']) * settings.SUBSCRIPTION_PRICE_USDT
            }
            return stats
        except Exception as e:
            print(f"❌ Error getting admin stats: {e}")
            return {}

# Global instance
firebase_manager = FirebaseManager()
