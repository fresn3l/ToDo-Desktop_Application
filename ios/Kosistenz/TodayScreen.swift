import SwiftUI
import UIKit

struct TodayScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var draft = ""
    @State private var weekDraft = ""
    @State private var parkDraft = ""
    @State private var burstingId: String?
    @State private var change: DayChange?

    private var rows: [TodayList.Entry] {
        guard let pack = store.pack else { return [] }
        return TodayList.entries(pack: pack, today: store.today)
    }

    private var clockRows: [TodayList.Entry] {
        rows.filter { $0.kind == .clock }
    }

    private var taskRows: [TodayList.Entry] {
        rows.filter { $0.kind == .task }
    }

    var body: some View {
        NavigationStack {
            List {
                if store.access == .needsFolder {
                    Section {
                        Text(store.statusLine)
                            .foregroundStyle(.secondary)
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
                Section("On the clock") {
                    if clockRows.isEmpty {
                        Text("Nothing on the clock.")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(clockRows) { row in
                        TodayCheckRow(
                            entry: row,
                            palette: store.palette,
                            bursting: burstingId == row.id
                        ) {
                            complete(row)
                        }
                        .contextMenu { rowMenu(row) }
                    }
                }
                .listRowBackground(store.palette.widgetBg)
                Section("Today") {
                    if taskRows.isEmpty {
                        Text("Nothing dated today.")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(taskRows) { row in
                        TodayCheckRow(
                            entry: row,
                            palette: store.palette,
                            bursting: burstingId == row.id
                        ) {
                            complete(row)
                        }
                        .contextMenu { rowMenu(row) }
                    }
                    HStack {
                        TextField("Add for today", text: $draft)
                        Button("Add") { addTodo() }
                            .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                }
                .listRowBackground(store.palette.widgetBg)
                Section("This week") {
                    HStack {
                        TextField("Sometime this week", text: $weekDraft)
                            .onSubmit { addWeek() }
                        Button("Add") { addWeek() }
                            .disabled(weekDraft.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                }
                .listRowBackground(store.palette.widgetBg)
                Section("Park") {
                    HStack {
                        TextField("No day yet", text: $parkDraft)
                        Button("Park") { park() }
                            .disabled(parkDraft.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                }
                .listRowBackground(store.palette.widgetBg)
                if let error = store.error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .navigationTitle(heading)
            .toolbarBackground(store.palette.sidebar, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar { QuietSyncButton() }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .refreshable { store.reload() }
            .onAppear { store.reload() }
            .sheet(item: $change) { pending in
                DayChangeSheet(change: pending, palette: store.palette) { pack in
                    store.pack = pack
                    store.error = nil
                } onError: { store.error = $0 }
            }
        }
    }

    @ViewBuilder
    private func rowMenu(_ row: TodayList.Entry) -> some View {
        Button("Rename") { change = DayChange(entry: row, mode: .rename) }
        Button(row.kind == .clock ? "Reschedule" : "Another day") {
            change = DayChange(entry: row, mode: .reschedule)
        }
        Button("Delete", role: .destructive) { remove(row) }
    }

    private var heading: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEEE"
        return formatter.string(from: Date())
    }

    private func complete(_ entry: TodayList.Entry) {
        do {
            if !entry.done {
                burstingId = entry.id
                UINotificationFeedbackGenerator().notificationOccurred(.success)
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                    if burstingId == entry.id { burstingId = nil }
                }
            }
            store.pack = try PackActions.complete(entry)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func addTodo() {
        let title = draft
        draft = ""
        do {
            store.pack = try PackActions.addTodo(title, date: store.today)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func recordId(_ entry: TodayList.Entry) -> String {
        if entry.kind == .task { return entry.workId ?? "" }
        let raw = entry.clockId ?? ""
        if let at = raw.firstIndex(of: "@") { return String(raw[..<at]) }
        return raw
    }

    private func remove(_ entry: TodayList.Entry) {
        do {
            if entry.kind == .clock {
                store.pack = try PackActions.deleteHardEvent(id: recordId(entry))
            } else if let workId = entry.workId {
                store.pack = try PackActions.deleteTodo(id: workId)
            }
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func addWeek() {
        let title = weekDraft
        weekDraft = ""
        do {
            store.pack = try PackActions.addThisWeek(title)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func park() {
        let title = parkDraft
        parkDraft = ""
        do {
            store.pack = try PackActions.park(title)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }
}

struct DayChange: Identifiable {
    enum Mode {
        case rename
        case reschedule
    }

    var entry: TodayList.Entry
    var mode: Mode
    var id: String { entry.id + (mode == .rename ? "-rename" : "-move") }
}

struct DayChangeSheet: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var store: PackStore
    var change: DayChange
    var palette: KosistenzPalette
    var onSave: (Pack) -> Void
    var onError: (String) -> Void

    @State private var title = ""
    @State private var date = Date()
    @State private var startText = "09:30"
    @State private var endText = "10:30"
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                Section(change.entry.kind == .clock ? "Appointment" : "To-do") {
                    TextField("Name", text: $title)
                    if change.mode == .reschedule {
                        DatePicker("Date", selection: $date, displayedComponents: .date)
                        if change.entry.kind == .clock {
                            TextField("Start", text: $startText)
                                .keyboardType(.numbersAndPunctuation)
                            TextField("End", text: $endText)
                                .keyboardType(.numbersAndPunctuation)
                        }
                    }
                }
                if let error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .navigationTitle(change.mode == .rename ? "Rename" : "Reschedule")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { save() }
                        .disabled(title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
            .onAppear { fill() }
        }
        .tint(palette.accent)
    }

    private func fill() {
        title = change.entry.title
        if let raw = change.entry.startAt, raw.count >= 16 {
            startText = String(raw.dropFirst(11).prefix(5))
        }
        if let raw = change.entry.endAt, raw.count >= 16 {
            endText = String(raw.dropFirst(11).prefix(5))
        }
        let day = String((change.entry.startAt ?? store.today).prefix(10))
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        date = formatter.date(from: day) ?? Date()
    }

    private func stampDay(_ value: Date) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar.current
        formatter.locale = Locale.current
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: value)
    }

    private func save() {
        do {
            let pack: Pack
            if change.entry.kind == .clock {
                let eventId = {
                    let raw = change.entry.clockId ?? ""
                    if let at = raw.firstIndex(of: "@") { return String(raw[..<at]) }
                    return raw
                }()
                if change.mode == .rename, let event = store.pack?.calendar.hard_events.first(where: { $0.id == eventId }) {
                    pack = try PackActions.updateHardEvent(id: eventId, title: title, startAt: event.start_at, endAt: event.end_at)
                } else {
                    let day = stampDay(date)
                    let startAt = try PhoneCalendar.combine(date: day, time: startText)
                    let endAt = try PhoneCalendar.combine(date: day, time: endText)
                    pack = try PackActions.updateHardEvent(id: eventId, title: title, startAt: startAt, endAt: endAt)
                }
            } else if let workId = change.entry.workId {
                if change.mode == .rename {
                    pack = try PackActions.renameTodo(id: workId, title: title)
                } else {
                    pack = try PackActions.assignDay(id: workId, date: stampDay(date))
                }
            } else {
                throw PackActionError.message("That row is gone.")
            }
            onSave(pack)
            dismiss()
        } catch {
            let text = error.localizedDescription
            self.error = text
            onError(text)
        }
    }
}

struct TodayCheckRow: View {
    var entry: TodayList.Entry
    var palette: KosistenzPalette
    var bursting: Bool
    var onToggle: () -> Void

    var body: some View {
        Button(action: onToggle) {
            HStack(spacing: 14) {
                ZStack {
                    Circle()
                        .stroke(entry.done ? palette.done : palette.openNext, lineWidth: 2)
                        .frame(width: 28, height: 28)
                    if entry.done {
                        Image(systemName: "checkmark")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(palette.done)
                            .scaleEffect(bursting ? 1.25 : 1)
                    }
                    if bursting {
                        Circle()
                            .stroke(palette.done.opacity(0.45), lineWidth: 3)
                            .frame(width: bursting ? 46 : 28, height: bursting ? 46 : 28)
                    }
                }
                .frame(width: 36, height: 36)
                VStack(alignment: .leading, spacing: 2) {
                    Text(entry.title)
                        .font(.body.weight(.semibold))
                        .strikethrough(entry.done, color: palette.done)
                        .foregroundStyle(entry.done ? palette.done : palette.titles)
                    Text(entry.timeLabel)
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }
            .padding(.vertical, 6)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .animation(.spring(response: 0.38, dampingFraction: 0.62), value: entry.done)
        .animation(.spring(response: 0.42, dampingFraction: 0.55), value: bursting)
        .accessibilityLabel("\(entry.title), \(entry.timeLabel)")
        .accessibilityAddTraits(entry.done ? [.isSelected] : [])
    }
}

struct QuietSyncButton: View {
    @EnvironmentObject private var store: PackStore

    var body: some View {
        Button {
            store.showSync = true
        } label: {
            Image(systemName: store.access == .iCloudDrive ? "icloud" : "icloud.slash")
                .foregroundStyle(store.access == .iCloudDrive ? store.palette.ink : Color.red)
        }
        .accessibilityLabel(store.access == .iCloudDrive ? "Sync" : "Sync failed — choose folder")
    }
}

struct SyncToolbarButton: View {
    var body: some View { QuietSyncButton() }
}
