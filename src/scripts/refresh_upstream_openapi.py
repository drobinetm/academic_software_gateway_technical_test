from __future__ import annotations

import json
import sys

import httpx

from src.core.config import get_settings


def main() -> int:
    settings = get_settings()
    print(f"Fetching {settings.upstream_openapi_url} ...")
    try:
        response = httpx.get(
            settings.upstream_openapi_url,
            timeout=settings.upstream_openapi_fetch_timeout,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"ERROR: failed to fetch upstream OpenAPI: {exc}", file=sys.stderr)
        return 1

    try:
        spec = response.json()
    except ValueError as exc:
        print(f"ERROR: response is not valid JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(spec, dict) or "openapi" not in spec:
        print(
            "ERROR: response is not an OpenAPI 3.x document (missing 'openapi' key).",
            file=sys.stderr,
        )
        return 1

    out_path = settings.openapi_cache_path
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(spec, handle, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path} ({len(response.content)} bytes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
