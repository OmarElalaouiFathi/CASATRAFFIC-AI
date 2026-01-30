import json
import redis.asyncio as redis
from typing import Any, Optional, List, Dict
from src.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.pool: Optional[redis.ConnectionPool] = None
    async def connect(self):
        try:
            self.pool = redis.ConnectionPool(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD, max_connections=50, decode_responses=True)
            self.redis = redis.Redis(connection_pool=self.pool)
            await self.redis.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    async def disconnect(self):
        if self.redis:
            await self.redis.close()
    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self.redis.get(key)
            return json.loads(value) if value else None
        except:
            return None
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        try:
            await self.redis.setex(key, ttl, json.dumps(value))
            return True
        except:
            return False
    async def delete(self, key: str) -> bool:
        try:
            await self.redis.delete(key)
            return True
        except:
            return False
    async def xadd(self, stream: str, data: Dict[str, Any]) -> Optional[str]:
        try:
            stream_data = {k: json.dumps(v) if not isinstance(v, str) else v for k, v in data.items()}
            return await self.redis.xadd(stream, stream_data)
        except:
            return None
    async def xread(self, streams: Dict[str, str], count: int = 10, block: int = 1000) -> List:
        try:
            return await self.redis.xread(streams, count=count, block=block)
        except:
            return []
    async def xlen(self, stream: str) -> int:
        try:
            return await self.redis.xlen(stream)
        except:
            return 0

redis_client = RedisClient()
