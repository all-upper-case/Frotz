const input = document.getElementById('cmd-input');
const log = document.getElementById('log');
const hud = document.getElementById('hud');

window.addEventListener('DOMContentLoaded', async () => {
    try {
        const data = await fetchJson('/get_state');

        if (!data) {
            return;
        }

        if (data.response === "INITIALIZING_GENESIS") {
            // First time load, no save file found
            appendLog("NO WORLD DATA FOUND.", 'system');
            appendLog("INITIATING GENESIS PROTOCOL...", 'system');
            triggerReset();
        } else {
            appendLog(data.response, 'system');
            safeUpdateHUD(data.state);
        }
    } catch (e) {
        console.error('Failed to initialize game state', e);
    }
});

async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status} from ${url}: ${text.slice(0, 250)}`);
    }

    const contentType = res.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
        const text = await res.text();
        throw new Error(`Expected JSON from ${url}, got: ${contentType}. Body preview: ${text.slice(0, 250)}`);
    }

    return res.json();
}

async function triggerReset() {
    appendLog("READING LORE... CONSTRUCTING MATTER... (PLEASE WAIT)", 'system');

    try {
        const data = await fetchJson('/reset', { method: 'POST' });

        log.innerHTML = ''; // Clear loading text
        appendLog(data.response, 'system'); // Show Intro + Room 1
        appendUsage(data.usage);
        safeUpdateHUD(data.state);
    } catch (e) {
        // Keep this in console so terminal text isn't cluttered with false alarms.
        console.error('Reset failed', e);
    }
}

// Reset via command
document.getElementById('send-btn').onclick = sendCommand;
input.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendCommand(); });

document.getElementById('hud-toggle').onclick = () => hud.classList.add('open');
document.getElementById('hud-close').onclick = () => hud.classList.remove('open');

async function sendCommand() {
    const text = input.value.trim();
    if (!text) return;

    if (text === '/reset') {
        if (confirm("Wipe world and regenerate from Lore?")) triggerReset();
        input.value = '';
        return;
    }

    appendLog(`> ${text}`, 'user');
    input.value = '';

    try {
        const data = await fetchJson('/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input: text })
        });

        appendLog(data.response, 'ai');
        appendUsage(data.usage);
        safeUpdateHUD(data.state);
    } catch (e) {
        // Avoid noisy in-terminal false error messages; keep diagnostics in dev console.
        console.error('Command request failed', e);
    }
}

function appendLog(html, type) {
    const div = document.createElement('div');
    div.className = `msg ${type}`;
    div.innerHTML = marked.parse(html || '');
    log.appendChild(div);
    document.getElementById('terminal').scrollTop = 99999;
}

function safeUpdateHUD(state) {
    if (!state || !Array.isArray(state.exits) || !Array.isArray(state.inventory)) {
        return;
    }
    updateHUD(state);
}

function updateHUD(state) {
    document.getElementById('stat-loc').textContent = state.location;
    document.getElementById('stat-exits').textContent = state.exits.join(', ').toUpperCase();
    const ul = document.getElementById('stat-inv');
    ul.innerHTML = '';
    state.inventory.forEach(i => {
        const li = document.createElement('li');
        li.textContent = i;
        ul.appendChild(li);
    });
}

if (typeof marked === 'undefined') window.marked = { parse: (t) => t };

function appendUsage(usage) {
    if (!usage) return;
    const input = usage.input_tokens ?? '?';
    const output = usage.output_tokens ?? '?';
    const total = usage.total_tokens ?? '?';
    appendLog(`TOKENS — input: ${input}, output: ${output}, total: ${total}`, 'system');
}
