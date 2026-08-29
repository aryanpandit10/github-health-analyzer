import streamlit as st
import plotly.graph_objects as go
from src.github_client import GitHubClient
from src.rules_engine import RulesEngine
from src.llm_evaluator import LLMEvaluator

st.set_page_config(
    page_title="AI GitHub Project Health Analyzer",
    page_icon="🥇",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .metric-box {
        background-color: #0e1117;
        border: 1px solid #262730;
        border-radius: 10px;
        padding: 18px;
        text-align: center;
    }
    .badge-preview {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("🥇 AI GitHub Project Health Analyzer")
st.caption("Enter any GitHub repository URL to evaluate code quality, structure, tests, and documentation with AI.")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    groq_api_key = st.text_input(
        "Groq API Key (Optional)", 
        type="password", 
        help="Enables qualitative LLM code reviews and tailored recommendations."
    )
    github_token = st.text_input(
        "GitHub Token (Optional)", 
        type="password", 
        help="Increases GitHub API rate limits from 60 to 5,000 requests/hour."
    )
    st.markdown("---")
    st.markdown("### 📊 Analyzed Dimensions")
    st.markdown("- 💻 **Code Quality**\n- 📚 **Documentation**\n- 🧪 **Testing & CI**\n- 🏗️ **Architecture & Modularity**\n- 📦 **Dependencies & Pinning**")

# Search Input
col_url, col_btn = st.columns([4, 1])
with col_url:
    repo_input = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/aryanpandit10/personal-knowledge-engine",
        label_visibility="collapsed"
    )
with col_btn:
    analyze_btn = st.button("🚀 Analyze Repo", use_container_width=True, type="primary")

if analyze_btn and repo_input:
    client = GitHubClient(token=github_token if github_token else None)
    evaluator = LLMEvaluator(api_key=groq_api_key if groq_api_key else None)
    
    with st.spinner("📥 Ingesting file tree, manifests, tests, and README via GitHub REST API..."):
        try:
            repo_data = client.fetch_full_repo_context(repo_input)
        except Exception as e:
            st.error(f"Error fetching repository: {e}")
            st.stop()
            
    with st.spinner("⚙️ Executing deterministic heuristics and rules engine..."):
        rule_scores = {
            "documentation": RulesEngine.evaluate_documentation(
                repo_data["readme_content"], repo_data["file_paths"]
            ),
            "testing": RulesEngine.evaluate_testing(
                repo_data["test_files"], repo_data["file_paths"]
            ),
            "structure": RulesEngine.evaluate_structure(repo_data["file_paths"]),
            "dependencies": RulesEngine.evaluate_dependencies(repo_data["dependency_files"]),
        }

    with st.spinner("🧠 Performing AI code audit and synthesizing improvement plan..."):
        analysis = evaluator.analyze_repository(repo_data, rule_scores)

    owner = repo_data["owner"]
    repo = repo_data["repo"]
    overall = analysis.get("overall_health", 70)

    st.success(f"Audit completed for **{owner}/{repo}**!")
    st.markdown("---")

    # Overview Metrics Row
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Overall Health", f"{overall}/100")
    m2.metric("⭐ Stars", repo_data["meta"]["stars"])
    m3.metric("🍴 Forks", repo_data["meta"]["forks"])
    m4.metric("📄 Total Files", len(repo_data["file_paths"]))
    m5.metric("⚖️ License", repo_data["meta"]["license"] or "Missing")

    st.markdown("---")

    # Visual Dimension Breakdown (Radar Chart + Progress Bars)
    col_chart, col_scores = st.columns([1, 1])

    categories = ['Code Quality', 'Documentation', 'Testing', 'Structure', 'Dependencies']
    scores_dict = analysis.get("scores", {})
    values = [
        scores_dict.get("code_quality", 70),
        scores_dict.get("documentation", 70),
        scores_dict.get("testing", 50),
        scores_dict.get("structure", 80),
        scores_dict.get("dependencies", 85)
    ]
    categories_plot = categories + [categories[0]]
    values_plot = values + [values[0]]

    with col_chart:
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values_plot,
            theta=categories_plot,
            fill='toself',
            fillcolor='rgba(88, 166, 255, 0.25)',
            line=dict(color='#58a6ff', width=2)
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10)),
            ),
            showlegend=False,
            margin=dict(l=40, r=40, t=30, b=30),
            height=320,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_scores:
        st.subheader("Dimension Scores")
        for cat, val in zip(categories, values):
            st.write(f"**{cat}** — `{val}/100`")
            st.progress(val / 100)

    # Executive Summary & Actionable Recommendations
    st.markdown("---")
    st.subheader("📋 Executive Summary")
    st.info(analysis.get("summary", "Analysis completed successfully."))

    col_str, col_rec = st.columns(2)
    with col_str:
        st.subheader("🌟 Key Strengths")
        for item in analysis.get("strengths", []):
            st.markdown(f"- ✅ {item}")

    with col_rec:
        st.subheader("🛠️ Recommended Action Items")
        for rec in analysis.get("recommendations", []):
            st.markdown(f"- 💡 {rec}")

    st.markdown("---")

    # 1-Click Fixes & Boilerplate Generator
    st.subheader("⚡ 1-Click Fix Generators")
    t1, t2, t3, t4 = st.tabs(["GitHub Actions CI Workflow", "Starter Test File", "MIT License", "README Health Badge"])
    
    with t1:
        st.caption("Add this to `.github/workflows/ci.yml` to set up automated testing:")
        ci_yaml = """name: CI

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
          python-version: '3.10'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          pip install pytest
      - name: Run unit tests
        run: |
          pytest
"""
        st.code(ci_yaml, language="yaml")

    with t2:
        st.caption("Add this to `tests/test_basic.py` to initialize unit tests:")
        test_py = """import pytest

def test_sanity_check():
    \"\"\"Basic sanity assertion test.\"\"\"
    assert 1 + 1 == 2

def test_imports():
    \"\"\"Verify modules load properly.\"\"\"
    try:
        import src
        assert True
    except ImportError:
        pytest.fail("Failed to import source package")
"""
        st.code(test_py, language="python")

    with t3:
        st.caption("Add this file named `LICENSE` in your project root:")
        license_text = f"""MIT License

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
        st.code(license_text, language="text")

    with t4:
        st.caption("Paste this Markdown badge into your `README.md`:")
        badge_color = "brightgreen" if overall >= 80 else ("yellow" if overall >= 60 else "red")
        badge_md = f"[![Project Health](https://img.shields.io/badge/Project_Health-{overall}%2F100-{badge_color})](https://github.com/{owner}/{repo})"
        st.code(badge_md, language="markdown")
        st.markdown(f"**Preview:** {badge_md}")

    # Export Report
    st.markdown("---")
    report_md = f"""# AI Health Audit Report: {owner}/{repo}

**Overall Health Score:** {overall}/100

## Dimension Breakdown
- **Code Quality:** {scores_dict.get('code_quality', 'N/A')}/100
- **Documentation:** {scores_dict.get('documentation', 'N/A')}/100
- **Testing & CI:** {scores_dict.get('testing', 'N/A')}/100
- **Structure:** {scores_dict.get('structure', 'N/A')}/100
- **Dependencies:** {scores_dict.get('dependencies', 'N/A')}/100

## Executive Summary
{analysis.get('summary', '')}

## Key Strengths
{chr(10).join(['- ' + s for s in analysis.get('strengths', [])])}

## Improvement Recommendations
{chr(10).join(['- ' + r for r in analysis.get('recommendations', [])])}
"""
    st.download_button(
        label="📥 Download Full Audit Report (.md)",
        data=report_md,
        file_name=f"{repo}_health_audit.md",
        mime="text/markdown"
    )