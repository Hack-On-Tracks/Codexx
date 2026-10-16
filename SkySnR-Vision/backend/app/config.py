from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "skysnr_vision"
    jwt_secret: str = ""
    access_token_minutes: int = 60
    cookie_secure: bool = False
    frontend_origin: str = "http://localhost:5173"
    roboflow_api_key: str = ""
    roboflow_model_id: str = ""
    roboflow_confidence: int = 40
    person_classes: str = "person"
    obstacle_classes: str = ""
    proximity_factor: float = 3.0
    storage_dir: str = "./storage"
    max_upload_mb: int = 10

    @property
    def person_class_set(self) -> set[str]:
        return {c.strip().lower() for c in self.person_classes.split(",") if c.strip()}

    @property
    def obstacle_class_set(self) -> set[str]:
        return {c.strip().lower() for c in self.obstacle_classes.split(",") if c.strip()}

    @property
    def media_dir(self) -> Path:
        p = Path(self.storage_dir) / "media"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def reports_dir(self) -> Path:
        p = Path(self.storage_dir) / "reports"
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
