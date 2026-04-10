"""
Layout analysis service for detecting document structure and tables.
"""

import numpy as np
import cv2
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import structlog

logger = structlog.get_logger()


class LayoutAnalyzer:
    """Service for analyzing document layout."""

    def __init__(self):
        """Initialize layout analyzer."""
        pass

    def analyze_layout(
        self, image: np.ndarray, ocr_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze document layout including headers, footers, columns, and reading order.

        Args:
            image: Document image
            ocr_result: OCR result with words, lines, blocks

        Returns:
            Layout analysis result
        """
        height, width = image.shape[:2]

        # Detect headers and footers
        headers = self._detect_headers(ocr_result["blocks"], height)
        footers = self._detect_footers(ocr_result["blocks"], height)

        # Detect columns
        columns = self._detect_columns(ocr_result["blocks"], width)

        # Determine reading order
        reading_order = self._determine_reading_order(ocr_result["blocks"], columns)

        return {
            "headers": headers,
            "footers": footers,
            "columns": columns,
            "reading_order": reading_order,
            "page_dimensions": {"width": width, "height": height},
        }

    def _detect_headers(
        self,
        blocks: List[Dict[str, Any]],
        page_height: int,
        threshold_ratio: float = 0.15,
    ) -> List[Dict[str, Any]]:
        """
        Detect header blocks (top of page).

        Args:
            blocks: List of text blocks
            page_height: Page height in pixels
            threshold_ratio: Ratio of page height to consider as header region

        Returns:
            List of header blocks
        """
        threshold_y = page_height * threshold_ratio
        headers = [block for block in blocks if block["bbox"][1] < threshold_y]
        return headers

    def _detect_footers(
        self,
        blocks: List[Dict[str, Any]],
        page_height: int,
        threshold_ratio: float = 0.15,
    ) -> List[Dict[str, Any]]:
        """
        Detect footer blocks (bottom of page).

        Args:
            blocks: List of text blocks
            page_height: Page height in pixels
            threshold_ratio: Ratio of page height to consider as footer region

        Returns:
            List of footer blocks
        """
        threshold_y = page_height * (1 - threshold_ratio)
        footers = [block for block in blocks if block["bbox"][3] > threshold_y]
        return footers

    def _detect_columns(
        self, blocks: List[Dict[str, Any]], page_width: int
    ) -> List[Dict[str, Any]]:
        """
        Detect column structure by analyzing horizontal distribution.

        Args:
            blocks: List of text blocks
            page_width: Page width in pixels

        Returns:
            List of column definitions
        """
        if not blocks:
            return []

        # Get x-centers of all blocks
        x_centers = [(block["bbox"][0] + block["bbox"][2]) / 2 for block in blocks]

        # Simple approach: check if there are distinct clusters
        # For now, assume single column if standard deviation is low
        if len(x_centers) < 2:
            return [{"column_id": 0, "x_min": 0, "x_max": page_width}]

        # Use clustering to detect columns
        x_centers_sorted = sorted(x_centers)
        clusters = []
        current_cluster = [x_centers_sorted[0]]

        # Group x-centers with similar values
        threshold = page_width * 0.2  # 20% of page width

        for x in x_centers_sorted[1:]:
            if x - current_cluster[-1] < threshold:
                current_cluster.append(x)
            else:
                clusters.append(current_cluster)
                current_cluster = [x]

        if current_cluster:
            clusters.append(current_cluster)

        # Create column definitions
        if len(clusters) == 1:
            # Single column
            return [{"column_id": 0, "x_min": 0, "x_max": page_width}]
        else:
            # Multiple columns
            columns = []
            for idx, cluster in enumerate(clusters):
                avg_x = sum(cluster) / len(cluster)
                # Estimate column boundaries
                if idx == 0:
                    x_min = 0
                    x_max = (
                        avg_x + sum(clusters[idx + 1]) / len(clusters[idx + 1])
                    ) / 2
                elif idx == len(clusters) - 1:
                    x_min = (
                        avg_x + sum(clusters[idx - 1]) / len(clusters[idx - 1])
                    ) / 2
                    x_max = page_width
                else:
                    x_min = (
                        avg_x + sum(clusters[idx - 1]) / len(clusters[idx - 1])
                    ) / 2
                    x_max = (
                        avg_x + sum(clusters[idx + 1]) / len(clusters[idx + 1])
                    ) / 2

                columns.append({"column_id": idx, "x_min": x_min, "x_max": x_max})

            return columns

    def _determine_reading_order(
        self, blocks: List[Dict[str, Any]], columns: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Determine reading order of blocks.

        Args:
            blocks: List of text blocks
            columns: List of column definitions

        Returns:
            List of block indices in reading order
        """
        if not blocks:
            return []

        # Assign blocks to columns
        block_column_map = {}
        for idx, block in enumerate(blocks):
            x_center = (block["bbox"][0] + block["bbox"][2]) / 2

            # Find which column this block belongs to
            for col in columns:
                if col["x_min"] <= x_center <= col["x_max"]:
                    block_column_map[idx] = col["column_id"]
                    break

        # Sort blocks: first by column, then by y-position
        sorted_indices = sorted(
            range(len(blocks)),
            key=lambda idx: (block_column_map.get(idx, 0), blocks[idx]["bbox"][1]),
        )

        return sorted_indices

    def detect_tables(
        self, image: np.ndarray, ocr_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect tables in document using line detection and word clustering.

        Args:
            image: Document image
            ocr_result: OCR result with words

        Returns:
            List of detected tables
        """
        # Detect horizontal and vertical lines
        h_lines, v_lines = self._detect_lines(image)

        if not h_lines and not v_lines:
            # No lines detected, try word-based clustering
            return self._detect_tables_by_alignment(ocr_result["words"])

        # Reconstruct table structure from lines
        tables = self._reconstruct_tables_from_lines(
            h_lines, v_lines, ocr_result["words"], image.shape
        )

        return tables

    def _detect_lines(
        self, image: np.ndarray
    ) -> Tuple[List[Tuple[int, int, int, int]], List[Tuple[int, int, int, int]]]:
        """
        Detect horizontal and vertical lines in image.

        Args:
            image: Document image

        Returns:
            Tuple of (horizontal_lines, vertical_lines)
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply threshold
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        # Detect horizontal lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines_img = cv2.morphologyEx(
            binary, cv2.MORPH_OPEN, horizontal_kernel
        )
        h_lines = self._extract_line_coords(horizontal_lines_img, horizontal=True)

        # Detect vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical_lines_img = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
        v_lines = self._extract_line_coords(vertical_lines_img, horizontal=False)

        logger.debug(
            "lines_detected", horizontal_lines=len(h_lines), vertical_lines=len(v_lines)
        )

        return h_lines, v_lines

    def _extract_line_coords(
        self, line_image: np.ndarray, horizontal: bool = True
    ) -> List[Tuple[int, int, int, int]]:
        """
        Extract line coordinates from binary image.

        Args:
            line_image: Binary image with lines
            horizontal: True for horizontal lines, False for vertical

        Returns:
            List of line coordinates (x1, y1, x2, y2)
        """
        contours, _ = cv2.findContours(
            line_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        lines = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            if horizontal and w > h * 5:  # Wide rectangle = horizontal line
                lines.append((x, y, x + w, y))
            elif not horizontal and h > w * 5:  # Tall rectangle = vertical line
                lines.append((x, y, x, y + h))

        return lines

    def _reconstruct_tables_from_lines(
        self,
        h_lines: List[Tuple[int, int, int, int]],
        v_lines: List[Tuple[int, int, int, int]],
        words: List[Dict[str, Any]],
        image_shape: Tuple[int, int],
    ) -> List[Dict[str, Any]]:
        """
        Reconstruct table structure from detected lines.

        Args:
            h_lines: Horizontal lines
            v_lines: Vertical lines
            words: OCR words
            image_shape: Image dimensions

        Returns:
            List of table structures
        """
        if not h_lines or not v_lines:
            return []

        # Find intersections and create grid
        # Simplified implementation: create a single table
        tables = []

        # Sort lines
        h_lines_sorted = sorted(h_lines, key=lambda l: l[1])
        v_lines_sorted = sorted(v_lines, key=lambda l: l[0])

        if len(h_lines_sorted) < 2 or len(v_lines_sorted) < 2:
            return tables

        # Create cells from grid
        rows = []
        for r in range(len(h_lines_sorted) - 1):
            cells = []
            for c in range(len(v_lines_sorted) - 1):
                cell_bbox = [
                    v_lines_sorted[c][0],
                    h_lines_sorted[r][1],
                    v_lines_sorted[c + 1][0],
                    h_lines_sorted[r + 1][1],
                ]

                # Find words in this cell
                cell_words = self._find_words_in_bbox(words, cell_bbox)
                cell_text = " ".join([w["text"] for w in cell_words])

                cells.append({"text": cell_text, "bbox": cell_bbox, "row": r, "col": c})

            rows.append({"cells": cells})

        tables.append(
            {
                "rows": rows,
                "row_count": len(rows),
                "col_count": len(v_lines_sorted) - 1 if rows else 0,
            }
        )

        logger.info("tables_reconstructed", table_count=len(tables))

        return tables

    def _detect_tables_by_alignment(
        self, words: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect tables by analyzing word alignment (when no lines are present).

        Args:
            words: OCR words

        Returns:
            List of table structures
        """
        # Simplified implementation: look for repeated x-coordinates (columns)
        # This is a placeholder for more sophisticated alignment detection
        return []

    def _find_words_in_bbox(
        self, words: List[Dict[str, Any]], bbox: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Find words that fall within a bounding box.

        Args:
            words: List of word dictionaries
            bbox: Bounding box [x1, y1, x2, y2]

        Returns:
            List of words within bbox
        """
        result = []
        for word in words:
            word_bbox = word["bbox"]
            # Check if word center is within bbox
            word_center_x = (word_bbox[0] + word_bbox[2]) / 2
            word_center_y = (word_bbox[1] + word_bbox[3]) / 2

            if (
                bbox[0] <= word_center_x <= bbox[2]
                and bbox[1] <= word_center_y <= bbox[3]
            ):
                result.append(word)

        return result


# Global layout analyzer instance
layout_analyzer = LayoutAnalyzer()
