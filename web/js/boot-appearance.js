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
        r.setAttribute('data-contrast', s.highContrast ? 'high' : 'normal');
        r.setAttribute('data-motion', s.reducedMotion ? 'reduce' : 'full');
        if (s.journalFontSize) r.style.setProperty('--journal-font-size', s.journalFontSize + 'px');
        var hexes = { sky: '#4F8FCF', teal: '#2A9A8C', amber: '#C8892C', rose: '#C45C6A', violet: '#7A6CB5', lime: '#6A9A6E' };
        var hex = s.accent === 'custom' ? s.customAccent : hexes[s.accent || 'sky'];
        if (hex) {
            var h = String(hex).replace('#', '');
            if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
            if (/^[0-9a-fA-F]{6}$/.test(h)) {
                var rr = parseInt(h.slice(0, 2), 16) / 255;
                var gg = parseInt(h.slice(2, 4), 16) / 255;
                var bb = parseInt(h.slice(4, 6), 16) / 255;
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
            }
        }
    } catch (e) {}
})();
