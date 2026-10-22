"""
Comprehensive Image Validation Pipeline for Tomato and Potato Disease Detection.

Implements strict, multi-stage input validation before machine learning disease classification:
- Stage A: File & image raster integrity (format, size, dimensions, sharpness, illumination).
- Stage B: Plant and leaf presence verification (rejection of people, animals, vehicles,
           furniture, buildings, and fruits/tubers alone without leaves).
- Stage C: Dedicated Crop Identification distinguishing supported crops (Tomato, Potato)
           from unsupported plants and non-plants.
- Stage D: Structured decision engine with standard validation outcomes:
  - VALID_TOMATO_LEAF
  - VALID_POTATO_LEAF
  - INVALID_NON_PLANT_IMAGE
  - INVALID_NO_LEAF
  - UNSUPPORTED_PLANT
  - UNSUPPORTED_CROP_UNCERTAIN
  - INVALID_IMAGE_QUALITY
  - INVALID_FILE
"""

from dataclasses import dataclass, field
import io
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CROP_VALIDATOR_PATH = PROJECT_ROOT / "models" / "crop_validator" / "crop_validator_head.pth"

# ---------------------------------------------------------------------------
# Outcome Definitions
# ---------------------------------------------------------------------------
VALID_TOMATO_LEAF = "VALID_TOMATO_LEAF"
VALID_POTATO_LEAF = "VALID_POTATO_LEAF"
INVALID_NON_PLANT_IMAGE = "INVALID_NON_PLANT_IMAGE"
INVALID_NO_LEAF = "INVALID_NO_LEAF"
UNSUPPORTED_PLANT = "UNSUPPORTED_PLANT"
UNSUPPORTED_CROP_UNCERTAIN = "UNSUPPORTED_CROP_UNCERTAIN"
INVALID_IMAGE_QUALITY = "INVALID_IMAGE_QUALITY"
INVALID_FILE = "INVALID_FILE"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MIN_DIMENSION = 60
MIN_PIXELS = 4096


@dataclass
class ValidationResult:
    """Structured decision outcome of image validation."""
    decision: str
    is_valid: bool
    crop: Optional[str] = None
    error_code: Optional[str] = None
    message: str = ""
    http_status: int = 422
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "is_valid": self.is_valid,
            "crop": self.crop,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ImageValidator:
    """
    Dedicated image validation pipeline for AI Farmer Assistant.
    """

    def __init__(self, validator_model_path: Optional[Union[str, Path]] = None, device: Optional[torch.device] = None):
        self.device = device or torch.device("cpu")
        self.model_path = Path(validator_model_path) if validator_model_path else CROP_VALIDATOR_PATH

        # 1. Base MobileNetV2 pretrained feature extractor
        weights = MobileNet_V2_Weights.DEFAULT
        self.base_mobilenet = mobilenet_v2(weights=weights)
        self.base_mobilenet.eval()
        self.base_mobilenet = self.base_mobilenet.to(self.device)
        self.imagenet_categories = weights.meta["categories"]

        # Standard preprocessing for MobileNetV2
        self.preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        # 2. Dedicated Crop Classifier Head
        self.crop_classes = ["tomato", "potato", "unsupported_plant", "non_plant"]
        self.crop_head = nn.Linear(1280, 4)

        if self.model_path.exists():
            checkpoint = torch.load(self.model_path, map_location=self.device)
            state_dict = checkpoint.get("state_dict", checkpoint)
            clean_state = {k.replace("linear.", ""): v for k, v in state_dict.items()}
            self.crop_head.load_state_dict(clean_state)
            self.crop_head.eval()
            self.crop_head = self.crop_head.to(self.device)
            self.is_crop_model_ready = True
        else:
            self.is_crop_model_ready = False

    # -----------------------------------------------------------------------
    # Stage A: File & Raster Validation
    # -----------------------------------------------------------------------
    def validate_file_and_raster(
        self,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        pil_image: Optional[Image.Image] = None,
    ) -> Tuple[Optional[Image.Image], Optional[ValidationResult]]:
        """
        Validates file size, decoding, raster structure, dimensions, and visual quality.
        """
        # A.1 File presence and extension
        if filename:
            ext = Path(filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                return None, ValidationResult(
                    decision=INVALID_FILE,
                    is_valid=False,
                    error_code=INVALID_FILE,
                    message="Unsupported file format. Please upload a JPEG, PNG, or WebP image.",
                    http_status=415,
                    details={"filename": filename, "extension": ext},
                )

        # A.2 Byte buffer validation
        if file_bytes is not None:
            if len(file_bytes) == 0:
                return None, ValidationResult(
                    decision=INVALID_FILE,
                    is_valid=False,
                    error_code=INVALID_FILE,
                    message="The uploaded file is empty (0 bytes).",
                    http_status=400,
                )
            if len(file_bytes) > MAX_FILE_SIZE:
                return None, ValidationResult(
                    decision=INVALID_FILE,
                    is_valid=False,
                    error_code=INVALID_FILE,
                    message=f"Uploaded file exceeds maximum allowed limit of {MAX_FILE_SIZE // (1024*1024)} MB.",
                    http_status=413,
                )

            try:
                stream = io.BytesIO(file_bytes)
                verify_img = Image.open(stream)
                fmt = verify_img.format
                verify_img.verify()

                if fmt not in ALLOWED_FORMATS:
                    return None, ValidationResult(
                        decision=INVALID_FILE,
                        is_valid=False,
                        error_code=INVALID_FILE,
                        message="Unsupported image format. Please upload a JPEG, PNG, or WebP image.",
                        http_status=415,
                    )

                stream.seek(0)
                img = Image.open(stream)
                img.load()
            except Exception as e:
                return None, ValidationResult(
                    decision=INVALID_FILE,
                    is_valid=False,
                    error_code=INVALID_FILE,
                    message="The uploaded file cannot be decoded as a valid image.",
                    http_status=422,
                    details={"error": str(e)},
                )
        elif pil_image is not None:
            img = pil_image
        else:
            return None, ValidationResult(
                decision=INVALID_FILE,
                is_valid=False,
                error_code=INVALID_FILE,
                message="No image data was provided.",
                http_status=400,
            )

        # A.3 Dimensional validity
        w, h = img.size
        if w < MIN_DIMENSION or h < MIN_DIMENSION or (w * h) < MIN_PIXELS:
            return None, ValidationResult(
                decision=INVALID_IMAGE_QUALITY,
                is_valid=False,
                error_code=INVALID_IMAGE_QUALITY,
                message="Image dimensions are too small for diagnostic analysis. Please upload an image at least 64x64 pixels.",
                http_status=422,
                details={"dimensions": [w, h]},
            )

        # Convert to RGB
        rgb_img = img.convert("RGB")
        np_img = np.array(rgb_img)

        # A.4 Uniform / Flat Blank image check
        std_per_channel = np.std(np_img, axis=(0, 1))
        if np.all(std_per_channel < 3.0):
            return None, ValidationResult(
                decision=INVALID_IMAGE_QUALITY,
                is_valid=False,
                error_code=INVALID_IMAGE_QUALITY,
                message="Image lacks sufficient contrast or visual detail to be analyzed.",
                http_status=422,
                details={"std": [float(s) for s in std_per_channel]},
            )

        # A.5 Overexposure / Underexposure check
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
        total_px = gray.size
        overexposed = np.count_nonzero(gray >= 252) / total_px
        underexposed = np.count_nonzero(gray <= 8) / total_px

        if overexposed > 0.94:
            return None, ValidationResult(
                decision=INVALID_IMAGE_QUALITY,
                is_valid=False,
                error_code=INVALID_IMAGE_QUALITY,
                message="Image is severely overexposed. Please upload a photo taken in balanced lighting.",
                http_status=422,
                details={"overexposed_ratio": round(overexposed, 3)},
            )
        if underexposed > 0.94:
            return None, ValidationResult(
                decision=INVALID_IMAGE_QUALITY,
                is_valid=False,
                error_code=INVALID_IMAGE_QUALITY,
                message="Image is severely dark or underexposed. Please upload a clear photo with sufficient light.",
                http_status=422,
                details={"underexposed_ratio": round(underexposed, 3)},
            )

        # A.6 Extreme blur check (Laplacian variance)
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if lap_var < 6.0:
            return None, ValidationResult(
                decision=INVALID_IMAGE_QUALITY,
                is_valid=False,
                error_code=INVALID_IMAGE_QUALITY,
                message="Image is severely blurred or out of focus. Please ensure the plant leaf is in sharp focus.",
                http_status=422,
                details={"sharpness_score": round(float(lap_var), 2)},
            )

        return rgb_img, None

    # -----------------------------------------------------------------------
    # Stage B: Plant & Leaf Detection
    # -----------------------------------------------------------------------
    def detect_leaf_presence(self, rgb_img: Image.Image) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluates whether the image contains a plant leaf rather than non-plant objects
        (people, vehicles, buildings, animals, fruit alone without leaves).
        """
        np_rgb = np.array(rgb_img)
        h, w = np_rgb.shape[:2]
        total_pixels = h * w

        bgr = cv2.cvtColor(np_rgb, cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)

        b = bgr[:, :, 0].astype(np.float32)
        g = bgr[:, :, 1].astype(np.float32)
        r = bgr[:, :, 2].astype(np.float32)

        hue, sat, val = cv2.split(hsv)
        l_chan, a_chan, b_chan = cv2.split(lab)

        # Foliage color cues:
        # Green plant tissue: Hue in [20, 95], sat > 25, a_chan < 125
        # Chlorotic/necrotic foliar tissue: Hue < 25, sat > 35, a_chan >= 120
        # ExG = 2G - R - B
        exg = 2.0 * g - r - b
        max_diff = np.maximum(np.maximum(np.abs(r - g), np.abs(g - b)), np.abs(r - b))

        is_neutral = max_diff < 20
        is_dark = val < 30
        is_blown = (val > 235) & (sat < 30)
        is_bg = is_neutral | is_dark | is_blown

        green_cue = (hue >= 20) & (hue <= 95) & (sat > 25) & (a_chan < 126)
        exg_cue = (exg > 2) & (sat > 20) & (val > 25)
        foliar_cue = (~is_bg) & (green_cue | exg_cue)

        # Check total leaf pixel proportion
        foliar_count = int(np.count_nonzero(foliar_cue))
        foliar_ratio = foliar_count / total_pixels if total_pixels > 0 else 0.0

        # Circular fruit alone check (e.g., tomato fruit without leaves)
        # Red fruit has strong R > G and R > B, but low green excess
        red_fruit_cue = (~is_bg) & (r > g + 40) & (r > b + 40) & (sat > 60)
        red_fruit_count = int(np.count_nonzero(red_fruit_cue))
        red_fruit_ratio = red_fruit_count / total_pixels if total_pixels > 0 else 0.0

        # If image is predominantly fruit with negligible foliar tissue
        if red_fruit_ratio > 0.15 and foliar_ratio < 0.04:
            return False, {
                "reason": "fruit_alone_detected",
                "foliar_ratio": round(foliar_ratio, 3),
                "red_fruit_ratio": round(red_fruit_ratio, 3),
            }

        # Check if visible foliage meets minimum threshold (at least 3.2% of image)
        if foliar_ratio < 0.032 or foliar_count < 350:
            return False, {
                "reason": "insufficient_foliage",
                "foliar_ratio": round(foliar_ratio, 3),
                "foliar_count": foliar_count,
            }

        return True, {
            "reason": "leaf_detected",
            "foliar_ratio": round(foliar_ratio, 3),
            "foliar_count": foliar_count,
        }

    # -----------------------------------------------------------------------
    # Stage C: Crop Identification (Dedicated Classifier & ImageNet Object Check)
    # -----------------------------------------------------------------------
    def classify_crop_and_plant(self, rgb_img: Image.Image) -> Dict[str, Any]:
        """
        Runs dedicated CropClassifier and ImageNet object rejection.
        """
        tensor = self.preprocess(rgb_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            # 1. Full ImageNet MobileNetV2 forward pass
            imagenet_logits = self.base_mobilenet(tensor)
            imagenet_probs = torch.softmax(imagenet_logits, dim=1)[0]
            top_imagenet_val, top_imagenet_idx = torch.topk(imagenet_probs, 5)

            top_cat_id = top_imagenet_idx[0].item()
            top_cat_prob = top_imagenet_val[0].item()
            top_cat_name = self.imagenet_categories[top_cat_id]

            # 2. Dedicated Crop Classifier Head
            feats = self.base_mobilenet.features(tensor)
            pooled = torch.nn.functional.adaptive_avg_pool2d(feats, (1, 1)).flatten(1)
            crop_logits = self.crop_head(pooled)
            crop_probs = torch.softmax(crop_logits, dim=1)[0]

        probs_dict = {
            self.crop_classes[i]: float(crop_probs[i].item())
            for i in range(len(self.crop_classes))
        }

        # Check ImageNet non-plant indicators:
        # Category IDs 0..397: Animals
        # Category IDs 400..900: Everyday objects, electronics, vehicles, buildings, apparel
        # Category IDs 923..960: Fast food dishes
        is_strong_animal = (0 <= top_cat_id <= 397) and (top_cat_prob > 0.30)
        is_strong_vehicle_or_building = (
            (400 <= top_cat_id <= 900)
            and (top_cat_prob > 0.30)
            and not any(k in top_cat_name.lower() for k in ["pot", "vase", "greenhouse"])
        )
        is_strong_prepared_food = (923 <= top_cat_id <= 960) and (top_cat_prob > 0.35)

        is_imagenet_non_plant = is_strong_animal or is_strong_vehicle_or_building or is_strong_prepared_food

        return {
            "crop_probabilities": probs_dict,
            "predicted_crop_class": self.crop_classes[int(torch.argmax(crop_probs).item())],
            "crop_confidence": float(torch.max(crop_probs).item()),
            "imagenet_top1": {"id": top_cat_id, "name": top_cat_name, "prob": round(top_cat_prob, 3)},
            "is_imagenet_non_plant": is_imagenet_non_plant,
        }

    # -----------------------------------------------------------------------
    # Stage D: Unified Validation Decision Engine
    # -----------------------------------------------------------------------
    def validate(
        self,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        pil_image: Optional[Image.Image] = None,
    ) -> ValidationResult:
        """
        Executes complete multi-stage validation pipeline.
        
        Returns:
            ValidationResult with decision (one of the 8 canonical outcomes),
            is_valid boolean, crop (if valid), error_code, and user-facing message.
        """
        # Stage A: File & Raster Validation
        rgb_img, file_err = self.validate_file_and_raster(file_bytes, filename, pil_image)
        if file_err is not None:
            return file_err

        # Stage B: Leaf & Foliage Presence Check
        has_leaf, leaf_info = self.detect_leaf_presence(rgb_img)
        if not has_leaf:
            if leaf_info.get("reason") == "fruit_alone_detected":
                return ValidationResult(
                    decision=INVALID_NO_LEAF,
                    is_valid=False,
                    error_code=INVALID_NO_LEAF,
                    message="Photograph appears to contain a fruit or object rather than a plant leaf. Disease analysis is available only for plant leaves.",
                    http_status=422,
                    details=leaf_info,
                )
            return ValidationResult(
                decision=INVALID_NO_LEAF,
                is_valid=False,
                error_code=INVALID_NO_LEAF,
                message="No suitable leaf was detected. Please upload a clear photo of a tomato or potato leaf.",
                http_status=422,
                details=leaf_info,
            )

        # Stage C: Crop & Plant Classification
        crop_res = self.classify_crop_and_plant(rgb_img)
        probs = crop_res["crop_probabilities"]
        p_tomato = probs.get("tomato", 0.0)
        p_potato = probs.get("potato", 0.0)
        p_unsupported = probs.get("unsupported_plant", 0.0)
        p_non_plant = probs.get("non_plant", 0.0)

        # Rule C.1: Non-Plant Image Rejection
        if crop_res["is_imagenet_non_plant"] or p_non_plant >= 0.40 or (crop_res["predicted_crop_class"] == "non_plant" and p_non_plant > 0.35):
            return ValidationResult(
                decision=INVALID_NON_PLANT_IMAGE,
                is_valid=False,
                error_code=INVALID_NON_PLANT_IMAGE,
                message="Invalid input. Please upload a clear photo of a tomato or potato leaf.",
                http_status=422,
                details=crop_res,
            )

        # Rule C.2: Unsupported Plant Rejection
        # If unsupported plant probability is high or dominant
        if p_unsupported >= 0.45 or (crop_res["predicted_crop_class"] == "unsupported_plant" and p_unsupported > max(p_tomato, p_potato)):
            return ValidationResult(
                decision=UNSUPPORTED_PLANT,
                is_valid=False,
                error_code=UNSUPPORTED_PLANT,
                message="This plant is not supported. Disease analysis is currently available only for tomato and potato leaves.",
                http_status=422,
                details=crop_res,
            )

        # Rule C.3: Tomato Leaf Acceptance
        if p_tomato >= 0.52 and p_tomato > (p_unsupported + 0.05) and p_tomato > p_potato:
            return ValidationResult(
                decision=VALID_TOMATO_LEAF,
                is_valid=True,
                crop="Tomato",
                message="Valid tomato leaf verified.",
                details=crop_res,
            )

        # Rule C.4: Potato Leaf Acceptance
        if p_potato >= 0.52 and p_potato > (p_unsupported + 0.05) and p_potato > p_tomato:
            return ValidationResult(
                decision=VALID_POTATO_LEAF,
                is_valid=True,
                crop="Potato",
                message="Valid potato leaf verified.",
                details=crop_res,
            )

        # Rule C.5: Uncertain Crop Identity
        # Cannot reliably distinguish whether it is tomato or potato
        return ValidationResult(
            decision=UNSUPPORTED_CROP_UNCERTAIN,
            is_valid=False,
            error_code=UNSUPPORTED_CROP_UNCERTAIN,
            message="We could not verify whether this is a tomato or potato leaf. Please upload a clearer photo of a single leaf.",
            http_status=422,
            details=crop_res,
        )


# Singleton instance
_validator_instance: Optional[ImageValidator] = None


def get_image_validator() -> ImageValidator:
    """Returns the singleton ImageValidator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ImageValidator()
    return _validator_instance


def validate_leaf_image(
    file_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
    pil_image: Optional[Image.Image] = None,
) -> ValidationResult:
    """Convenience helper to validate an uploaded leaf image."""
    validator = get_image_validator()
    return validator.validate(file_bytes=file_bytes, filename=filename, pil_image=pil_image)
