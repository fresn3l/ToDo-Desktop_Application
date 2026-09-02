/**
 * Home weather widget — forecast and rain chance via the Python Open-Meteo proxy.
 */

import * as utils from './utils.js';

function hasEel(name) {
    return typeof eel !== 'undefined' && typeof eel[name] === 'function';
}

function paintUnits(units) {
    document.querySelectorAll('#weatherUnits [data-value]').forEach((btn) => {
        btn.classList.toggle('is-selected', btn.getAttribute('data-value') === (units || 'fahrenheit'));
    });
}

function rainLine(data) {
    const rain = data.next_rain;
    if (!rain) return 'No rain likely in the next hours';
    const when = rain.at || 'soon';
    return `${rain.chance}% chance around ${when}`;
}

function paintCurrent(data) {
    const el = document.getElementById('weatherCurrent');
    if (!el) return;
    if (!data?.ok) {
        el.innerHTML = '';
        return;
    }
    const cur = data.current || {};
    const unit = data.unit_symbol || '°';
    const temp = cur.temp == null ? '—' : `${cur.temp}${unit}`;
    const feel = cur.feels == null ? '' : `Feels ${cur.feels}${unit}`;
    const wind = cur.wind == null ? '' : `${cur.wind} ${data.wind_unit || ''}`.trim();
    const humidity = cur.humidity == null ? '' : `${cur.humidity}% humidity`;
    const bits = [feel, wind, humidity].filter(Boolean).join(' · ');
    el.innerHTML = `
        <p class="weather-temp">${utils.escapeHtml(String(temp))}</p>
        <div class="weather-current-copy">
            <p class="weather-label">${utils.escapeHtml(cur.label || '')}</p>
            <p class="weather-precip">${utils.escapeHtml(`${cur.precip_chance ?? 0}% rain now`)}</p>
            <p class="weather-meta">${utils.escapeHtml(bits)}</p>
            <p class="weather-next">${utils.escapeHtml(rainLine(data))}</p>
        </div>`;
}

function paintHourly(data) {
    const el = document.getElementById('weatherHourly');
    if (!el) return;
    const rows = data?.hourly || [];
    if (!rows.length) {
        el.innerHTML = '';
        return;
    }
    el.innerHTML = rows
        .map((row) => {
            const pct = Math.max(0, Math.min(100, Number(row.precip_chance) || 0));
            return `<li title="${utils.escapeHtml(row.label || '')}">
                <span>${utils.escapeHtml(row.hour || '')}</span>
                <span class="weather-hour-track" aria-hidden="true"><i style="height:${pct}%"></i></span>
                <em>${pct}%</em>
            </li>`;
        })
        .join('');
}

function paintDaily(data) {
    const el = document.getElementById('weatherDaily');
    if (!el) return;
    const rows = data?.daily || [];
    if (!rows.length) {
        el.innerHTML = '';
        return;
    }
    const unit = data.unit_symbol || '°';
    el.innerHTML = rows
        .map((row) => {
            const high = row.high == null ? '—' : `${row.high}${unit}`;
            const low = row.low == null ? '—' : `${row.low}${unit}`;
            return `<li>
                <span>${utils.escapeHtml(row.day || '')}</span>
                <span class="weather-daily-label">${utils.escapeHtml(row.label || '')}</span>
                <span class="weather-daily-temps">${utils.escapeHtml(high)} / ${utils.escapeHtml(low)}</span>
                <em>${Number(row.precip_chance) || 0}%</em>
            </li>`;
        })
        .join('');
}

function paintStatus(data) {
    const el = document.getElementById('weatherStatus');
    const place = document.getElementById('weatherPlace');
    const sub = document.getElementById('weatherSub');
    if (place) {
        if (data?.ok) place.textContent = data.place || 'Weather';
        else if (data?.need_place) place.textContent = 'Set a place';
        else place.textContent = 'Weather';
    }
    if (sub) {
        if (data?.ok && data.stale) sub.textContent = 'Last good forecast — could not refresh';
        else if (data?.ok) sub.textContent = rainLine(data);
        else if (data?.need_place) sub.textContent = 'Search a city.';
        else sub.textContent = data?.error ? 'Could not load forecast' : '';
    }
    if (el) {
        if (data?.ok) el.textContent = '';
        else if (data?.error) el.textContent = data.error;
        else el.textContent = '';
    }
    const form = document.getElementById('weatherPlaceForm');
    if (form) {
        if (data?.ok) {
            if (!form.classList.contains('is-open')) form.classList.add('is-collapsed');
        } else {
            form.classList.remove('is-collapsed');
            form.classList.remove('is-open');
        }
    }
    paintUnits(data?.units || data?.settings?.units);
}

function paintResults(places) {
    const el = document.getElementById('weatherPlaceResults');
    if (!el) return;
    if (!places?.length) {
        el.innerHTML = '';
        return;
    }
    el.innerHTML = places
        .map(
            (row, index) =>
                `<button type="button" class="btn-ghost weather-place-result" data-index="${index}">${utils.escapeHtml(row.label || row.place)}</button>`,
        )
        .join('');
    el._places = places;
}

export function paintWeather(data) {
    paintCurrent(data);
    paintHourly(data);
    paintDaily(data);
    paintStatus(data);
}

export async function refreshWeather(force = false) {
    if (!hasEel('get_weather_forecast')) return;
    try {
        const data = await eel.get_weather_forecast(!!force)();
        paintWeather(data);
    } catch (err) {
        console.error(err);
        paintWeather({ ok: false, error: err?.message || 'Could not load weather' });
    }
}

export function setupWeather() {
    const units = document.getElementById('weatherUnits');
    if (units && units.dataset.ready !== '1') {
        units.dataset.ready = '1';
        units.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-value]');
            if (!btn || !hasEel('set_weather_units')) return;
            void (async () => {
                try {
                    const data = await eel.set_weather_units(btn.getAttribute('data-value'))();
                    paintWeather(data);
                } catch (err) {
                    console.error(err);
                    utils.showErrorFeedback(err?.message || 'Could not change units.');
                }
            })();
        });
    }

    const form = document.getElementById('weatherPlaceForm');
    if (form && form.dataset.ready !== '1') {
        form.dataset.ready = '1';
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const query = document.getElementById('weatherPlaceQuery')?.value.trim() || '';
            if (!query || !hasEel('search_weather_places')) return;
            void (async () => {
                try {
                    const places = await eel.search_weather_places(query)();
                    paintResults(places);
                    if (!places.length) utils.showErrorFeedback('No matching places.');
                } catch (err) {
                    console.error(err);
                    utils.showErrorFeedback(err?.message || 'Could not search.');
                }
            })();
        });
    }

    const results = document.getElementById('weatherPlaceResults');
    if (results && results.dataset.ready !== '1') {
        results.dataset.ready = '1';
        results.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-index]');
            if (!btn || !hasEel('set_weather_place')) return;
            const places = results._places || [];
            const place = places[Number(btn.getAttribute('data-index'))];
            if (!place) return;
            void (async () => {
                try {
                    const data = await eel.set_weather_place(place)();
                    paintResults([]);
                    const query = document.getElementById('weatherPlaceQuery');
                    if (query) query.value = '';
                    form?.classList.remove('is-open');
                    paintWeather(data);
                } catch (err) {
                    console.error(err);
                    utils.showErrorFeedback(err?.message || 'Could not save that place.');
                }
            })();
        });
    }

    const change = document.getElementById('weatherChangePlace');
    if (change && change.dataset.ready !== '1') {
        change.dataset.ready = '1';
        change.addEventListener('click', () => {
            form?.classList.add('is-open');
            form?.classList.remove('is-collapsed');
            document.getElementById('weatherPlaceQuery')?.focus();
        });
    }
}
