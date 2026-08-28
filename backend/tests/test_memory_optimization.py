"""
LABELSETU MEMORY OPTIMIZATION & OCR STABILITY TEST SUITE
Asserts that image preprocessing downscales oversized photos,
OCR defaults to lightweight cloud mode, and local reader memory is constrained.
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
        """Verify OCR_PROVIDER is configured to 'cloud' to prevent eager PyTorch model loading."""
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

    def test_04_easyocr_reader_uses_single_language_model(self):
        """Verify _get_reader loads en-only model to minimize PyTorch RAM footprint."""
        import inspect
        src = inspect.getsource(ocr_service._get_reader)
        self.assertIn('["en"]', src, "EasyOCR reader should use ['en'] to reduce memory")


if __name__ == "__main__":
    unittest.main()
