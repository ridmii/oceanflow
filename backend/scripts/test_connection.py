#!/usr/bin/env python3
"""
test_connection.py
==================
Verify that the Copernicus Marine Service is reachable and that your
credentials / cached token are valid.

This script does NOT download any data and does NOT require a dataset ID.
It calls only the lightweight catalogue metadata API.

Usage
-----
    python scripts/test_connection.py

Prerequisites
-------------
1. Run `copernicusmarine login` once, OR fill in COPERNICUS_USERNAME /
   COPERNICUS_PASSWORD in backend/.env.
2. An active internet connection.
"""

from __future__ import annotations

import os
import sys
import textwrap
import time

# Load .env from the backend/ directory (parent of scripts/)
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(dotenv_path=_env_path)
except ImportError:
    print(
        "[WARN] python-dotenv not installed. Reading credentials from shell "
        "environment only.\n       Install it with: pip install python-dotenv"
    )


def _check_env_credentials() -> tuple[str | None, str | None]:
    """Return (username, password) from environment, either may be None."""
    return os.getenv("COPERNICUS_USERNAME"), os.getenv("COPERNICUS_PASSWORD")


def main() -> None:
    print("=" * 60)
    print("  Copernicus Marine — Connection Test")
    print("=" * 60)

    # ── 1. Import copernicusmarine ───────────────────────────────
    try:
        import copernicusmarine  # noqa: F401
    except ImportError:
        print(
            "\n[ERROR] copernicusmarine is not installed.\n"
            "        Run: pip install copernicusmarine\n"
        )
        sys.exit(1)

    # ── 2. Check credentials ─────────────────────────────────────
    username, password = _check_env_credentials()
    using_env_creds = bool(username and password)

    if not using_env_creds:
        print(
            "\n[INFO] No COPERNICUS_USERNAME / COPERNICUS_PASSWORD found in environment.\n"
            "       The toolbox will fall back to the cached token from\n"
            "       `copernicusmarine login`. If you have not logged in yet, run:\n\n"
            "           copernicusmarine login\n\n"
            "       Or fill in backend/.env with your credentials.\n"
        )
    else:
        print(f"\n[INFO] Credentials found in environment for user: {username!r}")

    # ── 3. Call the catalogue (metadata-only, no download) ────────
    print("\n[...] Fetching catalogue metadata (this may take 5–15 s) …\n")
    t0 = time.time()

    try:
        import copernicusmarine as cm

        # describe() returns catalogue JSON without downloading anything.
        # We ask for a single well-known product to keep the response small.
        catalogue = cm.describe(
            include_datasets=True,
            include_description=True,
        )

        elapsed = time.time() - t0
        n_products = len(catalogue.get("products", []))

        print(f"[OK] Connection successful in {elapsed:.1f}s.")
        print(f"     Catalogue returned {n_products} product(s).")
        print(
            "\n[NEXT STEP] Run the discovery script to find your dataset ID:\n"
            "            python scripts/discover_datasets.py\n"
        )

    except Exception as exc:  # noqa: BLE001
        elapsed = time.time() - t0
        _print_error(exc, elapsed, using_env_creds)
        sys.exit(1)


def _print_error(exc: Exception, elapsed: float, using_env_creds: bool) -> None:
    msg = str(exc).lower()
    print(f"\n[FAIL] Connection failed after {elapsed:.1f}s.")

    if "timeout" in msg or "timed out" in msg:
        print(textwrap.dedent("""\
            Diagnosis: Network timeout.
            Fixes:
              - Check your internet connection.
              - Try again in a few minutes (service may be temporarily busy).
              - If behind a proxy, set HTTP_PROXY / HTTPS_PROXY in your shell.\
        """))

    elif "401" in msg or "unauthorized" in msg or "invalid credentials" in msg:
        if using_env_creds:
            print(textwrap.dedent("""\
                Diagnosis: Invalid credentials in .env.
                Fixes:
                  - Double-check COPERNICUS_USERNAME and COPERNICUS_PASSWORD in backend/.env.
                  - Register at: https://data.marine.copernicus.eu/register\
            """))
        else:
            print(textwrap.dedent("""\
                Diagnosis: No valid cached token found.
                Fixes:
                  - Run: copernicusmarine login
                  - Or fill in COPERNICUS_USERNAME / COPERNICUS_PASSWORD in backend/.env.\
            """))

    elif "403" in msg or "forbidden" in msg:
        print(textwrap.dedent("""\
            Diagnosis: Access forbidden — your account may not have the required
            service tier, or the token has expired.
            Fixes:
              - Run: copernicusmarine login   (refreshes the cached token)
              - Check account status at: https://data.marine.copernicus.eu\
        """))

    elif "token" in msg or "expired" in msg:
        print(textwrap.dedent("""\
            Diagnosis: Cached token may be expired.
            Fix: Run `copernicusmarine login` to refresh it.\
        """))

    else:
        print(f"Diagnosis: Unexpected error.\nDetails:   {exc!r}")

    print()


if __name__ == "__main__":
    main()
