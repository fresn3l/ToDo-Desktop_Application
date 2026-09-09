/**
 * Load a tab or Home overlay only when it is shown.
 */

const ready = new Map();

export async function bootFeature(name) {
    if (!name || typeof eel === 'undefined' || typeof eel.boot_feature !== 'function') return;
    try {
        await eel.boot_feature(name)();
    } catch (err) {
        console.error(err);
    }
}

export async function loadOnce(key, loader) {
    if (!ready.has(key)) {
        ready.set(key, Promise.resolve().then(loader));
    }
    return ready.get(key);
}
