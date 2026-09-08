import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import GitHubRepository

GITHUB_API_BASE = "https://api.github.com"
GITHUB_USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")


def validate_github_username(username: str) -> str:
    """Validates GitHub username format to prevent SSRF and path traversal."""
    cleaned = username.strip()
    if not GITHUB_USERNAME_REGEX.match(cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GitHub username format: '{cleaned}'.",
        )
    return cleaned


def get_github_headers(token: Optional[str] = None) -> Dict[str, str]:
    """Generates standard GitHub API headers with safe token handling."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "SkillForge-AI-Client",
    }
    if token:
        clean_token = token.strip()
        headers["Authorization"] = f"Bearer {clean_token}"
    return headers


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Safely parses GitHub ISO 8601 timestamps."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


class GitHubService:
    """
    Service layer isolating GitHub API interactions, fork filtering,
    metadata normalization, and idempotent persistence.
    """

    def __init__(self, client: Optional[httpx.Client] = None):
        self.client = client or httpx.Client(timeout=15.0)

    def verify_user(self, username: str, token: Optional[str] = None) -> Dict[str, Any]:
        """
        Verifies that a GitHub user exists and checks authorization status.
        Never leaks access tokens in exceptions or logs.
        """
        safe_username = validate_github_username(username)
        url = f"{GITHUB_API_BASE}/users/{safe_username}"
        headers = get_github_headers(token)

        try:
            res = self.client.get(url, headers=headers)
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="GitHub API service timed out. Please try again later.",
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to reach GitHub API service. Please try again later.",
            )

        if res.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GitHub user '{safe_username}' not found.",
            )
        elif res.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub authentication failed. Invalid token provided.",
            )
        elif res.status_code in (403, 429):
            detail_msg = "GitHub API rate limit exceeded. Please provide an access token or try again later."
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail_msg,
            )
        elif res.status_code == 422:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="GitHub API validation failed for user request.",
            )
        elif res.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API returned error status {res.status_code}.",
            )

        return res.json()

    def fetch_user_repositories(
        self,
        username: str,
        token: Optional[str] = None,
        max_pages: int = 5,
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetches repositories with safe pagination and rate limit handling.
        """
        safe_username = validate_github_username(username)
        headers = get_github_headers(token)
        repositories: List[Dict[str, Any]] = []

        for page in range(1, max_pages + 1):
            url = f"{GITHUB_API_BASE}/users/{safe_username}/repos"
            params = {
                "per_page": per_page,
                "page": page,
                "type": "owner",
                "sort": "updated",
            }

            try:
                res = self.client.get(url, headers=headers, params=params)
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="GitHub API repository retrieval timed out.",
                )
            except httpx.RequestError:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Network failure during GitHub repository retrieval.",
                )

            if res.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="GitHub authorization rejected during repository discovery.",
                )
            elif res.status_code in (403, 429):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="GitHub API rate limit reached during repository discovery.",
                )
            elif res.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Repositories for user '{safe_username}' could not be located.",
                )
            elif res.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"GitHub API returned unexpected status {res.status_code}.",
                )

            page_data = res.json()
            if not isinstance(page_data, list) or len(page_data) == 0:
                break

            repositories.extend(page_data)
            if len(page_data) < per_page:
                break

        return repositories

    def filter_and_normalize(
        self,
        raw_repos: List[Dict[str, Any]],
        expected_username: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filters out forked repositories and normalizes metadata fields.
        Ensures discovered repositories strictly belong to expected_username.
        """
        normalized = []
        for r in raw_repos:
            # Fork filtering: exclude all forked repositories
            if r.get("fork") is True:
                continue

            # Owner verification: ensure repo belongs strictly to expected GitHub username
            owner_login = ""
            if isinstance(r.get("owner"), dict) and r["owner"].get("login"):
                owner_login = r["owner"]["login"].strip()
            elif r.get("full_name") and "/" in r["full_name"]:
                owner_login = r["full_name"].split("/")[0].strip()

            if expected_username and owner_login:
                if owner_login.lower() != expected_username.strip().lower():
                    continue

            repo_name = r.get("name", "unnamed-repo")
            full_name = r.get("full_name") or (f"{owner_login}/{repo_name}" if owner_login else repo_name)
            html_url = r.get("html_url", "")
            if not html_url:
                continue

            normalized.append(
                {
                    "github_repository_id": r.get("id"),
                    "repo_name": repo_name,
                    "full_name": full_name,
                    "repo_url": html_url,
                    "description": r.get("description"),
                    "default_branch": r.get("default_branch") or "main",
                    "visibility": "private" if r.get("private") else "public",
                    "primary_language": r.get("language"),
                    "is_fork": False,
                    "stars_count": r.get("stargazers_count", 0),
                    "forks_count": r.get("forks_count", 0),
                    "last_pushed_at": parse_iso_datetime(r.get("pushed_at")),
                    "repo_metadata": {
                        "owner": owner_login or (full_name.split("/")[0] if "/" in full_name else None),
                        "has_dockerfile": False,
                        "has_ci_workflow": False,
                        "detected_dependencies": [],
                    },
                }
            )

        return normalized

    def sync_repositories(
        self,
        db: Session,
        username: str,
        user_id: Optional[uuid.UUID] = None,
        token: Optional[str] = None,
    ) -> List[GitHubRepository]:
        """
        Coordinates user verification, repository discovery, fork exclusion,
        and idempotent database persistence.
        """
        # 1. Verify user exists
        self.verify_user(username, token=token)

        # 2. Fetch user repositories
        raw_repos = self.fetch_user_repositories(username, token=token)

        # 3. Filter forks & normalize with owner isolation check
        clean_repos = self.filter_and_normalize(raw_repos, expected_username=username)

        # 4. Idempotent Upsert into PostgreSQL
        persisted_records: List[GitHubRepository] = []
        now = datetime.now()

        for item in clean_repos:
            # Query by user_id and repo_url (or github_repository_id)
            query = db.query(GitHubRepository)
            if user_id:
                query = query.filter(GitHubRepository.user_id == user_id)
            else:
                query = query.filter(GitHubRepository.user_id.is_(None))

            existing = query.filter(
                (GitHubRepository.repo_url == item["repo_url"])
                | (GitHubRepository.github_repository_id == item["github_repository_id"])
            ).first()

            if existing:
                # Update mutable metadata preserving primary key
                existing.repo_name = item["repo_name"]
                existing.full_name = item["full_name"]
                existing.description = item["description"]
                existing.default_branch = item["default_branch"]
                existing.visibility = item["visibility"]
                existing.primary_language = item["primary_language"]
                existing.stars_count = item["stars_count"]
                existing.forks_count = item["forks_count"]
                existing.last_pushed_at = item["last_pushed_at"]
                existing.synced_at = now
                persisted_records.append(existing)
            else:
                new_repo = GitHubRepository(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    github_repository_id=item["github_repository_id"],
                    repo_name=item["repo_name"],
                    full_name=item["full_name"],
                    repo_url=item["repo_url"],
                    description=item["description"],
                    default_branch=item["default_branch"],
                    visibility=item["visibility"],
                    primary_language=item["primary_language"],
                    is_fork=False,
                    stars_count=item["stars_count"],
                    forks_count=item["forks_count"],
                    last_pushed_at=item["last_pushed_at"],
                    repo_metadata=item["repo_metadata"],
                    synced_at=now,
                )
                db.add(new_repo)
                persisted_records.append(new_repo)

        db.commit()
        for rec in persisted_records:
            db.refresh(rec)

        return persisted_records


# Default singleton instance
github_service = GitHubService()
