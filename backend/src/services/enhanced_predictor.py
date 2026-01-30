import numpy as np
import logging
import os
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

from src.config import settings
from src.cache import redis_client

logger = logging.getLogger(__name__)


class EnhancedTrafficPredictor:
    def __init__(self):
        self.keras_model = None
        self.scaler = None
        self.model_config = {}
        self.data_loader = None
        self.is_loaded = False
        self.zone_features_cache: Dict[str, Dict] = {}
        self.historical_tti_cache: Dict[str, List[float]] = {}
        
        self.default_tti_by_hour = {
            0: 1.1, 1: 1.05, 2: 1.05, 3: 1.05, 4: 1.1, 5: 1.2,
            6: 1.4, 7: 1.7, 8: 1.9, 9: 1.8, 10: 1.5, 11: 1.4,
            12: 1.5, 13: 1.4, 14: 1.4, 15: 1.5, 16: 1.6, 17: 1.8,
            18: 1.9, 19: 1.7, 20: 1.4, 21: 1.3, 22: 1.2, 23: 1.1
        }
    
    def load_model(self) -> bool:
        try:
            import json
            import joblib
            from tensorflow import keras
            
            model_paths = [
                Path('src/models/trained'),
                Path('models/trained'),
                Path('models/enhanced_lstm'),
            ]
            
            model_path = next((p for p in model_paths if (p / 'model.keras').exists() or (p / 'model.h5').exists()), None)
            
            if model_path is None:
                logger.warning("No trained model found")
                return False
            
            model_file = model_path / 'model.keras' if (model_path / 'model.keras').exists() else model_path / 'model.h5'
            
            try:
                self.keras_model = keras.models.load_model(str(model_file))
            except TypeError:
                self.keras_model = keras.models.load_model(str(model_file), compile=False)
                self.keras_model.compile(optimizer='adam', loss='huber', metrics=['mae'])
            
            scaler_file = model_path / 'scaler.joblib'
            if scaler_file.exists():
                self.scaler = joblib.load(str(scaler_file))
            
            config_file = model_path / 'config.json'
            if config_file.exists():
                with open(config_file) as f:
                    self.model_config = json.load(f)
            
            self.is_loaded = True
            logger.info("Enhanced LSTM model loaded")
            return True
                
        except Exception as e:
            logger.error(f"Model load error: {e}")
            return False
    
    def load_data(self, excel_path: str) -> bool:
        try:
            from src.data.excel_loader import CasablancaDataLoader
            self.data_loader = CasablancaDataLoader(excel_path)
            self._cache_zone_features()
            return True
        except Exception as e:
            logger.error(f"Data load error: {e}")
            return False
    
    def _cache_zone_features(self):
        if self.data_loader is None:
            return
        
        try:
            coords = self.data_loader.load_coordinates()
            zones = self.data_loader.load_zone_features()
            
            for _, row in coords.iterrows():
                point_idx = row['point_idx']
                commune = row['commune']
                zone_row = zones[zones['commune'] == commune]
                if len(zone_row) > 0:
                    self.zone_features_cache[str(point_idx)] = zone_row.iloc[0].to_dict()
        except Exception:
            pass
    
    def get_zone_features(self, origin_idx: int, dest_idx: int, distance_km: float = 10.0) -> Dict[str, float]:
        origin_zone = self.zone_features_cache.get(str(origin_idx), {})
        dest_zone = self.zone_features_cache.get(str(dest_idx), {})
        
        return {
            'origin_population': origin_zone.get('population', 100000),
            'origin_density': origin_zone.get('density', 10000),
            'origin_tram_stations': origin_zone.get('tram_stations', 5),
            'origin_bus_stations': origin_zone.get('bus_stations', 20),
            'origin_primary_roads': origin_zone.get('primary_roads', 20),
            'origin_highways': origin_zone.get('highways', 10),
            'origin_industrial_pct': origin_zone.get('industrial_pct', 5),
            'origin_residential_pct': origin_zone.get('residential_pct', 50),
            'origin_university_pct': origin_zone.get('university_pct', 2),
            'origin_commercial_buildings': origin_zone.get('commercial_buildings', 10),
            'dest_population': dest_zone.get('population', 100000),
            'dest_density': dest_zone.get('density', 10000),
            'dest_tram_stations': dest_zone.get('tram_stations', 5),
            'dest_bus_stations': dest_zone.get('bus_stations', 20),
            'dest_primary_roads': dest_zone.get('primary_roads', 20),
            'dest_highways': dest_zone.get('highways', 10),
            'dest_industrial_pct': dest_zone.get('industrial_pct', 5),
            'dest_residential_pct': dest_zone.get('residential_pct', 50),
            'dest_university_pct': dest_zone.get('university_pct', 2),
            'dest_commercial_buildings': dest_zone.get('commercial_buildings', 10),
            'distance_km': distance_km,
        }
    
    def get_historical_tti(self, origin_idx: int, dest_idx: int) -> List[float]:
        cache_key = f"{origin_idx}_{dest_idx}"
        
        if cache_key in self.historical_tti_cache:
            return self.historical_tti_cache[cache_key]
        
        now = datetime.now()
        historical = []
        for i in range(12, 0, -1):
            hour = (now.hour - i) % 24
            tti = self.default_tti_by_hour.get(hour, 1.3) + np.random.normal(0, 0.1)
            historical.append(max(1.0, tti))
        
        self.historical_tti_cache[cache_key] = historical
        return historical
    
    async def predict_segment(self, road_segment_id: str, current_congestion: float, current_speed: float, time_horizon: int = 30) -> Optional[Dict]:
        try:
            seg_num = int(road_segment_id.split('_')[1])
            origin_idx = seg_num % 110
            dest_idx = (seg_num + 1) % 110
        except:
            origin_idx, dest_idx = 0, 1
        
        now = datetime.now()
        target_hour = (now.hour + (time_horizon // 60)) % 24
        day_of_week = now.weekday()
        
        if self.is_loaded and self.keras_model is not None:
            try:
                return self._predict_with_keras(road_segment_id, origin_idx, dest_idx, target_hour, day_of_week, current_congestion, time_horizon)
            except Exception as e:
                logger.error(f"Keras prediction error: {e}")
        
        return self._heuristic_prediction(road_segment_id, current_congestion, current_speed, time_horizon)
    
    def _predict_with_keras(self, road_segment_id: str, origin_idx: int, dest_idx: int, hour: int, day_of_week: int, current_congestion: float, time_horizon: int) -> Dict:
        zone_features = self.get_zone_features(origin_idx, dest_idx)
        historical_tti = self.get_historical_tti(origin_idx, dest_idx)
        
        zone_keys = ['origin_population', 'origin_density', 'origin_tram_stations', 'origin_bus_stations', 'origin_primary_roads', 'origin_highways', 'origin_industrial_pct', 'origin_residential_pct', 'origin_university_pct', 'origin_commercial_buildings', 'dest_population', 'dest_density', 'dest_tram_stations', 'dest_bus_stations', 'dest_primary_roads', 'dest_highways', 'dest_industrial_pct', 'dest_residential_pct', 'dest_university_pct', 'dest_commercial_buildings', 'distance_km']
        zone_array = np.array([[zone_features.get(k, 0) for k in zone_keys]])
        
        if self.scaler is not None:
            expected_size = getattr(self.scaler, 'n_features_in_', 21)
            if zone_array.shape[1] < expected_size:
                zone_array = np.hstack([zone_array, np.zeros((1, expected_size - zone_array.shape[1]))])
            zone_array = self.scaler.transform(zone_array)
        
        is_weekend = 1.0 if day_of_week >= 5 else 0.0
        is_rush = 1.0 if hour in [7, 8, 9, 17, 18, 19] else 0.0
        temporal_array = np.array([[day_of_week / 6.0, hour / 23.0, is_weekend, is_rush]])
        
        seq_length = self.model_config.get('sequence_length', 24)
        padded_tti = [1.0] * (seq_length - len(historical_tti)) + historical_tti
        normalized_tti = [(t - 1.0) / 2.0 for t in padded_tti[-seq_length:]]
        sequence_array = np.array([[normalized_tti]]).reshape(1, seq_length, 1)
        
        inputs = {
            'origin_idx': np.array([[origin_idx]]),
            'dest_idx': np.array([[dest_idx]]),
            'zone_features': zone_array,
            'temporal_features': temporal_array,
            'historical_tti': sequence_array
        }
        
        predicted_tti = float(self.keras_model.predict(inputs, verbose=0)[0][0])
        predicted_tti = max(1.0, min(3.0, predicted_tti))
        congestion_level = min(10, max(1, (predicted_tti - 1.0) * 10))
        
        current_tti = 1 + (current_congestion / 10)
        trend = 'up' if predicted_tti > current_tti + 0.1 else 'down' if predicted_tti < current_tti - 0.1 else 'stable'
        
        return {
            'road_segment_id': road_segment_id,
            'predicted_congestion': round(congestion_level, 1),
            'predicted_tti': round(predicted_tti, 2),
            'current_congestion': current_congestion,
            'trend': trend,
            'confidence': 0.85 if len(historical_tti) >= 6 else 0.70,
            'time_horizon': time_horizon,
            'prediction_time': datetime.now().isoformat(),
        }
    
    def _heuristic_prediction(self, road_segment_id: str, current_congestion: float, current_speed: float, time_horizon: int) -> Dict:
        now = datetime.now()
        target_hour = (now.hour + (time_horizon // 60)) % 24
        
        base_tti = self.default_tti_by_hour.get(target_hour, 1.3)
        if now.weekday() >= 5:
            base_tti *= 0.85
        
        predicted_congestion = np.clip((base_tti - 1) * 10, 1, 10)
        predicted_congestion = 0.7 * predicted_congestion + 0.3 * current_congestion
        
        trend = 'up' if predicted_congestion > current_congestion + 0.5 else 'down' if predicted_congestion < current_congestion - 0.5 else 'stable'
        
        return {
            'road_segment_id': road_segment_id,
            'predicted_congestion': round(predicted_congestion, 1),
            'predicted_tti': round(1 + (predicted_congestion / 10), 2),
            'current_congestion': current_congestion,
            'trend': trend,
            'confidence': 0.65,
            'time_horizon': time_horizon,
            'prediction_time': datetime.now().isoformat(),
        }
    
    async def predict_all_segments(self, segments: List[Dict], time_horizon: int = 30) -> List[Dict]:
        predictions = []
        for segment in segments:
            pred = await self.predict_segment(
                road_segment_id=segment.get('road_segment_id', 'seg_001'),
                current_congestion=segment.get('congestion_level', 5),
                current_speed=segment.get('average_speed', 30),
                time_horizon=time_horizon
            )
            if pred:
                predictions.append(pred)
        return predictions
    
    def get_model_info(self) -> Dict:
        return {
            'is_loaded': self.is_loaded,
            'model_type': 'EnhancedLSTM' if self.is_loaded else 'Heuristic',
            'features': {'temporal': 4, 'zone': 21, 'sequence': self.model_config.get('sequence_length', 24)},
            'zones_cached': len(self.zone_features_cache)
        }


enhanced_predictor = EnhancedTrafficPredictor()


async def initialize_predictor(excel_path: str = None) -> bool:
    if excel_path:
        enhanced_predictor.load_data(excel_path)
    return enhanced_predictor.load_model()
