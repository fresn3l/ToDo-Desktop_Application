import SwiftUI
import UIKit

struct WorkScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var draft = ""
    @State private var filter = "today"
    @State private var burstingId: String?
    @State private var placing: UnplacedItem?
    @State private var dueDate = Date()
    @State private var useDue = false

    private let filters: [(id: String, label: String)] = [
        ("today", "Today"),
        ("all", "All"),
        ("unplaced", "Unplaced"),
        ("due", "Due"),
    ]

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Picker("Filter", selection: $filter) {
                        ForEach(filters, id: \.id) { item in
                            Text(item.label).tag(item.id)
                        }
                    }
                    .pickerStyle(.segmented)
                    .listRowBackground(store.palette.widgetBg)
                    if let line = summary, !line.isEmpty {
                        Text(line)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .listRowBackground(store.palette.widgetBg)
                    }
                }
                if store.access == .needsFolder {
                    Section {
                        Text(store.statusLine)
                            .foregroundStyle(.secondary)
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
                if filter == "today" {
                    todayRows
                } else {
                    workRows
                }
                Section {
                    HStack {
                        TextField(placeholder, text: $draft)
                        Button(addLabel) { add() }
                            .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                    if filter == "due" {
                        Toggle("Due date", isOn: $useDue)
                        if useDue {
                            DatePicker("Due", selection: $dueDate, displayedComponents: .date)
                        }
                    }
                }
                .listRowBackground(store.palette.widgetBg)
                if let error = store.error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Work")
            .toolbarBackground(store.palette.sidebar, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar { SyncToolbarButton() }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .refreshable { store.reload() }
            .onAppear { store.reload() }
            .sheet(item: $placing) { item in
                PlaceWorkSheet(
                    item: item,
                    palette: store.palette,
                    defaultDate: store.today,
                    dayStart: store.pack?.calendar.day_start,
                    dayEnd: store.pack?.calendar.day_end,
                    onSave: { pack in
                        store.pack = pack
                        store.error = nil
                    },
                    onError: { store.error = $0 }
                )
            }
        }
    }

    @ViewBuilder
    private var todayRows: some View {
        if todayEntries.isEmpty {
            Section {
                Text("Nothing dated for today. Add a task here, or an event on Calendar.")
                    .foregroundStyle(.secondary)
            }
            .listRowBackground(store.palette.widgetBg)
        }
        ForEach(todayEntries) { row in
            TodayCheckRow(
                entry: row,
                palette: store.palette,
                bursting: burstingId == row.id
            ) {
                complete(row)
            }
            .listRowBackground(store.palette.widgetBg)
        }
    }

    @ViewBuilder
    private var workRows: some View {
        if filtered.isEmpty {
            Section {
                Text(emptyCopy)
                    .foregroundStyle(.secondary)
            }
            .listRowBackground(store.palette.widgetBg)
        }
        ForEach(filtered) { item in
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(item.title)
                    if let subtitle = subtitle(item), !subtitle.isEmpty {
                        Text(subtitle)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                if filter == "unplaced" {
                    Button("Place") { placing = unplacedRow(item) }
                        .font(.caption.weight(.semibold))
                } else if filter == "all" {
                    Button("Today") { moveToday(item) }
                        .font(.caption.weight(.semibold))
                } else {
                    Button(item.status == "done" ? "Open" : "Done") { finish(item) }
                        .font(.caption.weight(.semibold))
                }
            }
            .listRowBackground(store.palette.widgetBg)
            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                Button("All Work") { park(item) }
                    .tint(.gray)
                if filter != "today" {
                    Button("Today") { moveToday(item) }
                }
            }
        }
    }

    private var todayEntries: [TodayList.Entry] {
        guard let pack = store.pack else { return [] }
        return TodayList.entries(pack: pack, today: store.today)
    }

    private var unplacedIds: Set<String> {
        guard let pack = store.pack else { return [] }
        return Set(
            PhoneCalendar.unplacedFromWork(
                items: pack.work.items,
                blocks: PhoneCalendar.flattenBlocks(days: pack.calendar.days) + pack.calendar.phone_blocks
            ).compactMap(\.itemId)
        )
    }

    private var filtered: [WorkItem] {
        PhoneWork.filterItems(
            store.pack?.work.items ?? [],
            kind: filter,
            today: store.today,
            unplacedIds: unplacedIds
        )
    }

    private var summary: String? {
        if filter == "today" {
            let open = todayEntries.filter { !$0.done }.count
            let done = todayEntries.filter(\.done).count
            if open == 0 && done == 0 { return "Empty — add work for today" }
            return "\(open) open · \(done) finished"
        }
        if filter == "all" {
            return filtered.isEmpty ? "Empty — add work for later" : "\(filtered.count) waiting to be dated"
        }
        if filter == "unplaced" {
            return filtered.isEmpty ? "Nothing unplaced" : "\(filtered.count) with minutes left off the clock"
        }
        return filtered.isEmpty ? "Nothing due" : "\(filtered.count) with a due date"
    }

    private var placeholder: String {
        if filter == "all" { return "A task without a date yet" }
        if filter == "due" { return "What’s due" }
        if filter == "unplaced" { return "45 mins board memo" }
        return "45 mins board memo"
    }

    private var addLabel: String {
        if filter == "all" { return "Park" }
        if filter == "due" { return "Add due" }
        if filter == "unplaced" { return "Add unplaced" }
        return "Add"
    }

    private var emptyCopy: String {
        if filter == "all" { return "Nothing parked in All Work." }
        if filter == "unplaced" { return "Nothing to place. Add minutes, then Fill week or Place on Calendar." }
        return "No due dates."
    }

    private func subtitle(_ item: WorkItem) -> String? {
        if let due = item.due_at, !due.isEmpty {
            return "Due \(String(due.prefix(10)))"
        }
        if let scheduled = item.scheduled_date, !scheduled.isEmpty {
            return scheduled
        }
        if let mins = item.estimate_minutes, mins > 0 {
            return "\(mins) min"
        }
        return nil
    }

    private func unplacedRow(_ item: WorkItem) -> UnplacedItem {
        UnplacedItem(
            itemId: item.id,
            title: item.title,
            scheduled_date: item.scheduled_date,
            due_at: item.due_at,
            estimate_minutes: item.estimate_minutes,
            remaining_minutes: item.estimate_minutes
        )
    }

    private func add() {
        let title = draft
        draft = ""
        do {
            let date: String?
            var due: String?
            if filter == "all" || filter == "unplaced" {
                date = nil
            } else {
                date = store.today
            }
            if filter == "due", useDue {
                due = stampDay(dueDate)
            }
            store.pack = try PackActions.addWork(title, date: date, due: due)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
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

    private func moveToday(_ item: WorkItem) {
        do {
            store.pack = try PackActions.assignToToday(id: item.id, date: store.today)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func park(_ item: WorkItem) {
        do {
            store.pack = try PackActions.assignDate(id: item.id, date: nil)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func finish(_ item: WorkItem) {
        do {
            store.pack = try PackActions.finishWork(id: item.id)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func stampDay(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar.current
        formatter.locale = Locale.current
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }
}
