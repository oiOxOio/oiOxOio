#!/usr/bin/env python3
"""Refresh a public-only GitHub profile snapshot using the Python standard library.

Repository and star totals include every owned, public, non-fork repository,
including the profile repository. Language totals are GitHub Linguist byte counts
for those repositories, not a claim about the author's proficiency. PR totals are
all-time public PRs authored by the user, across all public repositories.

All API requests must succeed before the previous snapshot is replaced. A failed
refresh exits nonzero and leaves the last successful snapshot untouched.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


API = "https://api.github.com"
COLORS = {
    "C": "#555555",
    "C#": "#178600",
    "C++": "#f34b7d",
    "CSS": "#563d7c",
    "Dockerfile": "#384d54",
    "Go": "#00add8",
    "HTML": "#e34c26",
    "Java": "#b07219",
    "JavaScript": "#f1e05a",
    "Kotlin": "#a97bff",
    "Python": "#3572a5",
    "Rust": "#dea584",
    "SCSS": "#c6538c",
    "Shell": "#89e051",
    "TypeScript": "#3178c6",
    "Vue": "#41b883",
}


def require_count(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Expected a nonnegative integer for {label}")
    return value


def get_json(path: str) -> object:
    """GET a GitHub REST resource, with short bounded retries and no secret logs."""
    url = API + path
    if not path.startswith("/") or urlsplit(url).netloc != "api.github.com":
        raise ValueError("Only api.github.com REST requests are allowed")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-profile-public-stats",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            retryable = exc.code in (429, 500, 502, 503, 504)
            retryable |= exc.code == 403 and "Retry-After" in exc.headers
            if retryable and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"GitHub API returned HTTP {exc.code} for {path}") from None
        except URLError:
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"GitHub API connection failed for {path}") from None
    raise RuntimeError("GitHub API request did not complete")


def public_repositories(username: str) -> list[dict]:
    """The public user-repository endpoint is paginated; forks stay excluded."""
    repositories = []
    seen_ids = set()
    page = 1
    while True:
        params = urlencode({"type": "owner", "sort": "full_name", "per_page": 100, "page": page})
        batch = get_json(f"/users/{username}/repos?{params}")
        if not isinstance(batch, list):
            raise ValueError("GitHub returned an invalid repository list")
        for repo in batch:
            if not isinstance(repo, dict) or not isinstance(repo.get("id"), int):
                raise ValueError("GitHub returned invalid repository metadata")
            if repo["id"] in seen_ids:
                raise ValueError("Repository pagination returned a duplicate; retry refresh")
            seen_ids.add(repo["id"])
            # Defense in depth: never include private or forked repositories even
            # if the endpoint's behavior or the token's permissions change.
            if repo.get("private") is not False or repo.get("fork") is not False:
                continue
            if repo.get("owner", {}).get("login", "").casefold() != username.casefold():
                continue
            require_count(repo.get("stargazers_count"), "repository stars")
            repositories.append(repo)
        if len(batch) < 100:
            return repositories
        page += 1


def public_pr_count(username: str, *, merged: bool = False) -> int:
    query = f"author:{username} is:pr is:public"
    if merged:
        query += " is:merged"
    response = get_json("/search/issues?" + urlencode({"q": query, "per_page": 1}))
    if not isinstance(response, dict) or response.get("incomplete_results") is not False:
        raise ValueError("GitHub PR search was incomplete; retaining the previous snapshot")
    return require_count(response.get("total_count"), "public PR search total")


def collect(username: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", username):
        raise ValueError("Invalid GitHub username")
    repos = public_repositories(username)
    languages: Counter[str] = Counter()
    for repo in repos:
        full_name = repo["full_name"]
        # full_name originates in GitHub metadata; enforce the same owner again.
        if not full_name.casefold().startswith(username.casefold() + "/"):
            raise ValueError("Unexpected repository owner in language request")
        data = get_json(f"/repos/{full_name}/languages")
        if not isinstance(data, dict):
            raise ValueError("GitHub returned an invalid language breakdown")
        for language, byte_count in data.items():
            if not isinstance(language, str):
                raise ValueError("GitHub returned an invalid language name")
            languages[language] += require_count(byte_count, "language bytes")

    pull_requests = public_pr_count(username)
    merged_pull_requests = public_pr_count(username, merged=True)
    if merged_pull_requests > pull_requests:
        raise ValueError("GitHub search counts changed during refresh; retry later")
    return {
        "schema_version": 1,
        "username": username,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "GitHub REST API",
        "scope": {
            "repositories": "Owned public non-fork repositories, including the profile repository",
            "stars": "Sum of stars on owned public non-fork repositories",
            "pull_requests": "All-time authored public pull requests across GitHub",
            "merged_pull_requests": "All-time authored public pull requests that were merged",
            "languages": "GitHub Linguist byte counts across owned public non-fork repositories",
        },
        "repositories": len(repos),
        "stars": sum(repo["stargazers_count"] for repo in repos),
        "pull_requests": pull_requests,
        "merged_pull_requests": merged_pull_requests,
        "languages_status": "complete",
        "languages": [
            {"name": language, "bytes": count, "color": COLORS.get(language, "#8b949e")}
            for language, count in sorted(languages.items(), key=lambda item: (-item[1], item[0]))
            if count > 0
        ],
        "projects": [
            {
                "name": repo["name"],
                "url": repo["html_url"],
                "description": repo.get("description") or "",
                "language": repo.get("language"),
                "stars": repo["stargazers_count"],
            }
            for repo in sorted(repos, key=lambda repo: (-repo["stargazers_count"], repo["name"].casefold()))
        ],
    }


def save_atomic(destination: Path, snapshot: dict) -> None:
    encoded = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(encoded)
        os.replace(temp_path, destination)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default=os.environ.get("PROFILE_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "oiOxOio")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "assets" / "stats.json")
    args = parser.parse_args()
    try:
        snapshot = collect(args.username)
        save_atomic(args.output, snapshot)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"Profile statistics refresh failed; previous snapshot retained: {exc}", file=sys.stderr)
        return 1
    print(f"Updated public statistics for {args.username}: {snapshot['repositories']} repositories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
