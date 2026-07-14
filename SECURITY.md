# Security Policy

## Supported versions

capstat is in early development (pre-1.0). Security fixes are applied to the
latest `main` and the most recent release only.

## Reporting a vulnerability

Please report security issues **privately**. Do not open a public issue for a
vulnerability.

- Preferred: use GitHub's
  [private vulnerability reporting](https://github.com/Xindaan/capstat/security/advisories/new)
  ("Report a vulnerability" on the Security tab).
- Alternatively, email the maintainer at **leo@greatbelow.de** with the
  details and, if possible, a minimal reproduction.

You can expect an initial response within **7 days**. Once a fix is available,
we will coordinate a disclosure timeline with you.

## Scope

capstat-core is a stateless computation library with no network or persistence
layer. The most relevant concerns are in the ingestion paths of the API server
(CSV/XLSX parsing) and dependency vulnerabilities, both of which are in scope.
