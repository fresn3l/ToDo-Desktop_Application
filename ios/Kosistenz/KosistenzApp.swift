import SwiftUI
import UniformTypeIdentifiers

@main
struct KosistenzApp: App {
    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}

struct RootView: View {
    @Environment(\.horizontalSizeClass) private var sizeClass
    @StateObject private var store = PackStore()

    var body: some View {
        Group {
            if sizeClass == .regular {
                NavigationSplitView {
                    List {
                        ForEach(AppTab.allCases) { tab in
                            Button {
                                store.tab = tab
                            } label: {
                                Label(tab.title, systemImage: tab.icon)
                            }
                            .foregroundStyle(store.tab == tab ? store.palette.accent : store.palette.ink)
                            .listRowBackground(store.tab == tab ? store.palette.accent.opacity(0.2) : store.palette.widgetBg)
                        }
                    }
                    .navigationTitle("Kosistenz")
                } detail: {
                    tabBody(store.tab)
                }
            } else {
                TabView(selection: $store.tab) {
                    TodayScreen().tag(AppTab.today).tabItem { Label(AppTab.today.title, systemImage: AppTab.today.icon) }
                    CalendarScreen().tag(AppTab.calendar).tabItem { Label(AppTab.calendar.title, systemImage: AppTab.calendar.icon) }
                    TodoScreen().tag(AppTab.todo).tabItem { Label(AppTab.todo.title, systemImage: AppTab.todo.icon) }
                }
            }
        }
        .environmentObject(store)
        .tint(store.palette.accent)
        .sheet(isPresented: $store.showSync) {
            SettingsScreen()
                .environmentObject(store)
        }
        .fileImporter(isPresented: $store.pickingFolder, allowedContentTypes: [.folder], allowsMultipleSelection: false) { result in
            if case .success(let urls) = result, let url = urls.first {
                store.chooseFolder(url)
            }
        }
        .onAppear {
            store.reload()
            EventAlerts.request()
            if store.access == .needsFolder {
                store.showSync = true
            }
        }
    }

    @ViewBuilder
    private func tabBody(_ tab: AppTab) -> some View {
        switch tab {
        case .today: TodayScreen()
        case .calendar: CalendarScreen()
        case .todo: TodoScreen()
        }
    }
}

enum AppTab: String, Hashable, CaseIterable, Identifiable {
    case today, calendar, todo

    var id: String { rawValue }

    var title: String {
        switch self {
        case .today: return "Today"
        case .calendar: return "Calendar"
        case .todo: return "To Do"
        }
    }

    var icon: String {
        switch self {
        case .today: return "sun.max"
        case .calendar: return "calendar"
        case .todo: return "checklist"
        }
    }
}

final class PackStore: ObservableObject {
    @Published var pack: Pack?
    @Published var access: SyncPack.Access = .needsFolder
    @Published var error: String?
    @Published var syncedAt: String?
    @Published var palette = KosistenzPalette.ocean
    @Published var tab: AppTab = .today
    @Published var pickingFolder = false
    @Published var showSync = false

    var today: String { DayStamp.today() }

    var statusLine: String {
        if access == .needsFolder {
            return "Choose iCloud Drive / Kosistenz — until then this iPhone only."
        }
        if let synced = syncedAt {
            return "Pack \(synced)"
        }
        return "Waiting for iCloud. Pull to refresh, or Sync now."
    }

    func reload() {
        do {
            let loaded = try SyncPack.load()
            pack = loaded.pack
            access = loaded.access
            syncedAt = loaded.syncedAt
            palette = KosistenzPalette.from(appearance: loaded.pack.appearance)
            error = nil
            WidgetBridge.write(WidgetSnapshot.from(pack: loaded.pack, access: loaded.access))
            EventAlerts.sync(pack: loaded.pack)
        } catch {
            self.error = error.localizedDescription
        }
    }

    func chooseFolder(_ url: URL) {
        do {
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            try FolderBookmark.save(url)
            reload()
            showSync = false
        } catch {
            self.error = error.localizedDescription
        }
    }
}
