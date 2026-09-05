# Getting started

## Install

capstat uses [uv](https://docs.astral.sh/uv/). It manages its own Python, so you
do not need a system 3.11+.

```bash
git clone https://github.com/Xindaan/capstat
cd capstat
uv sync            # environment + every workspace member
uv run pytest      # confirm the reference suite passes
```

!!! tip "Just the statistics library?"
    The clone above gets you the API and the web app as well. If you only want
    the statistics, [`capstat-core`](https://pypi.org/project/capstat-core/) is
    on PyPI and depends on nothing but numpy and scipy:

    ```bash
    pip install capstat-core
    ```

    To follow unreleased changes instead, install it from a checkout:

    ```bash
    pip install ./packages/capstat-core
    ```

## A first capability study

```python
from capstat_core import capability

readings = [10.1, 9.9, 10.0, 10.2, 9.8, 10.05, 9.95, 10.15]
report = capability(readings, lsl=9.5, usl=10.5)

print(report.cpk, report.ppk)
for warning in report.warnings:
    print(warning)
```

Read `cpk` and `ppk` together. `cpk` is the number a supplier would like to
quote; `ppk` is the one the customer lives with. When they diverge, the gap
*is* the instability, and the report says so.

!!! warning "Let the decision path choose the model"
    `capability()` assumes normality. It will warn you when that assumption was
    rejected, but it still returns indices. If you do not already know your data
    is normal, call `analyze_capability()` instead: it tests normality first and
    routes to Box-Cox or the ISO 22514 percentile method, telling you which it
    used and why.

    ```python
    from capstat_core import analyze_capability

    analysis = analyze_capability(readings, lsl=9.5, usl=10.5)
    print(analysis.path)       # "normal" | "box-cox" | "percentile"
    print(analysis.rationale)  # why that path, in a sentence
    ```

## Run the API

```bash
uv run uvicorn capstat_api.main:app --reload   # http://127.0.0.1:8000/docs
```

```bash
curl -s http://127.0.0.1:8000/compute/capability \
  -H 'content-type: application/json' \
  -d '{"data": [10.1, 9.9, 10.0, 10.2, 9.8, 10.05], "lsl": 9.5, "usl": 10.5}'
```

Every response mirrors a core dataclass exactly — the `warnings` arrays and the
nullable indices survive serialisation instead of being flattened away. Each
warning arrives as `{"code", "message"}`, so a client can react to
`capability.unstable-process` without matching English prose.

!!! note "Developing against the core"
    `--reload` watches `apps/api` only. If you are editing `capstat-core` while
    the server runs, add `--reload-dir ../../packages/capstat-core/src`, or the
    server will keep serving the old library.

## Run the web app

With the API running:

```bash
cd apps/web
npm install
npm run dev        # http://localhost:3000
```

`examples/shaft-diameter.csv` is a synthetic dataset built to make the app say
something: 60 readings in time order from a drifting process, with an excursion,
a text column that gets ignored and two missing cells. Drop it on the upload
page.

Any analysis page is also its own report — **Print / save as PDF** drops the
navigation and controls, keeps the results, and prints the charts as vector.
