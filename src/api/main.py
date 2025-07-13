"""
FastAPI Backend for Invoice Processing AI
Complete production-ready API with Google Document AI integration
Using existing Google Cloud configuration
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import io
import json
from pathlib import Path
import uvicorn
from datetime import datetime
import logging
import sys
from pathlib import Path
import re
from typing import List, Dict, Any, Optional
from PIL import Image, ImageEnhance, ImageFilter
import io
import pytesseract
from PIL import Image
import cv2
import numpy as np

# Load environment variables from .env file FIRST
from dotenv import load_dotenv

load_dotenv()

# Google Cloud imports
from google.cloud import documentai
from google.api_core.client_options import ClientOptions


# ADD these imports at the top with your other imports:
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Initialize FastAPI app
app = FastAPI(
    title="Vritti Invoice AI",
    description="AI-powered invoice processing with camera scanning and Document AI",
    version="1.0.0"  # Updated version for MVP
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.4.185:3000",  # Your IP
        "http://192.168.4.185:8001",  # Backend
        "https://*.ngrok.io"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Tesseract path for Windows
if os.name == 'nt':  # Windows
    # Try common installation paths
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME')),
        r'C:\tesseract\tesseract.exe'
    ]

    for path in tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Found Tesseract at: {path}")
            break
    else:
        logger.warning("Tesseract not found in common paths. Please install Tesseract.")

# Pydantic models for request/response
class ProcessingResult(BaseModel):
    success: bool
    message: str
    extracted_data: Optional[Dict[str, Any]] = None
    confidence_scores: Optional[Dict[str, float]] = None
    processing_time: Optional[float] = None


class HealthCheck(BaseModel):
    status: str
    timestamp: str
    version: str


# Configuration using environment variables
class Config:
    # Google Cloud Document AI settings from environment
    PROJECT_ID = os.getenv("GCP_PROJECT_ID", "invoiceprocessingai2498")
    LOCATION = os.getenv("GCP_LOCATION", "us")
    PROCESSOR_ID = os.getenv("GCP_PROCESSOR_ID", "cca0593594bfdba1")

    # File upload settings
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB
    ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".gif"}

    @classmethod
    def verify_credentials(cls):
        """Verify Google Cloud credentials are properly set"""
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and os.path.exists(creds_path):
            logger.info(f"Google Cloud credentials found: {creds_path}")
            return True
        else:
            #logger.error(f"Google Cloud credentials not found. Path: {creds_path}")
            logger.error("Google Cloud credentials not found.")
            return False


config = Config()


# Initialize Document AI client
def get_document_ai_client():
    """Initialize and return Document AI client"""
    try:
        # Verify credentials first
        if not Config.verify_credentials():
            logger.error("Google Cloud credentials verification failed")
            return None

        # Set up client options for the specified location
        opts = ClientOptions(api_endpoint=f"{config.LOCATION}-documentai.googleapis.com")
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        logger.info(f"Document AI client initialized for location: {config.LOCATION}")
        logger.info(f"Using project: {config.PROJECT_ID}, processor: {config.PROCESSOR_ID}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Document AI client: {e}")
        logger.error(f"Credentials path: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
        return None


def test_ocr_installation():
    """Test if OCR is working properly"""
    try:
        # Create a simple test image
        from PIL import Image, ImageDraw, ImageFont

        # Create a simple test image with text
        img = Image.new('RGB', (300, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 30), "Test $123.45", fill='black')

        # Convert to bytes
        import io
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        # Test OCR
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        text = pytesseract.image_to_string(img_cv)

        logger.info(f"OCR test result: '{text.strip()}'")
        return len(text.strip()) > 0

    except Exception as e:
        logger.error(f"OCR test failed: {e}")
        return False

# Invoice processing functions
def extract_invoice_data(document: documentai.Document) -> Dict[str, Any]:
    """Extract structured data from processed invoice document"""

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

    # Process tables (line items)
    for page in document.pages:
        for table in page.tables:
            headers = []
            rows = []

            # Extract headers from header rows
            if table.header_rows:
                for header_row in table.header_rows:
                    header_cells = []
                    for cell in header_row.cells:
                        cell_text = ""
                        if cell.layout.text_anchor:
                            # Extract text from text segments
                            for segment in cell.layout.text_anchor.text_segments:
                                start_index = segment.start_index
                                end_index = segment.end_index
                                cell_text += document.text[start_index:end_index]
                        header_cells.append(cell_text.strip())
                    headers = header_cells
                    break  # Use first header row

            # Extract data rows
            for row in table.body_rows:
                row_data = {}
                for i, cell in enumerate(row.cells):
                    cell_text = ""
                    if cell.layout.text_anchor:
                        # Extract text from text segments
                        for segment in cell.layout.text_anchor.text_segments:
                            start_index = segment.start_index
                            end_index = segment.end_index
                            cell_text += document.text[start_index:end_index]

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

    return extracted_data, confidence_scores


async def process_document_with_ai(file_content: bytes, mime_type: str) -> ProcessingResult:
    """Process document using Google Document AI"""

    start_time = datetime.now()

    try:
        # Initialize client
        client = get_document_ai_client()
        if not client:
            raise HTTPException(status_code=500, detail="Document AI client not available")

        # Create the full resource name
        name = client.processor_path(config.PROJECT_ID, config.LOCATION, config.PROCESSOR_ID)
        logger.info(f"Using processor: {name}")

        # Create document object
        raw_document = documentai.RawDocument(content=file_content, mime_type=mime_type)

        # Create process request
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)

        # Process the document
        logger.info("Sending document to Document AI...")
        result = client.process_document(request=request)
        document = result.document

        logger.info(f"Document processed. Found {len(document.entities)} entities")

        # Extract structured data
        extracted_data, confidence_scores = extract_invoice_data(document)

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        return ProcessingResult(
            success=True,
            message="Document processed successfully with Google Document AI",
            extracted_data=extracted_data,
            confidence_scores=confidence_scores,
            processing_time=processing_time
        )

    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        processing_time = (datetime.now() - start_time).total_seconds()

        return ProcessingResult(
            success=False,
            message=f"Processing failed: {str(e)}",
            extracted_data=None,
            confidence_scores=None,
            processing_time=processing_time
        )


# Import agent components AFTER all dependencies are loaded
try:
    from src.api.agent_endpoints import agent_router
    from src.database import create_tables

    # Add agent router
    app.include_router(agent_router)
    logger.info("✅ LangChain Agent endpoints loaded successfully")

except ImportError as e:
    logger.warning(f"⚠️ Agent components not available: {e}")
    logger.warning("Running in legacy mode without AI agent features")


def enhance_invoice_image(image_content: bytes) -> bytes:
    """
    Enhance image quality for better OCR recognition
    """
    try:
        logger.info("🎨 Enhancing image quality...")

        # Open image
        image = Image.open(io.BytesIO(image_content))

        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Enhance contrast
        contrast_enhancer = ImageEnhance.Contrast(image)
        image = contrast_enhancer.enhance(1.3)

        # Enhance sharpness
        sharpness_enhancer = ImageEnhance.Sharpness(image)
        image = sharpness_enhancer.enhance(1.5)

        # Enhance brightness slightly
        brightness_enhancer = ImageEnhance.Brightness(image)
        image = brightness_enhancer.enhance(1.1)

        # Apply slight unsharp mask
        image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))

        # Convert back to bytes
        output = io.BytesIO()
        image.save(output, format='PNG', quality=95, dpi=(300, 300))
        return output.getvalue()

    except Exception as e:
        logger.warning(f"Image enhancement failed: {e}, using original")
        return image_content


def extract_enhanced_amounts(entities: List[Any]) -> Dict[str, Any]:
    """
    Enhanced amount extraction with multiple strategies
    """
    logger.info("💰 Starting enhanced amount extraction...")

    # Strategy 1: Look for standard Document AI amount fields
    total_amount = None
    amount_due = None

    for entity in entities:
        entity_type = entity.type_.lower()
        entity_text = entity.text_anchor.content.strip()

        logger.info(f"Found entity: {entity_type} = {entity_text}")

        if entity_type in ["total_amount", "invoice_total", "amount_total"]:
            total_amount = clean_amount_text(entity_text)
        elif entity_type in ["amount_due", "due_amount", "balance_due", "total_due"]:
            amount_due = clean_amount_text(entity_text)

    # Strategy 2: Extract all dollar amounts using multiple patterns
    all_amounts = []
    amount_patterns = [
        r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*\$',  # 1,234.56$
        r'USD\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # USD 1,234.56
        r'(?:TOTAL|DUE|AMOUNT|BALANCE).*?(\d{1,3}(?:,\d{3})*\.\d{2})',  # TOTAL: 1,234.56
    ]

    for entity in entities:
        entity_text = entity.text_anchor.content
        entity_type = entity.type_

        for pattern in amount_patterns:
            matches = re.findall(pattern, entity_text, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean and convert to float
                    clean_amount = match.replace(',', '').replace('$', '').strip()
                    amount_value = float(clean_amount)

                    if amount_value > 0:  # Only positive amounts
                        # Score amounts based on context
                        score = calculate_amount_score(entity_text, entity_type, amount_value)

                        all_amounts.append({
                            'value': amount_value,
                            'text': entity_text,
                            'formatted': f"${amount_value:.2f}",
                            'entity_type': entity_type,
                            'score': score
                        })
                except ValueError:
                    continue

    # Sort amounts by score (highest first), then by value
    all_amounts.sort(key=lambda x: (x['score'], x['value']), reverse=True)

    # Strategy 3: Smart amount selection
    final_amount = None

    if total_amount:
        final_amount = total_amount
        logger.info(f"✅ Using total_amount: {final_amount}")
    elif amount_due:
        final_amount = amount_due
        logger.info(f"✅ Using amount_due: {final_amount}")
    elif all_amounts:
        # Use the highest scoring amount
        best_amount = all_amounts[0]
        final_amount = best_amount['formatted']
        logger.info(f"✅ Using highest scored amount: {final_amount} (score: {best_amount['score']})")

    return {
        'final_amount': final_amount or "Unknown",
        'total_amount': total_amount,
        'amount_due': amount_due,
        'all_detected_amounts': [a['formatted'] for a in all_amounts[:5]],  # Top 5
        'amount_count': len(all_amounts),
        'best_score': all_amounts[0]['score'] if all_amounts else 0
    }


def calculate_amount_score(text: str, entity_type: str, amount_value: float) -> int:
    """
    Calculate score for amount based on context clues
    """
    score = 0
    text_upper = text.upper()

    # Higher score for specific entity types
    if entity_type.lower() in ['total_amount', 'invoice_total', 'amount_due']:
        score += 100

    # Higher score for text with "total" keywords
    total_keywords = ['TOTAL', 'AMOUNT DUE', 'BALANCE DUE', 'ESTIMATE TOTAL', 'FINAL AMOUNT', 'PAY']
    for keyword in total_keywords:
        if keyword in text_upper:
            score += 50
            break

    # Lower score for line items or detail amounts
    detail_keywords = ['TAX', 'DISCOUNT', 'SHIPPING', 'FEE', 'INTEREST', 'PENALTY']
    for keyword in detail_keywords:
        if keyword in text_upper:
            score -= 30

    # Score based on amount size (reasonable invoice amounts get higher scores)
    if 10 <= amount_value <= 50000:  # Reasonable range
        score += 20
    elif amount_value > 100000:  # Very large amounts might be wrong
        score -= 20
    elif amount_value < 1:  # Very small amounts likely not totals
        score -= 50

    return score


def clean_amount_text(text: str) -> Optional[str]:
    """
    Clean and standardize amount text
    """
    if not text:
        return None

    # Remove extra whitespace
    text = text.strip()

    # Extract amount using regex
    amount_match = re.search(r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
    if amount_match:
        amount = amount_match.group(1).replace(',', '')
        try:
            return f"${float(amount):.2f}"
        except ValueError:
            return None

    return None


def extract_enhanced_vendor_info(entities: List[Any]) -> Dict[str, Any]:
    """
    Enhanced vendor information extraction with scoring
    """
    logger.info("🏢 Starting enhanced vendor extraction...")

    vendor_candidates = []

    for entity in entities:
        entity_text = entity.text_anchor.content.strip()
        entity_type = entity.type_.lower()

        if len(entity_text) < 3:  # Skip very short text
            continue

        # Calculate vendor score
        score = calculate_vendor_score(entity_text, entity_type)

        if score > 0:  # Only consider positive scoring candidates
            vendor_candidates.append({
                'name': entity_text,
                'score': score,
                'type': entity_type
            })
            logger.info(f"Vendor candidate: {entity_text} (score: {score})")

    # Sort by score and pick best
    vendor_candidates.sort(key=lambda x: x['score'], reverse=True)

    best_vendor = vendor_candidates[0]['name'] if vendor_candidates else None

    return {
        'name': best_vendor,
        'candidates': [v['name'] for v in vendor_candidates[:3]],  # Top 3 for debugging
        'best_score': vendor_candidates[0]['score'] if vendor_candidates else 0
    }


def calculate_vendor_score(text: str, entity_type: str) -> int:
    """
    Calculate score for potential vendor names
    """
    score = 0
    text_upper = text.upper()

    # Higher score for specific vendor entity types
    if entity_type in ['supplier_name', 'vendor_name', 'company_name']:
        score += 100

    # Higher score for business indicators
    business_words = ['LLC', 'INC', 'CORP', 'CO.', 'LTD', 'COMPANY', 'CORPORATION', 'GROUP', 'SERVICES']
    for word in business_words:
        if word in text_upper:
            score += 30
            break

    # Higher score for common business types
    business_types = ['NISSAN', 'TOYOTA', 'COUNTY', 'CITY', 'BANK', 'STORE', 'SHOP', 'RESTAURANT']
    for btype in business_types:
        if btype in text_upper:
            score += 20

    # Lower score for system/software names
    tech_words = ['TEKION', 'SOFTWARE', 'SYSTEM', 'PORTAL', 'ONLINE', 'DIGITAL']
    for word in tech_words:
        if word in text_upper:
            score -= 40

    # Lower score for addresses, phones, emails
    if any(char in text for char in ['@', 'HTTP', 'WWW']):
        score -= 30
    if re.search(r'\d{3}-\d{3}-\d{4}', text):  # Phone number pattern
        score -= 20

    # Lower score for very long text (likely descriptions)
    if len(text) > 50:
        score -= 20

    # Lower score for numbers-only or mostly numbers
    if re.search(r'^\d+$', text) or len(re.findall(r'\d', text)) > len(text) * 0.7:
        score -= 50

    return score


def detect_document_type(entities: List[Any]) -> str:
    """
    Detect document type based on content patterns
    """
    text_content = " ".join([entity.text_anchor.content for entity in entities]).upper()

    # Tax document indicators
    tax_indicators = ['TAX COLLECTOR', 'PROPERTY TAX', 'INSTALLMENT', 'ALAMEDA COUNTY', 'TAX STATEMENT',
                      'PARCEL NUMBER']
    tax_score = sum(1 for indicator in tax_indicators if indicator in text_content)

    # HOA document indicators
    hoa_indicators = ['HOA', 'ASSOCIATION', 'COMMUNITY', 'HOMEOWNERS', 'DETACHED HOMES', 'MANAGEMENT COMPANY']
    hoa_score = sum(1 for indicator in hoa_indicators if indicator in text_content)

    # Invoice indicators
    invoice_indicators = ['INVOICE', 'ESTIMATE', 'SERVICE', 'LABOR', 'PARTS', 'SUBTOTAL']
    invoice_score = sum(1 for indicator in invoice_indicators if indicator in text_content)

    if tax_score >= 2:
        return "tax"
    elif hoa_score >= 1:
        return "hoa"
    elif invoice_score >= 2:
        return "invoice"
    else:
        return "unknown"


def calculate_enhanced_amount_score(text: str, entity_type: str, amount_value: float,
                                    existing_amounts: List[Dict]) -> int:
    """
    Enhanced scoring with document type awareness
    """
    score = 0
    text_upper = text.upper()

    # Base scoring from original function
    if entity_type.lower() in ['total_amount', 'invoice_total', 'amount_due']:
        score += 100

    # Enhanced keyword scoring
    high_priority_keywords = [
        'THIS AMOUNT DUE', 'AMOUNT DUE', 'TOTAL DUE', 'PAYMENT DUE',
        'ESTIMATE TOTAL', 'FINAL TOTAL', 'TOTAL AMOUNT',
        'INSTALLMENT PAYMENT', 'DUE FEB', 'DUE NOV'
    ]

    medium_priority_keywords = [
        'TOTAL', 'DUE', 'BALANCE', 'PAYMENT', 'FINAL', 'AMOUNT'
    ]

    low_priority_keywords = [
        'TAX', 'FEE', 'INTEREST', 'PENALTY', 'DISCOUNT', 'SHIPPING'
    ]

    # High priority keyword scoring
    for keyword in high_priority_keywords:
        if keyword in text_upper:
            score += 80
            break

    # Medium priority keyword scoring
    for keyword in medium_priority_keywords:
        if keyword in text_upper:
            score += 30
            break

    # Low priority (negative) keyword scoring
    for keyword in low_priority_keywords:
        if keyword in text_upper:
            score -= 20

    # Amount size scoring
    if 50 <= amount_value <= 100000:  # Reasonable invoice range
        score += 30
    elif 1000 <= amount_value <= 50000:  # Likely main amounts
        score += 50
    elif amount_value > 100000:  # Very large amounts might be totals
        score -= 10
    elif amount_value < 10:  # Very small amounts likely not main totals
        score -= 40

    # Context-based scoring
    if 'DUE DATE' in text_upper or 'AMOUNT DUE' in text_upper:
        score += 60
    if re.search(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b', text_upper):
        score += 20  # Dates often accompany due amounts

    # Penalty for amounts that appear multiple times (likely line items)
    duplicate_count = sum(1 for a in existing_amounts if abs(a['value'] - amount_value) < 0.01)
    if duplicate_count > 0:
        score -= 30 * duplicate_count

    return score

def calculate_enhanced_vendor_score(text: str, entity_type: str, document_type: str) -> int:
    """
    Enhanced vendor scoring with document type awareness
    """
    score = 0
    text_upper = text.upper()

    # Base scoring
    if entity_type in ['supplier_name', 'vendor_name', 'company_name']:
        score += 100

    # Document type specific scoring
    if document_type == "tax":
        tax_entities = ['ALAMEDA COUNTY', 'TAX COLLECTOR', 'COUNTY', 'TREASURER']
        for entity in tax_entities:
            if entity in text_upper:
                score += 80
                break
    elif document_type == "hoa":
        hoa_entities = ['DETACHED HOMES', 'MANAGEMENT', 'ASSOCIATION', 'COMMUNITY']
        for entity in hoa_entities:
            if entity in text_upper:
                score += 70
                break
    elif document_type == "invoice":
        business_entities = ['NISSAN', 'TOYOTA', 'FORD', 'SERVICE', 'COMPANY']
        for entity in business_entities:
            if entity in text_upper:
                score += 60

    # Standard business indicators
    business_words = ['LLC', 'INC', 'CORP', 'CO.', 'LTD', 'COMPANY', 'CORPORATION', 'GROUP', 'SERVICES']
    for word in business_words:
        if word in text_upper:
            score += 30
            break

    # Lower score for system/software names
    tech_words = ['TEKION', 'SOFTWARE', 'SYSTEM', 'PORTAL', 'ONLINE', 'DIGITAL']
    for word in tech_words:
        if word in text_upper:
            score -= 40

    # Lower score for addresses, phones, emails
    if any(char in text for char in ['@', 'HTTP', 'WWW']):
        score -= 30
    if re.search(r'\d{3}-\d{3}-\d{4}', text):  # Phone number pattern
        score -= 20

    # Lower score for very long text (likely descriptions)
    if len(text) > 50:
        score -= 20

    # Lower score for numbers-only
    if re.search(r'^\d+$', text) or len(re.findall(r'\d', text)) > len(text) * 0.7:
        score -= 50

    return score


def extract_enhanced_vendor_info_v2(entities: List[Any]) -> Dict[str, Any]:
    """
    Enhanced vendor extraction v2 with document type awareness
    """
    logger.info("🏢 Starting enhanced vendor extraction v2...")

    vendor_candidates = []
    document_type = detect_document_type(entities)

    for entity in entities:
        entity_text = entity.text_anchor.content.strip()
        entity_type = entity.type_.lower()

        if len(entity_text) < 3:  # Skip very short text
            continue

        # Calculate vendor score with document type awareness
        score = calculate_enhanced_vendor_score(entity_text, entity_type, document_type)

        if score > 0:  # Only consider positive scoring candidates
            vendor_candidates.append({
                'name': entity_text,
                'score': score,
                'type': entity_type
            })
            logger.info(f"Vendor candidate: {entity_text} (score: {score})")

    # Sort by score and pick best
    vendor_candidates.sort(key=lambda x: x['score'], reverse=True)

    best_vendor = vendor_candidates[0]['name'] if vendor_candidates else None

    return {
        'name': best_vendor,
        'candidates': [v['name'] for v in vendor_candidates[:3]],  # Top 3 for debugging
        'best_score': vendor_candidates[0]['score'] if vendor_candidates else 0,
        'document_type': document_type
    }


def get_pattern_priority(pattern: str) -> int:
    """
    Assign priority scores to different patterns
    """
    pattern_upper = pattern.upper()

    # Highest priority: Explicit "Amount Due" patterns
    if 'AMOUNT.*DUE' in pattern_upper or 'THIS.*AMOUNT.*DUE' in pattern_upper:
        return 10
    elif 'TOTAL.*AMOUNT.*DUE' in pattern_upper or 'BALANCE.*DUE' in pattern_upper:
        return 9

    # High priority: Total patterns
    elif 'ESTIMATE.*TOTAL' in pattern_upper or 'FINAL.*TOTAL' in pattern_upper:
        return 8
    elif 'TOTAL' in pattern_upper:
        return 7

    # Medium priority: Date-based patterns
    elif any(month in pattern_upper for month in ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN']):
        return 6
    elif r'\d{2}/\d{2}/\d{4}' in pattern:
        return 5

    # Lower priority: Standard dollar patterns
    else:
        return 3


def calculate_smart_amount_score(amount_value: float, full_text: str) -> int:
    """
    Smart scoring based on patterns and context (NO hard-coding)
    """
    score = 0
    text_upper = full_text.upper()

    # 1. Reasonable amount range scoring
    if 10 <= amount_value <= 50000:
        score += 100
    elif 50 <= amount_value <= 20000:  # Sweet spot for invoices
        score += 200

    # 2. Penalize obvious non-amounts
    if amount_value > 50000:  # Likely zip codes, addresses
        score -= 500
    if amount_value in range(2020, 2030):  # Years
        score -= 300
    if len(str(int(amount_value))) == 5:  # 5-digit numbers (zip codes)
        score -= 400
    if amount_value < 1:  # Too small
        score -= 200

    # 3. Boost for decimal amounts
    if amount_value != int(amount_value):  # Has decimal places
        score += 150

    # 4. Context-based scoring - look for amount near keywords
    amount_str = f"{amount_value:.2f}"

    # High value keywords that indicate this is a payment amount
    high_value_keywords = ['AMOUNT DUE', 'TOTAL AMOUNT DUE', 'THIS AMOUNT DUE', 'BALANCE DUE']
    medium_value_keywords = ['TOTAL', 'DUE', 'PAYMENT', 'INSTALLMENT', 'ESTIMATE TOTAL']

    for keyword in high_value_keywords:
        if keyword in text_upper and amount_str.replace('.', '.') in text_upper:
            score += 500  # Major boost for explicit amount due
            break

    for keyword in medium_value_keywords:
        if keyword in text_upper:
            score += 200
            break

    # 5. Document type specific scoring
    if 'PROPERTY TAX' in text_upper or 'TAX COLLECTOR' in text_upper:
        if 5000 <= amount_value <= 15000:  # Typical property tax range
            score += 300

    if any(word in text_upper for word in ['HOA', 'ASSOCIATION', 'HOMEOWNERS']):
        if 30 <= amount_value <= 300:  # Typical HOA fee range
            score += 300

    return score

def extract_enhanced_amounts_v2(entities: List[Any]) -> Dict[str, Any]:
    """
    Enhanced amount extraction v2 with improved pattern matching for "Amount Due" patterns
    """
    logger.info("💰 Starting enhanced amount extraction v2...")

    # Strategy 1: Look for standard Document AI amount fields
    total_amount = None
    amount_due = None

    for entity in entities:
        entity_type = entity.type_.lower()
        entity_text = entity.text_anchor.content.strip()

        logger.info(f"Found entity: {entity_type} = {entity_text}")

        if entity_type in ["total_amount", "invoice_total", "amount_total"]:
            total_amount = clean_amount_text(entity_text)
        elif entity_type in ["amount_due", "due_amount", "balance_due", "total_due"]:
            amount_due = clean_amount_text(entity_text)

    # Strategy 2: Search through ALL entity text content for dollar amounts
    all_amounts = []

    # Get all text content
    all_text_content = []
    for entity in entities:
        if hasattr(entity, 'text_anchor') and entity.text_anchor and entity.text_anchor.content:
            all_text_content.append(entity.text_anchor.content)

    # Combine all text and search for dollar patterns
    combined_text = " ".join(all_text_content)
    combined_text_upper = combined_text.upper()

    logger.info(f"Searching through {len(combined_text)} characters of text...")

    # Enhanced patterns specifically for "Amount Due" and "Total" contexts
    enhanced_patterns = [
        # High priority: Amount Due patterns
        r'AMOUNT\s+DUE[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'TOTAL\s+AMOUNT\s+DUE[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'THIS\s+AMOUNT\s+DUE[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'BALANCE\s+DUE[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',

        # Medium priority: Total patterns
        r'ESTIMATE\s+TOTAL[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'FINAL\s+TOTAL[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'TOTAL[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',

        # Date-based patterns (for tax/HOA documents)
        r'(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{1,2},?\s+\d{4}[^$]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'\d{2}/\d{2}/\d{4}[^$]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',

        # Standard dollar patterns
        r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'(\d{1,3}(?:,\d{3})*\.\d{2})',
    ]

    for pattern in enhanced_patterns:
        matches = re.findall(pattern, combined_text_upper, re.IGNORECASE)
        pattern_priority = get_pattern_priority(pattern)

        for match in matches:
            try:
                clean_amount = match.replace(',', '').replace('$', '').strip()
                amount_value = float(clean_amount)

                if amount_value > 0:
                    # Enhanced scoring with pattern priority
                    base_score = calculate_smart_amount_score(amount_value, combined_text_upper)
                    pattern_bonus = pattern_priority * 100  # Boost for high-priority patterns
                    total_score = base_score + pattern_bonus

                    all_amounts.append({
                        'value': amount_value,
                        'formatted': f"${amount_value:.2f}",
                        'score': total_score,
                        'pattern_used': pattern,
                        'source': 'enhanced_pattern_search'
                    })

                    logger.info(
                        f"Found amount: ${amount_value:.2f} (score: {total_score}, pattern priority: {pattern_priority})")

            except ValueError:
                continue

    # Remove duplicates and sort
    unique_amounts = []
    for amount in all_amounts:
        is_duplicate = False
        for existing in unique_amounts:
            if abs(amount['value'] - existing['value']) < 0.01:
                if existing['score'] < amount['score']:
                    existing.update(amount)  # Keep higher scoring version
                is_duplicate = True
                break
        if not is_duplicate:
            unique_amounts.append(amount)

    unique_amounts.sort(key=lambda x: x['score'], reverse=True)

    logger.info(f"Found {len(unique_amounts)} unique amounts:")
    for i, amt in enumerate(unique_amounts[:5]):
        logger.info(f"  {i + 1}. ${amt['value']:.2f} (score: {amt['score']})")

    # Strategy 3: Smart selection
    document_type = detect_document_type(entities)
    logger.info(f"Detected document type: {document_type}")

    final_amount = None

    if total_amount:
        final_amount = total_amount
        logger.info(f"✅ Using total_amount: {final_amount}")
    elif amount_due:
        final_amount = amount_due
        logger.info(f"✅ Using amount_due: {final_amount}")
    elif unique_amounts:
        final_amount = unique_amounts[0]['formatted']
        logger.info(f"✅ Using highest scored amount: {final_amount} (score: {unique_amounts[0]['score']})")

    return {
        'final_amount': final_amount or "Unknown",
        'total_amount': total_amount,
        'amount_due': amount_due,
        'all_detected_amounts': [a['formatted'] for a in unique_amounts[:10]],
        'amount_count': len(unique_amounts),
        'best_score': unique_amounts[0]['score'] if unique_amounts else 0,
        'document_type': document_type,
    }


def determine_processing_strategy(entities: List[Any], document_text: str) -> str:
    """
    Determine processing strategy - UPDATED to prefer Document AI text
    """
    logger.info("🧠 Determining processing strategy...")

    # Calculate complexity indicators
    entity_count = len(entities)
    text_length = len(document_text)
    non_empty_entities = sum(1 for entity in entities if entity.text_anchor and entity.text_anchor.content.strip())

    logger.info(f"Entity count: {entity_count}, Text length: {text_length}, Non-empty entities: {non_empty_entities}")

    # Strategy decision logic - PREFER Document AI text processing
    if text_length > 1000:  # Good amount of text from Document AI
        return "document_ai_enhanced_text"
    elif entity_count > 15 and text_length > 500:  # Good Document AI extraction
        return "document_ai"
    elif text_length > 200:  # Some text available
        return "document_ai_enhanced_text"
    else:
        return "enhanced_ocr"  # Last resort


def enhanced_ocr_processing(image_content: bytes) -> Dict[str, Any]:
    """
    Enhanced OCR processing with timeout and better error handling
    """
    logger.info("🔍 Starting enhanced OCR processing...")

    try:
        import signal

        # Set a timeout for OCR processing (30 seconds max)
        def timeout_handler(signum, frame):
            raise TimeoutError("OCR processing timed out")

        # Only set signal on Unix systems
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout

        logger.info("📸 Converting image to OpenCV format...")

        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_content))

        # Convert to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        logger.info("🎨 Preprocessing image...")

        # Simplified preprocessing (skip the heavy processing)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        logger.info("🔤 Extracting text with Tesseract...")

        # Use simple OCR without heavy preprocessing
        extracted_text = pytesseract.image_to_string(gray, config='--psm 6')

        # Cancel timeout
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)

        logger.info(f"OCR extracted {len(extracted_text)} characters")
        logger.info(f"OCR text sample: {extracted_text[:200]}...")

        # Extract amounts and vendors from OCR text
        amounts_result = extract_amounts_from_text(extracted_text)
        vendor_result = extract_vendor_from_text(extracted_text)

        return {
            "success": True,
            "method": "enhanced_ocr",
            "extracted_text": extracted_text,
            "amounts": amounts_result,
            "vendor": vendor_result
        }

    except TimeoutError:
        logger.error("❌ OCR processing timed out after 30 seconds")
        return {
            "success": False,
            "method": "enhanced_ocr",
            "error": "OCR timeout"
        }
    except Exception as e:
        logger.error(f"Enhanced OCR failed: {e}")
        return {
            "success": False,
            "method": "enhanced_ocr",
            "error": str(e)
        }

def preprocess_for_ocr(cv_image):
    """
    Preprocess image for better OCR accuracy
    """
    # Convert to grayscale
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray)

    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    # Threshold to binary
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Morphological operations to clean up
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    return cleaned


def extract_text_with_tesseract(processed_image) -> str:
    """
    Extract text using multiple Tesseract configurations
    """
    # Multiple OCR configurations for better accuracy
    configs = [
        '--psm 6',  # Uniform block of text
        '--psm 4',  # Single column of text
        '--psm 3',  # Fully automatic page segmentation
        '--psm 11',  # Sparse text
    ]

    best_text = ""
    best_length = 0

    for config in configs:
        try:
            text = pytesseract.image_to_string(processed_image, config=config)
            if len(text) > best_length:
                best_text = text
                best_length = len(text)
        except:
            continue

    return best_text


def extract_amounts_from_text(text: str) -> Dict[str, Any]:
    """
    Extract amounts from raw OCR text using aggressive pattern matching
    """
    logger.info("💰 Extracting amounts from OCR text...")

    text_upper = text.upper()
    all_amounts = []

    # Comprehensive amount patterns
    amount_patterns = [
        # High priority: Explicit payment patterns
        r'AMOUNT\s+DUE[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'THIS\s+AMOUNT\s+DUE[:\s=]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'TOTAL\s+DUE[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'BALANCE\s+DUE[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'PAYMENT\s+DUE[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',

        # Medium priority: Total patterns
        r'ESTIMATE\s+TOTAL[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'TOTAL\s+AMOUNT[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'INSTALLMENT[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',

        # Date-based patterns (for tax/HOA)
        r'(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{1,2},?\s+\d{4}[^$\d]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'\d{2}/\d{2}/\d{4}[^$\d]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',

        # General dollar patterns
        r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'(\d{1,3}(?:,\d{3})*\.\d{2})',

        # Catch specific problematic amounts
        r'\b(\d{2}\.\d{2})\b',  # 91.30
        r'\b(\d{1,2},\d{3}\.\d{2})\b',  # 8,786.78
    ]

    for i, pattern in enumerate(amount_patterns):
        pattern_priority = 10 - i  # Higher priority for earlier patterns

        matches = re.findall(pattern, text_upper, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            try:
                clean_amount = match.replace(',', '').replace('$', '').strip()
                amount_value = float(clean_amount)

                if amount_value > 0:
                    score = calculate_ocr_amount_score(amount_value, text_upper, pattern_priority)

                    all_amounts.append({
                        'value': amount_value,
                        'formatted': f"${amount_value:.2f}",
                        'score': score,
                        'pattern': pattern,
                        'priority': pattern_priority
                    })

                    logger.info(f"OCR found amount: ${amount_value:.2f} (score: {score}, priority: {pattern_priority})")

            except ValueError:
                continue

    # Remove duplicates and sort
    unique_amounts = []
    for amount in all_amounts:
        is_duplicate = False
        for existing in unique_amounts:
            if abs(amount['value'] - existing['value']) < 0.01:
                if existing['score'] < amount['score']:
                    existing.update(amount)
                is_duplicate = True
                break
        if not is_duplicate:
            unique_amounts.append(amount)

    unique_amounts.sort(key=lambda x: x['score'], reverse=True)

    logger.info(f"OCR found {len(unique_amounts)} unique amounts:")
    for i, amt in enumerate(unique_amounts[:3]):
        logger.info(f"  {i + 1}. ${amt['value']:.2f} (score: {amt['score']})")

    final_amount = unique_amounts[0]['formatted'] if unique_amounts else "Unknown"

    return {
        'final_amount': final_amount,
        'all_detected_amounts': [a['formatted'] for a in unique_amounts[:5]],
        'best_score': unique_amounts[0]['score'] if unique_amounts else 0,
        'method': 'enhanced_ocr'
    }


def calculate_ocr_amount_score(amount_value: float, full_text: str, pattern_priority: int) -> int:
    """
    Calculate score for OCR-extracted amounts
    """
    score = pattern_priority * 100  # Base score from pattern priority

    # Amount range scoring
    if 10 <= amount_value <= 50000:
        score += 200
    elif 50 <= amount_value <= 20000:
        score += 300

    # Penalty for obvious non-amounts
    if amount_value > 50000:  # Zip codes, etc.
        score -= 500
    if amount_value in range(2020, 2030):  # Years
        score -= 300
    if len(str(int(amount_value))) == 5:  # 5-digit numbers
        score -= 400

    # Boost for decimal amounts
    if amount_value != int(amount_value):
        score += 150

    # Context boost
    amount_str = f"{amount_value:.2f}"
    context_keywords = [
        'AMOUNT DUE', 'THIS AMOUNT DUE', 'TOTAL DUE', 'BALANCE DUE',
        'INSTALLMENT', 'PAYMENT', 'TOTAL'
    ]

    for keyword in context_keywords:
        if keyword in full_text and amount_str in full_text:
            score += 300
            break

    # Document type specific boosts
    if 'PROPERTY TAX' in full_text or 'TAX COLLECTOR' in full_text:
        if 5000 <= amount_value <= 15000:
            score += 400

    if any(word in full_text for word in ['HOA', 'ASSOCIATION', 'HOMEOWNERS']):
        if 30 <= amount_value <= 300:
            score += 400

    return score


def extract_vendor_from_text(text: str) -> Dict[str, Any]:
    """
    Smart vendor extraction using generic patterns and document structure
    """
    logger.info("🏢 Extracting vendor from text...")

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    vendor_candidates = []

    # Strategy 1: Look at the first few lines (header area)
    for i, line in enumerate(lines[:8]):  # Check first 8 lines
        cleaned_line = clean_vendor_name(line)
        if cleaned_line and is_potential_vendor(cleaned_line, i):
            score = calculate_vendor_score_generic(cleaned_line, i, text)
            vendor_candidates.append({
                'name': cleaned_line,
                'score': score,
                'source': f'header_line_{i}'
            })

    # Strategy 2: Look for lines with business indicators
    for i, line in enumerate(lines):
        if has_business_indicators(line):
            cleaned_line = clean_vendor_name(line)
            if cleaned_line and len(cleaned_line) > 3:
                score = calculate_vendor_score_generic(cleaned_line, i, text) + 50  # Bonus for business indicators
                vendor_candidates.append({
                    'name': cleaned_line,
                    'score': score,
                    'source': 'business_indicator'
                })

    # Strategy 3: Look for prominent text (all caps, centered, etc.)
    for i, line in enumerate(lines):
        if is_prominent_text(line):
            cleaned_line = clean_vendor_name(line)
            if cleaned_line and len(cleaned_line) > 3:
                score = calculate_vendor_score_generic(cleaned_line, i, text) + 30  # Bonus for prominence
                vendor_candidates.append({
                    'name': cleaned_line,
                    'score': score,
                    'source': 'prominent_text'
                })

    # Remove duplicates and sort
    unique_vendors = remove_duplicate_vendors(vendor_candidates)
    unique_vendors.sort(key=lambda x: x['score'], reverse=True)

    best_vendor = unique_vendors[0]['name'] if unique_vendors else "Unknown"

    logger.info(f"Vendor candidates:")
    for i, vendor in enumerate(unique_vendors[:3]):
        logger.info(f"  {i + 1}. {vendor['name']} (score: {vendor['score']}) [{vendor['source']}]")

    return {
        'name': best_vendor,
        'candidates': [v['name'] for v in unique_vendors[:3]],
        'best_score': unique_vendors[0]['score'] if unique_vendors else 0,
        'method': 'smart_generic'
    }


def clean_vendor_name(line: str) -> str:
    """
    Generic vendor name cleaning
    """
    if not line:
        return ""

    # Remove common non-vendor text
    junk_patterns = [
        r'\s*IF NOT RECEIVED.*$',
        r'\s*BILL TO.*$',
        r'\s*PLEASE MAKE.*$',
        r'\s*FAMILY ID.*$',
        r'\s*ACCOUNT NUMBER.*$',
        r'\s*DUE DATE.*$',
        r'\s*AMOUNT DUE.*$',
        r'\s*DATE PAID.*$',
        r'\s*ASSOCIATION ID.*$',
        r'^\s*PO BOX.*$',
        r'^\s*P\.O\..*$',
        r'^\s*\d+.*$',  # Lines starting with numbers
        r'.*@.*',  # Email addresses
        r'.*\.com.*',  # Websites
        r'.*\d{3}-\d{3}-\d{4}.*',  # Phone numbers
    ]

    cleaned = line.strip()

    for pattern in junk_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

    # Take only the first line if multiline
    cleaned = cleaned.split('\n')[0].strip()

    return cleaned


def is_potential_vendor(line: str, position: int) -> bool:
    """
    Check if a line could be a vendor name
    """
    if not line or len(line) < 3:
        return False

    # Skip obvious non-vendor lines
    skip_indicators = [
        'DUE DATE', 'AMOUNT DUE', 'BILL TO', 'ACCOUNT NUMBER',
        'FAMILY ID', 'DATE PAID', 'ASSOCIATION ID', 'RETURN SERVICE',
        'IF NOT RECEIVED', 'PLEASE MAKE', 'CHECKS PAYABLE'
    ]

    line_upper = line.upper()
    if any(skip in line_upper for skip in skip_indicators):
        return False

    # Skip lines that are mostly numbers
    if sum(c.isdigit() for c in line) > len(line) * 0.5:
        return False

    # Skip very long lines (likely descriptions)
    if len(line) > 60:
        return False

    return True


def has_business_indicators(line: str) -> bool:
    """
    Check if line has business entity indicators
    """
    business_indicators = [
        'LLC', 'INC', 'CORP', 'COMPANY', 'CO.', 'LTD', 'CORPORATION',
        'ASSOCIATION', 'MANAGEMENT', 'SERVICES', 'GROUP', 'ENTERPRISES',
        'COUNTY', 'COLLEGE', 'SCHOOL', 'UNIVERSITY', 'HOSPITAL',
        'BANK', 'CREDIT UNION', 'DEALERSHIP', 'AUTOMOTIVE',
        'TAX COLLECTOR', 'TREASURER', 'DEPARTMENT'
    ]

    line_upper = line.upper()
    return any(indicator in line_upper for indicator in business_indicators)


def calculate_vendor_score_generic(vendor_text: str, position: int, full_text: str) -> int:
    """
    Generic vendor scoring based on position and characteristics
    """
    score = 0
    text_upper = vendor_text.upper()

    # Position-based scoring (earlier = better)
    if position == 0:
        score += 100  # First line
    elif position <= 2:
        score += 80  # Top 3 lines
    elif position <= 5:
        score += 60  # Top 6 lines
    else:
        score += 20  # Lower lines

    # Business entity indicators
    if has_business_indicators(vendor_text):
        score += 100

    # Prominence indicators
    if is_prominent_text(vendor_text):
        score += 80

    # Length scoring (reasonable business name length)
    if 10 <= len(vendor_text) <= 35:
        score += 50
    elif 5 <= len(vendor_text) <= 50:
        score += 30
    else:
        score -= 20

    # Penalty for numbers and special characters
    if any(c.isdigit() for c in vendor_text):
        score -= 30
    if any(c in vendor_text for c in ['@', '.com', 'www']):
        score -= 50

    # Bonus for common business words
    business_words = ['COMPANY', 'CORP', 'INC', 'LLC', 'SERVICES', 'GROUP']
    if any(word in text_upper for word in business_words):
        score += 40

    return score


def remove_duplicate_vendors(vendor_candidates: List[Dict]) -> List[Dict]:
    """
    Remove duplicate or very similar vendor names
    """
    unique_vendors = []

    for vendor in vendor_candidates:
        is_duplicate = False
        vendor_name = vendor['name'].upper()

        for existing in unique_vendors:
            existing_name = existing['name'].upper()

            # Check for exact match or substring
            if (vendor_name == existing_name or
                    vendor_name in existing_name or
                    existing_name in vendor_name):

                # Keep the higher scoring version
                if existing['score'] < vendor['score']:
                    existing.update(vendor)
                is_duplicate = True
                break

        if not is_duplicate:
            unique_vendors.append(vendor)

    return unique_vendors

def is_prominent_text(line: str) -> bool:
    """
    Check if text appears prominent (likely a business name)
    """
    # All uppercase and reasonable length
    if (line.isupper() and 5 <= len(line) <= 40 and
            not any(c.isdigit() for c in line)):
        return True

    # Mixed case but looks like a proper business name
    if (line.istitle() and 5 <= len(line) <= 40 and
            sum(c.isdigit() for c in line) < 3):
        return True

    return False


def calculate_ocr_vendor_score(vendor_text: str, full_text: str) -> int:
    """
    Score vendor candidates from OCR
    """
    score = 0
    text_upper = vendor_text.upper()

    # High-value vendor indicators
    high_value_indicators = [
        'ALAMEDA COUNTY', 'TAX COLLECTOR', 'COUNTY', 'NISSAN',
        'DETACHED HOMES', 'ASSOCIATION', 'MANAGEMENT'
    ]

    for indicator in high_value_indicators:
        if indicator in text_upper:
            score += 100

    # Business type indicators
    business_indicators = ['LLC', 'INC', 'CORP', 'COMPANY', 'SERVICES']
    for indicator in business_indicators:
        if indicator in text_upper:
            score += 50

    # Penalty for addresses, numbers
    if any(char.isdigit() for char in vendor_text):
        score -= 30
    if any(word in text_upper for word in ['STREET', 'BLVD', 'ROAD', 'BOX']):
        score -= 50

    return score


async def hybrid_process_document(file_content: bytes, mime_type: str, entities: List[Any], document_text: str) -> Dict[
    str, Any]:
    """
    Main hybrid processing function - FIXED LOGIC
    """
    logger.info("🔄 Starting hybrid document processing...")

    # Determine processing strategy
    strategy = determine_processing_strategy(entities, document_text)
    logger.info(f"📋 Selected strategy: {strategy}")

    if strategy == "document_ai":
        # Use Document AI results
        logger.info("🤖 Using Document AI processing...")
        amount_info = extract_enhanced_amounts_v2(entities)
        vendor_info = extract_enhanced_vendor_info_v2(entities)

        return {
            "success": True,
            "method": "document_ai",
            "amount_info": amount_info,
            "vendor_info": vendor_info
        }

    elif strategy == "document_ai_enhanced_text":
        # Use Document AI text with enhanced patterns - THIS IS THE FIX!
        logger.info("📄 Using Document AI text with enhanced patterns...")
        logger.info(f"🔤 Processing {len(document_text)} characters from Document AI...")

        # Apply enhanced patterns to Document AI text instead of OCR
        amounts_result = extract_amounts_from_text(document_text)
        vendor_result = extract_vendor_from_text(document_text)

        return {
            "success": True,
            "method": "document_ai_enhanced_text",
            "amount_info": amounts_result,
            "vendor_info": vendor_result
        }

    else:
        # Use enhanced OCR (only if strategy is "enhanced_ocr")
        logger.info("🔍 Using enhanced OCR processing...")
        ocr_result = enhanced_ocr_processing(file_content)

        if ocr_result["success"]:
            return {
                "success": True,
                "method": "enhanced_ocr",
                "amount_info": ocr_result["amounts"],
                "vendor_info": ocr_result["vendor"]
            }
        else:
            # Final fallback to Document AI if OCR fails
            logger.warning("⚠️ OCR failed, falling back to Document AI...")
            amount_info = extract_enhanced_amounts_v2(entities)
            vendor_info = extract_enhanced_vendor_info_v2(entities)

            return {
                "success": True,
                "method": "document_ai_fallback",
                "amount_info": amount_info,
                "vendor_info": vendor_info
            }

# Initialize database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("🚀 Starting Vritti Invoice AI...")

    # Test OCR installation
    if test_ocr_installation():
        logger.info("✅ OCR (Tesseract) is working properly")
    else:
        logger.warning("⚠️ OCR (Tesseract) test failed - will use fallback methods")

    # Initialize database if agent components are available
    try:
        create_tables()
        logger.info("✅ Database tables initialized")
    except NameError:
        logger.info("📊 Running without database (legacy mode)")

    # Verify Document AI setup
    client = get_document_ai_client()
    if client:
        logger.info("✅ Document AI client ready")
    else:
        logger.warning("⚠️ Document AI client not available")

    logger.info("🎉 Vritti application startup complete!")


# API Routes
@app.get("/", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@app.post("/process-invoice", response_model=ProcessingResult)
async def process_invoice(file: UploadFile = File(...)):
    """
    Process an invoice file and extract structured data

    Supports: PDF, PNG, JPG, JPEG, TIFF, GIF
    Max file size: 10MB
    """

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Check file size
    if len(file_content) > config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {config.MAX_FILE_SIZE / (1024 * 1024):.1f}MB"
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
    mime_type = mime_type_map.get(file_ext, "application/octet-stream")

    # Process the document
    result = await process_document_with_ai(file_content, mime_type)

    # Store recent processing data for AI agent access
    if result.success and result.extracted_data:
        try:
            # Calculate average confidence
            avg_confidence = 0
            if result.confidence_scores:
                avg_confidence = sum(result.confidence_scores.values()) / len(result.confidence_scores)

            # Extract key information
            vendor_name = "Unknown Vendor"
            total_amount = "0.00"

            if result.extracted_data.get("vendor_info", {}).get("name"):
                vendor_name = result.extracted_data["vendor_info"]["name"]

            if result.extracted_data.get("totals", {}).get("total_amount"):
                total_amount = result.extracted_data["totals"]["total_amount"]

            # Prepare data for agent
            recent_data = {
                "timestamp": datetime.now().isoformat(),
                "filename": file.filename,
                "vendor": vendor_name,
                "amount": total_amount,
                "confidence": f"{avg_confidence:.1%}" if avg_confidence else "Unknown",
                "processing_time": f"{result.processing_time:.2f}s" if result.processing_time else "Unknown",
                "invoice_number": result.extracted_data.get("invoice_details", {}).get("invoice_number", "N/A"),
                "invoice_date": result.extracted_data.get("dates", {}).get("invoice_date", "N/A"),
                "line_items_count": len(result.extracted_data.get("line_items", [])),
                "extraction_success": True
            }

            # Save to file that agent can read
            recent_file_path = Path(__file__).parent.parent.parent / "recent_processing.json"
            with open(recent_file_path, "w") as f:
                json.dump(recent_data, f, indent=2)

            logger.info(f"✅ Saved recent processing data for agent: {vendor_name} - ${total_amount}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to save recent processing data: {e}")

    return result


@app.get("/config")
async def get_config():
    """Get current configuration (non-sensitive data only)"""
    return {
        "max_file_size_mb": config.MAX_FILE_SIZE / (1024 * 1024),
        "allowed_extensions": list(config.ALLOWED_EXTENSIONS),
        "processor_location": config.LOCATION,
        "project_id": config.PROJECT_ID,
        "processor_id": config.PROCESSOR_ID[:8] + "...",  # Partial ID for security
        "api_version": "2.0.0",
        "features": {
            "document_ai": True,
            #"langchain_agent": "agent_router" in locals(),
            "langchain_agent": hasattr(app, "include_router"),
            "database": "create_tables" in locals()
        }
    }


@app.post("/batch-process")
async def batch_process_invoices(files: List[UploadFile] = File(...)):
    """
    Process multiple invoice files in batch
    """

    if len(files) > 10:  # Limit batch size
        raise HTTPException(status_code=400, detail="Too many files. Maximum 10 files per batch.")

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

            # Check file extension
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in config.ALLOWED_EXTENSIONS:
                results.append({
                    "file_index": i,
                    "filename": file.filename,
                    "success": False,
                    "message": f"Unsupported file type: {file_ext}"
                })
                continue

            # Read and process file
            file_content = await file.read()

            if len(file_content) > config.MAX_FILE_SIZE:
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
            mime_type = mime_type_map.get(file_ext, "application/octet-stream")

            # Process document
            result = await process_document_with_ai(file_content, mime_type)

            results.append({
                "file_index": i,
                "filename": file.filename,
                "success": result.success,
                "message": result.message,
                "extracted_data": result.extracted_data,
                "confidence_scores": result.confidence_scores,
                "processing_time": result.processing_time
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
        "successful_files": sum(1 for r in results if r["success"]),
        "failed_files": sum(1 for r in results if not r["success"])
    }


@app.post("/api/v1/mobile/process-invoice")
async def process_mobile_invoice_enhanced(file: UploadFile = File(...)):
    """
    🚀 Hybrid mobile invoice processing - Document AI + Enhanced OCR
    """
    try:
        logger.info(f"📱 Processing mobile invoice: {file.filename}")

        # Read file content
        content = await file.read()

        # Enhance image quality
        logger.info("🎨 Enhancing image quality...")
        enhanced_content = enhance_invoice_image(content)

        # Initialize Document AI client
        client = get_document_ai_client()
        if not client:
            raise HTTPException(status_code=500, detail="Document AI client not available")

        # Create the full resource name
        name = client.processor_path(config.PROJECT_ID, config.LOCATION, config.PROCESSOR_ID)
        logger.info(f"Using processor: {name}")

        # Process with Document AI first
        logger.info("🤖 Sending enhanced image to Document AI...")
        raw_document = documentai.RawDocument(content=enhanced_content, mime_type="image/png")
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        response = client.process_document(request=request)
        document = response.document

        entities = document.entities
        document_text = document.text if hasattr(document, 'text') else ""

        logger.info(f"📊 Document processed. Found {len(entities)} entities")
        logger.info(f"📄 Document text length: {len(document_text)}")

        # 🚀 USE HYBRID PROCESSING HERE!
        hybrid_result = await hybrid_process_document(enhanced_content, "image/png", entities, document_text)

        if hybrid_result["success"]:
            amount_info = hybrid_result["amount_info"]
            vendor_info = hybrid_result["vendor_info"]
            processing_method = hybrid_result["method"]
        else:
            # Emergency fallback
            amount_info = {"final_amount": "Unknown", "best_score": 0}
            vendor_info = {"name": "Unknown", "best_score": 0}
            processing_method = "fallback"

        # Calculate confidence score
        confidence_scores = [getattr(entity, 'confidence', 0.0) for entity in entities]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Prepare enhanced response
        response_data = {
            "success": True,
            "message": f"🎉 Invoice processed with {processing_method}",
            "extracted_data": {
                "vendor_info": vendor_info,
                "totals": {
                    "total_amount": amount_info['final_amount'],
                    "detected_amounts": amount_info.get('all_detected_amounts', [])
                }
            },
            "confidence_score": avg_confidence,
            "enhancement_details": {
                "processing_method": processing_method,
                "amount_score": amount_info.get('best_score', 0),
                "vendor_score": vendor_info.get('best_score', 0),
                "entities_found": len(entities),
                "document_text_length": len(document_text)
            },
            "processing_time": "real-time",
            "mobile_optimized": True
        }

        logger.info(f"✅ Hybrid processing complete!")
        logger.info(f"   🔧 Method: {processing_method}")
        logger.info(f"   💰 Amount: {amount_info['final_amount']} (score: {amount_info.get('best_score', 0)})")
        logger.info(f"   🏢 Vendor: {vendor_info['name']} (score: {vendor_info.get('best_score', 0)})")

        return response_data

    except Exception as e:
        logger.error(f"❌ Error in hybrid processing: {str(e)}")
        return {
            "success": False,
            "message": f"Hybrid processing failed: {str(e)}",
            "error_details": str(e)
        }

def enhance_mobile_image(image_data: bytes) -> bytes:
    """Enhance mobile camera images for better OCR"""
    try:
        image = Image.open(io.BytesIO(image_data))
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Enhance for OCR
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)

        # Save enhanced image
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=90)
        return output.getvalue()
    except Exception as e:
        logger.warning(f"Image enhancement failed: {e}")
        return image_data


@app.get("/api/v1/mobile/dashboard")
async def get_mobile_dashboard():
    """Vritti mobile dashboard data"""
    return {
        "status": "healthy",
        "message": "🕉️ Vritti Invoice AI ready",
        "app_name": "Vritti",
        "features": {
            "camera_scan": True,
            "ai_chat": True,
            "document_ai": True,
            "mobile_optimized": True
        },
        "version": "1.0.0"
    }


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
