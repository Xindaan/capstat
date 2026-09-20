# Deployment

capstat is two deployable pieces: a Next.js app and a stateless FastAPI service.
They talk over HTTP and share no state, so they can live on different hosts.

## Self-hosting with Docker

The simplest complete setup, and the way to try capstat without a Python
toolchain:

```bash
docker compose up --build
# web  -> http://localhost:3000
# API  -> http://localhost:8000/docs
```

Both images run as a non-root user. The API image is built from the repository
root, because `capstat-api` depends on `capstat-core` as a uv workspace member
and a narrower build context could not see it.

!!! warning "`NEXT_PUBLIC_API_URL` is baked in at build time"
    It ends up in the client bundle, so it is the URL the **browser** uses — not
    a container hostname. `http://api:8000` resolves inside the compose network
    and nowhere else. For a real deployment:

    ```bash
    docker build -f apps/web/Dockerfile \
      --build-arg NEXT_PUBLIC_API_URL=https://api.example.com -t capstat-web .
    ```

    And set `CAPSTAT_CORS_ORIGINS` on the API to wherever the web app is served
    from, or the browser will refuse the response.

## The web app on Vercel

The app is a standard Next.js project under `apps/web`. Point Vercel at the
repository and set the **root directory** to `apps/web`; `vercel.json` supplies
the rest.

One environment variable matters: `NEXT_PUBLIC_API_URL`, pointing at wherever
the API is hosted. Because it is inlined into the client bundle, changing it
requires a rebuild, not just a restart.

## Hosting

capstat is **not hosted publicly**, by choice. A capability tool takes real
production measurements as input, and the least surprising thing to do with
those is to keep them on the machine that runs the analysis. `docker compose up`
does exactly that: no account, no cloud, no data leaving your network. That is
the recommended way to run it.

If you *do* want to put it on the internet, here is what to know rather than a
recommendation to follow.

The web app is entirely static — all three routes prerender to HTML — so it can
go on any static host (GitHub Pages, Cloudflare Pages, Netlify; all free). The
`output: "standalone"` setup in the web Dockerfile is for self-hosting the whole
thing behind one server; a static host does not need it.

The API is the part that needs real compute. Its runtime dependencies measure:

| Package | Size |
|---|---|
| scipy | 71 MB |
| pandas | 40 MB |
| numpy | 22 MB |
| everything else | ~19 MB |
| **total** | **~152 MB** uncompressed |

Cold import of `scipy.stats` + `pandas` + `fastapi` is roughly **1 second** on a
warm local disk; a cold serverless invocation, realistically two to four times
that. So a serverless function is *possible* (152 MB fits Vercel's 250 MB limit)
but tight — the headroom shrinks as scipy and pandas grow — and a compute
endpoint that stalls for several seconds on first request is a poor experience.
A container host is the more comfortable fit for the same image; pricing on the
free/cheap tiers changes often enough that it is not worth quoting here — check
the provider directly.

Whichever host: it must serve the port given in `$PORT` — the image already
honours that — and `CAPSTAT_CORS_ORIGINS` must name the web app's origin.

## Cutting a release

Releases are automated by
[release-please](https://github.com/googleapis/release-please). Every push to
`main` updates an open **release pull request** summarising the conventional
commits since the last tag. Merging that PR is the release: it tags the commit,
publishes a GitHub release, writes `CHANGELOG.md`, and bumps the version
everywhere it appears —

- `packages/capstat-core/pyproject.toml` and its `__version__`
- `apps/api/pyproject.toml` and its `__version__`
- `apps/web/package.json`
- `apps/api/openapi.json` (`info.version`)

That last one matters: the API's version is part of its published schema, and
the schema is drift-checked against the code. If a release bumped the version
without updating `openapi.json`, the next CI run would fail. It is in the
config for that reason.

The repository carries **one version for everything**. The core, the API and the
web app are built and released together, so independent version numbers would
imply a freedom that does not exist.

!!! warning "`uv.lock` is not on that list — stamp it **on the release branch**"
    The lock records a version for each workspace member and release-please
    does not update it, so its release commit bumps the six files above and
    leaves the lock a version behind. `uv sync --frozen` takes the lock as it
    finds it rather than checking it against the manifests, so nothing on
    `main` reports that.

    The refresh has to happen **before the merge, on the release branch**, not
    after it. The tag is created at the release commit: a lock fixed afterwards
    never reaches the tag, and `publish` checks the lock against the tag before
    it builds — so the release would be refused at its own gate, permanently,
    with no way to correct it but another version. This is not hypothetical;
    0.4.0 was one merge away from exactly that.

    So, with the release pull request open:

    ```bash
    git fetch origin release-please--branches--main--components--capstat
    git checkout -B release-lock FETCH_HEAD
    uv lock
    uv run python scripts/check_lock_version.py v0.4.0   # the tag being cut
    git commit -am "chore(deps): stamp 0.4.0 into uv.lock with the rest of the release"
    git push origin release-lock:release-please--branches--main--components--capstat
    ```

    Then merge the release pull request. Squashing folds the stamp into the
    release commit, which is where it belongs.

    The check is not in CI on purpose: release-please's own commit would fail
    it, so `main` would be red from the merge until a follow-up landed. The
    release gate is where a stale lock has consequences, so that is where it
    is caught.

!!! note "The release PR does not run CI"
    Pull requests opened with the default `GITHUB_TOKEN` do not trigger other
    workflows. The commits the PR summarises were each tested on `main` before
    landing, so nothing is unverified — but if you want CI on the PR itself,
    give the action a PAT with `repo` scope.

## Publishing to PyPI

Tagging is not publishing. `capstat-core` reaches PyPI only when someone runs
the **`publish`** workflow by hand from the Actions tab and names the tag to
publish. It has no push, tag or release trigger, and it stops at the `pypi`
environment's required reviewer before the upload — two deliberate gates,
because a PyPI version number can never be reused, not even after a yank.

The upload itself uses trusted publishing (OIDC), so no API token exists to
leak or rotate.

### Verifying what was published

A green publish run proves PyPI accepted *something*. It does not prove which
code: the version string is checked against the tag before the build, and
nothing afterwards looks at the artefact the index actually serves. A release
that adds no public symbol cannot be told apart by importing it — 0.3.1 was
exactly that.

So the workflow ends by asking PyPI instead of the runner:

```bash
uv run python scripts/verify_pypi_release.py 0.3.1
```

The script installs that version from pypi.org into a fresh environment with
caches disabled, imports it, and compares every installed source file byte for
byte against the tag `v0.3.1`, which it reads with `git cat-file` rather than
checking out — your working tree is never touched. It reports the file count
and exits `0` when they are identical, `1` when they are not, and `2` when the
check could not be run at all (unknown tag, no network, failed install). That
last code is separate on purpose: "could not look" must not read as "looked and
it was fine".

It is not only a CI step. Run it against any published version at any time to
re-establish that what PyPI serves today is still what the tag holds.

## Configuration

| Variable | Where | Meaning |
|---|---|---|
| `CAPSTAT_CORS_ORIGINS` | API | Comma-separated browser origins allowed to call the API. Default: `http://localhost:3000,http://127.0.0.1:3000`. |
| `CAPSTAT_MAX_COMPUTE_BYTES` | API | Largest accepted `/compute/*` request body, in bytes. Default: `10485760` (10 MB). A body beyond it gets a 413. Unparseable or non-positive values fall back to the default, so a typo cannot disable the guard. |
| `PORT` | API | Port to bind. Default 8000; container hosts usually inject this. |
| `NEXT_PUBLIC_API_URL` | web (build time) | Where the browser reaches the API. Default `http://127.0.0.1:8000`. |

The API is stateless and needs nothing else — no database, no secrets, no
persistent volume. Uploaded files are parsed in memory and never written to
disk.
