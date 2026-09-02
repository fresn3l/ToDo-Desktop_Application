/**
 * Currently reading — book, page, pages today, reading journal.
 */

import * as utils from './utils.js';

function paint(data) {
    const title = document.getElementById('readingTitle');
    const page = document.getElementById('readingPage');
    const todayEl = document.getElementById('readingPagesToday');
    const summary = document.getElementById('readingSummary');
    if (title && document.activeElement !== title) title.value = data?.title || '';
    if (page && document.activeElement !== page) page.value = data?.page ? String(data.page) : '';
    if (todayEl) todayEl.textContent = String(data?.pages_today || 0);
    if (summary) {
        summary.textContent = data?.title
            ? `${data.title} · page ${data.page || 0}`
            : 'No book yet.';
    }
}

export async function refreshReading() {
    if (typeof eel === 'undefined' || !eel.get_reading) return;
    try {
        paint(await eel.get_reading()());
    } catch (err) {
        console.error(err);
    }
}

export function setupReading() {
    const root = document.getElementById('readingSource');
    if (!root || root.dataset.ready === '1') return;
    root.dataset.ready = '1';
    document.getElementById('readingBookForm')?.addEventListener('submit', async (event) => {
        event.preventDefault();
        try {
            paint(await eel.set_reading_book(
                document.getElementById('readingTitle')?.value || '',
                document.getElementById('readingPage')?.value || 0,
            )());
            utils.notifyDataChanged();
            utils.showSuccessFeedback('Book saved.');
        } catch (err) {
            console.error(err);
            utils.showErrorFeedback(err?.message || 'Could not save the book.');
        }
    });
    root.querySelectorAll('[data-pages]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            try {
                paint(await eel.add_reading_pages(parseInt(btn.getAttribute('data-pages') || '1', 10))());
                utils.notifyDataChanged();
            } catch (err) {
                console.error(err);
                utils.showErrorFeedback(err?.message || 'Name the book first.');
            }
        });
    });
    document.getElementById('readingJournalForm')?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const note = document.getElementById('readingNote');
        try {
            const result = await eel.save_reading_journal(note?.value || '')();
            paint(result.reading);
            if (note) note.value = '';
            utils.notifyDataChanged();
            utils.showSuccessFeedback('Reading journal saved.');
        } catch (err) {
            console.error(err);
            utils.showErrorFeedback(err?.message || 'Could not save that note.');
        }
    });
}
