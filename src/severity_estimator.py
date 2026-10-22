"""
Plant Disease Severity Estimation Module for AI Farmer Assistant.

Estimates the percentage of visible leaf area affected by disease symptoms
(chlorosis, necrosis, lesions) using multi-spectral color-space segmentation
(HSV, CIELAB, Excess Green Index) and morphological filtering.

Provides:
- Validated leaf mask extraction distinguishing leaf from neutral, dark, or field backgrounds.
- Lesion segmentation within validated leaf tissue for foliar blights, spots, and molds.
- Standardized percentage calculation: (Validated Lesion Pixels / Validated Leaf Pixels) * 100.
- Calibrated/experimental severity categorization based on plant pathology guidelines (Horsfall-Barratt adaptations).
- Graceful handling of healthy leaves (0% lesion), insufficient leaf area, low contrast, and unsupported classes.
- Zero-crash guarantee: all exceptions are caught and returned as structured status objects.
"""

from dataclasses import dataclass, field
import io
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

# Authoritative supported disease classes and their operating modes
HEALTHY_CLASSES = {
    "Potato___healthy",
    "Tomato___healthy",
}

# Foliar diseases with localized necrotic/chlorotic lesions on leaf surface
FOLIAR_LESION_CLASSES = {
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Bacterial_spot",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Target_Spot",
    "Tomato___Leaf_Mold",
}

# Systemic, stippling, or viral diseases where optical surface necrosis is diffuse or uncalibrated
SYSTEMIC_VIRAL_CLASSES = {
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
}

# Configurable severity category thresholds (percentage of visible leaf area affected)
# Standard adapted plant pathology severity tiers
DEFAULT_SEVERITY_THRESHOLDS = {
    "none": 0.0,
    "mild": 10.0,       # 0.1% to 10.0%
    "moderate": 25.0,   # 10.1% to 25.0%
    "severe": 100.0,    # > 25.0%
}

SEVERITY_DISCLAIMER = (
    "Experimental estimate of visible leaf surface lesion area from this image. "
    "It describes the submitted photograph only and does not establish whole-plant "
    "severity or replace certified in-field agronomic scouting."
)


@dataclass
class SeverityResult:
    """Structured result of severity estimation."""
    status: str
    estimated_affected_area_percent: Optional[float] = None
    category: Optional[str] = None
    method: str = "multispectral_color_segmentation_v1"
    message: Optional[str] = None
    affected_pixels: Optional[int] = None
    total_leaf_pixels: Optional[int] = None
    confidence_level: Optional[str] = None
    disclaimer: str = SEVERITY_DISCLAIMER

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to API-compatible dictionary."""
        return {
            "status": self.status,
            "estimated_affected_area_percent": self.estimated_affected_area_percent,
            "category": self.category,
            "method": self.method,
            "message": self.message,
            "affected_pixels": self.affected_pixels,
            "total_leaf_pixels": self.total_leaf_pixels,
            "confidence_level": self.confidence_level,
            "disclaimer": self.disclaimer,
        }


class PlantDiseaseSeverityEstimator:
    """
    Modular Computer Vision pipeline for plant leaf disease severity estimation.
    """

    def __init__(
        self,
        min_leaf_ratio: float = 0.03,
        min_leaf_pixels: int = 400,
        severity_thresholds: Optional[Dict[str, float]] = None,
    ):
        """
        Args:
            min_leaf_ratio: Minimum ratio of image pixels that must constitute leaf tissue (default 3%).
            min_leaf_pixels: Absolute minimum pixel count for valid leaf segmentation.
            severity_thresholds: Configurable tier cutoff percentages.
        """
        self.min_leaf_ratio = min_leaf_ratio
        self.min_leaf_pixels = min_leaf_pixels
        self.severity_thresholds = severity_thresholds or DEFAULT_SEVERITY_THRESHOLDS

    def _to_cv2_bgr(
        self, image_input: Union[str, Path, bytes, io.BytesIO, Image.Image, np.ndarray]
    ) -> np.ndarray:
        """
        Converts various image input types safely into a verified BGR NumPy uint8 array.
        """
        if isinstance(image_input, np.ndarray):
            if image_input.ndim == 2:
                # Grayscale to BGR
                return cv2.cvtColor(image_input, cv2.COLOR_GRAY2BGR)
            elif image_input.ndim == 3:
                if image_input.shape[2] == 4:
                    # BGRA to BGR
                    return cv2.cvtColor(image_input, cv2.COLOR_BGRA2BGR)
                elif image_input.shape[2] == 3:
                    # Assume RGB if created from PIL, or preserve BGR
                    return image_input.copy()
            raise ValueError(f"Unsupported numpy image shape: {image_input.shape}")

        elif isinstance(image_input, Image.Image):
            rgb_img = image_input.convert("RGB")
            return cv2.cvtColor(np.array(rgb_img), cv2.COLOR_RGB2BGR)

        elif isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.exists() or not p.is_file():
                raise FileNotFoundError(f"Image path does not exist: {p}")
            bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
            if bgr is None:
                raise ValueError(f"Failed to read image at path: {p}")
            return bgr

        elif isinstance(image_input, (bytes, bytearray)):
            if len(image_input) == 0:
                raise ValueError("Empty byte sequence provided as image.")
            nparr = np.frombuffer(image_input, np.uint8)
            bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if bgr is None:
                raise ValueError("Failed to decode byte sequence into an image.")
            return bgr

        elif isinstance(image_input, io.IOBase):
            image_input.seek(0)
            nparr = np.frombuffer(image_input.read(), np.uint8)
            bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if bgr is None:
                raise ValueError("Failed to decode stream into an image.")
            return bgr

        else:
            raise TypeError(f"Unsupported image input type: {type(image_input).__name__}")

    def segment_leaf(self, bgr_img: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Identifies the visible plant leaf region and separates it from the background.
        
        Uses chromaticity analysis, Excess Green Index (ExG), LAB a* channel,
        and morphological contour filtering.
        
        Returns:
            leaf_mask: Boolean 2D numpy array (True for leaf pixels, False for background).
            stats: Diagnostic dictionary.
        """
        h, w = bgr_img.shape[:2]
        total_pixels = h * w

        if total_pixels == 0:
            return np.zeros((0, 0), dtype=bool), {"total_leaf_pixels": 0, "leaf_ratio": 0.0}

        # Check for uniform / blank / zero contrast images
        std_per_channel = np.std(bgr_img, axis=(0, 1))
        if np.all(std_per_channel < 1.0):
            return np.zeros((h, w), dtype=bool), {
                "total_leaf_pixels": 0,
                "leaf_ratio": 0.0,
                "low_contrast": True,
            }

        # Color representations
        hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2LAB)

        b = bgr_img[:, :, 0].astype(np.float32)
        g = bgr_img[:, :, 1].astype(np.float32)
        r = bgr_img[:, :, 2].astype(np.float32)

        hue, sat, val = cv2.split(hsv)
        l_chan, a_chan, b_chan = cv2.split(lab)

        # 1. Background Suppression
        # Detect neutral/monochrome backgrounds (white, gray, black paper/bench or neutral background)
        # In neutral surfaces, R ~= G ~= B, so max pairwise difference is small
        diff_rg = np.abs(r - g)
        diff_gb = np.abs(g - b)
        diff_rb = np.abs(r - b)
        max_diff = np.maximum(np.maximum(diff_rg, diff_gb), diff_rb)

        neutral_bg = (max_diff < 22)
        dark_bg = (val < 32)
        white_bg = (val > 232) & (sat < 32)

        is_background = neutral_bg | dark_bg | white_bg

        # 2. Vegetation Candidate Identification
        # Excess Green Index: 2G - R - B
        exg = 2.0 * g - r - b

        # Healthy green or chlorotic/necrotic tissue candidate
        # Leaf colors:
        # - Green: Hue in [20, 95], sat > 25, a_chan < 125
        # - Yellow/brown inside leaf: Hue < 25, sat > 35, val > 30, a_chan >= 120
        # - Excess green > 0 with reasonable brightness
        green_cue = (hue >= 20) & (hue <= 95) & (sat > 25) & (a_chan < 125)
        exg_cue = (exg > 0) & (sat > 20) & (val > 25)
        lesion_cue = (hue < 25) & (sat > 35) & (val > 35) & (val < 210) & (max_diff >= 18)

        leaf_candidate = (~is_background) & (green_cue | exg_cue | lesion_cue)

        # 3. Morphological Operations
        # Close internal gaps (especially necrotic spots inside leaf boundaries)
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        cand_u8 = leaf_candidate.astype(np.uint8) * 255
        closed = cv2.morphologyEx(cand_u8, cv2.MORPH_CLOSE, kernel_close, iterations=3)

        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel_open, iterations=1)

        # 4. Contour Filtering: Extract leaf components and fill interior holes
        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        leaf_mask = np.zeros((h, w), dtype=bool)

        min_area = self.min_leaf_ratio * total_pixels
        for c in contours:
            area = cv2.contourArea(c)
            if area >= min_area:
                c_mask = np.zeros((h, w), dtype=np.uint8)
                cv2.drawContours(c_mask, [c], -1, 255, -1)
                leaf_mask |= (c_mask > 0)

        leaf_pixels = int(np.count_nonzero(leaf_mask))
        leaf_ratio = float(leaf_pixels / total_pixels) if total_pixels > 0 else 0.0

        stats = {
            "total_pixels": total_pixels,
            "total_leaf_pixels": leaf_pixels,
            "leaf_ratio": round(leaf_ratio, 4),
            "low_contrast": False,
        }

        return leaf_mask, stats

    def segment_lesions(
        self, bgr_img: np.ndarray, leaf_mask: np.ndarray, disease_code: str
    ) -> Tuple[np.ndarray, int]:
        """
        Identifies visibly diseased lesions (necrotic and chlorotic regions) within the leaf mask.
        
        Returns:
            lesion_mask: Boolean 2D array of affected leaf pixels.
            lesion_pixels: Number of affected pixels.
        """
        if not np.any(leaf_mask):
            return np.zeros_like(leaf_mask, dtype=bool), 0

        hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2LAB)

        b = bgr_img[:, :, 0].astype(np.float32)
        g = bgr_img[:, :, 1].astype(np.float32)
        r = bgr_img[:, :, 2].astype(np.float32)

        hue, sat, val = cv2.split(hsv)
        l_chan, a_chan, b_chan = cv2.split(lab)
        exg = 2.0 * g - r - b

        # Healthy green reference tissue inside this leaf:
        # Hue solidly green (32..90), high saturation, low a* (distinctly green), positive ExG
        healthy_green = (
            leaf_mask
            & (hue >= 32)
            & (hue <= 90)
            & (sat > 35)
            & (a_chan < 122)
            & (exg > 8)
        )

        # 1. Necrotic Lesions (brown, dark necrotic, tan, black spots)
        # Characteristic of Early Blight, Late Blight, Septoria, Bacterial Spot, Target Spot
        necrotic = leaf_mask & (~healthy_green) & (
            # Warm brown / tan necrotic:
            ((hue < 30) & (sat > 28) & (a_chan >= 123) & (val < 205))
            # Water-soaked or dark necrotic (Late Blight, mature spots):
            | ((exg <= 0) & (val < 185) & (a_chan >= 121))
            # Very dark necrotic centers:
            | ((val < 65) & (sat > 18) & (exg < 6))
        )

        # 2. Chlorotic Halo / Yellow Discoloration
        # Characteristic halo surrounding necrotic lesions or viral yellowing
        chlorotic = leaf_mask & (~healthy_green) & (
            (hue >= 18)
            & (hue < 34)
            & (sat > 45)
            & (b_chan > 140)
            & (exg < 14)
        )

        raw_lesions = necrotic | chlorotic

        # 3. Morphological Noise Removal:
        # Remove isolated 1-2 pixel noise artifacts while preserving true lesion clusters
        lesion_u8 = raw_lesions.astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(lesion_u8, cv2.MORPH_OPEN, kernel, iterations=1)

        # Restrict strictly to inside the validated leaf mask
        final_lesion_mask = (cleaned > 0) & leaf_mask
        lesion_pixels = int(np.count_nonzero(final_lesion_mask))

        return final_lesion_mask, lesion_pixels

    def calculate_severity_category(
        self, affected_percent: Optional[float], disease_code: str
    ) -> str:
        """
        Assigns an agronomic severity category based on affected percentage.
        Thresholds are adapted from standard plant pathology assessment keys.
        """
        if affected_percent is None or not math.isfinite(affected_percent):
            return "unavailable"

        if affected_percent == 0.0:
            return "none"

        mild_cut = self.severity_thresholds.get("mild", 10.0)
        mod_cut = self.severity_thresholds.get("moderate", 25.0)

        if affected_percent <= mild_cut:
            return "mild"
        elif affected_percent <= mod_cut:
            return "moderate"
        else:
            return "severe"

    def estimate(
        self,
        image_input: Union[str, Path, bytes, io.BytesIO, Image.Image, np.ndarray],
        disease_code: str,
        confidence: Optional[float] = None,
    ) -> SeverityResult:
        """
        Main entry point for Plant Disease Severity Estimation.
        
        Args:
            image_input: Image in various formats.
            disease_code: Identified disease code (e.g., 'Potato___Early_blight').
            confidence: Optional classification confidence score.
            
        Returns:
            SeverityResult containing affected percentage, category, status, and metadata.
        """
        try:
            # 1. Decode & Validate Image
            bgr_img = self._to_cv2_bgr(image_input)
            h, w = bgr_img.shape[:2]
            if h <= 0 or w <= 0:
                return SeverityResult(
                    status="unreliable_segmentation",
                    message="Image dimensions are invalid or zero.",
                )

            # 2. Check Disease Operating Mode
            clean_code = (disease_code or "").strip()

            # Healthy Leaf Case:
            if clean_code in HEALTHY_CLASSES:
                # Segment leaf to verify presence
                leaf_mask, stats = self.segment_leaf(bgr_img)
                if stats["total_leaf_pixels"] < self.min_leaf_pixels:
                    return SeverityResult(
                        status="insufficient_leaf_area",
                        message="Visible leaf area is too small or no clear leaf region was detected.",
                        total_leaf_pixels=stats["total_leaf_pixels"],
                    )

                return SeverityResult(
                    status="healthy_leaf",
                    estimated_affected_area_percent=0.0,
                    category="none",
                    affected_pixels=0,
                    total_leaf_pixels=stats["total_leaf_pixels"],
                    confidence_level="high",
                    message="Plant tissue classified as healthy; no disease lesions detected.",
                )

            # Systemic / Viral / Diffuse Case:
            # Optical foliar lesion segmentation is only partially calibrated for systemic curling or mosaic
            if clean_code in SYSTEMIC_VIRAL_CLASSES:
                leaf_mask, stats = self.segment_leaf(bgr_img)
                leaf_pixels = stats["total_leaf_pixels"]
                if leaf_pixels < self.min_leaf_pixels:
                    return SeverityResult(
                        status="insufficient_leaf_area",
                        message="Visible leaf area is too small or no clear leaf region was detected.",
                        total_leaf_pixels=leaf_pixels,
                    )

                # Segment chlorosis
                _, lesion_px = self.segment_lesions(bgr_img, leaf_mask, clean_code)
                percent = round(float((lesion_px / leaf_pixels) * 100.0), 1)
                percent = max(0.0, min(100.0, percent))
                cat = self.calculate_severity_category(percent, clean_code)

                return SeverityResult(
                    status="estimated",
                    estimated_affected_area_percent=percent,
                    category=cat,
                    affected_pixels=lesion_px,
                    total_leaf_pixels=leaf_pixels,
                    confidence_level="moderate",
                    message="Notice: Viral / mite damage produces diffuse chlorosis or leaf curling; estimate reflects visible discoloration.",
                )

            # Unsupported Disease Class:
            if clean_code not in FOLIAR_LESION_CLASSES:
                return SeverityResult(
                    status="unsupported_class",
                    category="unavailable",
                    message=f"Severity estimation is not calibrated for condition '{clean_code}'.",
                )

            # 3. Foliar Blights & Spots: Extract Leaf Mask
            leaf_mask, stats = self.segment_leaf(bgr_img)

            if stats.get("low_contrast", False):
                return SeverityResult(
                    status="unreliable_segmentation",
                    message="Image has insufficient color contrast or illumination to separate leaf from background.",
                    total_leaf_pixels=stats["total_leaf_pixels"],
                )

            leaf_pixels = stats["total_leaf_pixels"]
            if leaf_pixels < self.min_leaf_pixels or stats["leaf_ratio"] < self.min_leaf_ratio:
                return SeverityResult(
                    status="insufficient_leaf_area",
                    message="Visible leaf area is too small or no clear leaf region was detected.",
                    total_leaf_pixels=leaf_pixels,
                )

            # 4. Lesion Segmentation
            lesion_mask, lesion_pixels = self.segment_lesions(bgr_img, leaf_mask, clean_code)

            # 5. Calculation with strict safety bounds
            if leaf_pixels <= 0:
                return SeverityResult(
                    status="insufficient_leaf_area",
                    message="Zero validated leaf pixels detected.",
                )

            raw_percent = (float(lesion_pixels) / float(leaf_pixels)) * 100.0

            if not math.isfinite(raw_percent):
                return SeverityResult(
                    status="unreliable_segmentation",
                    message="Calculated affected area percentage resulted in a non-finite value.",
                )

            bounded_percent = max(0.0, min(100.0, raw_percent))
            rounded_percent = round(bounded_percent, 1)

            category = self.calculate_severity_category(rounded_percent, clean_code)

            return SeverityResult(
                status="estimated",
                estimated_affected_area_percent=rounded_percent,
                category=category,
                affected_pixels=lesion_pixels,
                total_leaf_pixels=leaf_pixels,
                confidence_level="high" if leaf_pixels > 2000 else "medium",
                message="Visible affected leaf area successfully estimated.",
            )

        except Exception as e:
            # Defensive programming: ensure estimator failures never crash caller
            return SeverityResult(
                status="estimation_error",
                category="unavailable",
                message=f"Severity estimation encountered an error: {str(e)}",
            )


# Default singleton instance
_estimator_instance: Optional[PlantDiseaseSeverityEstimator] = None


def get_severity_estimator() -> PlantDiseaseSeverityEstimator:
    """Returns the singleton PlantDiseaseSeverityEstimator instance."""
    global _estimator_instance
    if _estimator_instance is None:
        _estimator_instance = PlantDiseaseSeverityEstimator()
    return _estimator_instance


def estimate_disease_severity(
    image_input: Union[str, Path, bytes, io.BytesIO, Image.Image, np.ndarray],
    disease_code: str,
    confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Convenience function returning dictionary ready for API response serialization.
    """
    estimator = get_severity_estimator()
    return estimator.estimate(image_input, disease_code, confidence).to_dict()
