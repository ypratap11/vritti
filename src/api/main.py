# src/api/main.py
"""
Final main.py using the complete modular architecture with hybrid service
Clean, focused FastAPI application with centralized configuration
"""

import logging
from pathlib import Path
import sys
from datetime import datetime
from typing import List
import os

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.conversation import router as conversation_router

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import your existing config
from src.core.config import get_settings

# Import modular services
from src.services.document_ai_service import document_ai_service
from src.services.ocr_service import ocr_service
from src.services.hybrid_service import hybrid_service
from src.services.image_service import image_service
from src.processors.currency.currency_config import get_all_currency_codes

from src.api.v1 import mobile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse


# Initialize settings
settings = get_settings()

# Set up logging using config
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app using config
app = FastAPI(
    title=settings.app_name,
    description="AI-powered global invoice processing with multi-currency support",
    version=settings.app_version,
    debug=settings.debug
)

# Mount the frontend landing page
app.mount("/landing", StaticFiles(directory="frontend/landing"), name="landing")

# Add this after your FastAPI app creation
app.include_router(conversation_router, prefix="/api/v1")
app.include_router(mobile.router, prefix="/api/v1")


# Add CORS middleware using config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"🚀 Starting {settings.app_name} v{settings.app_version}...")

    # Debug credential detection
    creds_path = settings.google_application_credentials
    logger.info(f"🔍 Debug - Credential path from config: {creds_path}")

    if creds_path:
        logger.info(f"📋 Found Google Cloud credentials at: {creds_path}")
        if Path(creds_path).exists():
            logger.info("✅ Credential file exists")
            # Set the environment variable for Google Cloud libraries
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(Path(creds_path).resolve())
            logger.info(f"🔧 Set GOOGLE_APPLICATION_CREDENTIALS to: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
        else:
            logger.error(f"❌ Credential file not found at: {creds_path}")
    else:
        logger.warning("⚠️ No Google Cloud credentials path detected")

    # Check environment variable
    env_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    logger.info(f"🌍 Environment GOOGLE_APPLICATION_CREDENTIALS: {env_creds}")

    # Test OCR installation
    if ocr_service.test_installation():
        logger.info("✅ OCR (Tesseract) is working properly")
    else:
        logger.warning("⚠️ OCR (Tesseract) test failed - will use fallback methods")

    # Verify Document AI setup
    if document_ai_service.is_available():
        logger.info("✅ Document AI service ready")
    else:
        logger.warning("⚠️ Document AI service not available")

    # Log supported currencies
    supported_currencies = get_all_currency_codes()
    logger.info(f"🌍 Supporting {len(supported_currencies)} currencies: {', '.join(supported_currencies[:10])}...")

    # Initialize database if enabled
    if settings.database_url:
        try:
            from src.database.connection import create_tables
            create_tables()
            logger.info("✅ Database tables initialized")
        except ImportError:
            logger.info("📊 Running without database (legacy mode)")
        except Exception as e:
            logger.warning(f"⚠️ Database initialization failed: {e}")

    logger.info("🎉 Application startup complete!")

@app.get("/")
async def root():
    """Root endpoint - redirect to landing page or return health info"""
    # You can add a query parameter to get health info: /?health=true
    from fastapi import Request

    # If you want health info, you can access it via /?health=true
    # Otherwise, redirect to landing page
    return RedirectResponse(url="/landing/index.html")

# Add a separate health endpoint:
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": f"🕉️ {settings.app_name} v{settings.app_version}",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "document_ai": document_ai_service.is_available(),
            "ocr_service": ocr_service.is_available(),
            "hybrid_processing": True,
            "image_enhancement": True,
            "multi_currency": True,
            "global_support": True,
            "supported_currencies": len(get_all_currency_codes()),
            "batch_processing": settings.enable_batch_processing,
            "mobile_optimization": settings.enable_mobile_optimization,
            "agent_features": settings.enable_agent_features
        }
    }

@app.get("/config")
async def get_config():
    """Get current configuration"""
    return {
        "max_file_size_mb": settings.max_file_size / (1024 * 1024),
        "allowed_extensions": settings.allowed_extensions,
        "api_version": settings.app_version,
        "supported_currencies": get_all_currency_codes(),
        "batch_size_limit": settings.batch_size_limit,
        "ocr_timeout": settings.ocr_timeout,
        "features": {
            "document_ai": document_ai_service.is_available(),
            "ocr_service": ocr_service.is_available(),
            "hybrid_processing": True,
            "image_enhancement": True,
            "multi_currency": True,
            "global_support": True,
            "batch_processing": settings.enable_batch_processing,
            "mobile_optimization": settings.enable_mobile_optimization,
            "agent_features": settings.enable_agent_features
        }
    }


@app.post("/api/v1/mobile/process-invoice")
async def process_mobile_invoice(file: UploadFile = File(...)):
    """
    🚀 Global mobile invoice processing endpoint using hybrid service
    Supports 30+ currencies and 25+ regions with intelligent processing strategy
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check file extension using config
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.allowed_extensions)}"
        )

    # Read and validate file content using config
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    if len(file_content) > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.max_file_size / (1024 * 1024):.1f}MB"
        )

    # Determine MIME type
    mime_type_map = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".tiff": "image/tiff",
        ".gif": "image/gif"
    }
    mime_type = mime_type_map.get(file_ext, "image/jpeg")

    # Process document using hybrid service
    logger.info(f"🔄 Processing {file.filename} using hybrid service...")
    result = await hybrid_service.process_invoice(file_content, mime_type, file.filename)

    # Add mobile-specific metadata using config
    result["mobile_optimized"] = settings.enable_mobile_optimization
    result["global_support"] = True
    result["supported_currencies"] = get_all_currency_codes()

    return result


@app.post("/process-invoice")
async def process_invoice(file: UploadFile = File(...)):
    """
    Standard invoice processing endpoint using hybrid service
    """
    return await process_mobile_invoice(file)


# Only include batch processing if enabled in config
if settings.enable_batch_processing:
    @app.post("/batch-process")
    async def batch_process_invoices(files: List[UploadFile] = File(...)):
        """
        Process multiple invoice files in batch using hybrid service
        """
        if len(files) > settings.batch_size_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Too many files. Maximum {settings.batch_size_limit} files per batch."
            )

        results = []

        for i, file in enumerate(files):
            try:
                # Validate file
                if not file.filename:
                    results.append({
                        "file_index": i,
                        "filename": "unknown",
                        "success": False,
                        "message": "No filename provided"
                    })
                    continue

                # Check file extension using config
                file_ext = Path(file.filename).suffix.lower()
                if file_ext not in settings.allowed_extensions:
                    results.append({
                        "file_index": i,
                        "filename": file.filename,
                        "success": False,
                        "message": f"Unsupported file type: {file_ext}"
                    })
                    continue

                # Process file
                file_content = await file.read()

                if len(file_content) > settings.max_file_size:
                    results.append({
                        "file_index": i,
                        "filename": file.filename,
                        "success": False,
                        "message": "File too large"
                    })
                    continue

                # Determine MIME type and process
                mime_type_map = {
                    ".pdf": "application/pdf",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".tiff": "image/tiff",
                    ".gif": "image/gif"
                }
                mime_type = mime_type_map.get(file_ext, "image/jpeg")

                # Process document using hybrid service
                result = await hybrid_service.process_invoice(file_content, mime_type, file.filename)

                results.append({
                    "file_index": i,
                    "filename": file.filename,
                    **result
                })

            except Exception as e:
                results.append({
                    "file_index": i,
                    "filename": file.filename if file.filename else "unknown",
                    "success": False,
                    "message": f"Processing error: {str(e)}"
                })

        return {
            "batch_results": results,
            "total_files": len(files),
            "successful_files": sum(1 for r in results if r.get("success", False)),
            "failed_files": sum(1 for r in results if not r.get("success", False))
        }


@app.get("/api/v1/mobile/dashboard")
async def get_mobile_dashboard():
    """Mobile dashboard data"""
    return {
        "status": "healthy",
        "message": f"🕉️ {settings.app_name} v{settings.app_version} ready",
        "app_name": settings.app_name,
        "features": {
            "camera_scan": True,
            "ai_chat": settings.enable_agent_features,
            "document_ai": document_ai_service.is_available(),
            "ocr_service": ocr_service.is_available(),
            "hybrid_processing": True,
            "image_enhancement": True,
            "multi_currency": True,
            "global_support": True,
            "supported_currencies": len(get_all_currency_codes()),
            "batch_processing": settings.enable_batch_processing,
            "mobile_optimization": settings.enable_mobile_optimization
        },
        "version": settings.app_version
    }


@app.get("/api/v1/image/analyze")
async def analyze_image_quality(file: UploadFile = File(...)):
    """
    Analyze uploaded image quality for processing optimization
    """
    try:
        file_content = await file.read()
        analysis = image_service.analyze_image_quality(file_content)

        return {
            "success": True,
            "filename": file.filename,
            "analysis": analysis
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )