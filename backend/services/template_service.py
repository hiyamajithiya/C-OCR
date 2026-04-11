"""
Template matching and field extraction service.
Updated: Field extraction with coordinate-based and text-based fallback.
"""

import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import structlog

from django.conf import settings

logger = structlog.get_logger()


class TemplateService:
    """Service for template matching and signature computation."""

    def __init__(self):
        """Initialize template service."""
        self.match_threshold = settings.TEMPLATE_MATCH_THRESHOLD

    def read_ocr_data(self, document: Any) -> List[Dict[str, Any]]:
        """Load OCR page JSON payloads for a document."""
        from documents.models import OCRPage
        from services.storage import storage_service

        ocr_pages = OCRPage.objects.filter(document_id=document.id).order_by("page_no")
        pages_data: List[Dict[str, Any]] = []

        for ocr_page in ocr_pages:
            try:
                full_json_path = storage_service.get_full_path(ocr_page.json_path)
                with open(full_json_path, "r", encoding="utf-8") as f:
                    pages_data.append(json.load(f))
            except Exception as e:
                logger.error(
                    "template_ocr_json_read_error",
                    page_id=ocr_page.id,
                    document_id=document.id,
                    error=str(e),
                )

        return pages_data

    def compute_document_signature(
        self,
        ocr_result: Dict[str, Any],
        layout_analysis: Dict[str, Any],
        page_count: int,
    ) -> Dict[str, Any]:
        """
        Compute document signature for template matching.

        Args:
            ocr_result: OCR result with text and structure
            layout_analysis: Layout analysis result
            page_count: Number of pages

        Returns:
            Document signature dictionary
        """
        try:
            # Extract header phrases (first few blocks)
            header_phrases = self._extract_header_phrases(ocr_result)

            # Extract table headers if tables exist
            table_headers = self._extract_table_headers(ocr_result)

            # Compute layout hash
            layout_hash = self._compute_layout_hash(ocr_result)

            # Create signature
            signature = {
                "header_phrases": header_phrases,
                "table_headers": table_headers,
                "layout_hash": layout_hash,
                "page_count": page_count,
                "total_blocks": len(ocr_result.get("blocks", [])),
                "total_words": len(ocr_result.get("words", [])),
            }

            logger.info("document_signature_computed", signature=signature)

            return signature

        except Exception as e:
            logger.error("document_signature_computation_failed", error=str(e))
            return {}

    def _extract_header_phrases(
        self, ocr_result: Dict[str, Any], max_phrases: int = 10
    ) -> List[str]:
        """
        Extract key phrases from document header.

        Args:
            ocr_result: OCR result
            max_phrases: Maximum number of phrases to extract

        Returns:
            List of header phrases
        """
        blocks = ocr_result.get("blocks", [])
        if not blocks:
            return []

        # Take first few blocks as header
        header_blocks = blocks[: min(3, len(blocks))]

        phrases = []
        for block in header_blocks:
            text = block.get("text", "").strip()
            if text:
                # Normalize: lowercase, remove extra spaces
                normalized = " ".join(text.lower().split())
                phrases.append(normalized)

        return phrases[:max_phrases]

    def _extract_table_headers(self, ocr_result: Dict[str, Any]) -> List[List[str]]:
        """
        Extract table headers (first row of tables).

        Args:
            ocr_result: OCR result with tables

        Returns:
            List of table header rows
        """
        tables = ocr_result.get("tables", [])
        if not tables:
            return []

        headers = []
        for table in tables:
            rows = table.get("rows", [])
            if rows:
                # Get first row as header
                first_row = rows[0]
                header_texts = [
                    cell.get("text", "").strip().lower()
                    for cell in first_row.get("cells", [])
                ]
                headers.append(header_texts)

        return headers

    def _compute_layout_hash(self, ocr_result: Dict[str, Any], bins: int = 10) -> str:
        """
        Compute layout hash based on spatial distribution of text.

        Args:
            ocr_result: OCR result
            bins: Number of bins for histogram

        Returns:
            Layout hash string
        """
        words = ocr_result.get("words", [])
        if not words:
            return ""

        # Create histogram of word positions
        x_positions = [w["bbox"][0] for w in words]
        y_positions = [w["bbox"][1] for w in words]

        # Normalize positions to 0-1 range
        if x_positions:
            x_min, x_max = min(x_positions), max(x_positions)
            x_norm = [(x - x_min) / (x_max - x_min + 1) for x in x_positions]

            y_min, y_max = min(y_positions), max(y_positions)
            y_norm = [(y - y_min) / (y_max - y_min + 1) for y in y_positions]

            # Create histograms
            x_hist, _ = np.histogram(x_norm, bins=bins)
            y_hist, _ = np.histogram(y_norm, bins=bins)

            # Combine histograms
            combined = np.concatenate([x_hist, y_hist])

            # Create hash
            hash_input = ",".join(map(str, combined))
            layout_hash = hashlib.md5(hash_input.encode()).hexdigest()[:16]

            return layout_hash

        return ""

    def match_templates(
        self,
        document_signature: Dict[str, Any],
        template_signatures: List[Dict[str, Any]],
    ) -> List[Tuple[int, float]]:
        """
        Match document against template signatures.

        Args:
            document_signature: Document signature
            template_signatures: List of template signatures with IDs

        Returns:
            List of (template_id, similarity_score) sorted by score
        """
        if not template_signatures:
            return []

        scores = []

        for template in template_signatures:
            template_id = template.get("template_version_id")
            template_sig = template.get("signature", {})

            # Calculate similarity score
            score = self._calculate_similarity(document_signature, template_sig)

            if score >= self.match_threshold:
                scores.append((template_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            "template_matching_completed",
            matches=len(scores),
            best_score=scores[0][1] if scores else 0.0,
        )

        return scores

    def _calculate_similarity(
        self, sig1: Dict[str, Any], sig2: Dict[str, Any]
    ) -> float:
        """
        Calculate similarity between two signatures.

        Args:
            sig1: First signature
            sig2: Second signature

        Returns:
            Similarity score (0-1)
        """
        scores = []

        # Compare header phrases using TF-IDF cosine similarity
        headers1 = sig1.get("header_phrases", [])
        headers2 = sig2.get("header_phrases", [])

        if headers1 and headers2:
            header_score = self._text_similarity(headers1, headers2)
            scores.append(("headers", header_score, 0.4))  # Weight: 0.4

        # Compare table headers
        tables1 = sig1.get("table_headers", [])
        tables2 = sig2.get("table_headers", [])

        if tables1 and tables2:
            table_score = self._table_headers_similarity(tables1, tables2)
            scores.append(("tables", table_score, 0.3))  # Weight: 0.3

        # Compare layout hash
        hash1 = sig1.get("layout_hash", "")
        hash2 = sig2.get("layout_hash", "")

        if hash1 and hash2:
            layout_score = 1.0 if hash1 == hash2 else 0.0
            scores.append(("layout", layout_score, 0.2))  # Weight: 0.2

        # Compare page count
        pages1 = sig1.get("page_count", 0)
        pages2 = sig2.get("page_count", 0)

        if pages1 and pages2:
            page_score = 1.0 if pages1 == pages2 else 0.5
            scores.append(("pages", page_score, 0.1))  # Weight: 0.1

        # Calculate weighted average
        if not scores:
            return 0.0

        total_weight = sum(s[2] for s in scores)
        weighted_sum = sum(s[1] * s[2] for s in scores)

        similarity = weighted_sum / total_weight if total_weight > 0 else 0.0

        return similarity

    def _text_similarity(self, texts1: List[str], texts2: List[str]) -> float:
        """
        Calculate text similarity using TF-IDF.

        Args:
            texts1: First list of texts
            texts2: Second list of texts

        Returns:
            Similarity score (0-1)
        """
        try:
            # Combine all texts
            all_texts = texts1 + texts2

            if len(all_texts) < 2:
                return 0.0

            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(all_texts)

            # Calculate cosine similarity between two groups
            vec1 = tfidf_matrix[: len(texts1)].mean(axis=0)
            vec2 = tfidf_matrix[len(texts1) :].mean(axis=0)

            similarity = cosine_similarity(vec1, vec2)[0][0]

            return float(similarity)

        except Exception as e:
            logger.error("text_similarity_calculation_failed", error=str(e))
            return 0.0

    def _table_headers_similarity(
        self, tables1: List[List[str]], tables2: List[List[str]]
    ) -> float:
        """
        Calculate similarity between table headers.

        Args:
            tables1: First list of table headers
            tables2: Second list of table headers

        Returns:
            Similarity score (0-1)
        """
        if not tables1 or not tables2:
            return 0.0

        # Compare first table headers (most tables have similar structure)
        headers1 = set(tables1[0])
        headers2 = set(tables2[0])

        if not headers1 or not headers2:
            return 0.0

        # Jaccard similarity
        intersection = len(headers1 & headers2)
        union = len(headers1 | headers2)

        similarity = intersection / union if union > 0 else 0.0

        return similarity


class FieldExtractor:
    """Service for extracting fields from documents using templates."""

    def __init__(
        self,
        fields_json: Optional[Dict[str, Any]] = None,
        rules_json: Optional[Dict[str, Any]] = None,
        template_id: Optional[int] = None,
        signature_json: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize field extractor.

        Args:
            fields_json: Field definitions from the template version.
            rules_json: Validation rules from the template version.
            template_id: If provided, trained ML models scoped to this template
                are used to blend confidence scores.
            signature_json: Template signature — used to scale field bbox
                coordinates to the OCR page's coordinate system.
        """
        self.template_config = {
            "fields_json": fields_json or {},
            "rules_json": rules_json or {},
        }
        self.template_id = template_id
        self.signature_json = signature_json or {}

    def extract(self, ocr_pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Backward-compatible extraction API used by existing views."""
        extracted_fields = self.extract_fields(ocr_pages, self.template_config)

        fields: Dict[str, Any] = {}
        confidence: Dict[str, float] = {}
        for field_name, payload in extracted_fields.items():
            fields[field_name] = payload.get("value")
            confidence[field_name] = float(payload.get("confidence", 0.0))

        return {
            "fields": fields,
            "confidence": confidence,
            "details": extracted_fields,
        }

    def extract_fields(
        self, ocr_pages: List[Dict[str, Any]], template_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract fields from document using template configuration.

        Args:
            ocr_pages: List of OCR results per page with text and positions
            template_config: Template configuration with field definitions

        Returns:
            Extracted fields dictionary
        """
        fields_config = template_config.get("fields_json", {}).get("fields", [])
        extracted = {}

        for field_def in fields_config:
            field_name = field_def.get("name")
            field_page = field_def.get("page", 1)

            # Get OCR result for the field's page
            if field_page > len(ocr_pages):
                logger.warning(
                    "field_page_out_of_range", field=field_name, page=field_page
                )
                extracted[field_name] = {
                    "value": None,
                    "confidence": 0.0,
                    "field_label": field_def.get("label", field_name),
                    "field_type": field_def.get("type", "text"),
                    "extraction_method": "none",
                }
                continue

            ocr_result = ocr_pages[field_page - 1]  # Pages are 1-indexed

            # Extract value from bounding box (returns tuple: value, method, ocr_confidence)
            extraction_result = self._extract_from_bbox(ocr_result, field_def)

            if isinstance(extraction_result, tuple):
                value, extraction_method, ocr_confidence = extraction_result
            else:
                # Backward compatibility
                value = extraction_result
                extraction_method = "unknown"
                ocr_confidence = 0.0

            extracted[field_name] = {
                "value": value,
                "confidence": self._calculate_field_confidence(
                    value, field_def, extraction_method, ocr_confidence, field_name=field_name
                ),
                "field_label": field_def.get("label", field_name),
                "field_type": field_def.get("type", "text"),
                "extraction_method": extraction_method,
            }

        logger.info("fields_extracted", field_count=len(extracted))

        return extracted

    def _bbox_scale_factor(self, ocr_result: Dict[str, Any]) -> float:
        """
        Compute scale factor to map template-draw-space bbox coordinates
        to OCR-space coordinates. Templates are drawn at 150 DPI in the UI
        while OCR extracts coordinates at 300 DPI, so typically returns 2.0.

        Legacy templates don't store draw dimensions, so we fall back to the
        default 150→300 DPI ratio of 2.0 when no info is available.
        """
        draw_w = self.signature_json.get("draw_image_width")
        draw_h = self.signature_json.get("draw_image_height")
        ocr_w = ocr_result.get("image_width")
        ocr_h = ocr_result.get("image_height")

        # Prefer width ratio (templates are wider than tall typically)
        if draw_w and ocr_w and draw_w > 0:
            return float(ocr_w) / float(draw_w)
        if draw_h and ocr_h and draw_h > 0:
            return float(ocr_h) / float(draw_h)

        # Fall back to DPI ratio if dimensions unknown
        draw_dpi = self.signature_json.get("draw_dpi")
        ocr_dpi = ocr_result.get("dpi", 300)
        if draw_dpi and ocr_dpi and draw_dpi > 0:
            return float(ocr_dpi) / float(draw_dpi)

        # Legacy templates: the frontend has always used 150 DPI for drawing
        # and OCR extracts at 300 DPI, so assume 2.0 for best compatibility.
        return 2.0

    def _extract_from_bbox(
        self, ocr_result: Dict[str, Any], field_def: Dict[str, Any]
    ) -> Tuple[Optional[str], str, float]:
        """
        Extract field value from a defined bounding box.

        Args:
            ocr_result: OCR result for the page
            field_def: Field definition with x, y, width, height

        Returns:
            Tuple of (extracted_value, extraction_method, ocr_confidence)
        """
        import re

        # First, check if we have words_with_coords (preferred for bbox extraction)
        words_with_coords = ocr_result.get("words_with_coords", [])

        # Scale bbox coordinates from template draw space to OCR space
        scale = self._bbox_scale_factor(ocr_result)
        x = field_def.get("x", 0) * scale
        y = field_def.get("y", 0) * scale
        width = field_def.get("width", 0) * scale
        height = field_def.get("height", 0) * scale
        field_type = field_def.get("type", "text")

        # If we have words with coordinates and valid bbox, use coordinate-based extraction
        if words_with_coords and width > 0 and height > 0:
            # Define field bounding box
            field_x1 = x
            field_y1 = y
            field_x2 = x + width
            field_y2 = y + height

            # Find words overlapping the bbox (rectangle intersection test).
            # This is more forgiving than strict center-in-box matching and
            # catches words that are partially inside a drawn region.
            words_in_box = []
            for word in words_with_coords:
                word_x = word.get("x", 0)
                word_y = word.get("y", 0)
                word_width = word.get("width", 0)
                word_height = word.get("height", 0)
                word_x2 = word_x + word_width
                word_y2 = word_y + word_height

                # Compute intersection
                ix1 = max(field_x1, word_x)
                iy1 = max(field_y1, word_y)
                ix2 = min(field_x2, word_x2)
                iy2 = min(field_y2, word_y2)

                if ix2 > ix1 and iy2 > iy1:
                    # Require at least 40% of the word area to be inside the bbox
                    inter_area = (ix2 - ix1) * (iy2 - iy1)
                    word_area = max(word_width * word_height, 1)
                    if inter_area / word_area >= 0.4:
                        words_in_box.append(word)

            if words_in_box:
                # Sort by position (top to bottom, left to right)
                words_in_box.sort(key=lambda w: (w.get("y", 0), w.get("x", 0)))

                # Combine words into text
                value = " ".join([w.get("text", "") for w in words_in_box])
                value = value.strip() if value else None

                # Calculate average OCR confidence for extracted words
                confidences = [
                    w.get("confidence", 0) for w in words_in_box if w.get("confidence")
                ]
                avg_ocr_confidence = (
                    sum(confidences) / len(confidences) if confidences else 0.0
                )

                # For number fields, validate that the extracted value contains numbers
                # If it doesn't, fall back to text-based extraction
                if value and field_type == "number":
                    # Regex requires at least one digit (not just commas)
                    numbers = re.findall(r"\d[\d,]*\.?\d*", value)
                    if not numbers:
                        logger.warning(
                            "bbox_extraction_invalid_number",
                            field=field_def.get("name"),
                            value=value,
                            msg="Extracted value is not a valid number, falling back to text search",
                        )
                        # Fall through to text-based extraction
                    else:
                        logger.info(
                            "bbox_extraction_success",
                            field=field_def.get("name"),
                            value=value,
                            words_found=len(words_in_box),
                            ocr_confidence=avg_ocr_confidence,
                        )
                        return (value, "bbox", avg_ocr_confidence)
                elif value:
                    logger.info(
                        "bbox_extraction_success",
                        field=field_def.get("name"),
                        value=value,
                        words_found=len(words_in_box),
                        ocr_confidence=avg_ocr_confidence,
                    )
                    return (value, "bbox", avg_ocr_confidence)
            else:
                logger.warning(
                    "bbox_extraction_no_words",
                    field=field_def.get("name"),
                    bbox=[field_x1, field_y1, field_x2, field_y2],
                )

        # Fall back to text-based extraction using label search
        field_label = field_def.get("label", "")
        full_text = ocr_result.get("text", "")

        if field_label and full_text:
            if field_type == "text":
                # Text fields: extract the next words/line after the label
                text_result = self._extract_text_by_label(
                    full_text, field_label, field_def, ocr_result
                )
                if text_result[0]:
                    return text_result
                # If label search failed, try the first words from the full text
                # as a best-effort (only for fields on page 1 like company name)
                return (None, "none", 0.0)

            # Numeric / date / currency fields: use label search for numbers
            return self._extract_by_label_search(
                full_text, field_label, field_def, ocr_result
            )

        return (None, "none", 0.0)

    def _extract_text_by_label(
        self,
        full_text: str,
        field_label: str,
        field_def: Dict[str, Any],
        ocr_result: Dict[str, Any] = None,
    ) -> Tuple[Optional[str], str, float]:
        """
        Extract a text value by searching for a label in the OCR text
        and returning the text immediately after the label on the same
        line, or on the next line if nothing follows on the same line.
        """
        import re

        page_confidence = ocr_result.get("confidence", 0.0) * 100 if ocr_result else 0.0
        label_lower = field_label.strip().lower()
        field_name = (field_def.get("name") or "").strip().lower()

        if not label_lower and not field_name:
            return (None, "none", 0.0)

        # Build set of search phrases
        search_phrases = set()
        if label_lower:
            search_phrases.add(label_lower)
        if field_name and field_name != label_lower:
            search_phrases.add(field_name)
            # Replace underscores with spaces for readability match
            search_phrases.add(field_name.replace("_", " "))

        lines = [ln.strip() for ln in full_text.split("\n") if ln.strip()]

        for phrase in search_phrases:
            if len(phrase) < 2:
                continue
            pattern = re.compile(
                r"(?i)" + re.escape(phrase) + r"\s*[:\-]?\s*(.+)"
            )
            for idx, line in enumerate(lines):
                match = pattern.search(line)
                if not match:
                    continue
                after = match.group(1).strip()
                # Drop leftover separators
                after = re.sub(r"^[:\-\s]+", "", after)
                if after:
                    return (after, "label_search", page_confidence)
                # Nothing after label on this line — try the next line
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1].strip()
                    if next_line:
                        return (next_line, "label_search", page_confidence)

        # Last-ditch: if the field is on page 1 and is a common header field
        # (like Company Name), return the first non-trivial header line.
        if field_def.get("page", 1) == 1 and lines:
            for candidate in lines[:10]:
                cleaned = candidate.strip()
                # Skip header-looking lines containing only dates or numbers
                if len(cleaned) >= 3 and re.search(r"[A-Za-z]{3,}", cleaned):
                    return (cleaned, "header_heuristic", max(page_confidence - 20, 50))

        return (None, "none", 0.0)

    def _extract_by_label_search(
        self,
        full_text: str,
        field_label: str,
        field_def: Dict[str, Any],
        ocr_result: Dict[str, Any] = None,
    ) -> Tuple[Optional[str], str, float]:
        """
        Extract field value by searching for label in text.

        Args:
            full_text: Full page text
            field_label: Label to search for
            field_def: Field definition
            ocr_result: OCR result for confidence info

        Returns:
            Tuple of (extracted_value, extraction_method, ocr_confidence)
        """
        import re

        field_name = field_def.get("name", "").lower()

        # Get page-level OCR confidence
        page_confidence = ocr_result.get("confidence", 0.0) * 100 if ocr_result else 0.0

        # For Trial Balance documents, handle specific column extraction
        # Labels like "Capital account Opening Balance" should extract the opening balance column
        # Labels like "Capital account closing balance" should extract the closing balance column
        label_lower = field_label.lower()
        name_lower = field_name.lower()

        # Check for opening/closing indicators in both label and field name
        is_opening = (
            "opening" in label_lower or "open" in label_lower or "op" in name_lower
        )
        is_closing = (
            "closing" in label_lower or "close" in label_lower or "cl" in name_lower
        )

        # Comprehensive abbreviation expansions for accounting terms
        abbreviations = {
            # Core accounting terms
            "cap": "capital",
            "acc": "account",
            "bal": "balance",
            "op": "opening",
            "cl": "closing",
            "opn": "opening",
            "cls": "closing",
            # Liabilities and assets
            "usl": "unsecured loans",
            "sl": "secured loans",
            "curr": "current",
            "liab": "liabilities",
            "asset": "assets",
            "fa": "fixed assets",
            "ca": "current assets",
            # Income and expenses
            "inc": "income",
            "exp": "expense",
            "rev": "revenue",
            "sal": "salary",
            "int": "interest",
            "rent": "rent",
            "comm": "commission",
            "disc": "discount",
            # Financial terms
            "dep": "depreciation",
            "amort": "amortization",
            "prov": "provision",
            "res": "reserve",
            "ret": "retained",
            "earn": "earnings",
            "div": "dividend",
            "pft": "profit",
            "loss": "loss",
            "net": "net",
            "gross": "gross",
            # Payables and receivables
            "rec": "receivable",
            "pay": "payable",
            "ar": "accounts receivable",
            "ap": "accounts payable",
            "dr": "debit",
            "cr": "credit",
            "adv": "advance",
            # Inventory and stock
            "inv": "inventory",
            "stk": "stock",
            "pur": "purchase",
            "wip": "work in progress",
            "fin": "finished",
            "raw": "raw material",
            "goods": "goods",
            # Tax terms
            "tax": "tax",
            "gst": "gst",
            "cgst": "cgst",
            "sgst": "sgst",
            "igst": "igst",
            "tds": "tds",
            "vat": "vat",
            # Other common terms
            "tot": "total",
            "sub": "subtotal",
            "amt": "amount",
            "qty": "quantity",
            "rate": "rate",
            "bnk": "bank",
            "cash": "cash",
            "pre": "prepaid",
            "out": "outstanding",
            "misc": "miscellaneous",
            "oth": "other",
            "gen": "general",
            "admin": "administrative",
            "mfg": "manufacturing",
            "prod": "production",
            "dir": "direct",
            "indir": "indirect",
            "oh": "overhead",
        }

        # Extract the base label without "opening/closing balance" suffix
        base_label = label_lower
        for suffix in [
            "opening balance",
            "closing balance",
            "balance",
            "op bal",
            "cl bal",
        ]:
            base_label = base_label.replace(suffix, "").strip()

        # Build search terms from both label and field name
        search_terms = set()

        # Add base label words
        if base_label:
            search_terms.add(base_label)
            # Also add individual significant words
            for word in base_label.split():
                if len(word) > 2:
                    search_terms.add(word)
                    # Expand abbreviations
                    if word in abbreviations:
                        search_terms.add(abbreviations[word])

        # Extract meaningful parts from field name (e.g., "capopbal" -> "cap", "op", "bal")
        # Scan for known abbreviations within the field name
        for abbr, expanded in abbreviations.items():
            if abbr in name_lower:
                search_terms.add(expanded)
                logger.debug(
                    "field_name_abbr_found",
                    field_name=field_name,
                    abbr=abbr,
                    expanded=expanded,
                )

        # Search for lines containing the search terms
        lines = full_text.split("\n")

        # Try exact base_label match first
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if base_label and len(base_label) > 2 and base_label in line_lower:
                numbers = re.findall(r"[\d,]+\.?\d+", line)
                if numbers:
                    logger.info(
                        "label_search_found_numbers",
                        label=field_label,
                        base_label=base_label,
                        numbers=numbers,
                        is_opening=is_opening,
                        is_closing=is_closing,
                    )
                    if is_opening and len(numbers) >= 1:
                        return (numbers[0], "label_search", page_confidence)
                    elif is_closing and len(numbers) >= 1:
                        return (numbers[-1], "label_search", page_confidence)
                    else:
                        return (numbers[0], "label_search", page_confidence)

        # Try matching expanded terms (e.g., "capital" from "cap")
        for term in search_terms:
            if len(term) > 3:  # Only try meaningful terms
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if term in line_lower:
                        numbers = re.findall(r"[\d,]+\.?\d+", line)
                        if numbers:
                            logger.info(
                                "label_search_found_numbers_via_term",
                                label=field_label,
                                matched_term=term,
                                numbers=numbers,
                                is_opening=is_opening,
                                is_closing=is_closing,
                            )
                            if is_opening and len(numbers) >= 1:
                                return (numbers[0], "term_search", page_confidence)
                            elif is_closing and len(numbers) >= 1:
                                return (numbers[-1], "term_search", page_confidence)
                            else:
                                return (numbers[0], "term_search", page_confidence)

        # Fallback: simple pattern matching
        label_pattern = re.escape(field_label.lower().strip())
        for i, line in enumerate(lines):
            if re.search(label_pattern, line.lower()):
                parts = re.split(label_pattern, line.lower(), maxsplit=1)
                if len(parts) > 1:
                    after_label = parts[1].strip()
                    numbers = re.findall(r"[\d,]+\.?\d*", after_label)
                    if numbers:
                        return (numbers[0], "fallback", page_confidence)

        return (None, "none", 0.0)

    def _extract_label_relative(
        self, ocr_result: Dict[str, Any], field_def: Dict[str, Any]
    ) -> Optional[str]:
        """
        Extract field value relative to a label.

        Args:
            ocr_result: OCR result
            field_def: Field definition

        Returns:
            Extracted value or None
        """
        label_text = field_def.get("label_text", "")
        direction = field_def.get("direction", "right")  # right or below
        max_distance = field_def.get("max_distance_px", 200)

        words = ocr_result.get("words", [])

        # Find label
        label_word = None
        for word in words:
            if label_text.lower() in word.get("text", "").lower():
                label_word = word
                break

        if not label_word:
            return None

        # Find value based on direction
        label_bbox = label_word["bbox"]

        candidate_words = []
        for word in words:
            word_bbox = word["bbox"]

            if direction == "right":
                # Value is to the right of label
                if (
                    word_bbox[0] > label_bbox[2]
                    and abs(word_bbox[1] - label_bbox[1]) < 20
                    and word_bbox[0] - label_bbox[2] < max_distance
                ):
                    candidate_words.append(word)

            elif direction == "below":
                # Value is below label
                if (
                    word_bbox[1] > label_bbox[3]
                    and abs(word_bbox[0] - label_bbox[0]) < 50
                    and word_bbox[1] - label_bbox[3] < max_distance
                ):
                    candidate_words.append(word)

        if not candidate_words:
            return None

        # Sort and combine
        if direction == "right":
            candidate_words.sort(key=lambda w: w["bbox"][0])
        else:
            candidate_words.sort(key=lambda w: w["bbox"][1])

        value = " ".join([w["text"] for w in candidate_words[:5]])  # Limit to 5 words

        return value

    def _extract_box_based(
        self, ocr_result: Dict[str, Any], field_def: Dict[str, Any]
    ) -> Optional[str]:
        """
        Extract field value from a defined bounding box.

        Args:
            ocr_result: OCR result
            field_def: Field definition

        Returns:
            Extracted value or None
        """
        bbox = field_def.get("bbox", [])
        if len(bbox) < 4:
            return None

        words = ocr_result.get("words", [])

        # Find words within bbox
        words_in_box = []
        for word in words:
            word_bbox = word["bbox"]
            word_center_x = (word_bbox[0] + word_bbox[2]) / 2
            word_center_y = (word_bbox[1] + word_bbox[3]) / 2

            if (
                bbox[0] <= word_center_x <= bbox[2]
                and bbox[1] <= word_center_y <= bbox[3]
            ):
                words_in_box.append(word)

        if not words_in_box:
            return None

        # Sort by position (top to bottom, left to right)
        words_in_box.sort(key=lambda w: (w["bbox"][1], w["bbox"][0]))

        value = " ".join([w["text"] for w in words_in_box])

        return value

    def _calculate_field_confidence(
        self,
        value: Optional[str],
        field_def: Dict[str, Any],
        extraction_method: str = "unknown",
        ocr_confidence: float = 0.0,
        field_name: Optional[str] = None,
    ) -> float:
        """
        Calculate confidence score for extracted field.

        Args:
            value: Extracted value
            field_def: Field definition
            extraction_method: How the value was extracted ('bbox', 'label_search', 'term_search')
            ocr_confidence: Average OCR confidence for the extracted words

        Returns:
            Confidence score (0-1)
        """
        import re

        if not value:
            return 0.0

        field_type = field_def.get("type", "text")

        # Base confidence depends on extraction method
        if extraction_method == "bbox":
            # Coordinate-based extraction is most reliable
            confidence = 0.90
        elif extraction_method == "label_search":
            # Direct label match is good
            confidence = 0.85
        elif extraction_method == "term_search":
            # Expanded term search is less certain
            confidence = 0.75
        else:
            confidence = 0.70

        # Adjust based on OCR confidence if available
        if ocr_confidence > 0:
            # OCR confidence is typically 0-100, normalize to 0-1
            ocr_factor = (
                ocr_confidence / 100.0 if ocr_confidence > 1 else ocr_confidence
            )
            # Blend with extraction confidence
            confidence = confidence * 0.7 + ocr_factor * 0.3

        # Validate based on field type
        if field_type == "number":
            # Check if value looks like a valid number
            clean_value = value.replace(",", "").replace(" ", "")
            if re.match(r"^-?\d+\.?\d*$", clean_value):
                confidence += 0.05  # Bonus for valid number format
            elif re.search(r"\d", value):
                pass  # Contains digits but not clean format
            else:
                confidence -= 0.20  # Penalty for no digits in number field

        elif field_type == "date":
            # Check for date-like patterns
            if re.search(r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}", value):
                confidence += 0.05

        elif field_type == "email":
            if "@" in value and "." in value:
                confidence += 0.05

        # Ensure confidence is within bounds
        confidence = max(0.0, min(1.0, confidence))

        # If a trained ML model exists for this template+field, blend in its prediction
        rule_confidence = round(confidence, 2)
        name = field_name or field_def.get("name")
        if self.template_id and name:
            try:
                from services.ml_training_service import ml_training_service

                ml_confidence = ml_training_service.predict_confidence(
                    template_id=self.template_id,
                    field_name=name,
                    extracted_value=value,
                    ocr_confidence=rule_confidence,
                    context_text="",
                )
                # predict_confidence returns the input ocr_confidence untouched when
                # no model file exists, so only log + use when it actually changed.
                if ml_confidence is not None and abs(ml_confidence - rule_confidence) > 1e-6:
                    logger.info(
                        "ml_confidence_used",
                        template_id=self.template_id,
                        field_name=name,
                        rule_confidence=rule_confidence,
                        ml_confidence=ml_confidence,
                    )
                    return round(float(ml_confidence), 2)
            except Exception as exc:
                logger.warning(
                    "ml_confidence_error",
                    template_id=self.template_id,
                    field_name=name,
                    error=str(exc),
                )

        return rule_confidence


# Global service instances
template_service = TemplateService()
field_extractor = FieldExtractor()
