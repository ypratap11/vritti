# src/services/hybrid_service.py
"""
Hybrid processing service - Orchestrates Document AI, OCR, and Global Currency Processing
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from .document_ai_service import document_ai_service
from .ocr_service import ocr_service
from .image_service import image_service
from ..processors.currency.amount_extractor import amount_extractor
from ..processors.vendor.vendor_extractor import vendor_extractor
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class HybridProcessingService:
    """
    Orchestrates multiple processing services for optimal invoice extraction
    """

    def __init__(self):
        self.settings = get_settings()

    async def process_invoice(self, file_content: bytes, mime_type: str, filename: str) -> Dict[str, Any]:
        """
        Main hybrid processing method that intelligently combines services

        Args:
            file_content: Document content as bytes
            mime_type: MIME type of the document
            filename: Original filename

        Returns:
            Dict with processing results
        """
        start_time = datetime.now()

        logger.info(f"🔄 Starting hybrid processing for: {filename}")

        try:
            # Step 1: Enhance image if it's an image file
            processed_content = file_content
            if mime_type.startswith("image/"):
                logger.info("🎨 Enhancing image quality...")
                processed_content = image_service.enhance_for_processing(file_content)

            # Step 2: Determine processing strategy
            strategy = self._determine_processing_strategy(mime_type, len(file_content))
            logger.info(f"📋 Selected processing strategy: {strategy}")

            # Step 3: Execute processing based on strategy
            if strategy == "document_ai_primary":
                result = await self._process_with_document_ai_primary(processed_content, mime_type, filename)
            elif strategy == "ocr_primary":
                result = await self._process_with_ocr_primary(processed_content, filename)
            elif strategy == "dual_processing":
                result = await self._process_with_dual_approach(processed_content, mime_type, filename)
            else:
                result = await self._process_with_fallback(processed_content, mime_type, filename)

            # Step 4: Add processing metadata
            processing_time = (datetime.now() - start_time).total_seconds()
            result["processing_time"] = processing_time
            result["strategy_used"] = strategy
            result["file_info"] = {
                "filename": filename,
                "mime_type": mime_type,
                "file_size_mb": len(file_content) / (1024 * 1024),
                "enhanced": mime_type.startswith("image/")
            }

            logger.info(f"✅ Hybrid processing completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Hybrid processing failed: {e}")

            return {
                "success": False,
                "message": f"Hybrid processing failed: {str(e)}",
                "error_details": str(e),
                "processing_time": processing_time,
                "strategy_used": "error"
            }

    def _determine_processing_strategy(self, mime_type: str, file_size: int) -> str:
        """
        Intelligently determine the best processing strategy
        """
        # Document AI availability
        doc_ai_available = document_ai_service.is_available()
        ocr_available = ocr_service.is_available()

        # File characteristics
        is_pdf = mime_type == "application/pdf"
        is_image = mime_type.startswith("image/")
        is_large_file = file_size > 5 * 1024 * 1024  # 5MB

        # Strategy decision logic
        if doc_ai_available and is_pdf:
            return "document_ai_primary"  # PDFs work best with Document AI
        elif doc_ai_available and is_image and not is_large_file:
            return "dual_processing"  # Compare both for images
        elif ocr_available and is_image:
            return "ocr_primary"  # OCR for images when Doc AI unavailable
        elif doc_ai_available:
            return "document_ai_primary"  # Fallback to Document AI
        elif ocr_available:
            return "ocr_primary"  # Fallback to OCR
        else:
            return "fallback"  # Emergency fallback

    async def _process_with_document_ai_primary(self, file_content: bytes, mime_type: str, filename: str) -> Dict[
        str, Any]:
        """
        Process primarily with Document AI, fallback to OCR if needed
        """
        logger.info("🤖 Processing with Document AI (primary)...")

        # Try Document AI first
        doc_ai_result = await document_ai_service.process_document(file_content, mime_type)

        if doc_ai_result["success"] and doc_ai_result["document_text"]:
            # Extract structured data using global processors
            amount_info = amount_extractor.extract_amounts(doc_ai_result["document_text"])

            # Try to extract vendor info
            try:
                vendor_info = vendor_extractor.extract_vendor(doc_ai_result["document_text"])
            except:
                # Fallback vendor extraction
                vendor_info = self._extract_vendor_from_entities(doc_ai_result.get("entities", []))

            # Calculate confidence
            confidence_scores = doc_ai_result.get("confidence_scores", {})
            avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0.0

            return {
                "success": True,
                "message": "✅ Processed with Document AI + Global Currency Processing",
                "method": "document_ai_primary",
                "extracted_data": {
                    "vendor_info": vendor_info,
                    "totals": {
                        "total_amount": amount_info.get('final_amount', 'Unknown'),
                        "detected_amounts": amount_info.get('all_detected_amounts', []),
                        "currency": amount_info.get('currency', 'USD'),
                        "region": amount_info.get('region', 'US')
                    }
                },
                "confidence_score": avg_confidence,
                "processing_details": {
                    "amount_score": amount_info.get('best_score', 0),
                    "vendor_score": vendor_info.get('best_score', 0) if isinstance(vendor_info, dict) else 0,
                    "entities_found": len(doc_ai_result.get("entities", [])),
                    "document_text_length": len(doc_ai_result.get("document_text", "")),
                    "detected_currency": amount_info.get('currency', 'USD'),
                    "detected_region": amount_info.get('region', 'US')
                }
            }

        # Fallback to OCR if Document AI fails
        logger.info("🔍 Document AI failed, falling back to OCR...")
        return await self._process_with_ocr_primary(file_content, filename)

    async def _process_with_ocr_primary(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Process primarily with OCR
        """
        logger.info("🔍 Processing with OCR (primary)...")

        # Extract text with OCR
        ocr_result = ocr_service.extract_text(file_content, enhance=True)

        if ocr_result["success"] and ocr_result["extracted_text"]:
            # Extract structured data using global processors
            amount_info = amount_extractor.extract_amounts(ocr_result["extracted_text"])

            # Extract vendor info
            try:
                vendor_info = vendor_extractor.extract_vendor(ocr_result["extracted_text"])
            except:
                # Fallback vendor extraction
                vendor_info = self._extract_vendor_from_text_simple(ocr_result["extracted_text"])

            return {
                "success": True,
                "message": "✅ Processed with OCR + Global Currency Processing",
                "method": "ocr_primary",
                "extracted_data": {
                    "vendor_info": vendor_info,
                    "totals": {
                        "total_amount": amount_info.get('final_amount', 'Unknown'),
                        "detected_amounts": amount_info.get('all_detected_amounts', []),
                        "currency": amount_info.get('currency', 'USD'),
                        "region": amount_info.get('region', 'US')
                    }
                },
                "confidence_score": 0.7,  # OCR has lower confidence
                "processing_details": {
                    "amount_score": amount_info.get('best_score', 0),
                    "vendor_score": vendor_info.get('best_score', 0) if isinstance(vendor_info, dict) else 0,
                    "text_length": len(ocr_result["extracted_text"]),
                    "detected_currency": amount_info.get('currency', 'USD'),
                    "detected_region": amount_info.get('region', 'US')
                }
            }

        # OCR failed
        return {
            "success": False,
            "message": "❌ OCR processing failed",
            "method": "ocr_primary",
            "error_details": ocr_result.get("error", "Unknown OCR error")
        }

    async def _process_with_dual_approach(self, file_content: bytes, mime_type: str, filename: str) -> Dict[str, Any]:
        """
        Process with both Document AI and OCR, compare results
        """
        logger.info("🔄 Processing with dual approach (Document AI + OCR)...")

        # Run both in parallel (simulated)
        doc_ai_result = await document_ai_service.process_document(file_content, mime_type)
        ocr_result = ocr_service.extract_text(file_content, enhance=True)

        # Determine which result is better
        doc_ai_success = doc_ai_result["success"] and doc_ai_result["document_text"]
        ocr_success = ocr_result["success"] and ocr_result["extracted_text"]

        if doc_ai_success and ocr_success:
            # Compare text lengths and confidence
            doc_ai_text_length = len(doc_ai_result["document_text"])
            ocr_text_length = len(ocr_result["extracted_text"])

            # Use Document AI if it extracted significantly more text
            if doc_ai_text_length > ocr_text_length * 1.2:
                logger.info("📊 Using Document AI result (better text extraction)")
                return await self._process_with_document_ai_primary(file_content, mime_type, filename)
            else:
                logger.info("📊 Using OCR result (comparable text extraction)")
                return await self._process_with_ocr_primary(file_content, filename)

        elif doc_ai_success:
            return await self._process_with_document_ai_primary(file_content, mime_type, filename)
        elif ocr_success:
            return await self._process_with_ocr_primary(file_content, filename)
        else:
            return {
                "success": False,
                "message": "❌ Both Document AI and OCR failed",
                "method": "dual_approach",
                "error_details": "No successful text extraction"
            }

    async def _process_with_fallback(self, file_content: bytes, mime_type: str, filename: str) -> Dict[str, Any]:
        """
        Emergency fallback processing
        """
        logger.warning("⚠️ Using emergency fallback processing...")

        return {
            "success": False,
            "message": "❌ No processing services available",
            "method": "fallback",
            "error_details": "Neither Document AI nor OCR services are available"
        }

    def _extract_vendor_from_entities(self, entities: List[Any]) -> Dict[str, Any]:
        """
        Extract vendor info from Document AI entities (fallback)
        """
        vendor_name = "Unknown"

        for entity in entities:
            entity_type = entity.type_.lower()
            if entity_type in ["supplier_name", "vendor_name", "remit_to_name"]:
                vendor_name = entity.mention_text if entity.mention_text else "Unknown"
                break

        return {
            "name": vendor_name,
            "method": "document_ai_entities",
            "confidence": 0.8,
            "best_score": 80
        }

    def _extract_vendor_from_text_simple(self, text: str) -> Dict[str, Any]:
        """
        Simple vendor extraction from text (fallback)
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Look for business indicators in first few lines
        business_indicators = ['LLC', 'INC', 'CORP', 'COMPANY', 'LTD', 'GMBH', 'SARL', 'SAS']

        for line in lines[:5]:  # Check first 5 lines
            line_upper = line.upper()
            if any(indicator in line_upper for indicator in business_indicators):
                if 3 < len(line) < 60:  # Reasonable length
                    return {
                        "name": line,
                        "method": "simple_text_extraction",
                        "confidence": 0.6,
                        "best_score": 60
                    }

        # Fallback to first non-empty line
        vendor_name = lines[0] if lines else "Unknown"

        return {
            "name": vendor_name,
            "method": "first_line_fallback",
            "confidence": 0.3,
            "best_score": 30
        }


# Global service instance
hybrid_service = HybridProcessingService()