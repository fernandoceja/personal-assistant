#!/usr/bin/env python3
"""Reference-only Gmail read-only OAuth setup patch.

This file is preserved as a docs patch artifact. It is not installed, does not run
OAuth during validation, and exists to show that Gmail safe-list support should
request only the Gmail read-only scope.
"""

from __future__ import annotations

import argparse

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
SERVICE_SCOPES = {
    "gmail": [GMAIL_READONLY_SCOPE],
}
DEFAULT_SERVICES = ["gmail"]


def scopes_for_services(services_value: str | None) -> list[str]:
    """Return de-duplicated scopes for a comma-separated service list or all."""
    requested = [s.strip().lower() for s in (services_value or "all").split(",") if s.strip()]
    if not requested or "all" in requested:
        requested = list(DEFAULT_SERVICES)

    unknown = [service for service in requested if service not in SERVICE_SCOPES]
    if unknown:
        valid = ",".join(["all", *SERVICE_SCOPES.keys()])
        raise ValueError(f"Unknown service(s): {', '.join(unknown)}. Valid values: {valid}")

    scopes: list[str] = []
    for service in requested:
        for scope in SERVICE_SCOPES[service]:
            if scope not in scopes:
                scopes.append(scope)
    return scopes


def main() -> int:
    parser = argparse.ArgumentParser(description="Reference Gmail read-only scope selector")
    parser.add_argument("--services", default="gmail", help="Valid values: gmail or all; all maps to gmail only")
    parser.add_argument("--print-scopes", action="store_true", help="Print requested scopes for review")
    args = parser.parse_args()

    scopes = scopes_for_services(args.services)
    if args.print_scopes:
        for scope in scopes:
            print(scope)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
