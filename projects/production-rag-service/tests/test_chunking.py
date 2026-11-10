import pytest

from app.chunking import split_text


def test_chunks_cover_text_and_overlap():
    chunks = split_text("one two three four five six", chunk_size=3, overlap=1)
    assert [chunk.text for chunk in chunks] == [
        "one two three", "three four five", "five six"
    ]


def test_empty_text_returns_no_chunks():
    assert split_text("   ") == []


def test_invalid_overlap_rejected():
    with pytest.raises(ValueError):
        split_text("hello", chunk_size=3, overlap=3)
