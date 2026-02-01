from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from datetime import datetime
import random
import logging
import os
import aiohttp
from dotenv import load_dotenv

from src.api.prediction import router as prediction_router
from src.api.traffic import router as traffic_router
from src.api.route import router as route_router
from src.api.analytics import router as analytics_router

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Traffic Solutions API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prediction_router, prefix="/api/prediction", tags=["prediction"])
app.include_router(traffic_router, prefix="/api/traffic", tags=["traffic"])
app.include_router(route_router, prefix="/api/routes", tags=["routes"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])

TRAFFIC_DATA = []
COORDINATES = []
WEATHER_CACHE = None
GOOGLE_TRAFFIC_CACHE = {}
LAST_GOOGLE_UPDATE = None
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')

ROAD_NAMES = [
    "Boulevard Mohammed V", "Avenue Hassan II", "Route de l'Aéroport",
    "Boulevard Zerktouni", "Avenue des FAR", "Boulevard Anfa",
    "Route d'El Jadida", "Boulevard Ghandi", "Avenue Mers Sultan",
    "Boulevard Moulay Youssef", "Route de Médiouna", "Boulevard Bir Anzarane",
    "Avenue Lalla Yacout", "Boulevard Abdelmoumen", "Route de Rabat",
    "Boulevard Yacoub El Mansour", "Avenue Al Qods", "Boulevard Roudani"
]


def load_excel_data():
    global TRAFFIC_DATA, COORDINATES
    
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'Dataset for traffic analysis in Casablanca, Morocco.xlsx'),
        '/Users/m/Downloads/STS_app/Dataset for traffic analysis in Casablanca, Morocco.xlsx',
    ]
    
    excel_path = next((p for p in possible_paths if os.path.exists(p)), None)
    
    if not excel_path:
        generate_default_data()
        return
    
    try:
        xl = pd.ExcelFile(excel_path)
        coords_df = pd.read_excel(xl, sheet_name='Table 0. Coordinates', header=None)
        
        current_commune = "Unknown"
        
        for i in range(12, min(122, len(coords_df))):
            row = coords_df.iloc[i].values
            vals = [v for v in row if pd.notna(v)]
            
            if len(vals) < 3:
                continue
            
            try:
                if isinstance(vals[0], str) and not vals[0].replace('.', '').replace('-', '').replace(',', '').replace(' ', '').isdigit():
                    current_commune = vals[0]
                    if len(vals) >= 5:
                        lat, lng = float(str(vals[3])), float(str(vals[4]))
                        idx = int(vals[2]) if len(vals) > 2 else len(COORDINATES)
                    else:
                        continue
                else:
                    idx = int(vals[0]) if isinstance(vals[0], (int, float)) else len(COORDINATES)
                    lat, lng = float(str(vals[1])), float(str(vals[2]))
                
                if 33.4 < lat < 33.7 and -7.7 < lng < -7.3:
                    COORDINATES.append({'commune': current_commune, 'latitude': lat, 'longitude': lng, 'index': idx})
            except (ValueError, TypeError, IndexError):
                continue
        
        for i, coord in enumerate(COORDINATES[:60]):
            congestion = random.randint(1, 10)
            TRAFFIC_DATA.append({
                'road_segment_id': f"casa_{i:03d}",
                'road_name': f"{ROAD_NAMES[i % len(ROAD_NAMES)]} - {coord['commune']}",
                'latitude': coord['latitude'],
                'longitude': coord['longitude'],
                'congestion_level': congestion,
                'average_speed': max(5, 60 - congestion * 4 + random.randint(-10, 10)),
                'vehicle_density': congestion * random.randint(10, 20),
                'time': datetime.utcnow().isoformat(),
                'weather_temp': None,
                'weather_condition': None
            })
        
        logger.info(f"Loaded {len(COORDINATES)} coordinates, {len(TRAFFIC_DATA)} segments")
        
    except Exception as e:
        logger.error(f"Excel load error: {e}")
        generate_default_data()


def generate_default_data():
    global TRAFFIC_DATA, COORDINATES
    
    casablanca_zones = [
        {"commune": "Centre Ville", "lat": 33.5928, "lng": -7.6187},
        {"commune": "Anfa", "lat": 33.5731, "lng": -7.6494},
        {"commune": "Maarif", "lat": 33.5789, "lng": -7.6324},
        {"commune": "Ain Diab", "lat": 33.5936, "lng": -7.6739},
        {"commune": "Hay Hassani", "lat": 33.5544, "lng": -7.6828},
        {"commune": "Sidi Maarouf", "lat": 33.5100, "lng": -7.6333},
        {"commune": "Bourgogne", "lat": 33.5867, "lng": -7.6272},
        {"commune": "Racine", "lat": 33.5844, "lng": -7.6481},
        {"commune": "Oasis", "lat": 33.5656, "lng": -7.6156},
        {"commune": "Palmier", "lat": 33.5678, "lng": -7.6067},
        {"commune": "Gauthier", "lat": 33.5781, "lng": -7.6217},
        {"commune": "Sidi Belyout", "lat": 33.5900, "lng": -7.6100},
        {"commune": "Hay Mohammadi", "lat": 33.5650, "lng": -7.5850},
        {"commune": "Ain Sebaa", "lat": 33.5950, "lng": -7.5600},
        {"commune": "Roches Noires", "lat": 33.5980, "lng": -7.5700},
        {"commune": "Belvédère", "lat": 33.5750, "lng": -7.6050},
        {"commune": "Habous", "lat": 33.5830, "lng": -7.6150},
        {"commune": "Derb Sultan", "lat": 33.5720, "lng": -7.6020},
        {"commune": "Sidi Othmane", "lat": 33.5550, "lng": -7.5900},
        {"commune": "Sbata", "lat": 33.5400, "lng": -7.5800},
    ]
    
    for i in range(60):
        zone = casablanca_zones[i % len(casablanca_zones)]
        offset_lat = (i // 20) * 0.005 + random.uniform(-0.003, 0.003)
        offset_lng = (i % 3) * 0.008 + random.uniform(-0.003, 0.003)
        
        COORDINATES.append({
            'commune': zone['commune'], 
            'latitude': zone['lat'] + offset_lat, 
            'longitude': zone['lng'] + offset_lng, 
            'index': i
        })
        
        congestion = random.randint(2, 9)
        TRAFFIC_DATA.append({
            'road_segment_id': f"casa_{i:03d}",
            'road_name': f"{ROAD_NAMES[i % len(ROAD_NAMES)]} - {zone['commune']}",
            'latitude': zone['lat'] + offset_lat,
            'longitude': zone['lng'] + offset_lng,
            'congestion_level': congestion,
            'average_speed': max(10, 55 - congestion * 4),
            'vehicle_density': congestion * 15,
            'time': datetime.utcnow().isoformat(),
            'weather_temp': None,
            'weather_condition': None
        })
    
    logger.info(f"Generated {len(TRAFFIC_DATA)} default traffic segments")


async def fetch_google_traffic():
    global GOOGLE_TRAFFIC_CACHE, LAST_GOOGLE_UPDATE
    
    if not GOOGLE_MAPS_API_KEY:
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            for i, coord in enumerate(COORDINATES[:60]):
                dest_lat, dest_lng = coord['latitude'] + 0.004, coord['longitude'] + 0.004
                url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={coord['latitude']},{coord['longitude']}&destinations={dest_lat},{dest_lng}&departure_time=now&traffic_model=best_guess&key={GOOGLE_MAPS_API_KEY}"
                
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('status') == 'OK':
                                element = data.get('rows', [{}])[0].get('elements', [{}])[0]
                                if element.get('status') == 'OK':
                                    duration = element.get('duration', {}).get('value', 60)
                                    duration_traffic = element.get('duration_in_traffic', {}).get('value', duration)
                                    traffic_ratio = duration_traffic / max(duration, 1)
                                    congestion = min(10, max(0, int((traffic_ratio - 1.0) * 20)))
                                    GOOGLE_TRAFFIC_CACHE[coord['index']] = {
                                        'congestion_level': congestion,
                                        'average_speed': max(5, int(50 / traffic_ratio)),
                                        'source': 'google_maps'
                                    }
                except Exception:
                    continue
            
            LAST_GOOGLE_UPDATE = datetime.utcnow()
    except Exception as e:
        logger.error(f"Google traffic error: {e}")


async def update_weather():
    global WEATHER_CACHE
    
    api_key = os.getenv('OPENWEATHER_API_KEY', '508deb6ce98947a6179acace2f635025')
    url = f"https://api.openweathermap.org/data/2.5/weather?lat=33.5928&lon=-7.6187&appid={api_key}&units=metric"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    WEATHER_CACHE = {
                        'temperature': data.get('main', {}).get('temp'),
                        'humidity': data.get('main', {}).get('humidity'),
                        'weather_condition': data.get('weather', [{}])[0].get('main'),
                        'wind_speed': data.get('wind', {}).get('speed'),
                    }
                    for point in TRAFFIC_DATA:
                        point['weather_temp'] = WEATHER_CACHE['temperature']
                        point['weather_condition'] = WEATHER_CACHE['weather_condition']
    except Exception:
        pass


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Smart Traffic Solutions API...")
    
    try:
        from src.cache import redis_client
        await redis_client.connect()
    except Exception:
        pass
    
    load_excel_data()
    
    try:
        from src.services.enhanced_predictor import enhanced_predictor
        
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'Dataset for traffic analysis in Casablanca, Morocco.xlsx'),
            '/Users/m/Downloads/STS_app/Dataset for traffic analysis in Casablanca, Morocco.xlsx',
        ]
        
        excel_path = next((p for p in possible_paths if os.path.exists(p)), None)
        if excel_path:
            enhanced_predictor.load_data(excel_path)
        
        if enhanced_predictor.load_model():
            logger.info("Enhanced LSTM model loaded")
    except Exception as e:
        logger.warning(f"Predictor init error: {e}")
    
    try:
        await fetch_google_traffic()
    except Exception:
        pass
    
    try:
        await update_weather()
    except Exception:
        pass


@app.get("/")
async def root():
    return {"message": "Smart Traffic Solutions API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "segments": len(TRAFFIC_DATA), "google_traffic": bool(GOOGLE_TRAFFIC_CACHE), "weather": bool(WEATHER_CACHE)}


@app.get("/api/traffic/current")
async def get_current_traffic(refresh: bool = False):
    global LAST_GOOGLE_UPDATE
    
    try:
        from src.cache import redis_client
        cached = await redis_client.get("traffic:current")
        if cached and not refresh:
            return {"data": cached, "count": len(cached), "source": "cache"}
    except Exception:
        pass
    
    if not TRAFFIC_DATA:
        raise HTTPException(status_code=503, detail="Traffic data not available")
    
    should_refresh = refresh or (LAST_GOOGLE_UPDATE and (datetime.utcnow() - LAST_GOOGLE_UPDATE).seconds > 300)
    if should_refresh and GOOGLE_MAPS_API_KEY:
        await fetch_google_traffic()
    
    updated_data = []
    for i, point in enumerate(TRAFFIC_DATA):
        updated_point = point.copy()
        
        if i in GOOGLE_TRAFFIC_CACHE:
            google_data = GOOGLE_TRAFFIC_CACHE[i]
            updated_point['congestion_level'] = google_data['congestion_level']
            updated_point['average_speed'] = google_data['average_speed']
            updated_point['traffic_source'] = 'google_maps'
        else:
            updated_point['congestion_level'] = max(0, min(10, point['congestion_level'] + random.randint(-1, 1)))
            updated_point['average_speed'] = max(5, point['average_speed'] + random.randint(-5, 5))
            updated_point['traffic_source'] = 'simulated'
        
        updated_point['time'] = datetime.utcnow().isoformat()
        updated_data.append(updated_point)
    
    try:
        from src.cache import redis_client
        await redis_client.set("traffic:current", updated_data, ttl=120)
    except Exception:
        pass
    
    return {"data": updated_data, "count": len(updated_data), "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/traffic/segments")
async def get_road_segments():
    return {"segments": [{'road_segment_id': p['road_segment_id'], 'road_name': p['road_name'], 'latitude': p['latitude'], 'longitude': p['longitude']} for p in TRAFFIC_DATA], "count": len(TRAFFIC_DATA)}


@app.get("/api/traffic/history/{road_segment_id}")
async def get_traffic_history(road_segment_id: str, hours: int = 24):
    segment = next((p for p in TRAFFIC_DATA if p['road_segment_id'] == road_segment_id), None)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    history = []
    for i in range(hours):
        hour = (datetime.utcnow().hour - hours + i) % 24
        rush = 1.5 if 7 <= hour <= 9 or 17 <= hour <= 19 else 0.5 if 0 <= hour <= 6 else 1.0
        congestion = max(0, min(10, int(segment['congestion_level'] * rush + random.randint(-2, 2))))
        history.append({'time': f"{hour:02d}:00", 'congestion_level': congestion, 'average_speed': max(5, 60 - congestion * 5)})
    
    return {"road_segment_id": road_segment_id, "data": history, "count": len(history)}


@app.get("/api/weather/current")
async def get_current_weather():
    if WEATHER_CACHE:
        return WEATHER_CACHE
    return {"temperature": 22, "weather_condition": "Clear", "humidity": 65}


@app.get("/api/analytics/dashboard")
async def get_dashboard():
    if not TRAFFIC_DATA:
        raise HTTPException(status_code=503, detail="Data not available")
    
    congestion_levels = [p['congestion_level'] for p in TRAFFIC_DATA]
    sorted_data = sorted(TRAFFIC_DATA, key=lambda x: x['congestion_level'], reverse=True)
    
    return {
        "metrics": {
            "average_congestion": round(sum(congestion_levels) / len(congestion_levels), 2),
            "active_segments": len(TRAFFIC_DATA),
            "top_congested_areas": [{'road_name': p['road_name'], 'road_segment_id': p['road_segment_id'], 'avg_congestion': p['congestion_level']} for p in sorted_data[:10]],
            "last_updated": datetime.utcnow().isoformat()
        }
    }


@app.get("/api/analytics/trends")
async def get_trends(hours: int = 24):
    trends = []
    for i in range(hours):
        hour = (datetime.utcnow().hour - hours + i) % 24
        if 7 <= hour <= 9:
            base = 7 + random.random() * 2
        elif 17 <= hour <= 19:
            base = 8 + random.random() * 2
        elif 0 <= hour <= 6:
            base = 2 + random.random() * 2
        else:
            base = 4 + random.random() * 2
        trends.append({'time': f"{hour:02d}:00", 'avg_congestion': round(base, 2), 'avg_speed': round(60 - base * 5, 2)})
    
    return {"trends": trends, "period_hours": hours, "count": len(trends)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
