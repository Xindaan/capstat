"""Container health check: is the service answering on /health?

Used by the Dockerfile's HEALTHCHECK and by docker-compose. Kept as a file
rather than an inline ``python -c`` so the quoting cannot rot unnoticed -- a
broken health check reports "unhealthy" for the wrong reason, which is worse
than having none.
"""

from __future__ import annotations

import os
import sys
import urllib.request

PORT = os.environ.get("PORT", "8000")
URL = f"http://127.0.0.1:{PORT}/health"


def main() -> int:
    try:
        with urllib.request.urlopen(URL, timeout=2) as response:
            return 0 if response.status == 200 else 1
    except OSError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
