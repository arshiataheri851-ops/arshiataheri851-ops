import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from app.config import Settings, get_settings
from app.normalization import normalize_persian_text
from app.predictor import HuggingFaceSentimentPredictor
from app.schemas import (
    BatchSentimentInput,
    BatchSentimentOutput,
    SentimentInput,
    SentimentOutput,
)

logger = logging.getLogger(__name__)
API_VERSION = "1.0.0"


def create_app(
    settings: Settings | None = None,
    predictor: Any | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(
        title="FarsiPulse — Persian Sentiment Intelligence API",
        description=(
            "Binary Persian review sentiment inference with conservative text normalization "
            "and a lazily loaded, revision-pinned Hugging Face model."
        ),
        version=API_VERSION,
    )
    app.state.predictor = predictor or HuggingFaceSentimentPredictor(app_settings)

    @app.get("/", tags=["service"])
    def root() -> dict[str, str]:
        return {
            "service": "farsipulse",
            "version": API_VERSION,
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health", tags=["service"])
    def health(request: Request) -> dict[str, Any]:
        model_loaded = bool(getattr(request.app.state.predictor, "is_loaded", False))
        return {
            "status": "ok",
            "model_loaded": model_loaded,
            "model_id": app_settings.model_id,
            "model_revision": app_settings.model_revision,
        }

    @app.post("/v1/sentiment", response_model=SentimentOutput, tags=["inference"])
    def predict_one(payload: SentimentInput, request: Request) -> SentimentOutput:
        normalized = normalize_persian_text(payload.text)
        try:
            prediction = request.app.state.predictor.predict_many([normalized])[0]
        except Exception as exc:
            logger.exception("Sentiment inference failed")
            raise HTTPException(
                status_code=503,
                detail="The sentiment model is unavailable. Check model dependencies and access.",
            ) from exc

        return SentimentOutput(
            text=payload.text,
            normalized_text=normalized,
            sentiment=prediction["sentiment"],
            confidence=prediction["confidence"],
            scores=prediction["scores"],
            model=app_settings.model_id,
        )

    @app.post(
        "/v1/sentiment/batch",
        response_model=BatchSentimentOutput,
        tags=["inference"],
    )
    def predict_batch(payload: BatchSentimentInput, request: Request) -> BatchSentimentOutput:
        normalized_texts: Sequence[str] = [
            normalize_persian_text(item.text) for item in payload.items
        ]
        try:
            predictions = request.app.state.predictor.predict_many(normalized_texts)
        except Exception as exc:
            logger.exception("Batch sentiment inference failed")
            raise HTTPException(
                status_code=503,
                detail="The sentiment model is unavailable. Check model dependencies and access.",
            ) from exc

        outputs = [
            SentimentOutput(
                text=item.text,
                normalized_text=normalized,
                sentiment=prediction["sentiment"],
                confidence=prediction["confidence"],
                scores=prediction["scores"],
                model=app_settings.model_id,
            )
            for item, normalized, prediction in zip(
                payload.items, normalized_texts, predictions, strict=True
            )
        ]
        return BatchSentimentOutput(predictions=outputs, count=len(outputs))

    return app


app = create_app()
