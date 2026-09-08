import SwiftUI

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
                    List(selection: $store.tab) {
                        Label("Today", systemImage: "sun.max").tag(AppTab.today)
                        Label("Week", systemImage: "calendar").tag(AppTab.week)
                        Label("Journal", systemImage: "book").tag(AppTab.journal)
                        Label("Inbox", systemImage: "tray").tag(AppTab.inbox)
                        Label("Sync", systemImage: "icloud").tag(AppTab.sync)
                    }
                    .navigationTitle("Kosistenz")
                } detail: {
                    tabBody(store.tab)
                }
            } else {
                TabView(selection: $store.tab) {
                    TodayScreen().tag(AppTab.today).tabItem { Label("Today", systemImage: "sun.max") }
                    WeekScreen().tag(AppTab.week).tabItem { Label("Week", systemImage: "calendar") }
                    JournalScreen().tag(AppTab.journal).tabItem { Label("Journal", systemImage: "book") }
                    InboxScreen().tag(AppTab.inbox).tabItem { Label("Inbox", systemImage: "tray") }
                    SettingsScreen().tag(AppTab.sync).tabItem { Label("Sync", systemImage: "icloud") }
                }
            }
        }
        .environmentObject(store)
        .tint(store.palette.accent)
        .onAppear { store.reload() }
    }

    @ViewBuilder
    private func tabBody(_ tab: AppTab) -> some View {
        switch tab {
        case .today: TodayScreen()
        case .week: WeekScreen()
        case .journal: JournalScreen()
        case .inbox: InboxScreen()
        case .sync: SettingsScreen()
        }
    }
}

enum AppTab: Hashable {
    case today, week, journal, inbox, sync
}

final class PackStore: ObservableObject {
    @Published var pack: Pack?
    @Published var access: SyncPack.Access = .needsFolder
    @Published var error: String?
    @Published var syncedAt: String?
    @Published var palette = KosistenzPalette.ocean
    @Published var tab: AppTab = .today
    @Published var pickingFolder = false

    var today: String { DayStamp.today() }

    func reload() {
        do {
            let loaded = try SyncPack.load()
            pack = loaded.pack
            access = loaded.access
            syncedAt = loaded.syncedAt
            palette = KosistenzPalette.from(appearance: loaded.pack.appearance)
            error = nil
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
        } catch {
            self.error = error.localizedDescription
        }
    }
}
