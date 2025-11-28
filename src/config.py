"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Configuration
    api_title: str = "AI Ticket Classifier"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Azure OpenAI Configuration
    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., env="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(default="gpt-4", env="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = "2024-02-15-preview"
    
    # Cosmos DB Configuration
    cosmos_endpoint: str = Field(..., env="COSMOS_ENDPOINT")
    cosmos_key: str = Field(..., env="COSMOS_KEY")
    cosmos_database: str = "ticketdb"
    cosmos_container: str = "classifications"
    
    # Application Insights
    appinsights_connection_string: Optional[str] = Field(None, env="APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    # Logging
    log_level: str = "INFO"
    
    # Classification Categories
    categories: list[str] = [
        "Billing",
        "Technical",
        "Feature Request",
        "Bug Report",
        "Account Management"
    ]
    
    priorities: list[str] = [
        "Critical",
        "High", 
        "Medium",
        "Low"
    ]
    
    # Model Configuration
    temperature: float = 0.0
    max_tokens: int = 500
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()