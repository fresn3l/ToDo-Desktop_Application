import SwiftUI

struct JournalScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var draft = ""
    @FocusState private var writing: Bool

    private var entries: [JournalEntry] {
        (store.pack?.journal ?? []).sorted { lhs, rhs in
            (lhs.updated_at ?? lhs.created_at ?? "") > (rhs.updated_at ?? rhs.created_at ?? "")
        }
    }

    private var todayEntries: [JournalEntry] {
        entries.filter { entry in
            let stamp = entry.date ?? entry.created_at ?? ""
            return stamp.hasPrefix(store.today)
        }
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
                Section("Write") {
                    TextEditor(text: $draft)
                        .frame(minHeight: 140)
                        .focused($writing)
                        .listRowBackground(store.palette.widgetBg)
                    Button("Save") { save() }
                        .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                        .listRowBackground(store.palette.widgetBg)
                }
                Section(todayEntries.isEmpty ? "Today" : "Today (\(todayEntries.count))") {
                    if todayEntries.isEmpty {
                        Text("Nothing written today.")
                            .foregroundStyle(.secondary)
                            .listRowBackground(store.palette.widgetBg)
                    }
                    ForEach(todayEntries) { entry in
                        Text(entry.content)
                            .listRowBackground(store.palette.widgetBg)
                    }
                }
                if let error = store.error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .navigationTitle("Journal")
            .toolbar { SyncToolbarButton() }
            .refreshable { store.reload() }
        }
    }

    private func save() {
        let text = draft
        do {
            store.pack = try PackActions.addJournal(text)
            draft = ""
            writing = false
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }
}
