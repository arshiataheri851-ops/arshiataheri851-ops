import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers import MockProvider, ProviderResponse
from app.router import BudgetExceeded, GatewayService, rank_providers


class StubProvider:
    is_fallback = False

    def __init__(self, name, cost, latency, fails=False):
        self.name = name
        self.model = "stub-v1"
        self.cost_per_1k_tokens = cost
        self.latency_ms = latency
        self.fails = fails

    def complete(self, prompt, system_prompt, max_tokens):
        if self.fails:
            raise RuntimeError("simulated provider outage")
        return ProviderResponse(output=f"ok:{prompt}", model=self.model)


def test_priority_routing_changes_provider_order():
    cheap = StubProvider("cheap", 0.001, 900)
    fast = StubProvider("fast", 0.01, 100)
    assert rank_providers([fast, cheap], "low_cost")[0].name == "cheap"
    assert rank_providers([cheap, fast], "low_latency")[0].name == "fast"


def test_gateway_falls_back_after_primary_failure():
    service = GatewayService([
        StubProvider("remote", 0.002, 100, fails=True),
        MockProvider(),
    ])
    result = service.generate("hello", None, 40, 0.1, "balanced")
    assert result.provider == "local-mock"
    assert result.used_fallback is True
    assert "SIMULATED MOCK OUTPUT" in result.output


def test_budget_is_checked_before_provider_call():
    service = GatewayService([StubProvider("expensive", 10.0, 100)])
    with pytest.raises(BudgetExceeded):
        service.generate("hello", None, 100, 0.001, "low_cost")


def test_mock_gateway_api_works_without_credentials():
    client = TestClient(create_app(GatewayService([MockProvider()])))
    response = client.post(
        "/v1/chat/completions",
        json={"prompt": "Explain embeddings", "max_output_tokens": 80},
    )
    assert response.status_code == 200
    assert response.json()["provider"] == "local-mock"
    assert response.json()["used_fallback"] is False
