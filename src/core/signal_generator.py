"""
Signal Generation System
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
import numpy as np
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SignalGenerator:
    """Generates trading signals from market analysis"""
    
    def __init__(self, market_analyzer, ml_engine, config):
        self.analyzer = market_analyzer
        self.ml_engine = ml_engine
        self.config = config
        self.last_signal_time = {}
        
    async def generate_signal(self, symbol: str, market_state: Dict) -> Optional[Dict]:
        """Generate trading signal if conditions are met"""
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
                'market_bias': market_state['bias']
            }
            
            # Update last signal time
            self.last_signal_time[symbol] = datetime.now()
            
            logger.info(f"Signal generated for {symbol}: {direction} {entry_data['entry_type']} @ {entry_data['entry']}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}", exc_info=True)
            return None
    
    def _check_cooldown(self, symbol: str) -> bool:
        """Check if enough time has passed since last signal"""
        if symbol not in self.last_signal_time:
            return True
        
        time_since_last = (datetime.now() - self.last_signal_time[symbol]).total_seconds()
        return time_since_last >= self.config.SIGNAL_COOLDOWN
    
    def _validate_setup(self, market_state: Dict) -> tuple:
        """Validate if setup meets SMC criteria"""
        try:
            # Check for liquidity sweep
            liquidity_sweep = market_state.get('liquidity_sweep', {})
            if not liquidity_sweep.get('detected', False):
                return False, None
            
            # Check for displacement
            displacement = market_state.get('m1_displacement', {})
            if not displacement.get('detected', False):
                return False, None
            
            # Check for FVG or Order Block
            fvgs = market_state.get('fvgs', [])
            order_blocks = market_state.get('order_blocks', [])
            
            if not fvgs and not order_blocks:
                return False, None
            
            # Determine setup type
            setup_type = self._identify_setup_type(market_state)
            
            # Verify alignment
            sweep_direction = liquidity_sweep.get('type')
            displacement_direction = displacement.get('direction')
            
            if sweep_direction != displacement_direction:
                return False, None
            
            # Check trend alignment
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
            
            # All must align
            if bias == displacement_dir == sweep_dir:
                return 'BUY' if bias == 'BULLISH' else 'SELL'
            
            return 'NEUTRAL'
            
        except Exception as e:
            logger.error(f"Error determining direction: {e}")
            return 'NEUTRAL'
    
    def _determine_entry_type(self, current_price: float, entry_zone: Dict, 
                             direction: str, displacement_strength: float, 
                             volatility: str) -> str:
        """
        Determine entry order type: MARKET, LIMIT, BUY_STOP, SELL_STOP
        
        Order Type Logic:
        
        MARKET:
        - Price already in optimal entry zone
        - Strong displacement happening NOW (>3.5)
        - High volatility environment
        - Immediate execution needed
        
        LIMIT (Buy/Sell at better price):
        - Price away from entry zone (above for BUY, below for SELL)
        - Waiting for pullback/retracement
        - Better risk:reward on patient entry
        
        BUY_STOP (Buy above current price):
        - BUY signal but price below entry zone
        - Waiting for breakout confirmation
        - Price needs to break through resistance
        
        SELL_STOP (Sell below current price):
        - SELL signal but price above entry zone
        - Waiting for breakdown confirmation
        - Price needs to break through support
        """
        try:
            entry_upper = entry_zone['upper']
            entry_lower = entry_zone['lower']
            entry_mid = (entry_upper + entry_lower) / 2
            
            # Calculate distance from entry zone
            zone_size = entry_upper - entry_lower
            
            # Strong displacement and high volatility favor immediate execution
            strong_displacement = displacement_strength > 3.5
            high_volatility = volatility == 'HIGH'
            immediate_entry = strong_displacement or high_volatility
            
            if direction == 'BUY':
                # Price is IN the entry zone
                if entry_lower <= current_price <= entry_upper:
                    if immediate_entry:
                        return 'MARKET'  # Execute NOW
                    else:
                        return 'BUY_LIMIT'  # Wait for better price within zone
                
                # Price is ABOVE entry zone (already moved past ideal entry)
                elif current_price > entry_upper:
                    distance = current_price - entry_upper
                    
                    # Too far above (>50% of zone size) = wait for pullback
                    if distance > zone_size * 0.5:
                        return 'BUY_LIMIT'  # Wait for retracement
                    
                    # Close above but moving fast = chase with market
                    elif immediate_entry:
                        return 'MARKET'
                    
                    # Otherwise wait for pullback
                    else:
                        return 'BUY_LIMIT'
                
                # Price is BELOW entry zone (needs to come up to entry)
                else:  # current_price < entry_lower
                    distance = entry_lower - current_price
                    
                    # Very close to zone (<25% zone size) = use LIMIT
                    if distance < zone_size * 0.25:
                        return 'BUY_LIMIT'  # Close enough for limit
                    
                    # Far below = wait for breakout confirmation
                    else:
                        return 'BUY_STOP'  # Stop order at entry zone
            
            else:  # SELL
                # Price is IN the entry zone
                if entry_lower <= current_price <= entry_upper:
                    if immediate_entry:
                        return 'MARKET'  # Execute NOW
                    else:
                        return 'SELL_LIMIT'  # Wait for better price within zone
                
                # Price is BELOW entry zone (already moved past ideal entry)
                elif current_price < entry_lower:
                    distance = entry_lower - current_price
                    
                    # Too far below (>50% of zone size) = wait for pullback
                    if distance > zone_size * 0.5:
                        return 'SELL_LIMIT'  # Wait for retracement
                    
                    # Close below but moving fast = chase with market
                    elif immediate_entry:
                        return 'MARKET'
                    
                    # Otherwise wait for pullback
                    else:
                        return 'SELL_LIMIT'
                
                # Price is ABOVE entry zone (needs to come down to entry)
                else:  # current_price > entry_upper
                    distance = current_price - entry_upper
                    
                    # Very close to zone (<25% zone size) = use LIMIT
                    if distance < zone_size * 0.25:
                        return 'SELL_LIMIT'  # Close enough for limit
                    
                    # Far above = wait for breakdown confirmation
                    else:
                        return 'SELL_STOP'  # Stop order at entry zone
                    
        except Exception as e:
            logger.error(f"Error determining entry type: {e}")
            return 'BUY_LIMIT' if direction == 'BUY' else 'SELL_LIMIT'  # Safe default
    
    def _calculate_entry_levels(self, market_state: Dict, direction: str) -> Optional[Dict]:
        """Calculate entry, SL, and TP levels with smart order type selection"""
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
                # Find bullish OB or FVG for entry
                entry_zone = self._find_bullish_entry_zone(fvgs, order_blocks, current_price)
                
                if not entry_zone:
                    return None
                
                # Determine entry type (MARKET, BUY_LIMIT, BUY_STOP)
                entry_type = self._determine_entry_type(
                    current_price, entry_zone, direction, displacement_strength, volatility
                )
                
                # Calculate entry price based on order type
                if entry_type == 'MARKET':
                    # Use current price for immediate market orders
                    entry = current_price
                    
                elif entry_type == 'BUY_LIMIT':
                    # Use lower part of zone for better entry on pullback
                    entry = entry_zone['lower'] + (entry_zone['upper'] - entry_zone['lower']) * 0.3
                    
                elif entry_type == 'BUY_STOP':
                    # Place stop above current price, at entry zone
                    entry = entry_zone['lower']  # Break into the zone
                    
                else:
                    entry = (entry_zone['upper'] + entry_zone['lower']) / 2
                
                # SL below the zone with buffer
                sl_buffer = 10 * point
                sl = entry_zone['lower'] - sl_buffer
                
                # Calculate SL in pips
                sl_pips = abs(entry - sl) / point
                
                # TP based on minimum R:R
                tp_pips = sl_pips * self.config.MIN_RISK_REWARD
                tp = entry + (tp_pips * point)
                
                # Verify RR
                rr = tp_pips / sl_pips if sl_pips > 0 else 0
                
                if rr < self.config.MIN_RISK_REWARD:
                    return None
                
                logger.info(f"BUY {entry_type}: Entry={entry:.5f}, SL={sl:.5f}, TP={tp:.5f}, R:R=1:{rr:.2f}")
                
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
                # Find bearish OB or FVG for entry
                entry_zone = self._find_bearish_entry_zone(fvgs, order_blocks, current_price)
                
                if not entry_zone:
                    return None
                
                # Determine entry type (MARKET, SELL_LIMIT, SELL_STOP)
                entry_type = self._determine_entry_type(
                    current_price, entry_zone, direction, displacement_strength, volatility
                )
                
                # Calculate entry price based on order type
                if entry_type == 'MARKET':
                    # Use current price for immediate market orders
                    entry = current_price
                    
                elif entry_type == 'SELL_LIMIT':
                    # Use upper part of zone for better entry on pullback
                    entry = entry_zone['upper'] - (entry_zone['upper'] - entry_zone['lower']) * 0.3
                    
                elif entry_type == 'SELL_STOP':
                    # Place stop below current price, at entry zone
                    entry = entry_zone['upper']  # Break into the zone
                    
                else:
                    entry = (entry_zone['upper'] + entry_zone['lower']) / 2
                
                # SL above the zone with buffer
                sl_buffer = 10 * point
                sl = entry_zone['upper'] + sl_buffer
                
                # Calculate SL in pips
                sl_pips = abs(sl - entry) / point
                
                # TP based on minimum R:R
                tp_pips = sl_pips * self.config.MIN_RISK_REWARD
                tp = entry - (tp_pips * point)
                
                # Verify RR
                rr = tp_pips / sl_pips if sl_pips > 0 else 0
                
                if rr < self.config.MIN_RISK_REWARD:
                    return None
                
                logger.info(f"SELL {entry_type}: Entry={entry:.5f}, SL={sl:.5f}, TP={tp:.5f}, R:R=1:{rr:.2f}")
                
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
            logger.error(f"Error calculating entry levels: {e}", exc_info=True)
            return None
    
    def _find_bullish_entry_zone(self, fvgs: list, order_blocks: list, current_price: float) -> Optional[Dict]:
        """Find bullish entry zone"""
        try:
            # Prioritize OB with FVG confluence
            bullish_obs = [ob for ob in order_blocks if ob['type'] == 'BULLISH']
            bullish_fvgs = [fvg for fvg in fvgs if fvg['type'] == 'BULLISH']
            
            # Check for confluence
            for ob in bullish_obs:
                for fvg in bullish_fvgs:
                    # Check overlap
                    if (ob['lower'] <= fvg['upper'] and ob['upper'] >= fvg['lower']):
                        return {
                            'upper': min(ob['upper'], fvg['upper']),
                            'lower': max(ob['lower'], fvg['lower']),
                            'type': 'CONFLUENCE'
                        }
            
            # Use OB if available
            if bullish_obs:
                ob = bullish_obs[0]
                return {
                    'upper': ob['upper'],
                    'lower': ob['lower'],
                    'type': 'ORDER_BLOCK'
                }
            
            # Use FVG as fallback
            if bullish_fvgs:
                fvg = bullish_fvgs[0]
                return {
                    'upper': fvg['upper'],
                    'lower': fvg['lower'],
                    'type': 'FVG'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding bullish entry zone: {e}")
            return None
    
    def _find_bearish_entry_zone(self, fvgs: list, order_blocks: list, current_price: float) -> Optional[Dict]:
        """Find bearish entry zone"""
        try:
            # Prioritize OB with FVG confluence
            bearish_obs = [ob for ob in order_blocks if ob['type'] == 'BEARISH']
            bearish_fvgs = [fvg for fvg in fvgs if fvg['type'] == 'BEARISH']
            
            # Check for confluence
            for ob in bearish_obs:
                for fvg in bearish_fvgs:
                    # Check overlap
                    if (ob['lower'] <= fvg['upper'] and ob['upper'] >= fvg['lower']):
                        return {
                            'upper': max(ob['upper'], fvg['upper']),
                            'lower': min(ob['lower'], fvg['lower']),
                            'type': 'CONFLUENCE'
                        }
            
            # Use OB if available
            if bearish_obs:
                ob = bearish_obs[0]
                return {
                    'upper': ob['upper'],
                    'lower': ob['lower'],
                    'type': 'ORDER_BLOCK'
                }
            
            # Use FVG as fallback
            if bearish_fvgs:
                fvg = bearish_fvgs[0]
                return {
                    'upper': fvg['upper'],
                    'lower': fvg['lower'],
                    'type': 'FVG'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding bearish entry zone: {e}")
            return None
    
    def _calculate_signal_strength(self, market_state: Dict, ml_confidence: float) -> str:
        """Calculate overall signal strength"""
        try:
            strength_score = 0
            
            # Trend alignment (0-30 points)
            trend = market_state.get('htf_trend', 'NEUTRAL')
            if 'STRONG' in trend:
                strength_score += 30
            elif trend != 'NEUTRAL':
                strength_score += 20
            
            # Structure confirmation (0-20 points)
            if market_state.get('htf_structure', {}).get('bos_detected'):
                strength_score += 20
            
            # Setup quality (0-20 points)
            fvgs = market_state.get('fvgs', [])
            order_blocks = market_state.get('order_blocks', [])
            if fvgs and order_blocks:
                strength_score += 20
            elif fvgs or order_blocks:
                strength_score += 10
            
            # ML confidence (0-30 points)
            strength_score += (ml_confidence / 100) * 30
            
            # Categorize
            if strength_score >= 80:
                return 'VERY_HIGH'
            elif strength_score >= 65:
                return 'HIGH'
            elif strength_score >= 50:
                return 'MEDIUM'
            else:
                return 'LOW'
                
        except Exception as e:
            logger.error(f"Error calculating signal strength: {e}")
            return 'MEDIUM'