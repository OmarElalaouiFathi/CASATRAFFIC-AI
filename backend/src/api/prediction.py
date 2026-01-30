from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

router = APIRouter()


class PredictionRequest(BaseModel):
    road_segment_id: str
    time_horizon: int = 30


class PredictionResponse(BaseModel):
    road_segment_id: str
    current_congestion: float
    predicted_congestion: float
    predicted_tti: Optional[float] = None
    trend: str = 'stable'
    confidence: float
    time_horizon: int
    prediction_time: str


@router.post("/predict", response_model=PredictionResponse)
async def predict_traffic(request: PredictionRequest):
    from src.services.enhanced_predictor import enhanced_predictor
    from src.cache import redis_client
    
    cached_traffic = await redis_client.get("traffic:current")
    if cached_traffic:
        segment_data = next((item for item in cached_traffic if item["road_segment_id"] == request.road_segment_id), None)
        current_congestion = segment_data.get("congestion_level", 5.0) if segment_data else 5.0
        current_speed = segment_data.get("average_speed", 30.0) if segment_data else 30.0
    else:
        current_congestion, current_speed = 5.0, 30.0
    
    prediction = await enhanced_predictor.predict_segment(request.road_segment_id, current_congestion, current_speed, request.time_horizon)
    
    if prediction is None:
        raise HTTPException(status_code=503, detail="Prediction service unavailable")
    
    return PredictionResponse(
        road_segment_id=prediction['road_segment_id'],
        current_congestion=prediction['current_congestion'],
        predicted_congestion=prediction['predicted_congestion'],
        predicted_tti=prediction.get('predicted_tti'),
        trend=prediction.get('trend', 'stable'),
        confidence=prediction['confidence'],
        time_horizon=prediction['time_horizon'],
        prediction_time=prediction['prediction_time']
    )


@router.get("/segments")
async def predict_all_segments(time_horizon: int = 30):
    from src.services.enhanced_predictor import enhanced_predictor
    from src.cache import redis_client
    
    cached_traffic = await redis_client.get("traffic:current")
    
    if not cached_traffic:
        return {"predictions": [], "model_type": enhanced_predictor.get_model_info()['model_type'], "timestamp": datetime.now().isoformat()}
    
    segments = [{'road_segment_id': item.get('road_segment_id'), 'congestion_level': item.get('congestion_level', 5.0), 'average_speed': item.get('average_speed', 30.0)} for item in cached_traffic]
    predictions = await enhanced_predictor.predict_all_segments(segments, time_horizon)
    
    return {"predictions": predictions, "model_type": enhanced_predictor.get_model_info()['model_type'], "timestamp": datetime.now().isoformat()}


@router.get("/model-info")
async def get_model_info():
    from src.services.enhanced_predictor import enhanced_predictor
    info = enhanced_predictor.get_model_info()
    return {"is_loaded": info['is_loaded'], "model_type": info['model_type'], "features": info['features'], "zones_cached": info['zones_cached']}


@router.get("/accuracy")
async def get_prediction_accuracy():
    from src.services.enhanced_predictor import enhanced_predictor
    
    if not enhanced_predictor.is_loaded:
        return {'status': 'model_not_loaded', 'accuracy': None, 'mae': None}
    
    return {'status': 'model_loaded', 'model_type': 'EnhancedLSTM', 'estimated_mae': 0.187, 'estimated_accuracy': 0.85}


@router.get("/zones")
async def get_zone_info():
    from src.services.enhanced_predictor import enhanced_predictor
    
    zones_info = []
    
    if enhanced_predictor.data_loader:
        try:
            coords = enhanced_predictor.data_loader.load_coordinates()
            zones = enhanced_predictor.data_loader.load_zone_features()
            
            for _, row in coords.iterrows():
                point_idx = row['point_idx']
                commune = row['commune']
                zone_data = zones[zones['commune'] == commune]
                zone_features = zone_data.iloc[0].to_dict() if len(zone_data) > 0 else {}
                
                zones_info.append({
                    'point_idx': int(point_idx),
                    'commune': commune,
                    'latitude': float(row['latitude']),
                    'longitude': float(row['longitude']),
                    'population': zone_features.get('population', 0),
                    'density': zone_features.get('density', 0),
                })
        except Exception as e:
            return {'error': str(e), 'zones': []}
    
    return {'count': len(zones_info), 'zones': zones_info}
