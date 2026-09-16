const processCtx = document.getElementById('processChart').getContext('2d');
const scoresCtx = document.getElementById('scoresChart').getContext('2d');
const scenarioSelect = document.getElementById('scenario-select');
const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');
const anomalyCountVal = document.getElementById('anomaly-count-val');
const alertList = document.getElementById('alert-list');
const groundTruthBadge = document.getElementById('ground-truth-badge');

Chart.defaults.color = '#94A3B8';
Chart.defaults.font.family = 'Inter';

// Shared Chart Options
const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    interaction: {
        mode: 'index',
        intersect: false,
    },
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: 'rgba(18, 22, 33, 0.9)',
            titleColor: '#fff',
            bodyColor: '#94A3B8',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
            padding: 12
        }
    },
    scales: {
        x: {
            grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
            ticks: { maxTicksLimit: 10 }
        },
        y: {
            grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false }
        }
    }
};

let processChart = new Chart(processCtx, {
    type: 'line',
    data: { labels: [], datasets: [] },
    options: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            y: { ...commonOptions.scales.y, min: 0, max: 2.5 }
        }
    }
});

let scoresChart = new Chart(scoresCtx, {
    type: 'line',
    data: { labels: [], datasets: [] },
    options: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            y: { ...commonOptions.scales.y, min: 0, max: 1.1 }
        }
    }
});

// Load Scenarios
async function loadScenarios() {
    try {
        const res = await fetch('/api/scenarios');
        const scenarios = await res.json();
        scenarioSelect.innerHTML = '<option value="">Select a scenario...</option>';
        scenarios.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s;
            opt.textContent = s;
            scenarioSelect.appendChild(opt);
        });
        if (scenarios.length > 0) {
            scenarioSelect.value = scenarios[0];
            loadTelemetry(scenarios[0]);
        }
    } catch (e) {
        console.error("Failed to load scenarios", e);
    }
}

// Load Telemetry
async function loadTelemetry(scenarioId) {
    if (!scenarioId) return;
    try {
        const res = await fetch(`/api/telemetry/${scenarioId}`);
        const data = await res.json();
        
        const times = data.simulation_time_s;
        
        // Update Process Chart
        processChart.data = {
            labels: times,
            datasets: [
                {
                    label: 'Tank Level (m)',
                    data: data.tank_level_observed,
                    borderColor: '#00E5FF',
                    backgroundColor: 'rgba(0, 229, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0
                },
                {
                    label: 'Pump State',
                    data: data.pump_state,
                    borderColor: '#00E676',
                    borderWidth: 1,
                    stepped: true,
                    pointRadius: 0
                }
            ]
        };
        processChart.update();

        // Update Scores Chart
        const hasScores = data.S_hybrid && data.S_hybrid.length > 0 && data.S_hybrid[0] !== null;
        
        if (hasScores) {
            scoresChart.data = {
                labels: times,
                datasets: [
                    {
                        label: 'Hybrid Anomaly Score',
                        data: data.S_hybrid,
                        borderColor: '#FF3366',
                        backgroundColor: 'rgba(255, 51, 102, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1,
                        pointRadius: 0
                    },
                    {
                        label: 'Threshold (0.95)',
                        data: Array(times.length).fill(0.95),
                        borderColor: '#94A3B8',
                        borderDash: [5, 5],
                        borderWidth: 1,
                        pointRadius: 0
                    }
                ]
            };
        } else {
            scoresChart.data = { labels: [], datasets: [] };
        }
        scoresChart.update();

        // Update UI Alerts
        let anomalies = 0;
        alertList.innerHTML = '';
        
        const attackType = data.attack_type[0] || 'None';
        if (attackType !== 'None') {
            groundTruthBadge.textContent = `ATTACK: ${attackType}`;
            groundTruthBadge.className = 'badge red';
        } else {
            groundTruthBadge.textContent = 'NORMAL';
            groundTruthBadge.className = 'badge green';
        }

        if (hasScores) {
            for (let i = 0; i < data.predicted_anomaly.length; i++) {
                if (data.predicted_anomaly[i] === 1) {
                    anomalies++;
                    // Add to log if it's a new continuous block or just sample it
                    // To prevent 1000s of alerts, we just add the first one of a block
                    if (i === 0 || data.predicted_anomaly[i-1] === 0) {
                        const li = document.createElement('li');
                        li.className = 'alert-item anomaly';
                        li.innerHTML = `<span class="alert-time">T=${data.simulation_time_s[i]}s</span> Anomaly Detected (Score: ${data.S_hybrid[i].toFixed(2)})`;
                        alertList.prepend(li);
                    }
                }
            }
        }

        anomalyCountVal.textContent = anomalies;
        
        if (anomalies > 0) {
            statusIndicator.className = 'status-indicator status-danger';
            statusText.textContent = 'SYSTEM COMPROMISED';
        } else {
            statusIndicator.className = 'status-indicator status-ok';
            statusText.textContent = 'NORMAL OPERATION';
            alertList.innerHTML = '<li class="alert-item empty">No events recorded.</li>';
        }

    } catch (e) {
        console.error("Failed to load telemetry", e);
    }
}

scenarioSelect.addEventListener('change', (e) => loadTelemetry(e.target.value));

loadScenarios();
