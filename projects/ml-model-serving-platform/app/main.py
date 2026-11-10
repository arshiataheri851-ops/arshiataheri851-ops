from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.model_service import ModelNotReadyError, ModelService


class PredictionInput(BaseModel):
    sepal_length: Annotated[float, Field(gt=0, le=10)]
    sepal_width: Annotated[float, Field(gt=0, le=10)]
    petal_length: Annotated[float, Field(gt=0, le=10)]
    petal_width: Annotated[float, Field(gt=0, le=10)]


class PredictionOutput(BaseModel):
    label: str
    confidence: float
    model_version: str


def create_app(model_service: ModelService | None = None) -> FastAPI:
    app = FastAPI(
        title="ML Model Serving Platform",
        description="A small, version-aware classification inference API.",
        version="0.1.0",
    )
    service = model_service or ModelService(
        Path(__file__).resolve().parents[1] / "artifacts" / "iris_model.joblib"
    )

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        return {"status": "ok", "model_ready": service.is_ready}

    @app.post("/predict", response_model=PredictionOutput)
    def predict(payload: PredictionInput) -> PredictionOutput:
        features = [
            payload.sepal_length,
            payload.sepal_width,
            payload.petal_length,
            payload.petal_width,
        ]
        try:
            result = service.predict(features)
        except ModelNotReadyError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=500, detail="Model inference failed.") from error
        return PredictionOutput(**result)

    return app


app = create_app()
