"""Provider-agnostic LLM access.

Talks to any OpenAI-compatible endpoint (OpenRouter by default, so cheap
models work out of the box). Structured output is enforced client-side:
the model is asked for JSON only, the reply is validated against a pydantic
schema, and validation errors are fed back for a bounded number of retries.
This works on every model, including ones without native json_schema support.
"""

import json
import os
from dataclasses import dataclass, field

from openai import OpenAI
from pydantic import BaseModel, ValidationError

DEFAULT_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("SPEC_ENGINE_MODEL", "deepseek/deepseek-chat")

# Cheap, JSON-reliable starting points on OpenRouter. Any model id works.
SUGGESTED_MODELS = [
    "deepseek/deepseek-chat",
    "google/gemini-2.0-flash-001",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.3-70b-instruct",
]

MAX_JSON_RETRIES = 2


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, other: "Usage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens


@dataclass
class LLM:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    usage: Usage = field(default_factory=Usage)

    def __post_init__(self) -> None:
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def complete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        """Ask for JSON matching `schema`; validate and retry on bad output."""
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        messages = [
            {
                "role": "system",
                "content": (
                    f"{system}\n\n"
                    "Reply with a single JSON object only - no markdown fences, no prose. "
                    f"It must validate against this JSON schema:\n{schema_json}"
                ),
            },
            {"role": "user", "content": user},
        ]

        last_error: Exception | None = None
        for _ in range(1 + MAX_JSON_RETRIES):
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
            )
            if response.usage:
                self.usage.add(
                    Usage(response.usage.prompt_tokens, response.usage.completion_tokens)
                )
            raw = (response.choices[0].message.content or "").strip()
            raw = _strip_fences(raw)
            try:
                return schema.model_validate_json(raw)
            except ValidationError as err:
                last_error = err
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your JSON failed validation with the errors below. "
                            f"Return the corrected JSON object only.\n{err}"
                        ),
                    }
                )
        raise RuntimeError(f"Model returned invalid JSON after retries: {last_error}")


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[: -3]
    return text.strip()
