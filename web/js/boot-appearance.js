/**
 * Apply saved appearance before first paint (no inline script — CSP script-src 'self').
 */
(function () {
    try {
        var s = JSON.parse(localStorage.getItem('kosistenz-appearance') || '{}');
        var r = document.documentElement;
        if (s.theme) r.setAttribute('data-theme', s.theme);
        if (s.density) r.setAttribute('data-density', s.density);
        if (s.radius) r.setAttribute('data-radius', s.radius);
        if (s.width) r.setAttribute('data-width', s.width);
        if (s.font) r.setAttribute('data-font', s.font);
        if (s.sidebar) r.setAttribute('data-sidebar', s.sidebar);
        r.setAttribute('data-today-layout', s.todayLayout || 'split');
        r.setAttribute('data-today-order', s.todayOrder || 'todo,workout,journal');
        r.setAttribute('data-today-todo', s.todayTodo === false ? 'off' : 'on');
        r.setAttribute('data-today-workout', s.todayWorkout === false ? 'off' : 'on');
        r.setAttribute('data-today-journal', s.todayJournal === false ? 'off' : 'on');
        r.setAttribute('data-contrast', s.highContrast ? 'high' : 'normal');
        r.setAttribute('data-motion', s.reducedMotion ? 'reduce' : 'full');
        if (s.journalFontSize) r.style.setProperty('--journal-font-size', s.journalFontSize + 'px');

        var hexes = { sky: '#4f8fcf', teal: '#2a9a8c', amber: '#c8892c', rose: '#c45c6a', violet: '#7a6cb5', lime: '#6a9a6e' };
        var ov = s.colorOverrides && typeof s.colorOverrides === 'object' ? s.colorOverrides : {};
        function hx(v, fallback) {
            var t = String(v || '').replace('#', '');
            if (t.length === 3) t = t[0] + t[0] + t[1] + t[1] + t[2] + t[2];
            return /^[0-9a-fA-F]{6}$/.test(t) ? '#' + t.toLowerCase() : fallback;
        }
        var accent = hx(ov.accent, '') || (s.accent === 'custom' ? hx(s.customAccent, '') : '') || hx(hexes[s.accent || 'sky'], '#4f8fcf');
        if (ov.pageBg) {
            var pageBg = hx(ov.pageBg, '');
            if (pageBg) {
                r.style.setProperty('--bg-canvas', pageBg);
                r.style.setProperty('--bg-main', pageBg);
            }
        }
        if (ov.widgetBg) {
            var widgetBg = hx(ov.widgetBg, '');
            if (widgetBg) {
                r.style.setProperty('--bg-elevated', widgetBg);
                r.style.setProperty('--bg-panel', widgetBg);
            }
        }
        if (ov.sidebar) {
            var sidebar = hx(ov.sidebar, '');
            if (sidebar) r.style.setProperty('--bg-sidebar', sidebar);
        }
        if (ov.titles) {
            var titles = hx(ov.titles, '');
            if (titles) r.style.setProperty('--text-title', titles);
        }
        if (ov.done) {
            var done = hx(ov.done, '');
            if (done) r.style.setProperty('--success', done);
        }
        if (ov.openNext) {
            var openNext = hx(ov.openNext, '');
            if (openNext) r.style.setProperty('--attention', openNext);
        }
        if (s.widgetBorderWidth != null) {
            var width = Math.max(0, Math.min(8, parseInt(s.widgetBorderWidth, 10)));
            if (!isNaN(width)) r.style.setProperty('--home-widget-border-width', width + 'px');
        }
        if (ov.widgetBorder) {
            var widgetBorder = hx(ov.widgetBorder, '');
            if (widgetBorder) r.style.setProperty('--home-widget-border-color', widgetBorder);
        }

        var hex = accent.replace('#', '');
        var rr = parseInt(hex.slice(0, 2), 16) / 255;
        var gg = parseInt(hex.slice(2, 4), 16) / 255;
        var bb = parseInt(hex.slice(4, 6), 16) / 255;
        var max = Math.max(rr, gg, bb), min = Math.min(rr, gg, bb);
        var l = (max + min) / 2, d = max - min, hue = 210, sat = 0;
        if (d) {
            sat = d / (1 - Math.abs(2 * l - 1));
            if (max === rr) hue = ((gg - bb) / d) % 6;
            else if (max === gg) hue = (bb - rr) / d + 2;
            else hue = (rr - gg) / d + 4;
            hue = hue * 60;
            if (hue < 0) hue += 360;
        }
        r.style.setProperty('--accent-h', String(Math.round(hue)));
        r.style.setProperty('--accent-s', Math.round(sat * 100) + '%');
        r.style.setProperty('--accent-l', Math.round(l * 100) + '%');

        function lin(c) { return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
        var lum = 0.2126 * lin(rr) + 0.7152 * lin(gg) + 0.0722 * lin(bb);
        var autoInk = lum > 0.45 ? '#1a1814' : '#f7fafc';
        var ink = s.inkAuto === false ? hx(s.ink, autoInk) : autoInk;
        r.style.setProperty('--on-primary', ink);
        r.style.setProperty('--primary-ink', ink);
    } catch (e) {}
})();
