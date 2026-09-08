/**
 * Insert clipboard text into the focused field.
 * WKWebView treats a copied http(s)/webcal link as navigation; the native
 * host cancels that load and calls window.kosistenzInsertText instead.
 */
(function (global) {
    function sanitizePastedUrl(raw) {
        var s = String(raw || '').replace(/^\uFEFF/, '').trim();
        if (!s) return '';
        var lines = s.split(/\r?\n/);
        var i;
        var line;
        s = '';
        for (i = 0; i < lines.length; i += 1) {
            line = lines[i].trim();
            if (line && line.charAt(0) !== '#') {
                s = line;
                break;
            }
        }
        s = s.replace(/^<|>$/g, '').replace(/^['"]|['"]$/g, '').trim();
        var href = s.match(/href=["']((?:https?|webcal):\/\/[^"']+)/i);
        if (href) s = href[1];
        var match = s.match(/(?:https?|webcal):\/\/[^\s<>"']+/i);
        if (match) s = match[0];
        if (s.toLowerCase().indexOf('webcal://') === 0) {
            s = 'https://' + s.slice('webcal://'.length);
        }
        return s;
    }

    function isEditableField(node) {
        if (!node || node.readOnly || node.disabled) return false;
        var tag = (node.tagName || '').toLowerCase();
        if (tag === 'textarea') return true;
        if (tag === 'input') {
            var t = (node.type || 'text').toLowerCase();
            return t === 'text' || t === 'url' || t === 'search' || t === 'email'
                || t === 'password' || t === 'tel' || t === '' || t === 'number';
        }
        return false;
    }

    function looksLikeUrl(text) {
        return /^(https?|webcal):\/\//i.test(text);
    }

    function looksLikeCalendarUrl(text) {
        var u = String(text || '').toLowerCase();
        if (!looksLikeUrl(u)) return false;
        return u.indexOf('webcal://') === 0
            || /\.ics(\?|#|$)/.test(u)
            || u.indexOf('/calendar') !== -1
            || u.indexOf('feeds/calendars') !== -1
            || u.indexOf('webcal') !== -1;
    }

    function isCalendarPage() {
        if (document.documentElement.getAttribute('data-page') === 'calendar') return true;
        var tab = document.getElementById('calendarTab');
        return !!(tab && tab.classList.contains('active'));
    }

    function fillIcsField(url) {
        var ics = document.getElementById('calIcsUrl');
        if (!ics) return false;
        ics.value = url;
        ics.dispatchEvent(new Event('input', { bubbles: true }));
        ics.dispatchEvent(new Event('change', { bubbles: true }));
        try { ics.focus(); } catch (err) { /* ignore */ }
        return true;
    }

    function insertPlainText(text) {
        var raw = String(text || '');
        if (!raw) return false;
        var url = sanitizePastedUrl(raw);
        var asUrl = looksLikeUrl(url);
        var el = document.activeElement;
        var ics = document.getElementById('calIcsUrl');
        var calActive = isCalendarPage();

        if (/BEGIN:VCALENDAR/i.test(raw) && typeof global.kosistenzImportIcsText === 'function') {
            global.kosistenzImportIcsText(raw);
            return true;
        }

        var intoIcs = asUrl && ics && (
            el === ics
            || (calActive && looksLikeCalendarUrl(url))
            || (calActive && !isEditableField(el) && !(el && el.isContentEditable))
        );
        if (intoIcs) {
            return fillIcsField(url);
        }

        if (isEditableField(el)) {
            var start = el.selectionStart != null ? el.selectionStart : (el.value || '').length;
            var end = el.selectionEnd != null ? el.selectionEnd : (el.value || '').length;
            var value = el.value || '';
            var piece = (asUrl && el.id === 'calIcsUrl') ? url : raw;
            el.value = value.slice(0, start) + piece + value.slice(end);
            var pos = start + piece.length;
            try { el.setSelectionRange(pos, pos); } catch (err2) { /* ignore */ }
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }

        if (el && el.isContentEditable) {
            try {
                document.execCommand('insertText', false, raw);
                return true;
            } catch (err3) {
                return false;
            }
        }

        if (asUrl && ics) {
            return fillIcsField(url);
        }
        return false;
    }

    function clipboardRaw(dt) {
        if (!dt) return '';
        return dt.getData('text/uri-list')
            || dt.getData('text/plain')
            || dt.getData('text/html')
            || '';
    }

    if (global.document && typeof global.document.addEventListener === 'function') {
        document.addEventListener('paste', function (e) {
            var raw = clipboardRaw(e.clipboardData);
            if (!raw) return;
            var url = sanitizePastedUrl(raw);
            if (!looksLikeUrl(url)) return;
            var ics = document.getElementById('calIcsUrl');
            var target = e.target;
            if (ics && (target === ics || (isCalendarPage() && looksLikeCalendarUrl(url)))) {
                e.preventDefault();
                insertPlainText(url);
            }
        }, true);
    }

    global.kosistenzSanitizePastedUrl = sanitizePastedUrl;
    global.kosistenzLooksLikeCalendarUrl = looksLikeCalendarUrl;
    global.kosistenzInsertText = insertPlainText;
})(window);
