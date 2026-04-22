from codec_through.session_bucketing import (
    classify_streaming_pair,
    is_degenerate_response,
)


def test_is_degenerate_on_parse_failure() -> None:
    assert is_degenerate_response(text="A", parse_failure=True)


def test_is_degenerate_on_marker() -> None:
    assert is_degenerate_response(text="addCriterion(foo)", parse_failure=False)


def test_clean_when_streaming_matches_cold() -> None:
    bucket = classify_streaming_pair(
        cold_choice="B",
        cold_correct=True,
        streaming_choice="B",
        streaming_correct=True,
        streaming_parse_failure=False,
        streaming_text="B",
    )
    assert bucket == "clean"


def test_mixed_when_streaming_clean_but_disagrees() -> None:
    bucket = classify_streaming_pair(
        cold_choice="B",
        cold_correct=True,
        streaming_choice="C",
        streaming_correct=False,
        streaming_parse_failure=False,
        streaming_text="C",
    )
    assert bucket == "mixed"


def test_degenerate_when_streaming_parse_fails() -> None:
    bucket = classify_streaming_pair(
        cold_choice="B",
        cold_correct=True,
        streaming_choice=None,
        streaming_correct=False,
        streaming_parse_failure=True,
        streaming_text="I cannot answer",
    )
    assert bucket == "degenerate"
