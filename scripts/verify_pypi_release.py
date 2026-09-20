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

Exit codes: ``0`` verified, ``1`` a difference was found (this is the finding
the script exists for), ``2`` the check could not be run at all -- an unknown
tag, no network, a failed install. A 2 is not a pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
# The simple index is what a resolver actually reads, and it trails the JSON API
# by seconds after an upload. Waiting on the JSON API alone is what made the
# publish run fail on a healthy 0.4.1 (T-0093).
SIMPLE_INDEX = "https://pypi.org/simple/{distribution}/"

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


def pypi_artifacts(version: str, *, retries: int, delay: float) -> list[str]:
    """The artefact types PyPI serves for this version, e.g. ``sdist``, ``bdist_wheel``.

    Retried, because a freshly accepted upload takes a moment to become visible
    -- which is exactly when this script runs inside the publish workflow.
    """
    url = PYPI_JSON.format(distribution=DISTRIBUTION, version=version)
    last = ""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = json.load(response)
            urls = payload.get("urls") or []
            return sorted({str(entry.get("packagetype")) for entry in urls})
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
            last = str(exc)
            if attempt + 1 < retries:
                print(f"  PyPI not ready yet ({last}); retrying in {delay:.0f}s")
                time.sleep(delay)
    raise CheckUnavailable(f"PyPI did not answer for {DISTRIBUTION} {version}: {last}")


def index_lists_version(payload: str, version: str) -> bool:
    """Does this simple-index page offer a file for exactly ``version``?

    Anchored on what may follow the version in a filename -- ``-`` for a wheel
    (``capstat_core-0.4.1-py3-none-any.whl``) and exactly ``.tar.gz`` for an
    sdist. Both anchors are needed: without them ``0.4.1`` matches ``0.4.10``,
    and allowing a bare ``.`` makes ``0.3`` match ``0.3.1.tar.gz``. Measured --
    the looser ``[-.]`` form passed four cases and failed that last one.
    """
    pattern = re.compile(
        rf"{re.escape(IMPORT_PACKAGE)}-{re.escape(version)}(?:-|\.tar\.gz)",
        re.IGNORECASE,
    )
    return bool(pattern.search(payload))


def await_index(version: str, *, retries: int, delay: float) -> None:
    """Block until the simple index offers ``version``, or give up.

    PyPI accepts an upload before it serves it, and `publish` runs this script
    about a second after the upload finishes -- on 0.4.1 the wheel landed at
    18:51:17 and the install failed at 18:51:19 with "there is no version of
    capstat-core==0.4.1". The JSON API already answered for that version by
    then; the simple index did not. So the wait belongs here, against the page
    the resolver reads.

    Giving up still raises: a version that is genuinely absent must fail the
    run, only later than it used to.
    """
    url = SIMPLE_INDEX.format(distribution=DISTRIBUTION)
    last = "not listed yet"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = response.read().decode("utf-8", "replace")
            if index_lists_version(payload, version):
                return
        except (urllib.error.URLError, TimeoutError) as exc:
            last = str(exc)
        if attempt + 1 < retries:
            print(
                f"  simple index has no {version} yet ({last}); "
                f"retrying in {delay:.0f}s"
            )
            time.sleep(delay)
    raise CheckUnavailable(
        f"the simple index still does not offer {DISTRIBUTION} {version}: {last}"
    )


def install_into(env_dir: Path, version: str) -> Path:
    """Create an environment, install the version from PyPI, return its python.

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


def verify(version: str, tag: str, *, retries: int, delay: float, keep: bool) -> int:
    commit = resolve_tag(tag)
    print(f"{DISTRIBUTION} {version} on PyPI vs tag {tag} ({commit[:12]})\n")

    expected = tag_sources(tag)

    artifacts = pypi_artifacts(version, retries=retries, delay=delay)
    lines = [f"pypi release        {version}: {', '.join(artifacts) or 'nothing'}"]
    failures: list[str] = []
    for wanted in ("sdist", "bdist_wheel"):
        if wanted not in artifacts:
            failures.append(f"PyPI serves no {wanted} for {version}")

    # Before installing, not after: the install is what raced the index.
    await_index(version, retries=retries, delay=delay)

    env_root = Path(tempfile.mkdtemp(prefix=f"verify-{DISTRIBUTION}-"))
    try:
        python = install_into(env_root / "venv", version)
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
        "--retries",
        type=int,
        default=5,
        help="attempts at PyPI (JSON API and simple index) before giving up "
        "(default: 5)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=15.0,
        help="seconds between those attempts (default: 15)",
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
            retries=max(1, int(args.retries)),
            delay=max(0.0, float(args.delay)),
            keep=bool(args.keep),
        )
    except CheckUnavailable as exc:
        print(f"\nCOULD NOT VERIFY: {exc}", file=sys.stderr)
        return EXIT_UNAVAILABLE


if __name__ == "__main__":
    sys.exit(main())
