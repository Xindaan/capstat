"""Verify that what PyPI serves for a version is what the tag holds.

A green ``publish`` run proves the upload was accepted. It does not prove
*which code* was accepted: the version string is checked against the tag before
the build, but nothing afterwards looks at the artefact PyPI actually serves. A
release with no new public symbol cannot be told apart by importing it, so the
only evidence that survives is a byte-for-byte comparison of the installed files
against the tag.

That comparison was done by hand for 0.3.1. This script is that check, written
down: it is the same four questions, in the same order, with an exit code.

1. Does PyPI list the version, with both an sdist and a wheel?
2. Does a fresh environment install it from PyPI and import it?
3. Does the installed tree hold exactly the files the tag holds -- none
   missing, none extra?
4. Is every one of those files byte-identical to the tag's?

The tag is read with ``git ls-tree``/``git cat-file`` rather than checked out:
nothing in the working tree is touched, so the check is safe to run mid-work and
needs no clean tree in CI.

Usage::

    uv run --no-project python scripts/verify_pypi_release.py 0.3.1
    uv run --no-project python scripts/verify_pypi_release.py v0.3.1 --keep

Straight after an upload, give it a budget: PyPI's CDN caches each view of a
project for up to 600s, so a version can be unresolvable for minutes while the
JSON API already reports it. `publish` passes ``--wait 900 --delay 30``::

    uv run --no-project python scripts/verify_pypi_release.py 0.4.2 --wait 900

Exit codes: ``0`` verified, ``1`` a difference was found (this is the finding
the script exists for), ``2`` the check could not be run at all -- an unknown
tag, no network, a failed install. A 2 is not a pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The distribution as PyPI names it, the import package, and where the tag keeps
# the sources the wheel is built from. The wheel maps that directory onto the
# import package one-to-one (hatchling, ``packages = ["src/capstat_core"]``),
# which is what makes a path-by-path comparison meaningful.
DISTRIBUTION = "capstat-core"
IMPORT_PACKAGE = "capstat_core"
SOURCE_PREFIX = "packages/capstat-core/src/capstat_core"

# Pinned rather than left to whatever index the environment defaults to: the
# question is what *PyPI* serves, so an inherited index URL would answer a
# different one.
INDEX_URL = "https://pypi.org/simple"
PYPI_JSON = "https://pypi.org/pypi/{distribution}/{version}/json"
# PyPI serves every view of a release through a CDN with `max-age=600` and
# `Vary: Accept` -- so the HTML simple index, the PEP 691 JSON index and the
# JSON API are three independently cached answers, and after an upload they
# disagree for up to ten minutes. No view is a trustworthy proxy for "can this
# be installed": on 0.4.2 the HTML index already listed the version while the
# JSON index uv reads did not (T-0093).

# Verification failed: files differ, or the wrong version answered.
EXIT_MISMATCH = 1
# Verification could not run. Deliberately distinct from a mismatch, because
# "we could not look" must never read as "we looked and it was fine".
EXIT_UNAVAILABLE = 2


class CheckUnavailable(Exception):
    """The check could not be carried out; this is not a verdict."""


@dataclass(frozen=True)
class Report:
    """What each step found, so the summary can be printed in one place."""

    lines: list[str]
    failures: list[str]


def _run(
    command: list[str], *, cwd: Path | None = None, what: str
) -> subprocess.CompletedProcess[bytes]:
    """Run a command, turning a non-zero exit into ``CheckUnavailable``."""
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, check=False)
    except OSError as exc:  # pragma: no cover - missing executable
        raise CheckUnavailable(f"{what}: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise CheckUnavailable(f"{what} failed:\n{detail}")
    return result


def _git(*args: str) -> bytes:
    return _run(["git", *args], cwd=ROOT, what=f"git {args[0]}").stdout


def resolve_tag(tag: str) -> str:
    """Return the commit the tag points at, fetching the tag if it is absent.

    ``actions/checkout`` fetches a single ref, so in CI the tag object may well
    not be in the clone even though the workflow checked that ref out.
    """
    try:
        return _git("rev-parse", "--verify", f"{tag}^{{commit}}").decode().strip()
    except CheckUnavailable:
        pass
    _run(
        ["git", "fetch", "--no-tags", "origin", f"refs/tags/{tag}:refs/tags/{tag}"],
        cwd=ROOT,
        what=f"fetching tag {tag}",
    )
    return _git("rev-parse", "--verify", f"{tag}^{{commit}}").decode().strip()


def tag_sources(tag: str) -> dict[str, bytes]:
    """The package's source files at ``tag``, keyed by path inside the package."""
    listing = _git("ls-tree", "-r", "--name-only", "-z", tag, "--", SOURCE_PREFIX)
    paths = [entry for entry in listing.decode().split("\0") if entry]
    if not paths:
        raise CheckUnavailable(f"tag {tag} holds no files under {SOURCE_PREFIX}")
    return {
        path[len(SOURCE_PREFIX) + 1 :]: _git("cat-file", "blob", f"{tag}:{path}")
        for path in sorted(paths)
    }


def _time_left(deadline: float) -> float:
    """Seconds until the shared propagation budget runs out."""
    return deadline - time.monotonic()


def pypi_artifacts(version: str, *, deadline: float, delay: float) -> list[str]:
    """The artefact types PyPI serves for this version, e.g. ``sdist``, ``bdist_wheel``.

    Retried until the shared deadline: a freshly accepted upload takes a while
    to become visible, which is exactly when this script runs inside publish.
    """
    url = PYPI_JSON.format(distribution=DISTRIBUTION, version=version)
    last = ""
    while True:
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = json.load(response)
            urls = payload.get("urls") or []
            return sorted({str(entry.get("packagetype")) for entry in urls})
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
            last = str(exc)
        if _time_left(deadline) <= delay:
            break
        print(f"  PyPI API not ready yet ({last}); retrying in {delay:.0f}s")
        time.sleep(delay)
    raise CheckUnavailable(f"PyPI did not answer for {DISTRIBUTION} {version}: {last}")


def _install_once(env_dir: Path, version: str) -> Path:
    """One attempt: create an environment, install from PyPI, return its python.

    Caches are disabled on both paths. A cached wheel could satisfy the install
    without PyPI being consulted, which would leave the script verifying a local
    artefact against the tag -- a check that passes while saying nothing.
    """
    uv = shutil.which("uv")
    requirement = f"{DISTRIBUTION}=={version}"
    if uv:
        _run([uv, "venv", "--quiet", str(env_dir)], what="creating the environment")
        python = _venv_python(env_dir)
        _run(
            [
                uv,
                "pip",
                "install",
                "--quiet",
                "--python",
                str(python),
                "--no-cache",
                "--index-url",
                INDEX_URL,
                requirement,
            ],
            what=f"installing {requirement}",
        )
        return python
    _run([sys.executable, "-m", "venv", str(env_dir)], what="creating the environment")
    python = _venv_python(env_dir)
    _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--quiet",
            "--disable-pip-version-check",
            "--no-cache-dir",
            "--index-url",
            INDEX_URL,
            requirement,
        ],
        what=f"installing {requirement}",
    )
    return python


def install_into(env_dir: Path, version: str, *, deadline: float, delay: float) -> Path:
    """Install ``version`` from PyPI, retrying until the shared deadline.

    The retry is on the install itself, not on any index page, because no index
    page answers the question. PyPI serves the HTML simple index, the PEP 691
    JSON index and the JSON API as separately cached documents (``Vary:
    Accept``, ``max-age=600``), and after an upload they disagree for minutes.
    Checking one of them and then installing means asking a different question
    than the one that matters: 0.4.2 failed exactly that way, with the HTML
    index already listing the version the resolver could not find (T-0093).

    Retrying regardless of the reason is deliberate. A broken artefact and an
    unpropagated one fail identically here, and telling them apart would mean
    matching on resolver prose that changes between uv releases. Both still end
    the run as a failure; a genuinely broken release only takes longer to say so.
    """
    attempt = 0
    while True:
        attempt += 1
        shutil.rmtree(env_dir, ignore_errors=True)
        try:
            return _install_once(env_dir, version)
        except CheckUnavailable as exc:
            last = exc
        if _time_left(deadline) <= delay:
            raise last
        print(
            f"  install attempt {attempt} failed; PyPI may still be "
            f"propagating -- retrying in {delay:.0f}s "
            f"({_time_left(deadline):.0f}s of budget left)"
        )
        time.sleep(delay)


def _venv_python(env_dir: Path) -> Path:
    candidates = [env_dir / "bin" / "python", env_dir / "Scripts" / "python.exe"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise CheckUnavailable(f"no interpreter in the environment at {env_dir}")


def installed_state(python: Path) -> tuple[Path, str, str]:
    """Import the package in the fresh environment; return its directory and versions.

    Both versions are asked for: ``__version__`` is what the code says about
    itself, the metadata version is what the index recorded. They have disagreed
    before in other projects, and either one alone can be right for the wrong
    reason.
    """
    probe = (
        "import importlib.metadata as m, pathlib, "
        f"{IMPORT_PACKAGE} as pkg;"
        f"print(pathlib.Path(pkg.__file__).parent);"
        "print(pkg.__version__);"
        f"print(m.version({DISTRIBUTION!r}))"
    )
    output = _run(
        [str(python), "-c", probe], what=f"importing {IMPORT_PACKAGE}"
    ).stdout.decode()
    directory, dunder, metadata = output.strip().splitlines()
    return Path(directory), dunder, metadata


def installed_sources(package_dir: Path) -> dict[str, bytes]:
    """Every shipped file under the installed package, keyed by relative path.

    ``__pycache__`` is excluded: it is produced by the import above, so it is an
    artefact of this script rather than of the release.
    """
    files: dict[str, bytes] = {}
    for path in sorted(package_dir.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        files[path.relative_to(package_dir).as_posix()] = path.read_bytes()
    return files


def compare(expected: dict[str, bytes], actual: dict[str, bytes]) -> Report:
    """Compare the two trees by inventory first, then byte by byte."""
    lines: list[str] = []
    failures: list[str] = []

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    shared = sorted(set(expected) & set(actual))

    if missing:
        failures.append(f"{len(missing)} file(s) in the tag but not installed")
        failures.extend(f"    missing: {name}" for name in missing)
    if extra:
        failures.append(f"{len(extra)} installed file(s) not in the tag")
        failures.extend(f"    unexpected: {name}" for name in extra)
    if not missing and not extra:
        lines.append(
            f"file inventory      {len(expected)} files, none missing, none extra"
        )

    differing = [name for name in shared if expected[name] != actual[name]]
    for name in differing:
        want = hashlib.sha256(expected[name]).hexdigest()[:12]
        got = hashlib.sha256(actual[name]).hexdigest()[:12]
        failures.append(f"    differs: {name} (tag {want}, installed {got})")
    if differing:
        failures.insert(
            len(failures) - len(differing),
            f"{len(differing)} of {len(shared)} shared file(s) differ",
        )
    else:
        lines.append(f"byte comparison     {len(shared)}/{len(shared)} files identical")
    return Report(lines=lines, failures=failures)


def verify(version: str, tag: str, *, budget: float, delay: float, keep: bool) -> int:
    commit = resolve_tag(tag)
    print(f"{DISTRIBUTION} {version} on PyPI vs tag {tag} ({commit[:12]})\n")

    expected = tag_sources(tag)

    # One budget for both PyPI-facing steps, so a slow index cannot spend the
    # whole allowance before the install -- which is the step that matters.
    deadline = time.monotonic() + budget

    artifacts = pypi_artifacts(version, deadline=deadline, delay=delay)
    lines = [f"pypi release        {version}: {', '.join(artifacts) or 'nothing'}"]
    failures: list[str] = []
    for wanted in ("sdist", "bdist_wheel"):
        if wanted not in artifacts:
            failures.append(f"PyPI serves no {wanted} for {version}")

    env_root = Path(tempfile.mkdtemp(prefix=f"verify-{DISTRIBUTION}-"))
    try:
        python = install_into(
            env_root / "venv", version, deadline=deadline, delay=delay
        )
        package_dir, dunder, metadata = installed_state(python)
        lines.append(
            f"clean install       imported {IMPORT_PACKAGE} "
            f"{dunder} (metadata {metadata})"
        )
        if dunder != version:
            failures.append(f"__version__ is {dunder}, expected {version}")
        if metadata != version:
            failures.append(f"installed metadata is {metadata}, expected {version}")

        report = compare(expected, installed_sources(package_dir))
        lines.extend(report.lines)
        failures.extend(report.failures)
    finally:
        if keep:
            print(f"\n(kept the environment at {env_root})")
        else:
            shutil.rmtree(env_root, ignore_errors=True)

    for line in lines:
        print(f"  {line}")
    if failures:
        print("\nFAILED")
        for failure in failures:
            print(f"  {failure}")
        return EXIT_MISMATCH
    print(
        f"\nOK: all {len(expected)} installed source files are byte-identical to {tag}."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a published version against its git tag.",
    )
    parser.add_argument("version", help="released version, e.g. 0.3.1 (or v0.3.1)")
    parser.add_argument(
        "--tag",
        help="tag to compare against; defaults to v<version>",
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="how long to keep retrying while PyPI propagates the upload, "
        "shared by every PyPI-facing step (default: 60). Raise it right "
        "after an upload: PyPI's CDN caches each view for up to 600s",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=15.0,
        help="seconds between attempts (default: 15)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep the temporary environment for inspection",
    )
    args = parser.parse_args(argv)

    version = str(args.version).removeprefix("v")
    tag = str(args.tag) if args.tag else f"v{version}"

    try:
        return verify(
            version,
            tag,
            budget=max(0.0, float(args.wait)),
            delay=max(1.0, float(args.delay)),
            keep=bool(args.keep),
        )
    except CheckUnavailable as exc:
        print(f"\nCOULD NOT VERIFY: {exc}", file=sys.stderr)
        return EXIT_UNAVAILABLE


if __name__ == "__main__":
    sys.exit(main())
