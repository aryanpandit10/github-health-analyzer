let currentData = null;
let radarChartInstance = null;
let historyChartInstance = null;

function switchMode(mode) {
  if (mode === 'single') {
    document.getElementById('singleInputBox').classList.remove('hidden');
    document.getElementById('compareInputBox').classList.add('hidden');
    document.getElementById('singleTabBtn').className = 'text-xs bg-accent text-white px-3 py-1.5 rounded-md font-semibold transition';
    document.getElementById('compareTabBtn').className = 'text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-md border border-darkBorder transition';
    document.getElementById('compareResults').classList.add('hidden');
  } else {
    document.getElementById('singleInputBox').classList.add('hidden');
    document.getElementById('compareInputBox').classList.remove('hidden');
    document.getElementById('compareTabBtn').className = 'text-xs bg-accent text-white px-3 py-1.5 rounded-md font-semibold transition';
    document.getElementById('singleTabBtn').className = 'text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-md border border-darkBorder transition';
    document.getElementById('results').classList.add('hidden');
  }
}

async function runSingleAudit(event) {
  if (event) event.preventDefault();

  const repoUrl = document.getElementById('repoUrl').value.trim();
  const groqKey = document.getElementById('groqKey').value.trim() || null;
  const ghToken = document.getElementById('ghToken').value.trim() || null;

  if (!repoUrl) return alert('Please enter a GitHub repository URL.');

  showLoading(true);
  try {
    const res = await fetch('http://127.0.0.1:8000/api/v1/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_url: repoUrl, groq_api_key: groqKey, github_token: ghToken })
    });
    
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Analysis request failed');
    
    currentData = data;
    renderSingle(data);
  } catch (e) {
    console.error('Audit Error:', e);
    showError(e.message);
  } finally {
    showLoading(false);
  }
}

async function runComparison(event) {
  if (event) event.preventDefault();

  const repoUrlA = document.getElementById('repoUrlA').value.trim();
  const repoUrlB = document.getElementById('repoUrlB').value.trim();
  const groqKey = document.getElementById('groqKey').value.trim() || null;
  const ghToken = document.getElementById('ghToken').value.trim() || null;

  if (!repoUrlA || !repoUrlB) return alert('Please enter both repository URLs.');

  showLoading(true);
  try {
    const res = await fetch('http://127.0.0.1:8000/api/v1/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_url_a: repoUrlA, repo_url_b: repoUrlB, groq_api_key: groqKey, github_token: ghToken })
    });
    
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Comparison Failed');
    
    renderComparison(data);
  } catch (e) {
    console.error('Comparison Error:', e);
    showError(e.message);
  } finally {
    showLoading(false);
  }
}

function renderSingle(data) {
  document.getElementById('scoreVal').innerText = `${data.overall_health || 0}/100`;
  
  const secScore = data.security?.score ?? 0;
  const secEl = document.getElementById('secVal');
  secEl.innerText = `${secScore}/100`;
  secEl.className = secScore >= 80 ? 'text-2xl font-bold text-emerald-400 mt-1' : 'text-2xl font-bold text-amber-400 mt-1';

  document.getElementById('starsVal').innerText = data.meta?.stars ?? 0;
  document.getElementById('forksVal').innerText = data.meta?.forks ?? 0;
  document.getElementById('filesVal').innerText = data.discovered_files?.total_files ?? 0;
  document.getElementById('licenseVal').innerText = data.meta?.license || 'Missing';
  document.getElementById('summaryText').innerText = data.summary || 'Audit complete.';

  // 1. Before vs After Delta & Timeline
  const deltaEl = document.getElementById('deltaBadge');
  const delta = data.delta ?? 0;
  if (delta > 0) {
    deltaEl.innerText = `+${delta} points since your last audit`;
    deltaEl.className = 'text-xs font-semibold px-3 py-1 rounded-full border border-emerald-500/40 bg-emerald-950/40 text-emerald-400';
  } else if (delta < 0) {
    deltaEl.innerText = `${delta} points since your last audit`;
    deltaEl.className = 'text-xs font-semibold px-3 py-1 rounded-full border border-red-500/40 bg-red-950/40 text-red-400';
  } else {
    deltaEl.innerText = `0 points (First or unchanged audit)`;
    deltaEl.className = 'text-xs font-semibold px-3 py-1 rounded-full border border-slate-700 bg-slate-800 text-slate-300';
  }

  // History Terminal logs
  const historyList = data.history || [];
  const historyTerminal = document.getElementById('historyTerminal');
  historyTerminal.innerHTML = historyList.length > 0 
    ? historyList.map((h, i) => `
        <div class="flex justify-between">
          <span class="text-slate-400">${h.date} (#${i + 1})</span>
          <span class="text-accent font-bold">Health: ${h.score}/100</span>
        </div>
      `).join('')
    : '<div class="text-slate-500">First audit entry recorded.</div>';

  // History Chart
  const histCtx = document.getElementById('historyChart').getContext('2d');
  if (historyChartInstance) historyChartInstance.destroy();
  historyChartInstance = new Chart(histCtx, {
    type: 'line',
    data: {
      labels: historyList.map((h, i) => `${h.date} (#${i + 1})`),
      datasets: [{
        label: 'Project Health',
        data: historyList.map(h => h.score),
        borderColor: '#58a6ff',
        backgroundColor: 'rgba(88, 166, 255, 0.15)',
        fill: true,
        tension: 0.3,
        pointBackgroundColor: '#58a6ff',
        pointRadius: 5,
        pointHoverRadius: 7
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { min: 0, max: 100, grid: { color: '#30363d' }, ticks: { color: '#8b949e' } },
        x: { grid: { color: '#30363d' }, ticks: { color: '#8b949e' } }
      },
      plugins: { legend: { display: false } }
    }
  });

  // 2. Score Transparency ("Why the Score Exists")
  const scores = data.scores || {};
  const dimsList = [
    { key: 'code_quality', name: 'Code Quality', score: scores.code_quality ?? 70 },
    { key: 'security', name: 'Security & Secret Sanitization', score: scores.security ?? 80 },
    { key: 'documentation', name: 'Documentation', score: scores.documentation ?? 70 },
    { key: 'testing', name: 'Testing & CI Suite', score: scores.testing ?? 50 },
    { key: 'structure', name: 'Repository Structure', score: scores.structure ?? 80 },
    { key: 'dependencies', name: 'Dependency Governance', score: scores.dependencies ?? 85 },
  ];

  const whyContainer = document.getElementById('dimensionWhyList');
  whyContainer.innerHTML = dimsList.map(dim => {
    const exp = data.score_explanations?.[dim.key] || { strengths: [], penalties: [] };
    const scoreColor = dim.score >= 80 ? 'text-emerald-400' : (dim.score >= 60 ? 'text-amber-400' : 'text-red-400');
    
    return `
      <details class="group bg-darkBg border border-darkBorder rounded-lg p-3 text-xs transition">
        <summary class="flex justify-between items-center cursor-pointer font-medium text-slate-200 hover:text-accent">
          <span class="text-sm font-semibold">${dim.name}</span>
          <div class="flex items-center gap-2">
            <span class="font-bold ${scoreColor}">${dim.score}/100</span>
            <span class="text-slate-500 group-open:rotate-180 transition-transform">▼</span>
          </div>
        </summary>
        <div class="mt-3 pt-3 border-t border-darkBorder space-y-2">
          <p class="font-semibold text-slate-400">Why this score?</p>
          ${(exp.strengths || []).map(s => `<div class="text-emerald-400 flex items-start gap-1.5"><span>✓</span> <span>${s}</span></div>`).join('')}
          ${(exp.penalties || []).map(p => `<div class="text-red-400 flex items-start gap-1.5"><span>⚠</span> <span>${p}</span></div>`).join('')}
          ${(!exp.strengths?.length && !exp.penalties?.length) ? '<p class="text-slate-500">Baseline evaluation criteria applied.</p>' : ''}
        </div>
      </details>
    `;
  }).join('');

  // 3. AI Improvement Roadmap
  const cats = data.roadmap?.categories || {};
  const renderTier = (arr, fallback) => (arr && arr.length > 0) ? arr.map(i => `<li>${i}</li>`).join('') : `<li class="text-slate-500 italic">${fallback}</li>`;
  
  document.getElementById('roadmapFixFirst').innerHTML = renderTier(cats.fix_first, 'No critical vulnerabilities');
  document.getElementById('roadmapFixNext').innerHTML = renderTier(cats.fix_next, 'No immediate blockers');
  document.getElementById('roadmapImproveLater').innerHTML = renderTier(cats.improve_later, 'None listed');
  document.getElementById('roadmapNiceToHave').innerHTML = renderTier(cats.nice_to_have, 'None listed');

  const seqPath = data.roadmap?.sequential_path || [];
  document.getElementById('sequentialPathBlock').innerHTML = seqPath.length > 0
    ? seqPath.map(p => `<div>${p}</div>`).join('')
    : '<div>1 → No immediate tasks pending.</div>';

  // Security risks
  const secRisks = data.security?.risks || [];
  const secContent = document.getElementById('securityContent');
  if (secRisks.length === 0) {
    secContent.innerHTML = `<p class="text-emerald-400 font-medium">✓ No exposed keys, sensitive files, or critical risk patterns detected.</p>`;
  } else {
    secContent.innerHTML = `<ul class="space-y-1 text-red-400 font-medium">${secRisks.map(r => `<li>⚠️ ${r}</li>`).join('')}</ul>`;
  }

  // Strengths & Recs
  document.getElementById('strengthsList').innerHTML = (data.strengths || []).map(s => `<li>✓ ${s}</li>`).join('') || '<li>Standard criteria met</li>';
  document.getElementById('recsList').innerHTML = (data.recommendations || []).map(r => `<li>! ${r}</li>`).join('') || '<li>No immediate actions required</li>';

  // Progress bars
  document.getElementById('progressBars').innerHTML = dimsList.map(d => `
    <div>
      <div class="flex justify-between mb-1"><span class="font-medium text-slate-300">${d.name}</span><span class="text-accent font-semibold">${d.score}/100</span></div>
      <div class="w-full bg-darkBg rounded-full h-2 border border-darkBorder"><div class="bg-accent h-2 rounded-full" style="width: ${d.score}%"></div></div>
    </div>
  `).join('');

  // Radar Chart
  const radarCtx = document.getElementById('radarChart').getContext('2d');
  if (radarChartInstance) radarChartInstance.destroy();
  radarChartInstance = new Chart(radarCtx, {
    type: 'radar',
    data: {
      labels: dimsList.map(d => d.name),
      datasets: [{
        data: dimsList.map(d => d.score),
        backgroundColor: 'rgba(88, 166, 255, 0.2)',
        borderColor: '#58a6ff',
        pointBackgroundColor: '#58a6ff',
      }]
    },
    options: {
      scales: { r: { min: 0, max: 100, ticks: { display: false }, grid: { color: '#30363d' }, angleLines: { color: '#30363d' }, pointLabels: { color: '#8b949e' } } },
      plugins: { legend: { display: false } },
      maintainAspectRatio: false
    }
  });

  switchFixTab('ci');
  document.getElementById('results').classList.remove('hidden');
}

function renderComparison(data) {
  document.getElementById('winnerTag').innerText = `🏆 ${data.winner || 'Tie'}`;
  const renderCard = (r) => `
    <div class="bg-darkCard border border-darkBorder p-6 rounded-xl space-y-4">
      <div class="flex justify-between items-center border-b border-darkBorder pb-3">
        <h3 class="font-bold text-lg text-white">${r.owner}/${r.repo}</h3>
        <span class="text-xl font-extrabold text-accent">${r.overall_health}/100</span>
      </div>
      <p class="text-xs text-slate-400">${r.summary || ''}</p>
      <div class="space-y-2 text-xs">
        <div class="flex justify-between"><span>Code Quality</span><span class="font-semibold">${r.scores?.code_quality ?? 0}/100</span></div>
        <div class="flex justify-between"><span>Security</span><span class="font-semibold">${r.security?.score ?? 0}/100</span></div>
        <div class="flex justify-between"><span>Documentation</span><span class="font-semibold">${r.scores?.documentation ?? 0}/100</span></div>
        <div class="flex justify-between"><span>Testing & CI</span><span class="font-semibold">${r.scores?.testing ?? 0}/100</span></div>
        <div class="flex justify-between"><span>Structure</span><span class="font-semibold">${r.scores?.structure ?? 0}/100</span></div>
        <div class="flex justify-between"><span>Dependencies</span><span class="font-semibold">${r.scores?.dependencies ?? 0}/100</span></div>
      </div>
    </div>
  `;
  document.getElementById('compareCards').innerHTML = renderCard(data.repository_a) + renderCard(data.repository_b);
  document.getElementById('compareResults').classList.remove('hidden');
}

function switchFixTab(tab) {
  if (!currentData || !currentData.starter_fixes) return;
  ['ci', 'test', 'license', 'security', 'badge'].forEach(t => {
    const el = document.getElementById(`tab-${t}`);
    if (t === tab) {
      el.className = 'text-xs bg-slate-800 text-white px-3 py-1.5 rounded font-semibold whitespace-nowrap';
    } else {
      el.className = 'text-xs bg-darkBg text-slate-400 px-3 py-1.5 rounded font-semibold whitespace-nowrap';
    }
  });

  const block = document.getElementById('fixCodeBlock');
  if (tab === 'ci') block.innerText = currentData.starter_fixes.ci_workflow || '';
  if (tab === 'test') block.innerText = currentData.starter_fixes.test_starter || '';
  if (tab === 'license') block.innerText = currentData.starter_fixes.license || '';
  if (tab === 'security') block.innerText = currentData.starter_fixes.security_policy || '';
  if (tab === 'badge') block.innerText = currentData.badge_markdown || '';
}

function downloadReport() {
  if (!currentData) return;
  const d = currentData;
  const seq = (d.roadmap && d.roadmap.sequential_path) ? d.roadmap.sequential_path.join('\n') : '';
  const md = `# AI GitHub Project Health Audit: ${d.owner}/${d.repo}\n\n**Overall Health Score:** ${d.overall_health}/100\n**Security Score:** ${d.security?.score}/100\n**Audit Progress (Delta):** ${d.delta > 0 ? '+' : ''}${d.delta} pts\n\n## Scores\n- Code Quality: ${d.scores?.code_quality}/100\n- Security: ${d.scores?.security}/100\n- Documentation: ${d.scores?.documentation}/100\n- Testing: ${d.scores?.testing}/100\n- Structure: ${d.scores?.structure}/100\n- Dependencies: ${d.scores?.dependencies}/100\n\n## AI Improvement Roadmap\n${seq}\n\n## Executive Summary\n${d.summary}\n\n## Key Strengths\n${(d.strengths || []).map(s => '- ' + s).join('\n')}\n\n## Recommendations\n${(d.recommendations || []).map(r => '- ' + r).join('\n')}\n`;
  const blob = new Blob([md], { type: 'text/markdown' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${d.repo}_health_audit.md`;
  a.click();
}

function showLoading(show) {
  document.getElementById('loader').classList.toggle('hidden', !show);
  if (show) {
    document.getElementById('results').classList.add('hidden');
    document.getElementById('compareResults').classList.add('hidden');
    document.getElementById('errorBox').classList.add('hidden');
  }
}

function showError(msg) {
  const err = document.getElementById('errorBox');
  err.innerText = `Error: ${msg}`;
  err.classList.remove('hidden');
}