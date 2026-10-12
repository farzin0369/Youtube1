from app.spiritual_content import _remove_duplicate_sentences


def test_remove_duplicate_sentences_preserves_paragraphs_and_unique_sentences():
    repeated = "وقتی روز سختی داری، چند لحظه مکث کن و آرام نفس بکش."
    unique = "بعد از آن، یک کار کوچک را انتخاب کن و با حوصله انجام بده."
    result = _remove_duplicate_sentences(f"{repeated} {unique} {repeated}")

    assert result.count(repeated) == 1
    assert unique in result


def test_remove_duplicate_sentences_keeps_distinct_paragraphs():
    first = "وقتی خسته‌ای، چند لحظه آرام بنشین و به خودت فرصت بده."
    second = "برای فردا، تنها یک قدم روشن و عملی انتخاب کن."
    result = _remove_duplicate_sentences(f"{first}\n\n{second}")

    assert "\n\n" in result
    assert first in result
    assert second in result


def test_remove_duplicate_sentences_does_not_drop_distinct_persian_sentences():
    from app.spiritual_content import _remove_duplicate_sentences

    first = "وقتی در پایان ماه دخل‌وخرج را بررسی می‌کنی، هزینه‌های رفت‌وآمد را جداگانه یادداشت کن."
    second = "وقتی در پایان ماه دخل‌وخرج را بررسی می‌کنی، هزینه‌های درمان و دارو را جداگانه یادداشت کن."
    result = _remove_duplicate_sentences(f"{first}\n\n{second}")
    assert first in result
    assert second in result
    assert result.count("\n\n") == 1
