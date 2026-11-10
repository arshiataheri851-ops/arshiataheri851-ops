import pytest

from app.pipeline import EventPipeline


def event(event_id="evt-1", event_type="purchase", occurred_at="2026-11-10T10:01:15Z", value=12.5):
    return {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "value": value,
    }


def test_ingest_valid_event_and_count(tmp_path):
    pipeline = EventPipeline(tmp_path / "events.db")
    result = pipeline.ingest(event())
    assert result.status == "accepted"
    assert not result.duplicate
    assert pipeline.counts() == {"events": 1, "dead_letters": 0}


def test_duplicate_event_is_idempotent(tmp_path):
    pipeline = EventPipeline(tmp_path / "events.db")
    pipeline.ingest(event())
    duplicate = pipeline.ingest(event())
    assert duplicate.duplicate
    assert pipeline.counts()["events"] == 1


def test_invalid_event_is_sent_to_dead_letter_queue(tmp_path):
    pipeline = EventPipeline(tmp_path / "events.db")
    result = pipeline.ingest({"event_id": "bad", "event_type": "click", "value": "not-a-number"})
    assert result.status == "rejected"
    assert pipeline.counts() == {"events": 0, "dead_letters": 1}


def test_naive_timestamp_is_rejected(tmp_path):
    pipeline = EventPipeline(tmp_path / "events.db")
    result = pipeline.ingest(event(occurred_at="2026-11-10T10:01:15"))
    assert result.status == "rejected"
    assert pipeline.counts()["dead_letters"] == 1


def test_boolean_is_not_accepted_as_numeric_value(tmp_path):
    pipeline = EventPipeline(tmp_path / "events.db")
    assert pipeline.ingest(event(value=True)).status == "rejected"


def test_rebuild_aggregates_groups_events_by_window(tmp_path):
    pipeline = EventPipeline(tmp_path / "events.db")
    pipeline.ingest(event("a", "purchase", "2026-11-10T10:01:15Z", 2))
    pipeline.ingest(event("b", "purchase", "2026-11-10T10:01:50Z", 3))
    pipeline.ingest(event("c", "view", "2026-11-10T10:02:10Z", 7))
    assert pipeline.rebuild_aggregates(1) == 2
    aggregates = pipeline.get_aggregates()
    assert aggregates[0]["event_count"] == 2
    assert aggregates[0]["value_sum"] == 5
    assert aggregates[1]["event_type"] == "view"


def test_rebuild_is_replayable_and_replaces_old_aggregates(tmp_path):
    pipeline = EventPipeline(tmp_path / "events.db")
    pipeline.ingest(event())
    pipeline.rebuild_aggregates()
    first = pipeline.get_aggregates()
    pipeline.rebuild_aggregates()
    assert pipeline.get_aggregates() == first


def test_invalid_window_size_raises(tmp_path):
    pipeline = EventPipeline(tmp_path / "events.db")
    with pytest.raises(ValueError, match="positive integer"):
        pipeline.rebuild_aggregates(0)


def test_events_persist_across_instances(tmp_path):
    database = tmp_path / "events.db"
    EventPipeline(database).ingest(event())
    assert EventPipeline(database).counts()["events"] == 1


def test_non_finite_value_is_rejected(tmp_path):
    pipeline = EventPipeline(tmp_path / "events.db")
    assert pipeline.ingest(event(value=float("nan"))).status == "rejected"


def test_windowing_handles_windows_larger_than_one_hour(tmp_path):
    pipeline = EventPipeline(tmp_path / "events.db")
    pipeline.ingest(event("a", "purchase", "2026-11-10T10:15:00Z", 1))
    pipeline.ingest(event("b", "purchase", "2026-11-10T11:15:00Z", 2))
    assert pipeline.rebuild_aggregates(90) == 2
