import Cocoa
import Darwin
import Foundation
import WebKit
#if canImport(WidgetKit)
import WidgetKit
#endif

/// WKWebView treats a copied http(s)/webcal link as “go to this URL”.
/// The focused HTML field’s first responder is WebKit’s private
/// WKContentView, not this subclass, so paste:/Cmd+V never reached us
/// and the URL vanished. The window intercepts Cmd+V and we insert.
final class KosistenzWebView: WKWebView {
    override var acceptsFirstResponder: Bool { true }

    @objc func paste(_ sender: Any?) {
        pasteFromClipboard()
    }

    override func performKeyEquivalent(with event: NSEvent) -> Bool {
        if KosistenzMainWindow.isPlainCommand(event, letter: "v") {
            pasteFromClipboard()
            return true
        }
        return super.performKeyEquivalent(with: event)
    }

    static func pasteboardURLText() -> String? {
        extractURL(fromPasteboard: NSPasteboard.general)
    }

    static func extractURL(fromPasteboard pb: NSPasteboard) -> String? {
        if let urls = pb.readObjects(forClasses: [NSURL.self], options: nil) as? [URL],
           let url = urls.first {
            let scheme = url.scheme?.lowercased() ?? ""
            if ["http", "https", "webcal"].contains(scheme) {
                return url.absoluteString
            }
        }
        if let urlString = pb.string(forType: .URL), let url = extractURL(from: urlString) {
            return url
        }
        if let html = htmlString(from: pb), let url = extractURL(from: html) {
            return url
        }
        let stringTypes: [NSPasteboard.PasteboardType] = [
            .string,
            NSPasteboard.PasteboardType("public.utf8-plain-text"),
            NSPasteboard.PasteboardType("public.utf16-plain-text"),
        ]
        for type in stringTypes {
            if let raw = pb.string(forType: type), let url = extractURL(from: raw) {
                return url
            }
        }
        return nil
    }

    static func htmlString(from pb: NSPasteboard) -> String? {
        let htmlTypes: [NSPasteboard.PasteboardType] = [
            .html,
            NSPasteboard.PasteboardType("public.html"),
        ]
        for htmlType in htmlTypes {
            if let html = pb.string(forType: htmlType), !html.isEmpty {
                return html
            }
            if let data = pb.data(forType: htmlType) {
                if let html = String(data: data, encoding: .utf8), !html.isEmpty {
                    return html
                }
                if let html = String(data: data, encoding: .utf16), !html.isEmpty {
                    return html
                }
            }
        }
        return nil
    }

    static func extractURL(from raw: String) -> String? {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, trimmed.count <= 8000 else { return nil }
        let first = trimmed.split(whereSeparator: \.isNewline)
            .map { String($0).trimmingCharacters(in: .whitespaces) }
            .first(where: { !$0.isEmpty && !$0.hasPrefix("#") }) ?? trimmed
        let cleaned = first.trimmingCharacters(in: CharacterSet(charactersIn: "<>\"' "))
        if let match = cleaned.range(of: #"(?:https?|webcal)://[^\s<>"']+"#, options: .regularExpression) {
            var url = String(cleaned[match])
            while let last = url.last, ".,;)]}>\"'".contains(last) {
                url.removeLast()
            }
            return url.isEmpty ? nil : url
        }
        if let match = raw.range(of: #"href=["']((?:https?|webcal)://[^"']+)"#, options: [.regularExpression, .caseInsensitive]) {
            let href = String(raw[match])
            if let inner = href.range(of: #"(?:https?|webcal)://[^"']+"#, options: .regularExpression) {
                var url = String(href[inner])
                while let last = url.last, ".,;)]}>\"'".contains(last) {
                    url.removeLast()
                }
                return url.isEmpty ? nil : url
            }
        }
        return nil
    }

    static func pasteboardIcsText() -> String? {
        let pb = NSPasteboard.general
        guard let raw = pb.string(forType: .string) else { return nil }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.uppercased().contains("BEGIN:VCALENDAR") else { return nil }
        guard trimmed.utf8.count <= 2_097_152 else { return nil }
        return trimmed
    }

    static func pasteboardPlainText() -> String? {
        let pb = NSPasteboard.general
        guard let raw = pb.string(forType: .string) else { return nil }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    func insertIcsIntoPage(_ text: String) {
        let payload = jsStringLiteral(text)
        let js = "window.kosistenzImportIcsText && window.kosistenzImportIcsText(\(payload))"
        evaluateJavaScript(js) { _, error in
            if let error {
                log("ICS JS insert failed: \(error.localizedDescription)")
            }
        }
    }

    func pasteFromClipboard() {
        pasteCalendarPayload()
    }

    func pasteCalendarPayload() {
        let types = NSPasteboard.general.types?.map(\.rawValue).joined(separator: ", ") ?? "none"
        log("Pasteboard types: \(types)")
        if let ics = Self.pasteboardIcsText() {
            log("Paste ICS blob (\(ics.utf8.count) bytes)")
            insertIcsIntoPage(ics)
            return
        }
        if let text = Self.pasteboardURLText() {
            log("Paste URL instead of navigating: \(text)")
            insertTextIntoPage(text)
            return
        }
        if let raw = Self.pasteboardPlainText() {
            log("Paste plain text (\(raw.count) chars)")
            insertTextIntoPage(raw)
            return
        }
        pastePlainStringThroughWebKit(nil)
    }

    func insertTextIntoPage(_ text: String) {
        let payload = jsStringLiteral(text)
        let js = "(function(){try{return !!(window.kosistenzInsertText && window.kosistenzInsertText(\(payload)));}catch(e){return false;}})()"
        evaluateJavaScript(js) { result, error in
            if let error {
                log("Paste JS insert failed: \(error.localizedDescription)")
            }
            let ok = (result as? Bool) ?? false
            if !ok {
                DispatchQueue.main.async {
                    log("Paste JS insert missed; falling back to plain-text paste")
                    self.pastePlainStringThroughWebKit(text)
                }
            }
        }
    }

    /// Strip public.url so WebKit inserts characters instead of navigating.
    func pastePlainStringThroughWebKit(_ text: String?) {
        if let text {
            let pb = NSPasteboard.general
            pb.clearContents()
            pb.setString(text, forType: .string)
        }
        // Never send paste: to this subclass — that re-enters pasteFromClipboard.
        // WKContentView (a descendant) still implements insertText:/paste: in AppKit.
        if performWebEdit("insertText:", on: self, sender: text ?? "", skip: self) {
            return
        }
        _ = performWebEdit("paste:", on: self, skip: self)
    }
}

/// Cmd+V must be taken here. WKContentView implements paste: and never
/// calls super, so a WKWebView subclass never sees the menu key equivalent.
final class KosistenzMainWindow: NSWindow {
    weak var hostWebView: KosistenzWebView?

    override func sendEvent(_ event: NSEvent) {
        if Self.isPlainCommand(event, letter: "v") {
            hostWebView?.pasteFromClipboard()
            return
        }
        if Self.isPlainCommand(event, letter: "c") {
            if performWebEdit("copy:", on: hostWebView) {
                return
            }
        }
        if Self.isPlainCommand(event, letter: "x") {
            if performWebEdit("cut:", on: hostWebView) {
                return
            }
        }
        if Self.isPlainCommand(event, letter: "a") {
            if performWebEdit("selectAll:", on: hostWebView) {
                return
            }
        }
        super.sendEvent(event)
    }

    static func isPlainCommand(_ event: NSEvent, letter: String) -> Bool {
        guard event.type == .keyDown else { return false }
        guard event.modifierFlags.contains(.command) else { return false }
        if event.modifierFlags.contains(.option) || event.modifierFlags.contains(.shift) {
            return false
        }
        let chars = event.charactersIgnoringModifiers?.lowercased() ?? ""
        return chars == letter.lowercased()
    }
}

/// macOS 26's Swift overlay no longer exposes AppKit edit actions on
/// WKWebView, and `.copy(nil)` binds to NSCopying.copy(with:). Call those
/// actions by selector and prefer the focused descendant (WKContentView)
/// over WKWebView itself.
@discardableResult
private func performWebEdit(
    _ name: String,
    on view: NSObject?,
    sender: Any? = nil,
    skip: NSObject? = nil
) -> Bool {
    let sel = NSSelectorFromString(name)
    if let fr = (view as? NSView)?.window?.firstResponder as NSObject?,
       fr !== skip,
       fr.responds(to: sel) {
        _ = fr.perform(sel, with: sender)
        return true
    }
    if let root = view as? NSView, let found = firstDescendant(root, respondingTo: sel, skip: skip) {
        _ = found.perform(sel, with: sender)
        return true
    }
    guard let view, view !== skip, view.responds(to: sel) else { return false }
    _ = view.perform(sel, with: sender)
    return true
}

private func firstDescendant(_ view: NSView, respondingTo sel: Selector, skip: NSObject?) -> NSView? {
    for sub in view.subviews {
        if sub !== skip, sub.responds(to: sel) {
            return sub
        }
        if let nested = firstDescendant(sub, respondingTo: sel, skip: skip) {
            return nested
        }
    }
    return nil
}

private func jsStringLiteral(_ value: String) -> String {
    let escaped = value
        .replacingOccurrences(of: "\\", with: "\\\\")
        .replacingOccurrences(of: "\"", with: "\\\"")
        .replacingOccurrences(of: "\n", with: "\\n")
        .replacingOccurrences(of: "\r", with: "\\r")
        .replacingOccurrences(of: "\u{2028}", with: "\\u2028")
        .replacingOccurrences(of: "\u{2029}", with: "\\u2029")
    return "\"\(escaped)\""
}

/// Native Mac host for Kosistenz: Cocoa window + WKWebView + menu bar.
/// Python (kosistenz-bridge) only serves the local UI; it does not create the window.
final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, WKNavigationDelegate, WKUIDelegate, NSMenuDelegate, WKScriptMessageHandler {
    var window: NSWindow?
    var webView: WKWebView?
    var bridge: Process?
    var logHandle: FileHandle?
    var stopping = false
    var uiPort: UInt16 = 17653
    var apiPort: UInt16 = 18741
    var statusItem: NSStatusItem?
    var effectView: NSVisualEffectView?

    func applicationDidFinishLaunching(_ notification: Notification) {
        log("Swift host launching")
        buildMenu()
        NSApp.servicesProvider = self
        NSUpdateDynamicServices()

        do {
            let port = try pickPort()
            uiPort = port
            let webDir = try locateWebDir()
            let bridgeURL = try locateBridge()
            log("Starting bridge: \(bridgeURL.path) --bridge \(port) \(webDir)")
            try startBridge(executable: bridgeURL, port: port, webDir: webDir)
            createWindow()
            setupStatusItem()
            waitForServerThenLoad(port: port)
        } catch {
            fail("Kosistenz could not start.\n\n\(error.localizedDescription)")
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        showMainWindow()
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        stopBridge()
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        sender.orderOut(nil)
        return false
    }

    func applicationDidBecomeActive(_ notification: Notification) {
        window?.makeFirstResponder(webView)
        webView?.evaluateJavaScript("window.kosistenzPullPhone && window.kosistenzPullPhone()")
    }

    func windowDidBecomeKey(_ notification: Notification) {
        window?.makeFirstResponder(webView)
    }

    @objc func copy(_ sender: Any?) {
        _ = performWebEdit("copy:", on: webView, sender: sender)
    }

    @objc func cut(_ sender: Any?) {
        _ = performWebEdit("cut:", on: webView, sender: sender)
    }

    @objc func paste(_ sender: Any?) {
        if let host = webView as? KosistenzWebView {
            host.pasteFromClipboard()
            return
        }
        _ = performWebEdit("paste:", on: webView, sender: sender, skip: webView)
    }

    @objc func selectAll(_ sender: Any?) {
        _ = performWebEdit("selectAll:", on: webView, sender: sender)
    }

    func application(_ application: NSApplication, open urls: [URL]) {
        for url in urls {
            handleKosistenzURL(url)
        }
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard isTrustedScriptOrigin(message.frameInfo.securityOrigin) else { return }
        guard let body = message.body as? [String: Any],
              let type = body["type"] as? String else { return }
        if type == "theme" {
            let dark = body["dark"] as? Bool ?? true
            applyNativeAppearance(dark: dark)
        } else if type == "tab", let title = body["title"] as? String {
            let clipped = String(title.prefix(80))
            window?.title = clipped
        } else if type == "calendarImport" {
            importAppleCalendars()
        } else if type == "icsPaste" {
            (webView as? KosistenzWebView)?.pasteCalendarPayload()
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.cancel)
            return
        }
        let scheme = url.scheme?.lowercased() ?? ""
        if scheme == "kosistenz" {
            handleKosistenzURL(url)
            decisionHandler(.cancel)
            return
        }
        if isUiURL(url) {
            decisionHandler(.allow)
            return
        }
        // Paste, drop, or Cmd+click of a calendar link must never navigate
        // away. Put the URL in the page (ICS box when Calendar is open).
        if ["http", "https", "webcal"].contains(scheme) {
            let pasted = url.absoluteString
            if let host = webView as? KosistenzWebView {
                host.insertTextIntoPage(pasted)
            }
            log("Inserted pasted URL instead of navigating: \(pasted)")
            decisionHandler(.cancel)
            return
        }
        log("Blocked navigation to \(url.absoluteString)")
        decisionHandler(.cancel)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        window?.makeFirstResponder(webView)
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        log("Navigation failed: \(error.localizedDescription)")
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        log("Provisional navigation failed: \(error.localizedDescription)")
    }

    func webView(
        _ webView: WKWebView,
        runJavaScriptAlertPanelWithMessage message: String,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping () -> Void
    ) {
        let alert = NSAlert()
        alert.messageText = "Kosistenz"
        alert.informativeText = message
        alert.alertStyle = .informational
        alert.addButton(withTitle: "OK")
        alert.runModal()
        completionHandler()
    }

    func webView(
        _ webView: WKWebView,
        runJavaScriptConfirmPanelWithMessage message: String,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping (Bool) -> Void
    ) {
        let alert = NSAlert()
        alert.messageText = "Kosistenz"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.addButton(withTitle: "Cancel")
        completionHandler(alert.runModal() == .alertFirstButtonReturn)
    }

    func webView(
        _ webView: WKWebView,
        runJavaScriptTextInputPanelWithPrompt prompt: String,
        defaultText: String?,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping (String?) -> Void
    ) {
        let alert = NSAlert()
        alert.messageText = "Kosistenz"
        alert.informativeText = prompt
        alert.alertStyle = .informational
        alert.addButton(withTitle: "OK")
        alert.addButton(withTitle: "Cancel")
        let field = NSTextField(frame: NSRect(x: 0, y: 0, width: 280, height: 24))
        field.stringValue = defaultText ?? ""
        alert.accessoryView = field
        alert.window.initialFirstResponder = field
        let response = alert.runModal()
        completionHandler(response == .alertFirstButtonReturn ? field.stringValue : nil)
    }

    func createWindow() {
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let width = min(1280.0, max(960.0, screen.width - 80))
        let height = min(840.0, max(680.0, screen.height - 80))
        let rect = NSRect(
            x: screen.midX - width / 2,
            y: screen.midY - height / 2,
            width: width,
            height: height
        )
        let style: NSWindow.StyleMask = [.titled, .closable, .miniaturizable, .resizable]
        let window = KosistenzMainWindow(
            contentRect: rect,
            styleMask: style,
            backing: .buffered,
            defer: false
        )
        window.title = "Kosistenz"
        window.minSize = NSSize(width: 960, height: 680)
        window.isReleasedWhenClosed = false
        window.delegate = self
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true
        window.backgroundColor = NSColor.windowBackgroundColor
        if #available(macOS 11.0, *) {
            window.toolbarStyle = .unified
            window.titlebarSeparatorStyle = .none
        }

        let config = WKWebViewConfiguration()
        let controller = WKUserContentController()
        let script = WKUserScript(
            source: """
            document.documentElement.classList.add('native-shell');
            window.kosistenzNative = true;
            """,
            injectionTime: .atDocumentStart,
            forMainFrameOnly: true
        )
        controller.addUserScript(script)
        controller.add(self, name: "kosistenz")
        config.userContentController = controller
        let prefs = WKWebpagePreferences()
        prefs.allowsContentJavaScript = true
        config.defaultWebpagePreferences = prefs

        let effect = NSVisualEffectView(frame: rect)
        effect.material = .sidebar
        effect.blendingMode = .behindWindow
        effect.state = .active
        effect.autoresizingMask = [.width, .height]

        let webView = KosistenzWebView(frame: effect.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = false
        webView.allowsLinkPreview = false
        // Opaque page so sidebar clicks hit the UI. A clear WKWebView
        // passes mouse events through transparent CSS pixels to the
        // vibrancy view behind it, which is why tabs used to be dead.
        webView.setValue(true, forKey: "drawsBackground")
        if #available(macOS 12.0, *) {
            webView.underPageBackgroundColor = NSColor.windowBackgroundColor
        }
        effect.addSubview(webView)
        window.contentView = effect
        setupToolbar(on: window)
        window.makeKeyAndOrderFront(nil)
        window.makeFirstResponder(webView)
        NSApp.activate(ignoringOtherApps: true)

        window.hostWebView = webView
        self.effectView = effect
        self.window = window
        self.webView = webView
        log("Native window shown")
    }

    func waitForServerThenLoad(port: UInt16) {
        let url = URL(string: "http://127.0.0.1:\(port)/index.html")!
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let ok = waitForHTTP(url: url, timeout: 20)
            DispatchQueue.main.async {
                guard let self = self else { return }
                // terminationStatus throws if the process is still running.
                if let process = self.bridge, !process.isRunning {
                    self.fail("The UI server exited immediately (code \(process.terminationStatus)). See ~/Library/Logs/Kosistenz.log")
                    return
                }
                if ok {
                    log("UI server ready on \(port)")
                    self.webView?.load(URLRequest(url: url))
                    log("Loading \(url.absoluteString)")
                    self.window?.makeFirstResponder(self.webView)
                    self.reloadWidgets()
                } else {
                    self.fail("The UI server did not start on port \(port). See ~/Library/Logs/Kosistenz.log")
                }
            }
        }
    }

    private func startBridge(executable: URL, port: UInt16, webDir: String) throws {
        let process = Process()
        process.executableURL = executable
        process.arguments = ["--bridge", "\(port)", webDir]
        var env = ProcessInfo.processInfo.environment
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        env["KOSISTENZ_API_PORT"] = "\(apiPort)"
        process.environment = env

        let logURL = logFileURL()
        if !FileManager.default.fileExists(atPath: logURL.path) {
            FileManager.default.createFile(atPath: logURL.path, contents: nil)
        }
        let handle = try FileHandle(forWritingTo: logURL)
        handle.seekToEndOfFile()
        process.standardOutput = handle
        process.standardError = handle
        self.logHandle = handle

        try process.run()
        self.bridge = process
    }

    private func stopBridge() {
        guard !stopping else { return }
        stopping = true
        guard let process = bridge, process.isRunning else { return }
        process.terminate()
        let deadline = Date().addingTimeInterval(2)
        while process.isRunning && Date() < deadline {
            Thread.sleep(forTimeInterval: 0.05)
        }
        if process.isRunning {
            kill(process.processIdentifier, SIGKILL)
        }
        log("Bridge stopped")
    }

    private func fail(_ message: String) {
        log(message)
        stopBridge()
        let alert = NSAlert()
        alert.messageText = "Kosistenz"
        alert.informativeText = message
        alert.alertStyle = .critical
        alert.addButton(withTitle: "OK")
        alert.runModal()
        NSApp.terminate(nil)
    }
}

private func locateBridge() throws -> URL {
    guard let exe = Bundle.main.executableURL else {
        throw simpleError("Could not find the app executable.")
    }
    let url = exe.deletingLastPathComponent().appendingPathComponent("kosistenz-bridge")
    guard FileManager.default.isExecutableFile(atPath: url.path) else {
        throw simpleError("Missing kosistenz-bridge in the app bundle.")
    }
    return url
}

private func locateWebDir() throws -> String {
    var candidates: [String] = []
    if let frameworks = Bundle.main.privateFrameworksPath {
        candidates.append((frameworks as NSString).appendingPathComponent("web"))
    }
    if let resources = Bundle.main.resourcePath {
        candidates.append((resources as NSString).appendingPathComponent("web"))
    }
    if let exe = Bundle.main.executableURL {
        candidates.append(
            exe.deletingLastPathComponent()
                .deletingLastPathComponent()
                .appendingPathComponent("Frameworks/web")
                .path
        )
    }
    for path in candidates {
        var isDir: ObjCBool = false
        if FileManager.default.fileExists(atPath: path, isDirectory: &isDir), isDir.boolValue {
            return path
        }
    }
    throw simpleError("UI folder missing (web/). Rebuild with ./macos/install_app.sh")
}

private func pickPort(preferred: UInt16 = 17653) throws -> UInt16 {
    if let port = bindPort(preferred) {
        return port
    }
    if let port = bindPort(0) {
        return port
    }
    throw simpleError("Could not reserve a local port.")
}

private func bindPort(_ requested: UInt16) -> UInt16? {
    let fd = socket(AF_INET, SOCK_STREAM, 0)
    guard fd >= 0 else { return nil }
    defer { close(fd) }
    var yes: Int32 = 1
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))
    var addr = sockaddr_in()
    addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
    addr.sin_family = sa_family_t(AF_INET)
    addr.sin_port = requested.bigEndian
    addr.sin_addr = in_addr(s_addr: inet_addr("127.0.0.1"))
    let bound = withUnsafePointer(to: &addr) { ptr in
        ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) {
            bind(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
        }
    }
    guard bound == 0 else { return nil }
    var actual = sockaddr_in()
    var len = socklen_t(MemoryLayout<sockaddr_in>.size)
    let named = withUnsafeMutablePointer(to: &actual) { ptr in
        ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) {
            getsockname(fd, $0, &len)
        }
    }
    guard named == 0 else { return nil }
    return UInt16(bigEndian: actual.sin_port)
}

private func waitForHTTP(url: URL, timeout: TimeInterval) -> Bool {
    let deadline = Date().addingTimeInterval(timeout)
    while Date() < deadline {
        if let _ = try? Data(contentsOf: url) {
            return true
        }
        Thread.sleep(forTimeInterval: 0.1)
    }
    return false
}

private func buildMenu() {
    let mainMenu = NSMenu()

    let appItem = NSMenuItem()
    mainMenu.addItem(appItem)
    let appMenu = NSMenu()
    appMenu.addItem(withTitle: "About Kosistenz", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
    appMenu.addItem(NSMenuItem.separator())
    appMenu.addItem(withTitle: "Hide Kosistenz", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
    let hideOthers = NSMenuItem(
        title: "Hide Others",
        action: #selector(NSApplication.hideOtherApplications(_:)),
        keyEquivalent: "h"
    )
    hideOthers.keyEquivalentModifierMask = [.command, .option]
    appMenu.addItem(hideOthers)
    appMenu.addItem(withTitle: "Show All", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: "")
    appMenu.addItem(NSMenuItem.separator())
    appMenu.addItem(withTitle: "Quit Kosistenz", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
    appItem.submenu = appMenu

    let editItem = NSMenuItem()
    mainMenu.addItem(editItem)
    let editMenu = NSMenu(title: "Edit")
    editMenu.addItem(withTitle: "Undo", action: NSSelectorFromString("undo:"), keyEquivalent: "z")
    editMenu.addItem(withTitle: "Redo", action: NSSelectorFromString("redo:"), keyEquivalent: "Z")
    editMenu.addItem(NSMenuItem.separator())
    editMenu.addItem(withTitle: "Cut", action: NSSelectorFromString("cut:"), keyEquivalent: "x")
    editMenu.addItem(withTitle: "Copy", action: NSSelectorFromString("copy:"), keyEquivalent: "c")
    let pasteItem = NSMenuItem(title: "Paste", action: #selector(AppDelegate.paste(_:)), keyEquivalent: "v")
    pasteItem.target = retainedDelegate
    editMenu.addItem(pasteItem)
    editMenu.addItem(withTitle: "Select All", action: NSSelectorFromString("selectAll:"), keyEquivalent: "a")
    editItem.submenu = editMenu

    NSApp.mainMenu = mainMenu
}

private func logFileURL() -> URL {
    FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Logs/Kosistenz.log")
}

func log(_ message: String) {
    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
    let line = "\(formatter.string(from: Date())) \(message)\n"
    let url = logFileURL()
    let dir = url.deletingLastPathComponent()
    try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    if !FileManager.default.fileExists(atPath: url.path) {
        FileManager.default.createFile(atPath: url.path, contents: nil)
    }
    guard let handle = try? FileHandle(forWritingTo: url),
          let data = line.data(using: .utf8) else { return }
    handle.seekToEndOfFile()
    handle.write(data)
    handle.closeFile()
}

private func simpleError(_ message: String) -> NSError {
    NSError(domain: "com.kosistenz.app", code: 1, userInfo: [NSLocalizedDescriptionKey: message])
}

private let retainedDelegate = AppDelegate()

@main
enum KosistenzApp {
    static func main() {
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)
        app.delegate = retainedDelegate
        app.run()
    }
}
