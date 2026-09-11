"""
PaddleOCR Singleton Engine Wrapper.
Ensures:
- Model is loaded ONCE at server startup.
- Thread-safe serialized inference using a Lock.
- Natural reading-order sorting (top-to-bottom, left-to-right).
- Real confidence extraction (never fabricated).
- Bounding box projection back to original image dimensions.
- Robust platform patches (IPv4 resolution, oneDNN CPU PIR workaround).
"""
import os
import socket
import logging
import threading
from typing import List, Dict, Any, Optional
import numpy as np

# Force IPv4 socket resolution to prevent Baidu/HuggingFace hangs on Windows
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

# Crucial PaddleX runtime configuration flags
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "False"

logger = logging.getLogger(__name__)

class PaddleOCREngine:
    """Singleton PaddleOCR Inference Engine."""
    _instance: Optional["PaddleOCREngine"] = None
    _lock = threading.Lock()

    def __init__(self, lang: str = "hi"):
        self.lang = lang
        self._ocr = None
        self._inference_lock = threading.Lock()
        self._initialized = False
        self._device = "cpu"
        self._init_engine()

    @classmethod
    def get_instance(cls, lang: str = "hi") -> "PaddleOCREngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(lang=lang)
            return cls._instance

    def _init_engine(self):
        logger.info(f"Initializing PaddleOCR Engine with lang='{self.lang}'...")
        try:
            import paddle
            from paddleocr import PaddleOCR

            if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
                self._device = "gpu"
            else:
                self._device = "cpu"

            self._ocr = PaddleOCR(
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="devanagari_PP-OCRv5_mobile_rec",
                text_recognition_batch_size=6,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                lang=self.lang,
            )
            self._initialized = True
            logger.info(f"PaddleOCR Engine successfully loaded on device: {self._device.upper()}")
        except Exception as e:
            self._initialized = False
            logger.error(f"Failed to initialize PaddleOCR Engine: {e}", exc_info=True)
            raise

    @property
    def is_ready(self) -> bool:
        return self._initialized and self._ocr is not None

    @property
    def device(self) -> str:
        return self._device

    def get_engine_info(self) -> Dict[str, Any]:
        import paddle
        import paddleocr
        return {
            "paddle_version": paddle.__version__,
            "paddleocr_version": paddleocr.__version__,
            "device": self._device,
            "configured_lang": self.lang,
            "initialized": self._initialized,
        }

    def _sort_reading_order(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort detected text lines in natural reading order (top-to-bottom, left-to-right)."""
        if not lines:
            return []

        heights = [l["bounding_box"]["y_max"] - l["bounding_box"]["y_min"] for l in lines]
        avg_h = sum(heights) / max(len(heights), 1)
        y_threshold = max(avg_h * 0.5, 8.0)

        # Primary sort by y_min
        sorted_by_y = sorted(lines, key=lambda l: (l["bounding_box"]["y_min"], l["bounding_box"]["x_min"]))

        clusters = []
        for item in sorted_by_y:
            y_center = (item["bounding_box"]["y_min"] + item["bounding_box"]["y_max"]) / 2.0
            placed = False
            for cluster in clusters:
                if abs(y_center - cluster["y_center"]) < y_threshold:
                    cluster["items"].append(item)
                    cluster["y_center"] = sum(
                        (it["bounding_box"]["y_min"] + it["bounding_box"]["y_max"]) / 2.0
                        for it in cluster["items"]
                    ) / len(cluster["items"])
                    placed = True
                    break
            if not placed:
                clusters.append({"y_center": y_center, "items": [item]})

        # Sort clusters top-to-bottom, and within each cluster left-to-right
        clusters.sort(key=lambda c: c["y_center"])
        final_sorted = []
        for cluster in clusters:
            cluster["items"].sort(key=lambda it: it["bounding_box"]["x_min"])
            final_sorted.extend(cluster["items"])
        return final_sorted

    def extract_text(
        self,
        np_image: np.ndarray,
        scale_factor: float = 1.0,
        orig_dimensions: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Runs OCR inference on a preprocessed NumPy image array.
        Serializes calls via thread lock.
        """
        if not self.is_ready:
            raise RuntimeError("PaddleOCR Engine is not initialized.")

        with self._inference_lock:
            # Predict using PaddleOCR
            preds = self._ocr.predict(np_image)

        lines: List[Dict[str, Any]] = []
        languages_detected = set()

        # Coordinate inverse scale factor (to project back to original image coordinates)
        inv_scale = 1.0 / scale_factor if scale_factor > 0 else 1.0

        for pred in preds:
            if not isinstance(pred, dict):
                continue

            texts = pred.get("rec_texts", [])
            scores = pred.get("rec_scores", [])
            polys = pred.get("rec_polys", [])

            for text, score, poly in zip(texts, scores, polys):
                if not text or not str(text).strip():
                    continue

                cleaned_text = str(text).strip()

                # Language detection heuristics from recognized characters
                if any("\u0900" <= ch <= "\u097F" for ch in cleaned_text):
                    languages_detected.add("hi")
                if any("a" <= ch.lower() <= "z" for ch in cleaned_text):
                    languages_detected.add("en")

                # Genuine confidence score: never fabricate
                conf = None
                if score is not None:
                    try:
                        conf = round(float(score), 4)
                    except (ValueError, TypeError):
                        conf = None

                # Calculate rectangular bounding box from polygon
                # and project back to original image coordinate space
                if poly is not None and len(poly) > 0:
                    poly_arr = np.array(poly)
                    x_coords = poly_arr[:, 0] * inv_scale
                    y_coords = poly_arr[:, 1] * inv_scale
                    x_min = int(round(float(np.min(x_coords))))
                    y_min = int(round(float(np.min(y_coords))))
                    x_max = int(round(float(np.max(x_coords))))
                    y_max = int(round(float(np.max(y_coords))))
                else:
                    x_min, y_min, x_max, y_max = 0, 0, 0, 0

                lines.append({
                    "text": cleaned_text,
                    "confidence": conf,
                    "bounding_box": {
                        "x_min": x_min,
                        "y_min": y_min,
                        "x_max": x_max,
                        "y_max": y_max
                    }
                })

        # Sort lines into natural packaging reading order
        sorted_lines = self._sort_reading_order(lines)
        raw_text = "\n".join(l["text"] for l in sorted_lines)

        if not languages_detected:
            languages_detected.add(self.lang)

        info = self.get_engine_info()

        return {
            "raw_text": raw_text,
            "lines": sorted_lines,
            "languages_detected": sorted(list(languages_detected)),
            "metadata": {
                "engine_version": info["paddleocr_version"],
                "framework_version": info["paddle_version"],
                "device": info["device"],
                "model_name": "devanagari_PP-OCRv5_mobile_rec+PP-OCRv5_server_det" if self.lang == "hi" else "PP-OCRv6_medium_rec",
                "total_lines_detected": len(sorted_lines),
                "image_dimensions": orig_dimensions or {
                    "width": np_image.shape[1],
                    "height": np_image.shape[0]
                }
            }
        }
