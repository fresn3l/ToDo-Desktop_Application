# Next sprint

Ship the current PR (`cursor/kosistenz-ui-redesign-7484`) as the Kosistenz `main` line, then use this list. Work is ordered by user-visible payoff vs. risk.

## 1. Review should match how people actually check in

Review still treats only `exercise_yn` (default) and `exercise_done` (evening) as exercise. Morning uses `planned_workout`, so those days never count.

- Count completed exercise from default + evening.
- Do not treat morning *intent* as a session.
- Split “days with exercise” from “sessions” if both templates are used on the same day.
- Show checklist titles in the breakdown, not raw ids (`default`, `evening`).

## 2. Wizard progress should follow the path taken

“3 of 8” counts every node in the JSON, including skipped branches (workout type, etc.). Progress often never reaches 100%.

- Estimate remaining steps from the current node (follow `next` / `onYes` / `onNo` / first option).
- Keep extras as a known tail (`+ N custom questions`).
- Recap is fine as-is.

## 3. One answer formatter

The same yes/no / other / duration shape is formatted in three places:

- `daily_checklist._format_answer_value`
- `web/js/daily_checklist.js` `formatPreviewValue`
- `export_data._flatten_answer`

Use one Python formatter for history, timeline, and CSV. Keep a thin JS helper only for the live wizard recap.

## 4. Packaging that matches the running app

There are three launch stories. Pick one supported path and delete or clearly mark the others.

- Keep the repo launcher (`macos/install_app.sh`) as the daily driver.
- PyInstaller (`build_app.py`) should include `macos/kosistenz-reminder.sh` (and any other runtime scripts). Frozen reminders currently look next to the Python module and miss the script.
- `setup.py` (py2app) is stale: it omits `appearance.js`, `settings.js`, `weekstrip.js`. Either update it or remove it so nobody ships a broken build.
- Update README clone path (`intelligent_to-do_list` is leftover).

## 5. Data directory and appearance defaults

- Journal still builds its own `…/ToDo/Journal` path instead of `get_data_directory() / "Journal"`.
- Appearance defaults live in both `appearance.py` and `web/js/appearance.js`. One source (Python) with the JS file as a cache is enough.

## 6. Journal performance

`_load_entries_from_disk` still walks every year/month/week file, then filters. Fine for months of use; slow after years.

- Skip year/month folders outside the cutoff from the folder names.
- Optional later: an index JSON or SQLite sidecar for tags/dates only.

## 7. Health import honesty

Overnight sleep is assigned to the start timestamp and timezones are stripped with `replace(tzinfo=None)`. Late-night sleep can land on the wrong local day.

- Bucket sleep by local end date, or split across midnight.
- Keep Screen Time disabled until there is a real source.

## 8. Daily-use polish left on the table

- Focus mode on the first keystroke is surprising. Make auto-focus a setting, default off; keep the Focus button.
- Move reminder setup from `daily_checklist.js` into `settings.js`.
- Persist the last Timeline date and last checklist template more obviously.
- Empty week-strip days should still feel clickable (they are) but the empty state on Timeline could say “Nothing on this day — write or check in.”

## 9. Tests worth adding

No automated tests today. A small `pytest` suite on the Python side would lock the last regressions:

- `fetch_submissions` by `local_date` / range returns rows older than the recent-list cap.
- Export count equals SQLite `COUNT(*)`.
- Journal `continued` is true whenever overtime is true.
- Recovery does not prompt before the first real check-in.

Skip UI screenshot tests until the shell is stable on `main`.

## Out of scope this sprint

- New analytics engine or charts.
- Another theme pack.
- Rebuilding the ToDo tasks/goals app inside Kosistenz.
- Re-enabling Screen Time.
