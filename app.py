import os
import sqlite3
import tempfile
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.github_client import GitHubClient
from src.rules_engine import RulesEngine
from src.llm_evaluator import LLMEvaluator

# Store database in system temp folder so writes never trigger Live Server reloads
DB_PATH = os.path.join(tempfile.gettempdir(), "github_health_analyzer_history.db")


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_identifier TEXT NOT NULL,
                scan_date TEXT NOT NULL,
                score INTEGER NOT NULL
            )
        """)


init_db()


def get_history(repo_identifier: str) -> List[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT scan_date, score FROM scan_history WHERE repo_identifier = ? ORDER BY id ASC",
            (repo_identifier,),
        )
        rows = cursor.fetchall()
        return [{"date": r[0], "score": r[1]} for r in rows]


def save_scan(repo_identifier: str, score: int):
    scan_date = datetime.now().strftime("%b %d")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO scan_history (repo_identifier, scan_date, score) VALUES (?, ?, ?)",
            (repo_identifier, scan_date, score),
        )


app = FastAPI(
    title="AI GitHub Project Health Analyzer API",
    description="Full-featured REST API for repository auditing, comparison, and fix generation.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., example="https://github.com/aryanpandit10/personal-knowledge-engine")
    groq_api_key: Optional[str] = Field(None, example=None)
    github_token: Optional[str] = Field(None, example=None)


class CompareRequest(BaseModel):
    repo_url_a: str = Field(...)
    repo_url_b: str = Field(...)
    groq_api_key: Optional[str] = Field(None)
    github_token: Optional[str] = Field(None)


class HealthScoreBreakdown(BaseModel):
    code_quality: int = 70
    security: int = 80
    documentation: int = 70
    testing: int = 50
    structure: int = 80
    dependencies: int = 85


class SecurityReport(BaseModel):
    score: int
    status: str
    risks: List[str]
    strengths: List[str] = []
    penalties: List[str] = []


class DimensionExplanation(BaseModel):
    strengths: List[str] = []
    penalties: List[str] = []


class RoadmapCategories(BaseModel):
    fix_first: List[str] = []
    fix_next: List[str] = []
    improve_later: List[str] = []
    nice_to_have: List[str] = []


class AIRoadmap(BaseModel):
    categories: RoadmapCategories
    sequential_path: List[str] = []


class HistoryItem(BaseModel):
    date: str
    score: int


class AuditResponse(BaseModel):
    owner: str
    repo: str
    overall_health: int
    scores: HealthScoreBreakdown
    score_explanations: Dict[str, DimensionExplanation]
    security: SecurityReport
    delta: int
    history: List[HistoryItem]
    roadmap: AIRoadmap
    summary: str
    strengths: List[str]
    recommendations: List[str]
    meta: Dict[str, Any]
    discovered_files: Dict[str, Any]
    starter_fixes: Dict[str, str]
    badge_markdown: str


def run_audit_pipeline(repo_url: str, groq_key: Optional[str], gh_token: Optional[str]) -> AuditResponse:
    client = GitHubClient(token=gh_token)
    evaluator = LLMEvaluator(api_key=groq_key)

    repo_data = client.fetch_full_repo_context(repo_url)

    rule_scores = {
        "security": RulesEngine.evaluate_security(repo_data["file_paths"]),
        "documentation": RulesEngine.evaluate_documentation(repo_data["readme_content"], repo_data["file_paths"]),
        "testing": RulesEngine.evaluate_testing(repo_data["test_files"], repo_data["file_paths"]),
        "structure": RulesEngine.evaluate_structure(repo_data["file_paths"]),
        "dependencies": RulesEngine.evaluate_dependencies(repo_data["dependency_files"]),
    }

    analysis = evaluator.analyze_repository(repo_data, rule_scores)
    scores_data = analysis.get("scores", {})

    owner = repo_data["owner"]
    repo = repo_data["repo"]
    repo_identifier = f"{owner}/{repo}"
    overall = int(analysis.get("overall_health", 70))

    # Before vs After Historical Tracking
    previous_history = get_history(repo_identifier)
    delta = (overall - previous_history[-1]["score"]) if previous_history else 0
    save_scan(repo_identifier, overall)
    updated_history = get_history(repo_identifier)

    badge_color = "brightgreen" if overall >= 80 else ("yellow" if overall >= 60 else "red")
    badge_md = f"[![Project Health](https://img.shields.io/badge/Health-{overall}%2F100-{badge_color})](https://github.com/{owner}/{repo})"

    starter_fixes = RulesEngine.generate_starter_fixes(owner, repo)

    # Score Explanations ("Why the score exists")
    score_explanations_raw = analysis.get("score_explanations", {})
    score_explanations = {
        dim: DimensionExplanation(
            strengths=score_explanations_raw.get(dim, {}).get("strengths", rule_scores.get(dim, {}).get("strengths", [])),
            penalties=score_explanations_raw.get(dim, {}).get("penalties", rule_scores.get(dim, {}).get("penalties", [])),
        )
        for dim in ["code_quality", "security", "documentation", "testing", "structure", "dependencies"]
    }

    # AI Improvement Roadmap
    roadmap_raw = analysis.get("roadmap", {})
    categories_raw = roadmap_raw.get("categories", {})
    roadmap = AIRoadmap(
        categories=RoadmapCategories(
            fix_first=categories_raw.get("fix_first", []),
            fix_next=categories_raw.get("fix_next", []),
            improve_later=categories_raw.get("improve_later", []),
            nice_to_have=categories_raw.get("nice_to_have", []),
        ),
        sequential_path=roadmap_raw.get("sequential_path", []),
    )

    return AuditResponse(
        owner=owner,
        repo=repo,
        overall_health=overall,
        scores=HealthScoreBreakdown(
            code_quality=int(scores_data.get("code_quality", 70)),
            security=int(scores_data.get("security", rule_scores["security"]["score"])),
            documentation=int(scores_data.get("documentation", rule_scores["documentation"]["score"])),
            testing=int(scores_data.get("testing", rule_scores["testing"]["score"])),
            structure=int(scores_data.get("structure", rule_scores["structure"]["score"])),
            dependencies=int(scores_data.get("dependencies", rule_scores["dependencies"]["score"])),
        ),
        score_explanations=score_explanations,
        security=SecurityReport(**rule_scores["security"]),
        delta=delta,
        history=[HistoryItem(**h) for h in updated_history],
        roadmap=roadmap,
        summary=str(analysis.get("summary", "Analysis completed.")),
        strengths=list(analysis.get("strengths", [])),
        recommendations=list(analysis.get("recommendations", [])),
        meta=repo_data["meta"],
        discovered_files={
            "total_files": len(repo_data["file_paths"]),
            "test_files": repo_data["test_files"],
            "manifests": list(repo_data["dependency_files"].keys()),
        },
        starter_fixes=starter_fixes,
        badge_markdown=badge_md,
    )


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "GitHub Health Analyzer API"}


@app.post("/api/v1/analyze", response_model=AuditResponse, tags=["Analysis"])
def analyze_repository(payload: AnalyzeRequest):
    groq_key = (
        payload.groq_api_key.strip()
        if payload.groq_api_key and payload.groq_api_key.strip().lower() not in ["string", "none", "null", ""]
        else None
    )
    gh_token = (
        payload.github_token.strip()
        if payload.github_token and payload.github_token.strip().lower() not in ["string", "none", "null", ""]
        else None
    )

    try:
        return run_audit_pipeline(payload.repo_url, groq_key, gh_token)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


@app.post("/api/v1/compare", tags=["Analysis"])
def compare_repositories(payload: CompareRequest):
    groq_key = (
        payload.groq_api_key.strip()
        if payload.groq_api_key and payload.groq_api_key.strip().lower() not in ["string", "none", "null", ""]
        else None
    )
    gh_token = (
        payload.github_token.strip()
        if payload.github_token and payload.github_token.strip().lower() not in ["string", "none", "null", ""]
        else None
    )

    try:
        report_a = run_audit_pipeline(payload.repo_url_a, groq_key, gh_token)
        report_b = run_audit_pipeline(payload.repo_url_b, groq_key, gh_token)
        winner = (
            f"{report_a.owner}/{report_a.repo}"
            if report_a.overall_health >= report_b.overall_health
            else f"{report_b.owner}/{report_b.repo}"
        )
        return {
            "repository_a": report_a,
            "repository_b": report_b,
            "winner": winner,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")