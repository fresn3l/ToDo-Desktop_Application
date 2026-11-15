# Kosistenz for iPhone

Companion to the Mac app. Same Apple ID. Data moves through **iCloud Drive / Kosistenz**, not a server.

The Mac writes a JSON pack (`work.json`, `calendar.json`, `appearance.json`). This app reads and writes those files through a folder you pick in Files. Appearance comes from the Mac pack.

Three tabs: **Today** (to-dos dated today, plus the day’s clock), **Calendar** (day clock, swipe yesterday/tomorrow), **To Do** (capture that is not dated today). Timed events from a subscribed calendar are busy. All-day and 11:59 items stay due chips. Sync is a quiet cloud icon. Local alerts fire **30, 15, and 5 minutes** before a timed event.

**Add** a named event on Calendar. Times are 24-hour, same as the Mac (`0930`, `21:30`). Tap a bar for Happened / Missed, or check off a placed to-do. Repeating asks this day vs the series once and remembers. Fill week and drag-to-pack stay on the Mac.

**Shortcuts:** Park in To Do, check off today’s first item.

## What you need

- A Mac with Xcode 15+ (this environment cannot compile or install to a phone)
- The same iCloud account on the Mac and the iPhone
- Kosistenz on the Mac rebuilt from this branch (`./macos/install_app.sh`), then **Settings → Phone → Push to iCloud** once

## Open the project

1. Open `ios/Kosistenz.xcodeproj` in Xcode.
2. Signing & Capabilities → your Personal Team. Bundle id defaults to `com.kosistenz.app`.
3. Run on your iPhone. First launch: pick **Files → iCloud Drive → Kosistenz**.

Until you pick the folder, the app says **On this iPhone only**.
