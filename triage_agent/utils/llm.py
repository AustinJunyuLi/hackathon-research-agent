"""LLM client abstraction — supports OpenAI and Anthropic backends.

Provides a unified interface for making LLM calls, with structured
output support via JSON mode.
"""

import json
import os
from typing import Any

import httpx

# Default model configuration
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_TEMPERATURE = 0.2


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float | None = None,
    response_format: str = "text",
) -> str:
    """Make a single LLM call and return the text response.

    Automatically selects the provider based on the model name:
    - Models starting with 'claude' use the Anthropic API
    - Models starting with 'gpt' or 'o1' use the OpenAI API

    Args:
        system_prompt: System message setting the LLM's role.
        user_prompt: User message with the actual query.
        model: Model identifier. Defaults to env LLM_MODEL or claude-sonnet-4-6.
        temperature: Sampling temperature. Defaults to env LLM_TEMPERATURE or 0.2.
        response_format: 'text' or 'json'.

    Returns:
        The LLM's text response.

    Raises:
        ValueError: If no API key is configured for the selected provider.
        httpx.HTTPError: On API errors.
    """
    model = model or os.getenv("LLM_MODEL", DEFAULT_MODEL)
    temperature = temperature if temperature is not None else float(
        os.getenv("LLM_TEMPERATURE", str(DEFAULT_TEMPERATURE))
    )

    if model.startswith("claude"):
        return await _call_anthropic(system_prompt, user_prompt, model, temperature, response_format)
    else:
        return await _call_openai(system_prompt, user_prompt, model, temperature, response_format)


async def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    """Make an LLM call and parse the response as JSON.

    Args:
        system_prompt: System message setting the LLM's role.
        user_prompt: User message. Should instruct the LLM to respond in JSON.
        model: Model identifier.
        temperature: Sampling temperature.

    Returns:
        Parsed JSON as a dictionary.

    Raises:
        json.JSONDecodeError: If the response is not valid JSON.
    """
    response = await call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt + "\n\nRespond with valid JSON only.",
        model=model,
        temperature=temperature,
        response_format="json",
    )
    # Strip markdown code fences if present
    text = response.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    return json.loads(text)


async def _call_anthropic(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    response_format: str,
) -> str:
    """Call the Anthropic Messages API."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


async def _call_openai(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    response_format: str,
) -> str:
    """Call the OpenAI Chat Completions API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    body: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if response_format == "json":
        body["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
