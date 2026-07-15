"""capstat-api: a stateless FastAPI service over capstat-core.

The service is a thin, faithful wrapper: every response model mirrors a
capstat-core dataclass exactly, including its ``warnings`` tuples and its
nullable capability indices. Nothing statistical happens here -- the core
does the maths, this package only serialises it and ingests files.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.0.0"
