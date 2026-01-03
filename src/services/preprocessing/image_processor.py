"""Image preprocessing service for OCR optimization."""

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Image preprocessing pipeline to clean and optimize images for OCR.
    
    This preprocessing can increase OCR accuracy by ~30%.
    """

    def __init__(
        self,
        denoise_strength: int = 10,
        adaptive_threshold_block_size: int = 11,
        adaptive_threshold_c: int = 2,
    ):
        """
        Initialize the preprocessor.
        
        Args:
            denoise_strength: Strength of denoising filter (higher = more smoothing)
            adaptive_threshold_block_size: Block size for adaptive thresholding (must be odd)
            adaptive_threshold_c: Constant subtracted from mean in adaptive thresholding
        """
        self.denoise_strength = denoise_strength
        self.block_size = adaptive_threshold_block_size
        self.threshold_c = adaptive_threshold_c

    def preprocess(
        self,
        image: NDArray[np.uint8],
        apply_grayscale: bool = True,
        apply_denoise: bool = True,
        apply_binarize: bool = True,
        apply_deskew: bool = True,
    ) -> NDArray[np.uint8]:
        """
        Apply the full preprocessing pipeline to an image.
        
        Args:
            image: Input image as numpy array (BGR format from cv2)
            apply_grayscale: Convert to grayscale
            apply_denoise: Apply denoising filter
            apply_binarize: Apply adaptive thresholding
            apply_deskew: Correct image rotation
            
        Returns:
            Preprocessed image as numpy array
        """
        processed = image.copy()

        # Step 1: Convert to grayscale
        if apply_grayscale and len(processed.shape) == 3:
            processed = self.to_grayscale(processed)
            logger.debug("Applied grayscale conversion")

        # Step 2: Denoise
        if apply_denoise:
            processed = self.denoise(processed)
            logger.debug("Applied denoising")

        # Step 3: Deskew (before binarization for better angle detection)
        if apply_deskew:
            processed = self.deskew(processed)
            logger.debug("Applied deskewing")

        # Step 4: Binarize
        if apply_binarize:
            processed = self.binarize(processed)
            logger.debug("Applied binarization")

        return processed

    def to_grayscale(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """
        Convert color image to grayscale.
        
        Args:
            image: BGR color image
            
        Returns:
            Grayscale image
        """
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def denoise(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """
        Remove noise/grain from image using Non-local Means Denoising.
        
        Args:
            image: Grayscale image
            
        Returns:
            Denoised image
        """
        if len(image.shape) == 2:
            # Grayscale denoising
            return cv2.fastNlMeansDenoising(
                image,
                None,
                h=self.denoise_strength,
                templateWindowSize=7,
                searchWindowSize=21,
            )
        else:
            # Color denoising
            return cv2.fastNlMeansDenoisingColored(
                image,
                None,
                self.denoise_strength,
                self.denoise_strength,
                7,
                21,
            )

    def binarize(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """
        Apply adaptive thresholding to make text black and background white.
        
        Uses Gaussian adaptive thresholding which handles varying lighting
        conditions better than global thresholding.
        
        Args:
            image: Grayscale image
            
        Returns:
            Binarized image
        """
        # Ensure grayscale
        if len(image.shape) == 3:
            image = self.to_grayscale(image)

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            self.block_size,
            self.threshold_c,
        )

        return binary

    def deskew(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """
        Detect and correct image rotation (skew).
        
        Uses Hough Line Transform to detect dominant line angles.
        
        Args:
            image: Input image
            
        Returns:
            Deskewed image
        """
        # Ensure grayscale for edge detection
        if len(image.shape) == 3:
            gray = self.to_grayscale(image)
        else:
            gray = image.copy()

        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Detect lines using Hough Transform
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=100,
            minLineLength=100,
            maxLineGap=10,
        )

        if lines is None or len(lines) == 0:
            logger.debug("No lines detected for deskewing")
            return image

        # Calculate angles of detected lines
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 != 0:
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                # Only consider near-horizontal lines
                if abs(angle) < 45:
                    angles.append(angle)

        if not angles:
            return image

        # Use median angle to avoid outliers
        median_angle = np.median(angles)

        # Only rotate if the angle is significant
        if abs(median_angle) < 0.5:
            return image

        # Rotate image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        
        # Calculate new image size to avoid cropping
        cos = np.abs(rotation_matrix[0, 0])
        sin = np.abs(rotation_matrix[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        
        # Adjust rotation matrix
        rotation_matrix[0, 2] += (new_w / 2) - center[0]
        rotation_matrix[1, 2] += (new_h / 2) - center[1]

        # Apply rotation with white background
        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255) if len(image.shape) == 3 else 255,
        )

        logger.info(f"Deskewed image by {median_angle:.2f} degrees")
        return rotated

    def remove_borders(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """
        Remove black borders from scanned documents.
        
        Args:
            image: Input image
            
        Returns:
            Image with borders removed
        """
        # Ensure grayscale
        if len(image.shape) == 3:
            gray = self.to_grayscale(image)
        else:
            gray = image.copy()

        # Threshold to find content
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        # Find contours
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return image

        # Find bounding box of all contours
        all_points = np.concatenate(contours)
        x, y, w, h = cv2.boundingRect(all_points)

        # Add padding
        padding = 10
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(image.shape[1] - x, w + 2 * padding)
        h = min(image.shape[0] - y, h + 2 * padding)

        return image[y : y + h, x : x + w]

    def enhance_contrast(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """
        Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
        
        Args:
            image: Input image
            
        Returns:
            Contrast-enhanced image
        """
        if len(image.shape) == 3:
            # Convert to LAB color space
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            # Merge and convert back
            lab = cv2.merge([l, a, b])
            return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            # Apply CLAHE directly for grayscale
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(image)

    @staticmethod
    def load_image(file_path: str | Path) -> NDArray[np.uint8]:
        """
        Load an image from file.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Image as numpy array
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be read as image
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Could not read image file: {file_path}")

        return image

    @staticmethod
    def save_image(image: NDArray[np.uint8], file_path: str | Path) -> None:
        """
        Save an image to file.
        
        Args:
            image: Image as numpy array
            file_path: Output path
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), image)


def preprocess_image(
    image_path: str | Path,
    output_path: str | Path | None = None,
) -> NDArray[np.uint8]:
    """
    Convenience function to preprocess an image file.
    
    Args:
        image_path: Path to input image
        output_path: Optional path to save preprocessed image
        
    Returns:
        Preprocessed image as numpy array
    """
    preprocessor = ImagePreprocessor()
    image = preprocessor.load_image(image_path)
    processed = preprocessor.preprocess(image)

    if output_path:
        preprocessor.save_image(processed, output_path)

    return processed
