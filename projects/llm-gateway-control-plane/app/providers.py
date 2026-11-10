import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ProviderResponse:
    output: str
    model: str


class ChatProvider(Protocol):
    name: str
    model: str
    cost_per_1k_tokens: float
    latency_ms: int
    is_fallback: bool

    def complete(self, prompt: str, system_prompt: str | None, max_tokens: int) -> ProviderResponse:
        ...


class MockProvider:
    name = "local-mock"
    model = "mock-v1"
    cost_per_1k_tokens = 0.0
    latency_ms = 50_000
    is_fallback = True

    def complete(self, prompt: str, system_prompt: str | None, max_tokens: int) -> ProviderResponse:
        del system_prompt, max_tokens
        return ProviderResponse(
            output=f"[SIMULATED MOCK OUTPUT — no model was called] {prompt[:240]}",
            model=self.model,
        )


class OpenAICompatibleProvider:
    name = "openai-compatible"
    is_fallback = False

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        cost_per_1k_tokens: float = 0.002,
        latency_ms: int = 900,
        timeout_seconds: float = 20,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.latency_ms = latency_ms
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "OpenAICompatibleProvider | None":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        return cls(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )

    def complete(self, prompt: str, system_prompt: str | None, max_tokens: int) -> ProviderResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }).encode("utf-8")
        request = Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("Provider request failed") from exc

        try:
            output = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Provider returned an unexpected response") from exc
        if not isinstance(output, str):
            raise RuntimeError("Provider response content was not text")
        return ProviderResponse(output=output, model=data.get("model", self.model))
