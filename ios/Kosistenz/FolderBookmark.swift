import Foundation
import UniformTypeIdentifiers

/// Security-scoped bookmark for iCloud Drive / Kosistenz — the same folder the Mac writes.
enum FolderBookmark {
    static let defaultsKey = "kosistenz.icloud.folder.bookmark"
    static let folderName = "Kosistenz"

    static func savedURL() -> URL? {
        guard let data = UserDefaults.standard.data(forKey: defaultsKey) else { return nil }
        var stale = false
        guard let url = try? URL(
            resolvingBookmarkData: data,
            options: [.withoutUI],
            relativeTo: nil,
            bookmarkDataIsStale: &stale
        ) else { return nil }
        if stale {
            try? save(url)
        }
        return url
    }

    static func save(_ url: URL) throws {
        let data = try url.bookmarkData(options: [], includingResourceValuesForKeys: nil, relativeTo: nil)
        UserDefaults.standard.set(data, forKey: defaultsKey)
    }

    static func clear() {
        UserDefaults.standard.removeObject(forKey: defaultsKey)
    }

    static func localFallback() throws -> URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let folder = docs.appendingPathComponent(folderName, isDirectory: true)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        return folder
    }

    @discardableResult
    static func access<T>(_ url: URL, _ body: (URL) throws -> T) throws -> T {
        let started = url.startAccessingSecurityScopedResource()
        defer {
            if started { url.stopAccessingSecurityScopedResource() }
        }
        return try body(url)
    }
}
