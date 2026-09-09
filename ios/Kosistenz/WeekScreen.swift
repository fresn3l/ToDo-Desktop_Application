import SwiftUI

struct WeekScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var showAdd = false

    var body: some View {
        NavigationStack {
            List {
                Section {
                    if store.pack?.calendar.days.isEmpty ?? true {
                        Text("No week clock in the pack yet. Add an event here, or open Kosistenz on the Mac and Push to iCloud.")
                            .foregroundStyle(.secondary)
                    } else if let calendar = store.pack?.calendar {
                        WeekClockView(file: calendar, palette: store.palette)
                            .frame(minHeight: 430)
                    }
                }
                .listRowBackground(store.palette.widgetBg)

                if !(store.pack?.calendar.unplaced.isEmpty ?? true) {
                    Section("Unplaced") {
                        Text("Not on the clock. Inbox holds the thought until you place it on the Mac.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .listRowBackground(store.palette.widgetBg)
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
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button("Add") { showAdd = true }
                }
            }
            .sheet(isPresented: $showAdd) {
                AddEventSheet(
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
            .refreshable { store.reload() }
        }
    }
}
