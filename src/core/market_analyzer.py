"""
Market Analysis Engine - SMC Strategy Implementation
Implements Smart Money Concepts from the trading document
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Dict, Optional, List, Tuple
from src.utils.logger import setup_logger
from src.core.fundamental_analyzer import FundamentalAnalyzer
from src.core.enhanced_trend_analyzer import EnhancedTrendAnalyzer

logger = setup_logger(__name__)


class MarketAnalyzer:
    """Analyzes market using SMC principles"""
    
    def __init__(self, mt5_connection, config):
        self.mt5 = mt5_connection
        self.config = config
        self.fundamental_analyzer = FundamentalAnalyzer(config)
        self.trend_analyzer = EnhancedTrendAnalyzer()  
        
    async def analyze(self, symbol: str) -> Dict:
        """Complete market analysis for a symbol"""
        try:
            # Get multi-timeframe data
            htf_data = await self.mt5.get_rates(symbol, self.config.TIMEFRAMES['HTF'], 200)
            mtf_data = await self.mt5.get_rates(symbol, self.config.TIMEFRAMES['MTF'], 200)
            ltf_data = await self.mt5.get_rates(symbol, self.config.TIMEFRAMES['LTF_ENTRY'], 500)
            m1_data = await self.mt5.get_rates(symbol, self.config.TIMEFRAMES['LTF_PRECISION'], 500)
            
            if any(df is None for df in [htf_data, mtf_data, ltf_data, m1_data]):
                return {}
            
            # Get current market info
            tick = await self.mt5.get_tick(symbol)
            symbol_info = await self.mt5.get_symbol_info(symbol)
            
            if not tick or not symbol_info:
                return {}
            
            # HTF Analysis - Directional Bias WITH ENHANCED TREND DETECTION
            htf_structure = self._analyze_structure(htf_data)
            enhanced_trend_analysis = self.trend_analyzer.identify_trend(htf_data)  
            htf_trend = enhanced_trend_analysis['trend']  # Use enhanced trend
            liquidity_levels = self._identify_liquidity_zones(htf_data)
            
            # NEW: Fundamental Analysis
            fundamental_analysis = await self.fundamental_analyzer.analyze(symbol, {
                'current_price': tick['bid'],
                'volatility': self._calculate_volatility(ltf_data),
                'bias': 'NEUTRAL'  # Will be updated below
            })
            
            # MTF Analysis - Intermediate confirmation
            mtf_structure = self._analyze_structure(mtf_data)
            
            # LTF Analysis - Entry setup
            ltf_structure = self._analyze_structure(ltf_data)
            fvgs = self._identify_fvg(ltf_data)
            order_blocks = self._identify_order_blocks(ltf_data)
            
            # M1 Precision Analysis
            m1_displacement = self._check_displacement(m1_data)
            liquidity_sweep = self._check_liquidity_sweep(m1_data, liquidity_levels)
            
            # Calculate technical indicators
            volatility = self._calculate_volatility(ltf_data)
            atr = self._calculate_atr(ltf_data)
            rsi = self._calculate_rsi(ltf_data)
            volume_profile = self._analyze_volume(ltf_data)
            
            # Market state
            market_state = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'current_price': tick['bid'],
                'spread': symbol_info['spread'] * symbol_info['point'],
                
                # HTF Analysis
                'htf_trend': htf_trend,
                'htf_structure': htf_structure,
                'liquidity_levels': liquidity_levels,
                'trend_quality': enhanced_trend_analysis['trend_quality'],  
                'trend_strength': enhanced_trend_analysis['trend_strength'], 
                'trend_confirmations': enhanced_trend_analysis['confirmations'], 
                
                # MTF Analysis
                'mtf_structure': mtf_structure,
                
                # LTF Analysis
                'ltf_structure': ltf_structure,
                'fvgs': fvgs,
                'order_blocks': order_blocks,
                
                # M1 Analysis
                'm1_displacement': m1_displacement,
                'liquidity_sweep': liquidity_sweep,
                
                # Technical Indicators
                'volatility': volatility,
                'atr': atr,
                'rsi': rsi,
                'volume_profile': volume_profile,
                
                # Bias determination (with fundamental influence)
                'bias': self._determine_bias_with_fundamentals(
                    htf_trend, htf_structure, liquidity_levels, fundamental_analysis  # UPDATED
                    ),
                'in_kill_zone': self._check_kill_zone(),
                
                 # NEW: Fundamental Analysis
                 'fundamental_analysis': fundamental_analysis,
                 'fundamental_bias': fundamental_analysis['fundamental_bias'],
                 'sentiment': fundamental_analysis['sentiment'],
                 'avoid_trading': fundamental_analysis['avoid_trading'],
                 'session': fundamental_analysis['session_impact'],
                
                # Additional metrics
                'trend_strength': self._calculate_trend_strength(htf_data),
                'volume_ratio': self._calculate_volume_ratio(ltf_data)
            }
            
            return market_state
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
            return {}
    
    def _analyze_structure(self, df: pd.DataFrame) -> Dict:
        """Analyze market structure for BOS and ChoCH"""
        try:
            highs = []
            lows = []
            
            # Identify swing highs and lows
            for i in range(2, len(df) - 2):
                # Swing high
                if (df.iloc[i]['high'] > df.iloc[i-1]['high'] and 
                    df.iloc[i]['high'] > df.iloc[i-2]['high'] and
                    df.iloc[i]['high'] > df.iloc[i+1]['high'] and 
                    df.iloc[i]['high'] > df.iloc[i+2]['high']):
                    highs.append({'price': df.iloc[i]['high'], 'index': i})
                
                # Swing low
                if (df.iloc[i]['low'] < df.iloc[i-1]['low'] and 
                    df.iloc[i]['low'] < df.iloc[i-2]['low'] and
                    df.iloc[i]['low'] < df.iloc[i+1]['low'] and 
                    df.iloc[i]['low'] < df.iloc[i+2]['low']):
                    lows.append({'price': df.iloc[i]['low'], 'index': i})
            
            # Determine BOS
            bos_detected = False
            bos_direction = None
            
            if len(highs) >= 2 and len(lows) >= 2:
                # Bullish BOS
                if df.iloc[-1]['close'] > highs[-2]['price']:
                    bos_detected = True
                    bos_direction = 'BULLISH'
                
                # Bearish BOS
                elif df.iloc[-1]['close'] < lows[-2]['price']:
                    bos_detected = True
                    bos_direction = 'BEARISH'
            
            return {
                'swing_highs': highs[-5:] if len(highs) > 5 else highs,
                'swing_lows': lows[-5:] if len(lows) > 5 else lows,
                'bos_detected': bos_detected,
                'bos_direction': bos_direction
            }
            
        except Exception as e:
            logger.error(f"Error analyzing structure: {e}")
            return {}
    
    def _identify_trend(self, df: pd.DataFrame) -> str:
        """Identify overall trend using EMAs"""
        try:
            # Calculate EMAs
            df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
            df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
            
            current_price = df.iloc[-1]['close']
            ema_20 = df.iloc[-1]['ema_20']
            ema_50 = df.iloc[-1]['ema_50']
            ema_200 = df.iloc[-1]['ema_200']
            
            # Strong uptrend
            if (current_price > ema_20 > ema_50 > ema_200):
                return 'STRONG_BULLISH'
            # Moderate uptrend
            elif (current_price > ema_50 > ema_200):
                return 'BULLISH'
            # Strong downtrend
            elif (current_price < ema_20 < ema_50 < ema_200):
                return 'STRONG_BEARISH'
            # Moderate downtrend
            elif (current_price < ema_50 < ema_200):
                return 'BEARISH'
            else:
                return 'NEUTRAL'
                
        except Exception as e:
            logger.error(f"Error identifying trend: {e}")
            return 'NEUTRAL'
    
    def _identify_liquidity_zones(self, df: pd.DataFrame) -> List[Dict]:
        """Identify key liquidity zones (PDH/PDL, session highs/lows)"""
        try:
            liquidity_zones = []
            
            # Previous day high/low
            if len(df) > 24:
                pdh = df.iloc[-24:-1]['high'].max()
                pdl = df.iloc[-24:-1]['low'].min()
                
                liquidity_zones.append({
                    'type': 'PDH',
                    'price': pdh,
                    'strength': 'HIGH'
                })
                
                liquidity_zones.append({
                    'type': 'PDL',
                    'price': pdl,
                    'strength': 'HIGH'
                })
            
            # Recent swing highs/lows
            structure = self._analyze_structure(df)
            
            if structure.get('swing_highs'):
                for high in structure['swing_highs'][-3:]:
                    liquidity_zones.append({
                        'type': 'SWING_HIGH',
                        'price': high['price'],
                        'strength': 'MEDIUM'
                    })
            
            if structure.get('swing_lows'):
                for low in structure['swing_lows'][-3:]:
                    liquidity_zones.append({
                        'type': 'SWING_LOW',
                        'price': low['price'],
                        'strength': 'MEDIUM'
                    })
            
            return liquidity_zones
            
        except Exception as e:
            logger.error(f"Error identifying liquidity zones: {e}")
            return []
    
    def _identify_fvg(self, df: pd.DataFrame) -> List[Dict]:
        """Identify Fair Value Gaps"""
        try:
            fvgs = []
            
            for i in range(2, len(df)):
                # Bullish FVG
                if df.iloc[i]['low'] > df.iloc[i-2]['high']:
                    gap_size = df.iloc[i]['low'] - df.iloc[i-2]['high']
                    
                    if gap_size >= self.config.FVG_MIN_SIZE * df.iloc[i]['close'] * 0.0001:
                        fvgs.append({
                            'type': 'BULLISH',
                            'upper': df.iloc[i]['low'],
                            'lower': df.iloc[i-2]['high'],
                            'size': gap_size,
                            'index': i,
                            'mitigated': False
                        })
                
                # Bearish FVG
                elif df.iloc[i]['high'] < df.iloc[i-2]['low']:
                    gap_size = df.iloc[i-2]['low'] - df.iloc[i]['high']
                    
                    if gap_size >= self.config.FVG_MIN_SIZE * df.iloc[i]['close'] * 0.0001:
                        fvgs.append({
                            'type': 'BEARISH',
                            'upper': df.iloc[i-2]['low'],
                            'lower': df.iloc[i]['high'],
                            'size': gap_size,
                            'index': i,
                            'mitigated': False
                        })
            
            # Check if FVGs have been mitigated
            for fvg in fvgs:
                for j in range(fvg['index'] + 1, len(df)):
                    if fvg['type'] == 'BULLISH':
                        if df.iloc[j]['low'] <= fvg['upper']:
                            fvg['mitigated'] = True
                            break
                    else:
                        if df.iloc[j]['high'] >= fvg['lower']:
                            fvg['mitigated'] = True
                            break
            
            # Return only unmitigated FVGs
            return [fvg for fvg in fvgs if not fvg['mitigated']][-5:]
            
        except Exception as e:
            logger.error(f"Error identifying FVGs: {e}")
            return []
    
    def _identify_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """Identify Order Blocks"""
        try:
            order_blocks = []
            
            for i in range(self.config.OB_LOOKBACK, len(df)):
                # Look for displacement
                displacement_size = abs(df.iloc[i]['close'] - df.iloc[i]['open'])
                avg_candle_size = df.iloc[i-20:i]['close'].sub(df.iloc[i-20:i]['open']).abs().mean()
                
                # Bullish Order Block
                if (df.iloc[i]['close'] > df.iloc[i]['open'] and 
                    displacement_size > 2 * avg_candle_size):
                    
                    # Last bearish candle before displacement
                    for j in range(i-1, max(0, i-5), -1):
                        if df.iloc[j]['close'] < df.iloc[j]['open']:
                            order_blocks.append({
                                'type': 'BULLISH',
                                'upper': df.iloc[j]['high'],
                                'lower': df.iloc[j]['low'],
                                'index': j,
                                'strength': displacement_size / avg_candle_size
                            })
                            break
                
                # Bearish Order Block
                elif (df.iloc[i]['close'] < df.iloc[i]['open'] and 
                      displacement_size > 2 * avg_candle_size):
                    
                    # Last bullish candle before displacement
                    for j in range(i-1, max(0, i-5), -1):
                        if df.iloc[j]['close'] > df.iloc[j]['open']:
                            order_blocks.append({
                                'type': 'BEARISH',
                                'upper': df.iloc[j]['high'],
                                'lower': df.iloc[j]['low'],
                                'index': j,
                                'strength': displacement_size / avg_candle_size
                            })
                            break
            
            return order_blocks[-10:]
            
        except Exception as e:
            logger.error(f"Error identifying order blocks: {e}")
            return []
    
    def _check_displacement(self, df: pd.DataFrame) -> Dict:
        """Check for strong displacement move"""
        try:
            if len(df) < 20:
                return {'detected': False}
            
            recent_candle = df.iloc[-1]
            displacement_size = abs(recent_candle['close'] - recent_candle['open'])
            avg_candle_size = df.iloc[-20:-1]['close'].sub(df.iloc[-20:-1]['open']).abs().mean()
            
            if displacement_size > 2.5 * avg_candle_size:
                return {
                    'detected': True,
                    'direction': 'BULLISH' if recent_candle['close'] > recent_candle['open'] else 'BEARISH',
                    'size': displacement_size,
                    'strength': displacement_size / avg_candle_size
                }
            
            return {'detected': False}
            
        except Exception as e:
            logger.error(f"Error checking displacement: {e}")
            return {'detected': False}
    
    def _check_liquidity_sweep(self, df: pd.DataFrame, liquidity_levels: List[Dict]) -> Dict:
        """Check if price has swept liquidity"""
        try:
            if not liquidity_levels or len(df) < 5:
                return {'detected': False}
            
            recent_high = df.iloc[-5:]['high'].max()
            recent_low = df.iloc[-5:]['low'].min()
            current_price = df.iloc[-1]['close']
            
            for level in liquidity_levels:
                price = level['price']
                
                # Bullish sweep (swept low and reversed)
                if recent_low < price < current_price:
                    if level['type'] in ['PDL', 'SWING_LOW']:
                        return {
                            'detected': True,
                            'type': 'BULLISH',
                            'level': price,
                            'level_type': level['type']
                        }
                
                # Bearish sweep (swept high and reversed)
                elif recent_high > price > current_price:
                    if level['type'] in ['PDH', 'SWING_HIGH']:
                        return {
                            'detected': True,
                            'type': 'BEARISH',
                            'level': price,
                            'level_type': level['type']
                        }
            
            return {'detected': False}
            
        except Exception as e:
            logger.error(f"Error checking liquidity sweep: {e}")
            return {'detected': False}
    
    def _calculate_volatility(self, df: pd.DataFrame) -> str:
        """Calculate current volatility state"""
        try:
            if len(df) < 20:
                return 'MEDIUM'
            
            returns = df['close'].pct_change().dropna()
            current_vol = returns.iloc[-20:].std()
            avg_vol = returns.std()
            
            if current_vol > 1.5 * avg_vol:
                return 'HIGH'
            elif current_vol < 0.5 * avg_vol:
                return 'LOW'
            else:
                return 'MEDIUM'
                
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 'MEDIUM'
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            
            atr = true_range.rolling(period).mean().iloc[-1]
            return float(atr)
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return 0.0
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate RSI"""
        try:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1])
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return 50.0
    
    def _analyze_volume(self, df: pd.DataFrame) -> Dict:
        """Analyze volume profile"""
        try:
            if len(df) < 20:
                return {'status': 'NORMAL'}
            
            current_volume = df.iloc[-1]['tick_volume']
            avg_volume = df.iloc[-20:-1]['tick_volume'].mean()
            
            ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            if ratio > 1.5:
                status = 'HIGH'
            elif ratio < 0.5:
                status = 'LOW'
            else:
                status = 'NORMAL'
            
            return {
                'status': status,
                'ratio': ratio,
                'current': current_volume,
                'average': avg_volume
            }
            
        except Exception as e:
            logger.error(f"Error analyzing volume: {e}")
            return {'status': 'NORMAL'}
    
    def _determine_bias_with_fundamentals(self, trend: str, structure: Dict, 
                                      liquidity_levels: List[Dict],
                                      fundamental: Dict) -> str:
        """Determine trading bias using both technical and fundamental analysis"""
        try:
            bullish_factors = 0
            bearish_factors = 0
            
            # Trend
            if 'BULLISH' in trend:
                bullish_factors += 2
            elif 'BEARISH' in trend:
                bearish_factors += 2
            
            # Structure
            if structure.get('bos_direction') == 'BULLISH':
                bullish_factors += 1
            elif structure.get('bos_direction') == 'BEARISH':
                bearish_factors += 1
                
            # NEW: Fundamental bias
            fundamental_bias = fundamental['fundamental_bias']
            if fundamental_bias == 'BUY':
                bullish_factors += 2  # Strong weight for fundamentals
            elif fundamental_bias == 'SELL':
                bearish_factors += 2
            
            # Determine final bias
            if bullish_factors > bearish_factors + 1:  # Need clear advantage
                return 'BULLISH'
            elif bearish_factors > bullish_factors + 1:
                return 'BEARISH'
            else:
                return 'NEUTRAL'
                
        except Exception as e:
            logger.error(f"Error determining bias with fundamentals: {e}")
            return 'NEUTRAL'
        
    
    def _check_kill_zone(self) -> bool:
        """Check if current time is in kill zone"""
        try:
            current_time = datetime.utcnow().time()
            
            london_start = time.fromisoformat(self.config.LONDON_SESSION['start'])
            london_end = time.fromisoformat(self.config.LONDON_SESSION['end'])
            ny_start = time.fromisoformat(self.config.NY_SESSION['start'])
            ny_end = time.fromisoformat(self.config.NY_SESSION['end'])
            
            return (london_start <= current_time <= london_end or 
                   ny_start <= current_time <= ny_end)
                   
        except Exception as e:
            logger.error(f"Error checking kill zone: {e}")
            return False
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate trend strength (0-100)"""
        try:
            if len(df) < 50:
                return 50.0
            
            # Use ADX-like calculation
            df['high_diff'] = df['high'].diff()
            df['low_diff'] = df['low'].diff().abs()
            
            plus_dm = df['high_diff'].where(df['high_diff'] > df['low_diff'], 0).rolling(14).sum()
            minus_dm = df['low_diff'].where(df['low_diff'] > df['high_diff'], 0).rolling(14).sum()
            
            atr = self._calculate_atr(df, 14)
            
            if atr > 0:
                plus_di = 100 * (plus_dm.iloc[-1] / atr)
                minus_di = 100 * (minus_dm.iloc[-1] / atr)
                
                dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
                
                return float(min(100, max(0, dx)))
            
            return 50.0
            
        except Exception as e:
            logger.error(f"Error calculating trend strength: {e}")
            return 50.0
    
    def _calculate_volume_ratio(self, df: pd.DataFrame) -> float:
        """Calculate volume ratio"""
        try:
            if len(df) < 20:
                return 1.0
            
            current_volume = df.iloc[-1]['tick_volume']
            avg_volume = df.iloc[-20:-1]['tick_volume'].mean()
            
            return float(current_volume / avg_volume) if avg_volume > 0 else 1.0
            
        except Exception as e:
            logger.error(f"Error calculating volume ratio: {e}")
            return 1.0