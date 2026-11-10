from dataclasses import dataclass

from app.providers import ChatProvider, ProviderResponse


class BudgetExceeded(Exception):
    """No configured provider fits within the request budget."""


class GatewayUnavailable(Exception):
    """All eligible providers failed."""


@dataclass(frozen=True)
class GatewayResult:
    provider: str
    model: str
    output: str
    estimated_cost_usd: float
    used_fallback: bool


def rank_providers(providers: list[ChatProvider], priority: str) -> list[ChatProvider]:
    def key(provider: ChatProvider) -> tuple[float, int] | tuple[int, float] | float:
        if priority == "low_cost":
            return (provider.cost_per_1k_tokens, provider.latency_ms)
        if priority == "low_latency":
            return (provider.latency_ms, provider.cost_per_1k_tokens)
        return provider.latency_ms / 1000 + provider.cost_per_1k_tokens * 10

    return sorted(providers, key=key)


class GatewayService:
    def __init__(self, providers: list[ChatProvider], retries: int = 1) -> None:
        self.providers = providers
        self.retries = max(0, min(retries, 2))

    def generate(
        self,
        prompt: str,
        system_prompt: str | None,
        max_output_tokens: int,
        budget_usd: float,
        priority: str,
    ) -> GatewayResult:
        estimated_tokens = (len(prompt) + len(system_prompt or "") + 3) // 4
        estimated_tokens += max_output_tokens
        primary = rank_providers(
            [provider for provider in self.providers if not provider.is_fallback],
            priority,
        )
        fallbacks = [provider for provider in self.providers if provider.is_fallback]
        candidates = primary + fallbacks
        if not candidates:
            raise GatewayUnavailable("No providers are configured")

        eligible = []
        for provider in candidates:
            estimate = estimated_tokens * provider.cost_per_1k_tokens / 1000
            if estimate <= budget_usd:
                eligible.append((provider, estimate))
        if not eligible:
            raise BudgetExceeded("No provider fits within the requested budget")

        last_error = None
        for index, (provider, estimate) in enumerate(eligible):
            for _ in range(self.retries + 1):
                try:
                    response: ProviderResponse = provider.complete(
                        prompt, system_prompt, max_output_tokens
                    )
                    return GatewayResult(
                        provider=provider.name,
                        model=response.model,
                        output=response.output,
                        estimated_cost_usd=round(estimate, 8),
                        used_fallback=provider.is_fallback and bool(primary),
                    )
                except Exception as exc:
                    last_error = type(exc).__name__
        raise GatewayUnavailable(
            f"All eligible providers failed (last error: {last_error or 'unknown'})"
        )
