from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
import asyncio, json
from src.cache import redis_client
from src.data.casablanca_roads import generate_monitoring_points

router = APIRouter()


@router.get("/current")
async def get_current_traffic():
    try:
        cached = await redis_client.get("traffic:current")
        if cached:
            return {"data": cached, "count": len(cached), "timestamp": datetime.utcnow().isoformat(), "source": "cache"}
        # Fallback to main.py's TRAFFIC_DATA
        from src.main import TRAFFIC_DATA
        if TRAFFIC_DATA:
            return {"data": TRAFFIC_DATA, "count": len(TRAFFIC_DATA), "timestamp": datetime.utcnow().isoformat(), "source": "memory"}
        return {"data": [], "count": 0, "timestamp": datetime.utcnow().isoformat(), "source": "empty"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live")
async def stream_traffic_live():
    async def event_generator():
        last_id = "0"
        while True:
            try:
                entries = await redis_client.xread({"traffic_stream": last_id}, count=10, block=2000)
                if entries:
                    for stream_name, messages in entries:
                        for message_id, data in messages:
                            last_id = message_id
                            yield f"data: {json.dumps({'id': message_id, 'data': data})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                await asyncio.sleep(0.1)
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})


@router.get("/segments")
async def get_road_segments():
    try:
        cached = await redis_client.get("traffic:segments")
        if cached:
            return {"segments": cached, "count": len(cached), "source": "cache"}
        # Fallback to main.py's TRAFFIC_DATA
        from src.main import TRAFFIC_DATA
        if TRAFFIC_DATA:
            return {"segments": TRAFFIC_DATA, "count": len(TRAFFIC_DATA), "source": "memory"}
        monitoring_points = generate_monitoring_points()
        return {"segments": monitoring_points, "count": len(monitoring_points), "source": "generated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
