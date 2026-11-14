from app.retrieval import tokenize
from app.store import SQLiteStore


def test_persian_variants_normalize_to_same_tokens():
    assert tokenize("ي ك") == tokenize("ی ک")


def test_fts_index_tracks_upsert_and_delete(tmp_path):
    store = SQLiteStore(str(tmp_path / "index.sqlite3"))
    store.upsert_document("first", "First", None, {}, ["شبکه عصبی برای تحلیل داده"])
    assert store.search_chunks("شبکه عصبی", 3)[0]["document_id"] == "first"

    store.upsert_document("first", "First revised", None, {}, ["سامانه پایگاه داده"])
    assert store.search_chunks("شبکه عصبی", 3) == []
    assert store.search_chunks("پایگاه داده", 3)[0]["title"] == "First revised"

    assert store.delete_document("first") is True
    assert store.search_chunks("پایگاه داده", 3) == []


def test_index_backfills_existing_database(tmp_path):
    path = str(tmp_path / "backfill.sqlite3")
    store = SQLiteStore(path)
    store.upsert_document("legacy", "Legacy", None, {}, ["legacyindexword"])
    reopened = SQLiteStore(path)
    assert reopened.search_chunks("legacyindexword", 1)[0]["document_id"] == "legacy"


def test_fts_search_normalizes_arabic_persian_letter_variants(tmp_path):
    store = SQLiteStore(str(tmp_path / "persian.sqlite3"))
    store.upsert_document("arabic", "Arabic spelling", None, {}, ["متن عربي درباره كيان"])
    result = store.search_chunks("متن فارسی درباره کیان", 3)
    assert result[0]["document_id"] == "arabic"


def test_fts_uses_same_nfkc_and_combining_mark_normalization(tmp_path):
    store = SQLiteStore(str(tmp_path / "unicode.sqlite3"))
    decomposed_yeh_hamza = "ه\u0654"
    store.upsert_document(
        "unicode", "Unicode", None, {},
        [f"متن {decomposed_yeh_hamza} برای آزمون"],
    )

    assert store.search_chunks("متن ۀ برای آزمون", 3)[0]["document_id"] == "unicode"
    assert store.search_chunks("متن ه برای آزمون", 3)[0]["document_id"] == "unicode"


def test_fts_normalization_remains_consistent_after_upsert(tmp_path):
    store = SQLiteStore(str(tmp_path / "unicode-upsert.sqlite3"))
    store.upsert_document("unicode", "Old", None, {}, ["متن ي درباره كيان"])
    assert store.search_chunks("متن ی درباره کیان", 3)

    store.upsert_document("unicode", "Updated", None, {}, ["متن ه\u0654 و داده"])
    assert store.search_chunks("متن ۀ و داده", 3)[0]["title"] == "Updated"
    assert store.search_chunks("درباره کیان", 3) == []


def test_in_memory_database_is_shared_across_store_connections():
    store = SQLiteStore(":memory:")
    store.upsert_document("memory", "Memory", None, {}, ["memoryindexword"])
    assert store.search_chunks("memoryindexword", 1)[0]["document_id"] == "memory"


def test_batch_upsert_rolls_back_all_documents_on_error():
    store = SQLiteStore(":memory:")
    try:
        store.upsert_documents_batch([
            {
                "document_id": "first", "title": "First", "source": None,
                "metadata": {}, "chunks": ["first anchor"],
            },
            {
                "document_id": "second", "title": "Second", "source": None,
                "metadata": {"invalid": object()}, "chunks": ["second anchor"],
            },
        ])
    except TypeError:
        pass
    else:
        raise AssertionError("invalid metadata should abort the complete batch")
    assert store.count_documents() == 0
    assert store.search_chunks("first anchor", 3) == []
