"""
OCR service integrating PaddleOCR and Tesseract.
"""

import numpy as np
from typing import List, Dict, Any, Optional
from PIL import Image
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class OCREngine:
    """Base OCR engine interface."""

    def recognize(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Perform OCR on image.

        Args:
            image: Input image as numpy array

        Returns:
            OCR result with words, lines, and bounding boxes
        """
        raise NotImplementedError


class PaddleOCREngine(OCREngine):
    """PaddleOCR engine implementation."""

    def __init__(self, lang: str = "en"):
        """
        Initialize PaddleOCR engine.

        Args:
            lang: Language code
        """
        self.lang = lang
        self._ocr = None

    def _get_ocr(self):
        """Lazy load PaddleOCR."""
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.lang,
                    show_log=False,
                    use_gpu=False  # Set to True if GPU available
                )
                logger.info("paddleocr_initialized", lang=self.lang)
            except Exception as e:
                logger.error("paddleocr_initialization_failed", error=str(e))
                raise

        return self._ocr

    def recognize(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Perform OCR using PaddleOCR.

        Args:
            image: Input image as numpy array

        Returns:
            Structured OCR result
        """
        try:
            ocr = self._get_ocr()
            result = ocr.ocr(image, cls=True)

            # Parse PaddleOCR result
            words = []
            lines = []

            if result and result[0]:
                for line_result in result[0]:
                    bbox = line_result[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    text = line_result[1][0]  # Text
                    confidence = line_result[1][1]  # Confidence score

                    # Convert bbox to [x1, y1, x2, y2] format
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    bbox_rect = [
                        min(x_coords),
                        min(y_coords),
                        max(x_coords),
                        max(y_coords)
                    ]

                    # Split into words (simple space-based split)
                    word_texts = text.split()
                    word_width = (bbox_rect[2] - bbox_rect[0]) / max(len(word_texts), 1)

                    line_words = []
                    for idx, word_text in enumerate(word_texts):
                        word_bbox = [
                            bbox_rect[0] + (idx * word_width),
                            bbox_rect[1],
                            bbox_rect[0] + ((idx + 1) * word_width),
                            bbox_rect[3]
                        ]

                        word = {
                            "text": word_text,
                            "bbox": word_bbox,
                            "confidence": confidence
                        }
                        words.append(word)
                        line_words.append(word)

                    lines.append({
                        "text": text,
                        "bbox": bbox_rect,
                        "confidence": confidence,
                        "words": line_words
                    })

            logger.info(
                "paddleocr_recognition_completed",
                words_count=len(words),
                lines_count=len(lines)
            )

            return {
                "engine": "paddle",
                "words": words,
                "lines": lines
            }

        except Exception as e:
            logger.error("paddleocr_recognition_failed", error=str(e))
            raise


class TesseractOCREngine(OCREngine):
    """Tesseract OCR engine implementation."""

    def __init__(self, lang: str = "eng"):
        """
        Initialize Tesseract engine.

        Args:
            lang: Language code (use 'eng' for English)
        """
        self.lang = lang

    def recognize(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Perform OCR using Tesseract.

        Args:
            image: Input image as numpy array

        Returns:
            Structured OCR result
        """
        try:
            import pytesseract
            from PIL import Image

            # Convert numpy array to PIL Image
            if len(image.shape) == 2:  # Grayscale
                pil_image = Image.fromarray(image)
            else:  # Color
                pil_image = Image.fromarray(image)

            # Get detailed OCR data
            ocr_data = pytesseract.image_to_data(
                pil_image,
                lang=self.lang,
                output_type=pytesseract.Output.DICT
            )

            words = []
            lines = {}

            # Process each word
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                if not text:
                    continue

                conf = float(ocr_data['conf'][i])
                if conf < 0:  # Skip invalid confidence
                    continue

                bbox = [
                    ocr_data['left'][i],
                    ocr_data['top'][i],
                    ocr_data['left'][i] + ocr_data['width'][i],
                    ocr_data['top'][i] + ocr_data['height'][i]
                ]

                word = {
                    "text": text,
                    "bbox": bbox,
                    "confidence": conf / 100.0  # Normalize to 0-1
                }
                words.append(word)

                # Group by line
                line_num = ocr_data['line_num'][i]
                if line_num not in lines:
                    lines[line_num] = []
                lines[line_num].append(word)

            # Construct lines with bounding boxes
            line_list = []
            for line_num in sorted(lines.keys()):
                line_words = lines[line_num]

                # Calculate line bounding box
                x_min = min(w['bbox'][0] for w in line_words)
                y_min = min(w['bbox'][1] for w in line_words)
                x_max = max(w['bbox'][2] for w in line_words)
                y_max = max(w['bbox'][3] for w in line_words)

                line_text = " ".join(w['text'] for w in line_words)
                avg_conf = sum(w['confidence'] for w in line_words) / len(line_words)

                line_list.append({
                    "text": line_text,
                    "bbox": [x_min, y_min, x_max, y_max],
                    "confidence": avg_conf,
                    "words": line_words
                })

            logger.info(
                "tesseract_recognition_completed",
                words_count=len(words),
                lines_count=len(line_list)
            )

            return {
                "engine": "tesseract",
                "words": words,
                "lines": line_list
            }

        except Exception as e:
            logger.error("tesseract_recognition_failed", error=str(e))
            raise


class OCRService:
    """High-level OCR service with fallback support."""

    def __init__(
        self,
        primary_engine: str = None,
        fallback_engine: str = None,
        lang: str = None
    ):
        """
        Initialize OCR service.

        Args:
            primary_engine: Primary OCR engine ('paddle' or 'tesseract')
            fallback_engine: Fallback OCR engine
            lang: Language code
        """
        self.primary_engine_name = primary_engine or settings.OCR_ENGINE_PRIMARY
        self.fallback_engine_name = fallback_engine or settings.OCR_ENGINE_FALLBACK
        self.lang = lang or settings.OCR_LANGS

        # Initialize engines
        self.primary_engine = self._create_engine(self.primary_engine_name)
        self.fallback_engine = self._create_engine(self.fallback_engine_name)

    def _create_engine(self, engine_name: str) -> Optional[OCREngine]:
        """
        Create OCR engine instance.

        Args:
            engine_name: Engine name ('paddle' or 'tesseract')

        Returns:
            OCR engine instance or None
        """
        try:
            if engine_name == "paddle":
                return PaddleOCREngine(lang=self.lang)
            elif engine_name == "tesseract":
                return TesseractOCREngine(lang=self.lang if self.lang == "en" else "eng")
            else:
                logger.warning("unknown_ocr_engine", engine=engine_name)
                return None
        except Exception as e:
            logger.error("ocr_engine_creation_failed", engine=engine_name, error=str(e))
            return None

    def recognize(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Perform OCR with automatic fallback.

        Args:
            image: Input image as numpy array

        Returns:
            OCR result with words, lines, and blocks
        """
        # Try primary engine
        try:
            if self.primary_engine:
                logger.info("attempting_ocr", engine=self.primary_engine_name)
                result = self.primary_engine.recognize(image)

                # Check if result has sufficient content
                if result and len(result.get('words', [])) > 0:
                    result['blocks'] = self._cluster_lines_to_blocks(result['lines'])
                    return result

                logger.warning("primary_ocr_insufficient_result", engine=self.primary_engine_name)

        except Exception as e:
            logger.error("primary_ocr_failed", engine=self.primary_engine_name, error=str(e))

        # Fallback to secondary engine
        try:
            if self.fallback_engine:
                logger.info("attempting_ocr_fallback", engine=self.fallback_engine_name)
                result = self.fallback_engine.recognize(image)

                if result:
                    result['blocks'] = self._cluster_lines_to_blocks(result['lines'])
                    return result

        except Exception as e:
            logger.error("fallback_ocr_failed", engine=self.fallback_engine_name, error=str(e))

        # Return empty result if all engines fail
        logger.error("all_ocr_engines_failed")
        return {
            "engine": "none",
            "words": [],
            "lines": [],
            "blocks": []
        }

    def _cluster_lines_to_blocks(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Cluster lines into blocks based on proximity.

        Args:
            lines: List of line dictionaries

        Returns:
            List of block dictionaries
        """
        if not lines:
            return []

        blocks = []
        current_block_lines = [lines[0]]

        # Group lines into blocks based on vertical spacing
        for i in range(1, len(lines)):
            prev_line = lines[i - 1]
            curr_line = lines[i]

            # Calculate vertical gap
            prev_bottom = prev_line['bbox'][3]
            curr_top = curr_line['bbox'][1]
            gap = curr_top - prev_bottom

            # If gap is small, add to current block, otherwise start new block
            avg_height = (prev_line['bbox'][3] - prev_line['bbox'][1])
            if gap < avg_height * 1.5:  # Threshold: 1.5x line height
                current_block_lines.append(curr_line)
            else:
                # Finalize current block
                blocks.append(self._create_block(current_block_lines))
                current_block_lines = [curr_line]

        # Add last block
        if current_block_lines:
            blocks.append(self._create_block(current_block_lines))

        return blocks

    def _create_block(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a block from lines.

        Args:
            lines: List of line dictionaries

        Returns:
            Block dictionary
        """
        # Calculate block bounding box
        x_min = min(line['bbox'][0] for line in lines)
        y_min = min(line['bbox'][1] for line in lines)
        x_max = max(line['bbox'][2] for line in lines)
        y_max = max(line['bbox'][3] for line in lines)

        text = "\n".join(line['text'] for line in lines)
        avg_conf = sum(line['confidence'] for line in lines) / len(lines)

        return {
            "text": text,
            "bbox": [x_min, y_min, x_max, y_max],
            "confidence": avg_conf,
            "lines": lines
        }


# Global OCR service instance
ocr_service = OCRService()
