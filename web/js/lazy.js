/**
 * Load a tab or Home overlay only when it is shown.
 */

const ready = new Map();

export function hasEel(name) {
    return typeof eel !== 'undefined' && typeof eel[name] === 'function';
}

export function eelErrorMessage(err) {
    if (err == null) return '';
    if (typeof err === 'string') return err;
    if (typeof err.errorText === 'string' && err.errorText.trim()) return err.errorText;
    if (typeof err.message === 'string' && err.message.trim()) return err.message;
    if (typeof err.error === 'string' && err.error.trim()) return err.error;
    try {
        const packed = JSON.stringify(err);
        if (packed && packed !== '{}' && packed !== 'null') return packed;
    } catch (_) {
        /* ignore */
    }
    return '';
}

export async function callEel(name, ...args) {
    try {
        if (hasEel(name)) {
            return await eel[name](...args)();
        }
        if (hasEel('invoke_exposed')) {
            return await eel.invoke_exposed(name, args)();
        }
    } catch (err) {
        const detail = eelErrorMessage(err) || `${name} failed`;
        const wrapped = new Error(detail);
        wrapped.cause = err;
        throw wrapped;
    }
    throw new Error(`${name} is not ready. Restart Kosistenz.`);
}

export async function bootFeature(name) {
    if (!name || !hasEel('boot_feature')) return;
    try {
        await eel.boot_feature(name)();
    } catch (err) {
        console.error(eelErrorMessage(err) || err);
    }
}

export async function loadOnce(key, loader) {
    if (!ready.has(key)) {
        ready.set(key, Promise.resolve().then(loader));
    }
    return ready.get(key);
}
