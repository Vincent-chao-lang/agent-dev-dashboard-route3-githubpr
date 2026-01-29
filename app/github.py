from __future__ import annotations
import os
import re
from dataclasses import dataclass
from typing import Optional

import httpx

@dataclass
class GithubRepo:
    owner: str
    repo: str

def parse_github_repo(repo_url: str) -> Optional[GithubRepo]:
    """Parse GitHub owner/repo from common SSH/HTTPS URLs."""
    s = repo_url.strip()

    m = re.match(r"^git@github\.com:([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$", s)
    if m:
        return GithubRepo(owner=m.group(1), repo=m.group(2))

    m = re.match(r"^https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", s)
    if m:
        return GithubRepo(owner=m.group(1), repo=m.group(2))

    return None

def _client() -> httpx.Client:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")
    api_url = os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "agent-dev-dashboard-route3",
    }
    return httpx.Client(base_url=api_url, headers=headers, timeout=30.0)

def create_or_get_pr(owner: str, repo: str, title: str, head: str, base: str, body: str = "") -> dict:
    """Create PR; if already exists, return existing open PR for that head+base."""
    with _client() as c:
        r = c.post(f"/repos/{owner}/{repo}/pulls", json={"title": title, "head": head, "base": base, "body": body})
        if r.status_code in (200, 201):
            return r.json()

        if r.status_code == 422:
            head_q = f"{owner}:{head}" if ":" not in head else head
            r2 = c.get(f"/repos/{owner}/{repo}/pulls", params={"state": "open", "head": head_q, "base": base, "per_page": 10})
            r2.raise_for_status()
            items = r2.json()
            if items:
                return items[0]

        r.raise_for_status()
        return {}

def comment_on_pr(owner: str, repo: str, pr_number: int, body: str) -> dict:
    with _client() as c:
        r = c.post(f"/repos/{owner}/{repo}/issues/{pr_number}/comments", json={"body": body})
        r.raise_for_status()
        return r.json()
