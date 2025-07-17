# src/core/config.py
"""
Centralized configuration management for Vritti Invoice AI
Updated for NEW GCP Account: vritti-invoice-ai-dev
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
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

    # NEW GCP Account Settings - Updated for vritti-invoice-ai-dev
    gcp_project_id: str = "vritti-invoice-ai-dev"
    gcp_location: str = "us"
    gcp_processor_id: str = "13b516481d9fc574"  # Your new processor ID
    google_application_credentials: Optional[str] = None

    # Environment-specific project IDs (for future scaling)
    gcp_project_dev: str = "vritti-invoice-ai-dev"
    gcp_project_staging: str = "vritti-invoice-ai-staging"
    gcp_project_prod: str = "vritti-invoice-ai-prod"

    # Company Information
    company_domain: str = "vritti.us"
    admin_email: str = "pratap.yeragudipati@vritti.us"
    support_email: str = "support@vritti.us"

    # File Upload Settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".gif"]
    upload_dir: str = "uploads"

    # Processing Settings
    ocr_timeout: int = 30
    batch_size_limit: int = 10
    min_confidence_threshold: float = 0.7

    # Model Settings
    model_path: str = "data/models/document_classifier.pkl"

    # CORS Settings - Updated for vritti.us domain
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.4.185:3000",
        "http://192.168.4.185:8001",
        "https://*.ngrok.io",
        "https://*.vritti.us",
        "https://app.vritti.us"
    ]

    # Database Settings
    database_url: Optional[str] = None

    # Authentication & Security
    secret_key: str = "vritti-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Feature Flags
    enable_agent_features: bool = False
    enable_batch_processing: bool = True
    enable_mobile_optimization: bool = True

    # LLM Settings - Added the missing configuration
    default_llm_model: str = "gemini-1.5-flash"
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    llm_cost_threshold: float = 0.01  # Cost threshold for LLM usage
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 3

    # Tesseract Settings
    tesseract_cmd: Optional[str] = None

    @field_validator("gcp_project_id", mode="before")
    @classmethod
    def set_project_by_environment(cls, v):
        """Set GCP project based on environment"""
        environment = os.getenv("ENVIRONMENT", "development").lower()

        project_mapping = {
            "development": "vritti-invoice-ai-dev",
            "staging": "vritti-invoice-ai-staging",
            "production": "vritti-invoice-ai-prod"
        }

        # Use environment variable if set, otherwise use mapping
        env_project = os.getenv("GCP_PROJECT_ID")
        if env_project:
            return env_project

        return project_mapping.get(environment, v)

    @field_validator("gcp_processor_id", mode="before")
    @classmethod
    def set_processor_by_environment(cls, v):
        """Set processor ID based on environment"""
        environment = os.getenv("ENVIRONMENT", "development").lower()

        # For now, all environments use the same processor
        # In the future, you might have different processors per environment
        processor_mapping = {
            "development": "13b516481d9fc574",  # Your new processor
            "staging": "13b516481d9fc574",  # Same for now
            "production": "13b516481d9fc574"  # Will be different in production
        }

        env_processor = os.getenv("GCP_PROCESSOR_ID")
        if env_processor:
            return env_processor

        return processor_mapping.get(environment, v)

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

        # Get project root
        config_file = Path(__file__)
        project_root = config_file.parent.parent.parent

        # NEW: Credential file paths for new GCP account
        possible_paths = [
            project_root / "vritti-dev-key.json",  # New service account key
            project_root / "credentials" / "vritti-dev-key.json",
            project_root / "keys" / "vritti-dev-key.json",
            # Fallback to old paths during migration
            project_root / "invoice-processor-key.json",
            "./vritti-dev-key.json"
        ]

        for path in possible_paths:
            if path.exists():
                return str(path.resolve())

        return None

    @field_validator("database_url", mode="before")
    @classmethod
    def set_database_by_environment(cls, v):
        """Set database URL based on environment"""
        env_db_url = os.getenv("DATABASE_URL")
        if env_db_url:
            return env_db_url

        environment = os.getenv("ENVIRONMENT", "development").lower()

        # Environment-specific defaults
        if environment == "production":
            return os.getenv("DATABASE_URL_PROD") or "postgresql://user:pass@prod-db/vritti_prod"
        elif environment == "staging":
            return os.getenv("DATABASE_URL_STAGING") or "postgresql://user:pass@staging-db/vritti_staging"
        else:
            return "sqlite:///./vritti_dev.db"

    @field_validator("secret_key", mode="before")
    @classmethod
    def set_secret_key(cls, v):
        """Generate or get secret key"""
        env_secret = os.getenv("SECRET_KEY")
        if env_secret:
            return env_secret

        if os.getenv("ENVIRONMENT") == "production":
            raise ValueError("SECRET_KEY must be set in production environment")

        return v  # Use default for development

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

        return None

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def set_gemini_api_key(cls, v):
        """Set Gemini API key from environment"""
        return v or os.getenv("GEMINI_API_KEY")

    def get_full_processor_name(self) -> str:
        """Get the full processor name for Document AI API calls"""
        return f"projects/{self.gcp_project_id}/locations/{self.gcp_location}/processors/{self.gcp_processor_id}"

    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration for AskVritti"""
        return {
            "gemini_api_key": self.gemini_api_key,
            "openai_api_key": None,  # Force disable OpenAI
            "anthropic_api_key": None,  # Force disable Anthropic
            "gcp_project_id": self.gcp_project_id,
            "enable_intelligent_routing": False,  # Disable routing, use Gemini only
            "cost_threshold": self.llm_cost_threshold,
            "fallback_model": "gemini-1.5-flash",  # Force Gemini as fallback
            "model_preferences": {
                "simple": "gemini-1.5-flash",  # All tasks use Gemini
                "medium": "gemini-1.5-flash",  # All tasks use Gemini
                "complex": "gemini-1.5-flash"  # All tasks use Gemini
            },
            "timeout_seconds": self.llm_timeout_seconds,
            "max_retries": self.llm_max_retries,
            "default_model": self.default_llm_model
        }

    def get_gcp_config(self) -> Dict[str, Any]:
        """Get Google Cloud Platform configuration"""
        return {
            "project_id": self.gcp_project_id,
            "location": self.gcp_location,
            "processor_id": self.gcp_processor_id,
            "credentials_path": self.google_application_credentials,
            "full_processor_name": self.get_full_processor_name()
        }

    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration"""
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"]
        }

    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that required API keys are available"""
        validation_results = {
            "gemini_available": bool(self.gemini_api_key),
            "gcp_credentials_available": bool(self.google_application_credentials),
            "openai_available": bool(self.openai_api_key),
            "anthropic_available": bool(self.anthropic_api_key)
        }

        # Log validation results
        if self.debug:
            for service, available in validation_results.items():
                status = "✅" if available else "❌"
                print(f"  {status} {service.replace('_', ' ').title()}")

        return validation_results

    def has_required_llm_keys(self) -> bool:
        """Check if at least one LLM API key is available"""
        validation = self.validate_api_keys()
        return (validation["gemini_available"] or
                validation["openai_available"] or
                validation["anthropic_available"])

    def get_available_llm_models(self) -> List[str]:
        """Get list of available LLM models based on API keys"""
        available_models = []
        validation = self.validate_api_keys()

        if validation["gemini_available"]:
            available_models.extend([
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-pro"
            ])

        if validation["openai_available"]:
            available_models.extend([
                "gpt-4",
                "gpt-3.5-turbo"
            ])

        if validation["anthropic_available"]:
            available_models.extend([
                "claude-3-sonnet",
                "claude-3-haiku"
            ])

        return available_models

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }


class ProductionSettings(Settings):
    """Production-specific settings"""
    debug: bool = False
    log_level: str = "WARNING"
    reload: bool = False
    gcp_project_id: str = "vritti-invoice-ai-prod"
    enable_agent_features: bool = True
    access_token_expire_minutes: int = 15  # Shorter tokens in production


class DevelopmentSettings(Settings):
    """Development-specific settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    reload: bool = True
    gcp_project_id: str = "vritti-invoice-ai-dev"
    gcp_processor_id: str = "13b516481d9fc574"


class StagingSettings(Settings):
    """Staging-specific settings"""
    debug: bool = False
    log_level: str = "INFO"
    reload: bool = False
    gcp_project_id: str = "vritti-invoice-ai-staging"


class TestSettings(Settings):
    """Test-specific settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    gcp_project_id: str = "vritti-invoice-ai-test"
    database_url: str = "sqlite:///./test.db"
    max_file_size: int = 1024 * 1024  # 1MB for tests


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    environment = os.getenv("ENVIRONMENT", "development").lower()

    settings_mapping = {
        "production": ProductionSettings,
        "staging": StagingSettings,
        "test": TestSettings,
        "development": DevelopmentSettings
    }

    settings_class = settings_mapping.get(environment, DevelopmentSettings)
    return settings_class()


# Global settings instance
settings = get_settings()


# Migration verification function
def verify_new_gcp_setup():
    """Verify the new GCP setup is working correctly"""
    current_settings = get_settings()

    checks = {
        "✅ New project ID": current_settings.gcp_project_id == "vritti-invoice-ai-dev",
        "✅ New processor ID": current_settings.gcp_processor_id == "13b516481d9fc574",
        "✅ Credentials file exists": current_settings.google_application_credentials is not None,
        "✅ Company domain set": current_settings.company_domain == "vritti.us",
        "✅ Business email set": current_settings.admin_email == "pratap.yeragudipati@vritti.us",
        "✅ LLM config available": current_settings.get_llm_config() is not None
    }

    print("🔍 New GCP Setup Verification:")
    for check, passed in checks.items():
        print(f"  {check if passed else '❌ ' + check[2:]}")

    # Show LLM configuration
    llm_config = current_settings.get_llm_config()
    print(f"\n🤖 LLM Configuration:")
    print(f"  Default model: {llm_config['fallback_model']}")
    print(f"  Gemini API key set: {'✅' if llm_config['gemini_api_key'] else '❌'}")
    print(f"  GCP project: {llm_config['gcp_project_id']}")

    all_passed = all(checks.values())
    if all_passed:
        print("\n🎉 All checks passed! New GCP setup is ready.")
    else:
        print("\n⚠️ Some checks failed. Please review configuration.")

    return all_passed


if __name__ == "__main__":
    # Run verification when script is executed directly
    verify_new_gcp_setup()