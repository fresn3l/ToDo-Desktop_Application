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
let journalStartTime = null;
let journalDuration = 0;

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
        clearBtn.addEventListener('click', clearJournalEntry);
    }
    if (entryTextarea) {
        entryTextarea.addEventListener('input', () => {
            updateWordCount();
            if (!journalTimerRunning && !journalTimerPaused && entryTextarea.value.trim().length > 0) {
                startJournalTimer();
            }
        });
    }
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
    journalStartTime = Date.now();
    journalDuration = 0;
    journalTimerSeconds = timerDurationSeconds();

    const statusEl = document.getElementById('timerStatus');
    const saveBtn = document.getElementById('saveEntry');

    setTimerButtonVisibility({ showStart: false, showPause: true, showContinue: false });
    if (statusEl) statusEl.textContent = 'Timer running...';
    if (saveBtn) saveBtn.disabled = false;

    journalTimer = setInterval(tickJournalTimer, 1000);
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
        const continued = journalTimerSeconds <= 0 && journalTimerPaused;
        const tags = collectJournalTags();
        await eel.save_journal_entry(content, journalDuration, continued, tags)();
        
        utils.showSuccessFeedback('Journal entry saved successfully!');
        
        clearJournalEntry();
        
        await loadPastEntries();
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
    journalStartTime = null;
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
}

/**
 * Load past journal entries (last 30 days)
 */
export async function loadPastEntries() {
    const container = document.getElementById('journalEntriesContainer');
    if (!container) return;
    
    try {
        container.innerHTML = '<div class="empty-state empty-state--loading"><div class="loading-spinner"></div><p>Loading entries...</p></div>';
        
        const entries = await eel.get_recent_entries(30)();
        
        if (entries.length === 0) {
            container.innerHTML = `
                <div class="empty-state empty-state--message empty-state--compact">
                    <h3>No entries yet</h3>
                    <p>Start writing your first journal entry above.</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        entries.forEach(entry => {
            const rawDate = entry.date || entry.created_at;
            const date = new Date(rawDate);
            const iso = typeof rawDate === 'string' ? rawDate : date.toISOString();
            const dateStr = date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            
            const duration = entry.duration_seconds || 0;
            const minutes = Math.floor(duration / 60);
            const seconds = duration % 60;
            const durationStr = duration > 0 ? `${minutes}m ${seconds}s` : '';
            
            const continuedBadge = entry.continued ? '<span class="journal-badge continued">Continued</span>' : '';
            const tagsHtml = (entry.tags || [])
                .map((t) => `<span class="journal-tag">#${utils.escapeHtml(t)}</span>`)
                .join('');
            
            html += `
                <article class="journal-entry-item">
                    <div class="journal-entry-header">
                        <time class="journal-entry-date" datetime="${utils.escapeHtml(iso)}">${utils.escapeHtml(dateStr)}</time>
                        ${durationStr ? `<span class="journal-entry-duration" aria-label="Time spent writing">${utils.escapeHtml(durationStr)}</span>` : ''}
                        ${continuedBadge}
                    </div>
                    ${tagsHtml ? `<div class="journal-entry-tags">${tagsHtml}</div>` : ''}
                    <div class="journal-entry-content">${utils.escapeHtml(entry.content)}</div>
                </article>
            `;
        });
        
        container.innerHTML = html;
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

