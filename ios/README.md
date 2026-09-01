# Kosistenz for iPhone

Companion to the Mac app. Same Apple ID. Data moves through **iCloud Drive / Kosistenz**, not a Kosistenz server.

The Mac writes a JSON pack (`work.json`, `workouts.json`, `journal.json`, `appearance.json`). This iOS app reads and writes those files. Appearance comes from the Mac pack — there is no second theme picker on the phone.

## What you need

- A Mac with Xcode 15+ (this Linux environment cannot compile or install to a phone)
- The same iCloud account on the Mac and the iPhone
- Kosistenz on the Mac rebuilt from `main` or this branch, then **Settings → Phone → Push to iCloud** once

## Create the Xcode project (first time)

Xcode project files go stale; the source of truth is the Swift files in `Kosistenz/`.

1. Xcode → File → New → Project → iOS → App
2. Product Name: `Kosistenz`
3. Organization Identifier: `com.kosistenz`
4. Interface: SwiftUI, Language: Swift
5. Uncheck tests if you want a tiny project
6. Save the project **inside this `ios/` folder**, replacing the placeholder app files with the ones already here:
   - `Kosistenz/KosistenzApp.swift`
   - `Kosistenz/TodayScreen.swift`
   - `Kosistenz/SyncPack.swift`
   - `Kosistenz/Appearance.swift`
7. Signing & Capabilities → your Personal Team. Add **iCloud** with **iCloud Documents** (default container is enough for iCloud Drive).
8. Run on your iPhone.

## After it launches

1. On the Mac: Settings → Phone → Push to iCloud
2. On the iPhone: pull to refresh, or wait a minute for iCloud Drive
3. Log a workout or add a to-do on the phone, then on the Mac click **Pull from iPhone** (or wait if auto-sync is on)

## Out of scope in this sprint

Full Journal / Analytics / All Work, CloudKit records, App Store / TestFlight.

**Next:** [docs/iphone-sprint-2.md](../docs/iphone-sprint-2.md) — shared iCloud
Drive folder, expected workout + miles, real journal, Mac auto-pull.
