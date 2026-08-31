# Next sprint

**Current plan:** [docs/iphone-sprint-2.md](iphone-sprint-2.md)

Make the iPhone app actually usable away from the Mac: same iCloud Drive
folder as the Mac, today’s to-dos, log the expected workout (including run
miles), write a journal, and have that show up on the Mac without hunting
Settings.

**Foundation (merge first):** [docs/iphone-sprint.md](iphone-sprint.md)
and [PR #17](https://github.com/fresn3l/ToDo-Desktop_Application/pull/17)
(`cursor/iphone-icloud-7484`) — `ios/` skeleton plus Settings → Phone.

The live SQLite database stays on the Mac.
Sync is still a JSON pack on iCloud Drive, not CloudKit.

The old checklist / wizard list is retired. Kosistenz on `main` is the Mac
journal + Today + To Do + Workout app.
