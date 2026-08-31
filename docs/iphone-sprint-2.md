# Sprint 2: iPhone you can actually use away from the Mac

Sprint 1 ([iphone-sprint.md](iphone-sprint.md), PR #17) shipped a **companion
skeleton**, not a daily phone app. This sprint is the one that makes Kosistenz
worth putting on the Home Screen.

**Depends on:** sprint 1 merged, or keep this branch stacked on
`cursor/iphone-icloud-7484`. Rebuild the Mac app from that work
(`./macos/install_app.sh`) before testing.

This Linux environment cannot compile or install to a phone. Install and
device testing happen on your Mac + iPhone.

---

## What “done” feels like

You leave the house with only the phone.

1. Open Kosistenz. Today’s to-dos are there. Check one off in a second.
2. The workout the week template actually planned for this weekday is
   highlighted. If it is a run, you type miles. If it is Other, you type a name.
3. You write a journal on a full-screen editor, not a one-line field.
4. You do **not** open Settings on the Mac to “make sync happen.” Pull-to-refresh
   or Sync now on the phone is enough. When you sit down at the Mac later,
   Today already has the check, the miles, and the journal.

If any of those four fail, the sprint is not done.

---

## What we will not do

- Rewrite sync as CloudKit.
- Ship Analytics, Timeline, or Settings on the phone.
- App Store / TestFlight (your Apple ID, your device).
- Edit repeating series or the week workout template from the phone.
- Put live SQLite in iCloud.

---

## Inventory: what sprint 1 actually left

Grounded in `ios/Kosistenz/` and `icloud_sync.py` as of this plan.

| Area | Today | Gap |
|------|--------|-----|
| Pack format | Mac writes `work.json`, `workouts.json`, `journal.json`, `appearance.json` to iCloud Drive / Kosistenz (`com~apple~CloudDocs`) | Phone reads a **different** folder: the app’s ubiquity container `Documents/Kosistenz`. They will not see each other’s files until this is fixed. |
| To-dos | Toggle + add for today | Fine for daily use. No All Work inbox. |
| Workout | Five equal chips; run is stored with `miles: 0`; Other is stored as `"Other"` | Mac **rejects** a run without miles and Other without a name (`workouts.add_workout_session`). Phone logging is not a real log. Template is already in the pack; the phone never reads it, so nothing is highlighted as expected. |
| Journal | `TextField` + Save, append-only by id | Not a writing surface. No “already wrote today” state. |
| Sync UX | Pull-to-refresh, `Data(contentsOf:)` | No `NSFileCoordinator`, no last-sync time, no “waiting for iCloud.” Mac only **writes** on change (`export_if_enabled`); it never **pulls** unless you click Settings → Phone. |
| Install | Swift sources only | No checked-in `.xcodeproj`. `ios/README.md` still says create a project by hand. |

---

## Must ship

### 0. Same folder, or nothing else matters

**Problem:** The Mac pack lives at

`~/Library/Mobile Documents/com~apple~CloudDocs/Kosistenz`

The iPhone app uses `url(forUbiquityContainerIdentifier: nil)` → the **app’s**
iCloud container, not iCloud Drive. Settings copy that says “the iPhone app
reads this folder” is currently false.

**Do:**

- On first launch, if the pack is not found, present a folder picker
  (`UIDocumentPickerViewController` / `fileImporter`) aimed at iCloud Drive
  and store a **security-scoped bookmark** for `Kosistenz`.
- All reads and writes go through that bookmark, coordinated with
  `NSFileCoordinator`.
- Keep the local Documents fallback only when iCloud Drive is off, and say so
  in the UI (“On this iPhone only”).
- Do **not** switch the Mac writer to an app-specific container. Python cannot
  reliably use `iCloud.com.kosistenz…`; CloudDocs is the shared contract.

Until a Files-app `Kosistenz` folder is the same bytes on both devices, skip
widget work.

### 1. Expected workout from the week template

**Problem:** `TodayScreen` hard-codes `["push", "pull", "legs", "running", "other"]`
with no highlight. The pack already includes `workouts.template` (same JSON as
`workout_plan.json`).

**Do:** Port `workouts.expected_kinds_for_date` to Swift (weekday lifts +
running interval/weekdays). Highlight those chips the way
`web/js/workout_chips.js` does (`is-expected` / `is-logged`). Completing the
expected type is one tap; the others remain “I did something else.”

Do **not** add a new `expected_workout` field to the pack unless the Swift port
cannot match the Python tests. Prefer one source of truth: the template.

Add a focused Python test (or a documented fixture) so the Swift weekday
examples stay aligned with `tests/test_workouts.py`
(`test_expected_kinds_default_monday_push`).

### 2. Run miles and Other name

**Problem:** `logWorkout` writes `miles: 0` for running and `other_label: "Other"`
for other. The Mac will import those rows, but they are not valid logs by the
app’s own rules.

**Do:**

- After Run: a miles field. Write numeric `miles` (not a string stuffed into
  `other_label`). Refuse to save a run with no miles, same as the Mac.
- After Other: a short name field. Refuse empty names.
- Show existing sessions with miles / other name
  (`3.1 mi`, `Pickleball`), not only the kind.

Chip order should match the Mac: Push, Pull, Legs, Run, Other.

### 3. Journal that is actually writable

**Problem:** One `TextField` is not a journal.

**Do:**

- Full-screen `TextEditor` (sheet or second screen).
- Save on explicit Save; keep append-by-id.
- If today’s entry already exists, open it for edit (update that id’s
  `content` + `updated_at` if the pack grows that field; otherwise replace
  in the JSON array for that id). Do not silently create a second “today.”

### 4. Sync you can trust without a developer

**Phone:**

- `NSFileCoordinator` on every pack read/write.
- Visible last-sync time and a **Sync now** control (plus pull-to-refresh).
- States: pack found / waiting for iCloud / folder not chosen / error.
  A blank Today with no explanation is a bug.

**Mac:**

- On launch (and when the window becomes active), `pull_icloud_pack` if a pack
  exists and auto-write has been used at least once — or an explicit
  “Also pull when opening the app” setting, default on after the first
  successful push.
- Keep far-future `updated_at` ignored, pack size caps, and the allowed-folder
  rule from sprint 1.

### 5. Xcode project so you are not stuck

Add a checked-in `ios/Kosistenz.xcodeproj` (iOS 17+, SwiftUI, iCloud Documents
or the Files entitlement needed for the bookmark, bundle id you own). Update
`ios/README.md` so the steps match how you actually open it.

Without this, the sprint cannot be installed.

---

## Should ship if time

### Home Screen widget

Small / medium, read-only from the same bookmarked folder:

- Open to-dos remaining today
- Expected workout: done / not done
- Tap opens the app

Only after must-item 0 and 4. A widget that is a day stale is worse than none.

### Park a thought in All Work

One field: title → append an open item in `work.json` with no
`scheduled_date` (or whatever the Mac uses for unscheduled All Work). Inbox
capture, not a full All Work client.

---

## Stretch (only after must)

- Lock screen widget / Live Activity
- Apple Watch
- `kosistenz://` deep link from widget to a specific to-do

---

## Suggested order of work

1. **Shared folder** — bookmark + coordinator. Prove in Files that Mac push and
   phone save touch the same `Kosistenz` directory.
2. **Xcode project** — so the rest can run on a device.
3. **Expected kinds from template** — port the Python function; highlight chips.
4. **Miles + Other name** — match Mac validation.
5. **Journal UI**
6. **Mac auto-pull** + last-sync status
7. **Widget** if 1 and 6 are solid
8. **All Work capture** if anything is left

Do not start the widget before the folder and coordination exist.

---

## Files likely to change

| Area | Files |
|------|--------|
| Phone folder + I/O | `ios/Kosistenz/SyncPack.swift`, new bookmark helper |
| Phone UI | `ios/Kosistenz/TodayScreen.swift`, Journal view, `KosistenzApp.swift` |
| Expected kinds | new Swift helper; keep in lockstep with `workouts.expected_kinds_for_date` |
| Mac pull | `app.py` / window focus, Settings copy in `web/index.html`, `web/js/settings.js` |
| Pack (only if needed) | `icloud_sync.py`, `tests/test_icloud_sync.py` |
| Install | `ios/Kosistenz.xcodeproj`, `ios/README.md` |

Keep the pack schema backward compatible. Old packs without a template still
open; the phone then shows chips with no highlight, same as sprint 1.

---

## Test plan (your Mac + iPhone)

This environment cannot do these. You can.

1. After choosing the folder on the phone, Files → iCloud Drive → Kosistenz
   shows the same `work.json` the Mac just pushed.
2. Expected type on the phone matches Settings week template for that weekday
   (default Monday = push).
3. Log a run with miles on the phone. Mac Workout today shows that run and the
   miles number — not `0`.
4. Log Other with a name. Mac shows that name. Empty Other does not save.
5. Write a journal on the phone. Mac Today / Journal shows it.
6. Airplane mode: to-do toggle still works locally; when you reconnect, the
   pack updates. If iCloud will not write, the UI says so.
7. Kill the Mac app, change a to-do on the phone, open the Mac app: Today
   updates without opening Settings → Phone.
8. Widget (if shipped): remaining to-do count matches the phone screen.

Python tests still cover merge, path traversal, pack size, and far-future
timestamps. Run `python3 -m pytest tests/ -q` on any pack or Mac-pull change.

---

## Definition of done

- [ ] Phone and Mac read and write the same iCloud Drive / Kosistenz folder.
- [ ] Expected workout is obvious on the phone and can be logged with miles /
      Other name.
- [ ] Journal is a real writing surface.
- [ ] Phone shows last sync / waiting / error — not a blank today with no
      explanation.
- [ ] Mac picks up phone writes without a mandatory Settings visit.
- [ ] Xcode project is in the repo; `ios/README.md` matches how you open it.
- [ ] Widget is either shipped and accurate, or explicitly deferred in the
      README so you do not think it exists.
