"""Provider-agnostic LLM access (v2: real token streaming).

Talks to any OpenAI-compatible endpoint (OpenRouter by default). Structured
output is enforced client-side: JSON requested against a pydantic schema,
validated, with validation errors fed back for bounded retries — works on any
cheap model.

Streaming: when `on_text` is given, the request streams and the characters of
selected string fields ("message", "observation") are emitted as they arrive,
via a small progressive partial-JSON scanner. Everything else renders on
completion. This is honest live typing: real tokens, no simulation.
"""

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field

from openai import OpenAI
from pydantic import BaseModel, ValidationError

def _load_dotenv() -> None:
    """Tiny .env loader (no dependency): project-root .env, never overrides."""
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(env_file):
        return
    for line in open(env_file, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

DEFAULT_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("KNOWLEDGE_ENGINE_MODEL", "deepseek/deepseek-chat")

SUGGESTED_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "deepseek/deepseek-chat",
    "google/gemini-2.0-flash-001",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.3-70b-instruct",
]

MAX_JSON_RETRIES = 2
STREAM_FIELDS = ("message", "observation")


class BudgetExhausted(RuntimeError):
    pass


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    def add(self, other: "Usage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens


class _FieldStreamer:
    """Scans a JSON char stream and emits chars of selected string fields."""

    def __init__(self, fields: tuple[str, ...], emit: Callable[[str], None]):
        self._patterns = [f'"{f}"' for f in fields]
        self._emit = emit
        self._buf = ""
        self._in_field = False
        self._escape = False

    def feed(self, chunk: str) -> None:
        for ch in chunk:
            if self._in_field:
                if self._escape:
                    self._emit({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(ch, ch))
                    self._escape = False
                elif ch == "\\":
                    self._escape = True
                elif ch == '"':
                    self._in_field = False
                    self._emit("\n")
                else:
                    self._emit(ch)
                continue
            self._buf += ch
            if ch == '"':
                # Did the buffer just open a value-string for a tracked key?
                head = self._buf[:-1].rstrip()
                if head.endswith(":"):
                    head = head[:-1].rstrip()
                    if any(head.endswith(p) for p in self._patterns):
                        self._in_field = True
            self._buf = self._buf[-120:]


@dataclass
class LLM:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    token_budget: int = 0  # 0 = unlimited
    usage: Usage = field(default_factory=Usage)

    def __post_init__(self) -> None:
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _check_budget(self) -> None:
        if self.token_budget and self.usage.total >= self.token_budget:
            raise BudgetExhausted(
                f"Token budget exhausted: {self.usage.total:,}/{self.token_budget:,}"
            )

    def complete_json(
        self,
        system: str,
        user: str,
        schema: type[BaseModel],
        on_text: Callable[[str], None] | None = None,
    ) -> BaseModel:
        """Ask for JSON matching `schema`; validate and retry on bad output."""
        self._check_budget()
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
        for attempt in range(1 + MAX_JSON_RETRIES):
            raw = self._call(messages, on_text if attempt == 0 else None)
            raw = _strip_fences(raw)
            try:
                return schema.model_validate_json(raw)
            except ValidationError as err:
                last_error = err
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": (
                        "Your JSON failed validation with the errors below. "
                        f"Return the corrected JSON object only.\n{err}"
                    ),
                })
        raise RuntimeError(f"Model returned invalid JSON after retries: {last_error}")

    def _call(self, messages: list[dict], on_text) -> str:
        if on_text is None:
            response = self._client.chat.completions.create(
                model=self.model, messages=messages, temperature=0,
            )
            if response.usage:
                self.usage.add(Usage(response.usage.prompt_tokens, response.usage.completion_tokens))
            return (response.choices[0].message.content or "").strip()

        streamer = _FieldStreamer(STREAM_FIELDS, on_text)
        parts: list[str] = []
        stream = self._client.chat.completions.create(
            model=self.model, messages=messages, temperature=0,
            stream=True, stream_options={"include_usage": True},
        )
        for event in stream:
            if getattr(event, "usage", None):
                self.usage.add(Usage(event.usage.prompt_tokens, event.usage.completion_tokens))
            if event.choices and event.choices[0].delta and event.choices[0].delta.content:
                delta = event.choices[0].delta.content
                parts.append(delta)
                streamer.feed(delta)
        return "".join(parts).strip()


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()
