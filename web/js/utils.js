/**
 * Shared UI helpers.
 */

export function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

export function showSuccessFeedback(message) {
    const feedback = document.createElement('div');
    feedback.className = 'feedback feedback-success';
    feedback.textContent = message;

    document.body.appendChild(feedback);

    setTimeout(() => {
        feedback.classList.add('show');
    }, 10);

    setTimeout(() => {
        feedback.classList.remove('show');
        setTimeout(() => feedback.remove(), 300);
    }, 3000);
}

export function showErrorFeedback(message) {
    const feedback = document.createElement('div');
    feedback.className = 'feedback feedback-error';
    feedback.textContent = message;

    document.body.appendChild(feedback);

    setTimeout(() => {
        feedback.classList.add('show');
    }, 10);

    setTimeout(() => {
        feedback.classList.remove('show');
        setTimeout(() => feedback.remove(), 300);
    }, 3000);
}

export function notifyDataChanged() {
    document.dispatchEvent(new CustomEvent('kosistenz:data-changed'));
    try {
        window.webkit?.messageHandlers?.kosistenz?.postMessage({ type: 'status' });
    } catch (_) {
        /* not the native host */
    }
}

/**
 * Local calendar date as YYYY-MM-DD (not UTC).
 */
export function localISODate(d = new Date()) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

let dialogResolver = null;
let dialogBound = false;

function dialogRoot() {
    return document.getElementById('appDialog');
}

export function dialogIsOpen() {
    const root = dialogRoot();
    return !!(root && !root.hidden);
}

function finishDialog(value) {
    const root = dialogRoot();
    const resolve = dialogResolver;
    dialogResolver = null;
    if (root) {
        root.classList.add('is-hidden');
        root.hidden = true;
    }
    if (resolve) resolve(value);
}

function bindDialogOnce() {
    if (dialogBound) return;
    dialogBound = true;
    const root = dialogRoot();
    if (!root) return;
    document.getElementById('appDialogOk')?.addEventListener('click', () => {
        const input = document.getElementById('appDialogInput');
        if (root.dataset.mode === 'prompt') {
            finishDialog(input ? input.value : '');
            return;
        }
        finishDialog(true);
    });
    document.getElementById('appDialogCancel')?.addEventListener('click', () => {
        finishDialog(root.dataset.mode === 'prompt' ? null : false);
    });
    root.addEventListener('click', (e) => {
        if (e.target === root) finishDialog(root.dataset.mode === 'prompt' ? null : false);
    });
    document.addEventListener(
        'keydown',
        (e) => {
            if (!dialogIsOpen()) return;
            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopImmediatePropagation();
                finishDialog(root.dataset.mode === 'prompt' ? null : false);
                return;
            }
            if (e.key === 'Enter' && e.target?.id === 'appDialogInput') {
                e.preventDefault();
                document.getElementById('appDialogOk')?.click();
            }
        },
        true,
    );
}

function openDialog({ mode, title, message = '', value = '', ok = 'OK', cancel = 'Cancel', danger = false }) {
    bindDialogOnce();
    const root = dialogRoot();
    if (!root) return Promise.resolve(mode === 'prompt' ? null : false);
    if (dialogResolver) finishDialog(root.dataset.mode === 'prompt' ? null : false);
    root.dataset.mode = mode;
    const titleEl = document.getElementById('appDialogTitle');
    const messageEl = document.getElementById('appDialogMessage');
    const input = document.getElementById('appDialogInput');
    const okBtn = document.getElementById('appDialogOk');
    const cancelBtn = document.getElementById('appDialogCancel');
    if (titleEl) titleEl.textContent = title || '';
    if (messageEl) {
        messageEl.textContent = message || '';
        messageEl.hidden = !message;
    }
    if (okBtn) {
        okBtn.textContent = ok;
        okBtn.classList.toggle('btn-danger', !!danger);
        okBtn.classList.toggle('btn-primary', !danger);
    }
    if (cancelBtn) cancelBtn.textContent = cancel;
    if (input) {
        const showInput = mode === 'prompt';
        input.hidden = !showInput;
        input.value = showInput ? String(value ?? '') : '';
    }
    root.classList.remove('is-hidden');
    root.hidden = false;
    requestAnimationFrame(() => {
        if (mode === 'prompt' && input) {
            input.focus();
            input.select();
        } else {
            okBtn?.focus();
        }
    });
    return new Promise((resolve) => {
        dialogResolver = resolve;
    });
}

/** WKWebView does not implement window.prompt; use this in-app field instead. */
export function askText({ title, message = '', value = '', ok = 'Save', cancel = 'Cancel' } = {}) {
    return openDialog({ mode: 'prompt', title, message, value, ok, cancel });
}

/** WKWebView window.confirm always returns false. */
export function askConfirm({ title, message = '', ok = 'OK', cancel = 'Cancel', danger = false } = {}) {
    return openDialog({ mode: 'confirm', title, message, ok, cancel, danger }).then((value) => value === true);
}
