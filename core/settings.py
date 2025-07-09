from pydantic_settings import BaseSettings
from pydantic import Field


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
    access_token_expire_minutes: int = Field(..., env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(..., env="REFRESH_TOKEN_EXPIRE_DAYS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 싱글톤 객체
settings = Settings()