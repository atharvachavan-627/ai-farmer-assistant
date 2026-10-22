"""
Unit tests for Plant Disease Severity Estimation module (src.severity_estimator).

Covers:
- Mathematical correctness on synthetic masks (zero-pixel denominator, boundary conditions, finite output)
- Valid leaf image with foliar lesions
- Identifiable background separation
- No detectable leaf region (all background/blank)
- Very small leaf region (insufficient area)
- Low contrast / uniform image (unreliable segmentation)
- Corrupted and invalid image inputs
- Unsupported disease classes
- Healthy leaf classification (0% lesions, status healthy_leaf)
- Category thresholds and calibrations
- Defensive exception handling (zero crashes)
"""

import math
import numpy as np
from PIL import Image
import unittest

from src.severity_estimator import (
    PlantDiseaseSeverityEstimator,
    SeverityResult,
    estimate_disease_severity,
    get_severity_estimator,
    DEFAULT_SEVERITY_THRESHOLDS,
)


class TestPlantDiseaseSeverityEstimator(unittest.TestCase):
    """Unit test suite for PlantDiseaseSeverityEstimator."""

    def setUp(self):
        self.estimator = PlantDiseaseSeverityEstimator(
            min_leaf_ratio=0.03,
            min_leaf_pixels=200,
        )

    # -------------------------------------------------------------
    # 1. Mathematical & Boundary Condition Tests
    # -------------------------------------------------------------

    def test_category_thresholds(self):
        """Verify agronomic severity tiers align with cutoff thresholds."""
        self.assertEqual(self.estimator.calculate_severity_category(0.0, "Tomato___Early_blight"), "none")
        self.assertEqual(self.estimator.calculate_severity_category(5.0, "Tomato___Early_blight"), "mild")
        self.assertEqual(self.estimator.calculate_severity_category(10.0, "Tomato___Early_blight"), "mild")
        self.assertEqual(self.estimator.calculate_severity_category(10.1, "Tomato___Early_blight"), "moderate")
        self.assertEqual(self.estimator.calculate_severity_category(25.0, "Tomato___Early_blight"), "moderate")
        self.assertEqual(self.estimator.calculate_severity_category(25.1, "Tomato___Early_blight"), "severe")
        self.assertEqual(self.estimator.calculate_severity_category(100.0, "Tomato___Early_blight"), "severe")
        self.assertEqual(self.estimator.calculate_severity_category(None, "Tomato___Early_blight"), "unavailable")
        self.assertEqual(self.estimator.calculate_severity_category(float("nan"), "Tomato___Early_blight"), "unavailable")

    def test_zero_pixel_denominator_safety(self):
        """Zero leaf pixels must never cause ZeroDivisionError and must return insufficient_leaf_area."""
        blank_image = np.zeros((100, 100, 3), dtype=np.uint8)
        result = self.estimator.estimate(blank_image, "Potato___Early_blight")
        self.assertIn(result.status, ("insufficient_leaf_area", "unreliable_segmentation"))
        self.assertIsNone(result.estimated_affected_area_percent)

    def test_finite_output_guarantee(self):
        """Outputs must always be finite floats between 0.0 and 100.0."""
        # Create a synthetic image with a distinct green leaf and dark lesion
        img = np.full((120, 120, 3), (150, 150, 150), dtype=np.uint8)  # gray background
        img[20:100, 20:100] = (34, 139, 34)  # green leaf in BGR
        img[30:50, 30:50] = (19, 69, 139)    # brown lesion in BGR

        result = self.estimator.estimate(img, "Potato___Early_blight")
        if result.estimated_affected_area_percent is not None:
            self.assertTrue(math.isfinite(result.estimated_affected_area_percent))
            self.assertGreaterEqual(result.estimated_affected_area_percent, 0.0)
            self.assertLessEqual(result.estimated_affected_area_percent, 100.0)

    # -------------------------------------------------------------
    # 2. Synthetic Image Processing Tests
    # -------------------------------------------------------------

    def test_healthy_class_always_zero_lesions(self):
        """Classified healthy leaves must report 0.0% affected area and status healthy_leaf."""
        # Synthetic green leaf
        img = np.full((100, 100, 3), (160, 150, 155), dtype=np.uint8)
        img[15:85, 15:85] = (40, 140, 45)  # green leaf
        pil_img = Image.fromarray(img)

        result = self.estimator.estimate(pil_img, "Tomato___healthy")
        self.assertEqual(result.status, "healthy_leaf")
        self.assertEqual(result.estimated_affected_area_percent, 0.0)
        self.assertEqual(result.category, "none")
        self.assertEqual(result.affected_pixels, 0)
        self.assertGreater(result.total_leaf_pixels, 0)

    def test_synthetic_foliar_lesion_detection(self):
        """Foliar lesion segmentation must detect necrotic/chlorotic regions within green leaf."""
        # 100x100 image, 50x50 leaf (2500 pixels), 10x10 lesion (100 pixels) -> ~4% lesion
        img = np.full((100, 100, 3), (150, 150, 150), dtype=np.uint8)  # gray background
        img[20:80, 20:80] = (30, 150, 40)   # green leaf
        img[30:50, 30:50] = (20, 50, 130)   # brown necrotic lesion

        result = self.estimator.estimate(img, "Tomato___Early_blight")
        self.assertEqual(result.status, "estimated")
        self.assertIsNotNone(result.estimated_affected_area_percent)
        self.assertGreater(result.estimated_affected_area_percent, 0.0)
        self.assertIn(result.category, ("mild", "moderate"))
        self.assertGreater(result.affected_pixels, 0)

    def test_insufficient_leaf_area(self):
        """Images with very tiny or negligible leaf regions must return insufficient_leaf_area."""
        img = np.full((200, 200, 3), (150, 150, 150), dtype=np.uint8)
        # Tiny 5x5 green patch (25 pixels, < 0.1% of image)
        img[50:55, 50:55] = (30, 160, 40)

        result = self.estimator.estimate(img, "Potato___Early_blight")
        self.assertEqual(result.status, "insufficient_leaf_area")
        self.assertIsNone(result.estimated_affected_area_percent)

    def test_low_contrast_image(self):
        """Completely uniform image must report unreliable_segmentation or insufficient_leaf_area."""
        uniform_img = np.full((100, 100, 3), (128, 128, 128), dtype=np.uint8)
        result = self.estimator.estimate(uniform_img, "Potato___Early_blight")
        self.assertIn(result.status, ("unreliable_segmentation", "insufficient_leaf_area"))
        self.assertIsNone(result.estimated_affected_area_percent)

    def test_unsupported_disease_class(self):
        """Unrecognized conditions must return status unsupported_class."""
        img = np.full((100, 100, 3), (40, 150, 40), dtype=np.uint8)
        result = self.estimator.estimate(img, "UnknownNonExistentDisease")
        self.assertEqual(result.status, "unsupported_class")
        self.assertEqual(result.category, "unavailable")
        self.assertIsNone(result.estimated_affected_area_percent)

    def test_corrupted_image_input(self):
        """Invalid byte data must be safely handled without throwing uncaught exceptions."""
        corrupted_bytes = b"not_a_valid_image_header_bytes_12345"
        result = self.estimator.estimate(corrupted_bytes, "Potato___Early_blight")
        self.assertEqual(result.status, "estimation_error")
        self.assertEqual(result.category, "unavailable")
        self.assertIsNone(result.estimated_affected_area_percent)

    def test_empty_byte_input(self):
        """Empty byte sequences must be safely caught."""
        result = self.estimator.estimate(b"", "Potato___Early_blight")
        self.assertEqual(result.status, "estimation_error")
        self.assertIsNone(result.estimated_affected_area_percent)

    # -------------------------------------------------------------
    # 3. Serialization and Convenience Helper Tests
    # -------------------------------------------------------------

    def test_estimate_disease_severity_helper(self):
        """estimate_disease_severity must return dictionary matching API schema."""
        img = np.full((100, 100, 3), (150, 150, 150), dtype=np.uint8)
        img[20:80, 20:80] = (30, 150, 40)
        res_dict = estimate_disease_severity(img, "Tomato___healthy")

        self.assertIsInstance(res_dict, dict)
        self.assertIn("status", res_dict)
        self.assertIn("estimated_affected_area_percent", res_dict)
        self.assertIn("category", res_dict)
        self.assertIn("method", res_dict)
        self.assertIn("disclaimer", res_dict)
        self.assertEqual(res_dict["status"], "healthy_leaf")
        self.assertEqual(res_dict["estimated_affected_area_percent"], 0.0)


if __name__ == "__main__":
    unittest.main()
