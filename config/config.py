import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base workspace path
BASE_DIR = Path(__file__).resolve().parent.parent

class AppConfig(BaseModel):
    name: str = "AI-Driven Video Evidence Analysis System"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    upload_dir: str = "data/uploads"
    output_dir: str = "data/processed"

    @property
    def upload_path(self) -> Path:
        p = BASE_DIR / self.upload_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def output_path(self) -> Path:
        p = BASE_DIR / self.output_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

class AzureConfig(BaseModel):
    api_key: Optional[str] = Field(default=None)
    endpoint: Optional[str] = Field(default=None)
    video_indexer_id: Optional[str] = Field(default=None)
    video_indexer_location: str = "trial"
    openai_api_key: Optional[str] = Field(default=None)
    openai_api_version: str = "2023-05-15"
    openai_deployment: str = "gpt-4"
    openai_embeddings_deployment: str = "text-embedding-ada-002"

class DatabricksConfig(BaseModel):
    host: Optional[str] = Field(default=None)
    token: Optional[str] = Field(default=None)
    cluster_id: Optional[str] = Field(default=None)
    workspace_path: str = "/Shared/video_evidence_etl"

class LangChainConfig(BaseModel):
    vector_store_path: str = "data/vector_store"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    @property
    def vector_store_dir(self) -> Path:
        p = BASE_DIR / self.vector_store_path
        p.mkdir(parents=True, exist_ok=True)
        return p

class Settings(BaseSettings):
    app: AppConfig = AppConfig()
    azure: AzureConfig = AzureConfig()
    databricks: DatabricksConfig = DatabricksConfig()
    langchain: LangChainConfig = LangChainConfig()

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
        extra="ignore"
    )

    @classmethod
    def load_settings(cls) -> "Settings":
        yaml_path = BASE_DIR / "config" / "settings.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r") as f:
                try:
                    yaml_data = yaml.safe_load(f) or {}
                except Exception:
                    yaml_data = {}
        else:
            yaml_data = {}

        # Merge environment variables directly if needed, Pydantic-Settings handles nesting
        # But to be safe, we load yaml into Settings constructor
        settings = cls(**yaml_data)
        
        # Override with environment variables directly if provided
        if os.getenv("AZURE_OPENAI_API_KEY"):
            settings.azure.openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if os.getenv("AZURE_API_KEY"):
            settings.azure.api_key = os.getenv("AZURE_API_KEY")
        if os.getenv("DATABRICKS_TOKEN"):
            settings.databricks.token = os.getenv("DATABRICKS_TOKEN")
            
        return settings

# Global settings instance
settings = Settings.load_settings()
