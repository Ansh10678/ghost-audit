import hashlib
import json
import os
import time
from typing import Any

from pydantic import BaseModel

from ..config import Config


class TokenUsage:
    def __init__(self):
        self.call_count: int = 0
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0

    def add_call(self, prompt_tokens: int, completion_tokens: int):
        self.call_count += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens

    def summary(self) -> dict[str, Any]:
        return {
            "call_count": self.call_count,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(
                (self.prompt_tokens / 1_000_000 * 0.15)
                + (self.completion_tokens / 1_000_000 * 0.60),
                4,
            ),
        }


global_usage = TokenUsage()


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        cache_dir: str | None = None,
    ):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model = model or Config.GEMINI_MODEL
        self.cache_dir = cache_dir or str(Config.CACHE_DIR)
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, prompt: str) -> str:
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{prompt_hash}.json")

    def generate_json(
        self,
        prompt: str,
        schema: type[BaseModel] | None = None,
        fallback: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Sends prompt to Gemini or returns cached response.
        If API key is missing or call fails, gracefully returns fallback.
        """
        cache_file = self._get_cache_path(prompt)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                return cached_data
            except Exception:
                pass

        if not self.api_key:
            return fallback or {}

        # Attempt API call with retries
        for attempt in range(max_retries):
            try:
                from google import genai

                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "temperature": 0.0,
                        "response_mime_type": "application/json",
                    },
                )
                txt = response.text or "{}"
                data = json.loads(txt)

                # Estimate token usage
                p_tok = len(prompt.split()) * 2
                c_tok = len(txt.split()) * 2
                global_usage.add_call(p_tok, c_tok)

                # Validate with schema if provided
                if schema:
                    schema.model_validate(data)

                # Cache result
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                return data
            except Exception:
                time.sleep(1.0 * (2**attempt))

        return fallback or {}
