# Kosistenz is the calendar you carry

One home. You do not open Apple Calendar, Mail, or a second to-do app to
plan the day. Those systems **feed** Kosistenz. The week grid here is what
you live in — Mac at the desk, iPhone between classes.

Locked from the current conversation:

- Kosistenz is the **only** calendar you use.
- Class work arrives from an Apple Calendar **subscription** whose events
  are all-day titles like “Essay 2 due” and **timed 11:59** due moments.
  Both are **deadlines**, not busy time.
- No write-back into Apple Calendar. Generated study/gym blocks exist only
  in Kosistenz.
- Mail, goals, and Cluny are later inboxes. They do not place times.

Cluny stays the local brain (syllabus PDF → proposed tasks). It does not
own a second task list and it does not pick 2:15 vs 2:40.

---

## Three kinds of time

| Kind | What it is | What the packer may do |
|------|------------|------------------------|
| **Hard** | Class, lab, work, sleep — timed events **you create in Kosistenz** (or import from a *timed* calendar you mark busy) | Cannot move |
| **Deadline** | Due-date subscription: all-day “Essay 2 due”, 11:59 events | Becomes a to-do with `due_at`. Never occupies 11:59 as a meeting |
| **Soft** | Study chunks, gym template, inbox items with an estimate | Placed into free gaps; you can freeze, skip, or +15 min |

**Rule for that class calendar:** every event is a deadline until you
explicitly mark a calendar as busy. A 11:59pm event with no duration (or
a one-minute stub) is `due_at`, not a block. An all-day event is due at
**end of that local day**, not “busy 8am–8pm.”

---

## You still need class *meeting* times

The subscribed calendar is dues, not lectures. If that is the only feed,
the packer does not know you have class at 9:30 and will put study on top
of lecture.

For Kosistenz-only to work, **recurring hard events live here**: Mon/Wed
CHEM 9:30–10:20, etc. Type them once (or import a *separate* lecture ICS
if you have one). After that you can stop opening Apple Calendar entirely.
Keep the due-date subscription in the background only so EventKit (or a
pasted Canvas ICS URL) can refresh dues.

---

## Data (what has to exist that does not today)

Kosistenz work is currently a **date**, not a clock (`scheduled_date`).
That is not a calendar.

| Record | Role |
|--------|------|
| **Event** | Hard block: start, end, title, recurrence, `busy`. Source `kosistenz` or import. |
| **Work item** | Inbox: title, `estimate_minutes`, optional `due_at`, status. All Work = no block yet. |
| **Block** | Placement: start, end, points at a work item / workout / leftover, status `proposed` / `locked` / `done` / `skipped`. |
| **Imported event** | Stable Apple/ICS `uid`. Class calendar → upsert work item by uid, do not duplicate every sync. |

Timers you already have become **actual vs estimate** later. Not in the
first slice.

---

## First sprint — clock + dues, not the whole OS

**Done feels like:** you open Kosistenz and see this week on a clock.
Canvas dues from that subscription appear as to-dos with due dates, not as
all-day busy. You add lecture times once. You add “Study essay 2 · 2h”
(or accept an imported due with a default estimate) and **Fill week**
drops chunks into free gaps before the due. The iPhone is not this sprint
until blocks exist to show.

### Must

1. **Week + day on a clock** (Mac). Replace “To Do = a list for a date”
   as the planning surface. Today becomes *today’s timeline* plus the
   journal/workout cards you already have.
2. **Ingest the due-date calendar** via EventKit (you already subscribe).
   Treat all events from calendars marked “deadlines” as work items with
   `due_at`. Dedupe on uid. Refresh on launch.
3. **Create hard events in Kosistenz** — one-off and weekly recurrence
   (lectures). These are the only busy time until another calendar is
   marked busy.
4. **To-do fields:** estimate (minutes) + optional due. Imported dues
   start with a default estimate you can edit (e.g. 60 min) so the packer
   has something to place. Blank estimate stays in All Work, unplaced.
5. **Dumb packer:** earliest due first; chunk estimates into 50–90 min;
   honor hard events and a simple sleep/awake window (e.g. 08:00–22:00);
   gym template as soft if there is room; never move locked blocks.
6. **No Apple write.** No Mail. No Cluny placement. No Canvas OAuth.

### Should (same sprint if the packer is honest)

- Paste the same Canvas **ICS URL** so Kosistenz can refresh dues without
  Calendar.app staying in the loop.
- Skip / done / freeze on a block; skipped hours try to re-pack before
  `due_at` or the item goes **at risk**.

### Defer

- iPhone day timeline (needs blocks in the iCloud pack — after this
  Mac slice).
- Mail / goals inboxes.
- Cluny “propose tasks from a PDF.”
- Estimate learning from timers.
- Apple Watch / system Calendar mirroring.

---

## Suggested order of work

1. Schema: `due_at`, `estimate_minutes`, `events`, `blocks` (tests first).
2. Mac week/day UI with hard events you type (lectures) — prove the clock
   without Apple.
3. EventKit: list calendars, tag one as deadlines, import → work items.
4. Packer + Fill week.
5. ICS URL as an alternative to EventKit.
6. Then a **carry sprint**: iPhone today = blocks (this replaces most of
   [iphone-sprint-2.md](iphone-sprint-2.md) UI work; shared iCloud folder
   is still a prerequisite).

---

## Test plan (Mac)

This environment cannot talk to EventKit. You can.

1. Import the class calendar. “Essay 2 due” (all-day) → to-do due that
   evening, **zero** 8-hour busy bar.
2. A 11:59pm event → `due_at` 23:59, **zero** meeting at 11:59.
3. Add a recurring lecture 9:30–10:20. Fill week does not overlap it.
4. 3h item due Friday → two or three chunks on earlier days.
5. Kill Calendar.app. Refresh still updates dues (EventKit or ICS URL).
6. No new events appear in Apple Calendar.

Python tests cover deadline heuristics, uid dedupe, packer overlap, and
chunking without EventKit.

---

## Definition of done

- [ ] Week view is the planning home on the Mac.
- [ ] Class subscription dues are to-dos with due times, never all-day busy.
- [ ] Lectures exist as hard events you added in Kosistenz.
- [ ] Fill week places estimates around hard time; you can lock/skip.
- [ ] Nothing is written to Apple Calendar.
- [ ] iPhone/mail/goals/Cluny-scheduling are explicitly not in this slice.
