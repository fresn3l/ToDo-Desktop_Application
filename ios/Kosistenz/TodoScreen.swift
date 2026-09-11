import SwiftUI

struct TodoScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var draft = ""

    private var later: [WorkItem] {
        (store.pack?.work.items ?? []).filter { item in
            let date = item.scheduled_date ?? ""
            return item.status != "done" && !date.isEmpty && date != store.today
        }
        .sorted { ($0.scheduled_date ?? "") < ($1.scheduled_date ?? "") }
    }

    private var inbox: [WorkItem] {
        (store.pack?.work.items ?? []).filter { item in
            (item.scheduled_date ?? "").isEmpty && item.status != "done"
        }
    }

    var body: some View {
        NavigationStack {
            List {
                Section("Park in All Work") {
                    HStack {
                        TextField("No day yet", text: $draft)
                        Button("Park") { park() }
                            .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
                Section("Later") {
                    if later.isEmpty {
                        Text("Nothing dated after today.")
                            .foregroundStyle(.secondary)
                            .listRowBackground(store.palette.widgetBg)
                    }
                    ForEach(later) { item in
                        todoRow(item, subtitle: item.scheduled_date)
                    }
                }
                Section("All Work") {
                    if inbox.isEmpty {
                        Text("Nothing parked.")
                            .foregroundStyle(.secondary)
                            .listRowBackground(store.palette.widgetBg)
                    }
                    ForEach(inbox) { item in
                        todoRow(item, subtitle: nil)
                    }
                }
                if let error = store.error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .navigationTitle("To Do")
            .toolbar { SyncToolbarButton() }
            .refreshable { store.reload() }
        }
    }

    private func todoRow(_ item: WorkItem, subtitle: String?) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(item.title)
                if let subtitle, !subtitle.isEmpty {
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
}
