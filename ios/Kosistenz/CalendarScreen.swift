import SwiftUI

struct CalendarScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var showAdd = false
    @State private var mode: CalMode = .today
    @State private var selectedDate = DayStamp.today()
    @State private var selectedBar: CalendarItem?
    @State private var pendingOutcome: String?
    @State private var askRepeat = false

    private enum CalMode: String, CaseIterable, Identifiable {
        case today = "Today"
        case week = "Week"
        var id: String { rawValue }
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if mode == .week, let calendar = store.pack?.calendar, !calendar.days.isEmpty {
                    GeometryReader { geo in
                        WeekClockView(
                            file: calendar,
                            palette: store.palette,
                            height: max(280, geo.size.height - 28),
                            onSelect: { selectedBar = $0 }
                        )
                        .padding(.horizontal, 8)
                        .padding(.top, 4)
                    }
                } else {
                    dayClock
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(store.palette.pageBg)
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Picker("View", selection: $mode) {
                        ForEach(CalMode.allCases) { item in
                            Text(item.rawValue).tag(item)
                        }
                    }
                    .pickerStyle(.segmented)
                    .frame(maxWidth: 160)
                    .controlSize(.mini)
                }
                ToolbarItem(placement: .topBarLeading) {
                    QuietSyncButton()
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Add") { showAdd = true }
                }
            }
            .sheet(isPresented: $showAdd) {
                AddEventSheet(
                    palette: store.palette,
                    defaultDate: selectedDate,
                    dayStart: store.pack?.calendar.day_start,
                    dayEnd: store.pack?.calendar.day_end,
                    onSave: { pack in
                        store.pack = pack
                        store.error = nil
                    },
                    onError: { store.error = $0 }
                )
            }
            .sheet(item: $selectedBar) { item in
                BarSheet(
                    item: item,
                    palette: store.palette,
                    repeats: repeats(item),
                    onHappened: { mark(item, status: "done") },
                    onMissed: { mark(item, status: "skipped") },
                    onCheckOff: { checkOff(item) },
                    onDismiss: { selectedBar = nil }
                )
                .environmentObject(store)
            }
            .confirmationDialog("This day or the series?", isPresented: $askRepeat, titleVisibility: .visible) {
                Button("This day") { applyOutcome(series: false) }
                Button("The series") { applyOutcome(series: true) }
                Button("Cancel", role: .cancel) { pendingOutcome = nil }
            } message: {
                Text("Repeating events need a choice. This is remembered next time.")
            }
            .refreshable { store.reload() }
            .onAppear {
                selectedDate = store.today
            }
        }
    }

    private var dayClock: some View {
        let pages = dayPages
        return TabView(selection: $selectedDate) {
            ForEach(pages, id: \.self) { date in
                GeometryReader { geo in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(dayHeading(date))
                            .font(.headline)
                            .foregroundStyle(store.palette.titles)
                            .padding(.horizontal, 12)
                        DayClockView(
                            day: day(for: date),
                            dayStart: store.pack?.calendar.day_start,
                            dayEnd: store.pack?.calendar.day_end,
                            palette: store.palette,
                            height: max(280, geo.size.height - 88),
                            onSelect: { selectedBar = $0 },
                            onToggleDue: { toggleDue($0) }
                        )
                        .padding(.horizontal, 8)
                    }
                }
                .tag(date)
            }
        }
        .tabViewStyle(.page(indexDisplayMode: .never))
    }

    private var dayPages: [String] {
        let packed = store.pack?.calendar.days ?? []
        let start = packed.first?.date ?? DayStamp.addDays(store.today, -1)
        let end = packed.last?.date ?? DayStamp.addDays(store.today, 1)
        var dates: [String] = []
        var cursor = DayStamp.addDays(start, -1)
        let last = DayStamp.addDays(end, 1)
        while cursor <= last {
            dates.append(cursor)
            cursor = DayStamp.addDays(cursor, 1)
            if dates.count > 16 { break }
        }
        if !dates.contains(selectedDate) {
            dates.append(selectedDate)
            dates.sort()
        }
        if dates.isEmpty { return [store.today] }
        return dates
    }

    private func day(for date: String) -> CalendarDay {
        if let match = store.pack?.calendar.days.first(where: { $0.date == date }) {
            return match
        }
        return CalendarDay(date: date, weekday: DayStamp.weekday(date), is_today: date == store.today)
    }

    private func dayHeading(_ date: String) -> String {
        let name = DayStamp.weekdayLong(date)
        if date == store.today { return "\(name) · Today" }
        return "\(name) \(String(date.suffix(5)))"
    }

    private func repeats(_ item: CalendarItem) -> Bool {
        guard let id = item.itemId else { return false }
        return (store.pack?.calendar.hard_events.first(where: { $0.id == id })?.weekdays.count ?? 0) > 0
    }

    private func mark(_ item: CalendarItem, status: String) {
        if repeats(item), RepeatScope.stored == nil {
            selectedBar = item
            pendingOutcome = status
            askRepeat = true
            return
        }
        applyMark(item, status: status, series: RepeatScope.stored == .series)
    }

    private func applyOutcome(series: Bool) {
        RepeatScope.stored = series ? .series : .occurrence
        guard let item = selectedBar, let status = pendingOutcome else { return }
        pendingOutcome = nil
        applyMark(item, status: status, series: series)
    }

    private func applyMark(_ item: CalendarItem, status: String, series: Bool) {
        do {
            store.pack = try PackActions.markBar(item, status: status, series: series)
            store.error = nil
            selectedBar = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func checkOff(_ item: CalendarItem) {
        do {
            store.pack = try PackActions.completeClock(item)
            store.error = nil
            selectedBar = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func toggleDue(_ due: DueItem) {
        guard let id = due.itemId, !id.isEmpty else { return }
        do {
            store.pack = try PackActions.toggle(id: id)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }
}

private struct BarSheet: View {
    @EnvironmentObject private var store: PackStore
    var item: CalendarItem
    var palette: KosistenzPalette
    var repeats: Bool
    var onHappened: () -> Void
    var onMissed: () -> Void
    var onCheckOff: () -> Void
    var onDismiss: () -> Void
    @State private var draft = ""
    @State private var pickId = ""

    private var isWork: Bool {
        let kind = (item.kind ?? "").lowercased()
        return kind == "work" || item.work_item_id != nil
    }

    private var isFocus: Bool {
        (item.kind ?? "").lowercased() == "focus"
    }

    private var focusId: String {
        item.itemId ?? item.id
    }

    private var attached: [NoteEntry] {
        (store.pack?.notes ?? []).filter { $0.focus_id == focusId }
    }

    private var storage: [NoteEntry] {
        (store.pack?.notes ?? []).filter { ($0.focus_id ?? "").isEmpty }
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text(item.title ?? "Event")
                        .font(.headline)
                        .listRowBackground(palette.widgetBg)
                    if !timeLine.isEmpty {
                        Text(timeLine)
                            .foregroundStyle(.secondary)
                            .listRowBackground(palette.widgetBg)
                    }
                    if repeats {
                        Text("Repeating. Happened / Missed will ask this day vs the series unless you already chose.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .listRowBackground(palette.widgetBg)
                    }
                }
                Section {
                    Button("Happened", action: onHappened)
                        .listRowBackground(palette.widgetBg)
                    Button("Missed", action: onMissed)
                        .listRowBackground(palette.widgetBg)
                    if isWork {
                        Button(item.status == "done" ? "Open again" : "Check off", action: onCheckOff)
                            .listRowBackground(palette.widgetBg)
                    }
                }
                if isFocus {
                    Section("Notes on this span") {
                        if attached.isEmpty {
                            Text("No notes on this span.")
                                .foregroundStyle(.secondary)
                                .listRowBackground(palette.widgetBg)
                        }
                        ForEach(attached) { note in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(note.title.isEmpty ? "Note" : note.title)
                                    .font(.headline)
                                if !note.body.isEmpty {
                                    Text(note.body)
                                        .font(.subheadline)
                                }
                                Button("Back to storage") { detach(note.id) }
                            }
                            .listRowBackground(palette.widgetBg)
                        }
                        if !storage.isEmpty {
                            Picker("Attach from storage", selection: $pickId) {
                                Text("Attach from storage…").tag("")
                                ForEach(storage) { note in
                                    Text(note.title.isEmpty ? "Note" : note.title).tag(note.id)
                                }
                            }
                            .onChange(of: pickId) { _, value in
                                guard !value.isEmpty else { return }
                                attach(value)
                                pickId = ""
                            }
                            .listRowBackground(palette.widgetBg)
                        }
                        TextField("New note on this span", text: $draft, axis: .vertical)
                            .lineLimit(3...6)
                            .listRowBackground(palette.widgetBg)
                        Button("Save note here") { addNote() }
                            .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                            .listRowBackground(palette.widgetBg)
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(palette.pageBg)
            .navigationTitle("On the clock")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close", action: onDismiss)
                }
            }
        }
    }

    private var timeLine: String {
        let start = DayStamp.clock(item.start_at)
        let end = DayStamp.clock(item.end_at)
        if start.isEmpty { return "" }
        if end.isEmpty { return start }
        return "\(start)–\(end)"
    }

    private func attach(_ noteId: String) {
        do {
            store.pack = try PackActions.attachNote(id: noteId, focusId: focusId)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func detach(_ noteId: String) {
        do {
            store.pack = try PackActions.detachNote(id: noteId)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func addNote() {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        do {
            store.pack = try PackActions.addNote(title: "", body: text, focusId: focusId)
            draft = ""
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }
}

private enum RepeatScope: String {
    case occurrence
    case series
    static let key = "kosistenz.repeatScope"
    static var stored: RepeatScope? {
        get {
            RepeatScope(rawValue: UserDefaults.standard.string(forKey: key) ?? "")
        }
        set {
            if let newValue {
                UserDefaults.standard.set(newValue.rawValue, forKey: key)
            }
        }
    }
}
