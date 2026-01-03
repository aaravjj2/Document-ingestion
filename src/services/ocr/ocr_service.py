"""OCR service using PaddleOCR."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
import cv2

logger = logging.getLogger(__name__)

# Extensions
from src.services.math.math_service import MathExtractionService

# Disable PaddleX model source check to avoid slow startup
os.environ.setdefault("DISABLE_MODEL_SOURCE_CHECK", "True")

# Thread lock for initialization
import threading
_ocr_lock = threading.Lock()
# Global PaddleOCR instance to avoid re-initialization issues
_paddle_ocr_instance = None

def _apply_paddlex_patch():
    """Patch PaddleX to handle re-initialization gracefully."""
    try:
        import paddlex.repo_manager as rm
        if hasattr(rm, 'initialize'):
            _orig_rm_init = rm.initialize
            def _safe_rm_init(*args, **kwargs):
                try:
                    return _orig_rm_init(*args, **kwargs)
                except RuntimeError as e:
                    if "already been initialized" in str(e):
                        logger.info("PaddleX already initialized (captured by patch)")
                        return None
                    raise
            rm.initialize = _safe_rm_init
            logger.info("Patched paddlex.repo_manager.initialize for idempotency")
    except (ImportError, Exception) as e:
        logger.debug(f"Could not patch paddlex: {e}")

def _setup_langchain_shim():
    """Create a shim for legacy langchain imports used by PaddleX."""
    import sys
    from types import ModuleType
    
    try:
        # 1. Ensure 'langchain' exists and is a package
        try:
            import langchain
        except ImportError:
            langchain = ModuleType('langchain')
            langchain.__path__ = []
            sys.modules['langchain'] = langchain

        if not hasattr(langchain, '__path__'):
            langchain.__path__ = []

        # Helper to ensure submodule exists
        def ensure_mod(name, parent_mod=None):
            if name not in sys.modules:
                mod = ModuleType(name)
                if '.' in name:
                    parent_name, child_name = name.rsplit('.', 1)
                    if parent_name in sys.modules:
                        setattr(sys.modules[parent_name], child_name, mod)
                sys.modules[name] = mod
            return sys.modules[name]

        # 2. Shim langchain.docstore.document.Document
        ensure_mod('langchain.docstore')
        document_mod = ensure_mod('langchain.docstore.document')
        if not hasattr(document_mod, 'Document'):
            try:
                from langchain_core.documents import Document
                document_mod.Document = Document
            except ImportError:
                pass

        # 3. Shim langchain.text_splitter.RecursiveCharacterTextSplitter
        splitter_mod = ensure_mod('langchain.text_splitter')
        if not hasattr(splitter_mod, 'RecursiveCharacterTextSplitter'):
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
                splitter_mod.RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
            except ImportError:
                pass
            
        logger.info("Setup robust legacy langchain shim for PaddleX")
    except Exception as e:
        logger.debug(f"Could not setup langchain shim: {e}")

# Apply shims and patches
_setup_langchain_shim()
_apply_paddlex_patch()


@dataclass
class OCRDetection:
    """Single OCR detection result."""
    
    text: str
    confidence: float
    bounding_box: list[list[float]]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box,
        }


@dataclass
class OCRPageResult:
    """OCR results for a single page."""
    
    page_number: int
    detections: list[OCRDetection]
    raw_text: str
    average_confidence: float
    latex_text: str = "" # Full text with latex replacements for Math Support
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "page_number": self.page_number,
            "detections": [d.to_dict() for d in self.detections],
            "raw_text": self.raw_text,
            "latex_text": self.latex_text,
            "average_confidence": self.average_confidence,
        }


class OCRService:
    """
    OCR service using PaddleOCR for text detection and recognition.
    
    PaddleOCR provides excellent accuracy for both printed and handwritten text,
    with support for multiple languages and complex layouts.
    """

    def __init__(
        self,
        language: str = "en",
        use_angle_cls: bool = True,
        use_gpu: bool = False,
        det_model_dir: str | None = None,
        rec_model_dir: str | None = None,
    ):
        """
        Initialize OCR service.
        
        Args:
            language: Language code for OCR (en, ch, fr, german, korean, japan, etc.)
            use_angle_cls: Whether to use angle classification for rotated text
            use_gpu: Whether to use GPU acceleration
            det_model_dir: Custom detection model directory
            rec_model_dir: Custom recognition model directory
        """
        self.language = language
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu
        self._det_model_dir = det_model_dir
        self._rec_model_dir = rec_model_dir
        
        # Initialize Math Extraction Service
        self.math_service = MathExtractionService(use_gpu=use_gpu)

    @property
    def ocr(self):
        """Lazy load PaddleOCR instance."""
        global _paddle_ocr_instance
        
        if _paddle_ocr_instance is None:
            with _ocr_lock:
                if _paddle_ocr_instance is None:
                    logger.info(f"Initializing PaddleOCR with language: {self.language}")
                    
                    try:
                        # Import inside try to catch reinitialization errors from paddlex
                        from paddleocr import PaddleOCR
                        
                        # Enhanced OCR parameters
                        kwargs = {
                            "lang": self.language,
                        }
                        
                        if self._det_model_dir:
                            kwargs["det_model_dir"] = self._det_model_dir
                        if self._rec_model_dir:
                            kwargs["rec_model_dir"] = self._rec_model_dir
                        
                        _paddle_ocr_instance = PaddleOCR(**kwargs)
                        logger.info("PaddleOCR initialized successfully")
                    except RuntimeError as e:
                        if "PDX has already been initialized" in str(e):
                            logger.info("PaddleX already initialized, attempting to get PaddleOCR...")
                            from paddleocr import PaddleOCR
                            # If we can't create a new instance, maybe we can use the existing one?
                            # But _paddle_ocr_instance is None, so we must at least try to create it.
                            try:
                                _paddle_ocr_instance = PaddleOCR(**kwargs)
                            except:
                                logger.error("Failed to recover PaddleOCR after re-init error")
                                raise
                        else:
                            raise
                    except Exception as e:
                        logger.error(f"Failed to initialize PaddleOCR: {e}")
                        raise

        return _paddle_ocr_instance

    def _deduplicate_detections(self, detections: list[tuple]) -> list[tuple]:
        """Remove duplicate detections from multi-scale processing."""
        if not detections:
            return []
        
        # Group detections by approximate position
        groups = {}
        for bbox, text, conf in detections:
            # Use center point as key
            center_x = sum(x for x, y in bbox) // 4
            center_y = sum(y for x, y in bbox) // 4
            # Round to nearest 20 pixels for grouping
            key = (center_x // 20, center_y // 20)
            
            if key not in groups:
                groups[key] = []
            groups[key].append((bbox, text, conf))
        
        # Keep highest confidence from each group
        unique = []
        for group in groups.values():
            best = max(group, key=lambda x: x[2])  # Sort by confidence
            unique.append(best)
        
        return unique

    def _preprocess_image(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """
        Apply advanced preprocessing optimized for high OCR confidence.
        Includes upscaling, multi-pass denoising, sharpening, and adaptive thresholding.
        """
        import cv2
        import numpy as np
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Upscale small images for better OCR (target min dimension ~1500px)
        min_dim = min(gray.shape[:2])
        if min_dim < 1000:
            scale = 1500 / min_dim
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Contrast stretching for better visibility
        p2, p98 = np.percentile(gray, (2, 98))
        if p98 > p2:
            gray = np.clip((gray - p2) * (255.0 / (p98 - p2)), 0, 255).astype(np.uint8)
        
        # Multi-pass denoising for cleaner text
        denoised = cv2.fastNlMeansDenoising(gray, h=8)
        denoised = cv2.bilateralFilter(denoised, 9, 75, 75)
        
        # CLAHE for local contrast enhancement (higher clip limit for documents)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Unsharp masking for text edge sharpening
        gaussian = cv2.GaussianBlur(enhanced, (0, 0), 3)
        sharpened = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)
        
        # Otsu's thresholding for optimal binary threshold
        # Otsu's thresholding for optimal binary threshold
        _, binary = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphological operations to clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Slight dilation to thicken thin text
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        binary = cv2.dilate(binary, kernel_dilate, iterations=1)
        
        # Convert back to BGR for PaddleOCR
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    
    def _deskew_image(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Automatically deskew tilted documents."""
        import cv2
        import numpy as np
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Threshold to get text regions
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find coordinates of all white pixels (text)
        coords = np.column_stack(np.where(thresh > 0))
        
        if len(coords) < 100:
            return image  # Not enough text to determine angle
        
        # Get rotated rectangle and angle
        angle = cv2.minAreaRect(coords)[-1]
        
        # Correct angle
        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90
        
        # Only correct if angle is significant
        if abs(angle) < 0.5:
            return image
        
        # Rotate image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), 
                                  flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)
        
        logger.debug(f"Deskewed image by {angle:.2f} degrees")
        return rotated
    
    def _enhance_low_quality(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Apply additional enhancements for low quality/noisy images."""
        import cv2
        import numpy as np
        
        # Detect if image is low quality (high noise variance)
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Calculate Laplacian variance (sharpness measure)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        if laplacian_var < 100:  # Low sharpness indicates blur
            # Apply more aggressive sharpening
            kernel = np.array([[-1, -1, -1],
                               [-1, 9, -1],
                               [-1, -1, -1]])
            image = cv2.filter2D(image, -1, kernel)
            logger.debug(f"Applied extra sharpening (Laplacian var: {laplacian_var:.1f})")
        
        return image
    
    def _preprocess_multi_pipeline(self, image: NDArray[np.uint8]) -> list[NDArray[np.uint8]]:
        """
        Generate multiple preprocessed versions for OCR ensemble.
        Returns list of preprocessed images to try.
        """
        import cv2
        
        variants = []
        
        # Pipeline 1: Standard preprocessing
        variants.append(self._preprocess_image(image))
        
        # Pipeline 2: Grayscale only (sometimes works better for high contrast docs)
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        variants.append(gray_bgr)
        
        # Pipeline 3: Adaptive threshold variant
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 11, 2)
        variants.append(cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR))
        
        return variants
    
    def _super_resolution_upscale(self, image: NDArray[np.uint8], target_dpi: int = 300) -> NDArray[np.uint8]:
        """
        Apply super-resolution upscaling for low-resolution images.
        Uses Lanczos interpolation with edge enhancement.
        """
        import cv2
        import numpy as np
        
        h, w = image.shape[:2]
        
        # Estimate current DPI (assume standard scan if unknown)
        estimated_dpi = min(w, h) / 4  # Rough estimate
        
        if estimated_dpi >= target_dpi * 0.8:
            return image  # Already high enough resolution
        
        # Calculate scale factor
        scale = min(target_dpi / max(estimated_dpi, 72), 4.0)  # Max 4x upscale
        
        if scale <= 1.0:
            return image
        
        # Lanczos upscaling (best for document text)
        upscaled = cv2.resize(image, None, fx=scale, fy=scale, 
                              interpolation=cv2.INTER_LANCZOS4)
        
        # Edge-preserving smoothing to reduce interpolation artifacts
        upscaled = cv2.bilateralFilter(upscaled, 5, 75, 75)
        
        # Sharpen after upscaling
        kernel = np.array([[-0.5, -1, -0.5],
                           [-1, 7, -1],
                           [-0.5, -1, -0.5]])
        upscaled = cv2.filter2D(upscaled, -1, kernel)
        
        logger.debug(f"Super-resolution: {w}x{h} -> {upscaled.shape[1]}x{upscaled.shape[0]} (scale={scale:.2f})")
        return upscaled
    
    def _perspective_correction(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """
        Detect and correct perspective distortion in document images.
        Finds document edges and applies perspective transform.
        """
        import cv2
        import numpy as np
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Dilate edges to connect broken lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return image
        
        # Find largest quadrilateral contour
        largest_quad = None
        max_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1000:  # Skip small contours
                continue
            
            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(approx) == 4 and area > max_area:
                # Check if it's a reasonable document shape
                if cv2.isContourConvex(approx):
                    max_area = area
                    largest_quad = approx
        
        if largest_quad is None:
            return image  # No suitable quadrilateral found
        
        # Order points: top-left, top-right, bottom-right, bottom-left
        pts = largest_quad.reshape(4, 2).astype(np.float32)
        rect = np.zeros((4, 2), dtype=np.float32)
        
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # top-left
        rect[2] = pts[np.argmax(s)]  # bottom-right
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right
        rect[3] = pts[np.argmax(diff)]  # bottom-left
        
        # Compute width and height
        width_a = np.linalg.norm(rect[2] - rect[3])
        width_b = np.linalg.norm(rect[1] - rect[0])
        max_width = int(max(width_a, width_b))
        
        height_a = np.linalg.norm(rect[1] - rect[2])
        height_b = np.linalg.norm(rect[0] - rect[3])
        max_height = int(max(height_a, height_b))
        
        # Only apply if distortion is significant
        if max_width < 100 or max_height < 100:
            return image
        
        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype=np.float32)
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (max_width, max_height))
        
        logger.debug(f"Applied perspective correction")
        return warped
    
    def _normalize_background(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """
        Normalize document background to improve text contrast.
        Removes shadows, uneven lighting, and background patterns.
        """
        import cv2
        import numpy as np
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Estimate background using large median filter
        background = cv2.medianBlur(gray, 51)
        
        # Divide original by background to normalize
        normalized = cv2.divide(gray, background, scale=255)
        
        # Apply gamma correction for optimal contrast
        normalized = self._apply_gamma_correction(normalized, gamma=1.2)
        
        if len(image.shape) == 3:
            return cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)
        return normalized
    
    def _apply_gamma_correction(self, image: NDArray[np.uint8], gamma: float = 1.0) -> NDArray[np.uint8]:
        """Apply gamma correction for optimal text visibility."""
        import numpy as np
        
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 
                          for i in range(256)]).astype(np.uint8)
        return cv2.LUT(image, table)
    
    def _ensemble_ocr(self, image: NDArray[np.uint8]) -> tuple[str, float, list]:
        """
        Run OCR with multiple preprocessing pipelines and merge results.
        Uses confidence-weighted voting for best accuracy.
        """
        import cv2
        
        all_results = []
        
        # Apply deskewing first
        deskewed = self._deskew_image(image)
        
        # Generate preprocessing variants
        variants = [
            ("original", deskewed),
            ("preprocessed", self._preprocess_image(deskewed)),
            ("background_norm", self._normalize_background(deskewed)),
        ]
        
        # Check if super-resolution is needed
        if min(deskewed.shape[:2]) < 800:
            upscaled = self._super_resolution_upscale(deskewed)
            variants.append(("super_res", self._preprocess_image(upscaled)))
        
        # Run OCR on each variant
        for name, variant in variants:
            try:
                result = self.ocr.predict(variant)
                if result:
                    # New PaddleOCR API returns OCRResult objects
                    for page_result in result:
                        # Access dict-like OCRResult fields
                        rec_texts = page_result.get('rec_texts', [])
                        rec_scores = page_result.get('rec_scores', [])
                        rec_polys = page_result.get('rec_polys', page_result.get('dt_polys', []))
                        
                        for i, text in enumerate(rec_texts):
                            if text and i < len(rec_scores):
                                conf = float(rec_scores[i])
                                bbox = rec_polys[i].tolist() if i < len(rec_polys) else []
                                all_results.append((bbox, text, conf, name))
            except Exception as e:
                logger.warning(f"OCR variant '{name}' failed: {e}")
        
        # Merge results using confidence-weighted voting
        merged_text, avg_confidence, final_detections = self._merge_ocr_results(all_results)
        
        return merged_text, avg_confidence, final_detections
    
    def _merge_ocr_results(self, all_results: list) -> tuple[str, float, list]:
        """
        Merge OCR results from multiple pipelines using confidence weighting.
        """
        if not all_results:
            return "", 0.0, []
        
        # Group by approximate position
        groups = {}
        for bbox, text, conf, source in all_results:
            # Use center point for grouping
            if isinstance(bbox, list) and len(bbox) >= 4:
                center_x = sum(p[0] for p in bbox) / len(bbox)
                center_y = sum(p[1] for p in bbox) / len(bbox)
            else:
                center_x, center_y = 0, 0
            
            key = (int(center_x // 30), int(center_y // 30))
            
            if key not in groups:
                groups[key] = []
            groups[key].append((bbox, text, conf, source))
        
        # Select best result from each group
        final_detections = []
        for key in sorted(groups.keys(), key=lambda k: (k[1], k[0])):
            group = groups[key]
            
            # Use confidence-weighted voting for text
            text_votes = {}
            for bbox, text, conf, source in group:
                # Normalize text for comparison
                norm_text = text.strip()
                if norm_text not in text_votes:
                    text_votes[norm_text] = {'conf_sum': 0, 'count': 0, 'bbox': bbox, 'best_conf': 0}
                text_votes[norm_text]['conf_sum'] += conf
                text_votes[norm_text]['count'] += 1
                if conf > text_votes[norm_text]['best_conf']:
                    text_votes[norm_text]['best_conf'] = conf
                    text_votes[norm_text]['bbox'] = bbox
            
            # Select text with highest weighted score
            best_text = max(text_votes.items(), 
                           key=lambda x: x[1]['conf_sum'] / x[1]['count'] * (1 + 0.1 * x[1]['count']))
            
            final_detections.append((
                best_text[1]['bbox'],
                best_text[0],
                best_text[1]['best_conf']
            ))
        
        # Build final text
        texts = [d[1] for d in final_detections]
        merged_text = " ".join(texts)
        
        # Calculate weighted average confidence
        if final_detections:
            total_conf = sum(d[2] for d in final_detections)
            avg_conf = total_conf / len(final_detections)
        else:
            avg_conf = 0.0
        
        return merged_text, avg_conf, final_detections
    
    def _deduplicate_detections(self, detections: list[tuple]) -> list[tuple]:
        """Remove duplicate detections from multi-scale processing."""
        if not detections:
            return []
        
        # Group detections by approximate position
        groups = {}
        for bbox, text, conf in detections:
            # Use center point as key
            center_x = sum(x for x, y in bbox) // 4
            center_y = sum(y for x, y in bbox) // 4
            # Round to nearest 20 pixels for grouping
            key = (center_x // 20, center_y // 20)
            
            if key not in groups:
                groups[key] = []
            groups[key].append((bbox, text, conf))
        
        # Keep highest confidence from each group
        unique = []
        for group in groups.values():
            best = max(group, key=lambda x: x[2])  # Sort by confidence
            unique.append(best)
        
        return unique

    def _extract_mrz_zone(self, image: NDArray[np.uint8], doc_type: str | None = None) -> str | None:
        """
        Extract and parse MRZ (Machine Readable Zone) from passport/ID images.
        
        For passport documents, crops the bottom 20% and uses specialized
        preprocessing for OCR-B font recognition.
        
        Args:
            image: Input image
            doc_type: Document type from classification (e.g., "passport")
            
        Returns:
            Parsed MRZ text if successful, None otherwise
        """
        # Only apply for passport-type documents
        if doc_type and doc_type.lower() not in ["passport", "travel_document", "id_card"]:
            return None
        
        try:
            h, w = image.shape[:2]
            
            # Crop bottom 20% for MRZ zone (typical passport layout)
            mrz_region = image[int(h * 0.80):, :]
            
            # Preprocess for OCR-B font (MRZ standard font)
            if len(mrz_region.shape) == 3:
                gray = cv2.cvtColor(mrz_region, cv2.COLOR_BGR2GRAY)
            else:
                gray = mrz_region.copy()
            
            # Apply Otsu's thresholding for optimal binary threshold
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert back to BGR for PaddleOCR
            binary_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
            
            # Run OCR on MRZ region
            result = self.ocr.ocr(binary_bgr, cls=True)
            
            if not result or not result[0]:
                return None
            
            # Combine detected lines
            mrz_lines = []
            for line in result[0]:
                text = line[1][0] if line[1] else ""
                # MRZ characters are uppercase with < as filler
                cleaned = text.upper().replace(" ", "<")
                # MRZ lines are typically 30+ chars for passports (TD3), 30 chars for ID (TD1)
                if len(cleaned) >= 28:
                    mrz_lines.append(cleaned)
            
            if len(mrz_lines) >= 2:
                mrz_text = "\n".join(mrz_lines[:2])
                logger.info(f"Extracted MRZ: {mrz_text[:40]}...")
                return mrz_text
            
            return None
            
        except Exception as e:
            logger.debug(f"MRZ extraction failed: {e}")
            return None


    def process_image(
        self,
        image: NDArray[np.uint8],
        page_number: int = 1,
        scientific_mode: bool = False,
    ) -> OCRPageResult:
        """
        Process a single image and extract text.
        
        Args:
            image: Image as numpy array (BGR format)
            page_number: Page number for multi-page documents
            scientific_mode: Whether to enable math/equation extraction
            
        Returns:
            OCRPageResult with all detections
        """
        logger.debug(f"Processing image, shape: {image.shape}")

        # 1. Run Ensemble OCR (Professional Grade)
        # This includes Deskewing, Super-Resolution (if needed), Multi-pipeline voting
        raw_text, avg_confidence, internal_detections = self._ensemble_ocr(image)
        
        # Convert internal detections (tuples) to OCRDetection objects
        detections = []
        for det in internal_detections:
            # det format: (bbox, text, conf, source)
            # Default OCRDetection logic expects box, text, confidence
            if len(det) >= 3:
                detections.append(OCRDetection(
                    bounding_box=det[0],
                    text=det[1],
                    confidence=det[2]
                ))

        # 2. Run Math Extraction if enabled (Phase C)
        latex_text = ""
        if scientific_mode:
            try:
                math_regions = self.math_service.extract_math(image)
                if math_regions:
                    # Append equations to the text output
                    # In a full implementation, we would merge them spatially
                    latex_text = "\n\n### Extracted Equations (Scientific Mode) ###\n"
                    for reg in math_regions:
                        latex_text += f"\n$$ {reg.latex} $$\n"
                    
                    # Also append to raw text for now so it appears in standard views
                    raw_text += latex_text
            except Exception as e:
                logger.error(f"Math extraction failed: {e}")

        # 3. Format Layout
        sorted_detections = self._sort_detections(detections)
        formatted_text = self._format_text_with_layout(sorted_detections)
        final_text = formatted_text if formatted_text.strip() else raw_text
        
        # If we had math, ensure it's attached to final text too if simpler
        if latex_text and latex_text not in final_text:
            final_text += latex_text

        return OCRPageResult(
            page_number=page_number,
            detections=sorted_detections,
            raw_text=final_text,
            average_confidence=avg_confidence,
            latex_text=latex_text,
        )

    def process_images(
        self,
        images: list[NDArray[np.uint8]],
        scientific_mode: bool = False,
    ) -> list[OCRPageResult]:
        """
        Process multiple images (e.g., pages of a document).
        
        Args:
            images: List of images as numpy arrays
            scientific_mode: Whether to enable scientific/math mode extraction
            
        Returns:
            List of OCRPageResult for each page
        """
        results = []
        for i, image in enumerate(images, start=1):
            # Pass scientific_mode to process_image
            result = self.process_image(image, page_number=i, scientific_mode=scientific_mode)
            results.append(result)
            logger.info(f"Processed page {i}/{len(images)}, confidence: {result.average_confidence:.2%}")
        
        return results

    def process_file(
        self,
        file_path: str | Path,
        scientific_mode: bool = False,
    ) -> list[OCRPageResult]:
        """
        Process a file (image or PDF) and extract text.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of OCRPageResult for each page
        """
        import cv2
        from src.services.preprocessing import (
            ImagePreprocessor,
            PDFConverter,
        )

        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine file type and convert to images
        suffix = file_path.suffix.lower()
        
        if suffix == ".pdf":
            converter = PDFConverter()
            images = converter.convert_to_images(file_path)
        elif suffix in {".png", ".jpg", ".jpeg", ".tiff", ".tif"}:
            image = cv2.imread(str(file_path))
            if image is None:
                raise ValueError(f"Could not read image: {file_path}")
            images = [image]
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        # Preprocess images
        preprocessor = ImagePreprocessor()
        processed_images = []
        
        for img in images:
            processed = preprocessor.preprocess(
                img,
                apply_grayscale=False,  # Keep color for better recognition
                apply_denoise=True,
                apply_binarize=False,  # PaddleOCR handles this internally
                apply_deskew=True,
            )
            processed_images.append(processed)

        # Process with OCR
        return self.process_images(processed_images, scientific_mode=scientific_mode)

    def _sort_detections(
        self,
        detections: list[OCRDetection],
    ) -> list[OCRDetection]:
        """
        Sort detections by reading order (top to bottom, left to right).
        
        Args:
            detections: List of OCR detections
            
        Returns:
            Sorted list of detections
        """
        if not detections:
            return detections

        def get_center(detection: OCRDetection) -> tuple[float, float]:
            """Get center point of bounding box."""
            bbox = detection.bounding_box
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            return (sum(x_coords) / 4, sum(y_coords) / 4)

        # Sort by y-coordinate (top to bottom), then by x-coordinate (left to right)
        # Use a tolerance for y-coordinate to group lines
        line_tolerance = 15  # pixels - tighter grouping for better line detection

        def sort_key(detection: OCRDetection) -> tuple[int, float]:
            x, y = get_center(detection)
            # Group into lines by y-coordinate
            line_group = int(y / line_tolerance)
            return (line_group, x)

        return sorted(detections, key=sort_key)
    
    def _format_text_with_layout(self, detections: list[OCRDetection]) -> str:
        """
        Format extracted text preserving document layout.
        Detects paragraphs, line breaks, indentation, and columns.
        """
        if not detections:
            return ""
        
        # Group detections into lines
        lines = self._group_into_lines(detections)
        
        # Format lines with proper spacing and structure
        formatted_lines = []
        prev_line_bottom = None
        prev_indent = 0
        
        for line_detections in lines:
            if not line_detections:
                continue
            
            # Calculate line metrics
            line_text = " ".join(d.text for d in line_detections)
            line_top = min(d.bounding_box[0][1] for d in line_detections)
            line_bottom = max(d.bounding_box[2][1] for d in line_detections)
            line_left = min(d.bounding_box[0][0] for d in line_detections)
            line_height = line_bottom - line_top
            
            # Detect indentation (relative to first line)
            if not formatted_lines:
                base_indent = line_left
                indent_level = 0
            else:
                indent_diff = line_left - base_indent
                indent_level = max(0, int(indent_diff / 40))  # ~40px per indent level
            
            # Detect paragraph breaks (larger vertical gap)
            if prev_line_bottom is not None:
                vertical_gap = line_top - prev_line_bottom
                gap_threshold = line_height * 1.5  # 1.5x line height = new paragraph
                
                if vertical_gap > gap_threshold:
                    formatted_lines.append("")  # Add blank line for paragraph break
            
            # Add indentation
            indented_text = ("  " * indent_level) + line_text
            formatted_lines.append(indented_text)
            
            prev_line_bottom = line_bottom
            prev_indent = indent_level
        
        return "\n".join(formatted_lines)
    
    def _group_into_lines(self, detections: list[OCRDetection]) -> list[list[OCRDetection]]:
        """
        Group text detections into lines based on vertical position with dynamic threshold.
        """
        if not detections:
            return []
        
        # Calculate average height for adaptive threshold
        avg_height = sum(
            abs(d.bounding_box[2][1] - d.bounding_box[0][1])
            for d in detections
        ) / len(detections) if detections else 20
        
        # Use dynamic threshold: at least 15px or half the average height
        line_tolerance = max(15, avg_height * 0.5)
        
        lines = []
        current_line = []
        
        for detection in detections:
            if not current_line:
                current_line.append(detection)
                continue
            
            # Get vertical centers
            curr_y = sum(p[1] for p in detection.bounding_box) / 4
            prev_y = sum(p[1] for p in current_line[-1].bounding_box) / 4
            
            # Check if same line
            if abs(curr_y - prev_y) <= line_tolerance:
                current_line.append(detection)
            else:
                # Start new line
                lines.append(current_line)
                current_line = [detection]
        
        # Add last line
        if current_line:
            lines.append(current_line)
        
        return lines

    def get_text_with_boxes(
        self,
        image: NDArray[np.uint8],
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Get raw text and bounding box information.
        
        Args:
            image: Input image
            
        Returns:
            Tuple of (raw_text, list of box info dicts)
        """
        result = self.process_image(image)
        
        boxes = []
        for detection in result.detections:
            boxes.append({
                "text": detection.text,
                "confidence": detection.confidence,
                "box": detection.bounding_box,
            })
        
        return result.raw_text, boxes


def process_document_ocr(
    file_path: str | Path,
    language: str = "en",
    confidence_threshold: float = 0.6,
    scientific_mode: bool = True,
) -> dict[str, Any]:
    """
    Convenience function to process a document with OCR.
    
    Args:
        file_path: Path to document file
        language: OCR language
        confidence_threshold: Minimum confidence to flag for review
        
    Returns:
        Dictionary with OCR results and metadata
    """
    ocr_service = OCRService(language=language)
    results = ocr_service.process_file(file_path, scientific_mode=scientific_mode)
    
    # Combine all pages
    all_text = "\n\n".join(r.raw_text for r in results)
    all_detections = []
    
    for result in results:
        for detection in result.detections:
            all_detections.append({
                "page": result.page_number,
                **detection.to_dict(),
            })
    
    # Calculate overall confidence
    avg_confidence = 0.0
    if results:
        avg_confidence = sum(r.average_confidence for r in results) / len(results)
    
    needs_review = avg_confidence < confidence_threshold
    
    return {
        "raw_text": all_text,
        "page_count": len(results),
        "detections": all_detections,
        "average_confidence": avg_confidence,
        "needs_review": needs_review,
        "page_results": [r.to_dict() for r in results],
    }
