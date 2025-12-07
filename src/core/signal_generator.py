"""
Signal Generation System
Generates trading signals based on SMC analysis and ML predictions
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
            
            logger.info(f"Signal generated for {symbol}: {direction} @ {entry_data['entry']}")
            
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
    
    def _calculate_entry_levels(self, market_state: Dict, direction: str) -> Optional[Dict]:
        """Calculate entry, SL, and TP levels"""
        try:
            current_price = market_state['current_price']
            symbol_info = self.config.get_symbol_info(market_state['symbol'])
            point = symbol_info['point_value']
            
            fvgs = market_state.get('fvgs', [])
            order_blocks = market_state.get('order_blocks', [])
            
            if direction == 'BUY':
                # Find bullish OB or FVG for entry
                entry_zone = self._find_bullish_entry_zone(fvgs, order_blocks, current_price)
                
                if not entry_zone:
                    return None
                
                # Entry at 50% of OB/FVG
                entry = (entry_zone['upper'] + entry_zone['lower']) / 2
                
                # SL below the zone
                sl = entry_zone['lower'] - (10 * point)
                
                # Calculate SL in pips
                sl_pips = abs(entry - sl) / point
                
                # TP based on minimum 1:3 RR
                tp_pips = sl_pips * self.config.MIN_RISK_REWARD
                tp = entry + (tp_pips * point)
                
                # Verify RR
                rr = tp_pips / sl_pips if sl_pips > 0 else 0
                
                if rr < self.config.MIN_RISK_REWARD:
                    return None
                
                return {
                    'entry_type': 'LIMIT',
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
                
                # Entry at 50% of OB/FVG
                entry = (entry_zone['upper'] + entry_zone['lower']) / 2
                
                # SL above the zone
                sl = entry_zone['upper'] + (10 * point)
                
                # Calculate SL in pips
                sl_pips = abs(sl - entry) / point
                
                # TP based on minimum 1:3 RR
                tp_pips = sl_pips * self.config.MIN_RISK_REWARD
                tp = entry - (tp_pips * point)
                
                # Verify RR
                rr = tp_pips / sl_pips if sl_pips > 0 else 0
                
                if rr < self.config.MIN_RISK_REWARD:
                    return None
                
                return {
                    'entry_type': 'LIMIT',
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