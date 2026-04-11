"""
OCR processing service for extracting text from documents.
"""

import json
import os
import platform
import shutil
from pathlib import Path
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger()

try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
    import fitz  # PyMuPDF

    TESSERACT_AVAILABLE = True
except ImportError as e:
    logger.warning("ocr_dependencies_not_available", error=str(e))
    TESSERACT_AVAILABLE = False


class OCRService:
    """
    Service for OCR processing using Tesseract OCR.
    """

    def __init__(self):
        """Initialize OCR service."""
        # Try to detect Tesseract installation
        if TESSERACT_AVAILABLE:
            tesseract_path = self._detect_tesseract_path()
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)
                logger.info("tesseract_path_configured", path=str(tesseract_path))

            try:
                version = pytesseract.get_tesseract_version()
                logger.info("tesseract_detected", version=str(version))
            except Exception as e:
                logger.warning("tesseract_not_installed", error=str(e))
                logger.info(
                    "tesseract_install_hint",
                    message="Install from: https://github.com/UB-Mannheim/tesseract/wiki",
                )

    def _detect_tesseract_path(self) -> Path | None:
        """Detect Tesseract executable path from env, PATH, and common install locations."""
        candidates: List[str] = []

        env_cmd = os.getenv("TESSERACT_CMD") or os.getenv("TESSERACT_PATH")
        if env_cmd:
            env_path = Path(env_cmd)
            if env_path.is_dir():
                candidates.append(str(env_path / "tesseract.exe"))
            else:
                candidates.append(str(env_path))

        in_path = shutil.which("tesseract")
        if in_path:
            candidates.append(in_path)

        if platform.system() == "Windows":
            candidates.extend(
                [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    r"D:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"D:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                ]
            )

        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return Path(candidate)

        return None

    def process_document(self, file_path: str, language: str = "eng") -> Dict[str, Any]:
        """
        Process a document and extract text using OCR.

        Args:
            file_path: Path to the document file
            language: OCR language code (default: eng for English)

        Returns:
            OCR results dictionary with pages and text

        Raises:
            Exception: If OCR processing fails
        """
        try:
            logger.info(
                "ocr_processing_started", file_path=file_path, language=language
            )

            # Determine file type
            file_extension = Path(file_path).suffix.lower()

            if file_extension == ".pdf":
                results = self._process_pdf(file_path, language)
            elif file_extension in [".jpg", ".jpeg", ".png", ".tiff", ".tif"]:
                results = self._process_image(file_path, language)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")

            logger.info(
                "ocr_processing_completed",
                file_path=file_path,
                page_count=len(results.get("pages", [])),
            )

            return results

        except Exception as e:
            logger.error("ocr_processing_failed", file_path=file_path, error=str(e))
            raise

    def _process_pdf(self, file_path: str, language: str) -> Dict[str, Any]:
        """
        Process a PDF document using PyMuPDF for rendering.

        Args:
            file_path: Path to PDF file
            language: OCR language

        Returns:
            OCR results
        """
        if not TESSERACT_AVAILABLE:
            logger.warning("tesseract_not_available_using_placeholder")
            return self._placeholder_result("pdf", language)

        try:
            # Open PDF with PyMuPDF
            pdf_doc = fitz.open(file_path)
            page_count = len(pdf_doc)

            logger.info(
                "converting_pdf_to_images", file_path=file_path, pages=page_count
            )

            pages_data = []
            full_text_parts = []

            for page_num in range(page_count):
                logger.info("processing_page", page=page_num + 1, total=page_count)

                # Get page and render to image at 300 DPI
                page = pdf_doc[page_num]
                # Scale factor for 300 DPI (default is 72 DPI)
                zoom = 300 / 72
                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix)

                # Convert to PIL Image
                img_data = pix.tobytes("png")
                from io import BytesIO

                image = Image.open(BytesIO(img_data))

                # Perform OCR on the image
                text = pytesseract.image_to_string(image, lang=language)

                # Get detailed OCR data with coordinates
                ocr_data = pytesseract.image_to_data(
                    image, lang=language, output_type=pytesseract.Output.DICT
                )

                # Calculate average confidence
                confidences = [int(conf) for conf in ocr_data["conf"] if conf != "-1"]
                avg_confidence = (
                    sum(confidences) / len(confidences) if confidences else 0.0
                )

                # Extract words with bounding box coordinates
                words_with_coords = []
                for i in range(len(ocr_data["text"])):
                    word = ocr_data["text"][i].strip()
                    if word:  # Only include non-empty words
                        words_with_coords.append(
                            {
                                "text": word,
                                "x": ocr_data["left"][i],
                                "y": ocr_data["top"][i],
                                "width": ocr_data["width"][i],
                                "height": ocr_data["height"][i],
                                "confidence": (
                                    int(ocr_data["conf"][i])
                                    if ocr_data["conf"][i] != "-1"
                                    else 0
                                ),
                            }
                        )

                # Get image dimensions for scaling
                img_width, img_height = image.size

                page_data = {
                    "page_number": page_num + 1,
                    "text": text.strip(),
                    "confidence": round(
                        avg_confidence / 100, 2
                    ),  # Convert to 0-1 scale
                    "words": ocr_data.get("text", []),
                    "words_with_coords": words_with_coords,
                    "image_width": img_width,
                    "image_height": img_height,
                    "dpi": 300,
                    "lines": [],
                    "blocks": [],
                }

                pages_data.append(page_data)
                full_text_parts.append(text.strip())

            pdf_doc.close()
            logger.info("pdf_processing_complete", pages=page_count)

            return {
                "document_type": "pdf",
                "page_count": page_count,
                "language": language,
                "pages": pages_data,
                "full_text": "\n\n".join(full_text_parts),
            }

        except Exception as e:
            logger.error("pdf_processing_error", file_path=file_path, error=str(e))
            # Fallback to placeholder if OCR fails
            return self._placeholder_result("pdf", language)

    def _process_image(self, file_path: str, language: str) -> Dict[str, Any]:
        """
        Process an image file.

        Args:
            file_path: Path to image file
            language: OCR language

        Returns:
            OCR results
        """
        if not TESSERACT_AVAILABLE:
            logger.warning("tesseract_not_available_using_placeholder")
            return self._placeholder_result("image", language)

        try:
            # Open image
            logger.info("processing_image", file_path=file_path)
            image = Image.open(file_path)

            # Perform OCR
            text = pytesseract.image_to_string(image, lang=language)

            # Get detailed OCR data with coordinates
            ocr_data = pytesseract.image_to_data(
                image, lang=language, output_type=pytesseract.Output.DICT
            )

            # Calculate average confidence
            confidences = [int(conf) for conf in ocr_data["conf"] if conf != "-1"]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Extract words with bounding box coordinates
            words_with_coords = []
            for i in range(len(ocr_data["text"])):
                word = ocr_data["text"][i].strip()
                if word:  # Only include non-empty words
                    words_with_coords.append(
                        {
                            "text": word,
                            "x": ocr_data["left"][i],
                            "y": ocr_data["top"][i],
                            "width": ocr_data["width"][i],
                            "height": ocr_data["height"][i],
                            "confidence": (
                                int(ocr_data["conf"][i])
                                if ocr_data["conf"][i] != "-1"
                                else 0
                            ),
                        }
                    )

            # Get image dimensions
            img_width, img_height = image.size

            page_data = {
                "page_number": 1,
                "text": text.strip(),
                "confidence": round(avg_confidence / 100, 2),  # Convert to 0-1 scale
                "words": ocr_data.get("text", []),
                "words_with_coords": words_with_coords,
                "image_width": img_width,
                "image_height": img_height,
                "dpi": 300,
                "lines": [],
                "blocks": [],
            }

            logger.info("image_processing_complete")

            return {
                "document_type": "image",
                "page_count": 1,
                "language": language,
                "pages": [page_data],
                "full_text": text.strip(),
            }

        except Exception as e:
            logger.error("image_processing_error", file_path=file_path, error=str(e))
            return self._placeholder_result("image", language)

    def _placeholder_result(self, doc_type: str, language: str) -> Dict[str, Any]:
        """
        Return placeholder OCR result when Tesseract is not available.

        Args:
            doc_type: Document type (pdf or image)
            language: OCR language

        Returns:
            Placeholder OCR results
        """
        return {
            "document_type": doc_type,
            "page_count": 1,
            "language": language,
            "pages": [
                {
                    "page_number": 1,
                    "text": "[Tesseract OCR not installed - install from https://github.com/UB-Mannheim/tesseract/wiki]",
                    "confidence": 0.0,
                    "words": [],
                    "words_with_coords": [],
                    "image_width": 0,
                    "image_height": 0,
                    "dpi": 300,
                    "lines": [],
                    "blocks": [],
                }
            ],
            "full_text": "[Tesseract OCR not installed - install from https://github.com/UB-Mannheim/tesseract/wiki]",
        }


# Global OCR service instance
ocr_service = OCRService()
