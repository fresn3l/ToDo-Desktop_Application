/**
 * Appearance engine — themes, typography, layout, and writing prefs.
 * Applies CSS data-attributes immediately, persists to localStorage,
 * and syncs to the desktop JSON file when Eel is available.
 */

const STORAGE_KEY = 'kosistenz-appearance';

export const COLOR_SLOTS = [
    { id: 'pageBg', label: 'Page background' },
    { id: 'widgetBg', label: 'Widget background' },
    { id: 'widgetBorder', label: 'Widget borders' },
    { id: 'titles', label: 'Titles' },
    { id: 'accent', label: 'Accent' },
    { id: 'done', label: 'Done' },
    { id: 'openNext', label: 'Open / next' },
    { id: 'sidebar', label: 'Sidebar' },
];

export const INK_LIGHT = '#f7fafc';
export const INK_DARK = '#1a1814';

export const THEME_PALETTES = {
    ocean: {
        pageBg: '#121c26',
        widgetBg: '#1d2c3b',
        widgetBorder: '#2c3d4e',
        titles: '#eef3f7',
        accent: '#4f8fcf',
        done: '#5ebb8e',
        openNext: '#d4a054',
        sidebar: '#0e1620',
    },
    midnight: {
        pageBg: '#0e0d0b',
        widgetBg: '#161512',
        widgetBorder: '#2a2722',
        titles: '#f0eee9',
        accent: '#e0b355',
        done: '#5ebb8e',
        openNext: '#e0b355',
        sidebar: '#161512',
    },
    slate: {
        pageBg: '#171e2b',
        widgetBg: '#243044',
        widgetBorder: '#2c3848',
        titles: '#eef2f6',
        accent: '#4f8fcf',
        done: '#5ebb8e',
        openNext: '#d4a054',
        sidebar: '#121824',
    },
    paper: {
        pageBg: '#f7f3eb',
        widgetBg: '#f1ebe0',
        widgetBorder: '#d8d0c2',
        titles: '#1b1814',
        accent: '#4f8fcf',
        done: '#2f7d57',
        openNext: '#b5791f',
        sidebar: '#f3eee4',
    },
    forest: {
        pageBg: '#141e1a',
        widgetBg: '#20312b',
        widgetBorder: '#2a3c36',
        titles: '#eef4f0',
        accent: '#4f8fcf',
        done: '#6bc49a',
        openNext: '#d4a054',
        sidebar: '#101816',
    },
    dusk: {
        pageBg: '#1b1824',
        widgetBg: '#2b2738',
        widgetBorder: '#3a3548',
        titles: '#f2eef6',
        accent: '#4f8fcf',
        done: '#5ebb8e',
        openNext: '#d4a054',
        sidebar: '#16131e',
    },
};

export const DEFAULTS = {
    theme: 'ocean',
    accent: 'sky',
    customAccent: '#4F8FCF',
    font: 'system',
    density: 'comfortable',
    radius: 'soft',
    width: 'standard',
    sidebar: 'compact',
    todayLayout: 'split',
    todayOrder: 'todo,workout,journal',
    todayTodo: true,
    todayWorkout: true,
    todayJournal: true,
    journalFontSize: 17,
    timerMinutes: 10,
    autoFocus: false,
    reducedMotion: false,
    highContrast: false,
    colorOverrides: {},
    widgetBorderWidth: 1,
    inkAuto: true,
    ink: '',
    activePresetId: '',
    userPresets: [],
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

let current = { ...DEFAULTS, colorOverrides: {}, userPresets: [] };
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

export function normalizeHex(hex, fallback = '') {
    let h = String(hex || '').trim();
    if (!h) return fallback;
    if (h[0] !== '#') h = `#${h}`;
    if (h.length === 4 && /^#[0-9a-fA-F]{3}$/.test(h)) {
        h = `#${h[1]}${h[1]}${h[2]}${h[2]}${h[3]}${h[3]}`;
    }
    if (!/^#[0-9a-fA-F]{6}$/.test(h)) return fallback;
    return h.toLowerCase();
}

function hexToHsl(hex) {
    const normalized = normalizeHex(hex, '#4f8fcf').slice(1);
    const r = parseInt(normalized.slice(0, 2), 16) / 255;
    const g = parseInt(normalized.slice(2, 4), 16) / 255;
    const b = parseInt(normalized.slice(4, 6), 16) / 255;
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

function srgbToLinear(channel) {
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance(hex) {
    const n = normalizeHex(hex, '');
    if (!n) return 0;
    const r = parseInt(n.slice(1, 3), 16) / 255;
    const g = parseInt(n.slice(3, 5), 16) / 255;
    const b = parseInt(n.slice(5, 7), 16) / 255;
    return 0.2126 * srgbToLinear(r) + 0.7152 * srgbToLinear(g) + 0.0722 * srgbToLinear(b);
}

export function inkForHex(hex) {
    return relativeLuminance(hex) > 0.45 ? INK_DARK : INK_LIGHT;
}

export function paletteFor(theme) {
    return { ...(THEME_PALETTES[theme] || THEME_PALETTES.ocean) };
}

export function resolveAccentHex(settings) {
    const overrides = settings.colorOverrides || {};
    const fromOverride = normalizeHex(overrides.accent, '');
    if (fromOverride) return fromOverride;
    if (settings.accent === 'custom') {
        const custom = normalizeHex(settings.customAccent, '');
        if (custom) return custom;
    }
    const preset = ACCENTS.find((a) => a.id === settings.accent);
    if (preset?.hex) return normalizeHex(preset.hex, paletteFor(settings.theme).accent);
    return paletteFor(settings.theme).accent;
}

export function resolveColors(settings) {
    const out = paletteFor(settings.theme);
    const overrides = settings.colorOverrides || {};
    COLOR_SLOTS.forEach(({ id }) => {
        if (id === 'accent') return;
        const hx = normalizeHex(overrides[id], '');
        if (hx) out[id] = hx;
    });
    out.accent = resolveAccentHex(settings);
    return out;
}

export function resolveInk(settings) {
    if (settings.inkAuto !== false) return inkForHex(resolveAccentHex(settings));
    return normalizeHex(settings.ink, '') || inkForHex(resolveAccentHex(settings));
}

function mergeSettings(partial) {
    const next = {
        ...DEFAULTS,
        ...current,
        ...partial,
    };
    next.colorOverrides = { ...(partial.colorOverrides ?? current.colorOverrides ?? {}) };
    next.userPresets = Array.isArray(partial.userPresets)
        ? partial.userPresets
        : [...(current.userPresets || [])];
    return next;
}

function setOrClear(root, prop, value, enabled) {
    if (enabled && value) root.style.setProperty(prop, value);
    else root.style.removeProperty(prop);
}

function applyResolvedVars(root, settings) {
    const colors = resolveColors(settings);
    const overrides = settings.colorOverrides || {};
    const ink = resolveInk(settings);
    const hsl = hexToHsl(colors.accent);
    const width = Math.max(0, Math.min(8, Number(settings.widgetBorderWidth) || 0));
    root.style.setProperty('--accent-h', String(hsl.h));
    root.style.setProperty('--accent-s', `${hsl.s}%`);
    root.style.setProperty('--accent-l', `${hsl.l}%`);
    setOrClear(root, '--bg-canvas', colors.pageBg, !!overrides.pageBg);
    setOrClear(root, '--bg-main', colors.pageBg, !!overrides.pageBg);
    setOrClear(root, '--bg-elevated', colors.widgetBg, !!overrides.widgetBg);
    setOrClear(root, '--bg-panel', colors.widgetBg, !!overrides.widgetBg);
    setOrClear(root, '--bg-sidebar', colors.sidebar, !!overrides.sidebar);
    setOrClear(root, '--text-title', colors.titles, !!overrides.titles);
    setOrClear(root, '--success', colors.done, !!overrides.done);
    setOrClear(root, '--attention', colors.openNext, !!overrides.openNext);
    root.style.setProperty('--home-widget-border-width', `${width}px`);
    setOrClear(root, '--home-widget-border-color', colors.widgetBorder, !!overrides.widgetBorder);
    root.style.setProperty('--on-primary', ink);
    root.style.setProperty('--primary-ink', ink);
}

export function applyAppearanceOverlay(extraOverrides) {
    const merged = {
        ...current,
        colorOverrides: { ...(current.colorOverrides || {}), ...(extraOverrides || {}) },
    };
    applyResolvedVars(document.documentElement, merged);
}

export function applyAppearance(settings) {
    current = mergeSettings(settings);
    const root = document.documentElement;
    root.setAttribute('data-theme', current.theme);
    root.setAttribute('data-density', current.density);
    root.setAttribute('data-radius', current.radius);
    root.setAttribute('data-width', current.width);
    root.setAttribute('data-font', current.font);
    root.setAttribute('data-sidebar', current.sidebar);
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        const compact = current.sidebar === 'compact';
        sidebarToggle.setAttribute('aria-expanded', compact ? 'false' : 'true');
        sidebarToggle.setAttribute('aria-label', compact ? 'Expand sidebar' : 'Collapse sidebar');
        sidebarToggle.title = compact ? 'Expand sidebar' : 'Collapse sidebar';
        const collapseLabel = sidebarToggle.querySelector('.nav-label');
        if (collapseLabel) collapseLabel.textContent = compact ? 'Expand' : 'Collapse';
    }
    root.setAttribute('data-today-layout', current.todayLayout || 'split');
    root.setAttribute('data-today-order', current.todayOrder || 'todo,workout,journal');
    root.setAttribute('data-today-todo', current.todayTodo === false ? 'off' : 'on');
    root.setAttribute('data-today-workout', current.todayWorkout === false ? 'off' : 'on');
    root.setAttribute('data-today-journal', current.todayJournal === false ? 'off' : 'on');
    root.setAttribute('data-contrast', current.highContrast ? 'high' : 'normal');
    root.setAttribute('data-motion', current.reducedMotion ? 'reduce' : 'full');
    applyResolvedVars(root, current);
    root.style.setProperty('--journal-font-size', `${current.journalFontSize}px`);
    notifyNativeShell(current);
    listeners.forEach((fn) => {
        try {
            fn(current);
        } catch (e) {
            console.error(e);
        }
    });
}

function notifyNativeShell(settings) {
    const dark = settings.theme !== 'paper';
    try {
        window.webkit?.messageHandlers?.kosistenz?.postMessage({ type: 'theme', dark });
    } catch (_) {
        /* not the native host */
    }
}

export function notifyNativeTab(tab, title) {
    try {
        window.webkit?.messageHandlers?.kosistenz?.postMessage({ type: 'tab', tab, title });
    } catch (_) {
        /* not the native host */
    }
}

export function getAppearance() {
    return {
        ...current,
        colorOverrides: { ...(current.colorOverrides || {}) },
        userPresets: [...(current.userPresets || [])],
    };
}

export function onAppearanceChange(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
}

export function snapshotPresetFrom(settings) {
    return {
        baseTheme: settings.theme || 'ocean',
        colors: resolveColors(settings),
        widgetBorderWidth: Math.max(0, Math.min(8, Number(settings.widgetBorderWidth) || 0)),
        inkAuto: settings.inkAuto !== false,
        ink: normalizeHex(settings.ink, ''),
    };
}

export async function persistAppearance(settings) {
    const next = mergeSettings(settings);
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
    return getAppearance();
}

export async function resetAppearance() {
    const kept = [...(current.userPresets || [])];
    const next = { ...DEFAULTS, colorOverrides: {}, userPresets: kept, activePresetId: '' };
    applyAppearance(next);
    writeLocal(next);
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
    return getAppearance();
}

export async function initAppearance() {
    const local = mergeSettings(readLocal());
    applyAppearance(local);
    if (typeof eel !== 'undefined' && eel.get_appearance_settings) {
        try {
            const remote = await eel.get_appearance_settings()();
            const merged = mergeSettings({ ...local, ...remote });
            applyAppearance(merged);
            writeLocal(merged);
            return merged;
        } catch (e) {
            console.warn('Could not load appearance from disk', e);
        }
    }
    return getAppearance();
}
