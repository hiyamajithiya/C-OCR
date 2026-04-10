"""
Image preprocessing service for OCR optimization.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
import structlog

logger = structlog.get_logger()


class ImagePreprocessor:
    """Service for image preprocessing operations."""

    def __init__(self):
        """Initialize image preprocessor."""
        pass

    def preprocess_for_ocr(
        self,
        image: np.ndarray,
        deskew: bool = True,
        denoise: bool = True,
        normalize: bool = True,
        remove_borders: bool = True,
    ) -> np.ndarray:
        """
        Complete preprocessing pipeline for OCR.

        Args:
            image: Input image as numpy array
            deskew: Apply deskewing
            denoise: Apply denoising
            normalize: Apply contrast normalization
            remove_borders: Remove blank borders

        Returns:
            Preprocessed image
        """
        processed = image.copy()

        try:
            # Convert to grayscale if needed
            if len(processed.shape) == 3:
                processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)

            # Denoise
            if denoise:
                processed = self.denoise(processed)

            # Deskew
            if deskew:
                processed = self.deskew(processed)

            # Normalize contrast
            if normalize:
                processed = self.normalize_contrast(processed)

            # Remove borders
            if remove_borders:
                processed = self.remove_blank_borders(processed)

            logger.info("image_preprocessing_completed", shape=processed.shape)

        except Exception as e:
            logger.error("image_preprocessing_failed", error=str(e))
            raise

        return processed

    def deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Deskew image using Hough transform.

        Args:
            image: Input grayscale image

        Returns:
            Deskewed image
        """
        try:
            # Threshold to binary
            _, binary = cv2.threshold(
                image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

            # Detect edges
            edges = cv2.Canny(binary, 50, 150, apertureSize=3)

            # Detect lines using Hough transform
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)

            if lines is None or len(lines) == 0:
                return image

            # Calculate angles
            angles = []
            for line in lines:
                rho, theta = line[0]
                angle = np.degrees(theta) - 90
                angles.append(angle)

            # Get median angle
            median_angle = np.median(angles)

            # Only deskew if angle is significant (> 0.5 degrees)
            if abs(median_angle) > 0.5:
                # Rotate image
                (h, w) = image.shape
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                rotated = cv2.warpAffine(
                    image,
                    M,
                    (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                )

                logger.info("image_deskewed", angle=median_angle)
                return rotated

            return image

        except Exception as e:
            logger.error("deskew_failed", error=str(e))
            return image

    def denoise(self, image: np.ndarray, strength: int = 10) -> np.ndarray:
        """
        Remove noise from image using Non-local Means Denoising.

        Args:
            image: Input grayscale image
            strength: Denoising strength

        Returns:
            Denoised image
        """
        try:
            denoised = cv2.fastNlMeansDenoising(image, None, strength, 7, 21)
            logger.debug("image_denoised", strength=strength)
            return denoised

        except Exception as e:
            logger.error("denoise_failed", error=str(e))
            return image

    def normalize_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize image contrast using CLAHE.

        Args:
            image: Input grayscale image

        Returns:
            Contrast-normalized image
        """
        try:
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            normalized = clahe.apply(image)

            logger.debug("contrast_normalized")
            return normalized

        except Exception as e:
            logger.error("contrast_normalization_failed", error=str(e))
            return image

    def remove_blank_borders(
        self, image: np.ndarray, threshold: int = 250
    ) -> np.ndarray:
        """
        Remove blank borders from image.

        Args:
            image: Input grayscale image
            threshold: Pixel value threshold for "blank"

        Returns:
            Cropped image
        """
        try:
            # Find non-blank rows and columns
            mask = image < threshold

            # Find rows with content
            rows = np.any(mask, axis=1)
            cols = np.any(mask, axis=0)

            if not rows.any() or not cols.any():
                return image

            # Get bounding box
            row_min, row_max = np.where(rows)[0][[0, -1]]
            col_min, col_max = np.where(cols)[0][[0, -1]]

            # Crop with small padding
            padding = 10
            row_min = max(0, row_min - padding)
            row_max = min(image.shape[0], row_max + padding)
            col_min = max(0, col_min - padding)
            col_max = min(image.shape[1], col_max + padding)

            cropped = image[row_min:row_max, col_min:col_max]

            logger.debug(
                "borders_removed",
                original_shape=image.shape,
                cropped_shape=cropped.shape,
            )
            return cropped

        except Exception as e:
            logger.error("border_removal_failed", error=str(e))
            return image

    def binarize(self, image: np.ndarray, method: str = "otsu") -> np.ndarray:
        """
        Convert image to binary (black and white).

        Args:
            image: Input grayscale image
            method: Binarization method ('otsu', 'adaptive')

        Returns:
            Binary image
        """
        try:
            if method == "otsu":
                _, binary = cv2.threshold(
                    image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
            elif method == "adaptive":
                binary = cv2.adaptiveThreshold(
                    image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                )
            else:
                binary = image

            logger.debug("image_binarized", method=method)
            return binary

        except Exception as e:
            logger.error("binarization_failed", error=str(e))
            return image

    def resize_to_dpi(
        self,
        image: np.ndarray,
        target_dpi: int = 300,
        current_dpi: Optional[int] = None,
    ) -> np.ndarray:
        """
        Resize image to target DPI.

        Args:
            image: Input image
            target_dpi: Target DPI
            current_dpi: Current DPI (if known)

        Returns:
            Resized image
        """
        try:
            if current_dpi and current_dpi != target_dpi:
                scale_factor = target_dpi / current_dpi
                new_width = int(image.shape[1] * scale_factor)
                new_height = int(image.shape[0] * scale_factor)

                resized = cv2.resize(
                    image,
                    (new_width, new_height),
                    interpolation=(
                        cv2.INTER_CUBIC if scale_factor > 1 else cv2.INTER_AREA
                    ),
                )

                logger.info(
                    "image_resized",
                    original_shape=image.shape,
                    new_shape=resized.shape,
                    scale_factor=scale_factor,
                )
                return resized

            return image

        except Exception as e:
            logger.error("resize_failed", error=str(e))
            return image

    @staticmethod
    def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
        """
        Convert PIL Image to OpenCV format.

        Args:
            pil_image: PIL Image

        Returns:
            OpenCV image (numpy array)
        """
        # Convert to RGB if needed
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        # Convert to numpy array
        numpy_image = np.array(pil_image)

        # Convert RGB to BGR (OpenCV format)
        opencv_image = cv2.cvtColor(numpy_image, cv2.COLOR_RGB2BGR)

        return opencv_image

    @staticmethod
    def cv2_to_pil(cv2_image: np.ndarray) -> Image.Image:
        """
        Convert OpenCV image to PIL Image.

        Args:
            cv2_image: OpenCV image (numpy array)

        Returns:
            PIL Image
        """
        # Convert BGR to RGB if color image
        if len(cv2_image.shape) == 3:
            rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = cv2_image

        # Convert to PIL Image
        pil_image = Image.fromarray(rgb_image)

        return pil_image


# Global image preprocessor instance
image_preprocessor = ImagePreprocessor()
