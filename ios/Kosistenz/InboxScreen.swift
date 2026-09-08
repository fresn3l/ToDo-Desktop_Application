import SwiftUI

struct InboxScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var draft = ""

    private var inbox: [WorkItem] {
        (store.pack?.work.items ?? []).filter { ($0.scheduled_date ?? "").isEmpty && $0.status != "done" }
    }

    private var goals: [GoalRow] {
        (store.pack?.work.goals ?? []).filter { ($0.archived ?? 0) == 0 }
    }

    var body: some View {
        NavigationStack {
            List {
                Section("Park a thought") {
                    HStack {
                        TextField("All Work — no day yet", text: $draft)
                        Button("Park") { park() }
                            .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
                Section("Unscheduled") {
                    if inbox.isEmpty {
                        Text("Nothing unscheduled.")
                            .foregroundStyle(.secondary)
                            .listRowBackground(store.palette.widgetBg)
                    }
                    ForEach(inbox) { item in
                        Text(item.title)
                            .listRowBackground(store.palette.widgetBg)
                    }
                }
                Section("Goals") {
                    if goals.isEmpty {
                        Text("No goals in the pack.")
                            .foregroundStyle(.secondary)
                            .listRowBackground(store.palette.widgetBg)
                    }
                    ForEach(goals) { goal in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(goal.title ?? "Goal")
                            Text(goal.horizon ?? "")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .listRowBackground(store.palette.widgetBg)
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .navigationTitle("Inbox")
            .refreshable { store.reload() }
        }
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
}
