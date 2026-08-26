/**
 * Appearance engine — themes, typography, layout, and writing prefs.
 * Applies CSS data-attributes immediately, persists to localStorage,
 * and syncs to the desktop JSON file when Eel is available.
 */

const STORAGE_KEY = 'kosistenz-appearance';

export const DEFAULTS = {
    theme: 'ocean',
    accent: 'sky',
    customAccent: '#4F8FCF',
    font: 'sans',
    density: 'comfortable',
    radius: 'soft',
    width: 'standard',
    sidebar: 'expanded',
    journalFontSize: 17,
    timerMinutes: 10,
    reducedMotion: false,
    highContrast: false,
};

export const THEMES = [
    { id: 'ocean', label: 'Ocean' },
    { id: 'midnight', label: 'Midnight' },
    { id: 'slate', label: 'Slate' },
    { id: 'paper', label: 'Paper' },
    { id: 'forest', label: 'Forest' },
    { id: 'dusk', label: 'Dusk' },
];

export const ACCENTS = [
    { id: 'sky', label: 'Blue', hex: '#4F8FCF' },
    { id: 'teal', label: 'Teal', hex: '#2A9A8C' },
    { id: 'amber', label: 'Ochre', hex: '#C8892C' },
    { id: 'rose', label: 'Rose', hex: '#C45C6A' },
    { id: 'violet', label: 'Violet', hex: '#7A6CB5' },
    { id: 'lime', label: 'Moss', hex: '#6A9A6E' },
    { id: 'custom', label: 'Custom', hex: null },
];

let current = { ...DEFAULTS };
const listeners = new Set();

function readLocal() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return {};
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === 'object' ? parsed : {};
    } catch (_) {
        return {};
    }
}

function writeLocal(settings) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (_) {
        /* private mode / quota */
    }
}

function hexToHsl(hex) {
    let h = String(hex || '').replace('#', '').trim();
    if (h.length === 3) {
        h = h.split('').map((c) => c + c).join('');
    }
    if (!/^[0-9a-fA-F]{6}$/.test(h)) {
        return { h: 210, s: 56, l: 56 };
    }
    const r = parseInt(h.slice(0, 2), 16) / 255;
    const g = parseInt(h.slice(2, 4), 16) / 255;
    const b = parseInt(h.slice(4, 6), 16) / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let hue = 0;
    let sat = 0;
    const light = (max + min) / 2;
    const d = max - min;
    if (d !== 0) {
        sat = d / (1 - Math.abs(2 * light - 1));
        switch (max) {
            case r:
                hue = ((g - b) / d) % 6;
                break;
            case g:
                hue = (b - r) / d + 2;
                break;
            default:
                hue = (r - g) / d + 4;
        }
        hue *= 60;
        if (hue < 0) hue += 360;
    }
    return {
        h: Math.round(hue),
        s: Math.round(sat * 100),
        l: Math.round(light * 100),
    };
}

function accentHsl(settings) {
    const preset = ACCENTS.find((a) => a.id === settings.accent);
    if (settings.accent === 'custom' || !preset || !preset.hex) {
        return hexToHsl(settings.customAccent);
    }
    return hexToHsl(preset.hex);
}

export function applyAppearance(settings) {
    current = { ...DEFAULTS, ...settings };
    const root = document.documentElement;
    root.setAttribute('data-theme', current.theme);
    root.setAttribute('data-density', current.density);
    root.setAttribute('data-radius', current.radius);
    root.setAttribute('data-width', current.width);
    root.setAttribute('data-font', current.font);
    root.setAttribute('data-sidebar', current.sidebar);
    root.setAttribute('data-contrast', current.highContrast ? 'high' : 'normal');
    root.setAttribute('data-motion', current.reducedMotion ? 'reduce' : 'full');
    const hsl = accentHsl(current);
    root.style.setProperty('--accent-h', String(hsl.h));
    root.style.setProperty('--accent-s', `${hsl.s}%`);
    root.style.setProperty('--accent-l', `${hsl.l}%`);
    root.style.setProperty('--journal-font-size', `${current.journalFontSize}px`);
    listeners.forEach((fn) => {
        try {
            fn(current);
        } catch (e) {
            console.error(e);
        }
    });
}

export function getAppearance() {
    return { ...current };
}

export function onAppearanceChange(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
}

export async function persistAppearance(settings) {
    const next = { ...DEFAULTS, ...current, ...settings };
    applyAppearance(next);
    writeLocal(next);
    if (typeof eel !== 'undefined' && eel.save_appearance_settings) {
        try {
            const saved = await eel.save_appearance_settings(next)();
            applyAppearance(saved);
            writeLocal(saved);
            return saved;
        } catch (e) {
            console.warn('Could not persist appearance to disk', e);
        }
    }
    return next;
}

export async function resetAppearance() {
    applyAppearance(DEFAULTS);
    writeLocal(DEFAULTS);
    if (typeof eel !== 'undefined' && eel.reset_appearance_settings) {
        try {
            const saved = await eel.reset_appearance_settings()();
            applyAppearance(saved);
            writeLocal(saved);
            return saved;
        } catch (e) {
            console.warn(e);
        }
    }
    return { ...DEFAULTS };
}

export async function initAppearance() {
    const local = { ...DEFAULTS, ...readLocal() };
    applyAppearance(local);
    if (typeof eel !== 'undefined' && eel.get_appearance_settings) {
        try {
            const remote = await eel.get_appearance_settings()();
            const merged = { ...local, ...remote };
            applyAppearance(merged);
            writeLocal(merged);
            return merged;
        } catch (e) {
            console.warn('Could not load appearance from disk', e);
        }
    }
    return local;
}
