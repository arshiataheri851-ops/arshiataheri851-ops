from app.normalization import normalize_persian_text


def test_normalizes_arabic_yeh_and_kaf() -> None:
    assert normalize_persian_text("علي كیف") == "علی کیف"


def test_removes_diacritics_and_tatweel() -> None:
    assert normalize_persian_text("مُـتَن") == "متن"


def test_preserves_zwnj_and_collapses_whitespace() -> None:
    assert normalize_persian_text("می‌ روم   امروز") == "می‌ روم امروز"


def test_empty_input_stays_empty() -> None:
    assert normalize_persian_text("   ") == ""
