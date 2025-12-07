"""
Machine Learning Engine
Trains on signal performance and improves predictions over time
"""

import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
from src.utils.logger import setup_logger
from src.utils.database import Database

logger = setup_logger(__name__)


class MLEngine:
    """Machine learning engine for signal quality prediction"""
    
    def __init__(self, config):
        self.config = config
        self.model = None
        self.scaler = None
        self.db = Database(config.DB_PATH)
        self.signal_count = 0
        self.training_threshold = config.ML_TRAINING_THRESHOLD
        
    async def initialize(self):
        """Initialize ML engine"""
        try:
            # Load existing model if available
            if os.path.exists(self.config.ML_MODEL_PATH):
                await self.load_model()
                logger.info("Loaded existing ML model")
            else:
                # Initialize new model
                self.model = GradientBoostingClassifier(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=5,
                    random_state=42
                )
                self.scaler = StandardScaler()
                logger.info("Initialized new ML model")
            
            # Get current signal count
            self.signal_count = await self.db.get_signal_count()
            
            logger.info(f"ML Engine initialized. Signals in database: {self.signal_count}")
            
        except Exception as e:
            logger.error(f"Error initializing ML engine: {e}", exc_info=True)
    
    async def predict_signal_quality(self, market_state: Dict) -> float:
        """Predict signal quality (confidence 0-100)"""
        try:
            # Extract features
            features = self._extract_features(market_state)
            
            # If model not trained yet, use rule-based confidence
            if self.model is None or not hasattr(self.model, 'classes_'):
                return self._calculate_baseline_confidence(market_state)
            
            # Scale features
            features_scaled = self.scaler.transform([features])
            
            # Get prediction probability
            probabilities = self.model.predict_proba(features_scaled)[0]
            
            # Return confidence for positive class (successful trade)
            confidence = probabilities[1] * 100 if len(probabilities) > 1 else 50.0
            
            return float(confidence)
            
        except Exception as e:
            logger.error(f"Error predicting signal quality: {e}", exc_info=True)
            return 50.0
    
    async def store_signal(self, signal: Dict):
        """Store signal for future training"""
        try:
            await self.db.insert_signal(signal)
            self.signal_count += 1
            
            logger.info(f"Signal stored. Total signals: {self.signal_count}")
            
            # Check if training threshold reached
            if self.signal_count % self.training_threshold == 0:
                logger.info(f"Training threshold reached ({self.training_threshold}). Starting training...")
                await self.train_model()
                
        except Exception as e:
            logger.error(f"Error storing signal: {e}", exc_info=True)
    
    async def update_signal_outcome(self, signal_id: int, outcome: str, profit_loss: float):
        """Update signal with actual outcome"""
        try:
            await self.db.update_signal_outcome(signal_id, outcome, profit_loss)
            logger.info(f"Signal {signal_id} updated with outcome: {outcome}")
            
        except Exception as e:
            logger.error(f"Error updating signal outcome: {e}", exc_info=True)
    
    async def train_model(self):
        """Train ML model on historical signals"""
        try:
            logger.info("Starting ML model training...")
            
            # Get training data
            signals = await self.db.get_all_signals_with_outcomes()
            
            if len(signals) < 20:
                logger.warning(f"Not enough data for training. Have {len(signals)}, need at least 20")
                return
            
            # Prepare training data
            X = []
            y = []
            
            for signal in signals:
                features = self._extract_features_from_signal(signal)
                X.append(features)
                
                # Label: 1 for successful trade (profit), 0 for loss
                outcome = 1 if signal.get('outcome') == 'WIN' else 0
                y.append(outcome)
            
            X = np.array(X)
            y = np.array(y)
            
            # Handle case where all outcomes are the same
            if len(np.unique(y)) < 2:
                logger.warning("All signals have same outcome. Cannot train model.")
                return
            
            # Split data
            if len(X) > 40:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42, stratify=y
                )
            else:
                X_train, X_test, y_train, y_test = X, X, y, y
            
            # Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            try:
                precision = precision_score(y_test, y_pred, zero_division=0)
                recall = recall_score(y_test, y_pred, zero_division=0)
            except:
                precision = 0.0
                recall = 0.0
            
            logger.info(f"Model trained successfully. Accuracy: {accuracy:.2%}, "
                       f"Precision: {precision:.2%}, Recall: {recall:.2%}")
            
            # Save model
            await self.save_model()
            
            # Store training metrics
            await self.db.store_training_metrics({
                'timestamp': datetime.now(),
                'samples': len(X),
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall
            })
            
        except Exception as e:
            logger.error(f"Error training model: {e}", exc_info=True)
    
    def _extract_features(self, market_state: Dict) -> List[float]:
        """Extract features from market state"""
        try:
            features = []
            
            # Volatility
            volatility_map = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
            features.append(volatility_map.get(market_state.get('volatility', 'MEDIUM'), 1))
            
            # ATR (normalized)
            atr = market_state.get('atr', 0)
            features.append(min(atr * 1000, 100))  # Scale to 0-100 range
            
            # RSI
            features.append(market_state.get('rsi', 50))
            
            # Trend strength
            features.append(market_state.get('trend_strength', 50))
            
            # Volume ratio
            features.append(market_state.get('volume_ratio', 1.0))
            
            # FVG size (if exists)
            fvgs = market_state.get('fvgs', [])
            fvg_size = fvgs[0].get('size', 0) if fvgs else 0
            features.append(min(fvg_size * 10000, 100))
            
            # Order block strength (if exists)
            order_blocks = market_state.get('order_blocks', [])
            ob_strength = order_blocks[0].get('strength', 0) if order_blocks else 0
            features.append(min(ob_strength * 10, 100))
            
            # Displacement size
            displacement = market_state.get('m1_displacement', {})
            disp_strength = displacement.get('strength', 0) if displacement.get('detected') else 0
            features.append(min(disp_strength * 10, 100))
            
            # Liquidity distance (normalized)
            features.append(50)  # Placeholder
            
            # Time of day (hour)
            features.append(datetime.now().hour)
            
            # Day of week
            features.append(datetime.now().weekday())
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}", exc_info=True)
            return [0] * 11  # Return default features
    
    def _extract_features_from_signal(self, signal: Dict) -> List[float]:
        """Extract features from stored signal"""
        try:
            features = []
            
            # Map volatility
            volatility_map = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
            features.append(volatility_map.get(signal.get('volatility', 'MEDIUM'), 1))
            
            # ATR
            features.append(min(signal.get('atr', 0) * 1000, 100))
            
            # RSI
            features.append(signal.get('rsi', 50))
            
            # Trend strength
            features.append(signal.get('trend_strength', 50))
            
            # Volume ratio
            features.append(signal.get('volume_ratio', 1.0))
            
            # FVG size
            features.append(signal.get('fvg_size', 0))
            
            # OB strength
            features.append(signal.get('ob_strength', 0))
            
            # Displacement strength
            features.append(signal.get('displacement_strength', 0))
            
            # Liquidity distance
            features.append(50)
            
            # Time features
            timestamp = signal.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            features.append(timestamp.hour)
            features.append(timestamp.weekday())
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features from signal: {e}")
            return [0] * 11
    
    def _calculate_baseline_confidence(self, market_state: Dict) -> float:
        """Calculate rule-based confidence when ML model not available"""
        try:
            confidence = 50.0
            
            # Trend alignment
            trend = market_state.get('htf_trend', 'NEUTRAL')
            if 'STRONG' in trend:
                confidence += 20
            elif trend != 'NEUTRAL':
                confidence += 10
            
            # Structure confirmation
            if market_state.get('htf_structure', {}).get('bos_detected'):
                confidence += 10
            
            # Setup quality
            fvgs = market_state.get('fvgs', [])
            order_blocks = market_state.get('order_blocks', [])
            
            if fvgs and order_blocks:
                confidence += 15
            elif fvgs or order_blocks:
                confidence += 8
            
            # Kill zone
            if market_state.get('in_kill_zone'):
                confidence += 5
            
            return min(confidence, 95.0)
            
        except Exception as e:
            logger.error(f"Error calculating baseline confidence: {e}")
            return 50.0
    
    async def save_model(self):
        """Save ML model to disk"""
        try:
            os.makedirs(os.path.dirname(self.config.ML_MODEL_PATH), exist_ok=True)
            
            with open(self.config.ML_MODEL_PATH, 'wb') as f:
                pickle.dump(self.model, f)
            
            with open(self.config.ML_SCALER_PATH, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            logger.info("ML model saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving ML model: {e}", exc_info=True)
    
    async def load_model(self):
        """Load ML model from disk"""
        try:
            with open(self.config.ML_MODEL_PATH, 'rb') as f:
                self.model = pickle.load(f)
            
            with open(self.config.ML_SCALER_PATH, 'rb') as f:
                self.scaler = pickle.load(f)
            
            logger.info("ML model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading ML model: {e}", exc_info=True)
            # Initialize new model if loading fails
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
            self.scaler = StandardScaler()
    
    async def get_model_stats(self) -> Dict:
        """Get ML model statistics"""
        try:
            stats = {
                'total_signals': self.signal_count,
                'model_trained': self.model is not None and hasattr(self.model, 'classes_'),
                'next_training': self.training_threshold - (self.signal_count % self.training_threshold)
            }
            
            # Get latest training metrics
            metrics = await self.db.get_latest_training_metrics()
            if metrics:
                stats.update(metrics)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting model stats: {e}")
            return {}