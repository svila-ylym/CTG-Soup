import pytest

from app.services.soup_rules import average_score, validate_score


@pytest.mark.parametrize("score", [1, 1.5, 5, 9.5, 10])
def test_validate_score_accepts_half_steps(score):
    assert validate_score(score) == score


@pytest.mark.parametrize("score", [0, 1.25, 10.5])
def test_validate_score_rejects_out_of_range_or_non_half_step(score):
    with pytest.raises(ValueError):
        validate_score(score)


def test_average_score_returns_rounded_value_and_count():
    assert average_score([7.5, 8.0, 9.0]) == (8.17, 3)


def test_average_score_empty_is_zero():
    assert average_score([]) == (0.0, 0)
