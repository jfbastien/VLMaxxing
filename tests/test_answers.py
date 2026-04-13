from codec_through.answers import extract_choice


def test_extract_choice_parses_letter_prefix() -> None:
    assert extract_choice("B. second option", ["first", "second", "third"]) == 1


def test_extract_choice_returns_none_on_failure() -> None:
    assert extract_choice("I am not sure.", ["first", "second", "third"]) is None


def test_extract_choice_can_default_on_failure() -> None:
    assert (
        extract_choice(
            "I am not sure.",
            ["first", "second", "third"],
            default_index_on_failure=0,
        )
        == 0
    )


def test_extract_choice_returns_none_on_ambiguous_letter_output() -> None:
    assert extract_choice("I think A or B.", ["first", "second", "third"]) is None


def test_extract_choice_can_default_on_ambiguous_letter_output() -> None:
    assert (
        extract_choice(
            "I think A or B.",
            ["first", "second", "third"],
            default_index_on_failure=0,
        )
        == 0
    )


def test_extract_choice_returns_none_when_text_match_is_ambiguous() -> None:
    candidates = ["red apple", "apple pie", "pear"]
    assert extract_choice("The answer mentions apple.", candidates) is None
