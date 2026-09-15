import SwiftUI

struct TodoScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var draft = ""

    private var offClock: [WorkItem] {
        (store.pack?.work.items ?? []).filter { item in
            item.status != "done" && (item.scheduled_date ?? "") != store.today
        }
        .sorted(by: workSort)
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text(store.statusLine)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .listRowBackground(store.palette.widgetBg)
                }
                Section("Park in Work") {
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
                        Text("Nothing off the clock. Park a thought, or it is already on Today.")
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
            .navigationTitle("Work")
            .toolbar { SyncToolbarButton() }
            .refreshable { store.reload() }
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
            Button("Today") { moveToday(item) }
                .font(.caption.weight(.semibold))
        }
        .listRowBackground(store.palette.widgetBg)
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

    private func moveToday(_ item: WorkItem) {
        do {
            store.pack = try PackActions.assignToToday(id: item.id, date: store.today)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func workSort(_ lhs: WorkItem, _ rhs: WorkItem) -> Bool {
        let leftDue = lhs.due_at ?? "9999"
        let rightDue = rhs.due_at ?? "9999"
        if leftDue != rightDue { return leftDue < rightDue }
        let leftDay = lhs.scheduled_date ?? "9999"
        let rightDay = rhs.scheduled_date ?? "9999"
        if leftDay != rightDay { return leftDay < rightDay }
        return lhs.title < rhs.title
    }

    private func workSubtitle(_ item: WorkItem) -> String? {
        if let due = item.due_at, due.count >= 10 {
            return "Due \(String(due.prefix(10)))"
        }
        return item.scheduled_date
    }

    private func bucket(_ item: WorkItem) -> WorkGroup {
        let today = store.today
        if let due = item.due_at, due.count >= 10 {
            let dueDay = String(due.prefix(10))
            if dueDay <= addDays(today, 7) {
                return .dueSoon
            }
        }
        guard let scheduled = item.scheduled_date, !scheduled.isEmpty else {
            return .noDay
        }
        let start = weekStart
        let end = addDays(start, 6)
        if scheduled >= start && scheduled <= end {
            return .thisWeek
        }
        return .later
    }

    private var weekStart: String {
        if let packed = store.pack?.calendar.week_start, packed.count >= 10 {
            return String(packed.prefix(10))
        }
        return monday(of: store.today)
    }

    private func monday(of iso: String) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        guard let day = formatter.date(from: String(iso.prefix(10))) else { return iso }
        var calendar = Calendar(identifier: .gregorian)
        calendar.firstWeekday = 2
        let weekday = calendar.component(.weekday, from: day)
        let offset = (weekday + 5) % 7
        return formatter.string(from: calendar.date(byAdding: .day, value: -offset, to: day) ?? day)
    }

    private func addDays(_ iso: String, _ days: Int) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        guard let day = formatter.date(from: String(iso.prefix(10))) else { return iso }
        return formatter.string(from: Calendar(identifier: .gregorian).date(byAdding: .day, value: days, to: day) ?? day)
    }
}

private enum WorkGroup: String, CaseIterable, Identifiable {
    case dueSoon, thisWeek, later, noDay

    var id: String { rawValue }

    var title: String {
        switch self {
        case .dueSoon: return "Due soon"
        case .thisWeek: return "This week"
        case .later: return "Later"
        case .noDay: return "No day"
        }
    }
}
