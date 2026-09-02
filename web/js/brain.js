/**
 * Brain tab — Cluny chat, streaming, brain editor, propose.
 */

import * as utils from './utils.js';

let brainReady = false;
let streamingAnswerEl = null;

function hasEel(name) {
    return typeof eel !== 'undefined' && typeof eel[name] === 'function';
}

function citationLabel(src) {
    if (typeof src === 'string') return src.trim();
    if (!src || typeof src !== 'object') return '';
    return String(src.title || src.label || src.doc_title || '').trim();
}

function paintSources(container, sources) {
    if (!container) return;
    const labels = [...new Set((sources || []).map(citationLabel).filter(Boolean))];
    if (!labels.length) {
        container.hidden = true;
        container.innerHTML = '';
        return;
    }
    container.hidden = false;
    container.innerHTML = labels
        .map((label) => `<span class="cluny-chip">${utils.escapeHtml(label)}</span>`)
        .join('');
}

function appendMessage(role, text, sources) {
    const log = document.getElementById('brainChatLog');
    if (!log) return null;
    const row = document.createElement('div');
    row.className = `brain-msg brain-msg--${role}`;
    const body = document.createElement('div');
    body.className = 'brain-msg-body';
    body.textContent = text || '';
    row.appendChild(body);
    if (sources?.length) {
        const chips = document.createElement('div');
        chips.className = 'cluny-sources';
        paintSources(chips, sources);
        row.appendChild(chips);
    }
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
    return body;
}

function applyHealth(probe) {
    brainReady = Boolean(probe?.brain_ready);
    document.getElementById('brainOffline')?.classList.toggle('is-hidden', brainReady);
    const form = document.getElementById('brainChatForm');
    if (form) form.hidden = !brainReady;
    const pill = document.getElementById('brainHealthPill');
    if (pill) {
        pill.textContent = brainReady ? 'Online' : 'Offline';
        pill.dataset.state = brainReady ? 'ok' : 'down';
    }
    const line = document.getElementById('brainStatusLine');
    if (line) {
        line.textContent = brainReady
            ? 'Live Kosistenz context on every message.'
            : (probe?.offline_copy || 'Cluny is off. Journal, to-dos, and the clock still work.');
    }
}

function applyStats(stats) {
    const doc = document.getElementById('brainDocCount');
    const chunks = document.getElementById('brainChunkCount');
    const model = document.getElementById('brainChatModel');
    if (doc) doc.textContent = stats?.doc_count ?? '—';
    if (chunks) chunks.textContent = stats?.chunk_count ?? '—';
    if (model) model.textContent = stats?.chat_model ?? '—';
}

function fillSelect(id, values, current) {
    const el = document.getElementById(id);
    if (!el) return;
    const opts = ['<option value="">All collections</option>']
        .concat((values || []).map((v) => {
            const val = utils.escapeHtml(String(v));
            const sel = current && current === v ? ' selected' : '';
            return `<option value="${val}"${sel}>${val}</option>`;
        }));
    el.innerHTML = opts.join('');
}

async function refreshBrainCollections() {
    if (!hasEel('brain_library_filters')) return;
    const collection = document.getElementById('brainCollectionFilter')?.value || '';
    try {
        const filters = await eel.brain_library_filters()();
        fillSelect('brainCollectionFilter', filters?.collections || [], collection);
    } catch (err) {
        console.error(err);
    }
}

export async function refreshBrain() {
    if (!hasEel('brain_health')) return;
    try {
        if (hasEel('brain_ensure_serve')) {
            await eel.brain_ensure_serve()();
        }
        const health = await eel.brain_health()();
        applyHealth(health);
        applyStats(health);
        if (health?.brain_ready && hasEel('brain_sync_analytics')) {
            eel.brain_sync_analytics()().catch((err) => console.error(err));
        }
        if (health?.brain_ready && hasEel('brain_stats')) {
            try {
                applyStats(await eel.brain_stats()());
            } catch (err) {
                console.error(err);
            }
        }
        await refreshBrainCollections();
        if (hasEel('brain_user_config_get')) {
            try {
                const cfg = await eel.brain_user_config_get()();
                const mode = document.getElementById('brainAgentMode');
                if (mode && cfg?.agent_mode) mode.value = cfg.agent_mode;
            } catch (err) {
                console.error(err);
            }
        }
    } catch (err) {
        console.error(err);
        applyHealth({ brain_ready: false });
    }
}

export async function onBrainTabShown() {
    await refreshBrain();
}

async function sendChat(event) {
    event.preventDefault();
    const input = document.getElementById('brainChatInput');
    const btn = document.getElementById('brainSendBtn');
    const text = (input?.value || '').trim();
    if (!text) {
        utils.showErrorFeedback('Write a message first.');
        return;
    }
    if (!brainReady || !hasEel('brain_chat_stream')) {
        utils.showErrorFeedback('Cluny is off.');
        return;
    }
    appendMessage('user', text);
    if (input) input.value = '';
    if (btn) btn.disabled = true;
    streamingAnswerEl = appendMessage('assistant', '');
    try {
        const collection = document.getElementById('brainCollectionFilter')?.value || '';
        const result = await eel.brain_chat_stream(text, collection)();
        if (streamingAnswerEl && result?.answer) {
            streamingAnswerEl.textContent = result.answer;
        }
        if (streamingAnswerEl?.parentElement && result?.sources?.length) {
            const chips = document.createElement('div');
            chips.className = 'cluny-sources';
            paintSources(chips, result.sources);
            streamingAnswerEl.parentElement.appendChild(chips);
        }
    } catch (err) {
        console.error(err);
        if (streamingAnswerEl) {
            streamingAnswerEl.textContent = err?.message || 'Cluny did not answer.';
        }
    } finally {
        streamingAnswerEl = null;
        if (btn) btn.disabled = false;
    }
}

export function onBrainStreamEvent(event) {
    if (!streamingAnswerEl || !event) return;
    if (event.token) {
        streamingAnswerEl.textContent += event.token;
        const log = document.getElementById('brainChatLog');
        if (log) log.scrollTop = log.scrollHeight;
    }
}

async function runPropose() {
    const btn = document.getElementById('brainProposeBtn');
    if (!brainReady || !hasEel('brain_propose')) {
        utils.showErrorFeedback('Cluny is off.');
        return;
    }
    if (btn) btn.disabled = true;
    try {
        const collection = document.getElementById('brainCollectionFilter')?.value || '';
        const result = await eel.brain_propose('', collection)();
        const panel = document.getElementById('brainProposePanel');
        panel?.classList.remove('is-hidden');
        paintSources(document.getElementById('brainProposeSources'), result?.sources || []);
        const list = document.getElementById('brainProposeList');
        const proposals = result?.proposals || [];
        if (!list) return;
        if (!proposals.length) {
            list.innerHTML = '<li class="checklist-hint small">No proposals right now.</li>';
            return;
        }
        list.innerHTML = proposals
            .map((row, idx) => {
                const id = utils.escapeHtml(row.id || `p-${idx}`);
                const meta = [row.estimate_minutes ? `${row.estimate_minutes} min` : '', row.due ? `due ${row.due}` : '']
                    .filter(Boolean).join(' · ');
                return `<li class="cluny-inbox-row" data-id="${id}">
                    <div>
                        <strong>${utils.escapeHtml(row.title || '')}</strong>
                        ${meta ? `<p class="checklist-hint small">${utils.escapeHtml(meta)}</p>` : ''}
                    </div>
                    <div class="cluny-inbox-actions">
                        <button type="button" class="btn-primary" data-brain-accept="${id}">Accept</button>
                    </div>
                </li>`;
            })
            .join('');
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Propose failed.');
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function acceptProposal(id) {
    if (!hasEel('brain_accept_proposal')) return;
    try {
        await eel.brain_accept_proposal(id)();
        utils.notifyDataChanged();
        utils.showSuccessFeedback('Added to All Work.');
        await runPropose();
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not accept.');
    }
}

function openBrainModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('is-hidden');
    el.hidden = false;
}

function closeBrainModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add('is-hidden');
    el.hidden = true;
}

async function openBrainEditor() {
    if (!hasEel('brain_config_get')) {
        utils.showErrorFeedback('Brain editor unavailable. Restart Kosistenz.');
        return;
    }
    try {
        const cfg = await eel.brain_config_get()();
        document.getElementById('brainPersona').value = cfg?.global_persona || '';
        document.getElementById('brainRagSystem').value = cfg?.prompts?.rag_system || cfg?.defaults?.rag_system || '';
        openBrainModal('brainEditorDialog');
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not load brain config.');
    }
}

async function saveBrainEditor(event) {
    event.preventDefault();
    if (!hasEel('brain_config_save')) return;
    try {
        await eel.brain_config_save({
            global_persona: document.getElementById('brainPersona')?.value || '',
            prompts: { rag_system: document.getElementById('brainRagSystem')?.value || '' },
        })();
        utils.showSuccessFeedback('Brain instructions saved.');
        closeBrainModal('brainEditorDialog');
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Save failed.');
    }
}

async function openBrainSettings() {
    if (!hasEel('brain_user_config_get')) {
        utils.showErrorFeedback('Brain settings unavailable. Restart Kosistenz.');
        return;
    }
    try {
        const cfg = await eel.brain_user_config_get()();
        document.getElementById('brainChatModelInput').value = cfg?.chat_model || '';
        document.getElementById('brainEmbedModelInput').value = cfg?.embed_model || '';
        document.getElementById('brainRetrievalK').value = cfg?.retrieval_k ?? 5;
        document.getElementById('brainHybridWeight').value = cfg?.hybrid_vector_weight ?? 0.5;
        document.getElementById('brainAskCollection').value = cfg?.ask_collection || '';
        openBrainModal('brainSettingsDialog');
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not load settings.');
    }
}

async function saveBrainSettings(event) {
    event.preventDefault();
    if (!hasEel('brain_user_config_save')) return;
    try {
        await eel.brain_user_config_save({
            chat_model: document.getElementById('brainChatModelInput')?.value || null,
            embed_model: document.getElementById('brainEmbedModelInput')?.value || null,
            retrieval_k: parseInt(document.getElementById('brainRetrievalK')?.value || '5', 10),
            hybrid_vector_weight: parseFloat(document.getElementById('brainHybridWeight')?.value || '0.5'),
            ask_collection: document.getElementById('brainAskCollection')?.value || null,
            agent_mode: document.getElementById('brainAgentMode')?.value || null,
        })();
        utils.showSuccessFeedback('Brain settings saved.');
        closeBrainModal('brainSettingsDialog');
        await refreshBrain();
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Save failed.');
    }
}

export function setupBrain() {
    const root = document.getElementById('brainTab');
    if (!root || root.dataset.ready === '1') return;
    root.dataset.ready = '1';

    if (typeof eel !== 'undefined' && typeof eel.expose === 'function') {
        eel.expose(onBrainStreamEvent, 'brain_push_stream_event');
    }

    document.getElementById('brainChatForm')?.addEventListener('submit', (e) => {
        void sendChat(e);
    });
    document.getElementById('brainProposeBtn')?.addEventListener('click', () => {
        void runPropose();
    });
    document.getElementById('brainNewSessionBtn')?.addEventListener('click', () => {
        if (hasEel('brain_new_session')) {
            eel.brain_new_session('Kosistenz')().then(() => {
                document.getElementById('brainChatLog').innerHTML = '';
            }).catch((err) => console.error(err));
        }
    });
    document.getElementById('brainStartServeBtn')?.addEventListener('click', () => {
        void refreshBrain();
    });
    document.getElementById('brainOpenLibraryBtn')?.addEventListener('click', () => {
        document.dispatchEvent(new CustomEvent('kosistenz:open-tab', { detail: { tab: 'library' } }));
    });
    document.getElementById('brainOpenBrainEditorBtn')?.addEventListener('click', () => {
        void openBrainEditor();
    });
    document.getElementById('brainOpenSettingsBtn')?.addEventListener('click', () => {
        void openBrainSettings();
    });
    document.getElementById('brainEditorClose')?.addEventListener('click', () => {
        closeBrainModal('brainEditorDialog');
    });
    document.getElementById('brainSettingsClose')?.addEventListener('click', () => {
        closeBrainModal('brainSettingsDialog');
    });
    document.getElementById('brainEditorForm')?.addEventListener('submit', (e) => {
        void saveBrainEditor(e);
    });
    document.getElementById('brainSettingsForm')?.addEventListener('submit', (e) => {
        void saveBrainSettings(e);
    });
    document.getElementById('brainResetConfigBtn')?.addEventListener('click', () => {
        if (!hasEel('brain_config_reset')) return;
        eel.brain_config_reset({ reset_all: true })()
            .then(() => openBrainEditor())
            .catch((err) => console.error(err));
    });
    document.getElementById('brainExportConfigBtn')?.addEventListener('click', () => {
        if (!hasEel('brain_export_config')) return;
        eel.brain_export_config()().then((raw) => {
            const blob = new Blob([raw], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'cluny-brain-config.json';
            a.click();
            URL.revokeObjectURL(url);
        }).catch((err) => console.error(err));
    });
    document.getElementById('brainImportConfigBtn')?.addEventListener('click', () => {
        document.getElementById('brainImportFile')?.click();
    });
    document.getElementById('brainImportFile')?.addEventListener('change', (e) => {
        const file = e.target.files?.[0];
        if (!file || !hasEel('brain_import_config')) return;
        file.text().then((raw) => eel.brain_import_config(raw)())
            .then(() => {
                utils.showSuccessFeedback('Imported brain config.');
                void openBrainEditor();
            })
            .catch((err) => console.error(err));
        e.target.value = '';
    });

    root.addEventListener('click', (event) => {
        const accept = event.target.closest('[data-brain-accept]');
        if (accept) {
            void acceptProposal(accept.getAttribute('data-brain-accept'));
        }
    });
}
