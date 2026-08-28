"""
Automated Unit Test Suite for OpenCV Image Quality Analysis & Panel Classifier.
"""

import sys
import unittest
import numpy as np
import cv2
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.image_processor import analyze_image_quality, classify_image_content, auto_deskew, enhance_image_for_ocr


class TestImageProcessor(unittest.TestCase):
    def test_clear_synthetic_image_quality(self):
        """Test clean synthetic image quality analysis."""
        # Create a clean high-contrast image matrix
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        cv2.putText(img, "NET QUANTITY: 500g MRP Rs 100", (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        _, encoded = cv2.imencode(".png", img)
        image_bytes = encoded.tobytes()

        quality = analyze_image_quality(image_bytes)
        self.assertEqual(quality["width"], 400)
        self.assertEqual(quality["height"], 400)
        self.assertIn(quality["quality_status"], ["GOOD", "FAIR"])

    def test_corrupt_image_bytes(self):
        """Test corrupt/invalid image byte handling."""
        corrupt_bytes = b"NOT_AN_IMAGE_DATA_12345"
        quality = analyze_image_quality(corrupt_bytes)
        self.assertEqual(quality["quality_status"], "UNREADABLE")
        self.assertTrue(len(quality["issues"]) > 0)

    def test_screenshot_classification(self):
        """Test browser UI screenshot classification."""
        text = "https://labelsetu-ivory.vercel.app/dashboard Loading profile..."
        quality = {"quality_status": "GOOD"}
        classification = classify_image_content(b"", text, quality)
        self.assertEqual(classification["classification"], "SCREENSHOT")
        self.assertFalse(classification["is_product_label"])

    def test_back_declaration_panel_classification(self):
        """Test back packaging declaration panel classification."""
        text = "Manufactured by: Tata Consumer Products Ltd Net Quantity: 1kg MRP: Rs 28.00 Mfg Date: 12/2026"
        quality = {"quality_status": "GOOD"}
        classification = classify_image_content(b"", text, quality)
        self.assertEqual(classification["classification"], "BACK_DECLARATION_PANEL")
        self.assertTrue(classification["is_product_label"])

    def test_front_panel_classification(self):
        """Test front packaging branding panel classification."""
        text = "Americana TOP Butter Cracker with a twist"
        quality = {"quality_status": "GOOD"}
        classification = classify_image_content(b"", text, quality)
        self.assertEqual(classification["classification"], "FRONT_PANEL")
        self.assertTrue(classification["is_product_label"])


if __name__ == "__main__":
    unittest.main()
