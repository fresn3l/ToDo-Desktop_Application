import Foundation
import UIKit

/// Reads and writes the same JSON pack the Mac puts in iCloud Drive / Kosistenz.
enum SyncPack {
    static let folderName = "Kosistenz"

    static func folderURL() throws -> URL {
        if let ubiquity = FileManager.default.url(forUbiquityContainerIdentifier: nil) {
            let docs = ubiquity.appendingPathComponent("Documents").appendingPathComponent(folderName)
            try FileManager.default.createDirectory(at: docs, withIntermediateDirectories: true)
            return docs
        }
        let fallback = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent(folderName)
        try FileManager.default.createDirectory(at: fallback, withIntermediateDirectories: true)
        return fallback
    }

    static func usingiCloudDrive() -> Bool {
        FileManager.default.url(forUbiquityContainerIdentifier: nil) != nil
    }

    static func load() throws -> Pack {
        let folder = try folderURL()
        return Pack(
            work: decode(WorkFile.self, at: folder.appendingPathComponent("work.json"))
                ?? WorkFile(items: [], series: [], exceptions: []),
            workouts: decode(WorkoutsFile.self, at: folder.appendingPathComponent("workouts.json"))
                ?? WorkoutsFile(days: [], sessions: [], template: nil),
            journal: decode([JournalEntry].self, at: folder.appendingPathComponent("journal.json")) ?? [],
            appearance: jsonObject(at: folder.appendingPathComponent("appearance.json")),
            folder: folder
        )
    }

    static func saveWork(_ file: WorkFile) throws {
        try encode(file, to: try folderURL().appendingPathComponent("work.json"))
        try touchManifest()
    }

    static func saveWorkouts(_ file: WorkoutsFile) throws {
        try encode(file, to: try folderURL().appendingPathComponent("workouts.json"))
        try touchManifest()
    }

    static func saveJournal(_ entries: [JournalEntry]) throws {
        try encode(entries, to: try folderURL().appendingPathComponent("journal.json"))
        try touchManifest()
    }

    private static func jsonObject(at url: URL) -> [String: Any] {
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { return [:] }
        return object
    }

    private static func decode<T: Decodable>(_ type: T.Type, at url: URL) -> T? {
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(type, from: data)
    }

    private static func encode<T: Encodable>(_ value: T, to url: URL) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(value).write(to: url, options: .atomic)
    }

    private static func touchManifest() throws {
        let payload = [
            "schema": 1,
            "exported_at": ISO8601DateFormatter().string(from: Date()),
            "device": UIDevice.current.name,
        ] as [String: Any]
        let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted])
        try data.write(to: try folderURL().appendingPathComponent("manifest.json"), options: .atomic)
    }
}

struct Pack {
    var work: WorkFile
    var workouts: WorkoutsFile
    var journal: [JournalEntry]
    var appearance: [String: Any]
    var folder: URL
}

struct WorkFile: Codable {
    var items: [WorkItem]
    var series: [FlexibleJSON]
    var exceptions: [FlexibleJSON]
}

struct WorkItem: Codable, Identifiable {
    var id: String
    var title: String
    var notes: String?
    var scheduled_date: String?
    var status: String
    var active_started_at: String?
    var finished_at: String?
    var duration_seconds: Int?
    var sort_order: Int?
    var created_at: String?
    var updated_at: String?
    var source: String?
    var series_id: String?
    var occurrence_date: String?
}

struct WorkoutsFile: Codable {
    var days: [FlexibleJSON]
    var sessions: [WorkoutSession]
    var template: FlexibleJSON?
}

struct WorkoutSession: Codable, Identifiable {
    var id: String
    var local_date: String
    var kind: String
    var other_label: String?
    var miles: Double?
    var minutes: Double?
    var created_at: String
}

struct JournalEntry: Codable, Identifiable {
    var id: String
    var content: String
    var date: String?
    var duration_seconds: Int?
    var continued: Bool?
    var created_at: String?
    var tags: [String]?
}

/// Pass-through JSON object so template / series blobs stay compatible with Python.
struct FlexibleJSON: Codable {
    var value: AnyJSON
    init(from decoder: Decoder) throws {
        value = try AnyJSON(from: decoder)
    }
    func encode(to encoder: Encoder) throws {
        try value.encode(to: encoder)
    }
}

enum AnyJSON: Codable {
    case object([String: AnyJSON])
    case array([AnyJSON])
    case string(String)
    case number(Double)
    case bool(Bool)
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() { self = .null; return }
        if let value = try? container.decode(Bool.self) { self = .bool(value); return }
        if let value = try? container.decode(Double.self) { self = .number(value); return }
        if let value = try? container.decode(String.self) { self = .string(value); return }
        if let value = try? container.decode([AnyJSON].self) { self = .array(value); return }
        if let value = try? container.decode([String: AnyJSON].self) { self = .object(value); return }
        self = .null
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .object(let value): try container.encode(value)
        case .array(let value): try container.encode(value)
        case .string(let value): try container.encode(value)
        case .number(let value): try container.encode(value)
        case .bool(let value): try container.encode(value)
        case .null: try container.encodeNil()
        }
    }
}
