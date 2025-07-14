# src/core/config.py
"""
Centralized configuration management for Vritti Invoice AI
Fixed for Pydantic v2 with proper field handling
"""

import os
from pathlib import Path
from typing import List, Optional
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # App Settings
    app_name: str = "Vritti Invoice AI"
    app_version: str = "2.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Legacy API settings (for backward compatibility)
    api_host: Optional[str] = None  # Will map to host
    api_port: Optional[int] = None  # Will map to port

    # Google Cloud Document AI Settings
    gcp_project_id: str = "invoiceprocessingai2498"
    gcp_location: str = "us"
    gcp_processor_id: str = "cca0593594bfdba1"
    google_application_credentials: Optional[str] = None

    # File Upload Settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".gif"]
    upload_dir: str = "uploads"  # Directory for file uploads

    # Processing Settings
    ocr_timeout: int = 30  # seconds
    batch_size_limit: int = 10
    min_confidence_threshold: float = 0.7  # Minimum confidence for processing results

    # Model Settings
    model_path: str = "data/models/document_classifier.pkl"  # Path to ML models

    # CORS Settings
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://192.168.4.185:3000",
        "http://192.168.4.185:8001",
        "https://*.ngrok.io"
    ]

    # Database Settings (optional)
    database_url: Optional[str] = None

    # Feature Flags
    enable_agent_features: bool = False
    enable_batch_processing: bool = True
    enable_mobile_optimization: bool = True

    # Tesseract Settings
    tesseract_cmd: Optional[str] = None

    @field_validator("google_application_credentials", mode="before")
    @classmethod
    def set_gcp_credentials(cls, v):
        """Set Google Cloud credentials path"""
        if v and Path(v).exists():
            return v

        # Try environment variable first
        env_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if env_creds and Path(env_creds).exists():
            return env_creds

        # Get the actual project root (where this config.py file is located)
        config_file = Path(__file__)  # This is src/core/config.py
        project_root = config_file.parent.parent.parent  # Go up 3 levels to project root

        # Try common credential paths relative to project root
        possible_paths = [
            project_root / "invoice-processor-key.json",  # Your actual file location
            project_root / "credentials" / "service-account.json",
            "./invoice-processor-key.json",
            "../invoice-processing-ai/invoice-processor-key.json",
        ]

        for path in possible_paths:
            if path.exists():
                return str(path.resolve())  # Return absolute path

        return None

    @field_validator("tesseract_cmd", mode="before")
    @classmethod
    def set_tesseract_path(cls, v):
        """Auto-detect Tesseract installation"""
        if v:
            return v

        if os.name == 'nt':  # Windows
            tesseract_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME')),
                r'C:\tesseract\tesseract.exe'
            ]

            for path in tesseract_paths:
                if os.path.exists(path):
                    return path

        return None  # Let system PATH handle it

    @field_validator("host", mode="before")
    @classmethod
    def set_host_from_api_host(cls, v, values=None):
        """Map api_host to host for backward compatibility"""
        # If api_host is set in environment, use it
        api_host = os.getenv("API_HOST")
        if api_host:
            return api_host
        return v

    @field_validator("port", mode="before")
    @classmethod
    def set_port_from_api_port(cls, v, values=None):
        """Map api_port to port for backward compatibility"""
        # If api_port is set in environment, use it
        api_port = os.getenv("API_PORT")
        if api_port:
            try:
                return int(api_port)
            except ValueError:
                pass
        return v

    def __init__(self, **kwargs):
        """Initialize with backward compatibility mapping"""
        # Handle legacy field mapping
        if 'api_host' in kwargs and 'host' not in kwargs:
            kwargs['host'] = kwargs['api_host']
        if 'api_port' in kwargs and 'port' not in kwargs:
            kwargs['port'] = kwargs['api_port']

        super().__init__(**kwargs)

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"  # This allows extra fields without error
    }


class ProductionSettings(Settings):
    """Production-specific settings"""
    debug: bool = False
    log_level: str = "WARNING"
    reload: bool = False


class DevelopmentSettings(Settings):
    """Development-specific settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    reload: bool = True


class TestSettings(Settings):
    """Test-specific settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    database_url: str = "sqlite:///./test.db"
    max_file_size: int = 1024 * 1024  # 1MB for tests


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        return ProductionSettings()
    elif environment == "test":
        return TestSettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()