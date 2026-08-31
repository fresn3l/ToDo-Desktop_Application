# Sprint: iPhone companion + iCloud sync

One person. One Apple ID. No Kosistenz server. The Mac stays the full app. The iPhone is a Today companion that reads and writes the same records.

## Why not wrap the Mac UI

The Mac app is Python + a local WebView. That will not run on an iPhone, and the phone cannot host `127.0.0.1`. A second WebView talking to the Mac only works when the laptop is awake on the same Wi‑Fi. That is not sync.

## How sync works

Apple already moves files between your Mac and iPhone when both are signed into the same iCloud account.

We do **not** put the live SQLite files in iCloud (WAL + two writers will corrupt them). Both apps talk to a **JSON pack** in:

`iCloud Drive / Kosistenz/`

On a Mac that folder is:

`~/Library/Mobile Documents/com~apple~CloudDocs/Kosistenz`

If iCloud Drive is off, the pack lives at `Application Support/ToDo/iCloudPack` so export still works.

Pack files:

| File | Contents |
| --- | --- |
| `manifest.json` | Schema version, last writer, timestamps |
| `work.json` | To Do items, repeating series, exceptions |
| `workouts.json` | Sessions, day notes / weight, week template |
| `journal.json` | Journal entries |
| `appearance.json` | Theme and Today layout |

Merge rule: **newer `updated_at` wins** for a given id, unless the stamp is more than a day in the future. Workout sessions are append-only by id. Journal entries are append-only by id. Import only writes under the journal folder; the Mac Settings RPC cannot point the pack at an arbitrary path.

The Mac writes the pack after a Today / To Do / Workout / Journal change (when auto-sync is on). Settings also has **Push to iCloud** and **Pull from iPhone**.

## What this sprint ships

1. Python pack export / import + tests.
2. Settings → Phone: folder path, auto-sync, push, pull.
3. SwiftUI iPhone skeleton (`ios/`) that opens the same pack: today’s to-dos, workout chips, a journal line.
4. This plan, replacing the old checklist-era `docs/next-sprint.md`.

## What you do on a Mac to run the iPhone app

1. Rebuild Kosistenz (`./macos/install_app.sh`) so Settings can push the pack.
2. Confirm iCloud Drive is on for your Apple ID.
3. Open `ios/README.md` and create/open the Xcode iOS app (needs a Mac with Xcode). First run uses your personal team; no App Store account is required for a device you own.
4. Sign both devices into the same iCloud account. After a push from the Mac, the phone should see `Kosistenz` in the Files app under iCloud Drive.

## Later sprints (not this one)

**Sprint 2 (next):** [iphone-sprint-2.md](iphone-sprint-2.md) — same iCloud
Drive folder on both devices, expected workout + miles, real journal, Mac
auto-pull, Xcode project. Widget only after the folder is actually shared.

After that, still out of scope until you ask:

- CloudKit records (better conflicts than last-write-wins).
- Analytics / Timeline / Settings on iPhone.
- App Store signing and a paid Apple Developer account (only if you want TestFlight or the store).
