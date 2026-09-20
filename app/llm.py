"""
LLM Client
==========
Thin wrapper around the Anthropic API so every agent can reason with
a real model instead of rules, once ANTHROPIC_API_KEY is set.

Falls back gracefully (raises LLMUnavailable) if no key is set, so
the app still runs end-to-end without one — agents that call this
catch that and fall back to their rule-based path.
"""
import os

_MODEL = os.environ.get("TRAVELPILOT_MODEL", "claude-sonnet-4-6")
_client = None


class LLMUnavailable(Exception):
    pass


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMUnavailable("ANTHROPIC_API_KEY not set")
    try:
        import anthropic
    except ImportError:
        raise LLMUnavailable("anthropic package not installed — pip install anthropic")
    _client = anthropic.Anthropic(api_key=api_key)
    return _client


def complete(system: str, user_message: str, max_tokens: int = 400) -> str:
    """Single-turn completion. Raises LLMUnavailable if no key/package."""
    client = _get_client()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    return "".join(parts).strip()
