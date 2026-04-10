"""
Searchable PDF generation service.
Creates PDFs with image underlay and invisible text layer.
"""

import io
from typing import List, Dict, Any, BinaryIO
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import fitz  # PyMuPDF
import structlog

logger = structlog.get_logger()


class SearchablePDFGenerator:
    """Service for generating searchable PDFs."""

    def __init__(self):
        """Initialize PDF generator."""
        pass

    def create_searchable_pdf(
        self, pages_data: List[Dict[str, Any]], output_path: str = None
    ) -> bytes:
        """
        Create a searchable PDF from pages with OCR data.

        Args:
            pages_data: List of page data containing:
                - image: PIL Image or image path
                - ocr_result: OCR result with words and bounding boxes
                - width: Page width
                - height: Page height
            output_path: Optional path to save PDF

        Returns:
            PDF content as bytes
        """
        try:
            # Create PDF document
            pdf_doc = fitz.open()

            for page_data in pages_data:
                # Add page to document
                self._add_page_to_pdf(pdf_doc, page_data)

            # Save to bytes
            pdf_bytes = pdf_doc.tobytes()

            # Optionally save to file
            if output_path:
                pdf_doc.save(output_path)

            pdf_doc.close()

            logger.info(
                "searchable_pdf_created",
                pages=len(pages_data),
                size_bytes=len(pdf_bytes),
            )

            return pdf_bytes

        except Exception as e:
            logger.error("searchable_pdf_creation_failed", error=str(e))
            raise

    def _add_page_to_pdf(self, pdf_doc: fitz.Document, page_data: Dict[str, Any]):
        """
        Add a single page with image and text layer to PDF.

        Args:
            pdf_doc: PyMuPDF document
            page_data: Page data with image and OCR result
        """
        # Get page dimensions
        width = page_data["width"]
        height = page_data["height"]

        # Create new page
        page = pdf_doc.new_page(width=width, height=height)

        # Insert background image
        image = page_data.get("image")
        if image:
            if isinstance(image, str):
                # Image path
                page.insert_image(page.rect, filename=image)
            elif isinstance(image, Image.Image):
                # PIL Image - convert to bytes
                img_bytes = io.BytesIO()
                image.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                page.insert_image(page.rect, stream=img_bytes.getvalue())

        # Add invisible text layer
        ocr_result = page_data.get("ocr_result", {})
        words = ocr_result.get("words", [])

        for word in words:
            text = word.get("text", "")
            bbox = word.get("bbox", [])

            if not text or len(bbox) < 4:
                continue

            # Create text rectangle (convert coordinates if needed)
            rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])

            # Insert invisible text
            # Set render mode to 3 (invisible)
            page.insert_textbox(
                rect,
                text,
                fontsize=bbox[3] - bbox[1],  # Approximate font size from height
                render_mode=3,  # Invisible
                color=(0, 0, 0),
                align=0,  # Left align
            )

    def create_searchable_pdf_reportlab(
        self, pages_data: List[Dict[str, Any]], output_stream: BinaryIO = None
    ) -> bytes:
        """
        Alternative implementation using ReportLab.
        Create a searchable PDF from pages with OCR data.

        Args:
            pages_data: List of page data
            output_stream: Optional output stream

        Returns:
            PDF content as bytes
        """
        try:
            # Create PDF in memory
            buffer = output_stream or io.BytesIO()
            c = canvas.Canvas(buffer)

            for page_data in pages_data:
                width = page_data.get("width", 612)
                height = page_data.get("height", 792)

                # Set page size
                c.setPageSize((width, height))

                # Draw background image
                image = page_data.get("image")
                if image:
                    if isinstance(image, str):
                        c.drawImage(image, 0, 0, width=width, height=height)
                    elif isinstance(image, Image.Image):
                        img_reader = ImageReader(image)
                        c.drawImage(img_reader, 0, 0, width=width, height=height)

                # Add invisible text layer
                ocr_result = page_data.get("ocr_result", {})
                words = ocr_result.get("words", [])

                c.setFillColorRGB(0, 0, 0, alpha=0)  # Invisible text

                for word in words:
                    text = word.get("text", "")
                    bbox = word.get("bbox", [])

                    if not text or len(bbox) < 4:
                        continue

                    # Calculate font size
                    text_height = bbox[3] - bbox[1]
                    font_size = max(1, int(text_height * 0.8))

                    # Position text (ReportLab uses bottom-left origin)
                    x = bbox[0]
                    y = height - bbox[3]  # Flip y-coordinate

                    # Draw invisible text
                    text_obj = c.beginText(x, y)
                    text_obj.setFont("Helvetica", font_size)
                    text_obj.setTextRenderMode(3)  # Invisible
                    text_obj.textLine(text)
                    c.drawText(text_obj)

                c.showPage()

            c.save()

            # Get PDF bytes
            if output_stream is None:
                buffer.seek(0)
                pdf_bytes = buffer.read()
            else:
                pdf_bytes = b""

            logger.info("searchable_pdf_created_reportlab", pages=len(pages_data))

            return pdf_bytes

        except Exception as e:
            logger.error("searchable_pdf_creation_reportlab_failed", error=str(e))
            raise

    def add_metadata(self, pdf_bytes: bytes, metadata: Dict[str, str]) -> bytes:
        """
        Add metadata to PDF.

        Args:
            pdf_bytes: PDF content
            metadata: Metadata dictionary (title, author, subject, etc.)

        Returns:
            PDF with metadata
        """
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            # Set metadata
            pdf_doc.set_metadata(metadata)

            # Save to bytes
            result_bytes = pdf_doc.tobytes()
            pdf_doc.close()

            return result_bytes

        except Exception as e:
            logger.error("pdf_metadata_addition_failed", error=str(e))
            return pdf_bytes


# Global PDF generator instance
pdf_generator = SearchablePDFGenerator()
