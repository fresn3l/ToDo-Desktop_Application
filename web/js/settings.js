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
    applyAppearanceOverlay,
} from './appearance.js';

let colorScope = 'global';
let colorPageId = '';
let homeLayoutCache = null;
const SETTINGS_COLS_KEY = 'kosistenz-settings-cols';

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
    paintColorScope();
}

function mergedColorSettings(settings) {
    if (colorScope !== 'page') return settings;
    const page = (homeLayoutCache?.pages || []).find((p) => p.id === colorPageId);
    return {
        ...settings,
        colorOverrides: { ...(settings.colorOverrides || {}), ...(page?.colors || {}) },
    };
}

function paintColorSlots(settings) {
    const colors = resolveColors(mergedColorSettings(settings));
    COLOR_SLOTS.forEach(({ id }) => {
        const input = document.querySelector(`[data-color-slot="${id}"]`);
        if (input) input.value = colors[id];
    });
}

function paintColorScope() {
    document.querySelectorAll('[data-color-scope]').forEach((btn) => {
        btn.classList.toggle('is-selected', btn.getAttribute('data-color-scope') === colorScope);
    });
    const select = document.getElementById('colorPageSelect');
    const label = document.getElementById('colorPageSelectLabel');
    const clearBtn = document.getElementById('clearPageColorsBtn');
    const note = document.getElementById('colorScopeNote');
    const pages = homeLayoutCache?.pages || [];
    if (select) {
        const current = colorPageId || homeLayoutCache?.active_page_id || pages[0]?.id || '';
        colorPageId = current;
        select.innerHTML = pages
            .map((page) => `<option value="${utils.escapeHtml(page.id)}"${page.id === current ? ' selected' : ''}>${utils.escapeHtml(page.name)}</option>`)
            .join('');
        select.hidden = colorScope !== 'page';
    }
    if (label) label.hidden = colorScope !== 'page';
    if (clearBtn) clearBtn.hidden = colorScope !== 'page';
    if (note) {
        if (colorScope === 'page') {
            const page = pages.find((p) => p.id === colorPageId);
            const n = Object.keys(page?.colors || {}).length;
            note.textContent = page
                ? `Editing “${page.name}”. ${n ? `${n} color${n === 1 ? '' : 's'} override the palette on this page.` : 'No overrides yet — pick a slot to color only this page.'}`
                : 'Add a Home page first.';
        } else {
            note.textContent = 'These colors apply to every Home page that does not set its own.';
        }
    }
    if (colorScope === 'page') {
        applyAppearanceOverlay((pages.find((p) => p.id === colorPageId) || {}).colors || {});
    }
}

function paintInk(settings) {
    const auto = document.getElementById('inkAutoToggle');
    if (auto) auto.checked = settings.inkAuto !== false;
    const inkInput = document.getElementById('inkColorInput');
    if (inkInput) {
        inkInput.value = resolveInk(settings);
        inkInput.title = settings.inkAuto !== false ? 'Auto from accent — click to override' : 'Custom button ink';
    }
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
    if (colorScope === 'page') {
        return setPageColorSlot(slot, value);
    }
    const current = getAppearance();
    const colorOverrides = { ...(current.colorOverrides || {}), [slot]: value };
    const patch = { colorOverrides };
    if (slot === 'accent') {
        patch.accent = 'custom';
        patch.customAccent = value;
    }
    return update(patch);
}

async function setPageColorSlot(slot, value) {
    if (typeof eel === 'undefined' || !eel.set_home_page_colors || !eel.get_home_layout) return;
    const pageId = colorPageId || homeLayoutCache?.active_page_id;
    if (!pageId) return;
    try {
        if (!homeLayoutCache) homeLayoutCache = await eel.get_home_layout()();
        const page = (homeLayoutCache.pages || []).find((p) => p.id === pageId);
        const colors = { ...(page?.colors || {}), [slot]: value };
        homeLayoutCache = await eel.set_home_page_colors(pageId, colors)();
        applyAppearanceOverlay((homeLayoutCache.pages.find((p) => p.id === pageId) || {}).colors || {});
        paintColorSlots(getAppearance());
        paintColorScope();
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not save page colors.');
    }
}

async function clearPageColors() {
    if (typeof eel === 'undefined' || !eel.set_home_page_colors) return;
    const pageId = colorPageId || homeLayoutCache?.active_page_id;
    if (!pageId) return;
    try {
        homeLayoutCache = await eel.set_home_page_colors(pageId, {})();
        applyAppearanceOverlay({});
        paintColorSlots(getAppearance());
        paintColorScope();
        utils.showSuccessFeedback('This page uses the shared palette again.');
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not clear page colors.');
    }
}

async function loadHomeLayoutForColors() {
    if (typeof eel === 'undefined' || !eel.get_home_layout) return;
    try {
        homeLayoutCache = await eel.get_home_layout()();
        if (!colorPageId) colorPageId = homeLayoutCache.active_page_id || '';
        paintColorScope();
        paintColorSlots(getAppearance());
    } catch (_) {
        /* eel not ready */
    }
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
    const name = await utils.askText({
        title: 'New palette',
        message: 'Name this color palette.',
        value: 'My palette',
        ok: 'Save palette',
    });
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
    const ok = await utils.askConfirm({
        title: 'Delete palette',
        message: `Delete “${preset.name}”?`,
        ok: 'Delete',
        danger: true,
    });
    if (!ok) return current;
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
        void loadHomeLayoutForColors();
        void loadClunySettings();
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
        const expanded = getAppearance().sidebar !== 'compact';
        const next = expanded ? 'compact' : 'expanded';
        update({ sidebar: next });
    });

    document.getElementById('colorScopeGroup')?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-color-scope]');
        if (!btn) return;
        colorScope = btn.getAttribute('data-color-scope') === 'page' ? 'page' : 'global';
        if (colorScope === 'global') {
            applyAppearance(getAppearance());
        }
        paintColorScope();
        paintColorSlots(getAppearance());
    });
    document.getElementById('colorPageSelect')?.addEventListener('change', (e) => {
        colorPageId = e.target.value;
        paintColorScope();
        paintColorSlots(getAppearance());
    });
    document.getElementById('clearPageColorsBtn')?.addEventListener('click', () => {
        void clearPageColors();
    });
    document.getElementById('clunySaveBtn')?.addEventListener('click', () => {
        void saveClunySettings();
    });
    document.getElementById('clunyTestBtn')?.addEventListener('click', () => {
        void testClunyConnection();
    });
    document.getElementById('clunyRestartBtn')?.addEventListener('click', () => {
        void restartClunyBrain();
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
    void loadHomeLayoutForColors();
    void loadClunySettings();
    setupSettingsResize();
}

export function onSettingsTabShown() {
    paintSettings(getAppearance());
    void loadAdvancedPaths();
    void loadIcloudSync();
    void loadHomeLayoutForColors();
    void loadClunySettings();
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

function setupSettingsResize() {
    const board = document.getElementById('settingsBoard');
    if (!board || board.dataset.resizeReady === '1') return;
    board.dataset.resizeReady = '1';
    const cols = () => [...board.querySelectorAll('.settings-col')];
    try {
        const saved = JSON.parse(localStorage.getItem(SETTINGS_COLS_KEY) || 'null');
        if (Array.isArray(saved) && saved.length === cols().length) {
            cols().forEach((col, i) => {
                const fr = Number(saved[i]);
                if (Number.isFinite(fr) && fr > 0) col.style.flex = `${fr} 1 0`;
            });
        }
    } catch (_) {
        /* ignore */
    }
    board.querySelectorAll('.settings-resize').forEach((handle) => {
        handle.addEventListener('pointerdown', (e) => {
            if (e.button != null && e.button !== 0) return;
            e.preventDefault();
            const index = Number(handle.getAttribute('data-resize'));
            const list = cols();
            const left = list[index];
            const right = list[index + 1];
            if (!left || !right) return;
            const startX = e.clientX;
            const leftW = left.getBoundingClientRect().width;
            const rightW = right.getBoundingClientRect().width;
            try {
                handle.setPointerCapture(e.pointerId);
            } catch (_) {
                /* still track on the handle */
            }
            const move = (ev) => {
                const dx = ev.clientX - startX;
                left.style.flex = `0 0 ${Math.max(200, leftW + dx)}px`;
                right.style.flex = `0 0 ${Math.max(200, rightW - dx)}px`;
            };
            const up = () => {
                handle.removeEventListener('pointermove', move);
                handle.removeEventListener('pointerup', up);
                const widths = cols().map((col) => col.getBoundingClientRect().width);
                const total = widths.reduce((sum, n) => sum + n, 0) || 1;
                try {
                    localStorage.setItem(SETTINGS_COLS_KEY, JSON.stringify(widths.map((n) => n / total)));
                } catch (_) {
                    /* quota */
                }
                cols().forEach((col, i) => {
                    col.style.flex = `${widths[i] / total} 1 0`;
                });
            };
            handle.addEventListener('pointermove', move);
            handle.addEventListener('pointerup', up);
        });
    });
}

function paintClunyHealth(probe) {
    const el = document.getElementById('clunyHealthStatus');
    if (!el) return;
    if (probe?.brain_ready) {
        const ollama = probe.ollama_ok ? 'Ollama is up.' : 'Ollama is not ready.';
        const managed = probe.managed ? 'Kosistenz is running Cluny.' : 'Cluny was already running.';
        el.textContent = `Brain ready. ${managed} ${ollama}`;
        return;
    }
    if (probe?.auto_start === false) {
        el.textContent = 'Auto-start is off. Start Cluny manually or enable it below.';
        return;
    }
    el.textContent = probe?.message || probe?.offline_copy || 'Cluny is starting…';
}

function paintClunySettings(cfg) {
    const sqlite = document.getElementById('clunySqlitePath');
    const url = document.getElementById('clunyIngestUrl');
    const brain = document.getElementById('clunyBrainUrl');
    const key = document.getElementById('clunyApiKey');
    const journal = document.getElementById('clunyJournalToggle');
    const checklist = document.getElementById('clunyChecklistToggle');
    const autoStart = document.getElementById('clunyAutoStartToggle');
    const binaryPath = document.getElementById('clunyBinaryPath');
    const status = document.getElementById('clunyStatus');
    const envNote = document.getElementById('clunyEnvNote');
    if (sqlite) {
        sqlite.value = cfg.sqlite_path || '';
        sqlite.readOnly = !!cfg.env_overrides?.sqlite_path;
    }
    if (brain) {
        brain.value = cfg.brain_url || 'http://127.0.0.1:8787';
        brain.readOnly = !!cfg.env_overrides?.brain_url;
    }
    if (url) {
        url.value = cfg.ingest_url || '';
        url.readOnly = !!cfg.env_overrides?.ingest_url;
    }
    if (key) {
        key.value = cfg.api_key || '';
        key.readOnly = !!cfg.env_overrides?.api_key;
    }
    if (journal) journal.checked = cfg.journal_enabled !== false;
    if (checklist) checklist.checked = cfg.checklist_enabled !== false;
    if (autoStart) autoStart.checked = cfg.auto_start_brain !== false;
    if (binaryPath) binaryPath.value = cfg.cluny_binary_path || '';
    if (status) status.textContent = cfg.status_note || '';
    if (envNote) {
        envNote.textContent = cfg.env_note || '';
    }
}

async function refreshClunyHealth() {
    if (typeof eel === 'undefined' || !eel.get_cluny_health) return;
    try {
        paintClunyHealth(await eel.get_cluny_health()());
    } catch (_) {
        paintClunyHealth({ brain_ready: false });
    }
}

async function loadClunySettings() {
    if (typeof eel === 'undefined' || !eel.get_cluny_settings) return;
    try {
        paintClunySettings(await eel.get_cluny_settings()());
    } catch (_) {
        /* eel not ready */
    }
    void refreshClunyHealth();
}

async function testClunyConnection() {
    const el = document.getElementById('clunyHealthStatus');
    if (el) el.textContent = 'Checking Cluny…';
    if (typeof eel === 'undefined' || !eel.probe_cluny_connection) {
        paintClunyHealth({ brain_ready: false });
        return;
    }
    try {
        const probe = await eel.probe_cluny_connection()();
        paintClunyHealth(probe);
        if (probe?.brain_ready) {
            utils.showSuccessFeedback('Cluny is reachable.');
        } else {
            utils.showErrorFeedback(probe?.offline_copy || 'Cluny is off.');
        }
    } catch (err) {
        paintClunyHealth({ brain_ready: false });
        utils.showErrorFeedback(err?.message || 'Cluny is off.');
    }
}

async function restartClunyBrain() {
    const el = document.getElementById('clunyHealthStatus');
    if (el) el.textContent = 'Restarting Cluny…';
    if (typeof eel === 'undefined' || !eel.restart_cluny_brain) return;
    try {
        const probe = await eel.restart_cluny_brain()();
        paintClunyHealth(probe);
    } catch (err) {
        console.error(err);
        if (el) el.textContent = err?.message || 'Could not restart Cluny.';
    }
}

async function saveClunySettings() {
    if (typeof eel === 'undefined' || !eel.save_cluny_settings) return;
    const payload = {
        sqlite_path: document.getElementById('clunySqlitePath')?.value || '',
        ingest_url: document.getElementById('clunyIngestUrl')?.value || '',
        brain_url: document.getElementById('clunyBrainUrl')?.value || '',
        api_key: document.getElementById('clunyApiKey')?.value || '',
        journal_enabled: !!document.getElementById('clunyJournalToggle')?.checked,
        checklist_enabled: !!document.getElementById('clunyChecklistToggle')?.checked,
        auto_start_brain: !!document.getElementById('clunyAutoStartToggle')?.checked,
        cluny_binary_path: document.getElementById('clunyBinaryPath')?.value || '',
    };
    try {
        const saved = await eel.save_cluny_settings(payload)();
        paintClunySettings(saved);
        utils.showSuccessFeedback('Cluny settings saved.');
        void refreshClunyHealth();
    } catch (err) {
        utils.showErrorFeedback(err?.message || 'Could not save Cluny settings.');
    }
}
