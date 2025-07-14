# src/services/ocr_service.py
"""
OCR service - Using centralized config
"""

import logging
import signal
from typing import Dict, Any, Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class OCRService:
    """OCR service using Tesseract with centralized config"""

    def __init__(self):
        self.settings = get_settings()
        self.tesseract_configured = False
        self._configure_tesseract()

    def _configure_tesseract(self) -> None:
        """Configure Tesseract using config settings"""
        if self.settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.settings.tesseract_cmd
            self.tesseract_configured = True
            logger.info(f"✅ Tesseract configured: {self.settings.tesseract_cmd}")
        else:
            # Assume tesseract is in PATH
            self.tesseract_configured = True
            logger.info("Using Tesseract from system PATH")

    def test_installation(self) -> bool:
        """Test if OCR is working properly"""
        try:
            # Create a simple test image
            img = Image.new('RGB', (300, 100), color='white')
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.text((10, 30), "Test $123.45", fill='black')

            # Convert to bytes
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

    def is_available(self) -> bool:
        """Check if OCR service is available"""
        return self.tesseract_configured

    def enhance_image(self, image_content: bytes) -> bytes:
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

    def extract_text(self, image_content: bytes, enhance: bool = True) -> Dict[str, Any]:
        """
        Extract text from image using OCR with configurable timeout

        Args:
            image_content: Image content as bytes
            enhance: Whether to enhance image before OCR

        Returns:
            Dict with OCR results
        """
        try:
            # Set timeout from config
            def timeout_handler(signum, frame):
                raise TimeoutError("OCR processing timed out")

            # Only set signal on Unix systems
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.settings.ocr_timeout)

            logger.info("📸 Converting image to OpenCV format...")

            # Enhance image if requested
            if enhance:
                image_content = self.enhance_image(image_content)

            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_content))

            # Convert to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

            logger.info("🎨 Preprocessing image...")

            # Simplified preprocessing
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

            logger.info("🔤 Extracting text with Tesseract...")

            # Use simple OCR without heavy preprocessing
            extracted_text = pytesseract.image_to_string(gray, config='--psm 6')

            # Cancel timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)

            logger.info(f"OCR extracted {len(extracted_text)} characters")
            logger.info(f"OCR text sample: {extracted_text[:200]}...")

            return {
                "success": True,
                "extracted_text": extracted_text,
                "method": "tesseract_ocr",
                "text_length": len(extracted_text)
            }

        except TimeoutError:
            logger.error(f"❌ OCR processing timed out after {self.settings.ocr_timeout} seconds")
            return {
                "success": False,
                "error": "OCR timeout",
                "method": "tesseract_ocr"
            }
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "tesseract_ocr"
            }

    def preprocess_for_ocr(self, cv_image):
        """
        Advanced preprocessing for better OCR accuracy
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

    def extract_with_multiple_configs(self, processed_image) -> str:
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


# Global service instance
ocr_service = OCRService()