from __future__ import annotations
import os
import json
import re
from typing import Optional, Dict, Any

from mistralai import Mistral
from jsonschema import validate as js_validate, ValidationError  # type: ignore


_CLIENT: Optional[Mistral] = None


def _get_client() -> Mistral:
    global _CLIENT
    if _CLIENT is None:
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY non définie")
        _CLIENT = Mistral(api_key=api_key)
    return _CLIENT


def is_configured() -> bool:
    """Return True if Mistral API key is available."""
    return os.environ.get("MISTRAL_API_KEY") is not None


def list_models() -> list[str]:
    """Return available Mistral models."""
    return [
        "mistral-small-latest",
        "mistral-medium-latest", 
        "mistral-large-latest",
        "open-mistral-7b",
        "open-mixtral-8x7b"
    ]


def has_model(name: str) -> bool:
    """Check if model name is valid."""
    if not name:
        return False
    return name in list_models()


def chat(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
) -> str:
    """Chat with Mistral API, return text or empty string on error."""
    try:
        client = _get_client()
        model = model or os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.complete(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens or 1024,
        )
        
        return response.choices[0].message.content or ""
    except Exception:
        # Any error: return empty to fallback to heuristics
        return ""


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = re.sub(r"^```(json)?\n|\n```$", "", text.strip(), flags=re.IGNORECASE)
    m = re.search(r"\{[\s\S]*\}$", text)
    blob = m.group(0) if m else text
    try:
        return json.loads(blob)
    except Exception:
        m2 = re.search(r"\{[\s\S]*?\}", text)
        if m2:
            try:
                return json.loads(m2.group(0))
            except Exception:
                return None
    return None


def chat_json(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    text = chat(prompt, system=system, model=model, temperature=temperature, max_tokens=max_tokens)
    return _extract_json(text)


def chat_json_schema(
    prompt: str,
    schema: Dict[str, Any],
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    data = chat_json(prompt, system=system, model=model, temperature=temperature, max_tokens=max_tokens)
    if not isinstance(data, dict):
        return None
    try:
        js_validate(instance=data, schema=schema)
        return data
    except ValidationError:
        return None
