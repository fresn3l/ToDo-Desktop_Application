import SwiftUI

struct WeekScreen: View {
    @EnvironmentObject private var store: PackStore

    var body: some View {
        NavigationStack {
            List {
                if store.pack?.calendar.days.isEmpty ?? true {
                    Section {
                        Text("No week clock in the pack yet. Open Kosistenz on the Mac and Push to iCloud.")
                            .foregroundStyle(.secondary)
                    }
                }
                ForEach(store.pack?.calendar.days ?? [], id: \.dateValue) { day in
                    Section(day.date ?? "") {
                        let items = (day.events) + (day.blocks)
                        if items.isEmpty {
                            Text("Open")
                                .foregroundStyle(.secondary)
                        } else {
                            ForEach(items) { item in
                                HStack {
                                    Text(DayStamp.clock(item.start_at)).monospacedDigit()
                                    Text(item.title ?? "")
                                    Spacer()
                                    Text(label(for: item))
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
                if !(store.pack?.calendar.unplaced.isEmpty ?? true) {
                    Section("Unplaced") {
                        ForEach(store.pack?.calendar.unplaced ?? []) { item in
                            Text(item.title ?? "")
                                .listRowBackground(store.palette.widgetBg)
                        }
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .navigationTitle("This week")
            .refreshable { store.reload() }
        }
    }

    private func label(for item: CalendarItem) -> String {
        if item.kind == "hard" { return "Class" }
        if item.kind == "workout" { return "Gym" }
        return item.status ?? "Work"
    }
}

private extension CalendarDay {
    var dateValue: String { date ?? UUID().uuidString }
}
