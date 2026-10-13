let chart;
let config = {};
let lastSseTime = Date.now();
let demoMode = false;
let currentMode = "monitor";

async function fetchMode() {
    try {
        const res = await fetch('/api/mode');
        if (res.ok) {
            const data = await res.json();
            updateModeUI(data.mode);
        }
    } catch(e) {}
}

async function toggleMode() {
    const newMode = currentMode === "monitor" ? "prevention" : "monitor";
    try {
        const res = await fetch('/api/mode', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({mode: newMode})
        });
        if (res.ok) {
            const data = await res.json();
            updateModeUI(data.mode);
        }
    } catch(e) {}
}

function updateModeUI(mode) {
    if (!mode) return;
    currentMode = mode.toLowerCase();
    const btn = document.getElementById('btn-mode-toggle');
    if (btn) {
        btn.textContent = currentMode.toUpperCase();
        btn.className = 'btn-mode ' + currentMode;
    }
}

// Chart.js init
function initChart() {
    const ctx = document.getElementById('levelChart').getContext('2d');
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array(300).fill(''),
            datasets: [
                {
                    label: 'Observed Level',
                    data: Array(300).fill(null),
                    borderColor: '#4fc3f7',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0
                },
                {
                    label: 'Twin Level',
                    data: Array(300).fill(null),
                    borderColor: '#ff9800',
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    tension: 0
                }
            ]
        },
        options: {
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { display: false },
                y: { min: 0, max: 2.5 }
            },
            plugins: {
                annotation: {
                    annotations: {} // for safe bands etc later if imported annotation plugin
                }
            }
        }
    });
}

function updateChart(verdicts) {
    if(!chart) return;
    verdicts.forEach(v => {
        chart.data.datasets[0].data.shift();
        chart.data.datasets[0].data.push(v.level_obs || null);
        chart.data.datasets[1].data.shift();
        chart.data.datasets[1].data.push(v.level_twin || null);
    });
    chart.update();
}

function updateProcessView(v) {
    if (v.level_obs !== undefined) {
        const levelPct = Math.min(100, Math.max(0, (v.level_obs / 2.5) * 100)); // assuming 2.5 is max height on svg
        const height = levelPct;
        const y = 120 - height;
        const rect = document.getElementById('tank-level');
        rect.setAttribute('height', height);
        rect.setAttribute('y', y);
    }
    if (v.commands) {
        const pump = document.getElementById('pump-indicator');
        pump.setAttribute('class', v.commands.pump_cmd ? 'pump-on' : 'pump-off');
        const valveTxt = document.getElementById('valve-text');
        valveTxt.textContent = v.commands.valve_cmd + '%';
    }
}

function updateEngines(v) {
    ['physics', 'lstm', 'policy', 'availability'].forEach(eng => {
        const score = v.scores ? v.scores[eng] : 0;
        const fill = document.querySelector(`#bar-${eng} .bar-fill`);
        fill.style.width = (score * 100) + '%';
        fill.className = score > 0.95 ? 'bar-fill high' : 'bar-fill';
    });
    if(v.hybrid !== undefined) {
        const fill = document.querySelector(`#bar-hybrid .bar-fill`);
        fill.style.width = (v.hybrid * 100) + '%';
        fill.className = v.hybrid > 0.95 ? 'bar-fill high' : 'bar-fill';
    }
}

function updateState(v) {
    const banner = document.getElementById('status-banner');
    const stateSpan = document.getElementById('banner-state');
    banner.className = 'banner ' + v.alert_state;
    stateSpan.textContent = v.alert_state;
    
    if (v.alert_state === 'CRITICAL' && v.attack_type) {
        document.getElementById('banner-details').textContent = `Likely: ${v.attack_type}`;
    } else {
        document.getElementById('banner-details').textContent = '';
    }
}

// Fetch initial data
async function fetchConfig() {
    const res = await fetch('/api/config');
    config = await res.json();
    demoMode = config.demo_mode;
    if(demoMode) {
        document.getElementById('demo-attack-panel').style.display = 'block';
    }
}

async function fetchState() {
    const res = await fetch('/api/state');
    const state = await res.json();
    updateState({alert_state: state.alert_state});
    
    const calibBadge = document.getElementById('calibrating-badge');
    const lstmCalib = document.getElementById('lstm-calib');
    if (state.calibrating) {
        calibBadge.style.display = 'block';
        document.getElementById('calib-ticks').textContent = state.recalibrating_ticks_left;
        lstmCalib.style.display = 'inline';
    } else {
        calibBadge.style.display = 'none';
        lstmCalib.style.display = 'none';
    }
}

async function fetchHistory() {
    const res = await fetch('/api/history?n=300');
    const data = await res.json();
    if(data.history && data.history.length > 0) {
        // pad if less than 300
        const padLen = 300 - data.history.length;
        for(let i=0; i<padLen; i++) {
            chart.data.datasets[0].data.shift();
            chart.data.datasets[0].data.push(null);
            chart.data.datasets[1].data.shift();
            chart.data.datasets[1].data.push(null);
        }
        updateChart(data.history);
        const last = data.history[data.history.length-1];
        updateProcessView(last);
        updateEngines(last);
    }
}

async function fetchMetrics() {
    try {
        const res = await fetch('/api/metrics');
        const m = await res.json();
        document.getElementById('m-detected').textContent = m.detected || 0;
        document.getElementById('m-missed').textContent = m.missed || 0;
        document.getElementById('m-spurious').textContent = m.spurious || 0;
        document.getElementById('m-lingering').textContent = m.lingering || 0;
        document.getElementById('m-delay').textContent = (m.mean_detection_delay_s || 0).toFixed(1) + 's';
    } catch(e) {}
}

function startSSE() {
    const es = new EventSource('/stream');
    es.onmessage = (e) => {
        lastSseTime = Date.now();
        document.getElementById('link-lost').style.display = 'none';
        const v = JSON.parse(e.data);
        
        updateChart([v]);
        updateProcessView(v);
        updateEngines(v);
        updateState(v);
        
        // Calibrating badge
        const calibBadge = document.getElementById('calibrating-badge');
        const lstmCalib = document.getElementById('lstm-calib');
        if (v.calibrating) {
            calibBadge.style.display = 'block';
            document.getElementById('calib-ticks').textContent = "Recalibrating";
            lstmCalib.style.display = 'inline';
        } else {
            calibBadge.style.display = 'none';
            lstmCalib.style.display = 'none';
        }

        // Mode and Prevention Badges
        if (v.mode) {
            updateModeUI(v.mode);
        }

        const srcBadge = document.getElementById('control-source-badge');
        const srcName = document.getElementById('source-name');
        if (srcBadge && srcName) {
            if (v.twin_takeover_active) {
                srcName.textContent = "Twin Takeover";
                srcBadge.className = "badge badge-source twin";
            } else if (v.action_taken === "external_hold") {
                srcName.textContent = "External Hold";
                srcBadge.className = "badge badge-source hold";
            } else {
                srcName.textContent = "Sensor";
                srcBadge.className = "badge badge-source";
            }
        }

        const tamperBadge = document.getElementById('tamper-badge');
        if (tamperBadge) {
            tamperBadge.style.display = v.wire_tamper ? 'inline-block' : 'none';
        }
        
        // Show ack dialog if CRITICAL
        if (v.alert_state === 'CRITICAL' && document.getElementById('ack-dialog').style.display === 'none') {
            document.getElementById('ack-dialog').style.display = 'flex';
            document.getElementById('ack-details').textContent = `Detected attack: ${v.attack_type}`;
        }
    };
    es.onerror = () => {
        es.close();
        document.getElementById('link-lost').style.display = 'flex';
        setTimeout(startSSE, 2000);
    };
}

// Controls
document.getElementById('btn-pause').onclick = () => fetch('/api/control/pause', {method: 'POST'});
document.getElementById('btn-resume').onclick = () => fetch('/api/control/resume', {method: 'POST'});
document.getElementById('btn-speed-1').onclick = () => fetch('/api/control/speed', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({speed: 1.0})});
document.getElementById('btn-speed-5').onclick = () => fetch('/api/control/speed', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({speed: 5.0})});
document.getElementById('btn-reset').onclick = () => {
    if(confirm('Are you sure you want to reset the system?')) {
        fetch('/api/control/reset', {method: 'POST'}).then(() => window.location.reload());
    }
};

document.getElementById('btn-ack').onclick = () => {
    fetch('/api/ack', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({recalibrate: false})})
        .then(() => document.getElementById('ack-dialog').style.display = 'none');
};
document.getElementById('btn-ack-recal').onclick = () => {
    fetch('/api/ack', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({recalibrate: true})})
        .then(async res => {
            if(!res.ok) {
                const data = await res.json();
                document.getElementById('ack-error').textContent = data.reason || 'Failed to recalibrate';
            } else {
                document.getElementById('ack-dialog').style.display = 'none';
                document.getElementById('ack-error').textContent = '';
            }
        });
};
document.getElementById('btn-ack-cancel').onclick = () => document.getElementById('ack-dialog').style.display = 'none';

document.getElementById('btn-mode-toggle').onclick = toggleMode;

document.getElementById('btn-attack-start').onclick = () => {
    const type = document.getElementById('attack-type').value;
    const body = { type: type, duration: 60 };
    if (type === 'FDI') body.magnitude = 0.2;
    if (type === 'Auth misuse') {
        body.target_command = 1; 
        body.target_valve = 100.0;
    }
    if (type === 'Wire tamper') {
        body.target_command = 1;
        body.target_valve = 50.0;
    }
    fetch('/demo/attack/start', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    document.getElementById('demo-status').textContent = 'Attack Active: ' + type;
};
document.getElementById('btn-attack-stop').onclick = () => {
    fetch('/demo/attack/stop', {method: 'POST'});
    document.getElementById('demo-status').textContent = 'Idle';
};

// Periodic checks
setInterval(() => {
    if(Date.now() - lastSseTime > 4000) {
        document.getElementById('link-lost').style.display = 'flex';
    }
}, 1000);
setInterval(fetchMetrics, 2000);
setInterval(fetchState, 2000);

initChart();
fetchMode();
fetchConfig().then(() => {
    fetchHistory();
    fetchState();
    startSSE();
});
