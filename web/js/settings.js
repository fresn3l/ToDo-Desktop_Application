/**
 * Settings tab — appearance, writing, reminders, and data tools.
 */

import * as utils from './utils.js';
import {
    THEMES,
    ACCENTS,
    getAppearance,
    persistAppearance,
    resetAppearance,
    applyAppearance,
} from './appearance.js';

function bindSegmented(name, current, onPick) {
    const group = document.querySelector(`[data-setting-group="${name}"]`);
    if (!group) return;
    group.querySelectorAll('[data-value]').forEach((btn) => {
        btn.classList.toggle('is-selected', btn.getAttribute('data-value') === String(current));
        btn.addEventListener('click', () => onPick(btn.getAttribute('data-value')));
    });
}

function paintSettings(settings) {
    document.querySelectorAll('[data-setting-group]').forEach((group) => {
        const key = group.getAttribute('data-setting-group');
        const value = settings[key];
        group.querySelectorAll('[data-value]').forEach((btn) => {
            btn.classList.toggle('is-selected', btn.getAttribute('data-value') === String(value));
        });
    });

    document.querySelectorAll('[data-theme-id]').forEach((btn) => {
        btn.classList.toggle('is-selected', btn.getAttribute('data-theme-id') === settings.theme);
    });
    document.querySelectorAll('[data-accent-id]').forEach((btn) => {
        btn.classList.toggle('is-selected', btn.getAttribute('data-accent-id') === settings.accent);
    });

    const customWrap = document.getElementById('customAccentWrap');
    if (customWrap) {
        customWrap.classList.toggle('is-hidden', settings.accent !== 'custom');
    }
    const customInput = document.getElementById('customAccentInput');
    if (customInput) customInput.value = settings.customAccent || '#4F8FCF';

    const fontSize = document.getElementById('journalFontSize');
    const fontSizeVal = document.getElementById('journalFontSizeValue');
    if (fontSize) fontSize.value = String(settings.journalFontSize);
    if (fontSizeVal) fontSizeVal.textContent = `${settings.journalFontSize}px`;

    const timer = document.getElementById('timerMinutes');
    if (timer) timer.value = String(settings.timerMinutes);

    const motion = document.getElementById('reducedMotionToggle');
    if (motion) motion.checked = !!settings.reducedMotion;
    const contrast = document.getElementById('highContrastToggle');
    if (contrast) contrast.checked = !!settings.highContrast;
}

async function update(partial) {
    const next = await persistAppearance(partial);
    paintSettings(next);
}

function applyLiveFontSize(n) {
    applyAppearance({ ...getAppearance(), journalFontSize: n });
}

export function setupSettings() {
    if (document.body.dataset.settingsReady === '1') {
        paintSettings(getAppearance());
        void loadAdvancedPaths();
        return;
    }
    document.body.dataset.settingsReady = '1';

    const themeGrid = document.getElementById('themeGrid');
    if (themeGrid && !themeGrid.dataset.ready) {
        themeGrid.dataset.ready = '1';
        themeGrid.innerHTML = THEMES.map(
            (t) =>
                `<button type="button" class="theme-swatch theme-swatch--${t.id}" data-theme-id="${t.id}" aria-label="${t.label}">
                    <span class="theme-swatch-preview" aria-hidden="true"></span>
                    <span class="theme-swatch-label">${t.label}</span>
                </button>`,
        ).join('');
        themeGrid.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-theme-id]');
            if (btn) update({ theme: btn.getAttribute('data-theme-id') });
        });
    }

    const accentGrid = document.getElementById('accentGrid');
    if (accentGrid && !accentGrid.dataset.ready) {
        accentGrid.dataset.ready = '1';
        accentGrid.innerHTML = ACCENTS.map((a) => {
            const style = a.hex ? `style="--swatch:${a.hex}"` : '';
            return `<button type="button" class="accent-swatch" data-accent-id="${a.id}" ${style} aria-label="${a.label}">
                <span class="accent-swatch-dot" aria-hidden="true"></span>
                <span>${a.label}</span>
            </button>`;
        }).join('');
        accentGrid.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-accent-id]');
            if (btn) update({ accent: btn.getAttribute('data-accent-id') });
        });
    }

    document.getElementById('customAccentInput')?.addEventListener('input', (e) => {
        update({ accent: 'custom', customAccent: e.target.value });
    });

    bindSegmented('font', getAppearance().font, (v) => update({ font: v }));
    bindSegmented('density', getAppearance().density, (v) => update({ density: v }));
    bindSegmented('radius', getAppearance().radius, (v) => update({ radius: v }));
    bindSegmented('width', getAppearance().width, (v) => update({ width: v }));
    bindSegmented('sidebar', getAppearance().sidebar, (v) => update({ sidebar: v }));

    document.getElementById('journalFontSize')?.addEventListener('input', (e) => {
        const n = parseInt(e.target.value, 10);
        const label = document.getElementById('journalFontSizeValue');
        if (label) label.textContent = `${n}px`;
        applyLiveFontSize(n);
    });
    document.getElementById('journalFontSize')?.addEventListener('change', (e) => {
        update({ journalFontSize: parseInt(e.target.value, 10) });
    });

    document.getElementById('timerMinutes')?.addEventListener('change', (e) => {
        update({ timerMinutes: parseInt(e.target.value, 10) });
    });

    document.getElementById('reducedMotionToggle')?.addEventListener('change', (e) => {
        update({ reducedMotion: e.target.checked });
    });
    document.getElementById('highContrastToggle')?.addEventListener('change', (e) => {
        update({ highContrast: e.target.checked });
    });

    document.getElementById('resetAppearanceBtn')?.addEventListener('click', async () => {
        const next = await resetAppearance();
        paintSettings(next);
        utils.showSuccessFeedback('Appearance reset to defaults.');
    });

    document.getElementById('sidebarToggle')?.addEventListener('click', () => {
        const next = getAppearance().sidebar === 'compact' ? 'expanded' : 'compact';
        update({ sidebar: next });
    });

    paintSettings(getAppearance());
    void loadAdvancedPaths();
}

export function onSettingsTabShown() {
    paintSettings(getAppearance());
    void loadAdvancedPaths();
}

async function loadAdvancedPaths() {
    const dbEl = document.getElementById('checklistDbPath');
    if (dbEl && !dbEl.textContent) {
        try {
            dbEl.textContent = await eel.get_daily_checklist_db_path_exposed()();
        } catch (_) {
            dbEl.textContent = '';
        }
    }
    const exportsPath = document.getElementById('exportsPath');
    if (exportsPath && !exportsPath.textContent) {
        try {
            exportsPath.textContent = await eel.get_exports_directory()();
        } catch (_) {
            exportsPath.textContent = 'Application Support/ToDo/exports';
        }
    }
}
