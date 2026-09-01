/**
 * Settings tab — appearance, writing, reminders, and data tools.
 */

import * as utils from './utils.js';
import {
    THEMES,
    ACCENTS,
    COLOR_SLOTS,
    getAppearance,
    persistAppearance,
    resetAppearance,
    applyAppearance,
    resolveColors,
    resolveInk,
    snapshotPresetFrom,
    normalizeHex,
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
        btn.classList.toggle('is-selected', btn.getAttribute('data-theme-id') === settings.theme && !settings.activePresetId);
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
    const autoFocus = document.getElementById('autoFocusToggle');
    if (autoFocus) autoFocus.checked = !!settings.autoFocus;

    paintColorSlots(settings);
    paintPresetSelect(settings);
    paintInk(settings);
}

function paintColorSlots(settings) {
    const colors = resolveColors(settings);
    COLOR_SLOTS.forEach(({ id }) => {
        const input = document.querySelector(`[data-color-slot="${id}"]`);
        if (input) input.value = colors[id];
    });
}

function paintInk(settings) {
    const auto = document.getElementById('inkAutoToggle');
    if (auto) auto.checked = settings.inkAuto !== false;
    const wrap = document.getElementById('inkCustomWrap');
    if (wrap) wrap.classList.toggle('is-hidden', settings.inkAuto !== false);
    const inkInput = document.getElementById('inkColorInput');
    if (inkInput) inkInput.value = resolveInk(settings);
}

function paintPresetSelect(settings) {
    const chips = document.getElementById('userPresetChips');
    if (chips) {
        const presets = settings.userPresets || [];
        const currentId = settings.activePresetId || '';
        if (!presets.length) {
            chips.innerHTML = '<span class="preset-empty">No saved palettes yet.</span>';
        } else {
            chips.innerHTML = presets
                .map(
                    (p) =>
                        `<button type="button" class="home-page-chip${p.id === currentId ? ' is-selected' : ''}" data-preset-id="${utils.escapeHtml(p.id)}">${utils.escapeHtml(p.name)}</button>`,
                )
                .join('');
        }
    }
    const del = document.getElementById('deletePresetBtn');
    if (del) del.disabled = !settings.activePresetId;
    const note = document.getElementById('presetNote');
    if (note) {
        const overrides = Object.keys(settings.colorOverrides || {});
        const themeLabel = (THEMES.find((t) => t.id === settings.theme) || { label: settings.theme }).label;
        if (settings.activePresetId) {
            const preset = (settings.userPresets || []).find((p) => p.id === settings.activePresetId);
            note.textContent = preset ? `Using “${preset.name}”. Save updates it.` : '';
        } else if (overrides.length) {
            note.textContent = `${themeLabel} with custom colors — Save keeps them as a palette.`;
        } else {
            note.textContent = '';
        }
    }
}

function newPresetId() {
    return `up-${Date.now().toString(36)}`;
}

async function applyBuiltinTheme(themeId) {
    return update({
        theme: themeId,
        activePresetId: '',
        colorOverrides: {},
    });
}

async function applyUserPreset(preset) {
    return update({
        theme: preset.baseTheme || 'ocean',
        activePresetId: preset.id,
        colorOverrides: { ...(preset.colors || {}) },
        widgetBorderWidth: preset.widgetBorderWidth,
        inkAuto: preset.inkAuto !== false,
        ink: preset.ink || '',
        accent: 'custom',
        customAccent: (preset.colors && preset.colors.accent) || '#4f8fcf',
    });
}

async function setColorSlot(slot, hex) {
    const value = normalizeHex(hex, '');
    if (!value) return;
    const current = getAppearance();
    const colorOverrides = { ...(current.colorOverrides || {}), [slot]: value };
    const patch = { colorOverrides };
    if (slot === 'accent') {
        patch.accent = 'custom';
        patch.customAccent = value;
    }
    if (slot === 'widgetBorder') {
        /* width stays; color is the slot */
    }
    return update(patch);
}

async function saveCurrentPreset() {
    const current = getAppearance();
    const snapshot = snapshotPresetFrom(current);
    const existing = (current.userPresets || []).find((p) => p.id === current.activePresetId);
    if (existing) {
        const userPresets = current.userPresets.map((p) => (p.id === existing.id ? { ...p, ...snapshot, name: p.name, id: p.id } : p));
        const next = await update({ userPresets });
        utils.showSuccessFeedback(`Saved “${existing.name}”.`);
        return next;
    }
    return createPreset(snapshot);
}

async function createPreset(snapshot) {
    const current = getAppearance();
    const snap = snapshot || snapshotPresetFrom(current);
    const name = window.prompt('Name this palette', 'My palette');
    if (name == null) return current;
    const label = name.trim();
    if (!label) {
        utils.showErrorFeedback('Give the palette a name.');
        return current;
    }
    const preset = {
        id: newPresetId(),
        name: label.slice(0, 40),
        ...snap,
    };
    const userPresets = [...(current.userPresets || []), preset];
    const next = await update({ userPresets, activePresetId: preset.id, colorOverrides: { ...snap.colors } });
    utils.showSuccessFeedback(`Saved “${preset.name}”.`);
    return next;
}

async function deleteActivePreset() {
    const current = getAppearance();
    if (!current.activePresetId) return current;
    const preset = (current.userPresets || []).find((p) => p.id === current.activePresetId);
    if (!preset) return current;
    if (!window.confirm(`Delete “${preset.name}”?`)) return current;
    const userPresets = current.userPresets.filter((p) => p.id !== preset.id);
    const next = await update({
        userPresets,
        activePresetId: '',
        colorOverrides: {},
        theme: preset.baseTheme || current.theme,
    });
    utils.showSuccessFeedback('Palette deleted.');
    return next;
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
            if (btn) applyBuiltinTheme(btn.getAttribute('data-theme-id'));
        });
    }

    const slotList = document.getElementById('colorSlotList');
    if (slotList && !slotList.dataset.ready) {
        slotList.dataset.ready = '1';
        slotList.innerHTML = COLOR_SLOTS.map(
            (slot) =>
                `<label class="color-slot" for="colorSlot-${slot.id}">
                    <span class="color-slot-label">${slot.label}</span>
                    <input type="color" class="color-input" id="colorSlot-${slot.id}" data-color-slot="${slot.id}" value="#4f8fcf">
                </label>`,
        ).join('');
        slotList.addEventListener('input', (e) => {
            const input = e.target.closest('[data-color-slot]');
            if (input) setColorSlot(input.getAttribute('data-color-slot'), input.value);
        });
    }

    document.getElementById('inkAutoToggle')?.addEventListener('change', (e) => {
        const inkAuto = e.target.checked;
        const patch = { inkAuto };
        if (!inkAuto) patch.ink = resolveInk({ ...getAppearance(), inkAuto: true });
        update(patch);
    });
    document.getElementById('inkColorInput')?.addEventListener('input', (e) => {
        update({ inkAuto: false, ink: e.target.value });
    });

    document.getElementById('userPresetChips')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-preset-id]');
        if (!btn) return;
        const preset = (getAppearance().userPresets || []).find((p) => p.id === btn.getAttribute('data-preset-id'));
        if (preset) applyUserPreset(preset);
    });
    document.getElementById('savePresetBtn')?.addEventListener('click', () => {
        void saveCurrentPreset();
    });
    document.getElementById('newPresetBtn')?.addEventListener('click', () => {
        void createPreset();
    });
    document.getElementById('deletePresetBtn')?.addEventListener('click', () => {
        void deleteActivePreset();
    });

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
            if (!btn) return;
            const accent = btn.getAttribute('data-accent-id');
            const colorOverrides = { ...(getAppearance().colorOverrides || {}) };
            delete colorOverrides.accent;
            update({ accent, colorOverrides });
        });
    }

    document.getElementById('customAccentInput')?.addEventListener('input', (e) => {
        const colorOverrides = { ...(getAppearance().colorOverrides || {}), accent: e.target.value };
        update({ accent: 'custom', customAccent: e.target.value, colorOverrides });
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
    document.getElementById('autoFocusToggle')?.addEventListener('change', (e) => {
        update({ autoFocus: e.target.checked });
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

    document.getElementById('icloudAutoToggle')?.addEventListener('change', async (e) => {
        if (typeof eel === 'undefined' || !eel.save_icloud_sync_settings) return;
        try {
            const status = await eel.save_icloud_sync_settings({ auto: e.target.checked })();
            paintIcloudStatus(status);
        } catch (err) {
            utils.showErrorFeedback('Could not save phone sync settings.');
        }
    });
    document.getElementById('icloudPushBtn')?.addEventListener('click', async () => {
        if (typeof eel === 'undefined' || !eel.push_icloud_pack) return;
        try {
            const result = await eel.push_icloud_pack()();
            const statusEl = document.getElementById('icloudSyncStatus');
            if (statusEl) statusEl.textContent = result.exported_at ? `Pushed ${result.exported_at}` : 'Pushed.';
            utils.showSuccessFeedback('Pushed the pack for the iPhone.');
            void loadIcloudSync();
        } catch (err) {
            utils.showErrorFeedback('Could not push the iCloud pack.');
        }
    });
    document.getElementById('icloudPullBtn')?.addEventListener('click', async () => {
        if (typeof eel === 'undefined' || !eel.pull_icloud_pack) return;
        try {
            const result = await eel.pull_icloud_pack()();
            const bits = result.applied || {};
            const statusEl = document.getElementById('icloudSyncStatus');
            if (statusEl) statusEl.textContent = `Pulled · work ${bits.work || 0} · workouts ${bits.workouts || 0} · journal ${bits.journal || 0}`;
            utils.showSuccessFeedback('Pulled phone changes into this Mac.');
            utils.notifyDataChanged();
            void loadIcloudSync();
        } catch (err) {
            utils.showErrorFeedback('Could not pull the iCloud pack.');
        }
    });

    paintSettings(getAppearance());
    void loadAdvancedPaths();
    void loadIcloudSync();
}

export function onSettingsTabShown() {
    paintSettings(getAppearance());
    void loadAdvancedPaths();
    void loadIcloudSync();
}

function paintIcloudStatus(status) {
    const folder = document.getElementById('icloudSyncFolder');
    if (folder) folder.textContent = status.folder || status.default_folder || '';
    const auto = document.getElementById('icloudAutoToggle');
    if (auto) auto.checked = status.auto !== false;
    const line = document.getElementById('icloudSyncStatus');
    if (line) {
        if (status.last_export) {
            const where = status.using_icloud_drive ? 'iCloud Drive' : 'this Mac';
            line.textContent = `Last pack ${status.last_export} · ${where}${status.last_device ? ` · ${status.last_device}` : ''}`;
        } else {
            line.textContent = status.using_icloud_drive
                ? 'No pack yet. Push once so the iPhone has something to read.'
                : 'iCloud Drive is not on this account. Packs stay in the local folder until you turn it on.';
        }
    }
}

async function loadIcloudSync() {
    if (typeof eel === 'undefined' || !eel.get_icloud_sync_status) return;
    try {
        paintIcloudStatus(await eel.get_icloud_sync_status()());
    } catch (_) {
        /* eel not ready */
    }
}

async function loadAdvancedPaths() {
    const dataDir = document.getElementById('appDataPath');
    if (dataDir && !dataDir.textContent) {
        try {
            dataDir.textContent = await eel.get_app_data_directory()();
        } catch (_) {
            dataDir.textContent = '';
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
    const workDb = document.getElementById('workDbPath');
    if (workDb && !workDb.textContent) {
        try {
            workDb.textContent = await eel.get_work_db_path_exposed()();
        } catch (_) {
            workDb.textContent = '';
        }
    }
    const workoutsDb = document.getElementById('workoutsDbPath');
    if (workoutsDb && !workoutsDb.textContent) {
        try {
            workoutsDb.textContent = await eel.get_workouts_db_path_exposed()();
        } catch (_) {
            workoutsDb.textContent = '';
        }
    }
    const widgetPath = document.getElementById('widgetSnapshotPath');
    if (widgetPath && !widgetPath.textContent) {
        try {
            widgetPath.textContent = await eel.get_widget_snapshot_path_exposed()();
        } catch (_) {
            widgetPath.textContent = '';
        }
    }
}
