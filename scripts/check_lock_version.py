"""Check that uv.lock stamps the same version as the packages it locks.

`uv.lock` records a version for every workspace member, and nothing in this
repository keeps it honest. release-please bumps the six extra files its config
lists and the lock is not one of them; CI runs ``uv sync --frozen``, which takes
the lock as it finds it rather than checking it against the manifests. So the
lock drifts silently at every release, and stays drifted until someone happens
to run ``uv lock``: on 2026-09-19 it still said ``0.3.0`` while the packages,
the tag and PyPI had all moved to ``0.3.1`` (T-0087).

`AGENTS.md` requires the tag to stamp the version in every file that carries it,
`uv.lock` named among them. This is that check for the one file nothing else
covers. `publish.yml` runs it before the build, so a stale lock stops a release
rather than riding along in it.

Run it by hand after merging a release pull request -- that is the moment the
lock goes stale::

    uv run python scripts/check_lock_version.py           # against the packages
    uv run python scripts/check_lock_version.py v0.4.0    # against a tag too

Exit codes: ``0`` the versions agree, ``1`` they do not (run ``uv lock``), ``2``
the check could not be run.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "uv.lock"
# The repository carries one version for everything, so any workspace member
# answers the question "what version is this tree?". capstat-core is the one
# that gets published, which makes it the natural anchor.
ANCHOR = ROOT / "packages" / "capstat-core" / "pyproject.toml"

EXIT_MISMATCH = 1
EXIT_UNAVAILABLE = 2


class CheckUnavailable(Exception):
    """The check could not be carried out; this is not a verdict."""


def _load(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise CheckUnavailable(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc


def anchor_version() -> str:
    project = _load(ANCHOR).get("project")
    if isinstance(project, dict):
        version = project.get("version")
        if isinstance(version, str):
            return version
    raise CheckUnavailable(f"no project.version in {ANCHOR.relative_to(ROOT)}")


def locked_versions() -> dict[str, str]:
    """The version the lock records for each workspace member.

    A workspace member is a package the lock points back at this tree for
    (``source = { editable = ... }``); everything else comes from an index and
    has nothing to do with our version.
    """
    packages = _load(LOCK).get("package")
    if not isinstance(packages, list):
        raise CheckUnavailable("uv.lock has no package list")
    found = {
        str(entry["name"]): str(entry["version"])
        for entry in packages
        if isinstance(entry, dict)
        and "editable" in (entry.get("source") or {})
        and "name" in entry
        and "version" in entry
    }
    if not found:
        raise CheckUnavailable("uv.lock records no workspace members")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check uv.lock against the version its packages declare.",
    )
    parser.add_argument(
        "tag",
        nargs="?",
        help="also require this tag's version, e.g. v0.4.0 (or 0.4.0)",
    )
    args = parser.parse_args(argv)

    try:
        expected = anchor_version()
        locked = locked_versions()
    except CheckUnavailable as exc:
        print(f"COULD NOT CHECK: {exc}", file=sys.stderr)
        return EXIT_UNAVAILABLE

    failures: list[str] = []
    if args.tag:
        # The tag comes from outside the tree, so it is the only anchor that can
        # disagree with everything in it -- which is exactly when it matters.
        wanted = str(args.tag).removeprefix("v")
        if wanted != expected:
            failures.append(
                f"tag {args.tag} expects {wanted}, "
                f"{ANCHOR.relative_to(ROOT)} says {expected}"
            )
        expected = wanted

    stale = {name: version for name, version in locked.items() if version != expected}
    for name, version in sorted(stale.items()):
        failures.append(f"uv.lock has {name} {version}, expected {expected}")

    if failures:
        # The headline stays neutral: with a tag argument the disagreement can
        # be the tag against the packages, which `uv lock` would not fix.
        print(f"Versions do not all agree on {expected}:")
        for failure in failures:
            print(f"  {failure}")
        if stale:
            print("\nRun `uv lock` and commit the result.")
        return EXIT_MISMATCH

    members = ", ".join(sorted(locked))
    print(f"uv.lock: {members} all at {expected}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
