"""Canonical runtime artifact paths for the production workflow."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProductionPaths:
    root: Path

    @property
    def raw(self) -> Path:
        return self.root / "raw" / "projectx"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def live(self) -> Path:
        return self.root / "live-state"

    @property
    def recaps(self) -> Path:
        return self.root / "recaps"

    @property
    def plans(self) -> Path:
        return self.root / "production" / "plans"

    @property
    def comparisons(self) -> Path:
        return self.root / "production" / "comparisons"

    def ensure(self) -> "ProductionPaths":
        for directory in (
            self.raw, self.logs, self.state, self.reports, self.live,
            self.recaps, self.plans, self.comparisons,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return self


def production_paths(project_root: str | Path, data_dir: str | Path | None = None) -> ProductionPaths:
    root = Path(data_dir) if data_dir is not None else Path(project_root) / "data"
    return ProductionPaths(root=root).ensure()
