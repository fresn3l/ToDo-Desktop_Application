import SwiftUI

struct NotesScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var currentId = ""
    @State private var title = ""
    @State private var bodyText = ""
    @State private var focusId = ""
    @FocusState private var writing: Bool

    private var notes: [NoteEntry] {
        (store.pack?.notes ?? []).sorted { lhs, rhs in
            (lhs.updated_at ?? lhs.created_at ?? "") > (rhs.updated_at ?? rhs.created_at ?? "")
        }
    }

    private var storage: [NoteEntry] {
        notes.filter { ($0.focus_id ?? "").isEmpty }
    }

    private var pinned: [NoteEntry] {
        notes.filter { !($0.focus_id ?? "").isEmpty }
    }

    private var spans: [FocusSpan] {
        FocusSpan.from(pack: store.pack, extraId: focusId)
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
                Section("Write") {
                    TextField("Title", text: $title)
                        .listRowBackground(store.palette.widgetBg)
                    TextEditor(text: $bodyText)
                        .frame(minHeight: 140)
                        .focused($writing)
                        .listRowBackground(store.palette.widgetBg)
                    Picker("Focus span", selection: $focusId) {
                        Text("In storage").tag("")
                        ForEach(spans) { span in
                            Text(span.label).tag(span.id)
                        }
                    }
                    .listRowBackground(store.palette.widgetBg)
                    Button("Save") { save() }
                        .disabled(title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                            && bodyText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                        .listRowBackground(store.palette.widgetBg)
                    if !currentId.isEmpty {
                        Button("Back to storage") { detach() }
                            .listRowBackground(store.palette.widgetBg)
                    }
                }
                noteSection(storage.isEmpty ? "Storage" : "Storage (\(storage.count))", storage, empty: "Nothing in storage.")
                noteSection(pinned.isEmpty ? "On a focus span" : "On a focus span (\(pinned.count))", pinned, empty: "No notes on a span.")
                if let error = store.error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .navigationTitle("Notes")
            .toolbar {
                QuietSyncButton()
                Button("New") { resetEditor() }
            }
            .refreshable { store.reload() }
        }
    }

    @ViewBuilder
    private func noteSection(_ heading: String, _ rows: [NoteEntry], empty: String) -> some View {
        Section(heading) {
            if rows.isEmpty {
                Text(empty)
                    .foregroundStyle(.secondary)
                    .listRowBackground(store.palette.widgetBg)
            }
            ForEach(rows) { note in
                Button {
                    load(note)
                } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(note.title.isEmpty ? "Note" : note.title)
                            .foregroundStyle(store.palette.ink)
                        Text(subtitle(note))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .listRowBackground(store.palette.widgetBg)
            }
            .onDelete { offsets in
                delete(rows, at: offsets)
            }
        }
    }

    private func subtitle(_ note: NoteEntry) -> String {
        if let focus = note.focus_id, !focus.isEmpty {
            return spans.first(where: { $0.id == focus })?.label ?? "On the clock"
        }
        return "In storage"
    }

    private func load(_ note: NoteEntry) {
        currentId = note.id
        title = note.title
        bodyText = note.body
        focusId = note.focus_id ?? ""
        writing = true
    }

    private func resetEditor() {
        currentId = ""
        title = ""
        bodyText = ""
        focusId = ""
        writing = true
    }

    private func save() {
        do {
            if currentId.isEmpty {
                store.pack = try PackActions.addNote(title: title, body: bodyText, focusId: focusId)
                if let newest = store.pack?.notes.first {
                    currentId = newest.id
                }
            } else {
                store.pack = try PackActions.updateNote(
                    id: currentId,
                    title: title,
                    body: bodyText,
                    focusId: focusId
                )
            }
            writing = false
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func detach() {
        guard !currentId.isEmpty else {
            focusId = ""
            return
        }
        do {
            store.pack = try PackActions.detachNote(id: currentId)
            focusId = ""
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func delete(_ rows: [NoteEntry], at offsets: IndexSet) {
        for index in offsets {
            let id = rows[index].id
            do {
                store.pack = try PackActions.deleteNote(id: id)
                if currentId == id { resetEditor() }
                store.error = nil
            } catch {
                store.error = error.localizedDescription
            }
        }
    }
}

struct FocusSpan: Identifiable, Hashable {
    var id: String
    var title: String
    var weekday: String

    var label: String {
        weekday.isEmpty ? title : "\(weekday) · \(title)"
    }

    static func from(pack: Pack?, extraId: String = "") -> [FocusSpan] {
        var seen = Set<String>()
        var rows: [FocusSpan] = []
        for day in pack?.calendar.days ?? [] {
            for item in day.blocks where (item.kind ?? "").lowercased() == "focus" {
                let id = item.itemId ?? item.id
                guard !id.isEmpty, seen.insert(id).inserted else { continue }
                rows.append(FocusSpan(
                    id: id,
                    title: item.title?.isEmpty == false ? (item.title ?? "Focus") : "Focus",
                    weekday: day.weekday ?? ""
                ))
            }
        }
        if !extraId.isEmpty, !seen.contains(extraId) {
            rows.append(FocusSpan(id: extraId, title: "On the clock", weekday: ""))
        }
        return rows
    }
}
