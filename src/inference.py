"""
Clean, reusable inference module for AI Farmer Assistant disease classification.

Handles image loading (file paths, byte streams, PIL images), preprocessing,
and model inference with full error handling. Never crashes on malformed input.
"""

from pathlib import Path
from typing import Union, Dict, Any, Optional
import io
import json
import torch
from PIL import Image

from src.preprocessing import val_test_transform
from src.model import create_mobilenetv2

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FINETUNED_PATH = PROJECT_ROOT / "models" / "mobilenetv2_finetuned" / "best_finetuned_model.pth"
DEFAULT_BASELINE_PATH = PROJECT_ROOT / "models" / "mobilenetv2" / "best_model.pth"
DEFAULT_MAPPING_PATH = PROJECT_ROOT / "models" / "mobilenetv2" / "class_mapping.json"


class InferenceError(Exception):
    """Custom exception raised when inference fails on invalid input."""
    pass


class DiseaseClassifier:
    """
    Reusable disease classification engine.
    """
    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        class_mapping_path: Optional[Union[str, Path]] = None,
        device: Optional[torch.device] = None
    ):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 1. Resolve model checkpoint
        if model_path:
            self.model_path = Path(model_path)
        elif DEFAULT_FINETUNED_PATH.exists():
            self.model_path = DEFAULT_FINETUNED_PATH
        elif DEFAULT_BASELINE_PATH.exists():
            self.model_path = DEFAULT_BASELINE_PATH
        else:
            raise FileNotFoundError("No model checkpoint found. Please verify models directory.")

        # Determine version name
        if "finetuned" in str(self.model_path).lower():
            self.model_version = "MobileNetV2-FineTuned-v1.0"
        else:
            self.model_version = "MobileNetV2-Baseline-v1.0"

        # 2. Load authoritative class mapping
        mapping_file = Path(class_mapping_path) if class_mapping_path else DEFAULT_MAPPING_PATH
        if not mapping_file.exists():
            raise FileNotFoundError(f"Authoritative class mapping not found at: {mapping_file}")

        with open(mapping_file, "r") as f:
            self.class_to_idx: Dict[str, int] = json.load(f)
        
        # Build inverted mapping: index -> class name
        self.idx_to_class: Dict[int, str] = {idx: name for name, idx in self.class_to_idx.items()}
        self.num_classes = len(self.idx_to_class)

        # 3. Initialize Model and Load State Dict
        self.model = create_mobilenetv2(num_classes=self.num_classes, pretrained=False)
        checkpoint = torch.load(self.model_path, map_location=self.device)
        
        if "model_state_dict" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state_dict"])
        else:
            self.model.load_state_dict(checkpoint)

        self.model = self.model.to(self.device)
        self.model.eval()

        # Cache preprocessing transform
        self.transform = val_test_transform

    def _load_image(self, image_input: Union[str, Path, bytes, io.BytesIO, Image.Image]) -> Image.Image:
        """
        Safely converts various input formats into a verified RGB PIL Image.
        """
        if isinstance(image_input, Image.Image):
            pil_img = image_input.copy()
        elif isinstance(image_input, (str, Path)):
            img_path = Path(image_input)
            if not img_path.exists():
                raise FileNotFoundError(f"Image file does not exist: {img_path}")
            if not img_path.is_file():
                raise ValueError(f"Path is not a regular file: {img_path}")
            pil_img = Image.open(img_path)
        elif isinstance(image_input, (bytes, bytearray)):
            if len(image_input) == 0:
                raise ValueError("Empty byte sequence provided as image input.")
            pil_img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, io.IOBase):
            pil_img = Image.open(image_input)
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input).__name__}")

        # Ensure image pixel raster is loaded and validated
        pil_img.load()

        if pil_img.width <= 0 or pil_img.height <= 0:
            raise ValueError(f"Invalid image dimensions: {pil_img.size}")

        return pil_img.convert("RGB")

    def predict(
        self,
        image_input: Union[str, Path, bytes, io.BytesIO, Image.Image],
        return_all_probabilities: bool = False,
        raise_on_error: bool = False
    ) -> Dict[str, Any]:
        """
        Runs inference on an image input and returns standard prediction output.
        
        Returns:
            {
                "disease": str,
                "confidence": float,
                "class_index": int,
                "model_version": str,
                (optional) "error": str,
                (optional) "all_probabilities": dict
            }
        """
        try:
            # 1. Safely load and convert image
            pil_img = self._load_image(image_input)

            # 2. Apply validated evaluation preprocessing
            tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

            # 3. Forward pass without gradients
            with torch.no_grad():
                outputs = self.model(tensor)
                probabilities = torch.softmax(outputs, dim=1)[0]

            # 4. Extract highest-confidence prediction
            class_idx = int(torch.argmax(probabilities).item())
            confidence = float(probabilities[class_idx].item())
            disease_name = self.idx_to_class[class_idx]

            result = {
                "disease": disease_name,
                "confidence": round(confidence, 4),
                "class_index": class_idx,
                "model_version": self.model_version
            }

            if return_all_probabilities:
                result["all_probabilities"] = {
                    self.idx_to_class[i]: round(float(p.item()), 4)
                    for i, p in enumerate(probabilities)
                }

            return result

        except Exception as e:
            if raise_on_error:
                raise InferenceError(f"Inference failed: {str(e)}") from e

            # Safe return without crashing the application
            return {
                "disease": "Unknown",
                "confidence": 0.0,
                "class_index": -1,
                "model_version": self.model_version,
                "error": str(e)
            }


# Global singleton instance for easy import
_default_classifier: Optional[DiseaseClassifier] = None
_classifier_disabled: bool = False


def get_classifier(reload: bool = False) -> Optional[DiseaseClassifier]:
    """Returns a cached global DiseaseClassifier instance, or None if disabled."""
    global _default_classifier, _classifier_disabled
    if _classifier_disabled:
        return None
    if reload or _default_classifier is None:
        _default_classifier = DiseaseClassifier()
    return _default_classifier


def set_classifier(classifier: Optional[DiseaseClassifier]) -> None:
    """Sets or clears the global DiseaseClassifier instance (useful for testing)."""
    global _default_classifier, _classifier_disabled
    _default_classifier = classifier
    _classifier_disabled = classifier is None


def predict_disease(image_input) -> Dict[str, Any]:
    """Convenience function using the default classifier instance."""
    return get_classifier().predict(image_input)
