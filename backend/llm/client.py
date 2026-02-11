"""Anthropic SDK client wrapper for LLM-powered scouting reports."""

import logging
import os

import anthropic

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """Get or create a singleton Anthropic client."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required for scouting reports"
            )
        _client = anthropic.Anthropic(api_key=api_key)
        logger.info("Initialized Anthropic client")
    return _client


def generate_text(
    system_prompt: str,
    user_prompt: str,
    model: str = "claude-sonnet-4-5-20250929",
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> str:
    """Generate text using Claude.

    Args:
        system_prompt: System-level instructions.
        user_prompt: User message with context.
        model: Claude model to use.
        max_tokens: Maximum response tokens.
        temperature: Sampling temperature (0.7 for creative but grounded reports).

    Returns:
        Generated text content.
    """
    client = get_client()
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text
