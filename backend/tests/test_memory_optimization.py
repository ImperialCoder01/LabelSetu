"""
LABELSETU MEMORY OPTIMIZATION & OCR STABILITY TEST SUITE
Asserts that image preprocessing downscales oversized photos,
OCR operates in lightweight cloud mode, and zero local model memory is allocated.
"""

import sys
import unittest
import numpy as np
import cv2
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from config import settings
from services.image_processor import _downscale_if_large, enhance_image_for_ocr
import services.ocr_service as ocr_service


class TestMemoryOptimization(unittest.TestCase):
    def test_01_cloud_ocr_is_default_provider(self):
        """Verify OCR_PROVIDER is configured to 'cloud' to prevent local model memory allocation."""
        self.assertEqual(settings.OCR_PROVIDER.lower(), "cloud")

    def test_02_image_downscaling_caps_large_photos(self):
        """Verify 4000x3000 high-res camera photos are downscaled to <= 1600px max dimension."""
        # Create a large 4000x3000 synthetic image
        large_img = np.zeros((3000, 4000, 3), dtype=np.uint8)
        downscaled = _downscale_if_large(large_img, max_dim=1600)
        h, w = downscaled.shape[:2]
        self.assertLessEqual(max(h, w), 1600)
        self.assertEqual(w, 1600)
        self.assertEqual(h, 1200)

    def test_03_enhance_image_handles_oversized_images_safely(self):
        """Verify enhance_image_for_ocr processes large photos without crashing."""
        # Generate 2000x2000 test image in memory
        img = np.full((2000, 2000, 3), 200, dtype=np.uint8)
        cv2.putText(img, "Tata Salt 1kg MRP Rs 28", (100, 500), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 3)
        _, img_bytes = cv2.imencode(".png", img)

        enhanced_bytes, was_enhanced = enhance_image_for_ocr(img_bytes.tobytes())
        self.assertTrue(was_enhanced)
        self.assertIsInstance(enhanced_bytes, bytes)
        self.assertGreater(len(enhanced_bytes), 0)

    def test_04_zero_local_model_allocation_and_no_easyocr(self):
        """Verify ocr_service has zero local model memory footprint and does not import easyocr/torch."""
        import inspect
        src = inspect.getsource(ocr_service)
        self.assertNotIn("import easyocr", src, "ocr_service must not import easyocr")
        self.assertNotIn("import torch", src, "ocr_service must not import torch")
        self.assertNotIn("Reader(", src, "ocr_service must not instantiate any local OCR Reader")


if __name__ == "__main__":
    unittest.main()
