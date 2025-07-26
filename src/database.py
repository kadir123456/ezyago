import firebase_admin
from firebase_admin import credentials, db, auth
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from .config import settings
from .models import UserData, TradeData, PaymentRequest, SubscriptionStatus, BotStatus
import uuid

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
    async def create_user(self, user_data: UserData) -> bool:
        """Create a new user in the database"""
        try:
            if not self.is_ready():
                print("❌ Firebase not ready for user creation")
                return False
            
            if user_data.email == settings.ADMIN_EMAIL:
                from .models import UserRole
                user_data.role = UserRole.ADMIN
                print(f"✅ Creating admin user: {user_data.email}")
            
            now_aware = datetime.now(timezone.utc)
            user_data.trial_end_date = now_aware + timedelta(days=settings.TRIAL_DAYS)
            user_data.created_at = now_aware
            
            user_dict = user_data.dict()
            for key, value in user_dict.items():
                if isinstance(value, datetime):
                    user_dict[key] = value.isoformat()
            
            self.db_ref.child('users').child(user_data.uid).set(user_dict)
            print(f"✅ User {user_data.email} created successfully")
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
            
            # --- ANA DÜZELTME: EKSİK BOT AYARLARINI EKLEME ---
            default_settings = {
                'bot_order_size_usdt': 25.0, 'bot_leverage': 10,
                'bot_stop_loss_percent': 4.0, 'bot_take_profit_percent': 8.0,
                'bot_timeframe': "15m"
            }
            for key, value in default_settings.items():
                if key not in user_data:
                    user_data[key] = value
            # ----------------------------------------------------

            for key, value in user_data.items():
                if key.endswith(('_date', '_at', '_expires')) and value and isinstance(value, str):
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
            if not self.is_ready():
                return False
            
            auth.delete_user(uid)
            self.db_ref.child('users').child(uid).delete()
            self.db_ref.child('trades').child(uid).delete()
            
            payments_ref = self.db_ref.child('payments')
            payments = payments_ref.order_by_child('user_id').equal_to(uid).get()
            if payments:
                for payment_id in payments.keys():
                    payments_ref.child(payment_id).delete()
            
            print(f"✅ User {uid} and all associated data deleted")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting user {uid}: {e}")
            return False
    
    # --- Subscription Management ---
    async def extend_subscription(self, uid: str, days: int) -> bool:
        """Extend user subscription"""
        try:
            user = await self.get_user(uid)
            if not user:
                return False
            
            now_aware = datetime.now(timezone.utc)
            
            if user.subscription_end_date and user.subscription_end_date > now_aware:
                new_end_date = user.subscription_end_date + timedelta(days=days)
            else:
                new_end_date = now_aware + timedelta(days=days)
            
            updates = {
                'subscription_status': SubscriptionStatus.ACTIVE.value,
                'subscription_end_date': new_end_date.isoformat()
            }
            
            return await self.update_user(uid, updates)
            
        except Exception as e:
            print(f"❌ Error extending subscription for {uid}: {e}")
            return False
    
    async def check_expired_subscriptions(self) -> List[str]:
        """Check and update expired subscriptions"""
        try:
            if not self.is_ready():
                return []
            
            now_aware = datetime.now(timezone.utc)
            expired_users = []
            
            users_ref = self.db_ref.child('users')
            users_data = users_ref.get()
            
            if not users_data:
                return []
            
            for uid, user_data in users_data.items():
                status = user_data.get('subscription_status')
                end_date_str = None
                
                if status == SubscriptionStatus.TRIAL.value:
                    end_date_str = user_data.get('trial_end_date')
                elif status == SubscriptionStatus.ACTIVE.value:
                    end_date_str = user_data.get('subscription_end_date')
                
                if end_date_str:
                    end_date_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    if end_date_dt <= now_aware:
                        await self.update_user(uid, {
                            'subscription_status': SubscriptionStatus.EXPIRED.value,
                            'bot_status': BotStatus.STOPPED.value
                        })
                        expired_users.append(uid)
            
            return expired_users
            
        except Exception as e:
            print(f"❌ Error checking expired subscriptions: {e}")
            return []
    
    # --- Trading Data ---
    async def log_trade(self, trade_data: TradeData) -> bool:
        """Log a trade to the database"""
        try:
            if not self.is_ready():
                return False
            
            trade_dict = trade_data.dict()
            for key, value in trade_dict.items():
                if isinstance(value, datetime):
                    trade_dict[key] = value.isoformat()
            
            self.db_ref.child('trades').child(trade_data.user_id).child(trade_data.trade_id).set(trade_dict)
            await self._update_user_stats(trade_data.user_id, trade_data)
            return True
            
        except Exception as e:
            print(f"❌ Error logging trade: {e}")
            return False
    
    async def _update_user_stats(self, uid: str, trade_data: TradeData):
        """Update user trading statistics"""
        try:
            user = await self.get_user(uid)
            if not user:
                return
            
            if trade_data.status == "CLOSED":
                updates = {
                    'total_trades': user.total_trades + 1,
                    'total_pnl': user.total_pnl + trade_data.pnl
                }
                
                if trade_data.pnl > 0:
                    updates['winning_trades'] = user.winning_trades + 1
                else:
                    updates['losing_trades'] = user.losing_trades + 1
                
                await self.update_user(uid, updates)
                print(f"📊 User stats updated for {uid}: Total PnL: ${user.total_pnl + trade_data.pnl:.2f}")
            
        except Exception as e:
            print(f"❌ Error updating user stats for {uid}: {e}")
    
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

    async def get_pending_payments(self) -> List[Dict[str, Any]]:
        """Get all pending payment requests"""
        try:
            if not self.is_ready(): return []
            payments_ref = self.db_ref.child('payments')
            payments_data = payments_ref.order_by_child('status').equal_to('pending').get()
            return list(payments_data.values()) if payments_data else []
        except Exception as e:
            print(f"❌ Error getting pending payments: {e}")
            return []
    
    # approve_payment fonksiyonu main.py içinde olduğu için buradan kaldırıldı.
    # Bu, sorumlulukların ayrılması prensibine daha uygundur.
    
    # --- Admin Functions ---
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users for admin panel"""
        try:
            if not self.is_ready(): return []
            users_data = self.db_ref.child('users').get()
            return list(users_data.values()) if users_data else []
        except Exception as e:
            print(f"❌ Error getting all users: {e}")
            return []
    
    async def get_admin_stats(self) -> Dict[str, Any]:
        """Get statistics for admin dashboard"""
        try:
            if not self.is_ready(): return {}
            
            all_users = await self.get_all_users()
            pending_payments = await self.get_pending_payments()
            
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
    
    # --- IP Whitelist Management (Mevcut kodunuzu koruyoruz) ---
    async def create_ip_whitelist_entry(self, entry: 'IPWhitelistEntry') -> bool:
        """Create IP whitelist entry"""
        try:
            if not self.is_ready():
                return False
            
            entry_dict = entry.dict()
            for key, value in entry_dict.items():
                if isinstance(value, datetime):
                    entry_dict[key] = value.isoformat()
            
            self.db_ref.child('ip_whitelist').child(entry.ip_address.replace('.', '_')).set(entry_dict)
            return True
            
        except Exception as e:
            print(f"❌ Error creating IP whitelist entry: {e}")
            return False
    
    async def get_ip_whitelist(self) -> List[Dict[str, Any]]:
        """Get all IP whitelist entries"""
        try:
            if not self.is_ready():
                return []
            
            whitelist_ref = self.db_ref.child('ip_whitelist')
            whitelist_data = whitelist_ref.get()
            
            if not whitelist_data:
                return []
            
            entries = []
            for ip_key, entry_data in whitelist_data.items():
                for key, value in entry_data.items():
                    if key.endswith('_at'):
                        if value:
                            entry_data[key] = datetime.fromisoformat(value)
                
                entries.append(entry_data)
            
            return entries
            
        except Exception as e:
            print(f"❌ Error getting IP whitelist: {e}")
            return []
    
    async def update_ip_whitelist_entry(self, ip_address: str, updates: Dict[str, Any]) -> bool:
        """Update IP whitelist entry"""
        try:
            if not self.is_ready():
                return False
            
            ip_key = ip_address.replace('.', '_')
            self.db_ref.child('ip_whitelist').child(ip_key).update(updates)
            return True
            
        except Exception as e:
            print(f"❌ Error updating IP whitelist entry: {e}")
            return False
    
    async def delete_ip_whitelist_entry(self, ip_address: str) -> bool:
        """Delete IP whitelist entry"""
        try:
            if not self.is_ready():
                return False
            
            ip_key = ip_address.replace('.', '_')
            self.db_ref.child('ip_whitelist').child(ip_key).delete()
            return True
            
        except Exception as e:
            print(f"❌ Error deleting IP whitelist entry: {e}")
            return False

# Global instance
firebase_manager = FirebaseManager()
