/**
 * Library tab — browse, search, and organize Cluny documents.
 */

import * as utils from './utils.js';

let activeCollection = '';
let activeSource = '';
let searchQuery = '';
let selectedDocId = '';
let selectedDocPath = '';
const selectedIds = new Set();
let allCollections = [];
let searchTimer = null;

function hasEel(name) {
    return typeof eel !== 'undefined' && typeof eel[name] === 'function';
}

function openModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('is-hidden');
    el.hidden = false;
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add('is-hidden');
    el.hidden = true;
}

function splitList(raw) {
    return String(raw || '')
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
}

function applyStats(stats) {
    const doc = document.getElementById('libraryDocCount');
    const chunks = document.getElementById('libraryChunkCount');
    const dir = document.getElementById('libraryDataDir');
    const line = document.getElementById('libraryStorageLine');
    if (doc) doc.textContent = stats?.doc_count ?? '—';
    if (chunks) chunks.textContent = stats?.chunk_count ?? '—';
    if (dir) dir.textContent = stats?.data_dir || '—';
    if (line && stats?.data_dir) {
        line.textContent = `Indexed storage at ${stats.data_dir}`;
    }
}

function paintCollections(collections, sources) {
    const list = document.getElementById('libraryCollectionList');
    if (!list) return;
    const items = ['<li><button type="button" class="library-filter-btn' + (!activeCollection ? ' is-active' : '') + '" data-library-collection="">All documents</button></li>'];
    (collections || []).forEach((name) => {
        const val = utils.escapeHtml(name);
        const active = activeCollection === name ? ' is-active' : '';
        items.push(`<li><button type="button" class="library-filter-btn${active}" data-library-collection="${val}">${val}</button></li>`);
    });
    list.innerHTML = items.join('');

    const srcList = document.getElementById('librarySourceList');
    if (!srcList) return;
    const srcItems = ['<li><button type="button" class="library-filter-btn' + (!activeSource ? ' is-active' : '') + '" data-library-source="">All sources</button></li>'];
    (sources || []).forEach((name) => {
        const val = utils.escapeHtml(name);
        const active = activeSource === name ? ' is-active' : '';
        srcItems.push(`<li><button type="button" class="library-filter-btn${active}" data-library-source="${val}">${val}</button></li>`);
    });
    srcList.innerHTML = srcItems.join('');
}

function paintDocList(docs) {
    const list = document.getElementById('libraryDocList');
    const bulkBtn = document.getElementById('libraryBulkDeleteBtn');
    if (!list) return;
    const rows = docs || [];
    if (!rows.length) {
        list.innerHTML = '<li class="library-doc-empty">No documents match.</li>';
        if (bulkBtn) bulkBtn.disabled = true;
        return;
    }
    list.innerHTML = rows.map((doc) => {
        const id = utils.escapeHtml(doc.id || '');
        const title = utils.escapeHtml(doc.title || doc.path || doc.id || 'Untitled');
        const kind = utils.escapeHtml(doc.kind || '');
        const source = doc.source ? utils.escapeHtml(doc.source) : '';
        const checked = selectedIds.has(doc.id) ? ' checked' : '';
        const active = selectedDocId === doc.id ? ' is-active' : '';
        const badges = [kind, source, doc.chunk_count != null ? `${doc.chunk_count} chunks` : '']
            .filter(Boolean)
            .map((b) => `<span class="library-badge">${utils.escapeHtml(b)}</span>`)
            .join('');
        return `<li class="library-doc-row${active}">
            <label class="library-doc-check"><input type="checkbox" data-library-select="${id}"${checked}></label>
            <button type="button" class="library-doc-btn" data-library-doc="${id}">
                <strong>${title}</strong>
                ${badges ? `<div class="library-doc-badges">${badges}</div>` : ''}
            </button>
        </li>`;
    }).join('');
    if (bulkBtn) bulkBtn.disabled = selectedIds.size === 0;
}

function showDetailEmpty() {
    document.getElementById('libraryDetailEmpty')?.classList.remove('is-hidden');
    const form = document.getElementById('libraryDetailForm');
    if (form) {
        form.classList.add('is-hidden');
        form.hidden = true;
    }
    selectedDocId = '';
    selectedDocPath = '';
}

async function loadDetail(docId) {
    if (!hasEel('library_get')) return;
    try {
        const doc = await eel.library_get(docId)();
        selectedDocId = doc.id || '';
        selectedDocPath = doc.path || '';
        document.getElementById('libraryDetailEmpty')?.classList.add('is-hidden');
        const form = document.getElementById('libraryDetailForm');
        if (form) {
            form.classList.remove('is-hidden');
            form.hidden = false;
        }
        document.getElementById('libraryDetailTitleInput').value = doc.title || '';
        document.getElementById('libraryDetailCollectionsInput').value = (doc.collections || []).join(', ');
        document.getElementById('libraryDetailTagsInput').value = (doc.tags || []).join(', ');
        document.getElementById('libraryDetailKind').textContent = doc.kind || '—';
        document.getElementById('libraryDetailChunks').textContent = doc.chunk_count ?? '—';
        document.getElementById('libraryDetailIngested').textContent = doc.ingested_at || '—';
        document.getElementById('libraryDetailPath').textContent = doc.path || '—';
        document.querySelectorAll('.library-doc-row').forEach((row) => {
            row.classList.toggle('is-active', row.querySelector(`[data-library-doc="${docId}"]`));
        });
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not load document.');
    }
}

async function refreshLibrary() {
    if (!hasEel('library_filters')) return;
    try {
        if (hasEel('library_stats')) {
            applyStats(await eel.library_stats()());
        }
        const filters = await eel.library_filters()();
        allCollections = filters?.collections || [];
        paintCollections(allCollections, filters?.sources || []);

        let docs = [];
        if (searchQuery.trim() && hasEel('library_search')) {
            const result = await eel.library_search(
                searchQuery.trim(),
                activeCollection,
                activeSource,
                100,
            )();
            docs = result?.documents || [];
        } else if (hasEel('library_list')) {
            const result = await eel.library_list(activeCollection, activeSource)();
            docs = result?.documents || [];
        }
        paintDocList(docs);
        if (selectedDocId && !docs.some((d) => d.id === selectedDocId)) {
            showDetailEmpty();
        }
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not refresh library.');
    }
}

export async function onLibraryTabShown() {
    await refreshLibrary();
}

async function saveDetail(event) {
    event.preventDefault();
    if (!selectedDocId || !hasEel('library_update')) return;
    try {
        await eel.library_update(selectedDocId, {
            title: document.getElementById('libraryDetailTitleInput')?.value || '',
            collections: splitList(document.getElementById('libraryDetailCollectionsInput')?.value),
            tags: splitList(document.getElementById('libraryDetailTagsInput')?.value),
        })();
        utils.showSuccessFeedback('Document updated.');
        await refreshLibrary();
        await loadDetail(selectedDocId);
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Save failed.');
    }
}

async function deleteSelectedDoc() {
    if (!selectedDocId || !hasEel('library_delete_doc')) return;
    const ok = await utils.askConfirm({
        title: 'Delete document',
        message: 'Delete this document from Cluny?',
        ok: 'Delete',
        danger: true,
    });
    if (!ok) return;
    try {
        await eel.library_delete_doc(selectedDocId)();
        utils.showSuccessFeedback('Document deleted.');
        selectedIds.delete(selectedDocId);
        showDetailEmpty();
        await refreshLibrary();
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Delete failed.');
    }
}

async function bulkDelete() {
    if (!selectedIds.size || !hasEel('library_delete_doc')) return;
    const ok = await utils.askConfirm({
        title: 'Delete documents',
        message: `Delete ${selectedIds.size} document(s) from Cluny?`,
        ok: 'Delete',
        danger: true,
    });
    if (!ok) return;
    for (const id of [...selectedIds]) {
        try {
            await eel.library_delete_doc(id)();
            selectedIds.delete(id);
        } catch (err) {
            console.error(err);
        }
    }
    if (selectedDocId && !selectedIds.has(selectedDocId)) {
        showDetailEmpty();
    }
    utils.showSuccessFeedback('Deleted selected documents.');
    await refreshLibrary();
}

async function uploadFiles(fileList) {
    if (!hasEel('library_upload_b64')) {
        utils.showErrorFeedback('Upload unavailable. Restart Kosistenz.');
        return;
    }
    const collection = document.getElementById('libraryUploadCollection')?.value || 'journal';
    const copy = !!document.getElementById('libraryUploadCopyToggle')?.checked;
    const status = document.getElementById('libraryUploadStatus');
    let done = 0;
    for (const file of fileList) {
        if (status) status.textContent = `Uploading ${file.name}…`;
        const buf = await file.arrayBuffer();
        const bytes = new Uint8Array(buf);
        let binary = '';
        for (let i = 0; i < bytes.length; i += 1) {
            binary += String.fromCharCode(bytes[i]);
        }
        const b64 = btoa(binary);
        try {
            await eel.library_upload_b64(file.name, b64, file.name, collection, copy)();
            done += 1;
        } catch (err) {
            console.error(err);
            utils.showErrorFeedback(err?.message || `Could not index ${file.name}`);
        }
    }
    if (status) status.textContent = done ? `Indexed ${done} file(s).` : '';
    if (done) {
        utils.showSuccessFeedback(`Indexed ${done} file(s).`);
        closeModal('libraryUploadDialog');
        await refreshLibrary();
    }
}

async function createCollection(event) {
    event.preventDefault();
    const name = document.getElementById('libraryNewCollectionInput')?.value?.trim();
    if (!name || !hasEel('library_create_collection')) return;
    try {
        await eel.library_create_collection(name)();
        utils.showSuccessFeedback(`Collection “${name}” created.`);
        closeModal('libraryNewCollectionDialog');
        document.getElementById('libraryNewCollectionInput').value = '';
        activeCollection = name;
        await refreshLibrary();
    } catch (err) {
        console.error(err);
        utils.showErrorFeedback(err?.message || 'Could not create collection.');
    }
}

export function setupLibrary() {
    const root = document.getElementById('libraryTab');
    if (!root || root.dataset.ready === '1') return;
    root.dataset.ready = '1';

    document.getElementById('libraryRefreshBtn')?.addEventListener('click', () => {
        void refreshLibrary();
    });
    document.getElementById('libraryOpenDataDirBtn')?.addEventListener('click', () => {
        if (hasEel('library_open_data_dir')) {
            eel.library_open_data_dir()();
        }
    });
    document.getElementById('libraryUploadBtn')?.addEventListener('click', () => {
        openModal('libraryUploadDialog');
        const status = document.getElementById('libraryUploadStatus');
        if (status) status.textContent = '';
    });
    document.getElementById('libraryUploadClose')?.addEventListener('click', () => {
        closeModal('libraryUploadDialog');
    });
    document.getElementById('libraryUploadPickBtn')?.addEventListener('click', () => {
        document.getElementById('libraryUploadFileInput')?.click();
    });
    document.getElementById('libraryUploadFileInput')?.addEventListener('change', (e) => {
        const files = e.target.files;
        if (files?.length) void uploadFiles(files);
        e.target.value = '';
    });
    document.getElementById('libraryNewCollectionBtn')?.addEventListener('click', () => {
        openModal('libraryNewCollectionDialog');
    });
    document.getElementById('libraryNewCollectionCancel')?.addEventListener('click', () => {
        closeModal('libraryNewCollectionDialog');
    });
    document.getElementById('libraryNewCollectionForm')?.addEventListener('submit', (e) => {
        void createCollection(e);
    });
    document.getElementById('librarySearchInput')?.addEventListener('input', (e) => {
        searchQuery = e.target.value || '';
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            void refreshLibrary();
        }, 250);
    });
    document.getElementById('libraryBulkDeleteBtn')?.addEventListener('click', () => {
        void bulkDelete();
    });
    document.getElementById('libraryDetailForm')?.addEventListener('submit', (e) => {
        void saveDetail(e);
    });
    document.getElementById('libraryDeleteDocBtn')?.addEventListener('click', () => {
        void deleteSelectedDoc();
    });
    document.getElementById('libraryRevealPathBtn')?.addEventListener('click', () => {
        if (selectedDocPath && hasEel('library_reveal_path')) {
            eel.library_reveal_path(selectedDocPath)();
        }
    });

    root.addEventListener('click', (event) => {
        const collBtn = event.target.closest('[data-library-collection]');
        if (collBtn) {
            activeCollection = collBtn.getAttribute('data-library-collection') || '';
            void refreshLibrary();
            return;
        }
        const srcBtn = event.target.closest('[data-library-source]');
        if (srcBtn) {
            activeSource = srcBtn.getAttribute('data-library-source') || '';
            void refreshLibrary();
            return;
        }
        const docBtn = event.target.closest('[data-library-doc]');
        if (docBtn) {
            void loadDetail(docBtn.getAttribute('data-library-doc'));
            return;
        }
        const check = event.target.closest('[data-library-select]');
        if (check) {
            const id = check.getAttribute('data-library-select');
            if (check.checked) selectedIds.add(id);
            else selectedIds.delete(id);
            const bulkBtn = document.getElementById('libraryBulkDeleteBtn');
            if (bulkBtn) bulkBtn.disabled = selectedIds.size === 0;
        }
    });
}
