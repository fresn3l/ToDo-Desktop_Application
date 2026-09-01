/**
 * Word of the day — German or precise English, stable for the local date.
 */

import * as utils from './utils.js';

function languageChip(word) {
    const lang = word.language_label || (word.language === 'de' ? 'German' : 'English');
    const pos = word.pos ? ` · ${word.pos}` : '';
    return `${lang}${pos}`;
}

function paintWord(word) {
    const root = document.getElementById('wordCard');
    if (!root) return;
    if (!word || !word.word) {
        root.innerHTML = `
            <p class="today-kicker">Word of the day</p>
            <p class="checklist-hint small">Could not load today’s word.</p>`;
        return;
    }
    const used = (word.used_tonight || '').trim();
    const usedBlock = used
        ? `<p class="word-used"><span class="word-used-label">Used tonight</span> ${utils.escapeHtml(used)}</p>`
        : `<p class="word-evening-hint">Evening check-in will ask you to use this word.</p>
           <button type="button" class="btn-ghost word-evening-btn" id="wordEveningBtn">Open Evening check-in</button>`;
    root.innerHTML = `
        <p class="today-kicker">Word of the day</p>
        <h2 class="word-head">${utils.escapeHtml(word.display || word.word)}</h2>
        <p class="word-chip">${utils.escapeHtml(languageChip(word))}</p>
        <p class="word-meaning">${utils.escapeHtml(word.meaning || '')}</p>
        ${word.example ? `<p class="word-example">${utils.escapeHtml(word.example)}</p>` : ''}
        ${usedBlock}
    `;
    document.getElementById('wordEveningBtn')?.addEventListener('click', () => {
        document.dispatchEvent(new CustomEvent('kosistenz:open-evening-checkin'));
    });
}

export async function refreshWord() {
    const root = document.getElementById('wordCard');
    if (!root) return;
    if (typeof eel === 'undefined' || !eel.get_word_of_the_day) {
        paintWord(null);
        return;
    }
    try {
        paintWord(await eel.get_word_of_the_day()());
    } catch (err) {
        console.error(err);
        paintWord(null);
    }
}

export function setupWord() {
    document.addEventListener('kosistenz:data-changed', () => {
        if (document.getElementById('wordTab')?.closest('.home-widget-body')) {
            void refreshWord();
        }
    });
}

export async function onWordTabShown() {
    await refreshWord();
}
