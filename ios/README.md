# Kosistenz for iPhone

Companion to the Mac app. Same Apple ID. Data moves through **iCloud Drive / Kosistenz**, not a Kosistenz server.

The Mac writes a JSON pack (`work.json`, `workouts.json`, `journal.json`, `calendar.json`, `appearance.json`). This iOS app reads and writes those files through a folder you pick in Files. Appearance comes from the Mac pack — there is no second theme picker on the phone.

Ask Cluny stays on the Mac. If the laptop is asleep, Cluny is off on the phone on purpose. To-dos, the week clock, and **named busy time** still save.

Two tabs: **Calendar** (week / month / year, same moves as the Mac clock) and **Work** (Today / All / Unplaced / Due). Sync is a sheet, not a tab.

**Calendar** can add a named event (one-off or weekly day chips), Fill week into free gaps, Place unplaced work onto a time, mark a bar Done / Skip / Park, and paste an ICS blob. Times are 24-hour, same as the Mac (`0930`, `21:30`). Phone-placed work bars merge on the Mac (`source: iphone`) the next time the laptop opens the pack.

**Work** is the Mac Work sheet: Today’s check-off list, All Work (no date yet), unplaced minutes, and due dates.

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
4. First launch: pick **Files → iCloud Drive → Kosistenz**. Saves go through that bookmark with `NSFileCoordinator`. Allow notifications when asked.

Until you pick the folder, the app says **On this iPhone only**.

## After it launches

1. On the Mac: Settings → Phone → Push to iCloud. Leave **Pull phone changes when this Mac app opens** on.
2. On the iPhone: pull to refresh, or open Sync (cloud icon) → Sync now.
3. Check off Today on Work, Place or Fill week on Calendar, or **Add** an event.
4. Open Kosistenz on the Mac. Checks, new events, and phone-placed bars should be there without visiting Settings → Phone.

## Phone tabs

| Tab | What it is |
| --- | --- |
| Calendar | Week clock, month, and year. Add an event, Fill week, Place unplaced work, Done / Park / Skip a bar, paste ICS. |
| Work | Today / All / Unplaced / Due. Add, park, send to today, or Place onto the clock. |

Sync (folder, last pack time, alerts note) is the cloud icon, not a tab. Journal is not on the phone.

The compact layout is for iPhone. On iPad (and Catalyst) a sidebar lists the same tabs.

## Out of scope here

Day-rollover `missed` marks and Mac Analytics consistency, Timeline, Brain/Library, Ask Cluny over the internet, CloudKit, App Store / TestFlight, editing repeating series or the week workout template from the phone, drag-to-place (Place sheet and Fill week stand in for drag).
