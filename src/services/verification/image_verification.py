"""OCR Verification Services - Image Reconstruction & Comparison."""

import logging
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageDraw, ImageFont
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of image verification."""
    ssim_score: float  # 0-1, higher is better
    pixel_match_percent: float  # 0-100
    text_region_match: float  # 0-100, focused on text areas
    diff_image: NDArray[np.uint8] | None  # Visual diff heatmap
    reconstructed_image: NDArray[np.uint8] | None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "ssim_score": round(self.ssim_score, 4),
            "pixel_match_percent": round(self.pixel_match_percent, 2),
            "text_region_match": round(self.text_region_match, 2),
            "overall_match": round(
                (self.ssim_score * 100 + self.pixel_match_percent + self.text_region_match) / 3, 2
            ),
        }


class ImageReconstructionService:
    """Reconstructs images from OCR metadata."""
    
    def __init__(self):
        self.default_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        self.fallback_font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    
    def reconstruct(
        self,
        original_shape: tuple[int, int, int],
        detections: list[dict[str, Any]],
        background_color: tuple[int, int, int] = (255, 255, 255),
        original_image: NDArray[np.uint8] | None = None,
    ) -> NDArray[np.uint8]:
        """
        Reconstruct image from OCR detections.
        
        Args:
            original_shape: (height, width, channels) of original image
            detections: List of OCR detections with bounding_box and text
            background_color: Background color for the canvas
            original_image: Original image for color sampling
            
        Returns:
            Reconstructed image as numpy array
        """
        height, width = original_shape[:2]
        channels = original_shape[2] if len(original_shape) > 2 else 3
        
        # Super-sampling factor for smoother text (antialiasing)
        scale = 3
        s_width, s_height = width * scale, height * scale
        
        # Super-sampling factor for smoother text (antialiasing)
        scale = 3
        s_width, s_height = width * scale, height * scale
        
        # Smart Ghosting: Use faded original as background for alignment verification
        if original_image is not None:
            # Convert original to PIL and resize to super-sampled size
            orig_pil = Image.fromarray(cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB))
            base_image = orig_pil.resize((s_width, s_height), Image.Resampling.LANCZOS)
            base_image = base_image.convert("RGBA")
            # Apply transparency (ghosted effect)
            base_image.putalpha(110)
            # Create final canvas with white background + ghosted overlay
            img = Image.new("RGBA", (s_width, s_height), (255, 255, 255, 255))
            img.alpha_composite(base_image)
        else:
            # Fallback to plain background
            img = Image.new("RGBA", (s_width, s_height), background_color + (255,))
        draw = ImageDraw.Draw(img)
        
        # --- Spatial NMS with Proximity Awareness ---
        # Only remove duplicates if they have BOTH similar text AND close proximity
        # This preserves legitimate instances of same text in different locations
        
        # Validate and clean detections input
        valid_detections = []
        for det in detections:
            # Skip if not a dict
            if not isinstance(det, dict):
                continue
            # Must have at least text field
            if not det.get("text"):
                continue
            # Must have some kind of bounding box
            bbox = det.get("bounding_box") or det.get("box")
            if not bbox or not isinstance(bbox, list) or len(bbox) < 4:
                continue
            valid_detections.append(det)
        
        if len(valid_detections) == 0:
            logger.warning("No valid detections found after filtering")
            # Return blank white image in numpy array format
            blank = Image.new("RGB", (width, height), (255, 255, 255))
            return np.array(blank)
        
        detections = valid_detections
        
        def get_conf(d): return d.get("confidence", 0)
        detections_conf_sorted = sorted(detections, key=get_conf, reverse=True)
        
        accepted_detections = []
        
        # Levenshtein distance helper for text similarity
        def levenshtein_ratio(s1, s2):
            if not s1 or not s2: return 0.0
            rows = len(s1)+1
            cols = len(s2)+1
            dist = [[0 for x in range(cols)] for x in range(rows)]
            for i in range(1, rows): dist[i][0] = i
            for i in range(1, cols): dist[0][i] = i
            for col in range(1, cols):
                for row in range(1, rows):
                    cost = 0 if s1[row-1] == s2[col-1] else 1
                    dist[row][col] = min(dist[row-1][col] + 1,      # deletion
                                         dist[row][col-1] + 1,      # insertion
                                         dist[row-1][col-1] + cost) # substitution
            max_len = max(len(s1), len(s2))
            return 1 - (dist[rows-1][cols-1] / max_len)

        for cand in detections_conf_sorted:
            cand_bbox = cand.get("bounding_box") or cand.get("box")
            cand_text = cand.get("text", "").strip().lower()
            if not cand_bbox or not isinstance(cand_bbox, list) or len(cand_bbox) < 4:
                continue
                
            # Calc Candidate Geometry
            xs = [p[0] for p in cand_bbox]
            ys = [p[1] for p in cand_bbox]
            cand_area = (max(xs) - min(xs)) * (max(ys) - min(ys))
            if cand_area <= 0: continue
            
            cand_cx = sum(xs) / len(xs)
            cand_cy = sum(ys) / len(ys)
            
            is_bad = False
            for kept in accepted_detections:
                kept_bbox = kept.get("bounding_box") or kept.get("box")
                kept_text = kept.get("text", "").strip().lower()
                
                k_xs = [p[0] for p in kept_bbox]
                k_ys = [p[1] for p in kept_bbox]
                kept_area = (max(k_xs) - min(k_xs)) * (max(k_ys) - min(k_ys))
                
                k_cx = sum(k_xs) / len(k_xs)
                k_cy = sum(k_ys) / len(k_ys)
                
                # Calculate spatial distance between centers
                distance = ((cand_cx - k_cx)**2 + (cand_cy - k_cy)**2)**0.5
                
                # Intersection for IoU
                inter_x1 = max(min(xs), min(k_xs))
                inter_y1 = max(min(ys), min(k_ys))
                inter_x2 = min(max(xs), max(k_xs))
                inter_y2 = min(max(ys), max(k_ys))
                
                has_intersection = inter_x2 > inter_x1 and inter_y2 > inter_y1
                
                if has_intersection:
                    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                    union_area = cand_area + kept_area - inter_area
                    iou = inter_area / union_area if union_area > 0 else 0
                else:
                    iou = 0
                    inter_area = 0
                
                # Text similarity
                text_sim = levenshtein_ratio(cand_text, kept_text)
                
                # RULE 1: Text Duplicate (only if spatially close)
                # Remove if text is very similar (>90%) AND boxes are close (distance < 50 OR any overlap)
                if text_sim > 0.90 and (distance < 50 or iou > 0.01):
                    is_bad = True
                    break
                
                # RULE 2: Geometric Overlap (significant IoU regardless of text)
                # Remove if boxes overlap significantly (>20% IoU)
                if iou > 0.20:
                    is_bad = True
                    break
                
                # RULE 3: Containment (watermark removal)
                # If candidate CONTAINS kept box (intersection ~= kept area)
                if has_intersection and inter_area / kept_area > 0.80:
                    is_bad = True
                    break
                    
                # RULE 4: Inside (noise removal)
                # If candidate is INSIDE kept box (intersection ~= cand area)
                if has_intersection and inter_area / cand_area > 0.80:
                    is_bad = True
                    break
            
            if not is_bad:
                accepted_detections.append(cand)

        # Re-sort accepted detections by Area (Z-Order) for drawing
        # Background first (if any large ones survived), Foreground last
        def get_detection_area(det):
            bbox = det.get("bounding_box") or det.get("box")
            if isinstance(bbox, list) and len(bbox) >= 4:
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                return (max(xs) - min(xs)) * (max(ys) - min(ys))
            return 0
            
        detections_drawing_order = sorted(accepted_detections, key=get_detection_area, reverse=True)
        
        # --- Enhanced Watermark Detection ---
        # Identify and filter watermarks using multiple heuristics
        def is_likely_watermark(det, img_width, img_height):
            """Detect watermarks using combined heuristics"""
            bbox = det.get("bounding_box") or det.get("box")
            if not bbox or len(bbox) < 4:
                return False
                
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
            area = width * height
            conf = det.get("confidence", 1.0)
            text = det.get("text", "").strip()
            
            # Heuristic 1: Very large area + low confidence
            if area > 20000 and conf < 0.85:
                return True
            
            # Heuristic 2: Large area + very low confidence
            if area > 10000 and conf < 0.70:
                return True
                
            # Heuristic 3: Low text density (few characters for large area)
            if area > 5000 and len(text) < 5:
                return True
            
            # Heuristic 4: Centered large text (typical watermark position)
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            center_ratio_x = abs(cx - img_width/2) / (img_width/2)
            center_ratio_y = abs(cy - img_height/2) / (img_height/2)
            if area > 15000 and conf < 0.90 and center_ratio_x < 0.3 and center_ratio_y < 0.3:
                return True
                
            return False
        
        # Filter out watermarks
        non_watermark_detections = []
        for det in detections_drawing_order:
            if not is_likely_watermark(det, width, height):
                non_watermark_detections.append(det)
        
        detections_drawing_order = non_watermark_detections
        
        # --- Dynamic Per-Box Font Sizing ---
        # Font size is calculated individually for each text box based on its height
        # This ensures headers get large fonts and labels get small fonts
        
        for det in detections_drawing_order:
            text = det.get("text", "")
            bbox = det.get("bounding_box") or det.get("box")
            
            if not text or not bbox:
                continue
            
            try:
                # 1. Parse Bounding Box
                if isinstance(bbox, list) and len(bbox) >= 4:
                    # Polygon format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    # Determine orientation
                    x_coords = [p[0] for p in bbox]
                    y_coords = [p[1] for p in bbox]
                    # Scaled coordinates for drawing
                    scaled_bbox = [[p[0] * scale, p[1] * scale] for p in bbox]
                    s_x = [p[0] for p in scaled_bbox]
                    s_y = [p[1] for p in scaled_bbox]
                    s_min_x, s_min_y = min(s_x), min(s_y)
                    s_box_w = max(s_x) - s_min_x
                    s_box_h = max(s_y) - s_min_y
                    
                    is_vertical = s_box_h > s_box_w * 1.5
                    
                    # Unscaled crop coordinates for color sampling
                    oy1, oy2 = max(0, int(min(y_coords))), min(height, int(max(y_coords)))
                    ox1, ox2 = max(0, int(min(x_coords))), min(width, int(max(x_coords)))
                    
                else:
                    continue
                
                # 2. Extract Style Info (Color & Boldness)
                fill_color = (0, 0, 0)
                is_bold = False
                
                if original_image is not None and oy2 > oy1 and ox2 > ox1:
                    crop = original_image[oy1:oy2, ox1:ox2]
                    if crop.size > 0:
                        # Color: simple dominant dark color
                        reshaped = crop.reshape(-1, 3)
                        # Assume text is darker than background (typical for documents)
                        # Get pixels with luminance < 180 (heuristic)
                        if channels == 3:
                            lum = 0.299*reshaped[:,2] + 0.587*reshaped[:,1] + 0.114*reshaped[:,0]
                            dark_mask = lum < 180
                            if dark_mask.any():
                                mean_color = reshaped[dark_mask].mean(axis=0)
                                # OpenCV BGR -> PIL RGB
                                fill_color = (int(mean_color[2]), int(mean_color[1]), int(mean_color[0]))
                            
                            # Boldness: High pixel density of dark pixels?
                            # Density = dark_pixels / total_pixels
                            density = np.count_nonzero(dark_mask) / len(dark_mask) if len(dark_mask) > 0 else 0
                            # Heuristic: Density > 0.35 implies thick/bold font for text regions
                            if density > 0.35:
                                is_bold = True
                
                # Determine opacity
                alpha = 255
                det_area = s_box_w * s_box_h
                conf = det.get("confidence", 1.0)
                # Keep watermark logic just in case, though NMS helps
                if det_area > (15000 * scale * scale) and conf < 0.85:
                    alpha = 40 
                elif det_area > (15000 * scale * scale):
                    alpha = 255
                    
                # 3. DYNAMIC PER-BOX FONT SIZING
                # Calculate font size based on THIS box's height (not global median)
                box_height = s_box_h  # Already scaled
                font_size = int(box_height * 0.8)  # 80% of box height
                if font_size < 10:
                    font_size = 10  # Minimum readable size
                if font_size > 200:
                    font_size = 200  # Sanity cap for huge boxes
                
                # Load font for this specific size
                current_font = self._get_font(font_size, is_bold)
                
                # Width Fitting: Shrink font if text overflows box width
                if is_vertical:
                    constraint = s_box_h  # For vertical text, height is the "width"
                else:
                    constraint = s_box_w
                
                text_len = draw.textlength(text, font=current_font)
                while text_len > constraint * 0.95 and font_size > 8:
                    font_size -= 1
                    current_font = self._get_font(font_size, is_bold)
                    text_len = draw.textlength(text, font=current_font)
                
                if is_vertical:
                    # Create temporary image for text
                    text_bbox = draw.textbbox((0, 0), text, font=current_font)
                    tw, th = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
                    
                    txt_img = Image.new('RGBA', (tw + 10, th + 10), (0,0,0,0))
                    txt_draw = ImageDraw.Draw(txt_img)
                    txt_draw.text((0, 0), text, font=current_font, fill=fill_color + (alpha,))
                    
                    rotated = txt_img.rotate(90, expand=True)
                    
                    # Center in box
                    rw, rh = rotated.size
                    paste_x = int(s_min_x + (s_box_w - rw) / 2)
                    paste_y = int(s_min_y + (s_box_h - rh) / 2)
                    
                    img.paste(rotated, (paste_x, paste_y), rotated)
                    
                else:
                    # Standard horizontal draw
                    text_bbox = draw.textbbox((0, 0), text, font=safety_font)
                    th = text_bbox[3] - text_bbox[1]
                    tw = text_bbox[2] - text_bbox[0]
                    
                    # Center vertically, left align horizontally
                    text_x = s_min_x + 2  # Small padding
                    text_y = s_min_y + (s_box_h - th) / 2
                    
                    draw.text((text_x, text_y), text, font=safety_font, fill=fill_color)
            
            except Exception as e:
                logger.debug(f"Failed to render text '{text[:20]}...': {e}")
                continue
        
        # Downsample to original size with high-quality resampling
        final_img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        # Convert PIL Image to numpy array for consistency
        final_array = np.array(final_img)
        # Convert RGBA to BGR if needed (standard OpenCV format)
        if final_array.shape[2] == 4:  # RGBA
            final_array = cv2.cvtColor(final_array, cv2.COLOR_RGBA2BGR)
        elif final_array.shape[2] == 3:  # RGB
            final_array = cv2.cvtColor(final_array, cv2.COLOR_RGB2BGR)
        
        return final_array
    
    def _get_font(self, size: int, is_bold: bool = False) -> ImageFont.FreeTypeFont:
        """Get font with fallback, supporting bold weight."""
        fonts_to_try = []
        
        if is_bold:
            fonts_to_try.extend([
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            ])
        else:
            fonts_to_try.extend([
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            ])
            
        # Add fallbacks
        fonts_to_try.append(self.default_font_path)
        
        for font_path in fonts_to_try:
            try:
                return ImageFont.truetype(font_path, size)
            except OSError:
                continue
                
        # Last resort
        return ImageFont.load_default()


class ImageComparisonService:
    """Compares original and reconstructed images."""
    
    def compare(
        self,
        original: NDArray[np.uint8],
        reconstructed: NDArray[np.uint8],
        text_mask: NDArray[np.uint8] | None = None,
    ) -> VerificationResult:
        """
        Compare original and reconstructed images.
        
        Args:
            original: Original image
            reconstructed: Reconstructed image from OCR
            text_mask: Optional mask highlighting text regions
            
        Returns:
            VerificationResult with metrics and diff visualization
        """
        # Ensure same size
        if original.shape[:2] != reconstructed.shape[:2]:
            reconstructed = cv2.resize(
                reconstructed, 
                (original.shape[1], original.shape[0])
            )
        
        # Convert to grayscale for comparison
        if len(original.shape) == 3:
            orig_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        else:
            orig_gray = original
            
        if len(reconstructed.shape) == 3:
            recon_gray = cv2.cvtColor(reconstructed, cv2.COLOR_BGR2GRAY)
        else:
            recon_gray = reconstructed
        
        # 1. SSIM Score
        ssim_score, ssim_diff = ssim(
            orig_gray, recon_gray, 
            full=True,
            data_range=255
        )
        
        # 2. Pixel Match Percentage
        # Threshold difference to binary
        diff = cv2.absdiff(orig_gray, recon_gray)
        _, thresh_diff = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        total_pixels = orig_gray.size
        matching_pixels = total_pixels - np.count_nonzero(thresh_diff)
        pixel_match = (matching_pixels / total_pixels) * 100
        
        # 3. Text Region Match
        # Create text mask from original if not provided
        if text_mask is None:
            text_mask = self._create_text_mask(orig_gray)
        
        masked_diff = cv2.bitwise_and(diff, diff, mask=text_mask)
        text_pixels = np.count_nonzero(text_mask)
        if text_pixels > 0:
            text_diff_pixels = np.count_nonzero(masked_diff > 30)
            text_region_match = ((text_pixels - text_diff_pixels) / text_pixels) * 100
        else:
            text_region_match = 100.0
        
        # 4. Create diff heatmap
        diff_heatmap = self._create_diff_heatmap(diff, original.shape)
        
        return VerificationResult(
            ssim_score=float(ssim_score),
            pixel_match_percent=float(pixel_match),
            text_region_match=float(text_region_match),
            diff_image=diff_heatmap,
            reconstructed_image=reconstructed,
        )
    
    def _create_text_mask(self, gray_image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Create mask highlighting potential text regions."""
        # Adaptive thresholding to find text
        binary = cv2.adaptiveThreshold(
            gray_image, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )
        
        # Dilate to connect text regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(binary, kernel, iterations=2)
        
        return dilated
    
    def _create_diff_heatmap(
        self, 
        diff: NDArray[np.uint8],
        original_shape: tuple,
    ) -> NDArray[np.uint8]:
        """Create colorful heatmap of differences."""
        # Normalize diff
        diff_normalized = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
        
        # Apply colormap (red = different, blue = same)
        heatmap = cv2.applyColorMap(diff_normalized.astype(np.uint8), cv2.COLORMAP_JET)
        
        return heatmap


class OCRVerificationService:
    """Combines reconstruction and comparison for end-to-end verification."""
    
    def __init__(self):
        self.reconstruction = ImageReconstructionService()
        self.comparison = ImageComparisonService()
    
    def verify(
        self,
        original_image: NDArray[np.uint8],
        ocr_detections: list[dict[str, Any]],
    ) -> VerificationResult:
        """
        Perform full round-trip OCR verification.
        
        Args:
            original_image: The original image
            ocr_detections: OCR results with text and bounding boxes
            
        Returns:
            VerificationResult with all metrics
        """
        logger.info(f"Starting verification with {len(ocr_detections)} detections")
        
        # Step 1: Reconstruct image from OCR data
        reconstructed = self.reconstruction.reconstruct(
            original_shape=original_image.shape,
            detections=ocr_detections,
            original_image=original_image,
        )
        
        # Step 2: Compare images
        result = self.comparison.compare(
            original=original_image,
            reconstructed=reconstructed,
        )
        
        logger.info(f"Verification complete: SSIM={result.ssim_score:.3f}, "
                   f"Pixel={result.pixel_match_percent:.1f}%, "
                   f"Text={result.text_region_match:.1f}%")
        
        return result
    
    def verify_and_improve(
        self,
        original_image: NDArray[np.uint8],
        ocr_detections: list[dict[str, Any]],
        target_match: float = 95.0,
        max_iterations: int = 3,
    ) -> tuple[VerificationResult, list[dict[str, Any]]]:
        """
        Iteratively verify and attempt to improve OCR results.
        
        Returns:
            Tuple of (final result, potentially improved detections)
        """
        current_detections = ocr_detections.copy()
        best_result = None
        
        for iteration in range(max_iterations):
            result = self.verify(original_image, current_detections)
            
            if best_result is None or result.text_region_match > best_result.text_region_match:
                best_result = result
            
            overall = (result.ssim_score * 100 + 
                      result.pixel_match_percent + 
                      result.text_region_match) / 3
            
            if overall >= target_match:
                logger.info(f"Target match achieved at iteration {iteration + 1}")
                break
            
            # Analyze and potentially correct problem areas
            # (Future: implement intelligent correction based on diff analysis)
            
        return best_result, current_detections
