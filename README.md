# ⚡ PulseRepo — AI GitHub Health Studio

PulseRepo is a full-stack repository diagnostic platform that audits code quality, security posture, test suites, architecture, and dependency governance using deterministic heuristic scoring and LLM evaluations.

![Project Health](https://img.shields.io/badge/Health-Audit-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11-indigo.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg)

---

## 🌟 Core Features

- **🛡️ Secret & Security Scanner**: Detects committed private keys, credentials, unmanaged environment variables, and missing `.gitignore` or `SECURITY.md` policies.
- **🧠 Transparent Score Explanations**: Breaks down point additions (+pts) and deduction penalties (-pts) for code quality, documentation, testing, structure, and dependencies.
- **🤖 Prioritized AI Improvement Roadmap**: Categorizes tasks into four tiers (*Fix First*, *Fix Next*, *Improve Later*, *Nice to Have*) with a sequential remediation plan.
- **📈 Historical Progress (Delta Tracking)**: Persists audit scores locally to visualize repository health trajectories over time.
- **⚔️ Arena Benchmark Mode**: Compares two repositories side-by-side to crown the cleaner, better-tested codebase.
- **⚡ 1-Click PR Fix Generators**: Generates ready-to-commit boilerplates for GitHub Actions CI, PyTest suites, licenses, security policies, and Shields.io status badges.

---

## 🛠️ Architecture & Tech Stack

- **Backend**: FastAPI, Pydantic, Uvicorn, SQLite3, Requests
- **LLM Engine**: Groq API (`llama-3.1-8b-instant`) with automatic deterministic fallback
- **Frontend**: HTML5, Tailwind CSS (Dark/Neon Glassmorphic UI), Chart.js, Canvas Confetti

---

## 🚀 Getting Started

### 1. Clone & Set Up Virtual Environment
```bash
git clone [https://github.com/aryanpandit10/github-health-analyzer.git](https://github.com/aryanpandit10/github-health-analyzer.git)
cd github-health-analyzer
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate