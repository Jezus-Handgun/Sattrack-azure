from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    tle_ttl_seconds: int = 7200
    tle_cache_dir: str = "/tmp/tle"
    default_lat: float = 50.30
    default_lon: float = 18.95
    min_elevation_deg: float = 10.0
    log_level: str = "INFO"


settings = Settings()
