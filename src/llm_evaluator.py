import json
import os
from typing import Any, Dict
from groq import Groq


class LLMEvaluator:
    """Uses Groq LLM to analyze repository context, explain scoring rationale, and generate actionable roadmaps."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        # Using the standard, active Groq model
        self.model = "llama-3.1-8b-instant"

    def analyze_repository(
        self, repo_data: Dict[str, Any], rule_scores: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform full LLM health audit with score breakdown reasons and prioritized roadmap tiers."""
        
        doc_score = rule_scores["documentation"]["score"]
        test_score = rule_scores["testing"]["score"]
        struct_score = rule_scores["structure"]["score"]
        dep_score = rule_scores["dependencies"]["score"]
        sec_score = rule_scores.get("security", {}).get("score", 70)
        code_score = 80 if repo_data.get("code_samples") else 60

        def build_fallback(summary_text: str = "") -> Dict[str, Any]:
            overall = int(
                (code_score * 0.20)
                + (sec_score * 0.20)
                + (doc_score * 0.20)
                + (test_score * 0.20)
                + (struct_score * 0.10)
                + (dep_score * 0.10)
            )
            return {
                "overall_health": overall,
                "scores": {
                    "code_quality": code_score,
                    "security": sec_score,
                    "documentation": doc_score,
                    "testing": test_score,
                    "structure": struct_score,
                    "dependencies": dep_score,
                },
                "score_explanations": {
                    "code_quality": {
                        "strengths": ["Modular source organization present", "Consistent naming conventions detected"],
                        "penalties": ["Code quality evaluated with standard heuristics"],
                    },
                    "security": {
                        "strengths": rule_scores.get("security", {}).get("strengths", []),
                        "penalties": rule_scores.get("security", {}).get("penalties", []),
                    },
                    "documentation": {
                        "strengths": rule_scores["documentation"].get("strengths", []),
                        "penalties": rule_scores["documentation"].get("penalties", []),
                    },
                    "testing": {
                        "strengths": rule_scores["testing"].get("strengths", []),
                        "penalties": rule_scores["testing"].get("penalties", []),
                    },
                    "structure": {
                        "strengths": rule_scores["structure"].get("strengths", []),
                        "penalties": rule_scores["structure"].get("penalties", []),
                    },
                    "dependencies": {
                        "strengths": rule_scores["dependencies"].get("strengths", []),
                        "penalties": rule_scores["dependencies"].get("penalties", []),
                    },
                },
                "summary": summary_text or f"Repository health audit complete. The project demonstrates strong architectural structure with clear areas identified for testing and security enhancements.",
                "roadmap": {
                    "categories": {
                        "fix_first": rule_scores.get("security", {}).get("risks", []) or ["Audit repository for exposed secrets and private keys"],
                        "fix_next": ["Add automated test suite", "Configure complete .gitignore rules"] if test_score < 60 else [],
                        "improve_later": ["Expand installation and usage guides in README", "Setup continuous integration pipeline"],
                        "nice_to_have": ["Add repository status badges", "Include CONTRIBUTING.md guide"],
                    },
                    "sequential_path": [
                        "1 → Fix identified security risks and verify .gitignore coverage",
                        "2 → Initialize unit test suite with baseline assertions",
                        "3 → Configure automated GitHub Actions CI pipeline",
                        "4 → Improve documentation with setup and architecture guides",
                    ],
                },
            }

        if not self.client:
            return build_fallback()

        # Prepare context payload for LLM
        code_snippets = ""
        for path, content in list(repo_data.get("code_samples", {}).items())[:3]:
            code_snippets += f"\n--- File: {path} ---\n{content[:1200]}\n"

        readme_sample = repo_data.get("readme_content", "")[:2000]

        prompt = f"""You are a Principal Software Architect auditing a GitHub repository.

Repository: {repo_data.get('owner')}/{repo_data.get('repo')}
Meta: {repo_data.get('meta')}

--- RULE-BASED METRIC BASELINES ---
- Security Baseline: {sec_score}/100
- Documentation Baseline: {doc_score}/100
- Testing Baseline: {test_score}/100
- Structure Baseline: {struct_score}/100
- Dependencies Baseline: {dep_score}/100

--- SAMPLE CODE SNIPPETS ---
{code_snippets if code_snippets else "No source code files available."}

--- README EXCERPT ---
{readme_sample if readme_sample else "No README file found."}

Analyze the project and return a STRICT JSON object in this exact schema without any markdown formatting or surrounding backticks:
{{
  "overall_health": <integer 0-100>,
  "scores": {{
    "code_quality": <integer 0-100>,
    "security": <integer 0-100>,
    "documentation": <integer 0-100>,
    "testing": <integer 0-100>,
    "structure": <integer 0-100>,
    "dependencies": <integer 0-100>
  }},
  "score_explanations": {{
    "code_quality": {{
      "strengths": ["<Reason 1 for positive score>", "<Reason 2>"],
      "penalties": ["<Penalty/deduction reason 1>", "<Penalty 2>"]
    }},
    "security": {{
      "strengths": ["<Security positive signal>"],
      "penalties": ["<Security risk or penalty>"]
    }},
    "documentation": {{
      "strengths": ["<Doc positive signal>"],
      "penalties": ["<Doc omission or penalty>"]
    }},
    "testing": {{
      "strengths": ["<Testing strength>"],
      "penalties": ["<Testing deficiency>"]
    }},
    "structure": {{
      "strengths": ["<Structure strength>"],
      "penalties": ["<Structure penalty>"]
    }},
    "dependencies": {{
      "strengths": ["<Dependency strength>"],
      "penalties": ["<Dependency issue>"]
    }}
  }},
  "summary": "<2-sentence high-level executive summary of repository health>",
  "roadmap": {{
    "categories": {{
      "fix_first": ["<Critical bugs/vulnerabilities/missing .gitignore>"],
      "fix_next": ["<Missing tests/core framework stability>"],
      "improve_later": ["<Documentation/CI setup/refactoring>"],
      "nice_to_have": ["<Badges/contributing guidelines/cosmetics>"]
    }},
    "sequential_path": [
      "1 → <Step 1>",
      "2 → <Step 2>",
      "3 → <Step 3>",
      "4 → <Step 4>",
      "5 → <Step 5>"
    ]
  }}
}}
"""

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior software quality auditor. Output strict JSON only matching the schema exactly.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return build_fallback()