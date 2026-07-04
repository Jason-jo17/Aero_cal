import json
from typing import Any, Dict, List

import litellm

from .config import MODEL_ALIASES


async def chat(messages: List[Dict[str, str]], alias: str = "default", **kwargs) -> str:
    """Free-text completion. Used for design-review explanations where no
    strict output shape is required."""
    response = await litellm.acompletion(
        model=MODEL_ALIASES[alias],
        messages=messages,
        temperature=kwargs.pop("temperature", 0.4),
        **kwargs,
    )
    return response.choices[0].message.content or ""


async def structured_chat(
    messages: List[Dict[str, str]], response_schema: Dict[str, Any], alias: str = "structured"
) -> Dict[str, Any]:
    """Structured JSON completion. `temperature=0` and a JSON-schema
    response_format reduce (but do not eliminate) malformed output — callers
    must still validate the result against their own Pydantic model rather
    than trusting the provider's schema enforcement claim."""
    response = await litellm.acompletion(
        model=MODEL_ALIASES[alias],
        messages=messages,
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "result", "schema": response_schema, "strict": True},
        },
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)
