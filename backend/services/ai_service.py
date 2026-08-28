"""
Groq AI Service — LLM Integration for FMCG Package Label Semantic Intelligence.

Uses GROQ_API_KEY to analyze OCR text & entity metadata, providing:
1. Normalized entity values
2. Semantic consistency observations & ambiguity detection
3. Plain-English package explanation
4. Actionable fix recommendations for Legal Metrology compliance

NOTE: Statutory compliance pass/fail decisions and scores remain 100% authoritative
under the deterministic Legal Metrology Rule Engine (services/rule_engine.py).
Groq AI operates as a non-blocking supplementary intelligence layer.
"""

import os
import json
import logging
import httpx
from typing import Dict, Any, Optional
from config import settings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Fast, low-latency, structured JSON model available on Groq
GROQ_MODEL = getattr(settings, "GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_TIMEOUT = 12.0  # Non-blocking timeout in seconds


def is_groq_available() -> bool:
    """Check if GROQ_API_KEY is configured in settings or environment."""
    key = getattr(settings, "GROQ_API_KEY", None) or getattr(settings, "GROQ_KEY", None) or os.getenv("GROQ_API_KEY", "")
    return bool(key and key.strip())


def _get_groq_key() -> str:
    """Retrieve the Groq API key safely without logging it."""
    return getattr(settings, "GROQ_API_KEY", None) or getattr(settings, "GROQ_KEY", None) or os.getenv("GROQ_API_KEY", "") or ""


def analyze_label_with_groq(
    ocr_text: str,
    extracted_entities: Optional[Dict[str, Any]] = None,
    rules_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Call Groq API to perform semantic interpretation, normalization, and recommendation generation.
    Returns a standardized dictionary. Never raises unhandled exceptions.
    """
    if not is_groq_available():
        return {
            "available": False,
            "status": "unconfigured",
            "provider": "groq",
            "message": "Groq AI key not configured. Compliance evaluated using deterministic rule engine.",
        }

    key = _get_groq_key()
    if not ocr_text or not ocr_text.strip():
        return {
            "available": False,
            "status": "empty_input",
            "provider": "groq",
            "message": "No OCR text available for AI analysis.",
        }

    # Context snippet for prompt
    entities_snippet = json.dumps(extracted_entities or {}, default=str)
    rules_snippet = ""
    if rules_summary and "fields" in rules_summary:
        missing = [f["field_name"] for f in rules_summary.get("fields", []) if f.get("status") == "fail"]
        rules_snippet = f"Rule Engine Missing Declarations: {', '.join(missing) if missing else 'None'}"

    prompt = f"""You are an expert Legal Metrology (Packaged Commodities) Rules 2011 compliance AI assistant in India.
Analyze the following packaging OCR text and extracted entity data:

--- OCR EXTRACTED TEXT ---
{ocr_text[:3500]}
--------------------------
Rule Engine Extracted Context: {entities_snippet}
{rules_snippet}

Perform semantic interpretation and return ONLY valid JSON matching this schema:
{{
  "normalized_entities": {{
    "product_name": "string or null",
    "manufacturer": "string or null",
    "net_quantity": "string or null",
    "mrp": "string or null",
    "manufacturing_date": "string or null",
    "country_of_origin": "string or null",
    "consumer_care": "string or null",
    "unit_sale_price": "string or null"
  }},
  "semantic_observations": [
    "key observation 1 (e.g. font clarity, declaration grouping, multi-pack details)"
  ],
  "ambiguous_fields": [
    "field name if ambiguous, or empty"
  ],
  "recommendations": [
    "actionable brand recommendation 1 for Legal Metrology compliance",
    "actionable brand recommendation 2"
  ],
  "explanation": "concise 2-sentence plain English summary of package label declarations"
}}"""

    system_instructions = (
        "You are an expert Legal Metrology AI assistant. "
        "You must distinguish strictly between facts directly supported by uploaded package evidence and external references. "
        "Never convert a missing or failed legal declaration into a pass using external data. "
        "Never invent MRP, batch numbers, manufacturing dates, or expiry dates. "
        "The deterministic Legal Metrology rule engine is the sole authority for legal pass/fail scoring. "
        "Output strictly valid JSON without markdown fences."
    )

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=GROQ_TIMEOUT) as client:
            resp = client.post(GROQ_API_URL, json=payload, headers=headers)

            if resp.status_code == 200:
                res_json = resp.json()
                content = res_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                parsed = json.loads(content)

                return {
                    "available": True,
                    "status": "success",
                    "provider": "groq",
                    "model": GROQ_MODEL,
                    "normalized_entities": parsed.get("normalized_entities", {}),
                    "semantic_observations": parsed.get("semantic_observations", []),
                    "ambiguous_fields": parsed.get("ambiguous_fields", []),
                    "recommendations": parsed.get("recommendations", []),
                    "explanation": parsed.get("explanation", ""),
                }
            else:
                logger.warning("Groq API returned HTTP %s: %s", resp.status_code, resp.text[:200])
                return {
                    "available": False,
                    "status": "api_error",
                    "http_status": resp.status_code,
                    "provider": "groq",
                    "message": "AI analysis temporarily unavailable. Statutory compliance verified via deterministic rule engine.",
                }

    except httpx.TimeoutException:
        logger.warning("Groq AI API timed out after %ss (non-blocking).", GROQ_TIMEOUT)
        return {
            "available": False,
            "status": "timeout",
            "provider": "groq",
            "message": "AI analysis timed out. Statutory compliance verified via deterministic rule engine.",
        }
    except Exception as exc:
        logger.warning("Groq AI API call failed (non-blocking): %s", exc)
        return {
            "available": False,
            "status": "error",
            "provider": "groq",
            "message": "AI analysis unavailable. Statutory compliance verified via deterministic rule engine.",
        }
