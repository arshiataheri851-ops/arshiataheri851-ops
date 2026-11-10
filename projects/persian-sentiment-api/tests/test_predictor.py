from app.config import Settings
from app.predictor import HuggingFaceSentimentPredictor


class FakePipeline:
    def __call__(self, texts, **kwargs):
        assert kwargs["top_k"] is None
        return [
            [
                {"label": "HAPPY", "score": 0.8},
                {"label": "SAD", "score": 0.2},
            ]
            for _ in texts
        ]


def test_predictor_maps_upstream_labels_to_api_labels():
    predictor = HuggingFaceSentimentPredictor(
        Settings(model_id="fake", model_revision="fake")
    )
    predictor._pipeline = FakePipeline()

    result = predictor.predict_many(["نظر فارسی"])

    assert result == [
        {
            "sentiment": "positive",
            "confidence": 0.8,
            "scores": {"positive": 0.8, "negative": 0.2},
        }
    ]


def test_predictor_handles_multiple_texts():
    predictor = HuggingFaceSentimentPredictor(
        Settings(model_id="fake", model_revision="fake")
    )
    predictor._pipeline = FakePipeline()

    results = predictor.predict_many(["متن اول", "متن دوم"])

    assert len(results) == 2
    assert all(item["sentiment"] == "positive" for item in results)
