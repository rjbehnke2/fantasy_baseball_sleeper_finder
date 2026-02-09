from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fantasy_baseball"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/fantasy_baseball"
    anthropic_api_key: str = ""
    app_env: str = "development"
    log_level: str = "INFO"
    pybaseball_cache_dir: str = ".pybaseball_cache"
    backfill_start_year: int = 2015
    statcast_start_year: int = 2019

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
