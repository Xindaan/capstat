"""Shared fixtures: loading reference cases and their archived datasets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import yaml

REFERENCES = Path(__file__).parent / "references"

# The StRD file format declares where its data block lives, e.g.
#   "Data            : lines 61 to 5060     (= 5000)"
# Parsing that line (rather than hard-coding 61) keeps the loader honest
# against the file it is actually reading.
_DATA_RANGE = re.compile(r"^\s*Data\s*:\s*lines\s+(\d+)\s+to\s+(\d+)", re.MULTILINE)


def load_strd_dataset(relative_path: str) -> npt.NDArray[np.float64]:
    """Load the observations from an archived NIST StRD ``.dat`` file."""
    path = REFERENCES / relative_path
    text = path.read_text()
    match = _DATA_RANGE.search(text)
    if match is None:
        raise ValueError(f"{path.name}: no 'Data: lines A to B' header found")
    start, end = int(match.group(1)), int(match.group(2))
    lines = text.splitlines()[start - 1 : end]
    return np.array([float(line.strip()) for line in lines], dtype=np.float64)


@dataclass(frozen=True)
class ReferenceCase:
    """One reference case: a dataset plus its certified values and tolerances."""

    id: str
    dataset: str
    description: str
    expected: dict[str, float]
    tolerance: dict[str, Any]

    def tolerance_for(self, statistic: str) -> tuple[float, float]:
        """Return ``(rel, abs)`` tolerance for one statistic."""
        per_statistic = self.tolerance.get("per_statistic", {})
        spec = per_statistic.get(statistic, self.tolerance)
        return float(spec.get("rel", 0.0)), float(spec.get("abs", 0.0))

    def data(self) -> npt.NDArray[np.float64]:
        return load_strd_dataset(self.dataset)


def load_reference_cases(yaml_name: str) -> list[ReferenceCase]:
    """Load and merge the cases of a reference YAML with its ``defaults``."""
    document = yaml.safe_load((REFERENCES / yaml_name).read_text())
    defaults = document.get("defaults", {})
    default_tolerance = defaults.get("tolerance", {})

    cases: list[ReferenceCase] = []
    for raw in document["cases"]:
        cases.append(
            ReferenceCase(
                id=raw["id"],
                dataset=raw["dataset"],
                description=raw.get("description", ""),
                expected=raw["expected"],
                tolerance=raw.get("tolerance", default_tolerance),
            )
        )
    return cases


def assert_within_tolerance(
    got: float, expected: float, rel: float, abs_: float, *, label: str
) -> None:
    """Assert ``got`` matches a certified ``expected`` within ``rel``/``abs_``.

    With both tolerances at zero this demands an exact (bit-for-bit) match,
    which is what the NIST datasets with exact certified values call for.
    """
    allowed = abs_ + rel * abs(expected)
    deviation = abs(got - expected)
    assert deviation <= allowed, (
        f"{label}: got {got!r}, certified {expected!r}; "
        f"deviation {deviation:.3e} exceeds allowed {allowed:.3e} "
        f"(rel={rel:g}, abs={abs_:g})"
    )
