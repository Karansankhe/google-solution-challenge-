from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agentic Backend"
    VERSION: str = "1.0.0"
    
    # API Keys
    GEMINI_API_KEY: str
    OPENWEATHER_API_KEY: str
    NEWS_API_KEY: str
    TAVILY_API_KEY: str
    
    # Security
    API_KEY: str
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache()
def get_settings():
    return Settings()
