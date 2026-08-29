import Cocoa
import Darwin
import Foundation
import WebKit

/// Native Mac host for Kosistenz: Cocoa window + WKWebView.
/// Python (kosistenz-bridge) only serves the local UI; it does not create the window.
final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, WKNavigationDelegate {
    private var window: NSWindow?
    private var webView: WKWebView?
    private var bridge: Process?
    private var logHandle: FileHandle?
    private var stopping = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        log("Swift host launching")
        buildMenu()

        do {
            let port = try pickPort()
            let webDir = try locateWebDir()
            let bridgeURL = try locateBridge()
            log("Starting bridge: \(bridgeURL.path) --bridge \(port) \(webDir)")
            try startBridge(executable: bridgeURL, port: port, webDir: webDir)
            createWindow()
            waitForServerThenLoad(port: port)
        } catch {
            fail("Kosistenz could not start.\n\n\(error.localizedDescription)")
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationWillTerminate(_ notification: Notification) {
        stopBridge()
    }

    func windowWillClose(_ notification: Notification) {
        stopBridge()
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.cancel)
            return
        }
        let scheme = url.scheme?.lowercased() ?? ""
        let host = url.host?.lowercased() ?? ""
        if (scheme == "http" || scheme == "https"), host == "127.0.0.1" || host == "localhost" {
            decisionHandler(.allow)
            return
        }
        log("Blocked navigation to \(url.absoluteString)")
        decisionHandler(.cancel)
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        log("Navigation failed: \(error.localizedDescription)")
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        log("Provisional navigation failed: \(error.localizedDescription)")
    }

    private func createWindow() {
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
        let window = NSWindow(
            contentRect: rect,
            styleMask: style,
            backing: .buffered,
            defer: false
        )
        window.title = "Kosistenz"
        window.minSize = NSSize(width: 960, height: 680)
        window.backgroundColor = NSColor(calibratedRed: 0.965, green: 0.961, blue: 0.953, alpha: 1)
        window.isReleasedWhenClosed = false
        window.delegate = self

        let config = WKWebViewConfiguration()
        let controller = WKUserContentController()
        let script = WKUserScript(
            source: """
            document.documentElement.classList.add('native-shell');
            window.kosistenzNative = true;
            """,
            injectionTime: .atDocumentEnd,
            forMainFrameOnly: true
        )
        controller.addUserScript(script)
        config.userContentController = controller
        let prefs = WKWebpagePreferences()
        prefs.allowsContentJavaScript = true
        config.defaultWebpagePreferences = prefs

        let webView = WKWebView(frame: rect, configuration: config)
        webView.navigationDelegate = self
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        self.window = window
        self.webView = webView
        log("Native window shown")
    }

    private func waitForServerThenLoad(port: UInt16) {
        let url = URL(string: "http://127.0.0.1:\(port)/index.html")!
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let ok = self?.waitForHTTP(url: url, timeout: 20) ?? false
            DispatchQueue.main.async {
                guard let self = self else { return }
                if let status = self.bridge?.terminationStatus, self.bridge?.isRunning == false {
                    self.fail("The UI server exited immediately (code \(status)). See ~/Library/Logs/Kosistenz.log")
                    return
                }
                if ok {
                    log("UI server ready on \(port)")
                    self.webView?.load(URLRequest(url: url))
                    log("Loading \(url.absoluteString)")
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
    editMenu.addItem(withTitle: "Undo", action: Selector("undo:"), keyEquivalent: "z")
    editMenu.addItem(withTitle: "Redo", action: Selector("redo:"), keyEquivalent: "Z")
    editMenu.addItem(NSMenuItem.separator())
    editMenu.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
    editMenu.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
    editMenu.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
    editMenu.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
    editItem.submenu = editMenu

    NSApp.mainMenu = mainMenu
}

private func logFileURL() -> URL {
    FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Logs/Kosistenz.log")
}

private func log(_ message: String) {
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

let app = NSApplication.shared
app.setActivationPolicy(.regular)
app.delegate = retainedDelegate
app.run()
