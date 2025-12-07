"""
Database Handler
Manages SQLite database for storing signals, users, and training data
"""

import os
import sqlite3
import aiosqlite
from datetime import datetime
from typing import Dict, List, Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class Database:
    """Database manager for bot data"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialized = False
        
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
        
    async def initialize(self):
        """Initialize database tables"""
        if self._initialized:
            return
            
        try:
            # Ensure the database file can be created
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            async with aiosqlite.connect(self.db_path) as db:
                # Users table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        subscribed BOOLEAN DEFAULT 1,
                        subscription_date TIMESTAMP,
                        last_activity TIMESTAMP
                    )
                ''')
                
                # Signals table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        entry_type TEXT,
                        entry_price REAL,
                        stop_loss REAL,
                        take_profit REAL,
                        sl_pips REAL,
                        tp_pips REAL,
                        risk_reward REAL,
                        setup_type TEXT,
                        signal_strength TEXT,
                        ml_confidence REAL,
                        timestamp TIMESTAMP,
                        current_price REAL,
                        volatility TEXT,
                        trend TEXT,
                        atr REAL,
                        rsi REAL,
                        market_bias TEXT,
                        outcome TEXT,
                        profit_loss REAL,
                        closed_at TIMESTAMP
                    )
                ''')
                
                # Training metrics table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS training_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP,
                        samples INTEGER,
                        accuracy REAL,
                        precision REAL,
                        recall REAL
                    )
                ''')
                
                await db.commit()
                
            self._initialized = True
            logger.info(f"Database initialized successfully at: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)
            raise
    
    async def subscribe_user(self, user_id: int, username: str):
        """Subscribe a user"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, subscribed, subscription_date, last_activity)
                    VALUES (?, ?, 1, ?, ?)
                ''', (user_id, username, datetime.now(), datetime.now()))
                await db.commit()
                logger.info(f"User {user_id} subscribed")
                
        except Exception as e:
            logger.error(f"Error subscribing user: {e}")
    
    async def unsubscribe_user(self, user_id: int):
        """Unsubscribe a user"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    UPDATE users SET subscribed = 0, last_activity = ?
                    WHERE user_id = ?
                ''', (datetime.now(), user_id))
                await db.commit()
                logger.info(f"User {user_id} unsubscribed")
                
        except Exception as e:
            logger.error(f"Error unsubscribing user: {e}")
    
    async def is_user_subscribed(self, user_id: int) -> bool:
        """Check if user is subscribed"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT subscribed FROM users WHERE user_id = ?
                ''', (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return bool(row[0]) if row else False
                    
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            return False
    
    async def get_subscription_date(self, user_id: int) -> Optional[datetime]:
        """Get user subscription date"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT subscription_date FROM users WHERE user_id = ?
                ''', (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        return datetime.fromisoformat(row[0])
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting subscription date: {e}")
            return None
    
    async def get_subscribers(self) -> List[Dict]:
        """Get all subscribed users"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT user_id, username FROM users WHERE subscribed = 1
                ''') as cursor:
                    rows = await cursor.fetchall()
                    return [{'user_id': row[0], 'username': row[1]} for row in rows]
                    
        except Exception as e:
            logger.error(f"Error getting subscribers: {e}")
            return []
    
    async def get_subscriber_count(self) -> int:
        """Get count of subscribed users"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT COUNT(*) FROM users WHERE subscribed = 1
                ''') as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
                    
        except Exception as e:
            logger.error(f"Error getting subscriber count: {e}")
            return 0
    
    async def insert_signal(self, signal: Dict) -> int:
        """Insert a new signal"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    INSERT INTO signals (
                        symbol, direction, entry_type, entry_price, stop_loss, take_profit,
                        sl_pips, tp_pips, risk_reward, setup_type, signal_strength,
                        ml_confidence, timestamp, current_price, volatility, trend,
                        atr, rsi, market_bias
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal['symbol'], signal['direction'], signal['entry_type'],
                    signal['entry_price'], signal['stop_loss'], signal['take_profit'],
                    signal['sl_pips'], signal['tp_pips'], signal['risk_reward'],
                    signal['setup_type'], signal['signal_strength'], signal['ml_confidence'],
                    signal['timestamp'], signal['current_price'], signal['volatility'],
                    signal['trend'], signal['atr'], signal['rsi'], signal['market_bias']
                ))
                await db.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error inserting signal: {e}", exc_info=True)
            return 0
    
    async def update_signal_outcome(self, signal_id: int, outcome: str, profit_loss: float):
        """Update signal with outcome"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    UPDATE signals
                    SET outcome = ?, profit_loss = ?, closed_at = ?
                    WHERE id = ?
                ''', (outcome, profit_loss, datetime.now(), signal_id))
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error updating signal outcome: {e}")
    
    async def get_signal_count(self) -> int:
        """Get total signal count"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT COUNT(*) FROM signals') as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
                    
        except Exception as e:
            logger.error(f"Error getting signal count: {e}")
            return 0
    
    async def get_all_signals_with_outcomes(self) -> List[Dict]:
        """Get all signals that have outcomes"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('''
                    SELECT * FROM signals WHERE outcome IS NOT NULL
                ''') as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error(f"Error getting signals with outcomes: {e}")
            return []
    
    async def get_win_rate(self) -> float:
        """Calculate win rate"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins
                    FROM signals
                    WHERE outcome IS NOT NULL
                ''') as cursor:
                    row = await cursor.fetchone()
                    if row and row[0] > 0:
                        return (row[1] / row[0]) * 100
                    return 0.0
                    
        except Exception as e:
            logger.error(f"Error calculating win rate: {e}")
            return 0.0
    
    async def get_average_rr(self) -> float:
        """Get average risk:reward ratio"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT AVG(risk_reward) FROM signals
                ''') as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row and row[0] else 3.0
                    
        except Exception as e:
            logger.error(f"Error getting average R:R: {e}")
            return 3.0
    
    async def store_training_metrics(self, metrics: Dict):
        """Store ML training metrics"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO training_metrics (timestamp, samples, accuracy, precision, recall)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    metrics['timestamp'], metrics['samples'], metrics['accuracy'],
                    metrics['precision'], metrics['recall']
                ))
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error storing training metrics: {e}")
    
    async def get_latest_training_metrics(self) -> Optional[Dict]:
        """Get latest training metrics"""
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('''
                    SELECT * FROM training_metrics
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''') as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
                    
        except Exception as e:
            logger.error(f"Error getting training metrics: {e}")
            return None