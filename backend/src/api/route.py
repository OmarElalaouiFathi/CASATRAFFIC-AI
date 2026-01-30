from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from src.services.google_maps import google_maps_client

logger = logging.getLogger(__name__)
router = APIRouter()

class RouteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    avoid_congestion: bool = True

class RouteOption(BaseModel):
    route_id: str
    duration: int
    distance: float
    congestion_score: float
    route_geojson: dict
    description: str

class RouteResponse(BaseModel):
    routes: List[RouteOption]
    recommended_route_id: str

@router.post("/suggest", response_model=Optional[RouteResponse])
async def suggest_routes(request: RouteRequest):
    logger.info(f"Route request: {request.origin_lat},{request.origin_lng} -> {request.destination_lat},{request.destination_lng}")
    
    try:
        result = await google_maps_client.get_route_suggestions(
            origin_lat=request.origin_lat,
            origin_lng=request.origin_lng,
            destination_lat=request.destination_lat,
            destination_lng=request.destination_lng,
            alternatives=True
        )
        
        if result is None:
            raise HTTPException(
                status_code=503,
                detail="Route service unavailable. Check Google Maps API configuration."
            )
        
        if not result.get("routes"):
            raise HTTPException(
                status_code=404,
                detail="No routes found between the specified locations."
            )
        
        # If avoiding congestion, routes are already sorted by congestion_score
        # Otherwise, sort by duration
        routes = result["routes"]
        if not request.avoid_congestion:
            routes.sort(key=lambda r: r["duration"])
            result["recommended_route_id"] = routes[0]["route_id"]
        
        return RouteResponse(
            routes=[RouteOption(**r) for r in routes],
            recommended_route_id=result["recommended_route_id"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in route suggestion: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error processing route request"
        )
