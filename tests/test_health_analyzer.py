import pytest
from src.rules_engine import RulesEngine
from src.github_client import GitHubClient


def test_parse_repo_url():
    """Verify GitHub URL parsing handles standard patterns."""
    url = "https://github.com/aryanpandit10/github-health-analyzer"
    owner, repo = GitHubClient.parse_repo_url(url)
    assert owner == "aryanpandit10"
    assert repo == "github-health-analyzer"


def test_security_evaluation_clean():
    """Verify security scanner returns high score on clean file list."""
    clean_files = ["src/rules_engine.py", "app.py", ".gitignore", "SECURITY.md"]
    res = RulesEngine.evaluate_security(clean_files)
    assert res["score"] >= 80
    assert len(res["risks"]) == 0


def test_documentation_evaluation():
    """Verify README content evaluation logic."""
    readme_sample = "# PulseRepo\n## Installation\npip install -r requirements.txt\n## Usage\nRun the app"
    file_paths = ["README.md", "docs/guide.md"]
    res = RulesEngine.evaluate_documentation(readme_sample, file_paths)
    assert res["score"] >= 50