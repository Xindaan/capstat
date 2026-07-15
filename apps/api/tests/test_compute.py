"""Compute endpoints: shape, and fidelity to the core they wrap.

The recurring assertion is not "the endpoint returns 200" but "the endpoint
returns exactly what the core computed" -- same numbers, same warnings, same
nulls. The API is a serialisation layer; a test that only checked status codes
would let it quietly diverge from the library.
"""

from __future__ import annotations

import math
from typing import ClassVar

from capstat_core import (
    capability,
    cusum_chart,
    describe,
    ewma_chart,
    i_mr_chart,
    xbar_r_chart,
    xbar_s_chart,
)
from fastapi.testclient import TestClient

# A mildly non-normal but well-behaved series reused across cases.
SERIES = [10.0 + (i % 5) * 0.1 + (i % 3) * 0.05 for i in range(60)]


def test_descriptive_matches_core(client: TestClient) -> None:
    body = client.post("/compute/descriptive", json={"data": SERIES}).json()
    core = describe(SERIES)
    assert body["n"] == core.n
    assert body["mean"] == core.mean
    assert body["std_dev"] == core.std_dev
    assert body["skewness"] == core.skewness


def test_capability_matches_core_and_keeps_warnings(client: TestClient) -> None:
    resp = client.post(
        "/compute/capability",
        json={"data": SERIES, "lsl": 9.5, "usl": 11.0},
    )
    assert resp.status_code == 200
    body = resp.json()
    core = capability(SERIES, lsl=9.5, usl=11.0)
    assert body["cpk"] == core.cpk
    assert body["within_method"] == core.within_method
    # The warnings tuple must survive as a JSON array, not be flattened away.
    assert body["warnings"] == list(core.warnings)
    # The derived property is not a dataclass field; it must still be present.
    assert body["stability_ratio"] == core.stability_ratio


def test_capability_one_sided_spec_yields_null_indices(client: TestClient) -> None:
    # Only an upper limit: cp/cpl are undefined and must serialise as null,
    # which is not the same as 0.0.
    body = client.post(
        "/compute/capability",
        json={"data": SERIES, "usl": 11.0},
    ).json()
    assert body["cp"] is None
    assert body["cpl"] is None
    assert body["cpu"] is not None
    assert body["lsl"] is None


def test_capability_accepts_subgroups(client: TestClient) -> None:
    subgroups = [[10.0, 10.1, 9.9, 10.2, 10.0] for _ in range(20)]
    resp = client.post(
        "/compute/capability",
        json={"data": subgroups, "lsl": 9.0, "usl": 11.0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["subgroup_size"] == 5
    assert body["subgroups"] == 20


def test_capability_analyze_reports_path(client: TestClient) -> None:
    body = client.post(
        "/compute/capability/analyze",
        json={"data": SERIES, "lsl": 9.5, "usl": 11.0},
    ).json()
    assert body["path"] in {"normal", "box-cox", "percentile"}
    assert body["normality"] is not None
    # Exactly the branch named by `path` is populated; the others are null.
    populated = [k for k in ("normal", "box_cox", "percentile") if body[k]]
    assert len(populated) == 1


def test_i_mr_chart_shape_and_nesting(client: TestClient) -> None:
    body = client.post("/compute/control-chart/i-mr", json={"data": SERIES}).json()
    core = i_mr_chart(SERIES)
    assert body["location"]["in_control"] == core.location.in_control
    assert body["dispersion"]["limits"]["center"] == core.dispersion.limits.center
    assert body["in_control"] == core.in_control


def test_xbar_r_matches_core(client: TestClient) -> None:
    subgroups = [[10.0 + (i % 3) * 0.1, 10.1, 9.9, 10.2] for i in range(15)]
    body = client.post(
        "/compute/control-chart/xbar-r", json={"subgroups": subgroups}
    ).json()
    core = xbar_r_chart(subgroups)
    assert body["location"]["points"] == list(core.location.points)
    assert body["dispersion"]["name"] == core.dispersion.name
    assert body["subgroup_size"] == 4


def test_xbar_s_matches_core(client: TestClient) -> None:
    subgroups = [[10.0, 10.1, 9.9, 10.2, 10.05, 9.95] for _ in range(12)]
    body = client.post(
        "/compute/control-chart/xbar-s", json={"subgroups": subgroups}
    ).json()
    core = xbar_s_chart(subgroups)
    assert body["sigma_within"] == core.sigma_within
    assert body["in_control"] == core.in_control


def test_ewma_matches_core(client: TestClient) -> None:
    body = client.post(
        "/compute/control-chart/ewma",
        json={"data": SERIES, "target": 10.0, "sigma": 0.2},
    ).json()
    core = ewma_chart(SERIES, target=10.0, sigma=0.2)
    assert body["points"] == list(core.points)
    assert body["steady_state_limits"] == list(core.steady_state_limits)
    assert body["violations"] == list(core.violations)


def test_cusum_matches_core(client: TestClient) -> None:
    body = client.post(
        "/compute/control-chart/cusum",
        json={"data": SERIES, "target": 10.0, "sigma": 0.2},
    ).json()
    core = cusum_chart(SERIES, target=10.0, sigma=0.2)
    assert body["upper"] == list(core.upper)
    assert body["H"] == core.H


def test_nan_serialises_as_null(client: TestClient) -> None:
    # A constant series has zero variance -> skewness/kurtosis are nan, which
    # JSON cannot hold; the API coerces them to null.
    body = client.post(
        "/compute/descriptive", json={"data": [5.0, 5.0, 5.0, 5.0]}
    ).json()
    assert body["skewness"] is None
    assert body["kurtosis"] is None
    assert body["mean"] == 5.0
    assert not math.isnan(body["mean"])


class TestRules:
    """The 8-vs-9 discriminant, carried through the HTTP layer.

    Western Electric rule 4 fires on eight consecutive points on one side;
    Nelson rule 2 needs nine. A run of exactly eight must trip one and not the
    other -- the off-by-one that nothing downstream would reveal.
    """

    LIMITS: ClassVar[dict[str, float]] = {
        "center": 0.0,
        "lower": -3.0,
        "upper": 3.0,
    }

    def test_eight_points_fire_we_not_nelson(self, client: TestClient) -> None:
        points = [0.5] * 8
        we = client.post(
            "/compute/rules/western-electric",
            json={"points": points, "limits": self.LIMITS},
        ).json()
        nelson = client.post(
            "/compute/rules/nelson",
            json={"points": points, "limits": self.LIMITS},
        ).json()
        assert 4 in {v["rule"] for v in we}
        assert nelson == []

    def test_nine_points_fire_nelson_rule_2(self, client: TestClient) -> None:
        points = [0.5] * 9
        nelson = client.post(
            "/compute/rules/nelson",
            json={"points": points, "limits": self.LIMITS},
        ).json()
        assert 2 in {v["rule"] for v in nelson}


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"


def test_rules_catalogue(client: TestClient) -> None:
    body = client.get("/rules/catalogue").json()
    assert set(body) == {"nelson", "western_electric"}
    # Nelson has eight rules, Western Electric four.
    assert len(body["nelson"]) == 8
    assert len(body["western_electric"]) == 4
