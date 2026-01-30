import aiohttp
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
from src.config import settings
from src.data.casablanca_roads import generate_monitoring_points

logger = logging.getLogger(__name__)

class GoogleMapsClient:
    BASE_URL = "https://maps.googleapis.com/maps/api/directions/json"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_route_traffic(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> Optional[Dict]:
        if not self.api_key:
            return None
        
        params = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{dest_lat},{dest_lng}",
            "departure_time": "now",
            "traffic_model": "best_guess",
            "key": self.api_key
        }
        
        try:
            async with self.session.get(self.BASE_URL, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status") == "OK" and data.get("routes"):
                        route = data["routes"][0]
                        leg = route["legs"][0]
                        
                        duration = leg.get("duration", {}).get("value", 0)
                        duration_in_traffic = leg.get("duration_in_traffic", {}).get("value", duration)
                        distance = leg.get("distance", {}).get("value", 0)
                        
                        if duration > 0:
                            congestion_ratio = duration_in_traffic / duration
                            congestion_level = min(10, max(0, (congestion_ratio - 1) * 10))
                        else:
                            congestion_level = 0
                        
                        if duration_in_traffic > 0:
                            avg_speed = (distance / 1000) / (duration_in_traffic / 3600)
                        else:
                            avg_speed = 0
                        
                        return {
                            "duration": duration,
                            "duration_in_traffic": duration_in_traffic,
                            "distance": distance / 1000,
                            "congestion_level": round(congestion_level, 2),
                            "average_speed": round(avg_speed, 2),
                            "timestamp": datetime.utcnow()
                        }
                return None
        except Exception as e:
            logger.error(f"Exception during Google Maps API request: {e}")
            return None
    
    async def collect_traffic_data(self) -> List[Dict]:
        monitoring_points = generate_monitoring_points()
        traffic_data = []
        
        routes = []
        for i in range(0, len(monitoring_points) - 1, 2):
            origin = monitoring_points[i]
            dest = monitoring_points[i + 1] if i + 1 < len(monitoring_points) else monitoring_points[0]
            routes.append((origin, dest))
        
        for i, (origin, dest) in enumerate(routes):
            if i > 0 and i % 10 == 0:
                await asyncio.sleep(1)
            
            traffic = await self.get_route_traffic(
                origin["latitude"],
                origin["longitude"],
                dest["latitude"],
                dest["longitude"]
            )
            
            if traffic:
                traffic_data.append({
                    "road_segment_id": origin["road_segment_id"],
                    "road_name": origin["road_name"],
                    "latitude": origin["latitude"],
                    "longitude": origin["longitude"],
                    **traffic
                })
        
        return traffic_data
    
    async def get_route_suggestions(
        self,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
        alternatives: bool = True,
        avoid_tolls: bool = False
    ) -> Optional[Dict]:
        if not self.api_key:
            return None
        
        params = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{destination_lat},{destination_lng}",
            "departure_time": "now",
            "traffic_model": "best_guess",
            "alternatives": str(alternatives).lower(),
            "mode": "driving",
            "units": "metric",
            "key": self.api_key
        }
        
        if avoid_tolls:
            params["avoid"] = "tolls"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=15) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    
                    if data.get("status") != "OK":
                        return None
                    
                    return self._parse_route_response(data)
        except:
            return None
    
    def _parse_route_response(self, data: Dict) -> Dict:
        routes = []
        
        for idx, route in enumerate(data.get("routes", [])):
            if not route.get("legs"):
                continue
                
            leg = route["legs"][0]
            
            duration = leg.get("duration", {}).get("value", 0)
            duration_in_traffic = leg.get("duration_in_traffic", {}).get("value", duration)
            distance_m = leg.get("distance", {}).get("value", 0)
            distance_km = distance_m / 1000
            
            congestion_score = 0.0
            if duration > 0:
                delay_ratio = duration_in_traffic / duration
                congestion_score = min(10, max(0, (delay_ratio - 1) * 10))
            
            polyline = route.get("overview_polyline", {}).get("points", "")
            coordinates = self._decode_polyline(polyline)
            
            route_geojson = {
                "type": "LineString",
                "coordinates": coordinates
            }
            
            summary = route.get("summary", f"Route {idx + 1}")
            
            routes.append({
                "route_id": f"route_{idx}",
                "duration": duration_in_traffic,
                "distance": round(distance_km, 2),
                "congestion_score": round(congestion_score, 1),
                "route_geojson": route_geojson,
                "description": summary
            })
        
        routes.sort(key=lambda r: (r["congestion_score"], r["duration"]))
        recommended_id = routes[0]["route_id"] if routes else None
        
        return {
            "routes": routes,
            "recommended_route_id": recommended_id
        }
    
    def _decode_polyline(self, polyline: str) -> List[List[float]]:
        coordinates = []
        index = 0
        lat = 0
        lng = 0
        
        while index < len(polyline):
            shift = 0
            result = 0
            while True:
                b = ord(polyline[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            dlat = ~(result >> 1) if result & 1 else result >> 1
            lat += dlat
            
            shift = 0
            result = 0
            while True:
                b = ord(polyline[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            dlng = ~(result >> 1) if result & 1 else result >> 1
            lng += dlng
            
            coordinates.append([lng / 1e5, lat / 1e5])
        
        return coordinates


google_maps_client = GoogleMapsClient()
