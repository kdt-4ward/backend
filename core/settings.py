from pydantic_settings import BaseSettings
from pydantic import Field
import itertools
import asyncio

class Settings(BaseSettings):
    # === 앱 설정 ===
    app_name: str = Field(default="LuvTune", env="APP_NAME")
    environment: str = Field(default="development", env="ENVIRONMENT")  # development, production, test
    debug: bool = Field(default=True, env="DEBUG")
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")

    # === OpenAI ===
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")

    # === DB ===
    db_user: str = Field(..., env="DB_USER")
    db_password: str = Field(..., env="DB_PASSWORD")
    db_endpoint: str = Field(..., env="DB_ENDPOINT")
    db_port: int = Field(default=3306, env="DB_PORT")
    db_name: str = Field(..., env="DB_NAME")

    # === Redis ===
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # === JWT ===
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(..., env="ALGORITHM")
    access_token_expire_seconds: int = Field(..., env="ACCESS_TOKEN_EXPIRE_SECONDS")
    refresh_token_expire_seconds: int = Field(..., env="REFRESH_TOKEN_EXPIRE_SECONDS")

    # === TMDB ===
    tmdb_api_key: str = Field(..., env="TMDB_API_KEY")

    # === YouTube ===
    youtube_api_key: str = Field(..., env="YOUTUBE_API_KEY")

    # == AWS ===
    s3_access_key: str = Field(..., env="S3_ACCESS_KEY")
    s3_secret_access_key: str = Field(..., env="S3_SECRET_ACCESS_KEY")
    s3_region: str = Field(..., env="S3_REGION")
    s3_bucket_name: str = Field(..., env="S3_BUCKET_NAME")

    # === Summary ===
    sum_turn_threshold: int = Field(..., env="SUM_TURN_THRESHOLD")
    sum_remaining_size: int = Field(..., env="SUM_REMAINING_SIZE")
    sum_trigger_tokens: int = Field(..., env="SUM_TRIGGER_TOKENS")

    # === FAISS ===
    faiss_turns_per_chunk: int = Field(..., env="FAISS_TURNS_PER_CHUNK")
    faiss_overlap_turns: int = Field(..., env="FAISS_OVERLAP_TURNS")
    faiss_threshold: float = Field(..., env="FAISS_THRESHOLD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._api_key_list = [k.strip() for k in self.openai_api_key.split(",") if k.strip()]
        self._key_iter = itertools.cycle(self._api_key_list)
        self._key_lock = asyncio.Lock()

    async def get_next_api_key(self):
        async with self._key_lock:
            return next(self._key_iter)
# 싱글톤 객체
settings = Settings()