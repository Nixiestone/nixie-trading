"""
Enhanced Trend Identification System
Improved accuracy using multiple indicators and confirmations
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class EnhancedTrendAnalyzer:
    """Enhanced trend identification with multiple confirmations"""
    
    def __init__(self):
        pass
    
    def identify_trend(self, df: pd.DataFrame) -> Dict:
        """
        Identify trend using multiple methods for accuracy
        Returns: {
            'trend': 'STRONG_BULLISH'/'BULLISH'/'NEUTRAL'/'BEARISH'/'STRONG_BEARISH',
            'trend_strength': 0-100,
            'trend_quality': 'excellent'/'good'/'fair'/'poor',
            'confirmations': int (number of confirming indicators),
            'detailed_analysis': Dict
        }
        """
        try:
            if len(df) < 200:
                return self._get_neutral_trend()
            
            # Method 1: EMA alignment
            ema_trend = self._ema_trend(df)
            
            # Method 2: Higher highs / Lower lows
            structure_trend = self._structure_trend(df)
            
            # Method 3: ADX (Trend Strength)
            adx_data = self._calculate_adx(df)
            
            # Method 4: Moving Average Slope
            ma_slope = self._ma_slope_trend(df)
            
            # Method 5: Price Action Trend
            price_action = self._price_action_trend(df)
            
            # Method 6: Volume Confirmation
            volume_confirm = self._volume_confirmation(df, ema_trend['direction'])
            
            # Aggregate all methods
            trend_analysis = self._aggregate_trends({
                'ema': ema_trend,
                'structure': structure_trend,
                'adx': adx_data,
                'ma_slope': ma_slope,
                'price_action': price_action,
                'volume': volume_confirm
            })
            
            return trend_analysis
            
        except Exception as e:
            logger.error(f"Error in trend identification: {e}")
            return self._get_neutral_trend()
    
    def _ema_trend(self, df: pd.DataFrame) -> Dict:
        """Trend based on EMA alignment"""
        try:
            # Calculate EMAs
            df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
            df['ema_100'] = df['close'].ewm(span=100, adjust=False).mean()
            df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
            
            current_price = df.iloc[-1]['close']
            ema_20 = df.iloc[-1]['ema_20']
            ema_50 = df.iloc[-1]['ema_50']
            ema_100 = df.iloc[-1]['ema_100']
            ema_200 = df.iloc[-1]['ema_200']
            
            # Count bullish alignments
            bullish_score = 0
            if current_price > ema_20:
                bullish_score += 1
            if ema_20 > ema_50:
                bullish_score += 1
            if ema_50 > ema_100:
                bullish_score += 1
            if ema_100 > ema_200:
                bullish_score += 1
            
            # Determine direction
            if bullish_score == 4:
                direction = 'STRONG_BULLISH'
                strength = 90
            elif bullish_score == 3:
                direction = 'BULLISH'
                strength = 70
            elif bullish_score == 1:
                direction = 'BEARISH'
                strength = 70
            elif bullish_score == 0:
                direction = 'STRONG_BEARISH'
                strength = 90
            else:
                direction = 'NEUTRAL'
                strength = 50
            
            return {
                'direction': direction,
                'strength': strength,
                'score': bullish_score,
                'method': 'ema'
            }
            
        except Exception as e:
            logger.error(f"Error in EMA trend: {e}")
            return {'direction': 'NEUTRAL', 'strength': 50, 'score': 0, 'method': 'ema'}
    
    def _structure_trend(self, df: pd.DataFrame) -> Dict:
        """Trend based on market structure (HH/HL or LH/LL)"""
        try:
            # Look back 50 candles
            lookback = min(50, len(df))
            recent_data = df.iloc[-lookback:]
            
            # Find swing highs and lows
            highs = []
            lows = []
            
            for i in range(2, len(recent_data) - 2):
                # Swing high
                if (recent_data.iloc[i]['high'] > recent_data.iloc[i-1]['high'] and
                    recent_data.iloc[i]['high'] > recent_data.iloc[i-2]['high'] and
                    recent_data.iloc[i]['high'] > recent_data.iloc[i+1]['high'] and
                    recent_data.iloc[i]['high'] > recent_data.iloc[i+2]['high']):
                    highs.append(recent_data.iloc[i]['high'])
                
                # Swing low
                if (recent_data.iloc[i]['low'] < recent_data.iloc[i-1]['low'] and
                    recent_data.iloc[i]['low'] < recent_data.iloc[i-2]['low'] and
                    recent_data.iloc[i]['low'] < recent_data.iloc[i+1]['low'] and
                    recent_data.iloc[i]['low'] < recent_data.iloc[i+2]['low']):
                    lows.append(recent_data.iloc[i]['low'])
            
            if len(highs) < 2 or len(lows) < 2:
                return {'direction': 'NEUTRAL', 'strength': 50, 'pattern': 'insufficient_data', 'method': 'structure'}
            
            # Check for Higher Highs and Higher Lows (Uptrend)
            recent_highs = highs[-3:]
            recent_lows = lows[-3:]
            
            hh = all(recent_highs[i] > recent_highs[i-1] for i in range(1, len(recent_highs)))
            hl = all(recent_lows[i] > recent_lows[i-1] for i in range(1, len(recent_lows)))
            
            # Check for Lower Highs and Lower Lows (Downtrend)
            lh = all(recent_highs[i] < recent_highs[i-1] for i in range(1, len(recent_highs)))
            ll = all(recent_lows[i] < recent_lows[i-1] for i in range(1, len(recent_lows)))
            
            if hh and hl:
                direction = 'STRONG_BULLISH'
                strength = 85
                pattern = 'HH_HL'
            elif hh or hl:
                direction = 'BULLISH'
                strength = 65
                pattern = 'HH' if hh else 'HL'
            elif lh and ll:
                direction = 'STRONG_BEARISH'
                strength = 85
                pattern = 'LH_LL'
            elif lh or ll:
                direction = 'BEARISH'
                strength = 65
                pattern = 'LH' if lh else 'LL'
            else:
                direction = 'NEUTRAL'
                strength = 50
                pattern = 'RANGING'
            
            return {
                'direction': direction,
                'strength': strength,
                'pattern': pattern,
                'method': 'structure'
            }
            
        except Exception as e:
            logger.error(f"Error in structure trend: {e}")
            return {'direction': 'NEUTRAL', 'strength': 50, 'pattern': 'error', 'method': 'structure'}
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> Dict:
        """Calculate ADX for trend strength"""
        try:
            # Calculate True Range
            df['high_low'] = df['high'] - df['low']
            df['high_close'] = np.abs(df['high'] - df['close'].shift())
            df['low_close'] = np.abs(df['low'] - df['close'].shift())
            df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
            
            # Calculate Directional Movement
            df['up_move'] = df['high'] - df['high'].shift()
            df['down_move'] = df['low'].shift() - df['low']
            
            df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
            df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
            
            # Smooth the values
            df['atr'] = df['tr'].rolling(window=period).mean()
            df['plus_di'] = 100 * (df['plus_dm'].rolling(window=period).mean() / df['atr'])
            df['minus_di'] = 100 * (df['minus_dm'].rolling(window=period).mean() / df['atr'])
            
            # Calculate ADX
            df['dx'] = 100 * np.abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
            df['adx'] = df['dx'].rolling(window=period).mean()
            
            adx_value = df.iloc[-1]['adx']
            plus_di = df.iloc[-1]['plus_di']
            minus_di = df.iloc[-1]['minus_di']
            
            # Determine trend
            if adx_value > 25:
                if plus_di > minus_di:
                    direction = 'STRONG_BULLISH' if adx_value > 40 else 'BULLISH'
                else:
                    direction = 'STRONG_BEARISH' if adx_value > 40 else 'BEARISH'
                strength = min(100, adx_value * 2)
            else:
                direction = 'NEUTRAL'
                strength = adx_value * 2
            
            return {
                'direction': direction,
                'strength': strength,
                'adx': adx_value,
                'plus_di': plus_di,
                'minus_di': minus_di,
                'method': 'adx'
            }
            
        except Exception as e:
            logger.error(f"Error calculating ADX: {e}")
            return {'direction': 'NEUTRAL', 'strength': 50, 'adx': 0, 'method': 'adx'}
    
    def _ma_slope_trend(self, df: pd.DataFrame) -> Dict:
        """Trend based on moving average slope"""
        try:
            df['ma_50'] = df['close'].rolling(window=50).mean()
            
            # Calculate slope
            recent_ma = df['ma_50'].iloc[-10:].values
            if len(recent_ma) < 10:
                return {'direction': 'NEUTRAL', 'strength': 50, 'slope': 0, 'method': 'ma_slope'}
            
            # Linear regression on MA
            x = np.arange(len(recent_ma))
            slope = np.polyfit(x, recent_ma, 1)[0]
            
            # Normalize slope
            price_range = df['close'].iloc[-50:].max() - df['close'].iloc[-50:].min()
            normalized_slope = (slope / price_range) * 1000 if price_range > 0 else 0
            
            if normalized_slope > 5:
                direction = 'STRONG_BULLISH'
                strength = min(100, 50 + abs(normalized_slope) * 5)
            elif normalized_slope > 2:
                direction = 'BULLISH'
                strength = min(80, 50 + abs(normalized_slope) * 5)
            elif normalized_slope < -5:
                direction = 'STRONG_BEARISH'
                strength = min(100, 50 + abs(normalized_slope) * 5)
            elif normalized_slope < -2:
                direction = 'BEARISH'
                strength = min(80, 50 + abs(normalized_slope) * 5)
            else:
                direction = 'NEUTRAL'
                strength = 50
            
            return {
                'direction': direction,
                'strength': strength,
                'slope': normalized_slope,
                'method': 'ma_slope'
            }
            
        except Exception as e:
            logger.error(f"Error in MA slope: {e}")
            return {'direction': 'NEUTRAL', 'strength': 50, 'slope': 0, 'method': 'ma_slope'}
    
    def _price_action_trend(self, df: pd.DataFrame) -> Dict:
        """Trend based on recent price action"""
        try:
            # Last 20 candles
            recent = df.iloc[-20:]
            
            # Count bullish/bearish candles
            bullish_candles = (recent['close'] > recent['open']).sum()
            bearish_candles = (recent['close'] < recent['open']).sum()
            
            # Recent price change
            price_change = (recent.iloc[-1]['close'] - recent.iloc[0]['close']) / recent.iloc[0]['close'] * 100
            
            # Determine trend
            if bullish_candles > 14 and price_change > 1:
                direction = 'STRONG_BULLISH'
                strength = 85
            elif bullish_candles > 11:
                direction = 'BULLISH'
                strength = 65
            elif bearish_candles > 14 and price_change < -1:
                direction = 'STRONG_BEARISH'
                strength = 85
            elif bearish_candles > 11:
                direction = 'BEARISH'
                strength = 65
            else:
                direction = 'NEUTRAL'
                strength = 50
            
            return {
                'direction': direction,
                'strength': strength,
                'bullish_candles': bullish_candles,
                'bearish_candles': bearish_candles,
                'price_change': price_change,
                'method': 'price_action'
            }
            
        except Exception as e:
            logger.error(f"Error in price action: {e}")
            return {'direction': 'NEUTRAL', 'strength': 50, 'method': 'price_action'}
    
    def _volume_confirmation(self, df: pd.DataFrame, trend_direction: str) -> Dict:
        """Check if volume confirms the trend"""
        try:
            # Recent volume vs average
            recent_volume = df.iloc[-10:]['tick_volume'].mean()
            avg_volume = df.iloc[-50:]['tick_volume'].mean()
            
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # Volume confirmation
            if volume_ratio > 1.5:
                confirmed = True
                strength = 80
            elif volume_ratio > 1.2:
                confirmed = True
                strength = 65
            else:
                confirmed = False
                strength = 50
            
            return {
                'confirmed': confirmed,
                'strength': strength,
                'volume_ratio': volume_ratio,
                'method': 'volume'
            }
            
        except Exception as e:
            logger.error(f"Error in volume confirmation: {e}")
            return {'confirmed': False, 'strength': 50, 'volume_ratio': 1, 'method': 'volume'}
    
    def _aggregate_trends(self, analyses: Dict) -> Dict:
        """Aggregate all trend analyses into final trend"""
        try:
            # Count confirmations for each direction
            directions = {
                'STRONG_BULLISH': 0,
                'BULLISH': 0,
                'NEUTRAL': 0,
                'BEARISH': 0,
                'STRONG_BEARISH': 0
            }
            
            total_strength = 0
            count = 0
            
            for method, analysis in analyses.items():
                if 'direction' in analysis:
                    direction = analysis['direction']
                    strength = analysis.get('strength', 50)
                    
                    directions[direction] += 1
                    total_strength += strength
                    count += 1
            
            # Find dominant direction
            max_count = max(directions.values())
            dominant_directions = [d for d, c in directions.items() if c == max_count]
            
            # If tie, use strength as tiebreaker
            if len(dominant_directions) > 1:
                final_trend = 'NEUTRAL'
            else:
                final_trend = dominant_directions[0]
            
            # Calculate average strength
            avg_strength = total_strength / count if count > 0 else 50
            
            # Count total confirmations
            confirmations = sum(1 for d in directions.values() if d > 0)
            
            # Determine quality
            if confirmations >= 5 and avg_strength > 75:
                quality = 'excellent'
            elif confirmations >= 4 and avg_strength > 65:
                quality = 'good'
            elif confirmations >= 3:
                quality = 'fair'
            else:
                quality = 'poor'
            
            return {
                'trend': final_trend,
                'trend_strength': avg_strength,
                'trend_quality': quality,
                'confirmations': confirmations,
                'direction_votes': directions,
                'detailed_analysis': analyses
            }
            
        except Exception as e:
            logger.error(f"Error aggregating trends: {e}")
            return self._get_neutral_trend()
    
    def _get_neutral_trend(self) -> Dict:
        """Return neutral trend on error"""
        return {
            'trend': 'NEUTRAL',
            'trend_strength': 50,
            'trend_quality': 'poor',
            'confirmations': 0,
            'direction_votes': {},
            'detailed_analysis': {}
        }