"""Generate the docs' validation-sources page from the reference YAML files.

Every number capstat validates against is recorded in
``packages/capstat-core/tests/references/*.yaml``, together with where it came
from. Those files are the single source of truth; this script renders them into
a documentation page rather than asking anyone to keep a second copy in prose.

That is the same rule the library applies to statistical constants: do not
transcribe what you can derive. A hand-written source list would drift the first
time a reference was added and the page forgotten.

Usage::

    python scripts/gen_sources_page.py            # write the page
    python scripts/gen_sources_page.py --check    # fail if it is stale (CI)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
REFERENCES = ROOT / "packages" / "capstat-core" / "tests" / "references"
TARGET = ROOT / "docs" / "validation-sources.md"

HEADER = """<!--
  GENERATED FILE -- do not edit.
  Rendered from packages/capstat-core/tests/references/*.yaml by
  scripts/gen_sources_page.py. Edit the YAML, then re-run that script.
-->

# Sources

Every reference value capstat is tested against, and where it came from. This
page is generated from the reference files themselves, so it cannot drift from
what the test suite actually asserts.

A source is listed here because a *number* was taken from it -- a certified
value, a published table, a worked example -- not merely because it was read.
"""

# The reference file each module is validated by, in the order a reader meets
# them. Anything not named here is appended alphabetically, so a new reference
# file shows up in the docs even if nobody updates this list.
ORDER = [
    ("nist_strd_univariate.yaml", "Descriptive statistics"),
    ("normality.yaml", "Normality testing"),
    ("capability.yaml", "Capability indices and chart constants"),
    ("nonnormal.yaml", "Non-normal capability"),
    ("control_charts.yaml", "Shewhart control charts"),
    ("time_weighted.yaml", "EWMA and CUSUM"),
    ("rules.yaml", "Run rules"),
    ("gage_rr.yaml", "Gage R&R"),
    ("bias.yaml", "Bias"),
    ("linearity.yaml", "Linearity"),
]


def _clean(text: object) -> str:
    """YAML block scalars arrive with newlines; flatten them for a table cell."""
    return " ".join(str(text).split())


def _render_source(key: str, source: dict[str, Any]) -> str:
    """One bullet per source: the citation, then its details indented under it."""
    title = _clean(source.get("title", key))
    details: list[str] = []
    if url := source.get("url"):
        details.append(f"<{url}>")
    if retrieved := source.get("retrieved"):
        details.append(f"Retrieved {retrieved}.")
    if quote := source.get("quote"):
        details.append(f'Stated check value: "{_clean(quote)}"')
    if note := source.get("note"):
        details.append(_clean(note))

    bullet = f"- **{title}**"
    if details:
        bullet += "\n  " + " ".join(details)
    return bullet


def render() -> str:
    files = {path.name: path for path in sorted(REFERENCES.glob("*.yaml"))}
    ordered = [(name, label) for name, label in ORDER if name in files]
    ordered += [
        (name, name.removesuffix(".yaml").replace("_", " ").title())
        for name in sorted(files)
        if name not in {n for n, _ in ORDER}
    ]

    out = [HEADER]
    for name, label in ordered:
        document = yaml.safe_load(files[name].read_text(encoding="utf-8")) or {}
        sources = document.get("sources") or {}
        out.append(f"## {label}")
        out.append("")
        out.append(f"Reference file: `tests/references/{name}`")
        out.append("")
        if not sources:
            # Datasets whose provenance is the data files themselves.
            out.append(
                "Certified values ship with the datasets in "
                "`tests/references/data/`; each file states its own source in "
                "its header."
            )
            out.append("")
            continue
        for key, source in sources.items():
            out.append(_render_source(key, source))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the committed page differs from a fresh render",
    )
    args = parser.parse_args(argv)

    rendered = render()
    if args.check:
        if not TARGET.exists():
            print(f"{TARGET} is missing; run scripts/gen_sources_page.py")
            return 1
        if TARGET.read_text(encoding="utf-8") != rendered:
            print(
                f"{TARGET} is stale; run scripts/gen_sources_page.py to regenerate it."
            )
            return 1
        print(f"{TARGET.name} is up to date.")
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(rendered, encoding="utf-8")
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
