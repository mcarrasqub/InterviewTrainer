// progreso.js - renders charts for Progreso page
// Expects window.PROGRESO_DATA_URL to be set by the template, and Chart.js loaded.
(function(){
    if (!window.PROGRESO_DATA_URL) {
        console.error('PROGRESO_DATA_URL not set. The template must expose the endpoint with a small inline script.');
        return;
    }

    // Cargar datos de progreso vía AJAX y renderizar gráficos
    fetch(window.PROGRESO_DATA_URL)
        .then(res => res.json())
        .then(data => {
            // Estadísticas principales
            const avgEl = document.getElementById('averageScore');
            const totalEl = document.getElementById('totalSessions');
            const compEl = document.getElementById('completedSessions');
            const avgTimeEl = document.getElementById('averageTimeScore');
            // format average_time_score to one decimal when present
            if (avgEl) avgEl.textContent = data.average_score;
            if (totalEl) totalEl.textContent = (data.sessions_labels || []).length;
            if (compEl) compEl.textContent = (data.sessions_labels || []).filter((_,i) => (data.sessions_scores[i] || 0) > 0).length;
            if (avgTimeEl) {
                if (typeof data.average_time_score !== 'undefined' && data.average_time_score !== null) {
                    // ensure numeric and show one decimal
                    const n = Number(data.average_time_score);
                    avgTimeEl.textContent = Number.isFinite(n) ? n.toFixed(1) : '-';
                } else {
                    avgTimeEl.textContent = '-';
                }
            }

            // Sessions chart (bar)
            const sessionsChartEl = document.getElementById('sessionsChart');
            const sessionsPlaceholder = document.getElementById('sessionsPlaceholder');
            if (!sessionsChartEl) {
                console.warn('sessionsChart element not found');
            }
            if (!data.sessions_scores || data.sessions_scores.length === 0 || data.sessions_scores.every(v => v === 0 || v === null)) {
                if (sessionsChartEl) sessionsChartEl.style.display = 'none';
                if (sessionsPlaceholder) sessionsPlaceholder.style.display = 'flex';
            } else {
                if (sessionsChartEl) {
                    sessionsChartEl.style.display = 'block';
                    if (sessionsPlaceholder) sessionsPlaceholder.style.display = 'none';
                    new Chart(sessionsChartEl.getContext('2d'), { type: 'bar', data: { labels: data.sessions_labels, datasets: [{ label: 'Puntaje', data: data.sessions_scores.map(v => v === null ? 0 : v), backgroundColor: 'rgba(124,58,237,0.25)', borderColor: 'rgba(79,70,229,1)', borderWidth: 2, borderRadius: 6 }] }, options: { responsive: true, scales: { y: { beginAtZero: true, max: 10 } }, plugins: { legend: { display: false } } } });
                }
            }

            // Evolution line
            const scoreEvolutionCanvas = document.getElementById('scoreEvolutionChart');
            if (scoreEvolutionCanvas) {
                const scoreEvolutionCtx = scoreEvolutionCanvas.getContext('2d');
                const labels = data.sessions_labels || [];
                const evolutionData = (data.sessions_scores || []).map(v => v === null ? null : v);
                const timeData = (data.sessions_time_scores || []).map(v => v === null ? null : v);
                const datasets = [{ label: 'Evolución de puntaje', data: evolutionData, borderColor: 'rgba(79,70,229,0.95)', backgroundColor: 'rgba(79,70,229,0.12)', tension: 0.25, fill: true }];
                // Only add the time management series if there's at least one numeric value
                const hasTimeValues = Array.isArray(timeData) && timeData.some(v => v !== null && !Number.isNaN(v));
                if (hasTimeValues) {
                    datasets.push({ label: 'Gestión del tiempo', data: timeData, borderColor: 'rgba(16,185,129,0.95)', backgroundColor: 'rgba(16,185,129,0.12)', tension: 0.25, fill: false, borderDash: [4,4], spanGaps: true, pointRadius: 4 });
                }
                new Chart(scoreEvolutionCtx, { type: 'line', data: { labels, datasets }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 10 } }, plugins: { legend: { display: true } } } });
            }

            // Sparklines + modal
            const skillsSeries = data.skills_series || {};
            const skillsSeriesCumulative = data.skills_series_cumulative || {};
            let skillNames = Object.keys(skillsSeries || {});
            const skillsGrid = document.getElementById('skillsGrid');
            const skillsPlaceholder = document.getElementById('skillsPlaceholder');
            const seriesToggle = document.getElementById('seriesToggle');
            const skillsSort = document.getElementById('skillsSort');
            let useCumulative = false;
            let modalChart = null;

            function getLastValid(series) {
                if (!series || !series.length) return null;
                for (let i = series.length - 1; i >= 0; i--) {
                    const v = series[i];
                    if (v !== null && v !== undefined && !Number.isNaN(v)) return v;
                }
                return null;
            }

            function sortSkillNames() {
                const mode = (skillsSort && skillsSort.value) || 'score_desc';
                const src = useCumulative ? skillsSeriesCumulative : skillsSeries;
                const keys = Object.keys(src || {});
                // build array with last value and original name for stable sort
                const items = keys.map(k => ({ name: k, last: getLastValid(src[k]) }));

                if (mode === 'alpha') {
                    items.sort((a,b) => a.name.localeCompare(b.name));
                } else {
                    // put nulls at the end, otherwise sort by last value
                    items.sort((a,b) => {
                        const aHas = a.last !== null;
                        const bHas = b.last !== null;
                        if (aHas && !bHas) return -1;
                        if (!aHas && bHas) return 1;
                        if (!aHas && !bHas) return a.name.localeCompare(b.name);
                        // both have numbers
                        return mode === 'score_asc' ? (a.last - b.last) : (b.last - a.last);
                    });
                }

                skillNames = items.map(i => i.name);
            }

            const modalEl = document.getElementById('skillModal');
            function openSkillModal(name, rawSeries, color, lastNum, mean, delta) {
                const labelEl = document.getElementById('skillModalLabel');
                const lastEl = document.getElementById('skillModalLast');
                const meanEl = document.getElementById('skillModalMean');
                const deltaEl = document.getElementById('skillModalDelta');
                if (labelEl) labelEl.textContent = name;
                if (lastEl) lastEl.textContent = (typeof lastNum === 'number') ? lastNum.toFixed(1) : '-';
                if (meanEl) meanEl.textContent = (typeof mean === 'number') ? mean.toFixed(2) : '-';
                if (deltaEl) deltaEl.textContent = (delta === null) ? '-' : ((delta >= 0 ? '+' : '') + delta.toFixed(2));
                if (modalChart) { try { modalChart.destroy(); } catch(e){} modalChart = null; }
                const modalCanvas = document.getElementById('skillModalChart');
                if (!modalCanvas) return;
                const ctx = modalCanvas.getContext('2d');
                modalChart = new Chart(ctx, { type: 'line', data: { labels: (data.sessions_labels || rawSeries.map((_,i)=>i+1)), datasets: [{ label: name, data: rawSeries.map(v => v === null ? NaN : v), borderColor: color, backgroundColor: color + '22', fill: true, pointRadius: 4 }] }, options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, suggestedMax: 10 } } } });
                // show bootstrap modal
                if (typeof bootstrap !== 'undefined' && modalEl) {
                    const bsModal = new bootstrap.Modal(modalEl);
                    bsModal.show();
                    // destroy modalChart when modal is hidden to avoid leaks
                    modalEl.addEventListener('hidden.bs.modal', () => {
                        if (modalChart) { try { modalChart.destroy(); } catch(e){} modalChart = null; }
                    }, { once: true });
                }
            }

            function renderSparklines() {
                if (!skillsGrid) return;
                skillsGrid.innerHTML = '';
                const src = useCumulative ? skillsSeriesCumulative : skillsSeries;
                if (!skillNames || skillNames.length === 0) { skillsGrid.style.display = 'none'; if (skillsPlaceholder) skillsPlaceholder.style.display = 'flex'; return; }
                skillsGrid.style.display = 'grid'; if (skillsPlaceholder) skillsPlaceholder.style.display = 'none';
                const palette = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2'];
                // allow sorting before rendering
                sortSkillNames();
                skillNames.forEach((name, idx) => {
                    const raw = (src[name] || []);
                    const series = raw.map(v => v === null ? NaN : v);
                    const validSeries = series.filter(v => !isNaN(v));
                    const lastNum = validSeries.length ? validSeries[validSeries.length - 1] : null;
                    const prevNum = validSeries.length > 1 ? validSeries[validSeries.length - 2] : null;
                    const delta = (typeof lastNum === 'number' && typeof prevNum === 'number') ? (lastNum - prevNum) : null;
                    const mean = validSeries.length ? (validSeries.reduce((a,b)=>a+b,0)/validSeries.length) : null;
                    const card = document.createElement('div'); card.className = 'sparkline-card';
                    let borderColor = 'transparent'; if (typeof lastNum === 'number') { if (lastNum >= 8) borderColor = '#16a34a'; else if (lastNum >= 6) borderColor = '#f59e0b'; else borderColor = '#ef4444'; }
                    card.style.borderLeftColor = borderColor;
                    const titleRow = document.createElement('div'); titleRow.className = 'sparkline-top';
                    const title = document.createElement('div'); title.textContent = name;
                    const latestVal = document.createElement('div'); latestVal.className = 'sparkline-value'; latestVal.textContent = (typeof lastNum === 'number') ? lastNum.toFixed(1) : '-';
                    const deltaBadge = document.createElement('span'); deltaBadge.className = 'delta-badge ' + (delta === null ? 'delta-neutral' : (delta >= 0 ? 'delta-pos' : 'delta-neg'));
                    deltaBadge.textContent = (delta === null) ? '-' : ((delta >= 0 ? '+' : '') + delta.toFixed(1));
                    const meta = document.createElement('div'); meta.className = 'sparkline-meta'; meta.appendChild(latestVal); meta.appendChild(deltaBadge);
                    titleRow.appendChild(title); titleRow.appendChild(meta);
                    const statsRow = document.createElement('div'); statsRow.style.display = 'flex'; statsRow.style.justifyContent = 'space-between'; statsRow.style.fontSize = '0.85rem'; statsRow.style.color = '#6b7280'; const meanEl = document.createElement('div'); meanEl.textContent = 'Prom: ' + ((typeof mean === 'number') ? mean.toFixed(1) : '-'); const deltaEl = document.createElement('div'); deltaEl.textContent = (delta === null) ? '' : ((delta >= 0 ? '+' : '') + delta.toFixed(1)); statsRow.appendChild(meanEl); statsRow.appendChild(deltaEl);
                    const canvas = document.createElement('canvas'); canvas.className = 'sparkline-canvas'; canvas.id = 'sparkline_' + idx; canvas.width = 320; canvas.height = 84;
                    card.appendChild(titleRow); card.appendChild(statsRow); card.appendChild(canvas); skillsGrid.appendChild(card);
                    new Chart(canvas.getContext('2d'), {
                        type: 'line',
                        data: {
                            labels: data.sessions_labels || series.map((_,i)=>i+1),
                            datasets: [{
                                label: name,
                                data: series,
                                borderColor: palette[idx % palette.length],
                                backgroundColor: palette[idx % palette.length] + '22',
                                borderWidth: 2,
                                pointRadius: 3,
                                pointHoverRadius: 5,
                                tension: 0.32,
                                fill: true
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false },
                                tooltip: { enabled: true, callbacks: { label: function(ctx){ return (ctx.formattedValue || '') + '/10'; } } }
                            },
                            scales: {
                                x: { display: false },
                                y: { display: true, suggestedMin: 0, suggestedMax: 10, ticks: { stepSize: 2, color: '#6b7280', font: { size: 11 } }, grid: { color: 'rgba(226,232,240,0.6)' } }
                            }
                        }
                    });
                    card.style.cursor = 'pointer'; card.addEventListener('click', () => { openSkillModal(name, raw, palette[idx % palette.length], lastNum, mean, delta); });
                });
            }

            renderSparklines();
            if (seriesToggle) seriesToggle.addEventListener('click', () => { useCumulative = !useCumulative; seriesToggle.textContent = useCumulative ? 'Ver: Acumulado' : 'Ver: Histórico'; renderSparklines(); });
            if (skillsSort) skillsSort.addEventListener('change', () => { renderSparklines(); });
        })
        .catch(err => { console.error('Error cargando progreso:', err); });
})();
