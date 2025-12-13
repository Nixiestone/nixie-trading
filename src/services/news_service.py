"""
News Service Module
Handles news fetching, scheduling, and notifications
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

class NewsService:
    """Manages news events and notifications"""
    
    def __init__(self, config, telegram_handler):
        self.config = config
        self.telegram = telegram_handler
        self.scheduler = BackgroundScheduler(timezone=pytz.UTC)
        self.news_cache = []
        self.last_fetch = None
        self.notified_events = set()
        self.api_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        
    def start(self):
        """Start the news service"""
        try:
            # Schedule daily news report at 8 AM user time
            self.scheduler.add_job(
                self.send_daily_news_report,
                CronTrigger(hour=8, minute=0),
                id='daily_news_report',
                misfire_grace_time=3600  # Allow 1 hour grace period
            )
            
            # Check for upcoming news every 5 minutes
            self.scheduler.add_job(
                self.check_upcoming_news,
                'interval',
                minutes=5,
                id='news_reminder',
                misfire_grace_time=300  # 5 minute grace period
            )
            
            # Fetch news every hour
            self.scheduler.add_job(
                self.fetch_news,
                'interval',
                hours=1,
                id='news_fetch',
                misfire_grace_time=1800  # 30 minute grace period
            )
            
            self.scheduler.start()
            logger.info("News service started successfully")
            
            # Initial news fetch
            self.fetch_news()
            
        except Exception as e:
            logger.error(f"Failed to start news service: {e}")
    
    def fetch_news(self) -> List[Dict]:
        """Fetch news from ForexFactory"""
        try:
            response = requests.get(self.api_url, timeout=10)
            if response.status_code == 200:
                raw_news = response.json()
                self.news_cache = self._parse_news(raw_news)
                self.last_fetch = datetime.now(pytz.UTC)
                logger.info(f"Fetched {len(self.news_cache)} news events")
                return self.news_cache
            else:
                logger.error(f"Failed to fetch news: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []
    
    def _parse_news(self, raw_news: List[Dict]) -> List[Dict]:
        """Parse and filter news events"""
        parsed_news = []
        
        for event in raw_news:
            try:
                impact = event.get('impact', '').lower()
                if impact not in ['high', 'medium']:
                    continue
                
                date_str = event.get('date', '')
                time_str = event.get('time', '')
                
                if not date_str or not time_str:
                    continue
                
                event_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                event_dt = pytz.UTC.localize(event_dt)
                
                parsed_news.append({
                    'title': event.get('title', 'Unknown'),
                    'country': event.get('country', ''),
                    'impact': impact.upper(),
                    'datetime': event_dt,
                    'forecast': event.get('forecast', 'N/A'),
                    'previous': event.get('previous', 'N/A'),
                    'actual': event.get('actual', None)
                })
                
            except Exception as e:
                logger.warning(f"Failed to parse news event: {e}")
                continue
        
        return sorted(parsed_news, key=lambda x: x['datetime'])
    
    def get_todays_red_folder_news(self, timezone_str: str = "UTC") -> List[Dict]:
        """Get all high-impact news for today"""
        try:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            todays_news = [
                news for news in self.news_cache
                if today_start <= news['datetime'].astimezone(tz) < today_end
                and news['impact'] in ['HIGH', 'MEDIUM']
            ]
            
            return todays_news
            
        except Exception as e:
            logger.error(f"Error getting today's news: {e}")
            return []
    
    def send_daily_news_report(self):
        """Send daily news report at 8 AM"""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_send_daily_report())
            loop.close()
        except Exception as e:
            logger.error(f"Error sending daily news report: {e}")
    
    async def _async_send_daily_report(self):
        """Async daily report sender"""
        try:
            subscribers = await self.telegram._async_get_all_subscribers()
            
            for subscriber in subscribers:
                user_id = subscriber['user_id']
                timezone = subscriber.get('timezone', 'UTC')
                
                user_tz = pytz.timezone(timezone)
                user_time = datetime.now(user_tz)
                
                if user_time.hour != 8:
                    continue
                
                news = self.get_todays_red_folder_news(timezone)
                
                if not news:
                    message = "📰 *Daily News Report*\n\nNo high-impact news scheduled for today. ✅"
                else:
                    message = "🚨 *Daily Red Folder News Report*\n\n"
                    message += f"📅 {user_time.strftime('%A, %B %d, %Y')}\n\n"
                    
                    for i, event in enumerate(news, 1):
                        event_time = event['datetime'].astimezone(user_tz)
                        message += f"*{i}. {event['title']}*\n"
                        message += f"   🌍 {event['country']} | ⚠️ {event['impact']}\n"
                        message += f"   ⏰ {event_time.strftime('%I:%M %p')}\n"
                        message += f"   📊 Forecast: {event['forecast']} | Previous: {event['previous']}\n\n"
                    
                    message += "\n💡 You'll receive reminders 10 minutes before each event."
                
                await self.telegram._async_send_message(user_id, message)
                
            logger.info(f"Sent daily news report to {len(subscribers)} subscribers")
        except Exception as e:
            logger.error(f"Error in async daily report: {e}")
    
    def check_upcoming_news(self):
        """Check for news events in the next 10 minutes"""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_check_news())
            loop.close()
        except Exception as e:
            logger.error(f"Error checking upcoming news: {e}")
    
    async def _async_check_news(self):
        """Async news checker"""
        try:
            now = datetime.now(pytz.UTC)
            
            for news in self.news_cache:
                time_diff = (news['datetime'] - now).total_seconds() / 60
                event_id = f"{news['title']}_{news['datetime'].isoformat()}"
                
                if 8 <= time_diff <= 12:
                    reminder_id = f"reminder_{event_id}"
                    if reminder_id not in self.notified_events:
                        await self._send_news_reminder(news)
                        self.notified_events.add(reminder_id)
                
                if -2 <= time_diff <= 2:
                    live_id = f"live_{event_id}"
                    if live_id not in self.notified_events:
                        await self._send_live_news_notification(news)
                        self.notified_events.add(live_id)
        except Exception as e:
            logger.error(f"Error in async check news: {e}")
    
    async def _send_news_reminder(self, news: Dict):
        """Send 10-minute reminder"""
        try:
            subscribers = await self.telegram._async_get_all_subscribers()
            
            for subscriber in subscribers:
                timezone = subscriber.get('timezone', 'UTC')
                event_time = news['datetime'].astimezone(pytz.timezone(timezone))
                
                message = "⏰ *News Reminder*\n\n"
                message += f"📰 {news['title']}\n"
                message += f"🌍 {news['country']} | ⚠️ {news['impact']} Impact\n"
                message += f"⏰ Starting in 10 minutes at {event_time.strftime('%I:%M %p')}\n\n"
                message += f"📊 Forecast: {news['forecast']}\n"
                message += f"📈 Previous: {news['previous']}\n\n"
                message += "⚠️ Trading may be volatile. Use caution!"
                
                await self.telegram._async_send_message(subscriber['user_id'], message)
                
            logger.info(f"Sent news reminder: {news['title']}")
        except Exception as e:
            logger.error(f"Error sending news reminder: {e}")
    
    async def _send_live_news_notification(self, news: Dict):
        """Send live news notification"""
        try:
            subscribers = await self.telegram._async_get_all_subscribers()
            self.fetch_news()
            
            updated_news = next(
                (n for n in self.news_cache if n['title'] == news['title'] 
                 and n['datetime'] == news['datetime']), 
                news
            )
            
            actual = updated_news.get('actual', 'Pending...')
            forecast = updated_news['forecast']
            prediction = self._analyze_prediction(forecast, actual)
            
            for subscriber in subscribers:
                message = "📢 *LIVE NEWS EVENT*\n\n"
                message += f"📰 {updated_news['title']}\n"
                message += f"🌍 {updated_news['country']} | ⚠️ {updated_news['impact']} Impact\n\n"
                message += f"🎯 Forecast: {forecast}\n"
                message += f"📊 Actual: {actual}\n"
                message += f"📈 Previous: {updated_news['previous']}\n\n"
                message += f"*Prediction: {prediction}*\n\n"
                message += "⚠️ High volatility expected!"
                
                await self.telegram._async_send_message(subscriber['user_id'], message)
                
            logger.info(f"Sent live news notification: {updated_news['title']}")
        except Exception as e:
            logger.error(f"Error sending live news notification: {e}")
    
    def _analyze_prediction(self, forecast: str, actual: str) -> str:
        """Analyze if actual beats/misses forecast"""
        try:
            if actual == 'Pending...' or actual == 'N/A':
                return "⏳ Data pending"
            
            forecast_val = float(forecast.replace('%', '').replace('K', '000').replace('M', '000000').replace('B', '000000000'))
            actual_val = float(actual.replace('%', '').replace('K', '000').replace('M', '000000').replace('B', '000000000'))
            
            if actual_val > forecast_val:
                return "📈 BETTER than forecast (Bullish)"
            elif actual_val < forecast_val:
                return "📉 WORSE than forecast (Bearish)"
            else:
                return "➡️ IN LINE with forecast (Neutral)"
        except:
            return "❓ Unable to compare"
    
    def is_news_blackout_period(self) -> bool:
        """Check if we're in a news blackout period"""
        try:
            if not hasattr(self.config, 'ALLOW_TRADING_DURING_NEWS'):
                return False
                
            if self.config.ALLOW_TRADING_DURING_NEWS:
                return False
            
            now = datetime.now(pytz.UTC)
            blackout_before = getattr(self.config, 'NEWS_BLACKOUT_MINUTES_BEFORE', 15)
            blackout_after = getattr(self.config, 'NEWS_BLACKOUT_MINUTES_AFTER', 15)
            
            for news in self.news_cache:
                if news['impact'] != 'HIGH':
                    continue
                
                time_diff = (news['datetime'] - now).total_seconds() / 60
                
                if -blackout_after <= time_diff <= blackout_before:
                    logger.info(f"News blackout active: {news['title']} in {time_diff:.1f} minutes")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking news blackout: {e}")
            return False
    
    def stop(self):
        """Stop the news service"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)  # Don't wait for jobs to complete
                logger.info("News service stopped")
        except Exception as e:
            logger.error(f"Error stopping news service: {e}")