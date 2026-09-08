import SwiftUI

struct JournalScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var draft = ""
    @State private var editingId: String?

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 12) {
                if store.access == .needsFolder {
                    Text("Choose iCloud Drive / Kosistenz in Sync so this page is the same journal as the Mac.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal)
                }
                TextEditor(text: $draft)
                    .padding(8)
                    .scrollContentBackground(.hidden)
                    .background(store.palette.widgetBg)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding(.horizontal)
                HStack {
                    Button(editingId == nil ? "Save" : "Save edits") { save() }
                        .buttonStyle(.borderedProminent)
                        .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    if editingId != nil {
                        Text("Editing today’s entry")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .padding(.horizontal)
                List {
                    ForEach(recent) { entry in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(String((entry.date ?? entry.created_at ?? "").prefix(10)))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text(entry.content)
                                .lineLimit(4)
                        }
                        .listRowBackground(store.palette.widgetBg)
                    }
                }
                .scrollContentBackground(.hidden)
            }
            .background(store.palette.pageBg)
            .navigationTitle("Journal")
            .toolbar {
                Button("Sync") { store.reload() }
            }
            .onAppear { loadToday() }
        }
    }

    private var recent: [JournalEntry] {
        Array((store.pack?.journal ?? []).prefix(20))
    }

    private func loadToday() {
        if let existing = (store.pack?.journal ?? []).first(where: { ($0.date ?? $0.created_at ?? "").hasPrefix(store.today) }) {
            draft = existing.content
            editingId = existing.id
        }
    }

    private func save() {
        guard var pack = store.pack else { return }
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        let now = DayStamp.isoNow()
        if let editingId, let index = pack.journal.firstIndex(where: { $0.id == editingId }) {
            pack.journal[index].content = text
            pack.journal[index].updated_at = now
        } else {
            let stamp = now.replacingOccurrences(of: ":", with: "-")
            let entry = JournalEntry(
                id: "entry_\(stamp)_ios",
                content: text,
                date: now,
                duration_seconds: 0,
                continued: false,
                created_at: now,
                updated_at: now,
                tags: [],
                kind: "journal"
            )
            pack.journal.insert(entry, at: 0)
            editingId = entry.id
        }
        do {
            try SyncPack.saveJournal(pack.journal)
            store.pack = pack
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }
}
