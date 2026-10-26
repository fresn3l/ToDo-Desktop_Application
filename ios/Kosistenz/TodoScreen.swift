import SwiftUI

enum TodoGroups {
    static func group(_ item: WorkItem, today: String) -> String {
        let monday = DayStamp.weekMonday(today)
        let scheduled = String((item.scheduled_date ?? "").prefix(10))
        if scheduled == today { return "today" }
        if !scheduled.isEmpty {
            let sunday = DayStamp.addDays(monday, 6)
            if scheduled >= monday && scheduled <= sunday { return "thisWeek" }
            return "later"
        }
        let horizon = item.horizon ?? ""
        let weekOf = String((item.week_of ?? "").prefix(10))
        if horizon == "later" { return "later" }
        if horizon == "week" {
            if weekOf == monday { return "thisWeek" }
            if !weekOf.isEmpty && weekOf < monday { return "review" }
            if !weekOf.isEmpty && weekOf > monday { return "later" }
        }
        return "noDay"
    }

    static func rows(_ pack: Pack?, today: String, group name: String) -> [WorkItem] {
        guard let pack else { return [] }
        return pack.work.items.filter { item in
            item.status != "done"
                && item.source != "calendar"
                && TodayList.live(id: item.id, updated: item.updated_at, deletions: pack.work.deleted ?? [])
                && group(item, today: today) == name
        }
        .sorted(by: sort)
    }

    static func reviewCount(_ pack: Pack?, today: String = DayStamp.today()) -> Int {
        rows(pack, today: today, group: "review").count
    }

    private static func sort(_ lhs: WorkItem, _ rhs: WorkItem) -> Bool {
        let left = lhs.sort_order ?? 0
        let right = rhs.sort_order ?? 0
        if left != right { return left < right }
        return lhs.title.localizedCaseInsensitiveCompare(rhs.title) == .orderedAscending
    }
}

struct TodoScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var draft = ""
    @State private var reviewMode = false
    @State private var picking: WorkItem?

    private var thisWeek: [WorkItem] { TodoGroups.rows(store.pack, today: store.today, group: "thisWeek") }
    private var later: [WorkItem] { TodoGroups.rows(store.pack, today: store.today, group: "later") }
    private var noDay: [WorkItem] { TodoGroups.rows(store.pack, today: store.today, group: "noDay") }
    private var review: [WorkItem] { TodoGroups.rows(store.pack, today: store.today, group: "review") }

    private var thisWeekDates: [String] {
        let monday = DayStamp.weekMonday(store.today)
        return (0..<7).map { DayStamp.addDays(monday, $0) }
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
                Section {
                    TextField("Sometime this week", text: $draft)
                        .onSubmit { addWeek() }
                    HStack {
                        Button("This week") { addWeek() }
                            .buttonStyle(.borderedProminent)
                        Button("Today") { addToday() }
                        Button("Park") { park() }
                    }
                    .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty)
                    Button(review.isEmpty ? "Review" : "Review \(review.count)") {
                        reviewMode.toggle()
                    }
                }
                .listRowBackground(store.palette.widgetBg)
                if reviewMode {
                    Section("Place these") {
                        if review.isEmpty {
                            Text("Nothing left to place.")
                                .foregroundStyle(.secondary)
                        }
                        ForEach(review) { item in
                            todoRow(item, showReview: true)
                        }
                    }
                } else {
                    bucketSection("This week", rows: thisWeek, name: "thisWeek")
                    bucketSection("Later", rows: later, name: "later")
                    bucketSection("No day", rows: noDay, name: "noDay")
                }
                if let error = store.error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .navigationTitle("To Do")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { EditButton() }
                ToolbarItem(placement: .topBarTrailing) { QuietSyncButton() }
            }
            .refreshable { store.reload() }
            .onAppear {
                if store.openReview { reviewMode = true }
            }
            .sheet(item: $picking) { item in
                DayPickSheet(
                    item: item,
                    today: store.today,
                    weekDates: thisWeekDates,
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

    @ViewBuilder
    private func bucketSection(_ title: String, rows: [WorkItem], name: String) -> some View {
        Section(title) {
            if rows.isEmpty {
                Text("Nothing here.")
                    .foregroundStyle(.secondary)
            }
            ForEach(rows) { item in
                todoRow(item, showReview: false)
            }
            .onMove { from, to in
                move(name, from: from, to: to)
            }
        }
    }

    private func todoRow(_ item: WorkItem, showReview: Bool) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(item.title)
            Text(subtitle(item))
                .font(.caption)
                .foregroundStyle(.secondary)
            if showReview {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack {
                        Button("This week") { place(item, "week") }
                        ForEach(thisWeekDates, id: \.self) { day in
                            Button(DayStamp.weekday(day)) { assign(item, day: day) }
                        }
                        Button("Later") { place(item, "later") }
                        Button("Done") { markDone(item) }
                    }
                    .font(.caption.weight(.semibold))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
        .swipeActions(edge: .leading, allowsFullSwipe: true) {
            Button("Done") { markDone(item) }
                .tint(.green)
        }
        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
            Button("Delete", role: .destructive) { remove(item) }
            Button("Today") { assign(item, day: store.today) }
        }
        .contextMenu { rowMenu(item) }
        .listRowBackground(store.palette.widgetBg)
    }

    @ViewBuilder
    private func rowMenu(_ item: WorkItem) -> some View {
        Button("This week") { place(item, "week") }
        Button("Today") { assign(item, day: store.today) }
        Button("Later") { place(item, "later") }
        Button("No day") { place(item, "none") }
        ForEach(thisWeekDates, id: \.self) { day in
            Button(DayStamp.weekdayLong(day)) { assign(item, day: day) }
        }
        Button("Other day…") { picking = item }
        Button("Delete", role: .destructive) { remove(item) }
    }

    private func subtitle(_ item: WorkItem) -> String {
        let scheduled = String((item.scheduled_date ?? "").prefix(10))
        if !scheduled.isEmpty { return DayStamp.weekdayLong(scheduled) }
        if item.horizon == "week" { return "Sometime this week" }
        if item.horizon == "later" { return "Later" }
        return "No day"
    }

    private func addWeek() {
        let title = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else { return }
        draft = ""
        mutate { try PackActions.addThisWeek(title) }
    }

    private func addToday() {
        let title = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else { return }
        draft = ""
        mutate { try PackActions.addTodo(title, date: store.today) }
    }

    private func park() {
        let title = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else { return }
        draft = ""
        mutate { try PackActions.park(title) }
    }

    private func assign(_ item: WorkItem, day: String) {
        mutate { try PackActions.assignDay(id: item.id, date: day) }
    }

    private func place(_ item: WorkItem, _ bucket: String) {
        mutate { try PackActions.placeBucket(id: item.id, bucket: bucket) }
    }

    private func markDone(_ item: WorkItem) {
        mutate { try PackActions.toggle(id: item.id) }
    }

    private func remove(_ item: WorkItem) {
        mutate { try PackActions.deleteTodo(id: item.id) }
    }

    private func move(_ name: String, from: IndexSet, to: Int) {
        var rows = TodoGroups.rows(store.pack, today: store.today, group: name)
        rows.move(fromOffsets: from, toOffset: to)
        mutate { try PackActions.reorder(rows.map(\.id)) }
    }

    private func mutate(_ action: () throws -> Pack) {
        do {
            store.pack = try action()
            store.error = nil
            if reviewMode && review.isEmpty {
                reviewMode = false
                store.openReview = false
            }
        } catch {
            store.error = error.localizedDescription
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
