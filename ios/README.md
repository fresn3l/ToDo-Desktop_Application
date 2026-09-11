# Kosistenz for iPhone

Companion to the Mac app. Same Apple ID. Data moves through **iCloud Drive / Kosistenz**, not a Kosistenz server.

The Mac writes a JSON pack (`work.json`, `workouts.json`, `journal.json`, `calendar.json`, `appearance.json`). This iOS app reads and writes those files through a folder you pick in Files. Appearance comes from the Mac pack — there is no second theme picker on the phone.

Ask Cluny stays on the Mac. If the laptop is asleep, Cluny is off on the phone on purpose. To-dos, journal, workouts, and **named busy time** still save.

Today and Week show the **awake-window clock** from the pack (`day_start`–`day_end`, default 05:30–21:30), with dues as chips. **Add** a named event (one-off or weekly day chips). Times are 24-hour, same as the Mac (`0930`, `21:30`). After Save, the block is on the phone clock immediately; opening the Mac merges it (`source: iphone`) and writes the canonical week back. Packed study still cannot be dragged from the phone. Nights stay empty unless you add a block yourself.

**Shortcuts / Siri / Action Button:** Park in All Work, check off today’s first to-do, log the expected workout. **Home Screen widget:** today’s to-dos; tap the circle to toggle. The widget reads a snapshot in the App Group; open the app once after installing so it fills.

## Signing extra for this sprint

Both the app and **KosistenzWidget** need the same Team. Add **App Groups** → `group.com.kosistenz.app` on both targets if Xcode complains. Widget bundle id is `com.kosistenz.app.widget` (or `your.id.widget` if you changed the app id).

## What you need

- A Mac with Xcode 15+ (this Linux environment cannot compile or install to a phone)
- The same iCloud account on the Mac and the iPhone
- Kosistenz on the Mac rebuilt from this branch (`./macos/install_app.sh`), then **Settings → Phone → Push to iCloud** once

## Open the project

1. Open `ios/Kosistenz.xcodeproj` in Xcode.
2. Signing & Capabilities → your Personal Team. Bundle id defaults to `com.kosistenz.app` — change it if Apple asks you to.
3. Run on your iPhone (or iPad). The same target supports Mac Catalyst if you want the companion window on a laptop next to the full Mac app.
4. First launch: **Sync → Choose iCloud Drive / Kosistenz**. Pick the `Kosistenz` folder in iCloud Drive (the one the Mac just pushed). Saves go through that bookmark with `NSFileCoordinator`.

Until you pick the folder, the app says **On this iPhone only**.

## After it launches

1. On the Mac: Settings → Phone → Push to iCloud. Leave **Pull phone changes when this Mac app opens** on.
2. On the iPhone: pull to refresh, or Sync now.
3. Check off a to-do, log the expected workout (miles for a run, a name for Other), write in Journal, or **Add** an event on Today or Week.
4. Open Kosistenz on the Mac. Today should update without visiting Settings → Phone.

## Phone tabs

| Tab | What it is |
| --- | --- |
| Today | Awake-window clock, dues, dated to-dos, expected workout chips, journal teaser. **Add** a busy block. |
| Week | This week’s clock (events + packed blocks + dues). **Add** a named event; no Fill week / drag. |
| Journal | Full-screen editor; edits today’s entry instead of minting a second one |
| Inbox | Park a thought in All Work + goals from the pack |
| Sync | Folder picker, last pack time, Cluny note |

The compact layout is for iPhone. On iPad (and Catalyst) a sidebar lists the same tabs.

## Out of scope here

Analytics, Timeline, Brain/Library, Ask Cluny, CloudKit, App Store / TestFlight, editing repeating series or the week workout template, Fill week / drag packed blocks.

**Next:** the phone should act on the packed day (unplaced → today, skip/done/park a block, due chips), not clone Mac Home. Contract: [docs/iphone.md](../docs/iphone.md).
