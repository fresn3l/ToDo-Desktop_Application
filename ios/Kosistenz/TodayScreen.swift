import SwiftUI
import UIKit

struct TodayScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var draft = ""
    @State private var burstingId: String?

    private var rows: [TodayList.Entry] {
        guard let pack = store.pack else { return [] }
        return TodayList.entries(pack: pack, today: store.today)
    }

    var body: some View {
        NavigationStack {
            List {
                if store.access == .needsFolder {
                    Section {
                        Text(store.statusLine)
                            .foregroundStyle(.secondary)
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
                if rows.isEmpty {
                    Section {
                        Text("Nothing dated for today. Add a task here, or an event on Calendar.")
                            .foregroundStyle(.secondary)
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
                ForEach(rows) { row in
                    TodayCheckRow(
                        entry: row,
                        palette: store.palette,
                        bursting: burstingId == row.id
                    ) {
                        complete(row)
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
                Section {
                    HStack {
                        TextField("Add for today", text: $draft)
                        Button("Add") { addTodo() }
                            .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                }
                .listRowBackground(store.palette.widgetBg)
                if let error = store.error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .navigationTitle(heading)
            .toolbarBackground(store.palette.sidebar, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar { SyncToolbarButton() }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .refreshable { store.reload() }
            .onAppear { store.reload() }
        }
    }

    private var heading: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEEE"
        return formatter.string(from: Date())
    }

    private func complete(_ entry: TodayList.Entry) {
        do {
            if !entry.done {
                burstingId = entry.id
                UINotificationFeedbackGenerator().notificationOccurred(.success)
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                    if burstingId == entry.id { burstingId = nil }
                }
            }
            store.pack = try PackActions.complete(entry)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func addTodo() {
        let title = draft
        draft = ""
        do {
            store.pack = try PackActions.addTodo(title, date: store.today)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }
}

struct TodayCheckRow: View {
    var entry: TodayList.Entry
    var palette: KosistenzPalette
    var bursting: Bool
    var onToggle: () -> Void

    var body: some View {
        Button(action: onToggle) {
            HStack(spacing: 14) {
                ZStack {
                    Circle()
                        .stroke(entry.done ? palette.done : palette.openNext, lineWidth: 2)
                        .frame(width: 28, height: 28)
                    if entry.done {
                        Image(systemName: "checkmark")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(palette.done)
                            .scaleEffect(bursting ? 1.25 : 1)
                    }
                    if bursting {
                        Circle()
                            .stroke(palette.done.opacity(0.45), lineWidth: 3)
                            .frame(width: bursting ? 46 : 28, height: bursting ? 46 : 28)
                    }
                }
                .frame(width: 36, height: 36)
                VStack(alignment: .leading, spacing: 2) {
                    Text(entry.title)
                        .font(.body.weight(.semibold))
                        .strikethrough(entry.done, color: palette.done)
                        .foregroundStyle(entry.done ? palette.done : palette.titles)
                    Text(entry.timeLabel)
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }
            .padding(.vertical, 6)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .animation(.spring(response: 0.38, dampingFraction: 0.62), value: entry.done)
        .animation(.spring(response: 0.42, dampingFraction: 0.55), value: bursting)
        .accessibilityLabel("\(entry.title), \(entry.timeLabel)")
        .accessibilityAddTraits(entry.done ? [.isSelected] : [])
    }
}

struct SyncToolbarButton: View {
    @EnvironmentObject private var store: PackStore

    var body: some View {
        Button {
            store.showSync = true
        } label: {
            Image(systemName: store.access == .iCloudDrive ? "icloud" : "icloud.slash")
        }
        .accessibilityLabel("Sync")
    }
}
