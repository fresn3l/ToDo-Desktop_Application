# Next sprint

**Current plan:** [docs/calendar-home.md](calendar-home.md). Home widgets, Calendar month/year, live Home drag, and iPhone appearance from the Mac pack are on this branch — see [futuresprints.md](futuresprints.md).

Kosistenz is the calendar you carry (Mac week on a clock, later the iPhone
agenda). The class due-date subscription is a **deadline feed** — all-day
“Essay 2 due” and 11:59 events become to-dos with `due_at`, not busy time.
You add lectures as hard events here. A packer fills study/gym into gaps.
Nothing is written back to Apple Calendar.

Mail, goals, and Cluny as inboxes come after a real week lands on that grid.

**iPhone:** still need a shared iCloud Drive folder
([iphone-sprint.md](iphone-sprint.md)). The companion’s job after the Mac
clock exists is **today as blocks**, not only to-do chips
([iphone-sprint-2.md](iphone-sprint-2.md)).

The live SQLite database stays on the Mac. Sync stays a JSON pack on
iCloud Drive, not CloudKit. Do not put the live DB in iCloud.
