import os
from typing import Optional
try:
    from pydantic import BaseSettings, Field
except ImportError:
    from pydantic_settings import BaseSettings
    from pydantic import Field

class Config(BaseSettings):
    """Configuration management for the transcript summarizer application."""
    
    # Ollama Configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        env="OLLAMA_BASE_URL",
        description="Base URL for Ollama API"
    )
    
    model_name: str = Field(
        default="llama3",
        env="MODEL_NAME",
        description="Name of the LLaMA model to use"
    )
    
    # Chunking Configuration
    chunk_size: int = Field(
        default=2000,
        env="CHUNK_SIZE",
        description="Maximum tokens per chunk"
    )
    
    chunk_overlap: int = Field(
        default=200,
        env="CHUNK_OVERLAP",
        description="Token overlap between chunks"
    )
    
    # Gradio Configuration
    gradio_port: int = Field(
        default=7860,
        env="GRADIO_PORT",
        description="Port for Gradio server"
    )
    
    # Processing Configuration
    max_concurrent_requests: int = Field(
        default=3,
        env="MAX_CONCURRENT_REQUESTS",
        description="Maximum concurrent API requests"
    )
    
    request_timeout: int = Field(
        default=300,
        env="REQUEST_TIMEOUT",
        description="Request timeout in seconds"
    )
    
    # Temperature for LLM
    temperature: float = Field(
        default=0.3,
        env="TEMPERATURE",
        description="Temperature for text generation"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global config instance
config = Config()
