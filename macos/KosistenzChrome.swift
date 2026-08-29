import Cocoa
import Foundation
import WebKit
#if canImport(WidgetKit)
import WidgetKit
#endif

extension AppDelegate {
    func showMainWindow() {
        if window == nil {
            createWindow()
            waitForServerThenLoad(port: uiPort)
            return
        }
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func setupStatusItem() {
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        if let button = item.button {
            if let image = NSImage(systemSymbolName: "checkmark.circle", accessibilityDescription: "Kosistenz") {
                image.isTemplate = true
                button.image = image
            } else {
                button.title = "K"
            }
            button.toolTip = "Kosistenz"
        }
        let menu = NSMenu()
        menu.delegate = self
        item.menu = menu
        statusItem = item
        rebuildStatusMenu(status: nil)
    }

    func menuNeedsUpdate(_ menu: NSMenu) {
        guard menu == statusItem?.menu else { return }
        rebuildStatusMenu(status: fetchStatus())
    }

    func rebuildStatusMenu(status: [String: Any]?) {
        guard let menu = statusItem?.menu else { return }
        menu.removeAllItems()

        let summary = (status?["summary"] as? String) ?? "Kosistenz"
        let summaryItem = NSMenuItem(title: summary, action: nil, keyEquivalent: "")
        summaryItem.isEnabled = false
        menu.addItem(summaryItem)
        menu.addItem(NSMenuItem.separator())

        menu.addItem(menuItem("Open Kosistenz", action: #selector(openKosistenz), key: ""))

        let activeTitle = status?["active_title"] as? String
        let firstOpen = status?["first_open_title"] as? String
        if let title = activeTitle, !title.isEmpty {
            menu.addItem(menuItem("Finish “\(clipped(title))”", action: #selector(finishActiveTodo), key: ""))
        } else if let title = firstOpen, !title.isEmpty {
            menu.addItem(menuItem("Start “\(clipped(title))”", action: #selector(startActiveTodo), key: ""))
        } else {
            let empty = NSMenuItem(title: "No open to do today", action: nil, keyEquivalent: "")
            empty.isEnabled = false
            menu.addItem(empty)
        }

        menu.addItem(NSMenuItem.separator())
        let logHeader = NSMenuItem(title: "Log session", action: nil, keyEquivalent: "")
        logHeader.isEnabled = false
        menu.addItem(logHeader)
        menu.addItem(menuItem("Push", action: #selector(logPush), key: ""))
        menu.addItem(menuItem("Pull", action: #selector(logPull), key: ""))
        menu.addItem(menuItem("Legs", action: #selector(logLegs), key: ""))
        menu.addItem(menuItem("Run", action: #selector(logRun), key: ""))

        menu.addItem(NSMenuItem.separator())
        menu.addItem(menuItem("New journal entry", action: #selector(openNewJournal), key: ""))
        menu.addItem(menuItem("Park in All Work…", action: #selector(promptParkInAllWork), key: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit Kosistenz", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
    }

    @objc func openKosistenz() {
        showMainWindow()
    }

    @objc func startActiveTodo() {
        _ = postJSON(path: "/api/todo/start", body: [:])
        reloadWidgets()
        refreshToolbarStatus()
        showMainWindow()
        runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'open-tab',tab:'today'}}));")
    }

    @objc func finishActiveTodo() {
        _ = postJSON(path: "/api/todo/finish", body: [:])
        reloadWidgets()
        refreshToolbarStatus()
        showMainWindow()
        runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'open-tab',tab:'today'}}));")
    }

    @objc func logPush() { logKind("push") }
    @objc func logPull() { logKind("pull") }
    @objc func logLegs() { logKind("legs") }
    @objc func logRun() { logKind("running") }

    func logKind(_ kind: String) {
        _ = postJSON(path: "/api/workout/log", body: ["kind": kind])
        reloadWidgets()
        refreshToolbarStatus()
        showMainWindow()
        runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'open-tab',tab:'today'}}));")
    }

    @objc func openNewJournal() {
        showMainWindow()
        runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'journal-new'}}));")
    }

    @objc func promptParkInAllWork() {
        let alert = NSAlert()
        alert.messageText = "Park in All Work"
        alert.informativeText = "Saved without a date. Assign it later from All Work."
        alert.alertStyle = .informational
        alert.addButton(withTitle: "Park")
        alert.addButton(withTitle: "Cancel")
        let field = NSTextField(frame: NSRect(x: 0, y: 0, width: 280, height: 24))
        field.placeholderString = "Title"
        alert.accessoryView = field
        alert.window.initialFirstResponder = field
        showMainWindow()
        let response = alert.runModal()
        guard response == .alertFirstButtonReturn else { return }
        let title = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else { return }
        parkTitle(title)
    }

    func parkTitle(_ title: String) {
        _ = postJSON(path: "/api/work/park", body: ["title": title])
        reloadWidgets()
        showMainWindow()
        runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'open-tab',tab:'allwork'}}));")
    }

    func handleKosistenzURL(_ url: URL) {
        showMainWindow()
        let host = url.host?.lowercased() ?? ""
        let path = url.path.lowercased()
        let combined = (host + path).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let query = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems ?? []
        let title = query.first(where: { $0.name == "title" })?.value
            ?? query.first(where: { $0.name == "text" })?.value
            ?? ""

        if combined.hasPrefix("journal") {
            runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'journal-new'}}));")
            return
        }
        if combined.hasPrefix("work/park") || combined.hasPrefix("park") || combined == "work" {
            if !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                parkTitle(title)
            } else {
                runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'open-tab',tab:'allwork'}}));")
            }
            return
        }
        if combined.hasPrefix("todo") || combined.hasPrefix("work/todo") {
            runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'open-tab',tab:'todo'}}));")
            return
        }
        if combined.isEmpty || combined == "today" || combined.hasPrefix("today") {
            runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'open-tab',tab:'today'}}));")
            return
        }
        if combined.hasPrefix("workout") {
            runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'open-tab',tab:'workout'}}));")
            return
        }
        log("Unhandled kosistenz URL \(url.absoluteString)")
    }

    @objc func newJournalEntry(_ pboard: NSPasteboard, userData: String, error: AutoreleasingUnsafeMutablePointer<NSString?>) {
        openNewJournal()
        if let text = pboard.string(forType: .string), !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            let escaped = jsonString(text)
            runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'journal-new',text:\(escaped)}}));")
        }
    }

    @objc func parkInAllWork(_ pboard: NSPasteboard, userData: String, error: AutoreleasingUnsafeMutablePointer<NSString?>) {
        let text = pboard.string(forType: .string)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if text.isEmpty {
            promptParkInAllWork()
            return
        }
        parkTitle(text)
    }

    func reloadWidgets() {
        #if canImport(WidgetKit)
        if #available(macOS 11.0, *) {
            WidgetCenter.shared.reloadAllTimelines()
        }
        #endif
    }

    func fetchStatus() -> [String: Any]? {
        getJSON(path: "/api/status")
    }

    func getJSON(path: String) -> [String: Any]? {
        for port in apiPort...UInt16(min(Int(apiPort) + 9, 18750)) {
            guard let url = URL(string: "http://127.0.0.1:\(port)\(path)") else { continue }
            var request = URLRequest(url: url, timeoutInterval: 1.5)
            request.httpMethod = "GET"
            if let data = syncRequest(request),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                apiPort = port
                return json
            }
        }
        return nil
    }

    func postJSON(path: String, body: [String: Any]) -> [String: Any]? {
        let payload = (try? JSONSerialization.data(withJSONObject: body, options: [])) ?? Data("{}".utf8)
        for port in apiPort...UInt16(min(Int(apiPort) + 9, 18750)) {
            guard let url = URL(string: "http://127.0.0.1:\(port)\(path)") else { continue }
            var request = URLRequest(url: url, timeoutInterval: 2.0)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = payload
            if let data = syncRequest(request),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                apiPort = port
                return json
            }
        }
        return nil
    }

    func syncRequest(_ request: URLRequest) -> Data? {
        var result: Data?
        let sem = DispatchSemaphore(value: 0)
        URLSession.shared.dataTask(with: request) { data, response, _ in
            if let http = response as? HTTPURLResponse, (200..<500).contains(http.statusCode) {
                result = data
            }
            sem.signal()
        }.resume()
        _ = sem.wait(timeout: .now() + 2.2)
        return result
    }

    func runInWebView(_ javascript: String, retries: Int = 10) {
        showMainWindow()
        guard let webView = webView else { return }
        if let current = webView.url, !isUiURL(current) {
            return
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) {
            if let current = webView.url, !self.isUiURL(current) {
                return
            }
            webView.evaluateJavaScript(javascript) { _, error in
                if error != nil && retries > 0 {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
                        self.runInWebView(javascript, retries: retries - 1)
                    }
                }
            }
        }
    }

    func isUiURL(_ url: URL) -> Bool {
        let scheme = url.scheme?.lowercased() ?? ""
        let host = url.host?.lowercased() ?? ""
        guard scheme == "http" || scheme == "https" else { return false }
        guard host == "127.0.0.1" || host == "localhost" else { return false }
        let port = url.port ?? (scheme == "https" ? 443 : 80)
        return port == Int(uiPort)
    }

    func isTrustedScriptOrigin(_ origin: WKSecurityOrigin) -> Bool {
        let host = origin.host.lowercased()
        guard host == "127.0.0.1" || host == "localhost" else { return false }
        return origin.port == Int(uiPort)
    }

    func applyNativeAppearance(dark: Bool) {
        let name: NSAppearance.Name = dark ? .darkAqua : .aqua
        window?.appearance = NSAppearance(named: name)
        effectView?.appearance = NSAppearance(named: name)
        effectView?.material = .sidebar
    }

    func setupToolbar(on window: NSWindow) {
        let toolbar = NSToolbar(identifier: "Kosistenz.Main")
        toolbar.delegate = self
        toolbar.allowsUserCustomization = false
        toolbar.displayMode = .iconAndLabel
        window.toolbar = toolbar
        refreshToolbarStatus()
    }

    func refreshToolbarStatus() {
        let status = fetchStatus()
        let workoutDone = status?["workout_logged"] as? Bool ?? false
        let openCount = intValue(status, "open_count")
        let journalToday = status?["journal_today"] as? Bool ?? false
        toolbarWorkout?.title = workoutDone ? "Workout ✓" : "Workout"
        toolbarTodo?.title = openCount > 0 ? "To Do (\(openCount))" : "To Do"
        toolbarJournal?.title = journalToday ? "Journal ✓" : "Journal"
    }

    func toolbarDefaultItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] {
        [
            NSToolbarItem.Identifier("todayWorkout"),
            NSToolbarItem.Identifier("todayTodo"),
            NSToolbarItem.Identifier("todayJournal"),
            .flexibleSpace,
        ]
    }

    func toolbarAllowedItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] {
        toolbarDefaultItemIdentifiers(toolbar)
    }

    func toolbar(
        _ toolbar: NSToolbar,
        itemForItemIdentifier itemIdentifier: NSToolbarItem.Identifier,
        willBeInsertedIntoToolbar flag: Bool
    ) -> NSToolbarItem? {
        let item = NSToolbarItem(itemIdentifier: itemIdentifier)
        let button: NSButton
        switch itemIdentifier.rawValue {
        case "todayWorkout":
            button = toolbarButton("Workout", action: #selector(toolbarOpenToday))
            toolbarWorkout = button
        case "todayTodo":
            button = toolbarButton("To Do", action: #selector(toolbarOpenToday))
            toolbarTodo = button
        case "todayJournal":
            button = toolbarButton("Journal", action: #selector(openNewJournal))
            toolbarJournal = button
        default:
            return nil
        }
        item.view = button
        item.label = button.title
        item.paletteLabel = button.title
        return item
    }

    func toolbarButton(_ title: String, action: Selector) -> NSButton {
        let button = NSButton(title: title, target: self, action: action)
        button.bezelStyle = .texturedRounded
        if #available(macOS 11.0, *) {
            button.bezelStyle = .toolbar
        }
        button.setButtonType(.momentaryPushIn)
        return button
    }

    @objc func toolbarOpenToday() {
        showMainWindow()
        runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:command',{detail:{action:'open-tab',tab:'today'}}));")
    }
}

private func intValue(_ json: [String: Any]?, _ key: String) -> Int {
    guard let json = json else { return 0 }
    if let n = json[key] as? Int { return n }
    if let n = json[key] as? NSNumber { return n.intValue }
    return 0
}

private func menuItem(_ title: String, action: Selector, key: String) -> NSMenuItem {
    NSMenuItem(title: title, action: action, keyEquivalent: key)
}

private func clipped(_ title: String, limit: Int = 32) -> String {
    if title.count <= limit { return title }
    let end = title.index(title.startIndex, offsetBy: limit)
    return String(title[..<end]) + "…"
}

private func jsonString(_ text: String) -> String {
    let data = try? JSONSerialization.data(withJSONObject: text, options: [.fragmentsAllowed])
    return String(data: data ?? Data("\"\"".utf8), encoding: .utf8) ?? "\"\""
}
