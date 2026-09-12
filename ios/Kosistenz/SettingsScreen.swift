import SwiftUI
import UniformTypeIdentifiers

struct SettingsScreen: View {
    @EnvironmentObject private var store: PackStore
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section("Folder") {
                    Text(folderCopy)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .listRowBackground(store.palette.widgetBg)
                    Button("Choose iCloud Drive / Kosistenz") {
                        store.pickingFolder = true
                    }
                    .listRowBackground(store.palette.widgetBg)
                    Button("Sync now") { store.reload() }
                        .listRowBackground(store.palette.widgetBg)
                    if let synced = store.syncedAt {
                        Text("Last pack \(synced)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .listRowBackground(store.palette.widgetBg)
                    }
                    Text("Alerts fire 30, 15, and 5 minutes before a timed event. Checking one off cancels the rest.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .listRowBackground(store.palette.widgetBg)
                }
                Section("Cluny") {
                    Text("Ask Cluny stays on the Mac. The phone syncs the week through this pack. If the Mac is asleep, Cluny is off here on purpose — your to-dos still save.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .listRowBackground(store.palette.widgetBg)
                }
                if let error = store.error {
                    Section {
                        Text(error).foregroundStyle(.red)
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .navigationTitle("Sync")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
            .fileImporter(isPresented: $store.pickingFolder, allowedContentTypes: [.folder], allowsMultipleSelection: false) { result in
                if case .success(let urls) = result, let url = urls.first {
                    store.chooseFolder(url)
                }
            }
        }
    }

    private var folderCopy: String {
        switch store.access {
        case .iCloudDrive:
            return "Using the folder you picked. It should be iCloud Drive / Kosistenz — the same files the Mac writes."
        case .localOnly:
            return "On this iPhone only. Sign into iCloud Drive and choose the Kosistenz folder."
        case .needsFolder:
            return "Pick Files → iCloud Drive → Kosistenz. Until then, saves stay on this iPhone."
        }
    }
}
