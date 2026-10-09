import pytest
from research_policy import classify_years, validate_classification


def test_reused_years_never_become_holdouts():
    assert classify_years([2025, 2023, 2024, 2023]) == {
        '2023': 'development_research', '2024': 'development_research',
        '2025': 'development_research'}


def test_2026_and_future_are_not_automatically_untouched():
    assert classify_years([2026, 2027]) == {
        '2026': 'pseudo_out_of_sample_validation',
        '2027': 'unclassified_not_a_holdout'}


def test_invalid_holdout_claim_is_rejected():
    with pytest.raises(ValueError, match='classification'):
        validate_classification([2023], {'2023': 'untouched_holdout'})
