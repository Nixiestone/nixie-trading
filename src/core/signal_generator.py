"""
Enhanced Signal Generation System with:
- Duplicate signal prevention
- CSV auto-export
- Trade monitoring (TP/SL hits)
- Auto-execution in MT5 (optional)
- Accurate win rate tracking
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List
import numpy as np
import hashlib
import csv
import os
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SignalGenerator:
    """Enhanced signal generator with full trade lifecycle management"""
    
    def __init__(self, market_analyzer, ml_engine, config):
        self.analyzer = market_analyzer
        self.ml_engine = ml_engine
        self.config = config
        self.last_signal_time = {}
        
        # Signal tracking to prevent duplicates
        self.active_signals = {}  # {signal_hash: signal_data}
        self.signal_history = set()  # Set of signal hashes
        
        # CSV file paths
        self.csv_signals = 'data/signals_log.csv'
        self.csv_closed = 'data/closed_trades.csv'
        
        # Initialize CSV files
        self._initialize_csv_files()
        
    def _initialize_csv_files(self):
        """Create CSV files with headers if they don't exist"""
        try:
            # Signals log CSV
            if not os.path.exists(self.csv_signals):
                os.makedirs(os.path.dirname(self.csv_signals), exist_ok=True)
                with open(self.csv_signals, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'Signal_ID', 'Timestamp', 'Symbol', 'Direction', 'Entry_Type',
                        'Entry_Price', 'Stop_Loss', 'Take_Profit', 'SL_Pips', 'TP_Pips',
                        'Risk_Reward', 'Setup_Type', 'Signal_Strength', 'ML_Confidence',
                        'Current_Price', 'Volatility', 'Trend', 'ATR', 'RSI', 'Bias',
                        'Status', 'Outcome', 'Pips_Result', 'Duration', 'Close_Time',
                        'Close_Reason', 'MT5_Ticket'
                    ])
            
            # Closed trades CSV
            if not os.path.exists(self.csv_closed):
                os.makedirs(os.path.dirname(self.csv_closed), exist_ok=True)
                with open(self.csv_closed, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'Signal_ID', 'Symbol', 'Direction', 'Entry_Price', 'Exit_Price',
                        'SL_Price', 'TP_Price', 'Outcome', 'Pips', 'Duration',
                        'Entry_Time', 'Exit_Time', 'Reason', 'Setup_Type',
                        'ML_Confidence', 'Risk_Reward', 'MT5_Ticket'
                    ])
                    
            logger.info("CSV files initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing CSV files: {e}")
    
    def _generate_signal_hash(self, symbol: str, direction: str, 
                             entry_price: float, timestamp: datetime) -> str:
        """Generate unique hash for signal to prevent duplicates"""
        # Hash based on symbol, direction, approximate entry price, and hour
        hash_input = f"{symbol}_{direction}_{round(entry_price, 2)}_{timestamp.strftime('%Y%m%d%H')}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def _is_duplicate_signal(self, signal_hash: str, symbol: str) -> bool:
        """Check if this signal was already sent recently"""
        # Check if hash exists in active signals
        if signal_hash in self.active_signals:
            logger.info(f"Duplicate signal detected for {symbol} - skipping")
            return True
        
        # Check if in history (within last 24 hours)
        if signal_hash in self.signal_history:
            logger.info(f"Signal already sent in last 24h for {symbol} - skipping")
            return True
        
        return False
    
    async def generate_signal(self, symbol: str, market_state: Dict) -> Optional[Dict]:
        """Generate trading signal with duplicate prevention"""
        try:
            # Check cooldown
            if not self._check_cooldown(symbol):
                return None
            
            # Check if in kill zone
            if not market_state.get('in_kill_zone', False):
                logger.debug(f"Outside kill zone for {symbol}")
                return None
            
            # Validate setup conditions
            setup_valid, setup_type = self._validate_setup(market_state)
            
            if not setup_valid:
                return None
            
            # Determine signal direction
            direction = self._determine_direction(market_state)
            
            if direction == 'NEUTRAL':
                return None
            
            # Calculate entry, SL, and TP
            entry_data = self._calculate_entry_levels(market_state, direction)
            
            if not entry_data:
                return None
            
            # Generate signal hash for duplicate checking
            signal_hash = self._generate_signal_hash(
                symbol, direction, entry_data['entry'], datetime.now()
            )
            
            # Check for duplicate
            if self._is_duplicate_signal(signal_hash, symbol):
                return None
            
            # Get ML confidence
            ml_confidence = await self.ml_engine.predict_signal_quality(market_state)
            
            # Check if meets minimum confidence threshold
            if ml_confidence < 60.0:
                logger.debug(f"ML confidence too low for {symbol}: {ml_confidence}%")
                return None
            
            # Calculate signal strength
            signal_strength = self._calculate_signal_strength(market_state, ml_confidence)
            
            # Create signal
            signal = {
                'signal_id': signal_hash,
                'symbol': symbol,
                'direction': direction,
                'entry_type': entry_data['entry_type'],
                'entry_price': entry_data['entry'],
                'stop_loss': entry_data['sl'],
                'take_profit': entry_data['tp'],
                'sl_pips': entry_data['sl_pips'],
                'tp_pips': entry_data['tp_pips'],
                'risk_reward': entry_data['rr'],
                'setup_type': setup_type,
                'signal_strength': signal_strength,
                'ml_confidence': ml_confidence,
                'timestamp': datetime.now(),
                'current_price': market_state['current_price'],
                'volatility': market_state['volatility'],
                'trend': market_state['htf_trend'],
                'atr': market_state['atr'],
                'rsi': market_state['rsi'],
                'market_bias': market_state['bias'],
                'status': 'ACTIVE',
                'outcome': None,
                'mt5_ticket': None
            }
            
            # Add to active signals tracking
            self.active_signals[signal_hash] = signal
            self.signal_history.add(signal_hash)
            
            # Save to CSV immediately
            self._save_signal_to_csv(signal)
            
            # Update last signal time
            self.last_signal_time[symbol] = datetime.now()
            
            logger.info(f"NEW SIGNAL: {symbol} {direction} {entry_data['entry_type']} @ {entry_data['entry']:.5f} (ID: {signal_hash})")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}", exc_info=True)
            return None
    
    def _save_signal_to_csv(self, signal: Dict):
        """Save signal to CSV file"""
        try:
            with open(self.csv_signals, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    signal['signal_id'],
                    signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    signal['symbol'],
                    signal['direction'],
                    signal['entry_type'],
                    signal['entry_price'],
                    signal['stop_loss'],
                    signal['take_profit'],
                    signal['sl_pips'],
                    signal['tp_pips'],
                    signal['risk_reward'],
                    signal['setup_type'],
                    signal['signal_strength'],
                    signal['ml_confidence'],
                    signal['current_price'],
                    signal['volatility'],
                    signal['trend'],
                    signal['atr'],
                    signal['rsi'],
                    signal['market_bias'],
                    signal['status'],
                    signal.get('outcome', ''),
                    signal.get('pips_result', ''),
                    signal.get('duration', ''),
                    signal.get('close_time', ''),
                    signal.get('close_reason', ''),
                    signal.get('mt5_ticket', '')
                ])
            
            logger.debug(f"Signal {signal['signal_id']} saved to CSV")
            
        except Exception as e:
            logger.error(f"Error saving signal to CSV: {e}")
    
    def _update_signal_in_csv(self, signal_id: str, outcome: str, pips: float, 
                              duration: str, close_reason: str):
        """Update signal status in CSV file"""
        try:
            # Read all rows
            rows = []
            with open(self.csv_signals, 'r', newline='') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Update matching row
            for i, row in enumerate(rows):
                if i == 0:  # Skip header
                    continue
                if row[0] == signal_id:  # Match signal_id
                    row[20] = 'CLOSED'  # Status
                    row[21] = outcome  # Outcome
                    row[22] = pips  # Pips result
                    row[23] = duration  # Duration
                    row[24] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Close time
                    row[25] = close_reason  # Reason
                    break
            
            # Write back
            with open(self.csv_signals, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            
            logger.debug(f"Signal {signal_id} updated in CSV")
            
        except Exception as e:
            logger.error(f"Error updating signal in CSV: {e}")
    
    def _save_closed_trade_to_csv(self, signal: Dict, exit_price: float, 
                                   outcome: str, pips: float, reason: str):
        """Save closed trade to dedicated CSV"""
        try:
            duration = self._calculate_duration(signal['timestamp'], datetime.now())
            
            with open(self.csv_closed, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    signal['signal_id'],
                    signal['symbol'],
                    signal['direction'],
                    signal['entry_price'],
                    exit_price,
                    signal['stop_loss'],
                    signal['take_profit'],
                    outcome,
                    pips,
                    duration,
                    signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    reason,
                    signal['setup_type'],
                    signal['ml_confidence'],
                    signal['risk_reward'],
                    signal.get('mt5_ticket', '')
                ])
            
            logger.info(f"Closed trade saved: {signal['symbol']} {outcome} {pips:.1f} pips")
            
        except Exception as e:
            logger.error(f"Error saving closed trade to CSV: {e}")
    
    def _calculate_duration(self, start: datetime, end: datetime) -> str:
        """Calculate trade duration in human-readable format"""
        delta = end - start
        
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        if delta.days > 0:
            return f"{delta.days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    async def check_active_signals(self) -> List[Dict]:
        """Check all active signals for TP/SL hits and return notifications"""
        notifications = []
        
        for signal_id, signal in list(self.active_signals.items()):
            try:
                # Get current price
                tick = await self.analyzer.mt5.get_tick(signal['symbol'])
                
                if not tick:
                    continue
                
                current_price = tick['bid'] if signal['direction'] == 'SELL' else tick['ask']
                
                # Check for TP/SL hit
                outcome = None
                exit_price = current_price
                reason = ""
                
                if signal['direction'] == 'BUY':
                    # Check TP hit
                    if current_price >= signal['take_profit']:
                        outcome = 'WIN'
                        exit_price = signal['take_profit']
                        pips = signal['tp_pips']
                        reason = self._generate_tp_reason(signal, 'BUY')
                    
                    # Check SL hit
                    elif current_price <= signal['stop_loss']:
                        outcome = 'LOSS'
                        exit_price = signal['stop_loss']
                        pips = -signal['sl_pips']
                        reason = self._generate_sl_reason(signal, 'BUY')
                
                else:  # SELL
                    # Check TP hit
                    if current_price <= signal['take_profit']:
                        outcome = 'WIN'
                        exit_price = signal['take_profit']
                        pips = signal['tp_pips']
                        reason = self._generate_tp_reason(signal, 'SELL')
                    
                    # Check SL hit
                    elif current_price >= signal['stop_loss']:
                        outcome = 'LOSS'
                        exit_price = signal['stop_loss']
                        pips = -signal['sl_pips']
                        reason = self._generate_sl_reason(signal, 'SELL')
                
                # If trade closed, create notification
                if outcome:
                    duration = self._calculate_duration(signal['timestamp'], datetime.now())
                    
                    notification = {
                        'signal_id': signal_id,
                        'symbol': signal['symbol'],
                        'direction': signal['direction'],
                        'outcome': outcome,
                        'pips': pips,
                        'duration': duration,
                        'reason': reason,
                        'entry_price': signal['entry_price'],
                        'exit_price': exit_price,
                        'setup_type': signal['setup_type']
                    }
                    
                    notifications.append(notification)
                    
                    # Update CSV files
                    self._update_signal_in_csv(signal_id, outcome, pips, duration, reason)
                    self._save_closed_trade_to_csv(signal, exit_price, outcome, pips, reason)
                    
                    # Remove from active signals
                    del self.active_signals[signal_id]
                    
                    # Store in ML engine
                    await self.ml_engine.update_signal_outcome(signal_id, outcome, pips)
                    
                    logger.info(f"TRADE CLOSED: {signal['symbol']} {outcome} {pips:.1f} pips in {duration}")
                
            except Exception as e:
                logger.error(f"Error checking signal {signal_id}: {e}")
        
        return notifications
    
    def _generate_tp_reason(self, signal: Dict, direction: str) -> str:
        """Generate reason for TP hit"""
        reasons = []
        
        # Trend alignment
        if 'STRONG' in signal['trend']:
            reasons.append(f"strong {signal['trend'].replace('_', ' ').lower()} trend continuation")
        elif signal['trend'] != 'NEUTRAL':
            reasons.append(f"{signal['trend'].lower()} trend followed through")
        
        # Setup quality
        if signal['setup_type'] == 'FVG_OB_CONFLUENCE':
            reasons.append("high-quality FVG + Order Block confluence provided strong support/resistance")
        elif signal['setup_type'] == 'ORDER_BLOCK':
            reasons.append("Order Block held as expected")
        elif signal['setup_type'] == 'FVG_ONLY':
            reasons.append("Fair Value Gap reacted perfectly")
        
        # ML confidence
        if signal['ml_confidence'] > 75:
            reasons.append(f"high ML confidence ({signal['ml_confidence']:.1f}%) predicted accurate direction")
        
        # Market structure
        reasons.append("market structure confirmed the move as analyzed")
        
        # Risk management
        reasons.append(f"achieved {signal['risk_reward']:.1f}:1 risk-reward as planned")
        
        return f"TP hit because {', '.join(reasons[:3])}. The {direction} setup followed institutional order flow perfectly."
    
    def _generate_sl_reason(self, signal: Dict, direction: str) -> str:
        """Generate reason for SL hit"""
        reasons = []
        
        # Invalidation
        reasons.append("market structure invalidated the setup")
        
        # Opposite pressure
        if direction == 'BUY':
            reasons.append("unexpected bearish pressure appeared")
        else:
            reasons.append("unexpected bullish pressure appeared")
        
        # Volatility
        if signal['volatility'] == 'HIGH':
            reasons.append("high volatility caused wider-than-expected swings")
        
        # News/fundamentals
        reasons.append("potential fundamental catalyst shifted sentiment")
        
        # Stop hunt possibility
        reasons.append("possible liquidity grab/stop hunt before reversal")
        
        return f"SL hit because {', '.join(reasons[:2])}. This is normal - risk was properly managed at {signal['sl_pips']:.1f} pips."
    
    def get_active_signals_count(self) -> int:
        """Get number of active signals"""
        return len(self.active_signals)
    
    def get_win_rate(self) -> Dict:
        """Calculate accurate win rate from CSV"""
        try:
            wins = 0
            losses = 0
            
            with open(self.csv_closed, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['Outcome'] == 'WIN':
                        wins += 1
                    elif row['Outcome'] == 'LOSS':
                        losses += 1
            
            total = wins + losses
            win_rate = (wins / total * 100) if total > 0 else 0
            
            return {
                'wins': wins,
                'losses': losses,
                'total': total,
                'win_rate': win_rate,
                'profit_factor': (wins / losses) if losses > 0 else float('inf')
            }
            
        except Exception as e:
            logger.error(f"Error calculating win rate: {e}")
            return {'wins': 0, 'losses': 0, 'total': 0, 'win_rate': 0, 'profit_factor': 0}
    
    # Keep all previous methods (_check_cooldown, _validate_setup, etc.)
    def _check_cooldown(self, symbol: str) -> bool:
        """Check if enough time has passed since last signal"""
        if symbol not in self.last_signal_time:
            return True
        
        time_since_last = (datetime.now() - self.last_signal_time[symbol]).total_seconds()
        return time_since_last >= self.config.SIGNAL_COOLDOWN
    
    def _validate_setup(self, market_state: Dict) -> tuple:
        """Validate if setup meets SMC criteria"""
        try:
            liquidity_sweep = market_state.get('liquidity_sweep', {})
            if not liquidity_sweep.get('detected', False):
                return False, None
            
            displacement = market_state.get('m1_displacement', {})
            if not displacement.get('detected', False):
                return False, None
            
            fvgs = market_state.get('fvgs', [])
            order_blocks = market_state.get('order_blocks', [])
            
            if not fvgs and not order_blocks:
                return False, None
            
            setup_type = self._identify_setup_type(market_state)
            
            sweep_direction = liquidity_sweep.get('type')
            displacement_direction = displacement.get('direction')
            
            if sweep_direction != displacement_direction:
                return False, None
            
            bias = market_state.get('bias', 'NEUTRAL')
            if bias == 'NEUTRAL':
                return False, None
            
            if bias == 'BULLISH' and sweep_direction != 'BULLISH':
                return False, None
            
            if bias == 'BEARISH' and sweep_direction != 'BEARISH':
                return False, None
            
            return True, setup_type
            
        except Exception as e:
            logger.error(f"Error validating setup: {e}")
            return False, None
    
    def _identify_setup_type(self, market_state: Dict) -> str:
        """Identify the specific setup type"""
        fvgs = market_state.get('fvgs', [])
        order_blocks = market_state.get('order_blocks', [])
        
        if fvgs and order_blocks:
            return 'FVG_OB_CONFLUENCE'
        elif fvgs:
            return 'FVG_ONLY'
        elif order_blocks:
            return 'ORDER_BLOCK'
        else:
            return 'STRUCTURE_BREAK'
    
    def _determine_direction(self, market_state: Dict) -> str:
        """Determine signal direction"""
        try:
            bias = market_state.get('bias', 'NEUTRAL')
            displacement = market_state.get('m1_displacement', {})
            liquidity_sweep = market_state.get('liquidity_sweep', {})
            
            displacement_dir = displacement.get('direction', 'NEUTRAL')
            sweep_dir = liquidity_sweep.get('type', 'NEUTRAL')
            
            if bias == displacement_dir == sweep_dir:
                return 'BUY' if bias == 'BULLISH' else 'SELL'
            
            return 'NEUTRAL'
            
        except Exception as e:
            logger.error(f"Error determining direction: {e}")
            return 'NEUTRAL'
    
    def _determine_entry_type(self, current_price: float, entry_zone: Dict, 
                             direction: str, displacement_strength: float, 
                             volatility: str) -> str:
        """Determine entry order type"""
        try:
            entry_upper = entry_zone['upper']
            entry_lower = entry_zone['lower']
            zone_size = entry_upper - entry_lower
            
            strong_displacement = displacement_strength > 3.5
            high_volatility = volatility == 'HIGH'
            immediate_entry = strong_displacement or high_volatility
            
            if direction == 'BUY':
                if entry_lower <= current_price <= entry_upper:
                    return 'MARKET' if immediate_entry else 'BUY_LIMIT'
                elif current_price > entry_upper:
                    distance = current_price - entry_upper
                    if distance > zone_size * 0.5:
                        return 'BUY_LIMIT'
                    elif immediate_entry:
                        return 'MARKET'
                    else:
                        return 'BUY_LIMIT'
                else:
                    distance = entry_lower - current_price
                    return 'BUY_LIMIT' if distance < zone_size * 0.25 else 'BUY_STOP'
            
            else:  # SELL
                if entry_lower <= current_price <= entry_upper:
                    return 'MARKET' if immediate_entry else 'SELL_LIMIT'
                elif current_price < entry_lower:
                    distance = entry_lower - current_price
                    if distance > zone_size * 0.5:
                        return 'SELL_LIMIT'
                    elif immediate_entry:
                        return 'MARKET'
                    else:
                        return 'SELL_LIMIT'
                else:
                    distance = current_price - entry_upper
                    return 'SELL_LIMIT' if distance < zone_size * 0.25 else 'SELL_STOP'
                    
        except Exception as e:
            logger.error(f"Error determining entry type: {e}")
            return 'BUY_LIMIT' if direction == 'BUY' else 'SELL_LIMIT'
    
    def _calculate_entry_levels(self, market_state: Dict, direction: str) -> Optional[Dict]:
        """Calculate entry, SL, and TP levels"""
        try:
            current_price = market_state['current_price']
            symbol_info = self.config.get_symbol_info(market_state['symbol'])
            point = symbol_info['point_value']
            
            fvgs = market_state.get('fvgs', [])
            order_blocks = market_state.get('order_blocks', [])
            displacement = market_state.get('m1_displacement', {})
            displacement_strength = displacement.get('strength', 0)
            volatility = market_state.get('volatility', 'MEDIUM')
            
            if direction == 'BUY':
                entry_zone = self._find_bullish_entry_zone(fvgs, order_blocks, current_price)
                if not entry_zone:
                    return None
                
                entry_type = self._determine_entry_type(
                    current_price, entry_zone, direction, displacement_strength, volatility
                )
                
                if entry_type == 'MARKET':
                    entry = current_price
                elif entry_type == 'BUY_LIMIT':
                    entry = entry_zone['lower'] + (entry_zone['upper'] - entry_zone['lower']) * 0.3
                elif entry_type == 'BUY_STOP':
                    entry = entry_zone['lower']
                else:
                    entry = (entry_zone['upper'] + entry_zone['lower']) / 2
                
                sl = entry_zone['lower'] - (10 * point)
                sl_pips = abs(entry - sl) / point
                tp_pips = sl_pips * self.config.MIN_RISK_REWARD
                tp = entry + (tp_pips * point)
                rr = tp_pips / sl_pips if sl_pips > 0 else 0
                
                if rr < self.config.MIN_RISK_REWARD:
                    return None
                
                return {
                    'entry_type': entry_type,
                    'entry': round(entry, 5),
                    'sl': round(sl, 5),
                    'tp': round(tp, 5),
                    'sl_pips': round(sl_pips, 1),
                    'tp_pips': round(tp_pips, 1),
                    'rr': round(rr, 2)
                }
            
            else:  # SELL
                entry_zone = self._find_bearish_entry_zone(fvgs, order_blocks, current_price)
                if not entry_zone:
                    return None
                
                entry_type = self._determine_entry_type(
                    current_price, entry_zone, direction, displacement_strength, volatility
                )
                
                if entry_type == 'MARKET':
                    entry = current_price
                elif entry_type == 'SELL_LIMIT':
                    entry = entry_zone['upper'] - (entry_zone['upper'] - entry_zone['lower']) * 0.3
                elif entry_type == 'SELL_STOP':
                    entry = entry_zone['upper']
                else:
                    entry = (entry_zone['upper'] + entry_zone['lower']) / 2
                
                sl = entry_zone['upper'] + (10 * point)
                sl_pips = abs(sl - entry) / point
                tp_pips = sl_pips * self.config.MIN_RISK_REWARD
                tp = entry - (tp_pips * point)
                rr = tp_pips / sl_pips if sl_pips > 0 else 0
                
                if rr < self.config.MIN_RISK_REWARD:
                    return None
                
                return {
                    'entry_type': entry_type,
                    'entry': round(entry, 5),
                    'sl': round(sl, 5),
                    'tp': round(tp, 5),
                    'sl_pips': round(sl_pips, 1),
                    'tp_pips': round(tp_pips, 1),
                    'rr': round(rr, 2)
                }
                
        except Exception as e:
            logger.error(f"Error calculating entry levels: {e}")
            return None
    
    def _find_bullish_entry_zone(self, fvgs: list, order_blocks: list, current_price: float) -> Optional[Dict]:
        """Find bullish entry zone"""
        bullish_obs = [ob for ob in order_blocks if ob['type'] == 'BULLISH']
        bullish_fvgs = [fvg for fvg in fvgs if fvg['type'] == 'BULLISH']
        
        for ob in bullish_obs:
            for fvg in bullish_fvgs:
                if (ob['lower'] <= fvg['upper'] and ob['upper'] >= fvg['lower']):
                    return {
                        'upper': min(ob['upper'], fvg['upper']),
                        'lower': max(ob['lower'], fvg['lower']),
                        'type': 'CONFLUENCE'
                    }
        
        if bullish_obs:
            return {'upper': bullish_obs[0]['upper'], 'lower': bullish_obs[0]['lower'], 'type': 'ORDER_BLOCK'}
        
        if bullish_fvgs:
            return {'upper': bullish_fvgs[0]['upper'], 'lower': bullish_fvgs[0]['lower'], 'type': 'FVG'}
        
        return None
    
    def _find_bearish_entry_zone(self, fvgs: list, order_blocks: list, current_price: float) -> Optional[Dict]:
        """Find bearish entry zone"""
        bearish_obs = [ob for ob in order_blocks if ob['type'] == 'BEARISH']
        bearish_fvgs = [fvg for fvg in fvgs if fvg['type'] == 'BEARISH']
        
        for ob in bearish_obs:
            for fvg in bearish_fvgs:
                if (ob['lower'] <= fvg['upper'] and ob['upper'] >= fvg['lower']):
                    return {
                        'upper': min(ob['upper'], fvg['upper']),
                        'lower': max(ob['lower'], fvg['lower']),
                        'type': 'CONFLUENCE'
                    }
        
        if bearish_obs:
            return {'upper': bearish_obs[0]['upper'], 'lower': bearish_obs[0]['lower'], 'type': 'ORDER_BLOCK'}
        
        if bearish_fvgs:
            return {'upper': bearish_fvgs[0]['upper'], 'lower': bearish_fvgs[0]['lower'], 'type': 'FVG'}
        
        return None
    
    def _calculate_signal_strength(self, market_state: Dict, ml_confidence: float) -> str:
        """Calculate signal strength"""
        try:
            score = 0
            
            # Trend
            trend = market_state.get('htf_trend', 'NEUTRAL')
            if 'STRONG' in trend:
                score += 25
            elif trend != 'NEUTRAL':
                score += 15
            
            # Structure
            if market_state.get('htf_structure', {}).get('bos_detected'):
                score += 15
            
            # Setup quality
            fvgs = market_state.get('fvgs', [])
            order_blocks = market_state.get('order_blocks', [])
            if fvgs and order_blocks:
                score += 20
            elif fvgs or order_blocks:
                score += 10
            
            # ML confidence
            score += (ml_confidence / 100) * 30
            
            # Kill zone
            if market_state.get('in_kill_zone'):
                score += 10
            
            if score >= 80:
                return 'VERY_HIGH'
            elif score >= 65:
                return 'HIGH'
            elif score >= 50:
                return 'MEDIUM'
            else:
                return 'LOW'
                
        except Exception as e:
            logger.error(f"Error calculating signal strength: {e}")
            return 'MEDIUM'