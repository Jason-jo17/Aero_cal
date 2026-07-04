import os

# Provider-agnostic model aliases. LiteLLM resolves the provider from the
# model string prefix (anthropic/, openai/, gemini/, ...) and reads API keys
# from the matching standard env var (ANTHROPIC_API_KEY, OPENAI_API_KEY, ...).
# Swapping providers is an env var change, not a code change.
MODEL_ALIASES = {
    "default": os.getenv("AI_AGENT_DEFAULT_MODEL", "anthropic/claude-sonnet-5"),
    "structured": os.getenv("AI_AGENT_STRUCTURED_MODEL", "anthropic/claude-sonnet-5"),
}

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
