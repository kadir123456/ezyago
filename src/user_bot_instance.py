import asyncio
import json
import websockets
from datetime import datetime, timezone
from typing import Optional, Dict
import math
from .binance_client_multi import MultiBinanceClient
from .trading_strategy import trading_strategy
from .database import firebase_manager
from .models import TradeData
from .config import settings

class UserBotInstance:
    """
    Individual bot instance for a single user
    """
    def __init__(self, user_id: str, user_email: str, api_key: str, api_secret: str, is_testnet: bool = False):
        self.user_id = user_id
        self.user_email = user_email
        self.api_key = api_key
        self.api_secret = api_secret
        self.is_testnet = is_testnet
        
        # Bot state
        self.current_symbol: Optional[str] = None
        self.position_side: Optional[str] = None
        self.last_signal: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.is_active = False
        self.stop_requested = False
        
        # Trading data
        self.klines = []
        self.quantity_precision = 0
        self.price_precision = 0
        
        # Binance client
        self.binance_client: Optional[MultiBinanceClient] = None
        
        # WebSocket connection
        self.websocket_task: Optional[asyncio.Task] = None
        
        print(f"🤖 Bot instance created for user {user_email} ({'TESTNET' if is_testnet else 'LIVE'})")
    
    async def start(self, symbol: str) -> bool:
        """Start the bot for this user"""
        try:
            if self.is_active:
                print(f"⚠️ Bot already active for user {self.user_email}")
                return False
            
            self.current_symbol = symbol.upper()
            self.stop_requested = False
            self.started_at = datetime.utcnow()
            
            print(f"🚀 Starting bot for user {self.user_email} with symbol {self.current_symbol}")
            
            # Initialize Binance client
            self.binance_client = MultiBinanceClient(
                api_key=self.api_key,
                api_secret=self.api_secret,
                is_testnet=self.is_testnet
            )
            
            await self.binance_client.initialize()
            
            # Get symbol info and set precision
            symbol_info = await self.binance_client.get_symbol_info(self.current_symbol)
            if not symbol_info:
                print(f"❌ Symbol {self.current_symbol} not found for user {self.user_email}")
                return False
            
            self.quantity_precision = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
            self.price_precision = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
            
            # Set leverage
            if not await self.binance_client.set_leverage(self.current_symbol, settings.LEVERAGE):
                print(f"❌ Failed to set leverage for user {self.user_email}")
                return False
            
            # Get historical data
            self.klines = await self.binance_client.get_historical_klines(
                self.current_symbol, 
                settings.TIMEFRAME, 
                limit=50
            )
            
            if not self.klines:
                print(f"❌ Failed to get historical data for user {self.user_email}")
                return False
            
            # Start WebSocket connection
            self.websocket_task = asyncio.create_task(self._websocket_handler())
            self.is_active = True
            
            print(f"✅ Bot started successfully for user {self.user_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error starting bot for user {self.user_email}: {e}")
            await self._cleanup()
            return False
    
    async def stop(self):
        """Stop the bot for this user"""
        try:
            print(f"🛑 Stopping bot for user {self.user_email}")
            
            self.stop_requested = True
            self.is_active = False
            
            # Cancel WebSocket task
            if self.websocket_task and not self.websocket_task.done():
                self.websocket_task.cancel()
                try:
                    await self.websocket_task
                except asyncio.CancelledError:
                    pass
            
            await self._cleanup()
            print(f"✅ Bot stopped for user {self.user_email}")
            
        except Exception as e:
            print(f"❌ Error stopping bot for user {self.user_email}: {e}")
    
    async def _cleanup(self):
        """Clean up resources"""
        if self.binance_client:
            await self.binance_client.close()
            self.binance_client = None
        
        self.websocket_task = None
        self.is_active = False
    
    async def _websocket_handler(self):
        """Handle WebSocket connection for real-time data"""
        ws_url = f"{settings.BINANCE_WS_URL_LIVE if not self.is_testnet else settings.BINANCE_WS_URL_TEST}/ws/{self.current_symbol.lower()}@kline_{settings.TIMEFRAME}"
        
        while not self.stop_requested:
            try:
                print(f"🔌 Connecting to WebSocket for user {self.user_email}: {ws_url}")
                
                async with websockets.connect(ws_url, ping_interval=30, ping_timeout=15) as ws:
                    print(f"✅ WebSocket connected for user {self.user_email}")
                    
                    while not self.stop_requested:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=60.0)
                            await self._handle_websocket_message(message)
                            
                        except asyncio.TimeoutError:
                            print(f"⚠️ WebSocket timeout for user {self.user_email}")
                            break
                        except websockets.exceptions.ConnectionClosed:
                            print(f"⚠️ WebSocket connection closed for user {self.user_email}")
                            break
                            
            except Exception as e:
                if not self.stop_requested:
                    print(f"❌ WebSocket error for user {self.user_email}: {e}")
                    await asyncio.sleep(5)  # Wait before reconnecting
                else:
                    break
    
    async def _handle_websocket_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            # Only process closed candles
            if not data.get('k', {}).get('x', False):
                return
            
            kline = data['k']
            print(f"📊 New candle closed for {self.user_email}: {self.current_symbol} - Close: {kline['c']}")
            
            # Update klines data
            self.klines.pop(0)
            self.klines.append([
                kline['t'], kline['o'], kline['h'], kline['l'], 
                kline['c'], kline['v'], kline['T'], kline['q'], 
                kline['n'], kline['V'], kline['Q'], '0'
            ])
            
            # Check current position
            open_positions = await self.binance_client.get_open_positions(self.current_symbol)
            
            # Check if position was closed by stop loss
            if self.position_side is not None and not open_positions:
                print(f"🛑 Position closed by SL for user {self.user_email}")
                await self._log_trade_closure("CLOSED_BY_SL")
                self.position_side = None
            
            # Get new signal
            signal = trading_strategy.analyze_klines(self.klines)
            self.last_signal = signal
            
            print(f"📈 Signal for {self.user_email}: {signal}")
            
            # Execute trade if signal changed
            if signal != "HOLD" and signal != self.position_side:
                await self._execute_trade(signal)
                
        except Exception as e:
            print(f"❌ Error handling WebSocket message for user {self.user_email}: {e}")
    
    async def _execute_trade(self, new_signal: str):
        """Execute trade based on new signal"""
        try:
            print(f"🔄 Executing trade for user {self.user_email}: {new_signal}")
            
            # Close existing position if any
            open_positions = await self.binance_client.get_open_positions(self.current_symbol)
            if open_positions:
                position = open_positions[0]
                position_amt = float(position['positionAmt'])
                side_to_close = 'SELL' if position_amt > 0 else 'BUY'
                
                print(f"📤 Closing existing position for user {self.user_email}")
                await self._log_trade_closure("CLOSED_BY_FLIP")
                await self.binance_client.close_position(self.current_symbol, position_amt, side_to_close)
                await asyncio.sleep(1)  # Wait for position to close
            
            # Open new position
            side = "BUY" if new_signal == "LONG" else "SELL"
            price = await self.binance_client.get_market_price(self.current_symbol)
            
            if not price:
                print(f"❌ Failed to get market price for user {self.user_email}")
                return
            
            quantity = self._format_quantity((settings.ORDER_SIZE_USDT * settings.LEVERAGE) / price)
            
            if quantity <= 0:
                print(f"❌ Invalid quantity calculated for user {self.user_email}")
                return
            
            # Create market order with stop loss
            order = await self.binance_client.create_market_order_with_sl(
                self.current_symbol, side, quantity, price, self.price_precision
            )
            
            if order:
                self.position_side = new_signal
                print(f"✅ New {new_signal} position opened for user {self.user_email} at {price}")
                
                # Log trade opening
                await self._log_trade_opening(new_signal, price, quantity)
            else:
                print(f"❌ Failed to open position for user {self.user_email}")
                self.position_side = None
                
        except Exception as e:
            print(f"❌ Error executing trade for user {self.user_email}: {e}")
    
    async def _log_trade_opening(self, side: str, entry_price: float, quantity: float):
        """Log trade opening"""
        try:
            trade_data = TradeData(
                trade_id=f"{self.user_id}_{int(datetime.utcnow().timestamp())}",
                user_id=self.user_id,
                symbol=self.current_symbol,
                side=side,
                entry_price=entry_price,
                quantity=quantity,
                pnl=0.0,
                status="OPEN",
                entry_time=datetime.utcnow(),
                close_reason=""
            )
            
            await firebase_manager.log_trade(trade_data)
            
        except Exception as e:
            print(f"❌ Error logging trade opening for user {self.user_email}: {e}")
    
    async def _log_trade_closure(self, close_reason: str):
        """Log trade closure"""
        try:
            pnl = await self.binance_client.get_last_trade_pnl(self.current_symbol)
            
            # Create a simple trade log for closure
            trade_data = TradeData(
                trade_id=f"{self.user_id}_{int(datetime.utcnow().timestamp())}",
                user_id=self.user_id,
                symbol=self.current_symbol,
                side=self.position_side or "UNKNOWN",
                entry_price=0.0,  # We don't track this in current implementation
                quantity=0.0,     # We don't track this in current implementation
                pnl=pnl,
                status="CLOSED",
                entry_time=datetime.utcnow(),
                exit_time=datetime.utcnow(),
                close_reason=close_reason
            )
            
            await firebase_manager.log_trade(trade_data)
            
        except Exception as e:
            print(f"❌ Error logging trade closure for user {self.user_email}: {e}")
    
    def _get_precision_from_filter(self, symbol_info, filter_type, key):
        """Get precision from symbol filter"""
        for f in symbol_info['filters']:
            if f['filterType'] == filter_type:
                size_str = f[key]
                if '.' in size_str:
                    return len(size_str.split('.')[1].rstrip('0'))
                return 0
        return 0
    
    def _format_quantity(self, quantity: float):
        """Format quantity according to precision"""
        if self.quantity_precision == 0:
            return math.floor(quantity)
        factor = 10 ** self.quantity_precision
        return math.floor(quantity * factor) / factor
    
    def is_running(self) -> bool:
        """Check if bot is currently running"""
        return self.is_active and not self.stop_requested
    
    def get_uptime(self) -> int:
        """Get bot uptime in seconds"""
        if not self.started_at:
            return 0
        return int((datetime.utcnow() - self.started_at).total_seconds())
    
    async def get_status(self) -> Dict:
        """Get current bot status"""
        return {
            'status': 'running' if self.is_running() else 'stopped',
            'symbol': self.current_symbol,
            'position_side': self.position_side,
            'last_signal': self.last_signal,
            'uptime': self.get_uptime(),
            'message': f"Bot is {'running' if self.is_running() else 'stopped'} for {self.current_symbol}"
        }