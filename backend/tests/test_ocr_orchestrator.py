import pytest
from unittest.mock import patch, MagicMock
from services.ocr_orchestrator import orchestrate_extract_with_scores, orchestrate_extract_text, map_local_response_to_contract
from config import settings
import httpx

@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_OCR_ENABLED", True)
    monkeypatch.setattr(settings, "OCR_LOCAL_FALLBACK_TO_CLOUD", True)
    monkeypatch.setattr(settings, "LOCAL_OCR_URL", "http://fake-local-ocr/ocr")
    monkeypatch.setattr(settings, "LOCAL_OCR_API_KEY", "test-key")
    monkeypatch.setattr(settings, "LOCAL_OCR_TIMEOUT_SECONDS", 5.0)

def mock_fallback_with_scores(image_bytes: bytes) -> dict:
    return {"provider": "cloud", "full_text": "cloud fallback", "detections": [], "average_confidence": 0.0}

def mock_fallback_text(image_bytes: bytes) -> str:
    return "cloud fallback"

def test_map_local_response_to_contract():
    # Case: Basic mapping test
    local_data = {
        "provider": "paddleocr (local)",
        "success": True,
        "raw_text": "Hello\nWorld",
        "lines": [
            {"text": "Hello", "confidence": 0.99, "bounding_box": {"x_min": 10, "y_min": 10, "x_max": 50, "y_max": 20}},
            {"text": "World", "confidence": 0.95, "bounding_box": {"x_min": 10, "y_min": 30, "x_max": 50, "y_max": 40}}
        ]
    }
    mapped = map_local_response_to_contract(local_data)
    assert mapped["provider"] == "paddleocr (local)"
    assert mapped["full_text"] == "Hello\nWorld"
    assert len(mapped["detections"]) == 2
    assert mapped["detections"][0]["text"] == "Hello"
    assert mapped["detections"][0]["confidence"] == 0.99
    assert mapped["detections"][0]["bbox"] == {"left": 10, "top": 10, "width": 40, "height": 10}
    assert mapped["average_confidence"] == 0.97

def test_case_a_cloud_provider(mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "cloud")
    res = orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)
    assert res["provider"] == "cloud"

def test_case_b_ocr_space_provider(mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "ocr_space")
    res = orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)
    assert res["provider"] == "cloud"

@patch("services.ocr_orchestrator.httpx.Client.post")
def test_case_c_local_success(mock_post, mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "local")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": True, "provider": "local_test", "raw_text": "local text", "lines": []}
    mock_post.return_value = mock_resp

    res = orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)
    assert res["provider"] == "local_test"
    assert res["full_text"] == "local text"

def test_case_d_local_disabled_with_fallback(mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "local")
    monkeypatch.setattr(settings, "LOCAL_OCR_ENABLED", False)
    
    res = orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)
    assert res["provider"] == "cloud"

def test_case_e_local_disabled_no_fallback(mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "local")
    monkeypatch.setattr(settings, "LOCAL_OCR_ENABLED", False)
    monkeypatch.setattr(settings, "OCR_LOCAL_FALLBACK_TO_CLOUD", False)
    
    with pytest.raises(RuntimeError):
        orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)

@patch("services.ocr_orchestrator.httpx.Client.post")
def test_case_f_local_timeout(mock_post, mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "local")
    mock_post.side_effect = httpx.TimeoutException("Timeout")
    
    res = orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)
    assert res["provider"] == "cloud"

@patch("services.ocr_orchestrator.httpx.Client.post")
def test_case_g_local_http_error(mock_post, mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "local")
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
    mock_post.return_value = mock_resp
    
    res = orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)
    assert res["provider"] == "cloud"

@patch("services.ocr_orchestrator.httpx.Client.post")
def test_case_h_local_invalid_json(mock_post, mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "local")
    mock_resp = MagicMock()
    mock_resp.json.side_effect = ValueError("Invalid JSON")
    mock_post.return_value = mock_resp
    
    res = orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)
    assert res["provider"] == "cloud"

@patch("services.ocr_orchestrator.httpx.Client.post")
def test_case_i_local_success_false(mock_post, mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "local")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": False, "error": "Internal Paddle error"}
    mock_post.return_value = mock_resp
    
    res = orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)
    assert res["provider"] == "cloud"

@patch("services.ocr_orchestrator.httpx.Client.post")
def test_case_j_auto_local_succeeds(mock_post, mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "auto")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": True, "provider": "paddleocr (local)", "raw_text": "auto success", "lines": []}
    mock_post.return_value = mock_resp
    
    res = orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)
    assert res["provider"] == "paddleocr (local)"

@patch("services.ocr_orchestrator.httpx.Client.post")
def test_case_k_auto_local_fails(mock_post, mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "auto")
    mock_post.side_effect = Exception("Connection Refused")
    
    res = orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)
    assert res["provider"] == "cloud"

def test_case_l_unknown_provider(mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "unknown_magical_provider")
    res = orchestrate_extract_with_scores(b"img", mock_fallback_with_scores)
    assert res["provider"] == "cloud"

@patch("services.ocr_orchestrator.httpx.Client.post")
def test_stage4_api_key_header_and_url_normalization(mock_post, mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "auto")
    monkeypatch.setattr(settings, "LOCAL_OCR_URL", "https://lenovo-loq.taile99993.ts.net")
    monkeypatch.setattr(settings, "LOCAL_OCR_API_KEY", "super-secret-stage4-key")
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": True, "provider": "paddleocr_local", "raw_text": "text", "lines": []}
    mock_post.return_value = mock_resp
    
    res = orchestrate_extract_with_scores(b"sample_img", mock_fallback_with_scores)
    assert res["provider"] == "paddleocr_local"
    
    # Assert call arguments to httpx post
    mock_post.assert_called_once()
    called_url = mock_post.call_args[0][0]
    called_headers = mock_post.call_args[1].get("headers", {})
    
    assert called_url == "https://lenovo-loq.taile99993.ts.net/ocr"
    assert called_headers.get("X-Local-OCR-Key") == "super-secret-stage4-key"

@patch("services.ocr_orchestrator.httpx.Client.post")
def test_stage4_api_key_never_in_logs(mock_post, mock_settings, monkeypatch, caplog):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "auto")
    monkeypatch.setattr(settings, "LOCAL_OCR_URL", "https://lenovo-loq.taile99993.ts.net")
    secret_key = "super-secret-must-never-leak"
    monkeypatch.setattr(settings, "LOCAL_OCR_API_KEY", secret_key)
    
    # Simulate connection error
    mock_post.side_effect = httpx.ConnectError("Connection failed to tunnel")
    
    with caplog.at_level("DEBUG"):
        res = orchestrate_extract_with_scores(b"sample_img", mock_fallback_with_scores)
        assert res["provider"] == "cloud"
        
    for record in caplog.records:
        assert secret_key not in record.message


@patch("services.ocr_orchestrator.httpx.Client")
def test_stage6a_ipv4_transport_configured(mock_client_cls, mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "OCR_PROVIDER", "auto")
    monkeypatch.setattr(settings, "LOCAL_OCR_URL", "https://lenovo-loq.taile99993.ts.net")
    
    mock_instance = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": True, "provider": "paddleocr_local", "raw_text": "text", "lines": []}
    mock_instance.post.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_instance
    
    res = orchestrate_extract_with_scores(b"sample_img", mock_fallback_with_scores)
    assert res["provider"] == "paddleocr_local"
    
    # Verify Client was initialized with HTTPTransport(local_address="0.0.0.0")
    mock_client_cls.assert_called_once()
    kwargs = mock_client_cls.call_args[1]
    transport = kwargs.get("transport")
    assert isinstance(transport, httpx.HTTPTransport)
    assert transport._pool._local_address == "0.0.0.0"

