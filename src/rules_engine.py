import re
from typing import Any, Dict, List, Optional


class RulesEngine:
    """Calculates deterministic heuristic scores across repository dimensions with full transparency."""

    @staticmethod
    def evaluate_security(file_paths: List[str]) -> Dict[str, Any]:
        """Detect potential secrets, sensitive files, and security configs."""
        score = 100
        strengths: List[str] = []
        penalties: List[str] = []
        risks: List[str] = []

        sensitive_patterns = [
            (r"(^|/)\.env(\..+)?$", "Committed environment file (.env) detected"),
            (r".*\.(pem|key|pkcs12|pfx|p12)$", "Private key/certificate file detected"),
            (r".*credentials(\.json|\.yml|\.yaml)$", "Credentials manifest file detected"),
            (r".*id_rsa.*", "SSH private key detected"),
        ]

        found_sensitive = False
        for pattern, warning in sensitive_patterns:
            for p in file_paths:
                if re.search(pattern, p, re.IGNORECASE):
                    found_sensitive = True
                    score -= 30
                    penalties.append(f"{warning}: `{p}` (-30 pts)")
                    risks.append(f"{warning}: `{p}`")

        if not found_sensitive:
            strengths.append("No sensitive files or exposed environment variables found")

        has_security_md = any(
            p.lower().startswith("security.md") or p.lower().startswith(".github/security.md")
            for p in file_paths
        )
        if has_security_md:
            strengths.append("Dedicated `SECURITY.md` vulnerability reporting policy detected")
        else:
            score -= 10
            penalties.append("No formal `SECURITY.md` file found (-10 pts)")

        has_gitignore = any(p == ".gitignore" or p.endswith("/.gitignore") for p in file_paths)
        if has_gitignore:
            strengths.append("`.gitignore` configured to prevent leaking unwanted files")
        else:
            score -= 20
            penalties.append("Missing `.gitignore` file (high risk for accidental credential commits) (-20 pts)")
            risks.append("Missing `.gitignore` file")

        score = max(0, min(100, score))
        return {
            "score": score,
            "status": "Secure" if score >= 80 else ("Warning" if score >= 50 else "Critical"),
            "risks": risks,
            "strengths": strengths,
            "penalties": penalties,
        }

    @staticmethod
    def evaluate_documentation(readme_content: str, file_paths: List[str]) -> Dict[str, Any]:
        """Evaluates documentation completeness and quality."""
        score = 0
        strengths: List[str] = []
        penalties: List[str] = []

        if not readme_content:
            return {
                "score": 10,
                "strengths": [],
                "penalties": ["Missing README file (-90 pts)"],
                "details": ["Missing README file."],
            }

        score += 30
        strengths.append("Primary README documentation present (+30 pts)")

        words = readme_content.split()
        length = len(words)
        if length > 300:
            score += 25
            strengths.append(f"Comprehensive documentation depth ({length} words) (+25 pts)")
        elif length > 100:
            score += 15
            strengths.append(f"Moderate documentation length ({length} words) (+15 pts)")
        else:
            penalties.append(f"Brief or incomplete README ({length} words) (-15 pts)")

        readme_lower = readme_content.lower()
        sections = {
            "installation": ("install", "setup", "getting started"),
            "usage": ("usage", "example", "quickstart", "how to run"),
            "architecture": ("architecture", "system design", "workflow", "features"),
            "license/contributing": ("license", "contributing"),
        }

        for sec_name, keywords in sections.items():
            if any(kw in readme_lower for kw in keywords):
                score += 10
                strengths.append(f"Contains clear '{sec_name}' guidelines (+10 pts)")
            else:
                penalties.append(f"Missing recommended '{sec_name}' section (-10 pts)")

        has_docs_folder = any(p.startswith("docs/") or "doc" in p.lower() for p in file_paths)
        if has_docs_folder:
            score += 5
            strengths.append("Dedicated `/docs` directory detected (+5 pts)")

        return {
            "score": min(100, score),
            "strengths": strengths,
            "penalties": penalties,
            "details": strengths + penalties,
        }

    @staticmethod
    def evaluate_testing(test_files: List[str], file_paths: List[str]) -> Dict[str, Any]:
        """Evaluates automated test suites and CI workflow coverage."""
        score = 0
        strengths: List[str] = []
        penalties: List[str] = []

        total_source_files = len([
            p for p in file_paths
            if p.endswith((".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp"))
        ])

        if not test_files:
            penalties.append("No automated test files or test directory discovered (-55 pts)")
        else:
            score += 40
            strengths.append(f"Discovered {len(test_files)} dedicated test file(s) (+40 pts)")

        ci_patterns = [".github/workflows", ".gitlab-ci.yml", "circleci", "azure-pipelines.yml"]
        has_ci = any(any(ci in p for ci in ci_patterns) for p in file_paths)
        if has_ci:
            score += 30
            strengths.append("Automated CI/CD workflow pipeline active (+30 pts)")
        else:
            penalties.append("No automated CI/CD pipeline configured (-30 pts)")

        if total_source_files > 0:
            ratio = len(test_files) / total_source_files
            if ratio >= 0.3:
                score += 30
                strengths.append(f"High test-to-source file ratio ({ratio:.1%}) (+30 pts)")
            elif ratio >= 0.1:
                score += 20
                strengths.append(f"Moderate test-to-source file ratio ({ratio:.1%}) (+20 pts)")
            else:
                score += 10
                penalties.append(f"Low test file coverage ratio ({ratio:.1%}) (-20 pts)")

        final_score = min(100, score)
        if not test_files and not has_ci:
            final_score = 15

        return {
            "score": final_score,
            "strengths": strengths,
            "penalties": penalties,
            "details": strengths + penalties,
        }

    @staticmethod
    def evaluate_structure(file_paths: List[str]) -> Dict[str, Any]:
        """Evaluates repo layout, licenses, and architecture patterns."""
        score = 30
        strengths: List[str] = ["Baseline project structure established (+30 pts)"]
        penalties: List[str] = []

        if any(p == ".gitignore" or p.endswith("/.gitignore") for p in file_paths):
            score += 25
            strengths.append("Proper `.gitignore` file present (+25 pts)")
        else:
            penalties.append("Missing `.gitignore` file (-25 pts)")

        modular_folders = {"src", "app", "pkg", "lib", "internal", "core", "components"}
        has_modular_structure = any(
            any(p.startswith(f"{folder}/") for folder in modular_folders)
            for p in file_paths
        )
        if has_modular_structure:
            score += 25
            strengths.append("Clean modular directory organization (+25 pts)")
        else:
            penalties.append("Flat structure detected; lack of modular directories (`src/`, `app/`, etc.) (-25 pts)")

        if any(p.lower().startswith("license") for p in file_paths):
            score += 20
            strengths.append("Open-source LICENSE file declared (+20 pts)")
        else:
            penalties.append("Missing LICENSE file (-20 pts)")

        return {
            "score": min(100, score),
            "strengths": strengths,
            "penalties": penalties,
            "details": strengths + penalties,
        }

    @staticmethod
    def evaluate_dependencies(dep_files: Dict[str, str]) -> Dict[str, Any]:
        """Evaluates dependency management manifests and version pinning."""
        score = 0
        strengths: List[str] = []
        penalties: List[str] = []

        if not dep_files:
            return {
                "score": 20,
                "strengths": [],
                "penalties": ["No standard dependency manifest file detected (-80 pts)"],
                "details": ["No standard dependency manifest detected."],
            }

        score += 50
        strengths.append(f"Dependency manifests detected: {', '.join(dep_files.keys())} (+50 pts)")

        has_pinned = False
        for fname, content in dep_files.items():
            if "requirements" in fname and ("==" in content or ">=" in content or "~=" in content):
                has_pinned = True
            elif "package.json" in fname and "dependencies" in content:
                has_pinned = True
            elif "Cargo.toml" in fname or "go.mod" in fname or "Pipfile.lock" in fname or "poetry.lock" in fname:
                has_pinned = True

        if has_pinned:
            score += 50
            strengths.append("Version constraints and explicit dependency pinning configured (+50 pts)")
        else:
            score += 25
            penalties.append("Unpinned dependency versions detected (-25 pts)")

        return {
            "score": min(100, score),
            "strengths": strengths,
            "penalties": penalties,
            "details": strengths + penalties,
        }

    @classmethod
    def evaluate_repository(
        cls,
        file_paths: List[str],
        readme_content: str = "",
        test_files: Optional[List[str]] = None,
        dep_files: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Comprehensive evaluation aggregating sub-scores with overall score explanations."""
        if test_files is None:
            test_files = [p for p in file_paths if "test" in p.lower() or "spec" in p.lower()]
        if dep_files is None:
            dep_files = {}

        sec_res = cls.evaluate_security(file_paths)
        doc_res = cls.evaluate_documentation(readme_content, file_paths)
        test_res = cls.evaluate_testing(test_files, file_paths)
        struct_res = cls.evaluate_structure(file_paths)
        dep_res = cls.evaluate_dependencies(dep_files)

        weights = {
            "security": 0.25,
            "testing": 0.25,
            "documentation": 0.20,
            "structure": 0.15,
            "dependencies": 0.15,
        }

        overall_score = round(
            sec_res["score"] * weights["security"]
            + test_res["score"] * weights["testing"]
            + doc_res["score"] * weights["documentation"]
            + struct_res["score"] * weights["structure"]
            + dep_res["score"] * weights["dependencies"]
        )

        all_strengths = (
            sec_res["strengths"]
            + doc_res["strengths"]
            + test_res["strengths"]
            + struct_res["strengths"]
            + dep_res["strengths"]
        )
        all_penalties = (
            sec_res["penalties"]
            + doc_res["penalties"]
            + test_res["penalties"]
            + struct_res["penalties"]
            + dep_res["penalties"]
        )

        return {
            "overall_score": overall_score,
            "dimensions": {
                "security": sec_res,
                "documentation": doc_res,
                "testing": test_res,
                "structure": struct_res,
                "dependencies": dep_res,
            },
            "breakdown": {
                "strengths": all_strengths,
                "penalties": all_penalties,
            },
        }

    @staticmethod
    def generate_starter_fixes(owner: str, repo: str) -> Dict[str, str]:
        """Generate ready-to-use boilerplate fix templates."""
        ci_yaml = """name: CI Quality Gate

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          pip install pytest
      - name: Run test suite
        run: |
          pytest
"""
        test_py = """import pytest

def test_environment_sanity():
    \"\"\"Validate core execution environment.\"\"\"
    assert 1 + 1 == 2

def test_source_import():
    \"\"\"Validate internal package structure imports cleanly.\"\"\"
    try:
        import src
        assert True
    except ImportError:
        pytest.fail("Module 'src' failed to load.")
"""

        mit_license = f"""MIT License

Copyright (c) 2026 {owner}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
"""

        security_md = f"""# Security Policy

## Supported Versions
Only the latest release is actively supported with security patches.

## Reporting a Vulnerability
Please report sensitive security issues directly to the maintainer: **https://github.com/{owner}** rather than opening a public issue.
"""

        return {
            "ci_workflow": ci_yaml,
            "test_starter": test_py,
            "license": mit_license,
            "security_policy": security_md,
        }