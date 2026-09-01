# Kosistenz ↔ Cluny — responsibilities roadmap

**Audience:** the agent on Cluny (`fresn3l/Cluny_the_AI_Agent`, branch `cursor/sprint-11-kosistenz-api`) and anyone wiring the two apps.

**Kosistenz repo:** [fresn3l/ToDo-Desktop_Application](https://github.com/fresn3l/ToDo-Desktop_Application) (this file lives there). The product name is **Kosistenz**; there is no `fresn3l/Kosistenz` repo.

This document is the **ownership contract**. If Cluny’s `INTEGRATION.md` / Sprint 11 plan disagrees with this file, **this file wins**. Cluny should rewrite its integration docs to match.

---

## One sentence

**Kosistenz is the life you live in. Cluny is the brain you ask.** Kosistenz owns the week, the to-do list, the clock, goals, workouts, the journal files, and the iPhone. Cluny owns indexing, retrieval, and proposals. Cluny does not schedule, and it does not keep a second copy of your life as the live list.

---

## Why this split exists

Two apps grew in parallel and both grew a task store and a calendar store. That cannot survive contact with a real week.

Kosistenz already *is* the planner:

- You open it to see **this week on a clock**.
- Lectures you typed are **hard** (busy).
- The class due-date calendar is a **deadline feed** (all-day / 11:59 → to-dos with `due_at`, never a busy bar).
- You pick **which day this week** to do a to-do. A dumb packer drops it in the **first free gap**. You do not ask an LLM for 2:15 vs 2:40.
- 1-week goals spawn a to-do every Sunday for the coming week.
- The iPhone companion reads a JSON pack Kosistenz writes. If a to-do only exists in Cluny, the phone never sees it.
- Apple Calendar is **read-only**. Nothing is written back. Generated blocks live only in Kosistenz.

Cluny already *is* the brain:

- Local RAG over PDFs, notes, URLs, journal-style files (SQLite catalog + vectors, Ollama).
- `cluny ask` / `chat` / `agent` / GUI / menu-bar widget.
- Optional `cluny serve` on localhost.

The failure mode we are preventing: **two calendars, two task lists, and an LLM that thinks it is the scheduler.** That is how plans diverge, the phone shows the wrong day, and Fill week fights Cluny.

---

## Current state (do not pretend otherwise)

### Kosistenz (this repo, on `main`)

Shipped, local-first, SQLite + files under Application Support (`ToDo/` legacy folder name):

| Surface | Canonical store | Role |
|---------|-----------------|------|
| Journal | JSON files under `Journal/` | Written here; optionally **pushed** to Cluny |
| Daily checklist | `daily_checklist.sqlite` | Written here; optionally **pushed** to Cluny |
| To Do / All Work | `work_items.sqlite` | Dated work, backlog, timers, repeats, `due_at`, estimates, goal links |
| Goals | same DB (`goals` table) | 1 week / 6 months / year / 5 years; weekly spawn |
| Calendar | `calendar.sqlite` + `calendar_feeds.json` | Hard events, deadline ingest, **blocks** (proposed/locked/done/skipped) |
| Workouts | `workouts.sqlite` + week template JSON | Sessions, weight, expected kinds |
| iPhone | JSON pack in iCloud Drive / Kosistenz | Mac is source; phone is companion |
| Menu bar / widget | snapshot JSON + loopback HTTP `:18741` | Same work/workout records |

Existing Cluny hook (`cluny_sync.py`): **one-way, best-effort, after local save**. Journal entries and checklist submissions can be copied into Cluny’s SQLite (or POSTed to an ingest URL). Failures never block saving in Kosistenz. This is ingest, not a shared database.

### Cluny (`Cluny_the_AI_Agent`)

Shipped independently:

- Library + Chroma + FTS, RAG, eval, backup/export.
- CLI, PySide6 GUI, menu-bar widget, `cluny serve`.
- **Also** `tasks.sqlite` and `calendar.sqlite`, plus planner tools that **create Cluny tasks** and **read Cluny calendar**.

Sprint 11 currently assumes Cluny is the durable store for todos and calendar, and Kosistenz is a thin UI. **That assumption is inverted.** Kosistenz already has those stores and the iPhone pack. Cluny’s copies are a **second brain’s scratchpad**, not the week you carry.

### What “on hold” meant

Cluny-as-scheduler was deferred until Kosistenz had a real week grid. That grid exists now. Integration can resume **as brain + inbox**, not as a second planner.

---

## Authority map

Who is allowed to **commit** a change to real life (the thing you will do, the time it occupies, the file you will re-open).

| Domain | Source of truth | Kosistenz | Cluny | Notes |
|--------|-----------------|-----------|-------|-------|
| Week clock / busy time | Kosistenz `calendar.sqlite` | Writes | Read-only snapshot, if at all | Hard events + placed blocks |
| Deadline to-dos | Kosistenz work items from Apple/ICS | Writes | Must not re-import the same ICS as a second calendar | Dedupe lives in Kosistenz |
| To-do list (open/done, day, timer) | Kosistenz `work_items` | Writes | May **propose** new items; must not be the live list | Phone pack follows this DB |
| Which day a to-do is done | You, in Kosistenz | Writes | Never | Mid-week chips; not Cluny |
| Exact clock time of study/gym | Kosistenz packer | Writes | **Never** | First free gap; lock/skip here |
| Weekly / long goals | Kosistenz goals | Writes | May coach against a **read** of progress | Sunday spawn is Kosistenz |
| Workouts actually logged | Kosistenz workouts | Writes | May read for “did you train” questions | Template is Kosistenz |
| Journal text | Kosistenz `Journal/` files | Writes | Indexes a **copy** | iPhone journal = Kosistenz pack |
| Daily checklist answers | Kosistenz checklist DB | Writes | Indexes a **copy** | Same as journal |
| PDF / article / note library | Cluny catalog | Does not own | Writes | Syllabi, papers, clips |
| RAG answers / citations | Cluny | Displays, later | Writes | Ollama stays in Cluny |
| Agent tool loop / planner | Cluny | May call “ask” | Writes | Planner emits **proposals**, not placements |
| Appearance, tabs, native window | Kosistenz | Writes | — | |
| Cluny GUI, widget, CLI admin | Cluny | — | Writes | Capture **notes** freely; life-tasks are proposals |
| Apple Calendar | External feed | Read-only ingest | Do not two-way sync | No write-back from either app |
| iPhone companion | Kosistenz iCloud pack | Writes/reads | Out of scope | Cluny has no phone app |

**Rule of thumb:** if it changes what you will *do today* or *where you have to be*, Kosistenz commits it. If it changes what you *know* or *might want to do*, Cluny may draft it.

---

## Hard locks (compatibility invariants)

These are product law. A Cluny or Kosistenz change that violates them is a bug, even if the API is convenient.

1. **One calendar you carry.** Kosistenz. Cluny does not present a competing week, does not import ICS as the live calendar, and does not CalDAV/Google two-way as the planner.
2. **One to-do list you carry.** Kosistenz To Do + All Work. Cluny `tasks.sqlite` is not the list you check off on the phone or on Today.
3. **The LLM never picks clock times.** No “put Spanish at 14:20.” No Fill week inside Cluny. No writing `blocks` start/end.
4. **You pick the do-on day; the packer picks the gap.** Cluny may suggest *that* something belongs this week. It may not assign Monday 9:30.
5. **Class subscription events are deadlines, not meetings.** Lectures are hard events you add in Kosistenz. Cluny must not treat 11:59 dues as busy.
6. **No Apple Calendar write-back.** From either app.
7. **Journal files stay in Kosistenz.** Cluny gets a copy to index. Deleting or editing “the journal” in Cluny must not orphan the Kosistenz/iPhone copy.
8. **iPhone pack is Kosistenz-only.** Cluny does not write the iCloud folder.
9. **Local-first.** Cluny stays on-device (Ollama). Kosistenz does not send the week to a cloud LLM.
10. **Kosistenz stays usable if Cluny is down.** Journal, to-dos, calendar, workouts, goals, phone sync must work with Cluny quit. Brain features degrade (no Ask, no new proposals).
11. **Proposals are opt-in.** A Cluny suggestion sits in an inbox until you accept it into Kosistenz. Accepting creates a Kosistenz work item (title, optional estimate, optional `due_at`, optional `goal_id`). Placement is a later, separate Kosistenz action.
12. **Ids do not fork.** If a proposal is accepted, the Kosistenz work-item id is canonical. Cluny may store `kosistenz:{uuid}` as a pointer. Cluny must not mint a second live id that Today and the phone disagree with.

---

## What Kosistenz controls (in detail)

### Product surface

The native Mac app you open every day: Today, Journal, To Do, All Work, Calendar (week clock), Goals, Workout, Analytics, Settings, menu bar, Notification Center widget, Services / URL schemes. The iPhone companion (Today-shaped: to-dos, workout, journal).

### Planning model (already shipped — Cluny must learn this vocabulary)

Three kinds of time:

| Kind | Meaning | Who may move it |
|------|---------|-----------------|
| **Hard** | Class, lab, work, sleep — timed events created in Kosistenz | Nobody automatic. You edit the event. |
| **Deadline** | Due-date feed: all-day titles, 11:59 stubs | Becomes a to-do with `due_at`. Never occupies 11:59 as a meeting. |
| **Soft** | Study / gym / inbox with an estimate | Packer places into free gaps; you freeze, skip, or +15. |

Work items are **inbox + date**, not a second calendar:

- Title often carries duration (`45 mins calculus`, `3h spanish`).
- Optional `due_at`, `estimate_minutes`, `goal_id`.
- `scheduled_date` = the day you chose. All Work = no day yet.
- Finish minutes: **timer if you ran it**; else **calendar block minutes**. No third guess.

Goals are **labels with optional end dates and optional hour targets**, not auto-resetting seasons. 1-week goals auto-create a to-do (Sunday → upcoming week; mid-week add → today). Progress for a week goal counts **this week only**.

### Stores Cluny must not take over

- `work_items.sqlite` (and `work_series`)
- `calendar.sqlite` / feeds
- `workouts.sqlite` / `workout_plan.json`
- Journal directory
- Checklist DB
- iCloud Drive `/Kosistenz` pack
- Widget snapshot

### What Kosistenz will eventually expose *to* Cluny

Not “Cluny owns these records.” Kosistenz **publishes a read model** so the brain can answer questions and propose work:

- This week’s hard events and placed blocks (busy map, not for Cluny to edit).
- Open to-dos (title, day, due, estimate, goal, status).
- Goal list and this week’s spent minutes.
- Pointers to journal entries already ingested.

Transport can be localhost HTTP from Kosistenz, or a snapshot file Cluny reads. The direction is **Kosistenz → Cluny, read-only.**

### What Kosistenz will eventually accept *from* Cluny

A **proposal inbox** (name TBD: Cluny inbox / Suggested work):

- Title
- Optional estimate minutes
- Optional due date (a day or datetime *deadline*, not a start time)
- Optional goal keyword or goal id
- Optional citation (which PDF/note Cluny used)
- Provenance (`source = cluny_proposal`, stable Cluny proposal id)

On accept: Kosistenz `create_work_item` (usually All Work or a day you pick). Then the existing weekday chip + packer path. Cluny is told the canonical `kosistenz:{work_item_id}` so it can stop re-proposing the same syllabus row.

Kosistenz does **not** accept from Cluny: start/end times, recurrence of lectures, workout session logs, goal create/delete, Apple event creates, iCloud pack writes.

---

## What Cluny controls (in detail)

### Product surface

- Second-brain library (add PDF/md/url, tags, collections, watch folders).
- Ask / chat / agent / planner **over knowledge**.
- Full library GUI and menu-bar **Ask + Capture (notes)**.
- `cluny serve` as the **brain API** (search, ask, ingest, proposals).
- Backup/export of **Cluny’s** data dir, eval harness, CLI admin.

### Knowledge

Cluny is the only RAG. Kosistenz will not grow embeddings, Chroma, or Ollama clients. “Ask Cluny” in Kosistenz is an HTTP call.

Watch/index Kosistenz’s journal folder if the user opts in (`cluny watch` on Application Support `…/ToDo/Journal`). That is **indexing files Kosistenz owns**, not moving the journal into `.cluny`.

### Proposals, not a life task list

Cluny’s existing `tasks.sqlite` must be **demoted** in the integration story:

| Allowed | Not allowed |
|---------|-------------|
| Internal Cluny-ops (“re-embed this PDF”, eval chores) | The list that Today, To Do, and iPhone show |
| **Proposal records** waiting for Kosistenz accept | Completing a Kosistenz to-do only in Cluny |
| Draft from syllabus PDF: title + estimate + due | Recurring lecture series as Cluny events |

Planner mode: `search_brain` then **create_proposal**, not `create_task` as the canonical to-do.

Widget Task tab: same rule. Until the inbox exists, label it clearly as **Cluny scratch** (will not appear in Kosistenz or on the phone), or disable it for life tasks.

### Calendar inside Cluny

Cluny’s `calendar.sqlite` / `cluny calendar import` is **not** the calendar you carry.

Allowed: optional **read-only mirror** of a Kosistenz-published snapshot, so `cluny chat "what's on Thursday"` can answer without guessing.

Not allowed: ICS import of the class feed as Cluny’s live calendar; CalDAV/Google two-way; writing events Kosistenz didn’t create; meeting times invented by the model.

Sprint 11’s `GET /calendar/events` as *Cluny’s* store is the wrong source. Either drop it as the Kosistenz contract, or re-point it at a snapshot Kosistenz published.

### Context bundles

“Day agenda” and “meeting prep” are useful **as read models**. They must be assembled from **Kosistenz’s** week + Cluny’s notes — not from Cluny’s task/calendar SQLite.

- **Busy / to-dos / dues:** Kosistenz.
- **Snippets / syllabus quotes / “what is this lecture about”:** Cluny retrieval.
- **No LLM required** for the structured agenda. LLM only for prose prep.

### What Cluny never controls

- Fill week, lock/skip/done on blocks
- Weekly goal spawn
- Workout template and logging
- Timer start/finish
- iPhone sync
- Native Kosistenz window chrome, tabs, appearance
- Apple Calendar

---

## Data flow (direction of truth)

```text
                    ┌─────────────────────┐
                    │   Apple Calendar    │
                    │   (deadlines only)  │
                    └──────────┬──────────┘
                               │ read
                               ▼
┌──────────────┐  write   ┌─────────────────────┐  JSON pack   ┌─────────┐
│ You / iPhone │ ───────► │     KOSISTENZ       │ ───────────► │ iPhone  │
└──────────────┘          │  week, todos, goals │              └─────────┘
                          │  journal, workouts  │
                          └──────────┬──────────┘
                 journal/checklist   │ publish read snapshot
                 (existing push)     │ accept proposals
                                     ▼
                          ┌─────────────────────┐
                          │       CLUNY         │
                          │  index, ask, propose│
                          │  PDFs / notes / RAG │
                          └─────────────────────┘
```

**Kosistenz → Cluny (already, keep):** journal + checklist copy after save.

**Kosistenz → Cluny (next):** read-only week/todo/goal snapshot for questions and coaching.

**Cluny → Kosistenz (next):** proposals only.

**Cluny → Kosistenz (never):** placements, hard events, workout logs, pack files, Apple writes.

**Neither → Apple Calendar.**

---

## Compatibility with Cluny Sprint 11 (what to change there)

Cluny’s current Sprint 11 / `INTEGRATION.md` says:

- Kosistenz must **not** have a task or calendar SQLite.
- Cluny `tasks.sqlite` / `calendar.sqlite` are the source of truth.
- Journal canonical store is Cluny catalog; Kosistenz holds drafts only.
- Kosistenz todos/calendar screens are HTTP clients of Cluny.

**That would require deleting Kosistenz’s shipped planner and breaking the iPhone pack.** Do not do that.

### Rewrite the Cluny contract to:

| Sprint 11 idea | Revised |
|----------------|---------|
| Task REST as live CRUD SoT | Optional **proposal** REST; live CRUD stays in Kosistenz |
| `external_id = kosistenz:{uuid}` | Keep — but it points **at Kosistenz ids**, after accept |
| Calendar GET from Cluny DB | GET from Kosistenz snapshot, or drop |
| `POST /calendar/import` | Kosistenz already ingests ICS/EventKit. Do not duplicate |
| Journal save → only `/ingest/text` | Keep ingest **in addition to** Kosistenz files, not instead |
| `/context/day` built from Cluny tasks+events | Built from Kosistenz snapshot + Cluny snippets |
| Handoff: “do not build a task schema in Kosistenz” | **Opposite:** Kosistenz schema already exists; Cluny must not replace it |
| Repo URL `fresn3l/Kosistenz` | `fresn3l/ToDo-Desktop_Application` |

Cluny Sprint 11 can still ship: richer `/health`, localhost serve, ingest, search, chat, meeting-prep **notes**, LaunchAgent for `cluny serve`. Those are brain-service work. The mistaken part is **owning the planner stores**.

### Widget vs Kosistenz

Both apps may stay installed.

- **Kosistenz menu bar / widget:** today’s to-dos, workout, journal streak — life.
- **Cluny widget:** ask the brain, capture a note into the library. Not a second Today.

---

## Phased roadmap (high level)

Phases are ownership-shaped, not week estimates. Each phase must preserve the hard locks. Kosistenz remains fully usable at every phase.

### Phase 0 — Freeze the split (now)

- This document is the contract.
- Cluny agent: update `INTEGRATION.md`, Sprint 11, and Agent_goals so Cluny is brain + proposals, not home-base stores.
- Do not migrate Kosistenz work/calendar DBs into Cluny.
- Do not have Kosistenz delete local SQLite in favor of `cluny serve`.

### Phase 1 — Brain ingest (safe, additive)

**Goal:** Cluny can answer questions about what you wrote, without touching the week.

- Keep `cluny_sync.py` journal + checklist push (or replace the SQLite dump with `POST /ingest/text` **without** making Cluny the file owner).
- Optional: `cluny watch` on the Kosistenz Journal folder.
- Syllabi and PDFs live in Cluny’s library (`cluny add`), not in Kosistenz.

**Done when:** you can `cluny ask` about yesterday’s journal and a syllabus PDF, while Kosistenz is the only place you *write* the journal.

### Phase 2 — Read-only life context

**Goal:** Cluny can see the week in order to talk about it, not to edit it.

- Kosistenz publishes a snapshot (HTTP or file): hard events, blocks, open work, goals/progress.
- Cluny chat/agent tools **read** that snapshot.
- Cluny calendar/task tools that *write* life records are disabled or retargeted.

**Done when:** `cluny chat "what's due this week"` is answered from Kosistenz data, and no new row appears in Cluny’s task list as the live to-do.

### Phase 3 — Proposal inbox

**Goal:** syllabus / brain → Kosistenz All Work, still no times.

- Cluny emits proposals (title, estimate, due, keyword, citations).
- Kosistenz shows an inbox; accept → work item; reject / snooze.
- Dedup: same syllabus row does not spam every launch (`source_uid` / proposal id).
- After accept, packer + weekday chips work as they do today.
- Weekly goals remain Kosistenz’s job; Cluny must not also spawn “3h spanish.”

**Done when:** a PDF becomes a to-do you accepted, it shows on To Do and (after you pick a day) on the clock, and on the iPhone pack — with no Cluny-only twin.

### Phase 4 — Ask Cluny inside Kosistenz

**Goal:** one window for life, brain on call.

- Optional Kosistenz panel: Ask Cluny (localhost). If Cluny/Ollama is down, the panel says so; the rest of the app is fine.
- Meeting prep: Kosistenz date/title + Cluny snippets. Still no auto-placement.
- Cluny must not need Kosistenz’s WebView to function as a library.

**Done when:** you can prep Thursday’s lecture from Calendar without leaving Kosistenz, and the busy bars still came only from Kosistenz.

### Phase 5 — Coaching, not control

**Goal:** the brain notices drift; you still commit the week.

Examples Cluny *may* say:

- “1-week Spanish has 0 minutes logged and no block this week.”
- “Essay 2 is due Friday and has no remaining estimate placed.”

Examples Cluny *may not* do:

- Lock a 90-minute block at 16:00.
- Mark the to-do done.
- Change the weekly goal target.
- Write Apple Calendar.

**Done when:** coaching is visible and ignoring it does not corrupt the week.

### Explicitly out of scope (until you reopen this file)

- Cluny as CalDAV/Google Calendar client for the life calendar
- Cloud LLM for planning
- Merging the two `.app`s into one process
- Cluny writing the iPhone pack or a second phone app
- Mail as an inbox (separate from Cluny)
- Letting planner mode call Fill week

---

## Responsibilities by persona (for implementers)

### Cluny agent should

1. Treat this file as the platform contract.
2. Keep RAG, ingest, ask, widget-as-brain, `cluny serve` for **knowledge**.
3. Stop documenting Kosistenz as a UI-only client of `tasks.sqlite` / `calendar.sqlite`.
4. Add a **proposal** concept (even if the first version is a JSON table Cluny owns that Kosistenz will later pull).
5. Consume a future Kosistenz snapshot for day/meeting context; do not invent a second week.
6. Keep Cluny useful when Kosistenz is quit (library + ask over PDFs).
7. Never send placements, never write Apple, never require Kosistenz to drop its DBs.

### Kosistenz agent should (later work in this repo)

1. Not add Ollama/Chroma/embeddings.
2. Keep `cluny_sync` ingest until HTTP ingest is proven, then prefer ingest-without-ownership.
3. Add snapshot publish + proposal inbox when Phase 2–3 start.
4. Optional Ask panel that degrades if port 8787 is down.
5. Keep weekly goals, packer, deadline ingest, iCloud pack entirely local to Kosistenz.

### Neither agent should

- “Unify” by picking one SQLite for both life and RAG.
- Let the supervisor complete Kosistenz to-dos as a side effect of chat.
- Duplicate Sunday weekly-goal spawning on the Cluny side.

---

## Failure modes to design against

| Failure | What it looks like | Prevention |
|---------|--------------------|------------|
| Twin lists | Checked off in Cluny widget, still open on iPhone | One live list: Kosistenz |
| Twin calendars | Lecture in Cluny ICS, study block on top of it in Kosistenz | One busy map: Kosistenz |
| LLM scheduler | Blocks jump to “optimal” times you didn’t pick | No write to `blocks` from Cluny |
| Journal split | Wrote in Cluny catalog, missing in Kosistenz/iPhone | Files stay in Kosistenz; Cluny indexes copies |
| Ghost proposals | Same PDF task every morning | Stable proposal id + accept/reject |
| Hard down | Cluny crash loses the week | Week never stored only in Cluny |
| Deadline as meeting | 11:59 essay = busy bar | Deadline heuristic stays in Kosistenz ingest |
| Goal double spawn | Cluny and Kosistenz both create “3h spanish” | Weekly spawn only in Kosistenz |

---

## Vocabulary (use these words in both repos)

| Say | Do not say |
|-----|------------|
| Kosistenz **commits** a to-do / block / journal | Cluny “saves the todo” |
| Cluny **proposes** work | Cluny “schedules” / “places” / “fills the week” |
| Kosistenz **publishes** a snapshot | Cluny “owns calendar.sqlite for Kosistenz” |
| Cluny **indexes** the journal | Cluny “is the journal database” |
| Deadline vs hard vs soft | “Calendar event” for an all-day due |
| Packer / first free gap | “AI timeboxing” |

---

## Success definition

You open **Kosistenz** to live the day (clock, to-dos, goals, gym, journal, phone). You open **Cluny** (or Ask Cluny) to think (PDFs, notes, “what did I write,” “what does this syllabus imply”). Suggestions become real only when you accept them in Kosistenz. The week still makes sense if Cluny is quit. There is still **one** list and **one** clock.
