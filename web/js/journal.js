/**
 * Journal Module
 * 
 * Handles journal functionality including timer and entry management
 */

import * as utils from './utils.js';

// ============================================
// JOURNAL STATE
// ============================================

let journalTimer = null;
let journalTimerSeconds = 600; // 10 minutes in seconds
let journalTimerRunning = false;
let journalTimerPaused = false;
let journalStartTime = null;
let journalDuration = 0;

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
            if (!journalTimerRunning && !journalTimerPaused && entryTextarea.value.trim().length > 0) {
                startJournalTimer();
            }
        });
    }
}

// ============================================
// TIMER FUNCTIONS
// ============================================

/**
 * Start the 10-minute journal timer
 */
function startJournalTimer() {
    if (journalTimerRunning) return;
    
    journalTimerRunning = true;
    journalTimerPaused = false;
    journalStartTime = Date.now();
    journalDuration = 0;
    
    const startBtn = document.getElementById('startTimer');
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const statusEl = document.getElementById('timerStatus');
    const saveBtn = document.getElementById('saveEntry');
    
    if (startBtn) startBtn.style.display = 'none';
    if (pauseBtn) pauseBtn.style.display = 'inline-block';
    if (continueBtn) continueBtn.style.display = 'none';
    if (statusEl) statusEl.textContent = 'Timer running...';
    if (saveBtn) saveBtn.disabled = false;
    
    journalTimer = setInterval(() => {
        journalTimerSeconds--;
        journalDuration++;
        updateTimerDisplay();
        
        if (journalTimerSeconds <= 0) {
            timerComplete();
        }
    }, 1000);
}

/**
 * Pause the timer
 */
function pauseJournalTimer() {
    if (!journalTimerRunning) return;
    
    clearInterval(journalTimer);
    journalTimerRunning = false;
    journalTimerPaused = true;
    
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const statusEl = document.getElementById('timerStatus');
    
    if (pauseBtn) pauseBtn.style.display = 'none';
    if (continueBtn) continueBtn.style.display = 'inline-block';
    if (statusEl) statusEl.textContent = 'Timer paused';
}

/**
 * Continue the timer after pause
 */
function continueJournalTimer() {
    if (!journalTimerPaused) return;
    
    journalTimerRunning = true;
    journalTimerPaused = false;
    
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const statusEl = document.getElementById('timerStatus');
    
    if (pauseBtn) pauseBtn.style.display = 'inline-block';
    if (continueBtn) continueBtn.style.display = 'none';
    if (statusEl) statusEl.textContent = 'Timer running...';
    
    journalTimer = setInterval(() => {
        journalTimerSeconds--;
        journalDuration++;
        updateTimerDisplay();
        
        if (journalTimerSeconds <= 0) {
            timerComplete();
        }
    }, 1000);
}

/**
 * Update timer display
 */
function updateTimerDisplay() {
    const minutes = Math.floor(journalTimerSeconds / 60);
    const seconds = journalTimerSeconds % 60;
    const display = document.getElementById('timerDisplay');
    
    if (display) {
        display.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
}

/**
 * Handle timer completion
 */
function timerComplete() {
    clearInterval(journalTimer);
    journalTimerRunning = false;
    
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const statusEl = document.getElementById('timerStatus');
    
    if (pauseBtn) pauseBtn.style.display = 'none';
    if (continueBtn) continueBtn.style.display = 'inline-block';
    if (statusEl) statusEl.textContent = 'Timer complete! Click "Continue" to keep writing.';
    
    utils.showSuccessFeedback('10 minutes complete! You can continue writing or save your entry.');
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
        await eel.save_journal_entry(content, journalDuration, continued)();
        
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
    journalTimerSeconds = 600;
    journalTimerRunning = false;
    journalTimerPaused = false;
    journalStartTime = null;
    journalDuration = 0;
    
    const startBtn = document.getElementById('startTimer');
    const pauseBtn = document.getElementById('pauseTimer');
    const continueBtn = document.getElementById('continueTimer');
    const statusEl = document.getElementById('timerStatus');
    const saveBtn = document.getElementById('saveEntry');
    
    if (startBtn) startBtn.style.display = 'inline-block';
    if (pauseBtn) pauseBtn.style.display = 'none';
    if (continueBtn) continueBtn.style.display = 'none';
    if (statusEl) statusEl.textContent = 'Ready to start';
    if (saveBtn) saveBtn.disabled = true;
    
    updateTimerDisplay();
}

/**
 * Load past journal entries (last 30 days)
 */
export async function loadPastEntries() {
    const container = document.getElementById('journalEntriesContainer');
    if (!container) return;
    
    try {
        container.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><p>Loading entries...</p></div>';
        
        const entries = await eel.get_recent_entries(30)();
        
        if (entries.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>No entries yet</h3>
                    <p>Start writing your first journal entry above!</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        entries.forEach(entry => {
            const date = new Date(entry.date || entry.created_at);
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
            
            html += `
                <div class="journal-entry-item">
                    <div class="journal-entry-header">
                        <span class="journal-entry-date">${utils.escapeHtml(dateStr)}</span>
                        ${durationStr ? `<span class="journal-entry-duration">⏱ ${durationStr}</span>` : ''}
                        ${continuedBadge}
                    </div>
                    <div class="journal-entry-content">${utils.escapeHtml(entry.content)}</div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading past entries:', error);
        container.innerHTML = `
            <div class="empty-state">
                <h3>Error loading entries</h3>
                <p>Please try again later.</p>
            </div>
        `;
    }
}

