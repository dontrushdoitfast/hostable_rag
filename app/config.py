from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General Service Settings
    APP_NAME: str = "R2R SharePoint Retrieval Service"
    API_V1_STR: str = "/v1"
    API_KEY: str = "default-secret-api-key"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Connector Configuration
    # Options: "dummy" or "sharepoint"
    CONNECTOR_MODE: str = "dummy"
    LOCAL_DATA_DIR: str = "./data/sharepoint_mock"
    MOCK_SHAREPOINT_BASE_URL: str = "https://contoso.sharepoint.com/sites/KnowledgeBase"

    # SharePoint Integration Settings (for production mode)
    SHAREPOINT_TENANT_ID: Optional[str] = None
    SHAREPOINT_CLIENT_ID: Optional[str] = None
    SHAREPOINT_CLIENT_SECRET: Optional[str] = None
    SHAREPOINT_SITE_ID: Optional[str] = None

    # Sync Configuration
    SYNC_INTERVAL_SECONDS: int = 3600  # Default 1 hour
    AUTO_SYNC_ENABLED: bool = True

    # R2R Configuration
    R2R_BASE_URL: str = "http://localhost:7272"
    R2R_API_KEY: Optional[str] = None

    # Azure OpenAI Embedding / LLM Configuration
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: Optional[str] = "text-embedding-ada-002"
    AZURE_OPENAI_API_VERSION: Optional[str] = "2023-05-15"

    # Retrieval Defaults
    DEFAULT_MAX_RESULTS: int = 10
    MAX_ALLOWED_RESULTS: int = 15


settings = Settings()
