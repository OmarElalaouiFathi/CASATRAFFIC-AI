
import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    REDIS_HOST: str = os.getenv("REDISHOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDISPORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDISPASSWORD", None)
    GOOGLE_MAPS_API_KEY: str = ""
    MAPBOX_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,https://casatraffic-ai.railway.internal,https://backend-production-e652.up.railway.app"
    DATA_COLLECTION_INTERVAL: int = 900
    WEATHER_COLLECTION_INTERVAL: int = 3600
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
