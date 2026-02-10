const input = document.getElementById('cmd-input');
const log = document.getElementById('log');
const hud = document.getElementById('hud');

window.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/get_state');
        const data = await res.json();

        if (data.response === "INITIALIZING_GENESIS") {
            // First time load, no save file found
            appendLog("NO WORLD DATA FOUND.", 'system');
            appendLog("INITIATING GENESIS PROTOCOL...", 'system');
            triggerReset();
        } else {
            appendLog(data.response, 'system');
            if (data.state) updateHUD(data.state);
        }
    } catch(e) {
        appendLog("CONNECTION FAILED.", 'error');
    }
});

async function triggerReset() {
    appendLog("READING LORE... CONSTRUCTING MATTER... (PLEASE WAIT)", 'system');
    const res = await fetch('/reset', {method: 'POST'});
    const data = await res.json();

    log.innerHTML = ''; // Clear loading text
    appendLog(data.response, 'system'); // Show Intro + Room 1
    appendUsage(data.usage);
    if (data.state) updateHUD(data.state);
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
        if(confirm("Wipe world and regenerate from Lore?")) triggerReset();
        input.value = '';
        return;
    }

    appendLog(`> ${text}`, 'user');
    input.value = '';

    try {
        const res = await fetch('/command', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({input: text})
        });
        const data = await res.json();
        appendLog(data.response, 'ai');
        appendUsage(data.usage);
        if (data.state) updateHUD(data.state);
    } catch (e) {
        appendLog("Error contacting server.", 'error');
    }
}

function appendLog(html, type) {
    const div = document.createElement('div');
    div.className = `msg ${type}`;
    div.innerHTML = marked.parse(html || "");
    log.appendChild(div);
    document.getElementById('terminal').scrollTop = 99999;
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
