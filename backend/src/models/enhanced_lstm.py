"""
Enhanced LSTM Model for Casablanca Traffic Prediction.

Uses the full dataset including:
- Temporal features (hour, day_of_week, is_weekend, is_rush_hour)
- OD pair features (origin, destination, distance)
- Zone features (population, transit, roads, land use)
- Historical TTI patterns
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import pickle
import logging
import os

from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

# TensorFlow imports
TF_AVAILABLE = False
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Model, load_model
    from tensorflow.keras.layers import (
        Input, LSTM, Dense, Dropout, BatchNormalization,
        Embedding, Concatenate, Flatten, Bidirectional
    )
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
    from tensorflow.keras.optimizers import Adam
    TF_AVAILABLE = True
    logger.info("TensorFlow loaded successfully")
except ImportError:
    logger.warning("TensorFlow not available")


class EnhancedTrafficLSTM:
    """
    Enhanced LSTM model with zone embeddings for traffic prediction.
    
    Architecture:
    - Point embeddings for origin/destination (learnable)
    - Zone features (population, transit, land use)
    - Temporal features (hour, day, weekend, rush hour)
    - Bidirectional LSTM for sequence patterns
    - Dense layers for final prediction
    """
    
    def __init__(
        self,
        sequence_length: int = 12,
        n_points: int = 110,
        embedding_dim: int = 16
    ):
        self.sequence_length = sequence_length
        self.n_points = n_points
        self.embedding_dim = embedding_dim
        self.model = None
        
        # Scalers for different feature groups
        self.scaler_temporal = MinMaxScaler()
        self.scaler_zone = MinMaxScaler()
        self.scaler_target = MinMaxScaler()
        
        # Feature column definitions
        self.temporal_cols = ['hour', 'day_of_week', 'is_weekend', 'is_rush_hour']
        self.zone_cols = [
            'origin_population', 'origin_density', 'origin_tram_stations', 'origin_bus_stations',
            'origin_primary_roads', 'origin_highways', 'origin_industrial_pct',
            'origin_residential_pct', 'origin_university_pct', 'origin_commercial_buildings',
            'dest_population', 'dest_density', 'dest_tram_stations', 'dest_bus_stations',
            'dest_primary_roads', 'dest_highways', 'dest_industrial_pct',
            'dest_residential_pct', 'dest_university_pct', 'dest_commercial_buildings',
            'distance_km'
        ]
        self.target_col = 'tti'
        
        # Model path
        self.model_dir = Path('models/enhanced_lstm')
    
    def build(self) -> Optional[Model]:
        """Build enhanced LSTM model with embeddings."""
        if not TF_AVAILABLE:
            logger.error("TensorFlow required for model building")
            return None
        
        # Input layers
        # Origin point embedding
        origin_input = Input(shape=(1,), name='origin_idx')
        origin_embed = Embedding(self.n_points, self.embedding_dim, name='origin_embedding')(origin_input)
        origin_embed = Flatten()(origin_embed)
        
        # Destination point embedding
        dest_input = Input(shape=(1,), name='dest_idx')
        dest_embed = Embedding(self.n_points, self.embedding_dim, name='dest_embedding')(dest_input)
        dest_embed = Flatten()(dest_embed)
        
        # Temporal features input (hour, day, weekend, rush_hour)
        temporal_input = Input(shape=(len(self.temporal_cols),), name='temporal_features')
        
        # Zone features input (population, transit, land use for origin & dest)
        zone_input = Input(shape=(len(self.zone_cols),), name='zone_features')
        
        # Historical TTI sequence input
        sequence_input = Input(shape=(self.sequence_length, 1), name='tti_sequence')
        
        # Process sequence with Bidirectional LSTM
        lstm_out = Bidirectional(LSTM(64, return_sequences=True))(sequence_input)
        lstm_out = BatchNormalization()(lstm_out)
        lstm_out = Dropout(0.3)(lstm_out)
        lstm_out = LSTM(32, return_sequences=False)(lstm_out)
        lstm_out = BatchNormalization()(lstm_out)
        lstm_out = Dropout(0.2)(lstm_out)
        
        # Combine all features
        combined = Concatenate()([
            origin_embed,
            dest_embed,
            temporal_input,
            zone_input,
            lstm_out
        ])
        
        # Dense layers
        x = Dense(128, activation='relu')(combined)
        x = BatchNormalization()(x)
        x = Dropout(0.3)(x)
        x = Dense(64, activation='relu')(x)
        x = BatchNormalization()(x)
        x = Dropout(0.2)(x)
        x = Dense(32, activation='relu')(x)
        
        # Output: TTI prediction
        output = Dense(1, activation='linear', name='tti_output')(x)
        
        # Build model
        self.model = Model(
            inputs=[origin_input, dest_input, temporal_input, zone_input, sequence_input],
            outputs=output
        )
        
        self.model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        logger.info(f"Model built with {self.model.count_params():,} parameters")
        return self.model
    
    def prepare_data(
        self,
        df: pd.DataFrame,
        fit_scalers: bool = True
    ) -> Tuple[Dict[str, np.ndarray], np.ndarray]:
        """
        Prepare data for training/prediction.
        
        Returns:
            inputs: Dict with keys 'origin_idx', 'dest_idx', 'temporal_features', 
                   'zone_features', 'tti_sequence'
            targets: TTI values
        """
        df = df.copy()
        
        # Ensure required columns exist
        for col in self.zone_cols:
            if col not in df.columns:
                df[col] = 0
        
        # Scale temporal features
        temporal_data = df[self.temporal_cols].values
        if fit_scalers:
            temporal_data = self.scaler_temporal.fit_transform(temporal_data)
        else:
            temporal_data = self.scaler_temporal.transform(temporal_data)
        
        # Scale zone features
        zone_data = df[self.zone_cols].values
        if fit_scalers:
            zone_data = self.scaler_zone.fit_transform(zone_data)
        else:
            zone_data = self.scaler_zone.transform(zone_data)
        
        # Create sequences per OD pair
        # Group by origin-destination and create TTI sequences
        sequences = []
        origins = []
        dests = []
        temporals = []
        zones = []
        targets = []
        
        # Sort by day and hour for proper sequencing
        df_sorted = df.sort_values(['origin_idx', 'destination_idx', 'day_of_week', 'hour'])
        
        for (origin, dest), group in df_sorted.groupby(['origin_idx', 'destination_idx']):
            tti_values = group[self.target_col].values
            
            # Create sequences
            for i in range(len(group) - self.sequence_length):
                seq = tti_values[i:i + self.sequence_length]
                target = tti_values[i + self.sequence_length]
                
                # Get the target row for other features
                target_idx = group.index[i + self.sequence_length]
                row_idx = df_sorted.index.get_loc(target_idx)
                
                sequences.append(seq.reshape(-1, 1))
                origins.append(origin)
                dests.append(dest)
                temporals.append(temporal_data[row_idx])
                zones.append(zone_data[row_idx])
                targets.append(target)
        
        inputs = {
            'origin_idx': np.array(origins),
            'dest_idx': np.array(dests),
            'temporal_features': np.array(temporals),
            'zone_features': np.array(zones),
            'tti_sequence': np.array(sequences)
        }
        
        targets = np.array(targets)
        
        # Scale targets
        if fit_scalers:
            targets = self.scaler_target.fit_transform(targets.reshape(-1, 1)).flatten()
        else:
            targets = self.scaler_target.transform(targets.reshape(-1, 1)).flatten()
        
        return inputs, targets
    
    def train(
        self,
        df: pd.DataFrame,
        epochs: int = 100,
        batch_size: int = 64,
        validation_split: float = 0.2
    ) -> Dict:
        """Train the model on the full dataset."""
        if not TF_AVAILABLE:
            return {'error': 'TensorFlow not available'}
        
        if self.model is None:
            self.build()
        
        logger.info("Preparing training data...")
        inputs, targets = self.prepare_data(df, fit_scalers=True)
        
        logger.info(f"Training samples: {len(targets)}")
        
        # Create model directory
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Callbacks
        callbacks = [
            EarlyStopping(
                patience=15,
                restore_best_weights=True,
                monitor='val_loss',
                verbose=1
            ),
            ReduceLROnPlateau(
                factor=0.5,
                patience=5,
                min_lr=1e-6,
                verbose=1
            ),
            ModelCheckpoint(
                str(self.model_dir / 'best_model.keras'),
                save_best_only=True,
                monitor='val_loss'
            )
        ]
        
        # Train
        history = self.model.fit(
            inputs,
            targets,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=callbacks,
            verbose=1
        )
        
        # Evaluate
        val_loss = min(history.history['val_loss'])
        val_mae = min(history.history['val_mae'])
        
        # Save scalers
        self._save_scalers()
        
        return {
            'val_loss': float(val_loss),
            'val_mae': float(val_mae),
            'epochs_trained': len(history.history['loss']),
            'samples_trained': len(targets),
            'model_path': str(self.model_dir)
        }
    
    def predict(
        self,
        origin_idx: int,
        dest_idx: int,
        hour: int,
        day_of_week: int,
        zone_features: Dict[str, float],
        historical_tti: List[float]
    ) -> Dict:
        """
        Predict TTI for a specific OD pair and time.
        
        Args:
            origin_idx: Origin point index (0-109)
            dest_idx: Destination point index (0-109)
            hour: Hour of day (0-23)
            day_of_week: Day of week (0=Monday, 6=Sunday)
            zone_features: Dict with zone feature values
            historical_tti: List of last 12 TTI values
        
        Returns:
            Dict with predicted TTI, congestion level, confidence
        """
        if self.model is None:
            return {'error': 'Model not loaded'}
        
        # Prepare temporal features
        is_weekend = 1 if day_of_week >= 5 else 0
        is_rush_hour = 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0
        
        temporal = np.array([[hour, day_of_week, is_weekend, is_rush_hour]])
        temporal_scaled = self.scaler_temporal.transform(temporal)
        
        # Prepare zone features
        zone_values = [zone_features.get(col, 0) for col in self.zone_cols]
        zone = np.array([zone_values])
        zone_scaled = self.scaler_zone.transform(zone)
        
        # Prepare sequence (pad if needed)
        if len(historical_tti) < self.sequence_length:
            padding = [historical_tti[0]] * (self.sequence_length - len(historical_tti))
            historical_tti = padding + list(historical_tti)
        
        sequence = np.array(historical_tti[-self.sequence_length:]).reshape(1, self.sequence_length, 1)
        
        # Predict
        inputs = {
            'origin_idx': np.array([[origin_idx]]),
            'dest_idx': np.array([[dest_idx]]),
            'temporal_features': temporal_scaled,
            'zone_features': zone_scaled,
            'tti_sequence': sequence
        }
        
        pred_scaled = self.model.predict(inputs, verbose=0)
        pred_tti = self.scaler_target.inverse_transform(pred_scaled)[0, 0]
        
        # Convert TTI to congestion level (1-10)
        congestion_level = np.clip((pred_tti - 1) * 10, 1, 10)
        
        # Estimate confidence based on prediction variance
        confidence = 0.85  # Placeholder - could implement MC dropout
        
        return {
            'predicted_tti': float(pred_tti),
            'congestion_level': float(congestion_level),
            'confidence': float(confidence),
            'origin_idx': origin_idx,
            'destination_idx': dest_idx,
            'hour': hour,
            'day_of_week': day_of_week
        }
    
    def _save_scalers(self):
        """Save scalers to disk."""
        scalers = {
            'temporal': self.scaler_temporal,
            'zone': self.scaler_zone,
            'target': self.scaler_target,
            'temporal_cols': self.temporal_cols,
            'zone_cols': self.zone_cols,
            'sequence_length': self.sequence_length,
            'n_points': self.n_points
        }
        
        with open(self.model_dir / 'scalers.pkl', 'wb') as f:
            pickle.dump(scalers, f)
        
        logger.info(f"Scalers saved to {self.model_dir / 'scalers.pkl'}")
    
    def save(self, path: Optional[str] = None):
        """Save model and scalers."""
        save_path = Path(path) if path else self.model_dir
        save_path.mkdir(parents=True, exist_ok=True)
        
        if self.model and TF_AVAILABLE:
            self.model.save(save_path / 'model.keras')
        
        self._save_scalers()
        logger.info(f"Model saved to {save_path}")
    
    def load(self, path: Optional[str] = None) -> bool:
        """Load model and scalers."""
        load_path = Path(path) if path else self.model_dir
        
        try:
            # Load model
            if TF_AVAILABLE and (load_path / 'model.keras').exists():
                self.model = load_model(load_path / 'model.keras')
                logger.info("Model loaded successfully")
            elif (load_path / 'best_model.keras').exists():
                self.model = load_model(load_path / 'best_model.keras')
                logger.info("Best model loaded successfully")
            
            # Load scalers
            with open(load_path / 'scalers.pkl', 'rb') as f:
                scalers = pickle.load(f)
            
            self.scaler_temporal = scalers['temporal']
            self.scaler_zone = scalers['zone']
            self.scaler_target = scalers['target']
            self.temporal_cols = scalers['temporal_cols']
            self.zone_cols = scalers['zone_cols']
            self.sequence_length = scalers['sequence_length']
            self.n_points = scalers['n_points']
            
            logger.info(f"Model and scalers loaded from {load_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


def train_enhanced_model(excel_path: str, epochs: int = 100) -> Dict:
    """
    Train the enhanced LSTM model on the Casablanca dataset.
    
    Args:
        excel_path: Path to the Excel dataset
        epochs: Number of training epochs
    
    Returns:
        Training metrics
    """
    from src.data.excel_loader import CasablancaDataLoader
    
    logger.info("Loading dataset...")
    loader = CasablancaDataLoader(excel_path)
    df = loader.build_training_dataset()
    
    logger.info(f"Dataset shape: {df.shape}")
    logger.info(f"Features: {list(df.columns)}")
    
    model = EnhancedTrafficLSTM()
    metrics = model.train(df, epochs=epochs)
    
    logger.info(f"Training complete: {metrics}")
    return metrics
