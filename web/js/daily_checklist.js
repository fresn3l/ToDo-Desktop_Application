/**
 * Daily Checklist — built-in JSON flow plus user-defined extra questions.
 */

import * as utils from './utils.js';

let state = null;
let checklistTemplateSelectBound = false;

async function populateChecklistTemplateSelect() {
    const sel = document.getElementById('checklistTemplateSelect');
    if (!sel) return;
    let bundles = [];
    let active = 'default';
    try {
        bundles = await eel.list_bundled_checklists()();
        active = await eel.get_active_checklist_stem()();
    } catch (e) {
        console.error(e);
        return;
    }
    sel.innerHTML = '';
    bundles.forEach((b) => {
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = b.title;
        if (b.id === active) opt.selected = true;
        sel.appendChild(opt);
    });
    sel.value = active;
    if (!checklistTemplateSelectBound) {
        checklistTemplateSelectBound = true;
        sel.addEventListener('change', async () => {
            try {
                await openChecklistTemplate(sel.value, { announce: true });
            } catch (e) {
                console.error(e);
                utils.showErrorFeedback(
                    typeof e === 'string' ? e : e?.message || 'Could not switch template.',
                );
                try {
                    sel.value = await eel.get_active_checklist_stem()();
                } catch (_) {
                    /* ignore */
                }
            }
        });
    }
}

export async function openChecklistTemplate(stem, { announce = false } = {}) {
    if (!stem) return;
    await eel.set_active_checklist_stem(stem)();
    const sel = document.getElementById('checklistTemplateSelect');
    if (sel) sel.value = stem;
    await loadDefinition();
    await renderCustomItemsList();
    startWizard();
    await loadRecentSubmissions();
    if (announce) {
        utils.showSuccessFeedback('Checklist template updated.');
    }
}

async function setupReminderControls() {
    const status = document.getElementById('reminderStatus');
    try {
        const cfg = await eel.get_reminder_config()();
        document.getElementById('reminderEnabled').checked = !!cfg.enabled;
        document.getElementById('reminderHour').value = cfg.hour ?? 20;
        document.getElementById('reminderMinute').value = cfg.minute ?? 0;
        if (status) {
            status.textContent = cfg.installed ? 'Installed' : 'Not installed';
        }
        const plistEl = document.getElementById('reminderPlistPath');
        if (plistEl) plistEl.textContent = cfg.plist_path || '';
    } catch (e) {
        console.error(e);
    }

    document.getElementById('saveReminderBtn')?.addEventListener('click', async () => {
        const enabled = !!document.getElementById('reminderEnabled')?.checked;
        const hour = parseInt(document.getElementById('reminderHour')?.value || '20', 10);
        const minute = parseInt(document.getElementById('reminderMinute')?.value || '0', 10);
        try {
            const result = await eel.set_reminder_config(enabled, hour, minute)();
            if (status) {
                status.textContent = result.error || (result.installed ? 'Reminder saved and installed.' : 'Reminder disabled.');
            }
            if (result.error) {
                utils.showErrorFeedback(result.error);
            } else {
                utils.showSuccessFeedback('Reminder updated.');
            }
        } catch (e) {
            utils.showErrorFeedback('Reminder setup failed.');
        }
    });

    document.getElementById('testReminderBtn')?.addEventListener('click', async () => {
        try {
            const result = await eel.test_local_reminder()();
            if (result.ok) utils.showSuccessFeedback('Test notification sent.');
            else utils.showErrorFeedback(result.error || result.stderr || 'Test failed.');
        } catch (e) {
            utils.showErrorFeedback('Test failed.');
        }
    });
}

export async function setupDailyChecklist() {
    const restart = document.getElementById('restartChecklist');
    if (restart) {
        restart.addEventListener('click', () => {
            startWizard();
        });
    }

    const typeSel = document.getElementById('newItemType');
    const choiceWrap = document.getElementById('choiceOptionsWrap');
    const trackDurationWrap = document.getElementById('trackDurationWrap');
    const toggleCustomItemFields = () => {
        const type = typeSel?.value || 'yes_no';
        if (choiceWrap) choiceWrap.classList.toggle('is-hidden', type !== 'choice');
        const allowDuration = type === 'yes_no' || type === 'choice';
        if (trackDurationWrap) {
            trackDurationWrap.classList.toggle('is-hidden', !allowDuration);
        }
        if (!allowDuration) {
            const td = document.getElementById('newItemTrackDuration');
            if (td) td.checked = false;
        }
    };
    typeSel?.addEventListener('change', toggleCustomItemFields);
    toggleCustomItemFields();

    await setupReminderControls();
    setupChecklistKeys();

    document.getElementById('addCustomItemBtn')?.addEventListener('click', async () => {
        const type = document.getElementById('newItemType')?.value || 'yes_no';
        const question = document.getElementById('newItemQuestion')?.value.trim() || '';
        if (!question) {
            utils.showErrorFeedback('Enter a question.');
            return;
        }
        try {
            const payload = { type, question };
            if (type === 'choice') {
                const raw = document.getElementById('newItemOptions')?.value || '';
                const options = raw.split('\n').map((s) => s.trim()).filter(Boolean);
                payload.options = options;
                payload.allowOther = !!document.getElementById('newItemAllowOther')?.checked;
            }
            if (type === 'yes_no' || type === 'choice') {
                payload.trackDuration = !!document.getElementById('newItemTrackDuration')?.checked;
            }
            await eel.add_custom_checklist_item(payload)();
            document.getElementById('newItemQuestion').value = '';
            const ta = document.getElementById('newItemOptions');
            if (ta) ta.value = '';
            const ao = document.getElementById('newItemAllowOther');
            if (ao) ao.checked = false;
            const td = document.getElementById('newItemTrackDuration');
            if (td) td.checked = false;
            utils.showSuccessFeedback('Question added.');
            await refreshCustomItems();
            await renderCustomItemsList();
        } catch (e) {
            console.error(e);
            utils.showErrorFeedback(typeof e === 'string' ? e : e?.message || 'Could not add question.');
        }
    });

    try {
        await populateChecklistTemplateSelect();
        await loadDefinition();
        await renderCustomItemsList();
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
    const customItems = await eel.get_custom_checklist_items()();
    state = {
        def,
        currentId: null,
        answers: {},
        customItems,
        extraIndex: null,
    };
}

async function refreshCustomItems() {
    if (!state) return;
    state.customItems = await eel.get_custom_checklist_items()();
}

async function renderCustomItemsList() {
    await refreshCustomItems();
    const container = document.getElementById('customItemsList');
    if (!container || !state) return;

    const items = state.customItems || [];
    if (!items.length) {
        container.innerHTML = `
            <div class="empty-state empty-state--message empty-state--compact">
                <h3>No extra questions yet</h3>
                <p>Open &ldquo;Add a custom question&rdquo; below to create one.</p>
            </div>
        `;
        return;
    }

    let html = '';
    items.forEach((item) => {
        const typeLabels = {
            yes_no: 'Yes / No',
            choice: 'Multiple choice',
            text: 'Short text',
            scale: 'Scale',
            number: 'Number',
        };
        const typeLabel = typeLabels[item.type] || item.type;
        let detail = '';
        if (item.type === 'choice' && Array.isArray(item.options)) {
            detail = item.options.map((o) => o.label || o.value).join(', ');
        }
        const durNote = item.trackDuration
            ? '<br><span class="checklist-duration-badge">Asks duration (min)</span>'
            : '';
        html += `
            <div class="custom-item-row">
                <div class="custom-item-meta">
                    <strong>${utils.escapeHtml(typeLabel)}</strong><br>
                    ${utils.escapeHtml(item.question)}${detail ? `<br><span class="checklist-empty">${utils.escapeHtml(detail)}</span>` : ''}${durNote}
                </div>
                <button type="button" class="btn-secondary custom-item-remove" data-id="${item.id}">Remove</button>
            </div>
        `;
    });
    container.innerHTML = html;
    container.querySelectorAll('.custom-item-remove').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const id = btn.getAttribute('data-id');
            try {
                await eel.remove_custom_checklist_item(id)();
                await renderCustomItemsList();
                utils.showSuccessFeedback('Removed.');
            } catch (err) {
                console.error(err);
                utils.showErrorFeedback('Could not remove.');
            }
        });
    });
}

function startWizard() {
    if (!state || !state.def) return;
    state.currentId = state.def.start;
    state.answers = {};
    state.extraIndex = null;
    renderWizard();
}

function isTypingTarget(el) {
    if (!el) return false;
    const tag = (el.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
    return !!el.isContentEditable;
}

function setupChecklistKeys() {
    if (document.body.dataset.checklistKeys === '1') return;
    document.body.dataset.checklistKeys = '1';
    document.addEventListener('keydown', (e) => {
        if (e.metaKey || e.ctrlKey || e.altKey) return;
        const tab = document.getElementById('checklistTab');
        if (!tab || !tab.classList.contains('active')) return;
        if (isTypingTarget(e.target)) return;
        const card = document.querySelector('#checklistWizard [data-kind]');
        if (!card) return;
        const kind = card.getAttribute('data-kind');
        if (kind === 'yes_no' && (e.key === 'y' || e.key === 'Y')) {
            e.preventDefault();
            card.querySelector('.checklist-yes, .extra-yes')?.click();
        } else if (kind === 'yes_no' && (e.key === 'n' || e.key === 'N')) {
            e.preventDefault();
            card.querySelector('.checklist-no, .extra-no')?.click();
        } else if (kind === 'scale') {
            let value = e.key;
            if (e.key === '0' && card.querySelector('.checklist-scale-btn[data-value="10"]')) {
                value = '10';
            }
            const btn = card.querySelector(`.checklist-scale-btn[data-value="${value}"]`);
            if (btn) {
                e.preventDefault();
                btn.click();
            }
        }
    });
}

function nodeForAnswerKey(key) {
    return state?.def?.nodes?.[key] || (state?.customItems || []).find((i) => i.id === key) || {};
}

function formatPreviewValue(node, val) {
    if (val === true) return 'Yes';
    if (val === false) return 'No';
    if (val == null) return '—';
    if (typeof val === 'object') {
        if (Object.prototype.hasOwnProperty.call(val, 'answer')) {
            const base = formatPreviewValue(node, val.answer);
            return val.durationMinutes != null ? `${base} (${val.durationMinutes} min)` : base;
        }
        if (val.value === 'other') {
            const base = `Other: ${val.otherText || ''}`;
            return val.durationMinutes != null ? `${base} (${val.durationMinutes} min)` : base;
        }
        if (val.value != null) {
            const opt = (node.options || []).find((o) => o.value === val.value);
            const base = opt ? opt.label : String(val.value);
            return val.durationMinutes != null ? `${base} (${val.durationMinutes} min)` : base;
        }
        if (val.durationMinutes != null) return `${val.durationMinutes} min`;
        return '';
    }
    if (node?.type === 'choice') {
        const opt = (node.options || []).find((o) => o.value === val);
        if (opt) return opt.label;
    }
    return String(val);
}

function estimatedTotalSteps() {
    const nodes = state?.def?.nodes || {};
    let n = 0;
    Object.values(nodes).forEach((node) => {
        if (node && ['yes_no', 'choice', 'text', 'scale', 'number'].includes(node.type)) n += 1;
    });
    n += (state?.customItems || []).length;
    return Math.max(n, 1);
}

function currentStepNumber() {
    return Object.keys(state?.answers || {}).length + 1;
}

function scaleKbdHint(min, max) {
    if (max >= 10) return `${min}–${max} · 0 for 10`;
    return `${min}–${max}`;
}

function paintWizard(cardBody, { kind = '', extraTag = '', kbdHint = '' } = {}) {
    const el = document.getElementById('checklistWizard');
    if (!el) return el;
    const total = estimatedTotalSteps();
    const current = Math.min(currentStepNumber(), total);
    const pct = Math.round((current / total) * 100);
    const recapItems = Object.entries(state?.answers || {})
        .map(([key, val]) => {
            const node = nodeForAnswerKey(key);
            const label = node.question || String(key).replace(/[_-]+/g, ' ');
            const value = formatPreviewValue(node, val);
            return `<li><span class="wizard-recap-q">${utils.escapeHtml(label)}</span><span class="wizard-recap-a">${utils.escapeHtml(value)}</span></li>`;
        })
        .join('');
    const recap = recapItems ? `<ol class="wizard-recap">${recapItems}</ol>` : '';
    const hint =
        kbdHint
        || (kind === 'yes_no' ? 'Y / N' : '');
    const kbd = hint ? `<p class="wizard-kbd">${utils.escapeHtml(hint)}</p>` : '';
    el.innerHTML = `
        <div class="wizard-shell">
            <div class="wizard-progress">
                <div class="wizard-progress-meta">
                    <span>${current} of ${total}</span>
                </div>
                <div class="wizard-progress-track" role="progressbar" aria-valuemin="1" aria-valuemax="${total}" aria-valuenow="${current}">
                    <div class="wizard-progress-fill" style="width:${pct}%"></div>
                </div>
            </div>
            ${recap}
            ${extraTag ? `<p class="checklist-extra-tag">${extraTag}</p>` : ''}
            <div class="checklist-card" data-kind="${utils.escapeHtml(kind)}">
                ${cardBody}
            </div>
            ${kbd}
        </div>
    `;
    return el;
}

export async function onChecklistTabShown() {
    await populateChecklistTemplateSelect();
    await loadRecentSubmissions();
    await renderCustomItemsList();
    await showRecoveryIfNeeded();
    if (!state || !state.def) {
        try {
            await loadDefinition();
        } catch (e) {
            console.error(e);
            return;
        }
    }
    if (state.extraIndex !== null && state.extraIndex >= 0) {
        renderExtraItem();
        return;
    }
    if (!state.currentId) {
        startWizard();
        return;
    }
    renderWizard();
}

function renderWizard() {
    const el = document.getElementById('checklistWizard');
    if (!el || !state || !state.def) return;

    const node = state.def.nodes[state.currentId];
    if (!node) {
        el.innerHTML = '<p class="checklist-error">Missing question in checklist definition.</p>';
        return;
    }

    if (node.type === 'text') {
        const ph = node.placeholder ? utils.escapeHtml(node.placeholder) : '';
        paintWizard(
            `
                <p class="checklist-q">${utils.escapeHtml(node.question)}</p>
                <textarea class="checklist-textarea checklist-flow-text" rows="4" placeholder="${ph}" id="checklistTextInput"></textarea>
                <button type="button" class="btn-primary checklist-next">Continue</button>
            `,
            { kind: 'text' },
        );
        el.querySelector('.checklist-next').addEventListener('click', () => {
            const text = (el.querySelector('#checklistTextInput')?.value || '').trim();
            if (!text && !node.optional) {
                utils.showErrorFeedback('Please enter a response.');
                return;
            }
            state.answers[state.currentId] = text;
            goTo(node.next || 'end');
        });
        return;
    }

    if (node.type === 'scale') {
        const min = node.min ?? 1;
        const max = node.max ?? 5;
        let buttons = '';
        for (let v = min; v <= max; v++) {
            buttons += `<button type="button" class="btn-secondary checklist-scale-btn" data-value="${v}">${v}</button>`;
        }
        paintWizard(
            `
                <p class="checklist-q">${utils.escapeHtml(node.question)}</p>
                <div class="checklist-scale-row">${buttons}</div>
            `,
            { kind: 'scale', kbdHint: scaleKbdHint(min, max) },
        );
        el.querySelectorAll('.checklist-scale-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                state.answers[state.currentId] = parseInt(btn.getAttribute('data-value'), 10);
                goTo(node.next || 'end');
            });
        });
        return;
    }

    if (node.type === 'number') {
        const min = node.min ?? 0;
        const max = node.max ?? 999;
        const step = node.step ?? 1;
        paintWizard(
            `
                <p class="checklist-q">${utils.escapeHtml(node.question)}</p>
                <input type="number" class="checklist-text-input" id="checklistNumberInput" min="${min}" max="${max}" step="${step}" placeholder="${node.optional ? 'Optional' : ''}">
                <button type="button" class="btn-primary checklist-next">Continue</button>
            `,
            { kind: 'number' },
        );
        el.querySelector('.checklist-next').addEventListener('click', () => {
            const raw = el.querySelector('#checklistNumberInput')?.value.trim() || '';
            if (!raw) {
                if (node.optional) {
                    state.answers[state.currentId] = null;
                    goTo(node.next || 'end');
                    return;
                }
                utils.showErrorFeedback('Enter a number.');
                return;
            }
            const n = parseFloat(raw);
            if (Number.isNaN(n) || n < min || n > max) {
                utils.showErrorFeedback(`Enter a number between ${min} and ${max}.`);
                return;
            }
            state.answers[state.currentId] = n;
            goTo(node.next || 'end');
        });
        return;
    }

    if (node.type === 'yes_no') {
        paintWizard(
            `
                <p class="checklist-q">${utils.escapeHtml(node.question)}</p>
                <div class="checklist-yesno">
                    <button type="button" class="btn-primary checklist-yes">Yes</button>
                    <button type="button" class="btn-secondary checklist-no">No</button>
                </div>
            `,
            { kind: 'yes_no' },
        );
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
                <input type="text" class="checklist-other-input" id="checklistOtherText" placeholder="Describe..." autocomplete="off">
            `;
        }
        paintWizard(
            `
                <p class="checklist-q">${utils.escapeHtml(node.question)}</p>
                <div class="checklist-options">${radios}${otherBlock}</div>
                <button type="button" class="btn-primary checklist-next">Continue</button>
            `,
            { kind: 'choice' },
        );
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
                    utils.showErrorFeedback('Please add a short description.');
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
        void finishMainFlow();
        return;
    }
    state.currentId = nextId;
    renderWizard();
}

async function finishMainFlow() {
    await refreshCustomItems();
    const items = state.customItems || [];
    if (items.length > 0) {
        state.extraIndex = 0;
        renderExtraItem();
        return;
    }
    await completeFlow();
}

/**
 * @param {object} partial - { type: 'yes_no', answer: boolean } | { type: 'choice', value, otherText? }
 * @param {number | null} durationMinutes - null if user left blank
 */
function applyDurationAndAdvance(item, partial, durationMinutes) {
    if (partial.type === 'yes_no') {
        const o = { answer: partial.answer };
        if (durationMinutes !== null) {
            o.durationMinutes = durationMinutes;
        }
        state.answers[item.id] = o;
    } else {
        const o =
            partial.value === 'other'
                ? { value: 'other', otherText: partial.otherText }
                : { value: partial.value };
        if (durationMinutes !== null) {
            o.durationMinutes = durationMinutes;
        }
        state.answers[item.id] = o;
    }
    advanceExtra();
}

/**
 * Second step after answering when item.trackDuration is true.
 */
function showDurationStep(item, partial) {
    const el = document.getElementById('checklistWizard');
    if (!el || !state) return;

    const items = state.customItems || [];
    const i = state.extraIndex;
    const total = items.length;

    let recap = '';
    if (partial.type === 'yes_no') {
        recap = partial.answer ? 'Yes' : 'No';
    } else if (partial.value === 'other') {
        recap = `Other (${partial.otherText})`;
    } else {
        const opt = item.options.find((o) => o.value === partial.value);
        recap = opt ? opt.label : String(partial.value);
    }

    paintWizard(
        `
            <p class="checklist-q">${utils.escapeHtml(item.question)}</p>
            <p class="duration-recap">Your answer: <strong>${utils.escapeHtml(recap)}</strong></p>
            <label class="checklist-field-label" for="extraDurMinutes">Duration (minutes)</label>
            <input type="number" id="extraDurMinutes" class="checklist-text-input duration-input" min="0" step="1" placeholder="Optional">
            <div class="checklist-duration-actions">
                <button type="button" class="btn-primary duration-continue">Continue</button>
            </div>
        `,
        { kind: 'duration', extraTag: `Extra question ${i + 1} of ${total} · Duration` },
    );

    el.querySelector('.duration-continue').addEventListener('click', () => {
        const raw = el.querySelector('#extraDurMinutes').value.trim();
        let dm = null;
        if (raw !== '') {
            const n = parseInt(raw, 10);
            if (Number.isNaN(n) || n < 0) {
                utils.showErrorFeedback('Enter a valid number of minutes, or leave blank.');
                return;
            }
            dm = n;
        }
        applyDurationAndAdvance(item, partial, dm);
    });
}

function renderExtraItem() {
    const el = document.getElementById('checklistWizard');
    if (!el || !state) return;

    const items = state.customItems || [];
    const i = state.extraIndex;
    if (i === null || i >= items.length) {
        void completeFlow();
        return;
    }

    const item = items[i];

    if (item.type === 'yes_no') {
        paintWizard(
            `
                <p class="checklist-q">${utils.escapeHtml(item.question)}</p>
                <div class="checklist-yesno">
                    <button type="button" class="btn-primary extra-yes">Yes</button>
                    <button type="button" class="btn-secondary extra-no">No</button>
                </div>
            `,
            { kind: 'yes_no', extraTag: `Extra question ${i + 1} of ${items.length}` },
        );
        el.querySelector('.extra-yes').addEventListener('click', () => {
            if (item.trackDuration) {
                showDurationStep(item, { type: 'yes_no', answer: true });
            } else {
                state.answers[item.id] = true;
                advanceExtra();
            }
        });
        el.querySelector('.extra-no').addEventListener('click', () => {
            if (item.trackDuration) {
                showDurationStep(item, { type: 'yes_no', answer: false });
            } else {
                state.answers[item.id] = false;
                advanceExtra();
            }
        });
        return;
    }

    if (item.type === 'choice') {
        let radios = '';
        item.options.forEach((opt, j) => {
            radios += `
                <label class="checklist-option">
                    <input type="radio" name="extraChoice" value="${j}">
                    <span>${utils.escapeHtml(opt.label)}</span>
                </label>
            `;
        });
        let otherBlock = '';
        if (item.allowOther) {
            otherBlock = `
                <label class="checklist-option">
                    <input type="radio" name="extraChoice" value="other">
                    <span>Other</span>
                </label>
                <input type="text" class="checklist-other-input" id="extraOtherText" placeholder="Describe..." autocomplete="off">
            `;
        }
        paintWizard(
            `
                <p class="checklist-q">${utils.escapeHtml(item.question)}</p>
                <div class="checklist-options">${radios}${otherBlock}</div>
                <button type="button" class="btn-primary extra-next">Continue</button>
            `,
            { kind: 'choice', extraTag: `Extra question ${i + 1} of ${items.length}` },
        );
        const otherInput = el.querySelector('#extraOtherText');
        if (otherInput) {
            el.querySelectorAll('input[name="extraChoice"]').forEach((r) => {
                r.addEventListener('change', () => {
                    const show = r.value === 'other' && r.checked;
                    otherInput.style.display = show ? 'block' : 'none';
                    if (!show) otherInput.value = '';
                });
            });
            otherInput.style.display = 'none';
        }
        el.querySelector('.extra-next').addEventListener('click', () => {
            const selected = el.querySelector('input[name="extraChoice"]:checked');
            if (!selected) {
                utils.showErrorFeedback('Choose an option.');
                return;
            }
            const idx = selected.value;
            if (idx === 'other') {
                const text = (otherInput && otherInput.value.trim()) || '';
                if (!text) {
                    utils.showErrorFeedback('Please add a short description.');
                    return;
                }
                if (item.trackDuration) {
                    showDurationStep(item, { type: 'choice', value: 'other', otherText: text });
                } else {
                    state.answers[item.id] = { value: 'other', otherText: text };
                    advanceExtra();
                }
                return;
            }
            const opt = item.options[parseInt(idx, 10)];
            if (!opt) return;
            if (item.trackDuration) {
                showDurationStep(item, { type: 'choice', value: opt.value });
            } else {
                state.answers[item.id] = { value: opt.value };
                advanceExtra();
            }
        });
        return;
    }

    if (item.type === 'text') {
        paintWizard(
            `
                <p class="checklist-q">${utils.escapeHtml(item.question)}</p>
                <textarea class="checklist-textarea checklist-flow-text" rows="3" id="extraTextInput"></textarea>
                <button type="button" class="btn-primary extra-next">Continue</button>
            `,
            { kind: 'text', extraTag: `Extra question ${i + 1} of ${items.length}` },
        );
        el.querySelector('.extra-next').addEventListener('click', () => {
            const text = el.querySelector('#extraTextInput')?.value.trim() || '';
            if (!text && !item.optional) {
                utils.showErrorFeedback('Please enter a response.');
                return;
            }
            state.answers[item.id] = text;
            advanceExtra();
        });
        return;
    }

    if (item.type === 'scale') {
        const min = item.min ?? 1;
        const max = item.max ?? 5;
        let buttons = '';
        for (let v = min; v <= max; v++) {
            buttons += `<button type="button" class="btn-secondary checklist-scale-btn" data-value="${v}">${v}</button>`;
        }
        paintWizard(
            `
                <p class="checklist-q">${utils.escapeHtml(item.question)}</p>
                <div class="checklist-scale-row">${buttons}</div>
            `,
            { kind: 'scale', extraTag: `Extra question ${i + 1} of ${items.length}`, kbdHint: scaleKbdHint(min, max) },
        );
        el.querySelectorAll('.checklist-scale-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                state.answers[item.id] = parseInt(btn.getAttribute('data-value'), 10);
                advanceExtra();
            });
        });
        return;
    }

    if (item.type === 'number') {
        const min = item.min ?? 0;
        const max = item.max ?? 999;
        const step = item.step ?? 1;
        paintWizard(
            `
                <p class="checklist-q">${utils.escapeHtml(item.question)}</p>
                <input type="number" class="checklist-text-input" id="extraNumberInput" min="${min}" max="${max}" step="${step}">
                <button type="button" class="btn-primary extra-next">Continue</button>
            `,
            { kind: 'number', extraTag: `Extra question ${i + 1} of ${items.length}` },
        );
        el.querySelector('.extra-next').addEventListener('click', () => {
            const raw = el.querySelector('#extraNumberInput')?.value.trim() || '';
            if (!raw) {
                if (item.optional) {
                    state.answers[item.id] = null;
                    advanceExtra();
                    return;
                }
                utils.showErrorFeedback('Enter a number.');
                return;
            }
            const n = parseFloat(raw);
            if (Number.isNaN(n) || n < min || n > max) {
                utils.showErrorFeedback(`Enter a number between ${min} and ${max}.`);
                return;
            }
            state.answers[item.id] = n;
            advanceExtra();
        });
    }
}

function advanceExtra() {
    state.extraIndex++;
    const items = state.customItems || [];
    if (state.extraIndex >= items.length) {
        state.extraIndex = null;
        void completeFlow();
        return;
    }
    renderExtraItem();
}

async function completeFlow() {
    try {
        const id = state.def.id;
        const version = state.def.version;
        const answers = { ...state.answers };
        await eel.submit_daily_checklist_response(id, version, answers)();
        utils.showSuccessFeedback('Saved to your local database.');
        utils.notifyDataChanged();
        await loadRecentSubmissions();
    } catch (e) {
        console.error(e);
        utils.showErrorFeedback('Could not save. Try again.');
        return;
    }
    startWizard();
}

async function showRecoveryIfNeeded() {
    const panel = document.getElementById('recoveryPanel');
    if (!panel) return;
    try {
        const data = await eel.get_pending_recovery()();
        if (!data.pending) {
            panel.classList.add('is-hidden');
            panel.innerHTML = '';
            return;
        }
        panel.classList.remove('is-hidden');
        let options = '';
        (data.options || []).forEach((opt) => {
            options += `<button type="button" class="btn-secondary recovery-option" data-value="${utils.escapeHtml(opt.value)}">${utils.escapeHtml(opt.label)}</button>`;
        });
        panel.innerHTML = `
            <div class="recovery-card">
                <h3>Missed check-in: ${utils.escapeHtml(data.missed_date)}</h3>
                <p class="checklist-q">${utils.escapeHtml(data.question)}</p>
                <div class="recovery-options">${options}</div>
            </div>
        `;
        panel.querySelectorAll('.recovery-option').forEach((btn) => {
            btn.addEventListener('click', async () => {
                try {
                    await eel.submit_recovery_response(data.missed_date, btn.getAttribute('data-value'))();
                    utils.showSuccessFeedback('Thanks — logged.');
                    utils.notifyDataChanged();
                    await showRecoveryIfNeeded();
                } catch (e) {
                    utils.showErrorFeedback('Could not save.');
                }
            });
        });
    } catch (e) {
        console.error(e);
    }
}

function fallbackFormatted(answers) {
    return Object.entries(answers || {}).map(([key, val]) => {
        const node = nodeForAnswerKey(key);
        return {
            label: node.question || String(key).replace(/[_-]+/g, ' '),
            value: formatPreviewValue(node, val),
        };
    });
}

async function loadRecentSubmissions() {
    const listEl = document.getElementById('checklistRecentList');
    if (!listEl) return;
    listEl.innerHTML = '<div class="empty-state empty-state--loading"><div class="loading-spinner"></div><p>Loading…</p></div>';
    try {
        const rows = await eel.list_daily_checklist_submissions(30)();
        if (!rows.length) {
            listEl.innerHTML = `
                <div class="empty-state empty-state--message empty-state--compact">
                    <h3>No submissions yet</h3>
                    <p>Complete the checklist above to see history here.</p>
                </div>
            `;
            return;
        }
        let html = '';
        rows.forEach((row) => {
            const when = new Date(row.created_at).toLocaleString();
            const title = row.title || 'Checklist';
            const formatted = row.answers_formatted?.length
                ? row.answers_formatted
                : fallbackFormatted(row.answers);
            const summary = row.summary || formatted
                .slice(0, 3)
                .map((a) => `${a.label}: ${a.value}`)
                .join(' · ');
            const qa = formatted
                .map(
                    (a) =>
                        `<tr><th>${utils.escapeHtml(a.label)}</th><td>${utils.escapeHtml(a.value)}</td></tr>`,
                )
                .join('');
            html += `
                <article class="checklist-history-item">
                    <div class="checklist-history-meta">
                        <strong>${utils.escapeHtml(title)}</strong>
                        <span>${utils.escapeHtml(when)}</span>
                    </div>
                    ${summary ? `<p class="checklist-history-summary">${utils.escapeHtml(summary)}</p>` : ''}
                    <table class="timeline-answers checklist-history-qa"><tbody>${qa}</tbody></table>
                </article>
            `;
        });
        listEl.innerHTML = html;
    } catch (e) {
        console.error(e);
        listEl.innerHTML = '<p class="checklist-error">Could not load history.</p>';
    }
}
