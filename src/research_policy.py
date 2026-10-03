"""Dataset labels are governance facts, independent of observed profitability."""
from __future__ import annotations

from pathlib import Path
import yaml

DEFAULT_POLICY = Path(__file__).resolve().parents[1] / 'config/research_policy.yaml'


def classify_years(years, policy_path=DEFAULT_POLICY):
    policy = yaml.safe_load(Path(policy_path).read_text())
    periods = policy['periods']
    return {str(int(year)): periods.get(int(year), 'unclassified_not_a_holdout')
            for year in sorted(set(years))}


def validate_classification(years, claimed, policy_path=DEFAULT_POLICY):
    actual = classify_years(years, policy_path)
    if claimed != actual:
        raise ValueError(f'Dataset classification disagrees with research policy: {actual}')
    return actual
