import SwiftUI

struct TodoScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var draft = ""
    @State private var picking: WorkItem?

    private var offClock: [WorkItem] {
        (store.pack?.work.items ?? []).filter { item in
            item.status != "done"
                && item.source != "calendar"
                && (item.scheduled_date ?? "") != store.today
        }
        .sorted(by: workSort)
    }

    var body: some View {
        NavigationStack {
            List {
                if store.access == .needsFolder {
                    Section {
                        Text(store.statusLine)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .listRowBackground(store.palette.widgetBg)
                    }
                }
                Section("Park in To Do") {
                    HStack {
                        TextField("No day yet", text: $draft)
                        Button("Park") { park() }
                            .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
                ForEach(WorkGroup.allCases) { group in
                    let rows = offClock.filter { bucket($0) == group }
                    if !rows.isEmpty {
                        Section(group.title) {
                            ForEach(rows) { item in
                                todoRow(item)
                            }
                        }
                    }
                }
                if offClock.isEmpty {
                    Section {
                        Text("Nothing in To Do. Park a thought, or it is already on Today.")
                            .foregroundStyle(.secondary)
                            .listRowBackground(store.palette.widgetBg)
                    }
                }
                if let error = store.error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .navigationTitle("To Do")
            .toolbar { QuietSyncButton() }
            .refreshable { store.reload() }
            .sheet(item: $picking) { item in
                DayPickSheet(
                    item: item,
                    today: store.today,
                    weekDates: weekDates,
                    palette: store.palette,
                    onPick: { day in
                        assign(item, day: day)
                        picking = nil
                    },
                    onDismiss: { picking = nil }
                )
            }
        }
    }

    private func todoRow(_ item: WorkItem) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(item.title)
                if let subtitle = workSubtitle(item), !subtitle.isEmpty {
                    Text(subtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
            Button("Today") { assign(item, day: store.today) }
                .font(.caption.weight(.semibold))
        }
        .contentShape(Rectangle())
        .onLongPressGesture { picking = item }
        .contextMenu {
            Button("Today") { assign(item, day: store.today) }
            ForEach(weekDates, id: \.self) { day in
                Button(DayStamp.weekday(day)) { assign(item, day: day) }
            }
            Button("No day") { assign(item, day: "") }
            Button("Pick a day…") { picking = item }
        }
        .listRowBackground(store.palette.widgetBg)
    }

    private var weekDates: [String] {
        (store.pack?.calendar.days ?? []).compactMap(\.date)
    }

    private func park() {
        let title = draft
        draft = ""
        do {
            store.pack = try PackActions.park(title)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func assign(_ item: WorkItem, day: String) {
        do {
            store.pack = try PackActions.assignDay(id: item.id, date: day)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func workSort(_ lhs: WorkItem, _ rhs: WorkItem) -> Bool {
        let leftDay = lhs.scheduled_date ?? "9999"
        let rightDay = rhs.scheduled_date ?? "9999"
        if leftDay != rightDay { return leftDay < rightDay }
        return lhs.title < rhs.title
    }

    private func workSubtitle(_ item: WorkItem) -> String? {
        item.scheduled_date
    }

    private func bucket(_ item: WorkItem) -> WorkGroup {
        let scheduled = item.scheduled_date ?? ""
        if scheduled.isEmpty { return .noDay }
        let dates = weekDates
        if dates.contains(scheduled) { return .thisWeek }
        if let first = dates.first, let last = dates.last, scheduled >= first && scheduled <= last {
            return .thisWeek
        }
        return .later
    }
}

private enum WorkGroup: String, CaseIterable, Identifiable {
    case thisWeek, later, noDay
    var id: String { rawValue }
    var title: String {
        switch self {
        case .thisWeek: return "This week"
        case .later: return "Later"
        case .noDay: return "No day"
        }
    }
}

private struct DayPickSheet: View {
    var item: WorkItem
    var today: String
    var weekDates: [String]
    var palette: KosistenzPalette
    var onPick: (String) -> Void
    var onDismiss: () -> Void
    @State private var picked = Date()

    var body: some View {
        NavigationStack {
            List {
                Section(item.title) {
                    Button("Today") { onPick(today) }
                        .listRowBackground(palette.widgetBg)
                    ForEach(weekDates, id: \.self) { day in
                        Button(DayStamp.weekdayLong(day)) { onPick(day) }
                            .listRowBackground(palette.widgetBg)
                    }
                    DatePicker("Other day", selection: $picked, displayedComponents: .date)
                        .listRowBackground(palette.widgetBg)
                    Button("Use that day") { onPick(DayStamp.dayString(picked)) }
                        .listRowBackground(palette.widgetBg)
                    Button("No day") { onPick("") }
                        .listRowBackground(palette.widgetBg)
                }
            }
            .scrollContentBackground(.hidden)
            .background(palette.pageBg)
            .navigationTitle("Pick a day")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close", action: onDismiss)
                }
            }
        }
    }
}
