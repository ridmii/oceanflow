from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os
from pathlib import Path

class Settings(BaseSettings):
    copernicus_username: str = ""
    copernicus_password: str = ""
    copernicus_dataset_id: str = ""
    
    redis_url: str = "redis://redis:6379/0"
    data_dir: str = "/data"
    max_concurrent_simulations: int = 1
    rate_limit_per_minute: int = 5
    cors_origins: str = "http://localhost:5173"

    # M4 WebSocket tunables
    ws_heartbeat_seconds: int = 15
    ws_marker_poll_seconds: int = 5

    # M5 Density defaults
    density_blur_sigma: float = 0.8
    density_default_cols: int = 720
    density_default_rows: int = 360

    model_config = SettingsConfigDict(
        env_file=os.path.join(Path(__file__).parent.parent, ".env"), 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

settings = Settings()
