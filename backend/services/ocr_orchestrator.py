import logging
import socket
import typing
import httpx
import httpcore
from httpcore._backends.sync import SyncStream, map_exceptions
from typing import Dict, Any, Callable

from config import settings

logger = logging.getLogger(__name__)


class IPv4SyncBackend(httpcore.SyncBackend):
    """
    Network backend enforcing deterministic IPv4 DNS resolution and connection.
    Prevents [Errno 101] Network is unreachable and [Errno -9] EAI_ADDRFAMILY
    in IPv4-only cloud container environments (e.g. Render/AWS).
    """
    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: typing.Iterable[typing.Any] | None = None,
    ) -> httpcore.NetworkStream:
        exc_map = {
            socket.timeout: httpcore.ConnectTimeout,
            OSError: httpcore.ConnectError,
        }
        with map_exceptions(exc_map):
            addrinfo = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
            if not addrinfo:
                raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

            sock = None
            exceptions = []
            for af, socktype, proto, canonname, sa in addrinfo:
                try:
                    sock = socket.socket(af, socktype, proto)
                    if timeout is not None:
                        sock.settimeout(timeout)
                    sock.connect(sa)
                    exceptions.clear()
                    break
                except OSError as exc:
                    exceptions.append(exc)
                    if sock is not None:
                        sock.close()
                    sock = None

            if sock is None:
                if exceptions:
                    raise exceptions[-1]
                raise httpcore.ConnectError(f"Failed to connect to {host}:{port} via IPv4")

            if socket_options:
                for option in socket_options:
                    sock.setsockopt(*option)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        return SyncStream(sock)


def _create_ipv4_transport() -> httpx.HTTPTransport:
    transport = httpx.HTTPTransport()
    transport._pool = httpcore.ConnectionPool(
        ssl_context=transport._pool._ssl_context,
        network_backend=IPv4SyncBackend(),
        retries=0,
    )
    return transport


def call_local_ocr(image_bytes: bytes) -> Dict[str, Any]:
    """Call the standalone local OCR service via HTTP."""
    if not settings.LOCAL_OCR_ENABLED:
        raise ValueError("Local OCR is disabled via settings")
        
    url = settings.LOCAL_OCR_URL.rstrip("/")
    if not url.endswith("/ocr"):
        url = f"{url}/ocr"
    headers = {"X-Local-OCR-Key": settings.LOCAL_OCR_API_KEY}
    files = {"file": ("image.png", image_bytes, "image/png")}
    
    logger.info("[OCR Orchestrator] Calling local OCR at %s (timeout=%.1fs)", url, settings.LOCAL_OCR_TIMEOUT_SECONDS)
    
    transport = _create_ipv4_transport()
    with httpx.Client(transport=transport, timeout=settings.LOCAL_OCR_TIMEOUT_SECONDS) as client:
        response = client.post(url, files=files, headers=headers)
        response.raise_for_status()
        
    return response.json()


def map_local_response_to_contract(local_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map the local OCR response to the existing LabelSetu contract."""
    detections = []
    lines = local_data.get("lines", [])
    
    for line in lines:
        text = line.get("text", "").strip()
        if not text:
            continue
            
        conf = line.get("confidence")
        if conf is not None:
            conf = round(float(conf), 4)
            
        bbox = line.get("bounding_box")
        mapped_bbox = None
        if bbox:
            # Check if bbox is a dictionary with x_min, y_min etc.
            if isinstance(bbox, dict) and "x_min" in bbox:
                mapped_bbox = {
                    "left": bbox["x_min"],
                    "top": bbox["y_min"],
                    "width": bbox["x_max"] - bbox["x_min"],
                    "height": bbox["y_max"] - bbox["y_min"],
                }
            # Or if it's a polygon list of lists
            elif isinstance(bbox, list):
                # The prompt mentions preserving polygons if supported, but existing contract uses left/top/width/height.
                # If the local OCR returns a polygon (list of [x, y]), we could compute the bounding box.
                xs = [pt[0] for pt in bbox]
                ys = [pt[1] for pt in bbox]
                mapped_bbox = {
                    "left": min(xs),
                    "top": min(ys),
                    "width": max(xs) - min(xs),
                    "height": max(ys) - min(ys),
                }

        detections.append({
            "text": text,
            "confidence": conf,
            "bbox": mapped_bbox,
        })
        
    confidences = [d["confidence"] for d in detections if d.get("confidence") is not None]
    avg = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    
    return {
        "provider": local_data.get("provider", "paddleocr (local)"),
        "full_text": local_data.get("raw_text", ""),
        "detections": detections,
        "average_confidence": avg,
    }


def orchestrate_extract_with_scores(image_bytes: bytes, fallback_fn: Callable[[bytes], Dict[str, Any]]) -> Dict[str, Any]:
    """
    Route OCR request according to OCR_PROVIDER ('auto', 'local', 'ocr_space').
    If local fails or returns empty extraction, and OCR_LOCAL_FALLBACK_TO_CLOUD is True, fallback to OCR.space.
    """
    provider = settings.OCR_PROVIDER.lower()
    
    if provider in ("local", "auto"):
        try:
            local_json = call_local_ocr(image_bytes)
            if local_json.get("success", False):
                raw_text = (local_json.get("raw_text") or "").strip()
                lines = local_json.get("lines") or []
                if raw_text or lines:
                    return map_local_response_to_contract(local_json)
                logger.warning("[OCR Orchestrator] Local OCR returned success=True but raw_text and lines are empty")
            else:
                logger.warning("[OCR Orchestrator] Local OCR returned success=False. Reason: %s", local_json.get("error"))
        except Exception as exc:
            logger.warning("[OCR Orchestrator] Local OCR failure: %s", exc)
            
        if not settings.OCR_LOCAL_FALLBACK_TO_CLOUD and provider == "local":
            raise RuntimeError("Local OCR failed and fallback to cloud is disabled")
            
        logger.info("[OCR Orchestrator] Falling back to cloud OCR...")
        return fallback_fn(image_bytes)
        
    elif provider in ("cloud", "ocr_space"):
        return fallback_fn(image_bytes)
        
    else:
        # Unknown provider, default to fallback
        logger.warning("[OCR Orchestrator] Unknown OCR_PROVIDER %s, defaulting to cloud", provider)
        return fallback_fn(image_bytes)


def orchestrate_extract_text(image_bytes: bytes, fallback_fn: Callable[[bytes], str]) -> str:
    """Same as above but for the simple raw_text contract."""
    provider = settings.OCR_PROVIDER.lower()
    
    if provider in ("local", "auto"):
        try:
            local_json = call_local_ocr(image_bytes)
            if local_json.get("success", False):
                raw_text = (local_json.get("raw_text") or "").strip()
                lines = local_json.get("lines") or []
                if raw_text or lines:
                    return raw_text
                logger.warning("[OCR Orchestrator] Local OCR returned success=True but raw_text and lines are empty")
        except Exception as exc:
            logger.warning("[OCR Orchestrator] Local OCR raw_text failure: %s", exc)
            
        if not settings.OCR_LOCAL_FALLBACK_TO_CLOUD and provider == "local":
            raise RuntimeError("Local OCR failed and fallback to cloud is disabled")
            
        logger.info("[OCR Orchestrator] Falling back to cloud OCR...")
        return fallback_fn(image_bytes)
        
    return fallback_fn(image_bytes)
