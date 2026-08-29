import base64
import os
import re
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

# Automatically load environment variables from .env file
load_dotenv()


class GitHubClient:
    """Client for fetching repository structure and content via GitHub REST API."""

    def __init__(self, token: Optional[str] = None):
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        
        # Priority: 1. Token passed from caller -> 2. GITHUB_TOKEN from .env / OS env
        auth_token = token if (token and token.strip() and token.strip().lower() not in ["string", "none", "null"]) else os.getenv("GITHUB_TOKEN")
        
        if auth_token and auth_token.strip():
            # Support standard Bearer / Token authorization header
            clean_token = auth_token.strip()
            self.headers["Authorization"] = f"Bearer {clean_token}" if not clean_token.startswith("Bearer ") else clean_token

        self.base_url = "https://api.github.com"

    @staticmethod
    def parse_repo_url(url: str) -> tuple[str, str]:
        """Extract owner and repo name from various GitHub URL formats."""
        clean_url = url.strip().rstrip("/")
        pattern = r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"
        match = re.search(pattern, clean_url)
        if not match:
            raise ValueError(
                "Invalid GitHub URL. Expected format: https://github.com/owner/repo"
            )
        return match.group("owner"), match.group("repo")

    def get_repo_metadata(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch general repository metadata."""
        res = requests.get(
            f"{self.base_url}/repos/{owner}/{repo}",
            headers=self.headers,
            timeout=10,
        )
        if res.status_code == 404:
            raise ValueError("Repository not found or is private.")
        if res.status_code == 403:
            raise RuntimeError(f"GitHub API Error: 403 - {res.text}")
        if res.status_code != 200:
            raise RuntimeError(f"GitHub API Error: {res.status_code} - {res.text}")
        return res.json()

    def get_file_tree(
        self, owner: str, repo: str, default_branch: str = "main"
    ) -> List[Dict[str, Any]]:
        """Fetch complete recursive git tree."""
        # Try default branch tree, fallback to master if needed
        branches = [default_branch, "main", "master"]
        for branch in set(branches):
            res = requests.get(
                f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
                headers=self.headers,
                timeout=15,
            )
            if res.status_code == 200:
                data = res.json()
                return data.get("tree", [])
        return []

    def get_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        """Fetch decoded raw text content of a single file."""
        res = requests.get(
            f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
            headers=self.headers,
            timeout=10,
        )
        if res.status_code != 200:
            return None
        data = res.json()
        if data.get("encoding") == "base64" and "content" in data:
            try:
                return base64.b64decode(data["content"]).decode(
                    "utf-8", errors="ignore"
                )
            except Exception:
                return None
        return None

    def fetch_full_repo_context(self, repo_url: str) -> Dict[str, Any]:
        """Orchestrate collection of metadata, structure, docs, dependencies, and code."""
        owner, repo = self.parse_repo_url(repo_url)
        meta = self.get_repo_metadata(owner, repo)
        default_branch = meta.get("default_branch", "main")
        tree = self.get_file_tree(owner, repo, default_branch)

        file_paths = [item["path"] for item in tree if item["type"] == "blob"]

        # Locate README
        readme_path = next(
            (p for p in file_paths if re.match(r"^readme(\.md|\.rst|\.txt)?$", p, re.I)),
            None,
        )
        readme_content = (
            self.get_file_content(owner, repo, readme_path) if readme_path else ""
        )

        # Locate Dependency manifests
        dep_files = {}
        target_dep_names = [
            "requirements.txt",
            "pyproject.toml",
            "setup.py",
            "Pipfile",
            "package.json",
            "go.mod",
            "Cargo.toml",
        ]
        for p in file_paths:
            filename = p.split("/")[-1]
            if filename in target_dep_names and len(dep_files) < 3:
                content = self.get_file_content(owner, repo, p)
                if content:
                    dep_files[p] = content

        # Identify test files
        test_files = [
            p
            for p in file_paths
            if "test" in p.lower()
            or p.startswith("tests/")
            or p.endswith(("_test.py", "test_.py", ".test.js", ".spec.ts"))
        ]

        # Sample source code files for quality heuristics (up to 4 primary code files)
        code_samples = {}
        code_exts = (".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp")
        source_candidates = [
            p
            for p in file_paths
            if p.endswith(code_exts)
            and not any(k in p.lower() for k in ["test", "venv", "node_modules", "dist", "build"])
        ]

        for p in source_candidates[:4]:
            content = self.get_file_content(owner, repo, p)
            if content:
                code_samples[p] = content

        return {
            "owner": owner,
            "repo": repo,
            "meta": {
                "stars": meta.get("stargazers_count", 0),
                "forks": meta.get("forks_count", 0),
                "open_issues": meta.get("open_issues_count", 0),
                "license": meta.get("license", {}).get("spdx_id")
                if meta.get("license")
                else None,
                "description": meta.get("description", ""),
                "default_branch": default_branch,
            },
            "file_paths": file_paths,
            "readme_content": readme_content or "",
            "dependency_files": dep_files,
            "test_files": test_files,
            "code_samples": code_samples,
        }