# Security Policy

## Project status

CUCU is an actively maintained academic/portfolio fork (see [README](README.md)). It has no live production user base today, but the codebase is treated as if it did: security issues are taken seriously and fixed promptly.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for a security vulnerability. Instead, use GitHub's private reporting:

1. Go to the [Security tab](https://github.com/TomasPosada0626/cucu/security) of this repository.
2. Click **"Report a vulnerability"**.

This opens a private advisory visible only to the maintainer, so the issue isn't disclosed before a fix is available.

For anything that isn't a security vulnerability (bugs, feature requests, questions), use the regular [Issues](https://github.com/TomasPosada0626/cucu/issues) instead.

## Supported versions

There is a single actively developed branch (`main`). Fixes land there; there is no separate long-term-support version.

## What's already been hardened

Recent security work (see the wiki's [Mejoras y Roadmap](../../wiki/Mejoras-y-Roadmap) for full detail) includes: no hardcoded secrets, SSRF protection (including DNS-rebinding), rate limiting on auth endpoints and the Django admin, CSP headers, upload validation against malicious files, and `IsAuthenticated` as the default API permission.
