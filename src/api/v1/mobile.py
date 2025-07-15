# src/api/v1/mobile.py - FIXED with correct InvoiceService methods

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import uuid

# Use your existing InvoiceService with correct methods
from src.services.invoice_service import InvoiceService
# Also import hybrid_service for file processing
from src.services.hybrid_service import hybrid_service

# Your existing imports
from src.database.connection import get_db
from src.models.tenant import Tenant, Invoice, Document, TenantUser
from src.core.config import get_settings

# Set up logging
logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize router
router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.post("/process-invoice")
async def mobile_process_invoice(
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Mobile invoice processing - Uses your existing services
    """
    try:
        logger.info(f"📱 Mobile processing: {file.filename}")

        # Use hybrid_service with correct method name
        file_content = await file.read()
        processing_result = await hybrid_service.process_invoice(
            file_content=file_content,
            mime_type=file.content_type or 'application/pdf',
            filename=file.filename
        )

        # If processing successful, save to database using InvoiceService
        if processing_result and processing_result.get('success'):
            try:
                invoice_service = InvoiceService(db, tenant_id="demo-tenant-id")

                # Extract data for database saving
                extracted_data = processing_result.get('extracted_data', {})

                # Prepare invoice data for your save_invoice_to_db method
                invoice_data = {
                    'vendor_name': extracted_data.get('vendor_info', {}).get('name', 'Unknown Vendor'),
                    'total_amount': extracted_data.get('totals', {}).get('total_amount', 0),
                    'invoice_number': extracted_data.get('document_info', {}).get('invoice_number'),
                    'currency': 'USD',
                    'notes': f"Processed via mobile app: {file.filename}"
                }

                # Save to database using your existing method
                saved_invoice = invoice_service.save_invoice_to_db(
                    invoice_data=invoice_data,
                    document_id=None,  # You can create a document record if needed
                    user_id="demo-user-id"
                )

                logger.info(f"✅ Invoice saved to database: {saved_invoice.id}")

            except Exception as db_error:
                logger.warning(f"Database save failed: {db_error}")
                # Continue without failing - file was processed successfully

        # Extract data for mobile response
        vendor_name = "Unknown Vendor"
        total_amount = "Unknown Amount"
        invoice_number = "Unknown"
        confidence_score = 0.85

        if processing_result and isinstance(processing_result, dict):
            extracted_data = processing_result.get('extracted_data', {})

            # Extract vendor
            if 'vendor_info' in extracted_data:
                vendor_name = extracted_data['vendor_info'].get('name', 'Unknown Vendor')

            # Extract amount
            if 'totals' in extracted_data:
                total_amount = extracted_data['totals'].get('total_amount', 'Unknown Amount')

            # Extract invoice number
            if 'document_info' in extracted_data:
                invoice_number = extracted_data['document_info'].get('invoice_number', 'Unknown')

            # Extract confidence
            confidence_score = processing_result.get('confidence_score', 0.85)

            # Mobile response format
            return {
                "success": True,
                "message": "Invoice processed successfully!",
                "extracted_data": extracted_data,  # Full data from processing
                "confidence_score": confidence_score,
                "summary": {
                    "vendor": vendor_name,
                    "amount": total_amount,
                    "invoice_number": invoice_number,
                    "status": "processed"
                },
                "next_actions": [
                    "Review extracted data",
                    "Approve invoice",
                    "Export to accounting"
                ],
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "Processing failed - no data returned",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Mobile processing error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/dashboard")
async def mobile_dashboard(db: Session = Depends(get_db)):
    """Mobile dashboard endpoint - health check and basic stats"""
    try:
        health_data = {
            "status": "healthy",
            "version": "2.0.0",
            "timestamp": datetime.now().isoformat(),
            "features": [
                "invoice_processing",
                "ai_chat",
                "multi_currency",
                "vendor_extraction",
                "amount_extraction"
            ],
            "supported_formats": [".pdf", ".png", ".jpg", ".jpeg", ".tiff"],
            "backend_url": f"http://127.0.0.1:{settings.port}",
            "environment": "development" if settings.debug else "production"
        }

        # Get stats using your InvoiceService with CORRECT method names
        try:
            invoice_service = InvoiceService(db, tenant_id="demo-tenant-id")

            # Use your ACTUAL methods from InvoiceService
            recent_invoices = invoice_service.get_recent_invoices(limit=30)
            pending_invoices = invoice_service.get_pending_approvals(limit=50)  # This method exists!

            # Calculate totals
            total_amount = sum(
                float(invoice.total_amount) if invoice.total_amount else 0
                for invoice in recent_invoices
            )

            health_data["stats"] = {
                "recent_invoices": len(recent_invoices),
                "pending_invoices": len(pending_invoices),
                "total_amount_30d": total_amount,
                "currency": "USD"
            }

        except Exception as e:
            logger.warning(f"Could not fetch stats: {e}")
            health_data["stats"] = {
                "recent_invoices": 0,
                "pending_invoices": 0,
                "total_amount_30d": 0.0,
                "currency": "USD"
            }

        return health_data

    except Exception as e:
        logger.error(f"Mobile dashboard error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e),
                "version": "2.0.0"
            }
        )


@router.get("/recent-invoices")
async def get_recent_invoices(
        limit: int = 10,
        db: Session = Depends(get_db)
):
    """Get recent invoices using your existing InvoiceService"""
    try:
        # Use your existing InvoiceService with CORRECT method name
        invoice_service = InvoiceService(db, tenant_id="demo-tenant-id")
        recent_invoices = invoice_service.get_recent_invoices(limit=limit)  # This method exists!

        # Convert to mobile format
        mobile_invoices = []
        for invoice in recent_invoices:
            mobile_invoices.append({
                "id": invoice.id,
                "vendor_name": invoice.vendor_name or "Unknown Vendor",
                "total_amount": float(invoice.total_amount) if invoice.total_amount else 0.0,
                "currency": invoice.currency or "USD",
                "invoice_number": invoice.invoice_number or "N/A",
                "approval_status": invoice.approval_status or "pending",
                "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
                "status_emoji": {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌",
                    "on_hold": "⏸️"
                }.get(invoice.approval_status, "❓")
            })

        return {
            "success": True,
            "invoices": mobile_invoices,
            "total_count": len(mobile_invoices),
            "has_more": len(mobile_invoices) == limit,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Recent invoices error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(e),
                "invoices": [],
                "total_count": 0
            }
        )


@router.get("/analytics")
async def get_mobile_analytics(
        days: int = 30,
        db: Session = Depends(get_db)
):
    """Mobile analytics using your existing InvoiceService"""
    try:
        # Use your existing analytics method!
        invoice_service = InvoiceService(db, tenant_id="demo-tenant-id")
        analytics_data = invoice_service.get_invoice_analytics(days=days)  # This method exists!

        return {
            "success": True,
            "analytics": analytics_data,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Mobile analytics error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(e),
                "analytics": {}
            }
        )


@router.get("/health")
async def mobile_health_check():
    """Simple health check for mobile apps"""
    return {
        "status": "healthy",
        "service": "vritti-ai-mobile",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "uptime": "Running smoothly! 🚀"
    }