# src/services/document_ai_service.py
"""
Google Document AI service - Using centralized config with lazy initialization
"""

import logging
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path

from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Try to import Google Cloud libraries, handle if not available
try:
    from google.cloud import documentai
    from google.api_core.client_options import ClientOptions

    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    logger.warning("Google Cloud libraries not available")


class DocumentAIService:
    """Google Document AI service wrapper using centralized config"""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional = None
        self.processor_name: Optional[str] = None
        self.available = None  # None = not initialized, True/False = initialized
        self._initialization_attempted = False

    def _initialize_client(self) -> None:
        """Initialize Document AI client using config settings (lazy initialization)"""
        if self._initialization_attempted:
            return  # Don't try again if we already attempted

        self._initialization_attempted = True

        try:
            if not GOOGLE_CLOUD_AVAILABLE:
                logger.warning("⚠️ Google Cloud SDK not available")
                self.available = False
                return

            # Check for credentials in environment variable first
            creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if not creds_path:
                creds_path = self.settings.google_application_credentials
                if creds_path:
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)
                    logger.info(f"📋 Set credentials from config: {creds_path}")

            if not creds_path or not Path(creds_path).exists():
                logger.warning("Google Cloud credentials not found - Document AI will be unavailable")
                self.available = False
                return

            logger.info(f"🔧 Using Google Cloud credentials: {creds_path}")

            # Set up client options for the specified location
            opts = ClientOptions(api_endpoint=f"{self.settings.gcp_location}-documentai.googleapis.com")
            self.client = documentai.DocumentProcessorServiceClient(client_options=opts)

            # Create processor name
            self.processor_name = self.client.processor_path(
                self.settings.gcp_project_id,
                self.settings.gcp_location,
                self.settings.gcp_processor_id
            )

            self.available = True
            logger.info(f"✅ Document AI client initialized for location: {self.settings.gcp_location}")
            logger.info(f"Using project: {self.settings.gcp_project_id}, processor: {self.settings.gcp_processor_id}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize Document AI client: {e}")
            self.client = None
            self.available = False

    def is_available(self) -> bool:
        """Check if Document AI service is available (with lazy initialization)"""
        if self.available is None:
            self._initialize_client()
        return self.available and self.client is not None and self.processor_name is not None

    async def process_document(self, file_content: bytes, mime_type: str) -> Dict[str, Any]:
        """
        Process document using Google Document AI

        Args:
            file_content: Document content as bytes
            mime_type: MIME type of the document

        Returns:
            Dict with processing results
        """
        start_time = datetime.now()

        try:
            # This will trigger lazy initialization if needed
            if not self.is_available():
                return {
                    "success": False,
                    "message": "Document AI service not available - check credentials",
                    "extracted_data": None,
                    "confidence_scores": None,
                    "processing_time": 0,
                    "entities": [],
                    "document_text": ""
                }

            logger.info(f"Processing document with Document AI (MIME: {mime_type})")

            # Create document object
            raw_document = documentai.RawDocument(content=file_content, mime_type=mime_type)

            # Create process request
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )

            # Process the document
            logger.info("Sending document to Document AI...")
            result = self.client.process_document(request=request)
            document = result.document

            logger.info(f"Document processed. Found {len(document.entities)} entities")

            # Extract structured data
            extracted_data, confidence_scores = self._extract_structured_data(document)

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "message": "Document processed successfully with Google Document AI",
                "document": document,  # Return the full document for further processing
                "extracted_data": extracted_data,
                "confidence_scores": confidence_scores,
                "processing_time": processing_time,
                "entities": document.entities,
                "document_text": document.text if hasattr(document, 'text') else ""
            }

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "success": False,
                "message": f"Processing failed: {str(e)}",
                "extracted_data": None,
                "confidence_scores": None,
                "processing_time": processing_time,
                "entities": [],
                "document_text": ""
            }

    def _extract_structured_data(self, document) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Extract structured data from processed document"""

        extracted_data = {
            "vendor_info": {},
            "invoice_details": {},
            "line_items": [],
            "totals": {},
            "dates": {},
            "addresses": {}
        }

        confidence_scores = {}

        # Process entities
        for entity in document.entities:
            entity_type = entity.type_
            entity_value = entity.mention_text if entity.mention_text else ""
            confidence = entity.confidence

            # Store confidence scores
            confidence_scores[entity_type] = confidence

            # Categorize entities based on common invoice fields
            self._categorize_entity(entity_type, entity_value, extracted_data)

        # Process tables (line items)
        self._extract_table_data(document, extracted_data)

        return extracted_data, confidence_scores

    def _categorize_entity(self, entity_type: str, entity_value: str, extracted_data: Dict[str, Any]) -> None:
        """Categorize entity based on type"""

        if entity_type in ["supplier_name", "vendor_name", "remit_to_name"]:
            extracted_data["vendor_info"]["name"] = entity_value
        elif entity_type in ["supplier_address", "vendor_address", "remit_to_address"]:
            extracted_data["addresses"]["vendor_address"] = entity_value
        elif entity_type in ["invoice_id", "invoice_number"]:
            extracted_data["invoice_details"]["invoice_number"] = entity_value
        elif entity_type in ["invoice_date", "invoice_issue_date"]:
            extracted_data["dates"]["invoice_date"] = entity_value
        elif entity_type in ["due_date", "payment_due_date"]:
            extracted_data["dates"]["due_date"] = entity_value
        elif entity_type in ["total_amount", "invoice_total_amount"]:
            extracted_data["totals"]["total_amount"] = entity_value
        elif entity_type in ["net_amount", "subtotal_amount"]:
            extracted_data["totals"]["net_amount"] = entity_value
        elif entity_type in ["total_tax_amount", "tax_amount"]:
            extracted_data["totals"]["tax_amount"] = entity_value
        elif entity_type in ["currency"]:
            extracted_data["totals"]["currency"] = entity_value
        elif entity_type in ["receiver_name", "bill_to_name"]:
            extracted_data["vendor_info"]["bill_to"] = entity_value
        elif entity_type in ["receiver_address", "bill_to_address"]:
            extracted_data["addresses"]["billing_address"] = entity_value

    def _extract_table_data(self, document, extracted_data: Dict[str, Any]) -> None:
        """Extract table data (line items) from document"""

        for page in document.pages:
            for table in page.tables:
                headers = []
                rows = []

                # Extract headers from header rows
                if table.header_rows:
                    for header_row in table.header_rows:
                        header_cells = []
                        for cell in header_row.cells:
                            cell_text = self._extract_cell_text(cell, document.text)
                            header_cells.append(cell_text.strip())
                        headers = header_cells
                        break  # Use first header row

                # Extract data rows
                for row in table.body_rows:
                    row_data = {}
                    for i, cell in enumerate(row.cells):
                        cell_text = self._extract_cell_text(cell, document.text)

                        # Map to header or use column index
                        if i < len(headers) and headers[i]:
                            row_data[headers[i]] = cell_text.strip()
                        else:
                            row_data[f"column_{i}"] = cell_text.strip()

                    # Only add non-empty rows
                    if any(value.strip() for value in row_data.values() if value):
                        rows.append(row_data)

                # Add line items if we found any
                if rows:
                    extracted_data["line_items"] = rows
                    break  # Use first table with data

    def _extract_cell_text(self, cell, document_text: str) -> str:
        """Extract text from table cell"""
        cell_text = ""
        if cell.layout.text_anchor:
            # Extract text from text segments
            for segment in cell.layout.text_anchor.text_segments:
                start_index = segment.start_index
                end_index = segment.end_index
                cell_text += document_text[start_index:end_index]
        return cell_text


# Global service instance
document_ai_service = DocumentAIService()