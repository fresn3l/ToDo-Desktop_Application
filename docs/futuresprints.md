# Future sprints

The three Home-UI follow-ons below **shipped** on the future-sprints branch. Older product plans (iPhone carry, Cluny proposals) stay in their own docs.

## Month / year calendar (Calendar tab) — shipped

The Calendar tab opens on a **month grid**. Week / Month / Year switch the long view. Prev / Today / Next jump in the current view. A day cell opens the **week clock** for that date. A year month heading opens that month. The Home **Today** widget stays the day strip.

Fill week still places study around lectures and only shows in week view. Nothing is written to Apple Calendar.

## Live Home (always-draggable widgets) — shipped

Drag a widget from its **title bar** without entering Edit Home. Size, add, and remove stay behind Edit Home so a to-do or journal field is not the grab target.

## iPhone appearance (color slots + palettes) — shipped

Mac Settings still owns color slots (page, widget, borders, titles, accent, done, open/next, sidebar), auto button ink with a manual override, widget border width/color in Edit Home, and save/create palettes on top of Ocean / Paper / the other built-ins.

The iPhone reads `appearance.json` from the iCloud pack and applies the Mac’s `resolved` colors. There is no second iPhone-only theme picker.

## Future UX (not this sprint)

Parked while Ask Cluny lands on Home. Do not treat these as blockers for the brain widget.

### Composer / finish flow

- The To Do composer is dense (day chips, estimate, due, goal, repeat, add-to-calendar) for a one-line capture.
- Repeating series vs a single occurrence is easy to get wrong when renaming or deleting.
- Fill week only appears in week view, so month/year users never see the packer.
- Menu bar **Run** logs a 0-mile session; the Workout widget requires miles.

### Unfinished polish

- Settings still lists `⌘1` Today and `2–7` other tabs. The live shortcuts are Home / Calendar / Settings.
- `web/js/today.js` still expects a full Today dashboard (`#todayHome`, module cards) that is not in the DOM. The Home **Today** widget is the mini agenda only.
- Appearance still stores `todayLayout` / `todayOrder` / module toggles with no Settings UI.
- Leftover CSS for `.today-home` / `.today-card` is unused.
