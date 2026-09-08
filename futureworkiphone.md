# Future iPhone work (not this sprint)

Parked while the Mac calendar paste + awake-window sprint ships. Do not treat this as a blocker for ICS paste or 05:30–21:30.

## Add hard events from the phone

**Done feels like:** On the phone, **Add** a named busy block (class, work, one-off or weekly day chips). It shows on Today’s timeline after Sync. Opening the Mac pulls it onto the week clock. Packed study still cannot be dragged from the phone. Nights stay empty unless you add a block yourself.

### Pack change

Today `calendar.json` is **Mac → phone only**. `apply_pack` ignores phone clock writes on purpose.

To add from the phone:

- Phone **appends/updates hard events** only (`source: iphone`).
- Mac **`apply_pack` merges those events** (same id → newer `updated_at`; new id → insert).
- Still **ignore** packed study blocks from the phone.
- After merge, Mac writes the pack back so the phone sees the canonical week.

Unplaced to-dos stay Inbox. This is **busy time**, not “park a thought.”

### UI

- **Add** on Week (and a short entry on Today): name, start, end, optional Mon–Sun chips, Save.
- 24-hour times, same as the Mac awake fields (`0530`, `21:30`).
- Respect `day_start` / `day_end` already in the pack for the timeline scale (Mac now publishes those keys).

### Later, not required for the first phone-add slice

- App Intent: “Add a class in Kosistenz.”
- Widget stays to-dos.
- Sleep as a locked bar on the clock (explicitly deferred — nights stay empty).
- Fill week / drag blocks on the phone.

### Hard locks (unchanged)

- Cluny does not write the pack or pick clock times.
- No Apple Calendar write-back.
- Last-write-wins with a merge for hard events only; do not put live SQLite in iCloud.
