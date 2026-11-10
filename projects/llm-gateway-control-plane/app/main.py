from fastapi import FastAPI, HTTPException

from app.providers import MockProvider, OpenAICompatibleProvider
from app.router import BudgetExceeded, GatewayService, GatewayUnavailable
from app.schemas import ChatRequest, ChatResponse


def build_service() -> GatewayService:
    providers = []
    remote = OpenAICompatibleProvider.from_environment()
    if remote is not None:
        providers.append(remote)
    providers.append(MockProvider())
    return GatewayService(providers=providers, retries=1)


def create_app(service: GatewayService | None = None) -> FastAPI:
    gateway = service or build_service()
    api = FastAPI(
        title="LLM Gateway Control Plane",
        version="1.0.0",
        description="Provider routing, budget preflight, retry, and fallback.",
    )

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.post("/v1/chat/completions", response_model=ChatResponse)
    def create_completion(payload: ChatRequest) -> ChatResponse:
        try:
            result = gateway.generate(
                prompt=payload.prompt,
                system_prompt=payload.system_prompt,
                max_output_tokens=payload.max_output_tokens,
                budget_usd=payload.budget_usd,
                priority=payload.priority,
            )
        except BudgetExceeded as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except GatewayUnavailable as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return ChatResponse(
            provider=result.provider,
            model=result.model,
            output=result.output,
            estimated_cost_usd=result.estimated_cost_usd,
            used_fallback=result.used_fallback,
        )

    return api


app = create_app()
