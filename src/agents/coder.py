import json
import re
from openai import OpenAI
from src.models import CodeResponse
from src.config import API_KEY, BASE_URL, MODEL


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return _client


_SYSTEM_PROMPT = """You are an expert Python code generator. Given a user's intent, produce a runnable Python script.

Rules:
- Output ONLY valid Python code that can execute in an isolated environment.
- Include all necessary imports.
- Use print() for any output you want the user to see.
- Do NOT use interactive functions like input().
- Do NOT access files outside /tmp or the current directory.
- If you generate charts/plots/images, save them to /tmp with a descriptive filename and print the path at the end.
- If you need external packages, list them in requirements.
- The execution environment HAS full network access. You may use urllib, requests, aiohttp, httpx, etc. to fetch remote data.
- Keep the script self-contained and focused.

Respond with valid JSON in exactly this format (no markdown, no code fences):
{"explanation": "brief explanation", "script": "python code here", "requirements": ["package1", "package2"]}"""


def generate_code(user_prompt: str, previous_error: str | None = None) -> CodeResponse:
    client = _get_client()

    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    if previous_error:
        user_content = (
            f"The previous attempt failed:\n\n{previous_error}\n\n"
            f"Fix the issue and rewrite. User intent: {user_prompt}"
        )
    else:
        user_content = user_prompt

    messages.append({"role": "user", "content": user_content})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=4000,
        temperature=0.1,
    )

    raw = response.choices[0].message.content or "{}"
    return _parse_json(raw, user_prompt)


def _parse_json(raw: str, fallback_prompt: str) -> CodeResponse:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        return CodeResponse(
            explanation=data.get("explanation", ""),
            script=data.get("script", ""),
            requirements=data.get("requirements", []),
        )
    except json.JSONDecodeError:
        code_match = re.search(r"```python\n?(.*?)```", raw, re.DOTALL)
        if code_match:
            return CodeResponse(
                explanation="Extracted from code block",
                script=code_match.group(1).strip(),
                requirements=[],
            )
        return CodeResponse(
            explanation="Fallback: treated entire response as script",
            script=raw,
            requirements=[],
        )
