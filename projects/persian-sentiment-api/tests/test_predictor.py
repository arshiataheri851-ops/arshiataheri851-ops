from app.config import Settings
from app.predictor import HuggingFaceSentimentPredictor


class FakePipeline:
    def __call__(self, texts, **kwargs):
        assert kwargs["top_k"] is None
        assert kwargs["batch_size"] == 8
        return [
            [
                {"label": "HAPPY", "score": 0.8},
                {"label": "SAD", "score": 0.2},
            ]
            for _ in texts
        ]


def make_predictor() -> HuggingFaceSentimentPredictor:
    predictor = HuggingFaceSentimentPredictor(
        Settings(
            model_id="fake",
            model_revision="fake",
            inference_batch_size=8,
            cpu_threads=1,
        )
    )
    predictor._pipeline = FakePipeline()
    return predictor


def test_predictor_maps_upstream_labels_to_api_labels():
    result = make_predictor().predict_many(["نظر فارسی"])

    assert result == [
        {
            "sentiment": "positive",
            "confidence": 0.8,
            "scores": {"positive": 0.8, "negative": 0.2},
        }
    ]


def test_predictor_handles_multiple_texts():
    results = make_predictor().predict_many(["متن اول", "متن دوم"])

    assert len(results) == 2
    assert all(item["sentiment"] == "positive" for item in results)


def test_predictor_returns_empty_list_without_loading_model():
    predictor = make_predictor()
    predictor._pipeline = None

    assert predictor.predict_many([]) == []
    assert predictor.is_loaded is False
