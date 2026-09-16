# Kosistenz for iPhone

Companion to the Mac app. Same Apple ID. Data moves through **iCloud Drive / Kosistenz**, not a Kosistenz server.

The Mac writes a JSON pack (`work.json`, `workouts.json`, `journal.json`, `calendar.json`, `appearance.json`). This iOS app reads and writes those files through a folder you pick in Files. Appearance comes from the Mac pack — there is no second theme picker on the phone.

Ask Cluny stays on the Mac. If the laptop is asleep, Cluny is off on the phone on purpose. Today, To Do, Journal, and **named busy time** still save.

Four tabs: **Today** (To Dos dated today), **Calendar** (day clock, swipe yesterday/tomorrow), **To Do** (personal capture — park, pin a weekday, or send to Today), **Journal** (short write). **Due** from a subscribed calendar is chips on the day, not the To Do pile. Sync is a quiet cloud icon — red only when the folder is missing or iCloud failed. Local alerts fire **30, 15, and 5 minutes** before a timed event; checking it off cancels the rest.

**Add** a named event on Calendar (one-off or weekly day chips). Times are 24-hour, same as the Mac (`0930`, `21:30`). Tap a named bar for Happened / Missed, or check off a placed To Do. Repeating asks this day vs the series once and remembers. After Save, the block is on the phone clock immediately; opening the Mac merges it (`source: iphone`) and writes the canonical week back. Packed study still cannot be dragged from the phone.

**Shortcuts / Siri / Action Button:** Park in To Do, check off today’s first item, log the expected workout. **Home Screen widget:** today’s list; tap the circle to toggle. The widget reads a snapshot in the App Group; open the app once after installing so it fills.

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
2. On the iPhone: the cloud icon stays quiet when the pack is fine. Red means pick the folder or Sync now. Last pack time is on the Sync sheet.
3. Check off Today’s list, give a To Do a day (Today, or long-press for Wednesday), write a short journal, or **Add** / tap a bar on Calendar.
4. Open Kosistenz on the Mac. Checks, journal, and new events should be there without visiting Settings → Phone.

## Phone tabs

| Tab | What it is |
| --- | --- |
| Today | Ordered list of today’s timed events and dated To Dos. Check off with a short animation. Add a task → dated today. Imported dues stay off this list. |
| Calendar | Opens on **today**. Tiny Week / Today control. Swipe to yesterday or tomorrow. Tap a bar: Happened, Missed, or check off a placed To Do. Due chips on the day. **Add** a named event; no Fill week / drag. |
| To Do | Personal capture that is not dated today and not an imported Due. Park a thought, tap Today, or long-press / Pick a day for a weekday. |
| Journal | A short write surface. Saves into the same `journal.json` the Mac already syncs. |

Sync (folder, last pack time, alerts note) is the cloud icon, not a tab.

The compact layout is for iPhone. On iPad (and Catalyst) a sidebar lists the same tabs.

## Out of scope here

Day-rollover `missed` marks and Mac Analytics consistency, Timeline, Brain/Library, Ask Cluny over the internet, CloudKit, App Store / TestFlight, editing repeating series or the week workout template from the phone, Fill week / drag packed blocks.
