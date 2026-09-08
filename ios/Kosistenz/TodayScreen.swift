import SwiftUI

struct TodayScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var draftTodo = ""
    @State private var askMiles = false
    @State private var askOther = false
    @State private var milesDraft = ""
    @State private var otherDraft = ""

    private var todayItems: [WorkItem] {
        (store.pack?.work.items ?? []).filter { $0.scheduled_date == store.today }
    }

    private var todaySessions: [WorkoutSession] {
        (store.pack?.workouts.sessions ?? []).filter { $0.local_date == store.today }
    }

    private var agenda: [CalendarItem] {
        let day = store.pack?.calendar.days.first(where: { $0.date == store.today })
        return (day?.events ?? []) + (day?.blocks ?? [])
    }

    private var expected: [String] {
        WorkoutPlan.expectedKinds(on: Date(), template: store.pack?.workouts.template)
    }

    private var logged: Set<String> {
        Set(todaySessions.map(\.kind))
    }

    private var expectedLabels: String {
        expected.map { id in WorkoutPlan.chipKinds.first(where: { $0.id == id })?.label ?? id }.joined(separator: " · ")
    }

    private var heading: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEEE"
        return formatter.string(from: Date())
    }

    var body: some View {
        NavigationStack {
            List {
                statusSection
                clockSection
                todoSection
                workoutSection
                journalTeaser
                if let error = store.error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .navigationTitle(heading)
            .toolbarBackground(store.palette.sidebar, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .refreshable { store.reload() }
            .onAppear { store.reload() }
            .alert("Miles for this run", isPresented: $askMiles) {
                TextField("Miles", text: $milesDraft)
                    .keyboardType(.decimalPad)
                Button("Save") { logRun() }
                Button("Cancel", role: .cancel) { milesDraft = "" }
            }
            .alert("Name this session", isPresented: $askOther) {
                TextField("Pickleball, walk, …", text: $otherDraft)
                Button("Save") { logOther() }
                Button("Cancel", role: .cancel) { otherDraft = "" }
            }
        }
    }

    private var statusSection: some View {
        Section {
            Text(dateLine)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text(statusLine)
                .font(.caption)
                .foregroundStyle(.secondary)
        } header: {
            Text("Today")
        }
        .listRowBackground(store.palette.widgetBg)
    }

    private var clockSection: some View {
        Section("On the clock") {
            if agenda.isEmpty {
                Text("No lectures or blocks on today.")
                    .foregroundStyle(.secondary)
                    .listRowBackground(store.palette.widgetBg)
            } else {
                ForEach(agenda) { item in
                    HStack {
                        Text(DayStamp.clock(item.start_at)).monospacedDigit()
                        Text(item.title ?? "")
                        Spacer()
                        Text(item.kind == "hard" ? "Class" : (item.kind ?? ""))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
            }
        }
    }

    private var todoSection: some View {
        Section("To Do") {
            if todayItems.isEmpty {
                Text("Nothing dated for today.")
                    .foregroundStyle(.secondary)
                    .listRowBackground(store.palette.widgetBg)
            }
            ForEach(todayItems) { item in
                Button { toggle(item) } label: {
                    Label(item.title, systemImage: item.status == "done" ? "checkmark.circle.fill" : "circle")
                        .foregroundStyle(item.status == "done" ? store.palette.done : store.palette.openNext)
                }
                .listRowBackground(store.palette.widgetBg)
            }
            HStack {
                TextField("Add for today", text: $draftTodo)
                Button("Add") { addTodo() }
                    .disabled(draftTodo.trimmingCharacters(in: .whitespaces).isEmpty)
            }
            .listRowBackground(store.palette.widgetBg)
        }
    }

    private var workoutSection: some View {
        Section("Workout") {
            if todaySessions.isEmpty {
                Text(expected.isEmpty ? "No session yet" : "Expected: \(expectedLabels)")
                    .foregroundStyle(.secondary)
                    .listRowBackground(store.palette.widgetBg)
            } else {
                ForEach(todaySessions) { session in
                    Text(WorkoutPlan.sessionLabel(session))
                        .listRowBackground(store.palette.widgetBg)
                }
            }
            HStack {
                ForEach(WorkoutPlan.chipKinds, id: \.id) { kind in
                    let due = expected.contains(kind.id)
                    let done = logged.contains(kind.id)
                    Button(kind.label) { tapWorkout(kind.id) }
                        .buttonStyle(.bordered)
                        .tint(done ? store.palette.done : due ? store.palette.accent : store.palette.widgetBorder)
                }
            }
            .font(.caption)
            .listRowBackground(store.palette.widgetBg)
        }
    }

    private var journalTeaser: some View {
        Section("Journal") {
            if let entry = todayJournal {
                Text(entry.content)
                    .lineLimit(3)
                    .listRowBackground(store.palette.widgetBg)
                Button("Continue writing") { store.tab = .journal }
                    .listRowBackground(store.palette.widgetBg)
            } else {
                Text("Nothing saved today.")
                    .foregroundStyle(.secondary)
                    .listRowBackground(store.palette.widgetBg)
                Button("Write") { store.tab = .journal }
                    .listRowBackground(store.palette.widgetBg)
            }
        }
    }

    private var todayJournal: JournalEntry? {
        (store.pack?.journal ?? []).first { ($0.date ?? $0.created_at ?? "").hasPrefix(store.today) }
    }

    private var dateLine: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .long
        return formatter.string(from: Date())
    }

    private var statusLine: String {
        if store.access == .needsFolder {
            return "Choose iCloud Drive / Kosistenz in Sync — until then this iPhone only."
        }
        if let synced = store.syncedAt {
            return "Pack \(synced)"
        }
        return "Waiting for iCloud. Sync now on the Sync tab, or push from the Mac."
    }

    private func toggle(_ item: WorkItem) {
        guard var pack = store.pack else { return }
        guard let index = pack.work.items.firstIndex(where: { $0.id == item.id }) else { return }
        pack.work.items[index].status = item.status == "done" ? "open" : "done"
        pack.work.items[index].updated_at = DayStamp.isoNow()
        persistWork(pack)
    }

    private func addTodo() {
        guard var pack = store.pack else { return }
        let title = draftTodo.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else { return }
        let now = DayStamp.isoNow()
        pack.work.items.insert(
            WorkItem(
                id: UUID().uuidString,
                title: title,
                notes: "",
                scheduled_date: store.today,
                status: "open",
                active_started_at: nil,
                finished_at: nil,
                duration_seconds: 0,
                sort_order: 0,
                created_at: now,
                updated_at: now,
                source: "iphone",
                series_id: nil,
                occurrence_date: store.today,
                due_at: nil,
                estimate_minutes: nil,
                goal_id: nil
            ),
            at: 0
        )
        draftTodo = ""
        persistWork(pack)
    }

    private func persistWork(_ pack: Pack) {
        do {
            try SyncPack.saveWork(pack.work)
            store.pack = pack
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func tapWorkout(_ kind: String) {
        if kind == "running" {
            milesDraft = ""
            askMiles = true
            return
        }
        if kind == "other" {
            otherDraft = ""
            askOther = true
            return
        }
        logSession(kind: kind, miles: nil, other: "")
    }

    private func logRun() {
        let miles = Double(milesDraft.replacingOccurrences(of: ",", with: "."))
        guard let miles, miles > 0 else {
            store.error = "Add miles for a run"
            return
        }
        logSession(kind: "running", miles: miles, other: "")
        milesDraft = ""
    }

    private func logOther() {
        let name = otherDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else {
            store.error = "Name the other activity"
            return
        }
        logSession(kind: "other", miles: nil, other: name)
        otherDraft = ""
    }

    private func logSession(kind: String, miles: Double?, other: String) {
        guard var pack = store.pack else { return }
        pack.workouts.sessions.append(
            WorkoutSession(
                id: UUID().uuidString,
                local_date: store.today,
                kind: kind,
                other_label: other,
                miles: miles,
                minutes: nil,
                created_at: DayStamp.isoNow()
            )
        )
        do {
            try SyncPack.saveWorkouts(pack.workouts)
            store.pack = pack
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }
}
