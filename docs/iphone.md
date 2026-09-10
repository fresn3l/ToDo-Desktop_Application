# Kosistenz on iPhone

**Audience:** whoever next implements the phone, and anyone still reading the old sprint files.

This file is the **carry contract**. If `docs/iphone-sprint.md`, `docs/iphone-sprint-2.md`, `docs/next-sprint.md`, or `futureworkiphone.md` disagree with it, **this file wins**. Those older docs describe work that already shipped, or a Mac that no longer exists.

Kosistenz on the Mac is Home + a week clock + Fill week + check-in + Cluny. The iPhone is not a second copy of that app. It is the calendar you carry **between classes**, reading and writing the same records through the iCloud Drive pack.

---

## One sentence

**Mac commits the week. Phone lives the day.** The phone shows today’s clock and lets you act on what the Mac already packed. It does not Fill week, ask Cluny, or edit repeating series.

---

## What already exists (do not rebuild)

Grounded in `ios/` and `icloud_sync.py` on `main` after the calendar-home / appearance / iPhone-add-event work.

| Surface | What it does |
| --- | --- |
| Sync | Folder picker + security-scoped bookmark for **iCloud Drive / Kosistenz**. `NSFileCoordinator`. Local Documents fallback labeled “On this iPhone only.” |
| Pack | `manifest.json`, `work.json`, `workouts.json`, `journal.json`, `calendar.json`, `appearance.json`. Mac writes the week snapshot; phone writes work, workouts, journal, and **hard events** with `source: iphone`. |
| Today | Awake-window day clock, due chips, dated to-dos (toggle + add), expected workout chips with miles / Other name, journal teaser. **Add** a named busy block. |
| Week | Seven-day clock. **Add** one-off or weekly hard events. Packed study is visible, not draggable. |
| Journal | Full-screen editor; edits today’s entry instead of minting a second one. |
| Inbox | Park in All Work. Goals are **read-only**. Unplaced titles are listed with “pick a day on the Mac.” |
| Widget / Siri | Today’s to-dos (tap to toggle), next block line, expected gym. Intents: park, check off first to-do, log expected workout. |
| Look | Mac `appearance.json` `resolved` colors. No second theme picker. |

`futureworkiphone.md` (“add hard events from the phone”) is **done**. `iphone-sprint-2.md` (shared folder, miles, journal, Xcode project) is **done**. Treating those files as a backlog will rebuild shipped work.

---

## Why the phone feels outdated

The Mac product moved. The phone did not get the *actions* that make the clock a living day.

1. **Unplaced is a poster.** Today/Week list titles and say to place them on the Mac. Between classes you need **Today / tomorrow**, not a reminder that the laptop exists.
2. **Packed blocks are glass.** Skip, done, park, and +15 exist on the Mac clock. The pack slims blocks to `id, title, kind, status, start_at, end_at` — no `work_item_id`. The phone cannot change a block, and `apply_pack` **ignores** packed study from the phone on purpose.
3. **Due chips do not complete.** They paint. Checking off a Canvas due still means finding the matching to-do row, if it is dated today.
4. **Capture is thinner than All Work.** Phone to-dos have no estimate, so they sit undated-in-spirit until you type minutes on the Mac. Inbox cannot send a parked thought to today.
5. **Five tabs, one of them Sync.** The Mac is Home. The phone is a list of sections plus a whole tab for choosing a folder you already chose.
6. **This week only.** `calendar.json` is the Mac’s current week snapshot. Next Monday on the phone is empty until the Mac opens and pushes. There is no “Mac hasn’t published this week” state — just a blank clock.
7. **Check-in / now-next live only on Mac Home.** The phone has a clock but not the beat (“now · CHEM · next · 40m gap”).

None of that is fixed by wrapping the Mac WebView. The phone still cannot host `127.0.0.1`, and Cluny stays off when the laptop is asleep.

---

## Hard locks (unchanged)

- Live SQLite stays on the Mac. Sync stays the JSON pack in iCloud Drive / Kosistenz. **No CloudKit rewrite** in this plan.
- **No Fill week** on the phone. **No drag** of packed blocks to a new HH:MM.
- **No Ask Cluny**, Brain, or Library on the phone. Cluny never writes the pack.
- **No Apple Calendar write-back.**
- Phone may create **hard events** (`source: iphone`) and mutate **life records** (to-do status, scheduled day, workout session, journal text, block *status* on an id the Mac already packed). Phone may not invent packed study times.
- Repeating **series** and the **week workout template** stay Mac-only.
- Analytics, Timeline, Appearance editor, Home widget board stay Mac-only.
- App Store / TestFlight stay your Apple ID when you want them — not a blocker for the carry loop.

---

## Three kinds of phone writes

| Kind | Phone may | Mac `apply_pack` |
| --- | --- | --- |
| **Life** | Toggle to-do, add dated/undated work, park, log workout, edit today’s journal | Already merges (newer `updated_at`, append-only sessions/journal) |
| **Hard time** | Add/update named busy blocks `source: iphone` | Already upserts those events, then rewrites the canonical week into the pack |
| **Packed status** | Skip / done / park / +15 on a block **id that already exists** | **Not applied today.** Must start applying status (and `estimate_minutes` / `scheduled_date` on the pointed work item). Still ignore new `start_at`/`end_at` from the phone for `kind != hard`. |

That third row is the gap. Until it exists, the clock on the phone is a screenshot of the last Mac push.

---

## Pack (what has to exist that does not today)

`calendar.json` is a **read model** plus a small **write-back** of hard events. Widen the read model; add a narrow mutation channel.

### Mac → phone (publish)

Keep the week snapshot. Add fields the phone needs to act:

| Record | Add |
| --- | --- |
| **Block** | `work_item_id`, `minutes` (already on Mac clock items). Status stays. |
| **Unplaced** | `id`, `title`, `remaining_minutes` / `estimate_minutes`, `due_at`, `scheduled_date` — not title-only. |
| **Due** | `id` already present; phone toggles the matching **work item**, not a fake due row. |
| **Beat** (optional, or compute on device) | today’s `now` / `next` / `gap_minutes` from the same items. Prefer compute on the phone from `start_at` so a stale pack still ticks. |
| **Week stamp** | `week_start`, `week_end`, `exported_at` (manifest already has this). Phone shows “Week of 7 Sep · pushed 2h ago” or “This week isn’t in the pack yet — open Kosistenz on the Mac.” |

Do not publish Cluny inbox, check-in wizard JSON, or Home layout. Appearance `resolved` is enough.

Bump `SCHEMA` only if old phones would mis-parse. New keys must be ignored by old Swift; old packs without `work_item_id` still open (blocks stay read-only).

### Phone → Mac (apply)

Extend `_apply_calendar` / `_apply_work`:

1. **Work:** already last-write-wins. Phone `scheduled_date` (today / tomorrow / empty) must survive. Phone `estimate_minutes` on new items must survive.
2. **Blocks:** for each incoming block with an id that exists on the Mac, accept `status` in `{proposed, locked, done, skipped}` and ignore `start_at`/`end_at` unless `source == iphone` **and** `kind == hard`.
3. **Park from a block:** status + `work.assign_work_item(work_item_id, "")` on the Mac after pull.
4. **+15:** prefer mutating `estimate_minutes` / remaining on the work item in `work.json` (phone already owns work items). Do not let the phone rewrite block end times.
5. After apply, Mac **rewrites the pack** (already does) so the phone’s painted week matches Fill week / skip.

Conflicts: same rule as today — newer `updated_at` wins; stamps more than a day in the future are ignored. Two devices skipping the same block is fine (idempotent status).

---

## Phased roadmap

Phases are ownership-shaped, not calendar estimates. Kosistenz on the Mac stays fully usable at every phase. Each phase must preserve the hard locks.

### Phase 0 — Freeze the split (this document)

- This file is the contract. Old sprint docs point here.
- Do not start from “rebuild the skeleton.”
- Do not put Ask Cluny on the phone “so it feels like the Mac.”

**Done when:** the next phone PR cites this file, not `iphone-sprint-2.md`.

### Phase 1 — Carry actions (makes the app useful again)

**Goal:** leave the house with only the phone and finish what the Mac packed.

Today (and Inbox, if it still exists):

1. **Unplaced → Today / Tomorrow.** Writes `scheduled_date` on that work id. Copy matches Mac Unplaced glance chips.
2. **Due chip → done.** Same `toggle` as the to-do row (`id` is the work item).
3. **Block → Skip / Done / Park.** Phone writes status (and park clears `scheduled_date` via work.json). Mac apply accepts those statuses.
4. **Add to-do** gets an optional minutes field (default 60 if they type a number in the title, same as Mac “45 mins calculus”). Blank estimate is allowed; it stays unplaced.
5. **Inbox row → Today.** One tap, not “open the Mac.”

Widget: remaining open to-dos **and** “now / next” from today’s blocks (already has a next-block string — keep it honest after skip).

**Done when:** you can skip a study block, check off a due, and pull an unplaced item onto today without touching the laptop; opening the Mac does not resurrect the skipped block or duplicate the to-do.

Python tests: apply_pack honors phone block status; ignores phone-invented `start_at` on packed study; unplaced dump includes id + minutes + due. Swift cannot be compiled here — you run the device cases.

### Phase 2 — Today is one surface

**Goal:** the phone looks like a carry Home, not a settings list.

- **Today** is the home screen: now/next line, day clock, unplaced actions, today’s to-dos, expected workout, journal teaser, **Park** field.
- **Week** stays the seven-day clock + Add event.
- **Journal** stays full-screen.
- **Inbox** folds into Today (unscheduled list + park). Goals stay a short read-only section or disappear until you ask for them.
- **Sync** becomes a gear: folder, last push time, “waiting for iCloud,” Cluny-is-Mac-only note. Not a fifth tab.

Do **not** port the Mac Home widget grid, Edit Home, or extra pages.

**Done when:** a first-run user who already picked the folder never opens Sync to live the day, and Today is enough between two classes.

### Phase 3 — Trust the pack

**Goal:** a blank clock has a reason.

- If `calendar.days` is empty or `week_start` is not this Monday: explicit empty state (“Open Kosistenz on the Mac and Push,” or auto-pull reminder) — not “Nothing on the clock” as if the day is free.
- After every phone save, rewrite widget snapshot (already `WidgetBridge.write`). Reload Today when the app becomes active (`scenePhase`), not only pull-to-refresh.
- Mac: keep **Pull when this Mac app opens** default on (already). If phone mutations did not apply, Settings → Phone should say so (applied counts).
- Optional: `NSMetadataQuery` / coordinated directory observer so iCloud updates refresh without a manual pull. Only after Phase 1 is honest.

**Done when:** airplane-mode toggle still works locally; reconnecting + opening the Mac does not require Settings → Phone; a week the Mac never exported does not look like a free day.

### Phase 4 — Optional, after the carry loop

Only if you reopen this file:

- Morning **intention** one-liner (from `day_brief`, not the full check-in wizard).
- Lock Screen widget / Live Activity for now/next.
- App Intent: “Add a class in Kosistenz” (hard event, not Fill week).
- Estimate learning / timers — still Mac-first; phone can show remaining minutes once the pack has them.

Still out of scope until you say otherwise: CloudKit, Fill week, Cluny on device, sleep as a locked night bar, series editor, workout template editor, Analytics.

---

## Suggested order of work (implementation)

1. **Pack dump** — block `work_item_id` + unplaced minutes/due. Tests in `tests/test_icloud_sync.py`.
2. **Pack apply** — block status + scheduled_date from phone. Tests: skip on phone, Mac week shows skipped; phone cannot move a study block to 14:20.
3. **Swift Today actions** — unplaced chips, due toggle, block skip/done/park. Rebuild iOS on your Mac (`ios/Kosistenz.xcodeproj`).
4. **Capture** — estimate on add; Inbox → today.
5. **Today layout** — fold Inbox + hide Sync tab behind a gear.
6. **Empty/stale week copy** + become-active reload.

Do not start a visual redesign of Week until 1–3 work with a real pack. A prettier screenshot of unplaced titles is still a poster.

This Linux environment cannot compile or install to a phone. Device proof is on your Mac + iPhone after `git pull` and an Xcode run. Mac side still needs `./macos/install_app.sh` so `apply_pack` matches the phone.

---

## Files likely to change

| Area | Files |
| --- | --- |
| Pack publish / apply | `icloud_sync.py`, `tests/test_icloud_sync.py`, maybe `calclock.py` slim fields |
| Phone actions | `ios/Kosistenz/PackActions.swift`, `TodayScreen.swift`, `WeekScreen.swift`, `InboxScreen.swift` |
| Clock UI | `ios/Kosistenz/DayClock.swift` (tappable blocks / due chips) |
| Models | `ios/Kosistenz/SyncPack.swift` (decode new keys) |
| Widget | `ios/KosistenzWidget/KosistenzWidget.swift`, `WidgetSnapshot` |
| Chrome | `ios/Kosistenz/KosistenzApp.swift` (tabs → Today/Week/Journal + gear) |
| Copy | `ios/README.md`, this file |

Keep the pack backward compatible. A phone that has not updated still reads old dumps; a Mac that has not updated still ignores unknown keys in `hard_events`.

---

## Test plan (your Mac + iPhone)

1. Fill week on the Mac, Push. Phone Today shows the same busy bars and unplaced titles **with minutes**.
2. Skip a packed block on the phone. Open the Mac: that block is skipped, not restored.
3. Unplaced “Spanish · 45m” → Today on the phone. Mac To Do shows it dated today; Fill week can place it.
4. Tap a due chip to done. Mac to-do for that id is done. The 11:59 bar does not become busy time.
5. Add “30 mins reading” on the phone. Mac has estimate 30. Park a thought; send it to today from the phone.
6. Add a lecture on the phone. Mac week clock has it (`source: iphone`). Packed study still cannot be dragged on the phone.
7. Airplane mode: toggle a to-do; when you reconnect and open the Mac, it matches.
8. Widget now/next matches Today after a skip.

Python tests cover merge, path traversal, pack size, far-future stamps, and the new apply rules. Run `python3 -m unittest tests.test_icloud_sync tests.test_phone_calendar -q` on pack changes.

---

## Definition of done (the carry loop)

- [ ] Phone and Mac still share iCloud Drive / Kosistenz (already true; do not regress).
- [ ] Unplaced items can be dated today/tomorrow from the phone.
- [ ] Packed blocks can be skipped, done, or parked from the phone; Mac apply honors status and ignores phone-invented study times.
- [ ] Due chips complete the work item.
- [ ] New phone to-dos can carry an estimate; Inbox can send a row to today.
- [ ] A missing/stale week is explained, not painted as a free day.
- [ ] Ask Cluny, Fill week, CloudKit, and live SQLite in iCloud are still absent on the phone.

When those hold, the iPhone is up to speed with the **life** Mac owns — not with Home widgets, Brain, or the packer. That is the intended split.
