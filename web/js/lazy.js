/**
 * Load a tab or Home overlay only when it is shown.
 */

const ready = new Map();

export function hasEel(name) {
    return typeof eel !== 'undefined' && typeof eel[name] === 'function';
}

export async function callEel(name, ...args) {
    if (hasEel(name)) {
        return eel[name](...args)();
    }
    if (hasEel('invoke_exposed')) {
        return eel.invoke_exposed(name, args)();
    }
    throw new Error(`${name} is not ready. Restart Kosistenz.`);
}

export async function bootFeature(name) {
    if (!name || !hasEel('boot_feature')) return;
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
