import SwiftUI

struct TodayScreen: View {
    @State private var pack: Pack?
    @State private var error: String?
    @State private var draftTodo = ""
    @State private var draftJournal = ""
    @State private var usingCloud = false

    private var today: String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar.current
        formatter.locale = Locale.current
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: Date())
    }

    private var heading: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEEE"
        return formatter.string(from: Date())
    }

    private var todayItems: [WorkItem] {
        (pack?.work.items ?? []).filter { $0.scheduled_date == today }
    }

    private var todaySessions: [WorkoutSession] {
        (pack?.workouts.sessions ?? []).filter { $0.local_date == today }
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text(dateLine)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text(usingCloud ? "iCloud Drive / Kosistenz" : "On this iPhone only — sign into iCloud Drive")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } header: {
                    Text("Today")
                }

                Section("To Do") {
                    if todayItems.isEmpty {
                        Text("Nothing dated for today.")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(todayItems) { item in
                        Button {
                            toggle(item)
                        } label: {
                            Label(item.title, systemImage: item.status == "done" ? "checkmark.circle.fill" : "circle")
                        }
                    }
                    HStack {
                        TextField("Add for today", text: $draftTodo)
                        Button("Add") { addTodo() }
                            .disabled(draftTodo.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                }

                Section("Workout") {
                    if todaySessions.isEmpty {
                        Text("No session yet")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(todaySessions) { session in
                            Text(session.other_label?.isEmpty == false ? session.other_label! : session.kind.capitalized)
                        }
                    }
                    HStack {
                        ForEach(["push", "pull", "legs", "running", "other"], id: \.self) { kind in
                            Button(kind.capitalized) { logWorkout(kind) }
                                .buttonStyle(.bordered)
                        }
                    }
                    .font(.caption)
                }

                Section("Journal") {
                    TextField("What happened today?", text: $draftJournal, axis: .vertical)
                        .lineLimit(3...8)
                    Button("Save") { saveJournal() }
                        .disabled(draftJournal.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }

                if let error {
                    Section {
                        Text(error).foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle(heading)
            .refreshable { reload() }
            .onAppear { reload() }
        }
    }

    private var dateLine: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .long
        return formatter.string(from: Date())
    }

    private func reload() {
        usingCloud = SyncPack.usingiCloudDrive()
        do {
            pack = try SyncPack.load()
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func toggle(_ item: WorkItem) {
        guard var pack else { return }
        guard let index = pack.work.items.firstIndex(where: { $0.id == item.id }) else { return }
        pack.work.items[index].status = item.status == "done" ? "open" : "done"
        pack.work.items[index].updated_at = ISO8601DateFormatter().string(from: Date())
        persistWork(pack)
    }

    private func addTodo() {
        guard var pack else { return }
        let title = draftTodo.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else { return }
        let now = ISO8601DateFormatter().string(from: Date())
        pack.work.items.insert(
            WorkItem(
                id: UUID().uuidString,
                title: title,
                notes: "",
                scheduled_date: today,
                status: "open",
                active_started_at: nil,
                finished_at: nil,
                duration_seconds: 0,
                sort_order: 0,
                created_at: now,
                updated_at: now,
                source: "iphone",
                series_id: nil,
                occurrence_date: today
            ),
            at: 0
        )
        draftTodo = ""
        persistWork(pack)
    }

    private func persistWork(_ pack: Pack) {
        do {
            try SyncPack.saveWork(pack.work)
            self.pack = pack
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func logWorkout(_ kind: String) {
        guard var pack else { return }
        let now = ISO8601DateFormatter().string(from: Date())
        pack.workouts.sessions.append(
            WorkoutSession(
                id: UUID().uuidString,
                local_date: today,
                kind: kind,
                other_label: kind == "other" ? "Other" : "",
                miles: kind == "running" ? 0 : nil,
                minutes: nil,
                created_at: now
            )
        )
        do {
            try SyncPack.saveWorkouts(pack.workouts)
            self.pack = pack
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func saveJournal() {
        guard var pack else { return }
        let text = draftJournal.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        let now = ISO8601DateFormatter().string(from: Date())
        let stamp = now.replacingOccurrences(of: ":", with: "-")
        pack.journal.insert(
            JournalEntry(
                id: "entry_\(stamp)_ios",
                content: text,
                date: now,
                duration_seconds: 0,
                continued: false,
                created_at: now,
                tags: []
            ),
            at: 0
        )
        draftJournal = ""
        do {
            try SyncPack.saveJournal(pack.journal)
            self.pack = pack
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }
}
