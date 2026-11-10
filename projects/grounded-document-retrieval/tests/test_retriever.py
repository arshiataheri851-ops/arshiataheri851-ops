from pathlib import Path

from app.retriever import DocumentRetriever


def test_search_returns_matching_source(tmp_path: Path) -> None:
    (tmp_path / "api.txt").write_text(
        "API request validation checks required fields and data types.\n\n"
        "Response schemas define the output contract.",
        encoding="utf-8",
    )
    (tmp_path / "other.txt").write_text(
        "A garden contains flowers and trees.",
        encoding="utf-8",
    )

    retriever = DocumentRetriever(tmp_path)
    results = retriever.search("required fields validation", top_k=2)

    assert results
    assert results[0]["source"] == "api.txt"


def test_empty_directory_returns_no_results(tmp_path: Path) -> None:
    retriever = DocumentRetriever(tmp_path)
    assert retriever.search("anything") == []
