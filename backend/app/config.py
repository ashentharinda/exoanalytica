from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./exo.db"
    jwt_secret: str  # required: no default on purpose
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 60
    jobs_root: str = "/data/jobs"
    max_upload_mb: int = 25
    worker_timeout_s: int = 240
    worker_mem_mb: int = 3072
    max_active_jobs_per_user: int = 3
    model_path: str = "/app/weights/exo_cnn.pt"
    cors_origins: str = "http://localhost:8080"
    storage_backend: str = "local"  # local | s3
    s3_bucket: str = ""


settings = Settings()
