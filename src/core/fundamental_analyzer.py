"""
Fundamental Analysis Module
Analyzes economic news, events, and sentiment for trading decisions
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class FundamentalAnalyzer:
    """Analyzes fundamental factors affecting markets"""
    
    def __init__(self, config):
        self.config = config
        
        # Economic calendar (major events to avoid/trade)
        self.high_impact_events = {
            'USD': ['NFP', 'FOMC', 'CPI', 'GDP', 'Interest Rate', 'Unemployment'],
            'EUR': ['ECB', 'CPI', 'GDP', 'Interest Rate'],
            'GBP': ['BOE', 'CPI', 'GDP', 'Interest Rate'],
            'JPY': ['BOJ', 'CPI', 'Tankan'],
            'AUD': ['RBA', 'Employment'],
            'CAD': ['BOC', 'Employment'],
            'NZD': ['RBNZ'],
            'CHF': ['SNB']
        }
        
        # Market sentiment indicators
        self.sentiment_keywords = {
            'bullish': ['rally', 'surge', 'climb', 'gain', 'boost', 'rise', 'positive', 'strong'],
            'bearish': ['fall', 'drop', 'decline', 'weak', 'negative', 'sell', 'crash', 'plunge'],
            'volatile': ['volatile', 'uncertain', 'mixed', 'choppy', 'erratic'],
            'stable': ['stable', 'steady', 'calm', 'consolidate']
        }
        
        # Currency strength based on economic conditions
        self.currency_strength = {}
        self._initialize_currency_strength()
    
    def _initialize_currency_strength(self):
        """Initialize baseline currency strength"""
        # These would ideally come from live data feeds
        # For now, use neutral baseline
        currencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'NZD', 'CHF']
        for curr in currencies:
            self.currency_strength[curr] = {
                'score': 50,  # Neutral (0-100 scale)
                'trend': 'neutral',
                'last_update': datetime.now()
            }
    
    async def analyze(self, symbol: str, market_state: Dict) -> Dict:
        """
        Perform fundamental analysis for a symbol
        Returns: {
            'sentiment': 'bullish'/'bearish'/'neutral',
            'strength_score': 0-100,
            'currency_correlation': Dict,
            'news_impact': 'high'/'medium'/'low',
            'avoid_trading': bool,
            'fundamental_bias': 'buy'/'sell'/'neutral'
        }
        """
        try:
            # Extract base and quote currencies
            base_curr, quote_curr = self._extract_currencies(symbol)
            
            # Get currency strength
            base_strength = self._get_currency_strength(base_curr)
            quote_strength = self._get_currency_strength(quote_curr)
            
            # Calculate relative strength
            relative_strength = base_strength - quote_strength
            
            # Check for upcoming high-impact events
            upcoming_events = self._check_upcoming_events(base_curr, quote_curr)
            
            # Analyze market hours (trading activity)
            session_impact = self._analyze_trading_session(symbol)
            
            # Determine sentiment
            sentiment = self._determine_sentiment(relative_strength)
            
            # Calculate fundamental bias
            fundamental_bias = self._calculate_fundamental_bias(
                relative_strength,
                upcoming_events,
                market_state
            )
            
            # Check if should avoid trading
            avoid_trading = self._should_avoid_trading(upcoming_events, market_state)
            
            fundamental_analysis = {
                'sentiment': sentiment,
                'strength_score': 50 + relative_strength,  # Normalize to 0-100
                'base_currency': base_curr,
                'quote_currency': quote_curr,
                'base_strength': base_strength,
                'quote_strength': quote_strength,
                'relative_strength': relative_strength,
                'upcoming_events': upcoming_events,
                'session_impact': session_impact,
                'news_impact': self._assess_news_impact(upcoming_events),
                'avoid_trading': avoid_trading,
                'fundamental_bias': fundamental_bias,
                'confidence': self._calculate_fundamental_confidence(
                    relative_strength, 
                    upcoming_events,
                    session_impact
                )
            }
            
            logger.debug(f"Fundamental analysis for {symbol}: {sentiment}, bias: {fundamental_bias}")
            
            return fundamental_analysis
            
        except Exception as e:
            logger.error(f"Error in fundamental analysis for {symbol}: {e}")
            return self._get_neutral_analysis()
    
    def _extract_currencies(self, symbol: str) -> tuple:
        """Extract base and quote currencies from symbol"""
        # Remove trailing 'm' if present (Exness notation)
        clean_symbol = symbol.replace('m', '')
        
        # Handle special cases
        if 'XAU' in clean_symbol:
            return 'GOLD', 'USD'
        elif 'XAG' in clean_symbol:
            return 'SILVER', 'USD'
        elif 'BTC' in clean_symbol:
            return 'BTC', 'USD'
        elif 'US30' in clean_symbol or 'US100' in clean_symbol or 'US500' in clean_symbol:
            return 'US_INDEX', 'USD'
        
        # Standard forex pairs
        if len(clean_symbol) >= 6:
            base = clean_symbol[:3]
            quote = clean_symbol[3:6]
            return base, quote
        
        return 'UNKNOWN', 'UNKNOWN'
    
    def _get_currency_strength(self, currency: str) -> float:
        """Get current currency strength (0-100)"""
        if currency in self.currency_strength:
            return self.currency_strength[currency]['score']
        
        # For commodities/indices, use market conditions
        if currency in ['GOLD', 'SILVER']:
            return 55  # Slightly bullish (safe haven)
        elif currency == 'BTC':
            return 50  # Neutral
        elif currency == 'US_INDEX':
            return 52  # Slightly bullish
        
        return 50  # Neutral default
    
    def _check_upcoming_events(self, base_curr: str, quote_curr: str) -> List[Dict]:
        """Check for upcoming high-impact economic events"""
        # This would ideally fetch from an economic calendar API
        # For now, use time-based logic for common events
        
        upcoming = []
        now = datetime.now()
        hour = now.hour
        day = now.weekday()
        
        # NFP (First Friday of month, 8:30 AM EST = 13:30 UTC)
        if day == 4 and 1 <= now.day <= 7:
            if 12 <= hour <= 14:
                upcoming.append({
                    'currency': 'USD',
                    'event': 'NFP',
                    'impact': 'high',
                    'time': '13:30 UTC'
                })
        
        # FOMC (typically 14:00 EST = 19:00 UTC on Wednesday)
        if day == 2 and 18 <= hour <= 20:
            upcoming.append({
                'currency': 'USD',
                'event': 'FOMC',
                'impact': 'high',
                'time': '19:00 UTC'
            })
        
        # CPI releases (usually 8:30 AM EST = 13:30 UTC)
        if 12 <= hour <= 14:
            if day == 2:  # Wednesday
                upcoming.append({
                    'currency': base_curr,
                    'event': 'CPI',
                    'impact': 'high',
                    'time': '13:30 UTC'
                })
        
        return upcoming
    
    def _analyze_trading_session(self, symbol: str) -> Dict:
        """Analyze which trading session is active"""
        now = datetime.utcnow()
        hour = now.hour
        
        # London session: 08:00-16:00 UTC
        london_active = 8 <= hour < 16
        
        # New York session: 13:00-21:00 UTC
        ny_active = 13 <= hour < 21
        
        # Tokyo session: 00:00-08:00 UTC
        tokyo_active = 0 <= hour < 8
        
        # Sydney session: 22:00-06:00 UTC
        sydney_active = hour >= 22 or hour < 6
        
        # Overlap = high liquidity
        overlap = london_active and ny_active
        
        # Determine primary session
        if overlap:
            primary_session = 'london_ny_overlap'
            liquidity = 'very_high'
        elif london_active:
            primary_session = 'london'
            liquidity = 'high'
        elif ny_active:
            primary_session = 'new_york'
            liquidity = 'high'
        elif tokyo_active:
            primary_session = 'tokyo'
            liquidity = 'medium'
        elif sydney_active:
            primary_session = 'sydney'
            liquidity = 'low'
        else:
            primary_session = 'none'
            liquidity = 'very_low'
        
        return {
            'primary_session': primary_session,
            'liquidity': liquidity,
            'london_active': london_active,
            'ny_active': ny_active,
            'tokyo_active': tokyo_active,
            'overlap': overlap
        }
    
    def _determine_sentiment(self, relative_strength: float) -> str:
        """Determine market sentiment based on relative strength"""
        if relative_strength > 10:
            return 'strongly_bullish'
        elif relative_strength > 5:
            return 'bullish'
        elif relative_strength < -10:
            return 'strongly_bearish'
        elif relative_strength < -5:
            return 'bearish'
        else:
            return 'neutral'
    
    def _calculate_fundamental_bias(self, relative_strength: float, 
                                     events: List[Dict], 
                                     market_state: Dict) -> str:
        """Calculate fundamental trading bias"""
        # Strong fundamental bias
        if relative_strength > 10:
            return 'BUY'
        elif relative_strength < -10:
            return 'SELL'
        
        # Medium bias (requires confirmation from technical)
        if relative_strength > 5:
            bias = 'BUY'
        elif relative_strength < -5:
            bias = 'SELL'
        else:
            return 'NEUTRAL'
        
        # Check if technical confirms
        technical_bias = market_state.get('bias', 'NEUTRAL')
        
        if technical_bias == bias:
            return bias  # Alignment = strong signal
        else:
            return 'NEUTRAL'  # Divergence = wait
    
    def _should_avoid_trading(self, events: List[Dict], market_state: Dict) -> bool:
        """Determine if trading should be avoided"""
        # Avoid during high-impact news
        for event in events:
            if event['impact'] == 'high':
                return True
        
        # Avoid during very low liquidity
        session = self._analyze_trading_session('')
        if session['liquidity'] == 'very_low':
            return True
        
        # Avoid during extreme volatility
        volatility = market_state.get('volatility', 'MEDIUM')
        if volatility == 'EXTREME':
            return True
        
        return False
    
    def _assess_news_impact(self, events: List[Dict]) -> str:
        """Assess overall news impact"""
        if not events:
            return 'low'
        
        high_impact_count = sum(1 for e in events if e['impact'] == 'high')
        
        if high_impact_count > 0:
            return 'high'
        elif len(events) > 2:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_fundamental_confidence(self, relative_strength: float,
                                          events: List[Dict],
                                          session: Dict) -> float:
        """Calculate confidence in fundamental analysis (0-100)"""
        confidence = 50.0
        
        # Strong currency divergence increases confidence
        if abs(relative_strength) > 10:
            confidence += 20
        elif abs(relative_strength) > 5:
            confidence += 10
        
        # High liquidity sessions increase confidence
        if session['liquidity'] == 'very_high':
            confidence += 15
        elif session['liquidity'] == 'high':
            confidence += 10
        
        # Upcoming high-impact events decrease confidence
        high_impact = sum(1 for e in events if e['impact'] == 'high')
        confidence -= high_impact * 10
        
        return max(0, min(100, confidence))
    
    def _get_neutral_analysis(self) -> Dict:
        """Return neutral analysis on error"""
        return {
            'sentiment': 'neutral',
            'strength_score': 50,
            'base_currency': 'UNKNOWN',
            'quote_currency': 'UNKNOWN',
            'base_strength': 50,
            'quote_strength': 50,
            'relative_strength': 0,
            'upcoming_events': [],
            'session_impact': {'primary_session': 'none', 'liquidity': 'low'},
            'news_impact': 'low',
            'avoid_trading': False,
            'fundamental_bias': 'NEUTRAL',
            'confidence': 50
        }
    
    def update_currency_strength(self, currency: str, score: float, trend: str):
        """Update currency strength (would be called from external data feed)"""
        if currency in self.currency_strength:
            self.currency_strength[currency] = {
                'score': max(0, min(100, score)),
                'trend': trend,
                'last_update': datetime.now()
            }
            logger.info(f"Updated {currency} strength: {score} ({trend})")
    
    def get_currency_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calculate correlation between two symbols"""
        # This would ideally use historical price data
        # For now, use currency-based logic
        
        base1, quote1 = self._extract_currencies(symbol1)
        base2, quote2 = self._extract_currencies(symbol2)
        
        # Same pair = perfect correlation
        if base1 == base2 and quote1 == quote2:
            return 1.0
        
        # Inverse pair = perfect negative correlation
        if base1 == quote2 and quote1 == base2:
            return -1.0
        
        # Shared currency = partial correlation
        if base1 == base2 or quote1 == quote2:
            return 0.5
        elif base1 == quote2 or quote1 == base2:
            return -0.5
        
        # No shared currency = low correlation
        return 0.0