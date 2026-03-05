"""LLM client abstraction used by triage agents.

Backend selection supports:
1. Direct provider API keys (OpenAI / Anthropic)
2. OpenClaw runtime fallback (no provider key env vars needed)

This makes the skill usable inside OpenClaw out of the box, while still
supporting standalone CLI usage with direct provider keys.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from typing import Any

import httpx

# Provider/model defaults
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_BACKEND = "openclaw"  # openclaw-first for OpenClaw skill usage


def _normalize_backend(raw: str | None) -> str:
    v = (raw or DEFAULT_BACKEND).strip().lower()
    if v in {"auto", "openai", "anthropic", "openclaw"}:
        return v
    return DEFAULT_BACKEND


def _model_family(model: str | None) -> str:
    """Infer model family from model name.

    Returns: "openai" | "anthropic" | "unknown"
    """
    if not model:
        return "unknown"
    lower = model.lower()
    if lower.startswith("claude"):
        return "anthropic"
    if lower.startswith(("gpt", "o1", "o3", "o4", "chatgpt")):
        return "openai"
    return "unknown"


def _resolve_openai_model(requested_model: str | None) -> str:
    if _model_family(requested_model) == "openai" and requested_model:
        return requested_model
    return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)


def _resolve_anthropic_model(requested_model: str | None) -> str:
    if _model_family(requested_model) == "anthropic" and requested_model:
        return requested_model
    return os.getenv("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float | None = None,
    response_format: str = "text",
) -> str:
    """Make a single LLM call and return text response.

    Backend resolution (LLM_BACKEND=auto):
    - Prefer provider implied by model name if that key exists.
    - Else use whichever direct provider key exists.
    - Else fallback to OpenClaw runtime via `openclaw agent`.
    """
    requested_model = model or os.getenv("LLM_MODEL", DEFAULT_ANTHROPIC_MODEL)
    temp = temperature if temperature is not None else float(
        os.getenv("LLM_TEMPERATURE", str(DEFAULT_TEMPERATURE))
    )

    backend = _normalize_backend(os.getenv("LLM_BACKEND", DEFAULT_BACKEND))
    openai_key = bool(os.getenv("OPENAI_API_KEY"))
    anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    preferred_family = _model_family(requested_model)

    if backend == "openai":
        return await _call_openai(
            system_prompt,
            user_prompt,
            _resolve_openai_model(requested_model),
            temp,
            response_format,
        )

    if backend == "anthropic":
        return await _call_anthropic(
            system_prompt,
            user_prompt,
            _resolve_anthropic_model(requested_model),
            temp,
            response_format,
        )

    if backend == "openclaw":
        return await _call_openclaw_agent(system_prompt, user_prompt, response_format)

    # backend == auto
    if preferred_family == "openai" and openai_key:
        return await _call_openai(
            system_prompt,
            user_prompt,
            _resolve_openai_model(requested_model),
            temp,
            response_format,
        )

    if preferred_family == "anthropic" and anthropic_key:
        return await _call_anthropic(
            system_prompt,
            user_prompt,
            _resolve_anthropic_model(requested_model),
            temp,
            response_format,
        )

    if openai_key:
        return await _call_openai(
            system_prompt,
            user_prompt,
            _resolve_openai_model(requested_model),
            temp,
            response_format,
        )

    if anthropic_key:
        return await _call_anthropic(
            system_prompt,
            user_prompt,
            _resolve_anthropic_model(requested_model),
            temp,
            response_format,
        )

    # No direct provider keys available: use OpenClaw runtime.
    return await _call_openclaw_agent(system_prompt, user_prompt, response_format)


async def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    """Make an LLM call and parse response as JSON object."""
    response = await call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt + "\n\nRespond with valid JSON only.",
        model=model,
        temperature=temperature,
        response_format="json",
    )
    return _parse_json_object(response)


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    return cleaned


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    """Parse response text into a JSON object, with forgiving extraction."""
    text = _strip_code_fences(raw_text)

    # First pass: direct parse.
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Second pass: extract likely JSON object span.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        data2 = json.loads(candidate)
        if isinstance(data2, dict):
            return data2

    raise json.JSONDecodeError("Response is not a JSON object", text, 0)


async def _call_anthropic(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    response_format: str,
) -> str:
    """Call Anthropic Messages API."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    _ = response_format  # Anthropic endpoint here uses prompt-level JSON constraints.

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
        data: dict[str, Any] = response.json()

    content = data.get("content", [])
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    return text

    raise RuntimeError("Anthropic response missing text content")


async def _call_openai(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    response_format: str,
) -> str:
    """Call OpenAI Chat Completions API."""
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
        data: dict[str, Any] = response.json()

    choices = data.get("choices", [])
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message", {})
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content

    raise RuntimeError("OpenAI response missing message content")


def _build_openclaw_prompt(system_prompt: str, user_prompt: str, response_format: str) -> str:
    lines = [
        "You are serving as an internal model backend for a Python pipeline.",
        "Do not call any tools.",
        "Do not ask follow-up questions.",
        "Follow the instructions exactly and return only the requested output.",
    ]
    if response_format == "json":
        lines.append("Return valid JSON only (no markdown fences, no explanation).")

    lines.extend(
        [
            "",
            "SYSTEM INSTRUCTIONS:",
            system_prompt.strip(),
            "",
            "USER INPUT:",
            user_prompt.strip(),
        ]
    )
    return "\n".join(lines)


async def _call_openclaw_agent(
    system_prompt: str,
    user_prompt: str,
    response_format: str,
) -> str:
    """Use OpenClaw runtime as the LLM backend (no provider key env required)."""
    if shutil.which("openclaw") is None:
        raise ValueError("openclaw CLI not found; cannot use OpenClaw backend")

    prompt = _build_openclaw_prompt(system_prompt, user_prompt, response_format)
    agent_id = os.getenv("OPENCLAW_LLM_AGENT", "main")
    timeout_s = float(os.getenv("OPENCLAW_LLM_TIMEOUT_SECONDS", "180"))
    thinking = os.getenv("OPENCLAW_LLM_THINKING", "")

    cmd: list[str] = [
        "openclaw",
        "agent",
        "--agent",
        agent_id,
        "--message",
        prompt,
        "--json",
    ]
    if thinking:
        cmd.extend(["--thinking", thinking])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError as exc:
        proc.kill()
        await proc.communicate()
        raise TimeoutError(f"OpenClaw backend call timed out after {timeout_s:.0f}s") from exc

    stdout_text = stdout.decode("utf-8", errors="replace").strip()
    stderr_text = stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        detail = stderr_text or stdout_text or "unknown OpenClaw backend error"
        raise RuntimeError(f"OpenClaw backend failed: {detail}")

    data: dict[str, Any]
    try:
        parsed = json.loads(stdout_text)
        if not isinstance(parsed, dict):
            raise RuntimeError("OpenClaw backend returned non-object JSON")
        data = parsed
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "OpenClaw backend returned non-JSON output"
            + (f": {stdout_text[:400]}" if stdout_text else "")
        ) from exc

    result = data.get("result", {})
    payloads: list[dict[str, Any]] = []
    if isinstance(result, dict):
        raw_payloads = result.get("payloads", [])
        if isinstance(raw_payloads, list):
            payloads = [p for p in raw_payloads if isinstance(p, dict)]

    texts = [p.get("text", "") for p in payloads if isinstance(p.get("text"), str)]
    merged = "\n".join(t.strip() for t in texts if t and t.strip()).strip()
    if merged:
        return merged

    raise RuntimeError("OpenClaw backend returned no text payload")
