# src/services/image_service.py
"""
Image processing and enhancement service
Specialized for invoice document processing
"""

import logging
import io
from typing import Optional, Tuple, Dict, Any

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class ImageProcessingService:
    """
    Advanced image processing service for invoice documents
    """

    def __init__(self):
        self.settings = get_settings()

    def enhance_for_processing(self, image_content: bytes) -> bytes:
        """
        Main enhancement method for invoice processing

        Args:
            image_content: Original image bytes

        Returns:
            Enhanced image bytes
        """
        try:
            logger.info("🎨 Starting advanced image enhancement...")

            # Open and validate image
            image = Image.open(io.BytesIO(image_content))
            original_format = image.format

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Apply enhancement pipeline
            enhanced_image = self._enhancement_pipeline(image)

            # Convert back to bytes
            output = io.BytesIO()
            save_format = 'PNG' if original_format in ['PNG', 'TIFF'] else 'JPEG'
            quality = 95 if save_format == 'JPEG' else None

            if quality:
                enhanced_image.save(output, format=save_format, quality=quality, dpi=(300, 300))
            else:
                enhanced_image.save(output, format=save_format, dpi=(300, 300))

            enhanced_bytes = output.getvalue()

            logger.info(f"✅ Image enhanced: {len(image_content)} -> {len(enhanced_bytes)} bytes")
            return enhanced_bytes

        except Exception as e:
            logger.warning(f"⚠️ Image enhancement failed: {e}, using original")
            return image_content

    def _enhancement_pipeline(self, image: Image.Image) -> Image.Image:
        """
        Complete enhancement pipeline for invoice images
        """
        # Step 1: Auto-rotate if needed
        image = self._auto_rotate(image)

        # Step 2: Enhance contrast and brightness
        image = self._enhance_contrast_brightness(image)

        # Step 3: Enhance sharpness
        image = self._enhance_sharpness(image)

        # Step 4: Remove noise
        image = self._reduce_noise(image)

        # Step 5: Optimize for text recognition
        image = self._optimize_for_ocr(image)

        return image

    def _auto_rotate(self, image: Image.Image) -> Image.Image:
        """
        Auto-rotate image based on EXIF data and content analysis
        """
        try:
            # Try EXIF orientation first
            image = ImageOps.exif_transpose(image)

            # TODO: Add content-based rotation detection for invoices
            # This would analyze text orientation using OCR

            return image
        except Exception as e:
            logger.debug(f"Auto-rotation failed: {e}")
            return image

    def _enhance_contrast_brightness(self, image: Image.Image) -> Image.Image:
        """
        Intelligently enhance contrast and brightness
        """
        # Analyze image statistics
        grayscale = image.convert('L')
        histogram = grayscale.histogram()

        # Calculate brightness statistics
        total_pixels = sum(histogram)
        weighted_sum = sum(i * count for i, count in enumerate(histogram))
        mean_brightness = weighted_sum / total_pixels

        # Adaptive enhancement based on image characteristics
        if mean_brightness < 100:  # Dark image
            brightness_factor = 1.2
            contrast_factor = 1.4
        elif mean_brightness > 180:  # Bright image
            brightness_factor = 0.9
            contrast_factor = 1.2
        else:  # Normal image
            brightness_factor = 1.1
            contrast_factor = 1.3

        # Apply enhancements
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(brightness_factor)

        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(contrast_factor)

        return image

    def _enhance_sharpness(self, image: Image.Image) -> Image.Image:
        """
        Enhance image sharpness for better text recognition
        """
        # Apply moderate sharpening
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)

        # Apply unsharp mask for fine details
        image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))

        return image

    def _reduce_noise(self, image: Image.Image) -> Image.Image:
        """
        Reduce noise while preserving text clarity
        """
        # Convert to OpenCV format for advanced filtering
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(cv_image, 9, 75, 75)

        # Convert back to PIL
        image = Image.fromarray(cv2.cvtColor(filtered, cv2.COLOR_BGR2RGB))

        return image

    def _optimize_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Final optimization specifically for OCR recognition
        """
        # Convert to grayscale for analysis
        gray = image.convert('L')

        # Apply adaptive histogram equalization
        cv_gray = np.array(gray)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(cv_gray)

        # Convert back to RGB
        enhanced_image = Image.fromarray(enhanced_gray).convert('RGB')

        return enhanced_image

    def enhance_for_mobile(self, image_content: bytes) -> bytes:
        """
        Mobile-specific image enhancement (lighter processing)
        """
        try:
            logger.info("📱 Applying mobile-optimized enhancement...")

            image = Image.open(io.BytesIO(image_content))

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Lighter enhancement for mobile
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)

            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.3)

            # Convert back to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=90)
            return output.getvalue()

        except Exception as e:
            logger.warning(f"Mobile enhancement failed: {e}")
            return image_content

    def prepare_for_document_ai(self, image_content: bytes) -> bytes:
        """
        Prepare image specifically for Google Document AI
        """
        try:
            logger.info("🤖 Preparing image for Document AI...")

            image = Image.open(io.BytesIO(image_content))

            # Document AI works well with high contrast images
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Moderate enhancement for Document AI
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.25)

            # Ensure good resolution
            width, height = image.size
            if width < 1000 or height < 1000:
                # Upscale small images
                scale_factor = max(1000 / width, 1000 / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Convert to PNG for Document AI (better quality)
            output = io.BytesIO()
            image.save(output, format='PNG', dpi=(300, 300))
            return output.getvalue()

        except Exception as e:
            logger.warning(f"Document AI preparation failed: {e}")
            return image_content

    def prepare_for_ocr(self, image_content: bytes) -> bytes:
        """
        Prepare image specifically for Tesseract OCR
        """
        try:
            logger.info("🔍 Preparing image for OCR...")

            image = Image.open(io.BytesIO(image_content))

            # Convert to RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Apply full enhancement pipeline for OCR
            enhanced_image = self._enhancement_pipeline(image)

            # Additional OCR-specific processing
            enhanced_image = self._ocr_specific_processing(enhanced_image)

            # Convert to PNG for OCR (lossless)
            output = io.BytesIO()
            enhanced_image.save(output, format='PNG', dpi=(300, 300))
            return output.getvalue()

        except Exception as e:
            logger.warning(f"OCR preparation failed: {e}")
            return image_content

    def _ocr_specific_processing(self, image: Image.Image) -> Image.Image:
        """
        Additional processing specifically for OCR
        """
        # Convert to OpenCV for advanced processing
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Convert to grayscale
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive thresholding to improve text contrast
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Apply morphological operations to clean up text
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Convert back to RGB
        result = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2RGB)
        return Image.fromarray(result)

    def analyze_image_quality(self, image_content: bytes) -> Dict[str, Any]:
        """
        Analyze image quality and characteristics
        """
        try:
            image = Image.open(io.BytesIO(image_content))

            # Basic metrics
            width, height = image.size
            mode = image.mode
            format_type = image.format

            # Calculate quality metrics
            gray = image.convert('L')
            histogram = gray.histogram()

            # Brightness analysis
            total_pixels = sum(histogram)
            weighted_sum = sum(i * count for i, count in enumerate(histogram))
            mean_brightness = weighted_sum / total_pixels

            # Contrast analysis (standard deviation)
            variance = sum((i - mean_brightness) ** 2 * count for i, count in enumerate(histogram)) / total_pixels
            contrast_score = np.sqrt(variance)

            # Resolution adequacy
            pixel_count = width * height
            resolution_adequate = pixel_count > 500000  # 0.5 megapixels minimum

            return {
                "width": width,
                "height": height,
                "mode": mode,
                "format": format_type,
                "file_size": len(image_content),
                "mean_brightness": round(mean_brightness, 2),
                "contrast_score": round(contrast_score, 2),
                "resolution_adequate": resolution_adequate,
                "pixel_count": pixel_count,
                "quality_score": self._calculate_overall_quality_score(
                    mean_brightness, contrast_score, pixel_count
                )
            }

        except Exception as e:
            logger.error(f"Image quality analysis failed: {e}")
            return {"error": str(e)}

    def _calculate_overall_quality_score(self, brightness: float, contrast: float, pixels: int) -> float:
        """
        Calculate overall quality score (0-100)
        """
        # Brightness score (optimal around 128)
        brightness_score = 100 - abs(brightness - 128) / 128 * 100
        brightness_score = max(0, min(100, brightness_score))

        # Contrast score (higher is better, up to a point)
        contrast_score = min(contrast / 50 * 100, 100)

        # Resolution score
        resolution_score = min(pixels / 1000000 * 100, 100)  # 1MP = 100%

        # Weighted average
        overall_score = (brightness_score * 0.3 + contrast_score * 0.4 + resolution_score * 0.3)

        return round(overall_score, 2)


# Global service instance
image_service = ImageProcessingService()