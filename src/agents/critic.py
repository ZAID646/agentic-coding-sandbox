import json
import re
from openai import OpenAI
from src.models import CritiqueResponse
from src.config import API_KEY, BASE_URL, MODEL


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return _client


_SYSTEM_PROMPT = """You are an expert Python code debugger. Given a script and its error output, analyze the root cause and provide a fix strategy.

Common error patterns:
- Network errors (Cannot connect, Temporary failure in name resolution, Connection refused, timeout): the environment HAS network access, so retry with correct URL, add retries, or check the host/service is reachable.
- ImportError/Missing package: add the missing package to requirements list.
- Syntax errors: fix the syntax.
- File not found: check path exists before reading.

Respond with valid JSON in exactly this format (no markdown, no code fences):
{"error_analysis": "root cause explanation", "correction_strategy": "specific fix strategy", "confidence": 0.95}"""


def analyze_error(script: str, stderr: str, user_prompt: str) -> CritiqueResponse:
    client = _get_client()

    user_content = (
        f"User intent: {user_prompt}\n\n"
        f"Script:\n```python\n{script}\n```\n\n"
        f"Error:\n```\n{stderr}\n```"
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=2000,
        temperature=0.1,
    )

    raw = response.choices[0].message.content or "{}"
    return _parse_json(raw)


def _parse_json(raw: str) -> CritiqueResponse:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        return CritiqueResponse(
            error_analysis=data.get("error_analysis", ""),
            correction_strategy=data.get("correction_strategy", ""),
            confidence=float(data.get("confidence", 0.0)),
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        return CritiqueResponse(
            error_analysis=raw[:500],
            correction_strategy="Review the error and fix syntax/import issues.",
            confidence=0.5,
        )
