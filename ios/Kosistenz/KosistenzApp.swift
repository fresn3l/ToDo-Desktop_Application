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
                    WeekScreen().tag(AppTab.week).tabItem { Label(AppTab.week.title, systemImage: AppTab.week.icon) }
                    JournalScreen().tag(AppTab.journal).tabItem { Label(AppTab.journal.title, systemImage: AppTab.journal.icon) }
                    InboxScreen().tag(AppTab.inbox).tabItem { Label(AppTab.inbox.title, systemImage: AppTab.inbox.icon) }
                    SettingsScreen().tag(AppTab.sync).tabItem { Label(AppTab.sync.title, systemImage: AppTab.sync.icon) }
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

enum AppTab: String, Hashable, CaseIterable, Identifiable {
    case today, week, journal, inbox, sync

    var id: String { rawValue }

    var title: String {
        switch self {
        case .today: return "Today"
        case .week: return "Week"
        case .journal: return "Journal"
        case .inbox: return "Inbox"
        case .sync: return "Sync"
        }
    }

    var icon: String {
        switch self {
        case .today: return "sun.max"
        case .week: return "calendar"
        case .journal: return "book"
        case .inbox: return "tray"
        case .sync: return "icloud"
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
