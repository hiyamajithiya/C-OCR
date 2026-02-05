"""
PDF processing service for text extraction and page rendering.
"""

import io
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
import structlog

logger = structlog.get_logger()


class PDFService:
    """Service for PDF processing operations."""

    def __init__(self):
        """Initialize PDF service."""
        pass

    def has_text_layer(self, pdf_path: str) -> bool:
        """
        Check if PDF has a text layer (is it selectable or scanned).

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if PDF has selectable text, False if scanned
        """
        try:
            doc = fitz.open(pdf_path)

            # Check first few pages for text
            pages_to_check = min(3, len(doc))
            total_text_length = 0

            for page_num in range(pages_to_check):
                page = doc[page_num]
                text = page.get_text().strip()
                total_text_length += len(text)

            doc.close()

            # If we have significant text, consider it has a text layer
            # Threshold: at least 50 characters per page on average
            has_text = (total_text_length / pages_to_check) > 50

            logger.info(
                "pdf_text_layer_check",
                pdf_path=pdf_path,
                has_text=has_text,
                avg_text_length=total_text_length / pages_to_check
            )

            return has_text

        except Exception as e:
            logger.error("pdf_text_layer_check_failed", pdf_path=pdf_path, error=str(e))
            return False

    def extract_text_with_positions(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text with bounding box positions from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of pages with text blocks and positions
        """
        pages_data = []

        try:
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Get page dimensions
                page_rect = page.rect
                width = page_rect.width
                height = page_rect.height

                # Extract text with positions
                blocks = []
                text_dict = page.get_text("dict")

                for block in text_dict.get("blocks", []):
                    if block.get("type") == 0:  # Text block
                        block_bbox = block.get("bbox", [])

                        lines = []
                        for line in block.get("lines", []):
                            line_bbox = line.get("bbox", [])

                            words = []
                            for span in line.get("spans", []):
                                word_text = span.get("text", "").strip()
                                if word_text:
                                    words.append({
                                        "text": word_text,
                                        "bbox": span.get("bbox", []),
                                        "font": span.get("font", ""),
                                        "size": span.get("size", 0),
                                        "confidence": 1.0  # Native PDF text has perfect confidence
                                    })

                            if words:
                                lines.append({
                                    "words": words,
                                    "bbox": line_bbox,
                                    "text": " ".join([w["text"] for w in words])
                                })

                        if lines:
                            blocks.append({
                                "lines": lines,
                                "bbox": block_bbox,
                                "text": "\n".join([l["text"] for l in lines])
                            })

                page_data = {
                    "page_no": page_num + 1,
                    "width": width,
                    "height": height,
                    "blocks": blocks,
                    "source": "pdf_text_layer"
                }

                pages_data.append(page_data)

            doc.close()

            logger.info("pdf_text_extraction_completed", pdf_path=pdf_path, pages=len(pages_data))

        except Exception as e:
            logger.error("pdf_text_extraction_failed", pdf_path=pdf_path, error=str(e))
            raise

        return pages_data

    def render_page_to_image(
        self,
        pdf_path: str,
        page_num: int,
        dpi: int = 300
    ) -> Image.Image:
        """
        Render a PDF page as an image.

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            dpi: Resolution in DPI

        Returns:
            PIL Image object
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num - 1]  # Convert to 0-indexed

            # Calculate zoom factor for desired DPI
            zoom = dpi / 72  # 72 is the default DPI
            mat = fitz.Matrix(zoom, zoom)

            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat, alpha=False)

            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))

            doc.close()

            logger.info(
                "pdf_page_rendered",
                pdf_path=pdf_path,
                page_num=page_num,
                dpi=dpi,
                size=image.size
            )

            return image

        except Exception as e:
            logger.error(
                "pdf_page_render_failed",
                pdf_path=pdf_path,
                page_num=page_num,
                error=str(e)
            )
            raise

    def get_page_count(self, pdf_path: str) -> int:
        """
        Get the number of pages in a PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Number of pages
        """
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            logger.error("pdf_page_count_failed", pdf_path=pdf_path, error=str(e))
            return 0

    def extract_tables(self, pdf_path: str, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract tables from a PDF page using pdfplumber.

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)

        Returns:
            List of extracted tables with structure
        """
        tables = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_num > len(pdf.pages):
                    return tables

                page = pdf.pages[page_num - 1]

                # Extract tables
                page_tables = page.extract_tables()

                for table_idx, table_data in enumerate(page_tables):
                    if not table_data:
                        continue

                    # Convert table to structured format
                    rows = []
                    for row_idx, row in enumerate(table_data):
                        cells = []
                        for cell_idx, cell in enumerate(row):
                            cells.append({
                                "text": str(cell).strip() if cell else "",
                                "row": row_idx,
                                "col": cell_idx
                            })
                        rows.append({"cells": cells})

                    tables.append({
                        "table_id": table_idx,
                        "rows": rows,
                        "row_count": len(rows),
                        "col_count": len(table_data[0]) if table_data else 0
                    })

            logger.info(
                "pdf_tables_extracted",
                pdf_path=pdf_path,
                page_num=page_num,
                table_count=len(tables)
            )

        except Exception as e:
            logger.error(
                "pdf_table_extraction_failed",
                pdf_path=pdf_path,
                page_num=page_num,
                error=str(e)
            )

        return tables

    def get_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract PDF metadata.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary of metadata
        """
        try:
            doc = fitz.open(pdf_path)
            metadata = {
                "page_count": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
                "is_encrypted": doc.is_encrypted,
                "has_text": self.has_text_layer(pdf_path)
            }
            doc.close()
            return metadata

        except Exception as e:
            logger.error("pdf_metadata_extraction_failed", pdf_path=pdf_path, error=str(e))
            return {}


# Global PDF service instance
pdf_service = PDFService()
