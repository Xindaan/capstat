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

## Where the API goes

This is the open decision, and it is worth making with numbers rather than
instinct. Measured footprint of the API's runtime dependencies:

| Package | Size |
|---|---|
| scipy | 71 MB |
| pandas | 40 MB |
| numpy | 22 MB |
| everything else | ~19 MB |
| **total** | **~152 MB** uncompressed |

Cold import of `scipy.stats` + `pandas` + `fastapi` costs roughly **1 second**
on a warm local disk; on a cold serverless invocation, realistically two to four
times that.

**A container host is the safer pairing.** 152 MB fits under Vercel's 250 MB
serverless limit, so Python functions are not impossible — but the headroom is
thin and it only shrinks, since scipy and pandas grow with every release. A
compute API that pauses for several seconds on first request also makes a poor
demo. Render's free tier (sleeps when idle) or Fly.io (a few EUR/month, no
sleep) both take the image above unchanged.

Whichever host: it must serve the port given in `$PORT` — the image already
honours that — and `CAPSTAT_CORS_ORIGINS` must name the web app's origin.

## Configuration

| Variable | Where | Meaning |
|---|---|---|
| `CAPSTAT_CORS_ORIGINS` | API | Comma-separated browser origins allowed to call the API. Default: `http://localhost:3000,http://127.0.0.1:3000`. |
| `PORT` | API | Port to bind. Default 8000; container hosts usually inject this. |
| `NEXT_PUBLIC_API_URL` | web (build time) | Where the browser reaches the API. Default `http://127.0.0.1:8000`. |

The API is stateless and needs nothing else — no database, no secrets, no
persistent volume. Uploaded files are parsed in memory and never written to
disk.
