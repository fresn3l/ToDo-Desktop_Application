/**
 * Daily Checklist — branching flow driven by Python-provided JSON definition.
 */

import * as utils from './utils.js';

let state = null;

export async function setupDailyChecklist() {
    const restart = document.getElementById('restartChecklist');
    if (restart) {
        restart.addEventListener('click', () => {
            startWizard();
        });
    }
    try {
        await loadDefinition();
        startWizard();
    } catch (e) {
        console.error(e);
        const el = document.getElementById('checklistWizard');
        if (el) {
            el.innerHTML = `<p class="checklist-error">Could not load checklist: ${utils.escapeHtml(String(e))}</p>`;
        }
    }
}

async function loadDefinition() {
    const def = await eel.get_daily_checklist()();
    state = { def, currentId: null, answers: {} };
}

function startWizard() {
    if (!state || !state.def) return;
    state.currentId = state.def.start;
    state.answers = {};
    renderWizard();
}

export async function onChecklistTabShown() {
    await loadRecentSubmissions();
    if (!state || !state.def) {
        try {
            await loadDefinition();
        } catch (e) {
            console.error(e);
            return;
        }
    }
    if (!state.currentId) {
        startWizard();
    } else {
        renderWizard();
    }
}

function renderWizard() {
    const el = document.getElementById('checklistWizard');
    if (!el || !state || !state.def) return;

    const node = state.def.nodes[state.currentId];
    if (!node) {
        el.innerHTML = '<p class="checklist-error">Missing question in checklist definition.</p>';
        return;
    }

    if (node.type === 'yes_no') {
        el.innerHTML = `
            <div class="checklist-card">
                <p class="checklist-q">${utils.escapeHtml(node.question)}</p>
                <div class="checklist-yesno">
                    <button type="button" class="btn-primary checklist-yes">Yes</button>
                    <button type="button" class="btn-secondary checklist-no">No</button>
                </div>
            </div>
        `;
        el.querySelector('.checklist-yes').addEventListener('click', () => {
            state.answers[state.currentId] = true;
            goTo(node.onYes);
        });
        el.querySelector('.checklist-no').addEventListener('click', () => {
            state.answers[state.currentId] = false;
            goTo(node.onNo);
        });
        return;
    }

    if (node.type === 'choice') {
        let radios = '';
        node.options.forEach((opt, i) => {
            radios += `
                <label class="checklist-option">
                    <input type="radio" name="checklistChoice" value="${i}">
                    <span>${utils.escapeHtml(opt.label)}</span>
                </label>
            `;
        });
        let otherBlock = '';
        if (node.allowOther) {
            otherBlock = `
                <label class="checklist-option">
                    <input type="radio" name="checklistChoice" value="other">
                    <span>Other</span>
                </label>
                <input type="text" class="checklist-other-input" id="checklistOtherText" placeholder="Describe your workout..." autocomplete="off">
            `;
        }
        el.innerHTML = `
            <div class="checklist-card">
                <p class="checklist-q">${utils.escapeHtml(node.question)}</p>
                <div class="checklist-options">${radios}${otherBlock}</div>
                <button type="button" class="btn-primary checklist-next">Continue</button>
            </div>
        `;
        const otherInput = el.querySelector('#checklistOtherText');
        if (otherInput) {
            el.querySelectorAll('input[name="checklistChoice"]').forEach((r) => {
                r.addEventListener('change', () => {
                    const show = r.value === 'other' && r.checked;
                    otherInput.style.display = show ? 'block' : 'none';
                    if (!show) otherInput.value = '';
                });
            });
            otherInput.style.display = 'none';
        }
        el.querySelector('.checklist-next').addEventListener('click', () => {
            const selected = el.querySelector('input[name="checklistChoice"]:checked');
            if (!selected) {
                utils.showErrorFeedback('Choose an option.');
                return;
            }
            const idx = selected.value;
            if (idx === 'other') {
                const text = (otherInput && otherInput.value.trim()) || '';
                if (!text) {
                    utils.showErrorFeedback('Please describe your workout type.');
                    return;
                }
                state.answers[state.currentId] = { value: 'other', otherText: text };
                goTo(node.otherNext || 'end');
                return;
            }
            const opt = node.options[parseInt(idx, 10)];
            if (!opt) return;
            state.answers[state.currentId] = { value: opt.value };
            goTo(opt.next);
        });
    }
}

function goTo(nextId) {
    if (nextId === 'end') {
        completeFlow();
        return;
    }
    state.currentId = nextId;
    renderWizard();
}

async function completeFlow() {
    try {
        const id = state.def.id;
        const version = state.def.version;
        const answers = { ...state.answers };
        await eel.submit_daily_checklist_response(id, version, answers)();
        utils.showSuccessFeedback('Saved to your local database.');
        await loadRecentSubmissions();
    } catch (e) {
        console.error(e);
        utils.showErrorFeedback('Could not save. Try again.');
        return;
    }
    startWizard();
}

async function loadRecentSubmissions() {
    const listEl = document.getElementById('checklistRecentList');
    const pathEl = document.getElementById('checklistDbPath');
    if (pathEl) {
        try {
            const p = await eel.get_daily_checklist_db_path_exposed()();
            pathEl.textContent = p;
        } catch (_) {
            pathEl.textContent = '';
        }
    }
    if (!listEl) return;
    listEl.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><p>Loading…</p></div>';
    try {
        const rows = await eel.list_daily_checklist_submissions(30)();
        if (!rows.length) {
            listEl.innerHTML = '<p class="checklist-empty">No submissions yet.</p>';
            return;
        }
        let html = '';
        rows.forEach((row) => {
            const when = new Date(row.created_at).toLocaleString();
            const summary = utils.escapeHtml(JSON.stringify(row.answers, null, 2));
            html += `
                <div class="checklist-history-item">
                    <div class="checklist-history-meta">${utils.escapeHtml(when)} · ${utils.escapeHtml(row.local_date)}</div>
                    <pre class="checklist-history-json">${summary}</pre>
                </div>
            `;
        });
        listEl.innerHTML = html;
    } catch (e) {
        console.error(e);
        listEl.innerHTML = '<p class="checklist-error">Could not load history.</p>';
    }
}
