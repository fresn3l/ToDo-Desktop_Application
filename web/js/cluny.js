/**
 * Ask Cluny Home widget — questions, citations, and work proposals.
 * Cluny never places clock times. Accept lands in All Work.
 */

import * as utils from './utils.js';

function hasEel(name) {
    return typeof eel !== 'undefined' && typeof eel[name] === 'function';
}

function citationLabel(src) {
    if (typeof src === 'string') return src.trim();
    if (!src || typeof src !== 'object') return '';
    return String(src.title || src.label || src.doc_title || '').trim();
}

function applyHealth(probe) {
    const offline = !probe?.brain_ready;
    document.getElementById('clunyOffline')?.classList.toggle('is-hidden', !offline);
    const form = document.getElementById('clunyAskForm');
    const suggest = document.getElementById('clunySuggestBtn');
    if (form) form.hidden = offline;
    if (suggest) suggest.disabled = offline;
    const status = document.getElementById('clunyWidgetStatus');
    if (status) {
        status.textContent = offline
            ? (probe?.offline_copy || 'Cluny is off. Journal, to-dos, and the clock still work.')
            : 'Cluny is the brain. Kosistenz stays the list and the clock.';
    }
}

function paintAnswer(result) {
    const answer = document.getElementById('clunyAnswer');
    const sources = document.getElementById('clunySources');
    if (answer) {
        const text = String(result?.answer || '').trim();
        answer.hidden = !text;
        answer.textContent = text;
    }
    if (!sources) return;
    const labels = [...new Set((result?.sources || []).map(citationLabel).filter(Boolean))];
    if (!labels.length) {
        sources.hidden = true;
        sources.innerHTML = '';
        return;
    }
    sources.hidden = false;
    sources.innerHTML = labels
        .map((label) => `<span class="cluny-chip">${utils.escapeHtml(label)}</span>`)
        .join('');
}

function paintInbox(inbox) {
    const el = document.getElementById('clunyInbox');
    if (!el) return;
    const pending = inbox?.pending || [];
    if (!pending.length) {
        el.innerHTML = '';
        return;
    }
    el.innerHTML = pending
        .map((row) => {
            const id = utils.escapeHtml(row.id || '');
            const mins = row.estimate_minutes ? `${row.estimate_minutes} min` : '';
            const due = row.due ? `due ${row.due}` : '';
            const kws = (row.keywords || []).filter(Boolean).join(', ');
            const meta = [mins, due, kws].filter(Boolean).join(' · ');
            return `<li class="cluny-inbox-row" data-id="${id}">
                <div>
                    <strong>${utils.escapeHtml(row.title || '')}</strong>
                    ${meta ? `<p class="checklist-hint small">${utils.escapeHtml(meta)}</p>` : ''}
                </div>
                <div class="cluny-inbox-actions">
                    <button type="button" class="btn-primary" data-cluny-accept="${id}">Accept</button>
                    <button type="button" class="btn-ghost" data-cluny-dismiss="${id}">Dismiss</button>
                </div>
            </li>`;
        })
        .join('');
}

export async function refreshCluny() {
    const root = document.getElementById('clunySource');
    if (!root) return;
    if (hasEel('get_cluny_health')) {
        try {
            applyHealth(await eel.get_cluny_health()());
        } catch (err) {
            console.error(err);
            applyHealth({ brain_ready: false });
        }
    }
    if (!hasEel('get_cluny_inbox')) return;
    try {
        paintInbox(await eel.get_cluny_inbox()());
    } catch (err) {
        console.error(err);
    }
}

export async function onClunyTabShown() {
    await refreshCluny();
}

async function askQuestion(event) {
    event.preventDefault();
    const input = document.getElementById('clunyAskInput');
    const btn = document.getElementById('clunyAskBtn');
    const question = (input?.value || '').trim();
    if (!question) {
        utils.showErrorFeedback('Ask a question first.');
        return;
    }
    if (!hasEel('ask_cluny')) {
        utils.showErrorFeedback('Cluny is off. Journal, to-dos, and the clock still work.');
        return;
    }
    if (btn) btn.disabled = true;
    try {
        paintAnswer(await eel.ask_cluny(question)());
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Cluny did not answer.');
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function suggestWork() {
    const btn = document.getElementById('clunySuggestBtn');
    if (!hasEel('suggest_cluny_work')) {
        utils.showErrorFeedback('Cluny is off. Journal, to-dos, and the clock still work.');
        return;
    }
    if (btn) btn.disabled = true;
    try {
        const inbox = await eel.suggest_cluny_work()();
        paintInbox(inbox);
        const added = inbox?.added || 0;
        if (added) {
            utils.showSuccessFeedback(added === 1 ? 'One suggestion.' : `${added} suggestions.`);
        } else {
            utils.showSuccessFeedback('No new suggestions.');
        }
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Cluny could not suggest work.');
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function acceptProposal(id) {
    if (!hasEel('accept_cluny_proposal')) return;
    try {
        const result = await eel.accept_cluny_proposal(id)();
        paintInbox(result?.inbox);
        utils.notifyDataChanged();
        if (result?.duplicate) {
            utils.showSuccessFeedback('Already in All Work.');
            return;
        }
        utils.showSuccessFeedback('Added to All Work. You pick the day.');
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not accept that suggestion.');
    }
}

async function dismissProposal(id) {
    if (!hasEel('dismiss_cluny_proposal')) return;
    try {
        paintInbox(await eel.dismiss_cluny_proposal(id)());
        utils.notifyDataChanged();
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not dismiss that suggestion.');
    }
}

export function setupCluny() {
    const root = document.getElementById('clunySource');
    if (!root || root.dataset.ready === '1') return;
    root.dataset.ready = '1';
    document.getElementById('clunyAskForm')?.addEventListener('submit', (event) => {
        void askQuestion(event);
    });
    document.getElementById('clunySuggestBtn')?.addEventListener('click', () => {
        void suggestWork();
    });
    root.addEventListener('click', (event) => {
        const accept = event.target.closest('[data-cluny-accept]');
        if (accept) {
            void acceptProposal(accept.getAttribute('data-cluny-accept'));
            return;
        }
        const dismiss = event.target.closest('[data-cluny-dismiss]');
        if (dismiss) {
            void dismissProposal(dismiss.getAttribute('data-cluny-dismiss'));
        }
    });
}
