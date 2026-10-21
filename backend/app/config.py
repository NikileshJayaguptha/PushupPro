from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    database_url: str = "postgresql+psycopg2://pushup:pushup@localhost:5432/pushuppro"
    storage_dir: Path = Path("./storage")
    pose_weights: str = "yolo11n-pose.pt"
    pose_device: str | None = None          
    max_analysis_fps: float = 30.0
    max_upload_mb: int = 500
    transcode_for_web: bool = True           
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.storage_dir.mkdir(parents=True, exist_ok=True)
    return s
