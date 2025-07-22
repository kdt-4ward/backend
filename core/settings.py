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

    # === Google OAuth ===
    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(..., env="GOOGLE_REDIRECT_URI")
    
    # === JWT ===
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(..., env="ALGORITHM")
    access_token_expire_seconds: int = Field(..., env="ACCESS_TOKEN_EXPIRE_SECONDS")
    refresh_token_expire_seconds: int = Field(..., env="REFRESH_TOKEN_EXPIRE_SECONDS")

    # === TMDB ===
    tmdb_api_key: str = Field(..., env="TMDB_API_KEY")

    # === YouTube ===
    youtube_api_key: str = Field(..., env="YOUTUBE_API_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

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