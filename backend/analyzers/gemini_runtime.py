import asyncio
import json
import os
from typing import Any, Dict, List

import google.genai as genai


class LLMUnavailable(RuntimeError):
    pass


def parse_json_array(text: str) -> List[Dict[str, Any]]:
    if not isinstance(text, str):
        raise ValueError("LLM response was not text")

    lines = text.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

    data = json.loads("\n".join(lines).strip())
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("LLM response must be a JSON array of objects")
    return data


async def generate_json_array(prompt: str) -> List[Dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise LLMUnavailable("Gemini API key is unavailable")

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    timeout_seconds = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "45"))
    attempts = max(1, int(os.getenv("GEMINI_MAX_ATTEMPTS", "2")))
    error: Exception | None = None

    for _ in range(attempts):
        try:
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(model=model, contents=prompt),
                ),
                timeout=timeout_seconds,
            )
            return parse_json_array(response.text)
        except Exception as exc:
            error = exc

    raise LLMUnavailable("Gemini JSON generation was unavailable") from error
