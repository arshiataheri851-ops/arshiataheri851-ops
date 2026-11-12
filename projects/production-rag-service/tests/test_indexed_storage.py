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
    # Reopening the same file exercises the idempotent index initialization.
    reopened = SQLiteStore(path)
    assert reopened.search_chunks("legacyindexword", 1)[0]["document_id"] == "legacy"


def test_fts_search_normalizes_arabic_persian_letter_variants(tmp_path):
    store = SQLiteStore(str(tmp_path / "persian.sqlite3"))
    store.upsert_document("arabic", "Arabic spelling", None, {}, ["متن عربي درباره كيان"])
    result = store.search_chunks("متن فارسی درباره کیان", 3)
    assert result[0]["document_id"] == "arabic"
