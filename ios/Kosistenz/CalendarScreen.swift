import SwiftUI

struct CalendarScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var showAdd = false
    @State private var view: CalView = .week

    private enum CalView: String, CaseIterable, Identifiable {
        case week = "Week"
        case today = "Today"
        var id: String { rawValue }
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Picker("View", selection: $view) {
                        ForEach(CalView.allCases) { item in
                            Text(item.rawValue).tag(item)
                        }
                    }
                    .pickerStyle(.segmented)
                    .listRowBackground(store.palette.widgetBg)
                }
                Section {
                    if store.pack?.calendar.days.isEmpty ?? true {
                        Text("No week clock in the pack yet. Add an event here, or open Kosistenz on the Mac and Push to iCloud.")
                            .foregroundStyle(.secondary)
                    } else if view == .week, let calendar = store.pack?.calendar {
                        WeekClockView(file: calendar, palette: store.palette)
                            .frame(minHeight: 430)
                    } else if let day = todayDay {
                        DayClockView(
                            day: day,
                            dayStart: store.pack?.calendar.day_start,
                            dayEnd: store.pack?.calendar.day_end,
                            palette: store.palette,
                            height: 420
                        )
                        .frame(minHeight: 440)
                    } else {
                        Text("Nothing on today’s clock. Add an event, or Fill week on the Mac.")
                            .foregroundStyle(.secondary)
                    }
                }
                .listRowBackground(store.palette.widgetBg)
                .listRowInsets(EdgeInsets(top: 10, leading: 16, bottom: 10, trailing: 16))
            }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .navigationTitle("Calendar")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button("Add") { showAdd = true }
                }
                ToolbarItem(placement: .navigationBarLeading) {
                    SyncToolbarButton()
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

    private var todayDay: CalendarDay? {
        store.pack?.calendar.days.first(where: { $0.date == store.today })
    }
}
