#!/usr/bin/env python3
"""Check every 'name==version' line in a requirements file against PyPI.

For each line, two separate PyPI JSON API calls are made:
  - https://pypi.org/pypi/<name>/json          -> package exists at all?
  - https://pypi.org/pypi/<name>/<version>/json -> that exact version exists?

Both return 404 (via urllib.error.HTTPError) when the thing being asked
about doesn't exist, which is how "not on PyPI" is detected below.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime

PYPI_BASE = "https://pypi.org/pypi"
# PyPI returns 403 for requests with no User-Agent at all, so set one.
HEADERS = {"User-Agent": "pypi-dependency-checker/1.0"}


def fetch_json(url: str) -> dict | None:
    """GET url and return the parsed JSON body, or None if it 404s.

    Any other HTTP error (5xx, rate limiting, etc.) is re-raised rather
    than silently treated as "missing" - only a 404 means "doesn't exist".
    """
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def parse_line(line: str) -> tuple[str, str] | None:
    """Split a 'name==version' line into (name, version).

    Returns None for lines that aren't a simple pinned dependency (blank
    lines, comments, or anything without a '==').
    """
    line = line.strip()
    if not line or line.startswith("#") or "==" not in line:
        return None
    name, _, version = line.partition("==")
    name, version = name.strip(), version.strip()
    if not name or not version:
        return None
    return name, version


def check_file(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        raw_lines = f.readlines()

    dependencies = [parse_line(line) for line in raw_lines]
    dependencies = [dep for dep in dependencies if dep is not None]
    checked = len(dependencies)

    packages_missing: list[str] = []
    versions_missing: list[str] = []
    oldest: tuple[datetime, str, str] | None = None  # (upload_time, name, version)

    for name, version in dependencies:
        package_data = fetch_json(f"{PYPI_BASE}/{name}/json")
        if package_data is None:
            packages_missing.append(name)
            continue

        release_data = fetch_json(f"{PYPI_BASE}/{name}/{version}/json")
        if release_data is None:
            versions_missing.append(f"{name}=={version}")
            continue

        urls = release_data.get("urls") or []
        if not urls:
            # Package+version exist but no files were ever uploaded for it
            # (rare, but possible) - nothing to compare, so skip.
            continue

        upload_time_str = urls[0]["upload_time"]
        upload_time = datetime.strptime(upload_time_str, "%Y-%m-%dT%H:%M:%S")

        if oldest is None or upload_time < oldest[0]:
            oldest = (upload_time, name, version)

    print(f"Dependencies checked: {checked}")
    print(f"Packages not on PyPI: {len(packages_missing)}")
    print(f"Versions not on PyPI: {len(versions_missing)}")
    if oldest is not None:
        upload_time, name, version = oldest
        print(f"Oldest pinned release: {name}=={version}({upload_time.year})")
    else:
        print("Oldest pinned release: none found")


if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    check_file(file_path)
