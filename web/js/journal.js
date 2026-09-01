/**
 * Journal Module
 * 
 * Handles journal functionality including timer and entry management
 */

import * as utils from './utils.js';
import { getAppearance, onAppearanceChange } from './appearance.js';

// ============================================
// JOURNAL STATE
// ============================================

let journalTimer = null;
let journalTimerSeconds = 600;
let journalTimerRunning = false;
let journalTimerPaused = false;
let journalOvertime = false;
let journalDuration = 0;
let journalCache = [];
let expandedEntryId = null;
let journalSearchQuery = '';
let journalTagFilter = '';
let focusMode = false;

function timerDurationSeconds() {
    const minutes = getAppearance().timerMinutes || 10;
    return minutes * 60;
}

function setTimerButtonVisibility({ showStart, showPause, showContinue }) {
    const startBtn = document.getElementById('startTimer');
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    if (startBtn) startBtn.classList.toggle('is-hidden', !showStart);
    if (pauseBtn) pauseBtn.classList.toggle('is-hidden', !showPause);
    if (continueBtn) continueBtn.classList.toggle('is-hidden', !showContinue);
}

// ============================================
// JOURNAL INITIALIZATION
// ============================================

/**
 * Initialize journal functionality
 */
export function setupJournal() {
    const startBtn = document.getElementById('startTimer');
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const saveBtn = document.getElementById('saveEntry');
    const clearBtn = document.getElementById('clearEntry');
    const entryTextarea = document.getElementById('journalEntry');
    
    if (startBtn) {
        startBtn.addEventListener('click', startJournalTimer);
    }
    if (pauseBtn) {
        pauseBtn.addEventListener('click', pauseJournalTimer);
    }
    if (continueBtn) {
        continueBtn.addEventListener('click', continueJournalTimer);
    }
    if (saveBtn) {
        saveBtn.addEventListener('click', saveJournalEntry);
    }
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (hasJournalDraft() && !window.confirm('Clear this journal entry and reset the timer?')) {
                return;
            }
            clearJournalEntry();
        });
    }
    if (entryTextarea) {
        entryTextarea.addEventListener('input', () => {
            updateWordCount();
            if (!journalTimerRunning && !journalTimerPaused && entryTextarea.value.trim().length > 0) {
                startJournalTimer();
            }
        });
    }

    document.getElementById('journalFocusBtn')?.addEventListener('click', () => {
        setJournalFocus(!focusMode);
    });
    document.getElementById('journalSearch')?.addEventListener('input', (e) => {
        journalSearchQuery = e.target.value.trim().toLowerCase();
        renderJournalHistory();
    });
    document.getElementById('journalTagFilter')?.addEventListener('change', (e) => {
        journalTagFilter = e.target.value;
        renderJournalHistory();
    });

    setupJournalKeys();
    journalTimerSeconds = timerDurationSeconds();
    updateTimerDisplay();
    updateWordCount();
    onAppearanceChange((settings) => {
        if (!journalTimerRunning && !journalTimerPaused) {
            journalTimerSeconds = (settings.timerMinutes || 10) * 60;
            updateTimerDisplay();
        }
    });
    void loadJournalTagPresets();
}

export function beginNewJournalEntry(seedText) {
    const textarea = document.getElementById('journalEntry');
    if (!textarea) return;
    if (typeof seedText === 'string' && seedText.trim()) {
        const current = textarea.value;
        textarea.value = current && !current.endsWith('\n') && current.length ? `${current}\n${seedText}` : `${current}${seedText}`;
        updateWordCount();
        if (textarea.value.trim().length > 0 && !journalTimerRunning && !journalTimerPaused) {
            startJournalTimer();
        }
    }
    textarea.focus();
}

function updateWordCount() {
    const el = document.getElementById('journalWordCount');
    const textarea = document.getElementById('journalEntry');
    if (!el || !textarea) return;
    const text = textarea.value.trim();
    const words = text ? text.split(/\s+/).length : 0;
    el.textContent = words === 1 ? '1 word' : `${words} words`;
}

async function loadJournalTagPresets() {
    const container = document.getElementById('journalTagPresets');
    if (!container) return;
    try {
        const presets = await eel.get_journal_tag_presets()();
        container.innerHTML = presets
            .map(
                (t) =>
                    `<label class="journal-tag-preset"><input type="checkbox" name="journalTag" value="${utils.escapeHtml(t)}"> #${utils.escapeHtml(t)}</label>`,
            )
            .join('');
    } catch (e) {
        console.error(e);
    }
}

function collectJournalTags() {
    const checked = Array.from(document.querySelectorAll('input[name="journalTag"]:checked')).map(
        (el) => el.value,
    );
    const custom = document.getElementById('journalCustomTags')?.value || '';
    const extra = custom
        .split(',')
        .map((s) => s.trim().replace(/^#/, ''))
        .filter(Boolean);
    return [...checked, ...extra];
}

// ============================================
// TIMER FUNCTIONS
// ============================================

/**
 * Start the 10-minute journal timer
 */
function startJournalTimer() {
    if (journalTimerRunning) return;
    if (journalTimerPaused || journalOvertime) {
        continueJournalTimer();
        return;
    }

    journalTimerRunning = true;
    journalTimerPaused = false;
    journalOvertime = false;
    journalDuration = 0;
    journalTimerSeconds = timerDurationSeconds();

    const statusEl = document.getElementById('timerStatus');
    const saveBtn = document.getElementById('saveEntry');

    setTimerButtonVisibility({ showStart: false, showPause: true, showContinue: false });
    if (statusEl) statusEl.textContent = 'Timer running...';
    if (saveBtn) saveBtn.disabled = false;

    journalTimer = setInterval(tickJournalTimer, 1000);
    if (getAppearance().autoFocus) {
        setJournalFocus(true);
    }
}

function tickJournalTimer() {
    journalDuration++;
    if (journalOvertime) {
        updateTimerDisplay();
        return;
    }
    if (journalTimerSeconds > 0) {
        journalTimerSeconds--;
    }
    updateTimerDisplay();
    if (journalTimerSeconds <= 0) {
        timerComplete();
    }
}

/**
 * Pause the timer
 */
function pauseJournalTimer() {
    if (!journalTimerRunning) return;
    
    clearInterval(journalTimer);
    journalTimerRunning = false;
    journalTimerPaused = true;
    
    const statusEl = document.getElementById('timerStatus');

    setTimerButtonVisibility({ showStart: false, showPause: false, showContinue: true });
    if (statusEl) statusEl.textContent = 'Timer paused';
}

/**
 * Continue the timer after pause
 */
function continueJournalTimer() {
    if (!journalTimerPaused) return;

    journalTimerRunning = true;
    journalTimerPaused = false;

    const statusEl = document.getElementById('timerStatus');

    setTimerButtonVisibility({ showStart: false, showPause: true, showContinue: false });
    if (statusEl) {
        statusEl.textContent = journalOvertime ? 'Continuing past the timer…' : 'Timer running...';
    }

    journalTimer = setInterval(tickJournalTimer, 1000);
    if (getAppearance().autoFocus) {
        setJournalFocus(true);
    }
}

/**
 * Update timer display
 */
function updateTimerDisplay() {
    const display = document.getElementById('timerDisplay');
    if (!display) return;

    if (journalOvertime) {
        const extra = Math.max(0, journalDuration - timerDurationSeconds());
        const minutes = Math.floor(extra / 60);
        const seconds = extra % 60;
        display.textContent = `+${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        return;
    }

    const minutes = Math.floor(Math.max(0, journalTimerSeconds) / 60);
    const seconds = Math.max(0, journalTimerSeconds) % 60;
    display.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * Handle timer completion
 */
function timerComplete() {
    clearInterval(journalTimer);
    journalTimerRunning = false;
    journalTimerPaused = true;
    journalOvertime = true;
    journalTimerSeconds = 0;

    const statusEl = document.getElementById('timerStatus');

    setTimerButtonVisibility({ showStart: false, showPause: false, showContinue: true });
    if (statusEl) statusEl.textContent = 'Timer complete! Click "Continue" to keep writing.';
    updateTimerDisplay();
    
    const minutes = getAppearance().timerMinutes || 10;
    utils.showSuccessFeedback(`${minutes} minutes complete! You can continue writing or save your entry.`);
}

// ============================================
// JOURNAL ENTRY FUNCTIONS
// ============================================

/**
 * Save journal entry
 */
async function saveJournalEntry() {
    const entryTextarea = document.getElementById('journalEntry');
    const content = entryTextarea ? entryTextarea.value.trim() : '';
    
    if (!content) {
        utils.showErrorFeedback('Please write something before saving.');
        return;
    }
    
    try {
        const continued = journalOvertime || journalDuration > timerDurationSeconds();
        const tags = collectJournalTags();
        await eel.save_journal_entry(content, journalDuration, continued, tags)();
        
        utils.showSuccessFeedback('Journal entry saved successfully!');
        
        clearJournalEntry();
        
        await loadPastEntries();
        setJournalFocus(false);
        utils.notifyDataChanged();
    } catch (error) {
        console.error('Error saving journal entry:', error);
        utils.showErrorFeedback('Failed to save entry. Please try again.');
    }
}

/**
 * Clear journal entry
 */
function clearJournalEntry() {
    const entryTextarea = document.getElementById('journalEntry');
    if (entryTextarea) {
        entryTextarea.value = '';
    }
    
    clearInterval(journalTimer);
    journalTimer = null;
    journalTimerSeconds = timerDurationSeconds();
    journalTimerRunning = false;
    journalTimerPaused = false;
    journalOvertime = false;
    journalDuration = 0;
    
    const statusEl = document.getElementById('timerStatus');
    const saveBtn = document.getElementById('saveEntry');

    document.querySelectorAll('input[name="journalTag"]').forEach((cb) => {
        cb.checked = false;
    });
    const customTags = document.getElementById('journalCustomTags');
    if (customTags) customTags.value = '';

    setTimerButtonVisibility({ showStart: true, showPause: false, showContinue: false });
    if (statusEl) statusEl.textContent = 'Ready to start';
    if (saveBtn) saveBtn.disabled = true;
    
    updateTimerDisplay();
    updateWordCount();
    setJournalFocus(false);
}

function hasJournalDraft() {
    const textarea = document.getElementById('journalEntry');
    return !!(textarea && textarea.value.trim()) || journalTimerRunning || journalTimerPaused;
}

export function setJournalFocus(on) {
    focusMode = !!on;
    document.documentElement.setAttribute('data-focus', focusMode ? 'on' : 'off');
    const btn = document.getElementById('journalFocusBtn');
    if (btn) {
        btn.textContent = focusMode ? 'Exit focus' : 'Focus';
        btn.setAttribute('aria-pressed', focusMode ? 'true' : 'false');
    }
}

export function exitJournalFocus() {
    setJournalFocus(false);
}

function setupJournalKeys() {
    if (document.body.dataset.journalKeys === '1') return;
    document.body.dataset.journalKeys = '1';
    document.addEventListener('keydown', (e) => {
        const tab = document.getElementById('journalTab');
        if (!tab || !tab.classList.contains('active')) return;

        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            e.preventDefault();
            saveJournalEntry();
            return;
        }

        if (e.key !== 'Escape') return;
        e.preventDefault();
        if (journalTimerRunning) {
            pauseJournalTimer();
            return;
        }
        const id = e.target && e.target.id;
        if (id === 'journalSearch' || id === 'journalTagFilter') return;
        if (hasJournalDraft()) {
            if (window.confirm('Clear this journal entry and reset the timer?')) {
                clearJournalEntry();
            }
        }
    });
}

/**
 * Load past journal entries (last 30 days)
 */
export async function loadPastEntries() {
    const container = document.getElementById('journalEntriesContainer');
    if (!container) return;

    try {
        container.innerHTML = '<div class="empty-state empty-state--loading"><div class="loading-spinner"></div><p>Loading entries...</p></div>';
        journalCache = await eel.get_recent_entries(30)();
        refreshJournalTagFilter();
        renderJournalHistory();
    } catch (error) {
        console.error('Error loading past entries:', error);
        container.innerHTML = `
            <div class="empty-state empty-state--message empty-state--compact">
                <h3>Error loading entries</h3>
                <p>Please try again later.</p>
            </div>
        `;
    }
}

function refreshJournalTagFilter() {
    const sel = document.getElementById('journalTagFilter');
    if (!sel) return;
    const current = journalTagFilter;
    const tags = new Set();
    journalCache.forEach((e) => (e.tags || []).forEach((t) => tags.add(t)));
    const options = ['<option value="">All tags</option>']
        .concat([...tags].sort().map((t) => `<option value="${utils.escapeHtml(t)}">#${utils.escapeHtml(t)}</option>`));
    sel.innerHTML = options.join('');
    if (current && [...tags].includes(current)) {
        sel.value = current;
        journalTagFilter = current;
    } else {
        sel.value = '';
        journalTagFilter = '';
    }
}

function entryLocalDate(entry) {
    const raw = entry.date || entry.created_at;
    const d = raw ? new Date(raw) : new Date();
    return utils.localISODate(d);
}

function filteredJournalEntries() {
    return journalCache.filter((entry) => {
        if (journalTagFilter && !(entry.tags || []).includes(journalTagFilter)) return false;
        if (!journalSearchQuery) return true;
        const hay = `${entry.content || ''} ${(entry.tags || []).join(' ')} ${entry.kind || ''}`.toLowerCase();
        return hay.includes(journalSearchQuery);
    });
}

function renderJournalHistory() {
    const container = document.getElementById('journalEntriesContainer');
    if (!container) return;
    const entries = filteredJournalEntries();

    if (!journalCache.length) {
        container.innerHTML = `
            <div class="empty-state empty-state--message empty-state--compact">
                <h3>No entries yet</h3>
                <p>Start writing your first journal entry above.</p>
            </div>
        `;
        return;
    }

    if (!entries.length) {
        container.innerHTML = `
            <div class="empty-state empty-state--message empty-state--compact">
                <h3>No matching entries</h3>
                <p>Try a different search or tag.</p>
            </div>
        `;
        return;
    }

    const groups = [];
    const map = new Map();
    entries.forEach((entry) => {
        const day = entryLocalDate(entry);
        if (!map.has(day)) {
            const group = { day, entries: [] };
            map.set(day, group);
            groups.push(group);
        }
        map.get(day).entries.push(entry);
    });

    const today = utils.localISODate();
    let html = '';
    groups.forEach((group) => {
        const dayDate = new Date(`${group.day}T12:00:00`);
        const label = group.day === today
            ? 'Today'
            : dayDate.toLocaleDateString('en-US', { weekday: 'short', month: 'long', day: 'numeric' });
        html += `
            <section class="journal-day-group">
                <header class="journal-day-header">
                    <h3>${utils.escapeHtml(label)}</h3>
                    <span>${group.entries.length} ${group.entries.length === 1 ? 'entry' : 'entries'}</span>
                </header>
                <div class="journal-day-list">
        `;
        group.entries.forEach((entry, idx) => {
            const id = String(entry.id || `${entry.date || group.day}-${idx}`);
            const rawDate = entry.date || entry.created_at;
            const date = new Date(rawDate);
            const timeStr = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
            const duration = entry.duration_seconds || 0;
            const durationStr = duration > 0
                ? `${Math.floor(duration / 60)}m ${duration % 60}s`
                : '';
            const continuedBadge = entry.continued ? '<span class="journal-badge continued">Continued</span>' : '';
            const tagsHtml = (entry.tags || [])
                .map((t) => `<span class="journal-tag">#${utils.escapeHtml(t)}</span>`)
                .join('');
            const preview = (entry.content || '').trim().replace(/\s+/g, ' ');
            const previewText = preview.length > 140 ? `${preview.slice(0, 137)}…` : preview;
            const open = expandedEntryId === id;
            const kind = entry.kind || 'journal';
            const kindBadge = kind === 'morning_brief'
                ? '<span class="journal-badge">Morning</span>'
                : kind === 'evening_review'
                    ? '<span class="journal-badge">Evening</span>'
                    : kind === 'reading'
                        ? '<span class="journal-badge">Reading</span>'
                        : '';
            html += `
                <article class="journal-entry-item ${open ? 'is-open' : ''}" data-entry-id="${utils.escapeHtml(id)}">
                    <button type="button" class="journal-entry-toggle">
                        <div class="journal-entry-header">
                            <time class="journal-entry-date">${utils.escapeHtml(timeStr)}</time>
                            ${durationStr ? `<span class="journal-entry-duration">${utils.escapeHtml(durationStr)}</span>` : ''}
                            ${kindBadge}
                            ${continuedBadge}
                        </div>
                        ${tagsHtml ? `<div class="journal-entry-tags">${tagsHtml}</div>` : ''}
                        <p class="journal-entry-preview">${utils.escapeHtml(previewText)}</p>
                    </button>
                    ${open ? `<div class="journal-entry-content">${utils.escapeHtml(entry.content || '')}</div>` : ''}
                </article>
            `;
        });
        html += '</div></section>';
    });

    container.innerHTML = html;
    container.querySelectorAll('.journal-entry-toggle').forEach((btn) => {
        btn.addEventListener('click', () => {
            const article = btn.closest('[data-entry-id]');
            const id = article?.getAttribute('data-entry-id');
            expandedEntryId = expandedEntryId === id ? null : id;
            renderJournalHistory();
        });
    });
}

