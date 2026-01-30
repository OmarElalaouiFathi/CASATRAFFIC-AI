from fastapi import APIRouter, HTTPException
from datetime import datetime
from src.cache import redis_client

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_metrics():
    try:
        cached = await redis_client.get("analytics:dashboard")
        if cached:
            return {"metrics": cached, "source": "cache"}
        
        traffic_data = await redis_client.get("traffic:current") or []
        
        if not traffic_data:
            return {"metrics": {"average_congestion": 0, "active_segments": 0, "top_congested_areas": [], "last_updated": datetime.utcnow().isoformat(), "period": "1h"}, "source": "empty"}
        
        avg_congestion = sum(t.get("congestion_level", 0) for t in traffic_data) / len(traffic_data) if traffic_data else 0
        sorted_by_congestion = sorted(traffic_data, key=lambda x: x.get("congestion_level", 0), reverse=True)[:5]
        top_congested = [{"road_name": t.get("road_name", ""), "road_segment_id": t.get("road_segment_id", ""), "avg_congestion": t.get("congestion_level", 0)} for t in sorted_by_congestion]
        
        metrics = {"average_congestion": round(avg_congestion, 2), "active_segments": len(traffic_data), "top_congested_areas": top_congested, "last_updated": datetime.utcnow().isoformat(), "period": "1h"}
        
        await redis_client.set("analytics:dashboard", metrics, ttl=60)
        return {"metrics": metrics, "source": "computed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def get_traffic_trends(hours: int = 24):
    return {"trends": [], "period_hours": hours, "count": 0, "message": "Historical trends require database storage"}
