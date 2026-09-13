import Foundation
import UIKit

/// Reads and writes the same JSON pack the Mac puts in iCloud Drive / Kosistenz.
enum SyncPack {
    static let folderName = FolderBookmark.folderName

    enum Access {
        case iCloudDrive
        case localOnly
        case needsFolder
    }

    struct LoadResult {
        var pack: Pack
        var access: Access
        var syncedAt: String?
        var folder: URL
    }

    static func folderURL() throws -> (URL, Access) {
        if let bookmarked = FolderBookmark.savedURL() {
            return (bookmarked, .iCloudDrive)
        }
        return (try FolderBookmark.localFallback(), .needsFolder)
    }

    static func usingChosenFolder() -> Bool {
        FolderBookmark.savedURL() != nil
    }

    static func load() throws -> LoadResult {
        let (folder, access) = try folderURL()
        return try FolderBookmark.access(folder) { live in
            let pack = Pack(
                work: coordinatedDecode(WorkFile.self, at: live.appendingPathComponent("work.json"))
                    ?? WorkFile(items: [], series: [], exceptions: [], goals: []),
                workouts: coordinatedDecode(WorkoutsFile.self, at: live.appendingPathComponent("workouts.json"))
                    ?? WorkoutsFile(days: [], sessions: [], template: nil),
                journal: coordinatedDecode([JournalEntry].self, at: live.appendingPathComponent("journal.json")) ?? [],
                calendar: coordinatedDecode(CalendarFile.self, at: live.appendingPathComponent("calendar.json"))
                    ?? CalendarFile(),
                appearance: coordinatedJSON(at: live.appendingPathComponent("appearance.json")),
                folder: live
            )
            let manifest = coordinatedJSON(at: live.appendingPathComponent("manifest.json"))
            let exported = manifest["exported_at"] as? String
            let resolvedAccess: Access
            if access == .needsFolder, packHasBytes(pack) {
                resolvedAccess = .needsFolder
            } else if access == .needsFolder {
                resolvedAccess = .needsFolder
            } else {
                resolvedAccess = .iCloudDrive
            }
            return LoadResult(pack: pack, access: resolvedAccess, syncedAt: exported, folder: live)
        }
    }

    static func saveWork(_ file: WorkFile) throws { try write(file, name: "work.json") }
    static func saveWorkouts(_ file: WorkoutsFile) throws { try write(file, name: "workouts.json") }
    static func saveJournal(_ entries: [JournalEntry]) throws { try write(entries, name: "journal.json") }
    static func saveCalendar(_ file: CalendarFile) throws { try write(file, name: "calendar.json") }

    private static func packHasBytes(_ pack: Pack) -> Bool {
        !pack.work.items.isEmpty || !pack.journal.isEmpty || !pack.workouts.sessions.isEmpty
    }

    private static func write<T: Encodable>(_ value: T, name: String) throws {
        let (folder, _) = try folderURL()
        try FolderBookmark.access(folder) { live in
            try coordinatedEncode(value, to: live.appendingPathComponent(name))
            try touchManifest(in: live)
        }
    }

    private static func coordinatedDecode<T: Decodable>(_ type: T.Type, at url: URL) -> T? {
        guard let data = coordinatedRead(url) else { return nil }
        return try? JSONDecoder().decode(type, from: data)
    }

    private static func coordinatedJSON(at url: URL) -> [String: Any] {
        guard let data = coordinatedRead(url),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { return [:] }
        return object
    }

    private static func coordinatedRead(_ url: URL) -> Data? {
        var data: Data?
        var error: NSError?
        NSFileCoordinator().coordinate(readingItemAt: url, options: [], error: &error) { readURL in
            data = try? Data(contentsOf: readURL)
        }
        return data
    }

    private static func coordinatedEncode<T: Encodable>(_ value: T, to url: URL) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let payload = try encoder.encode(value)
        var error: NSError?
        var writeError: Error?
        NSFileCoordinator().coordinate(writingItemAt: url, options: .forReplacing, error: &error) { writeURL in
            do {
                try payload.write(to: writeURL, options: .atomic)
            } catch {
                writeError = error
            }
        }
        if let error { throw error }
        if let writeError { throw writeError }
    }

    private static func touchManifest(in folder: URL) throws {
        let payload: [String: Any] = [
            "schema": 1,
            "exported_at": ISO8601DateFormatter().string(from: Date()),
            "device": UIDevice.current.name,
        ]
        let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted])
        var error: NSError?
        var writeError: Error?
        let url = folder.appendingPathComponent("manifest.json")
        NSFileCoordinator().coordinate(writingItemAt: url, options: .forReplacing, error: &error) { writeURL in
            do {
                try data.write(to: writeURL, options: .atomic)
            } catch {
                writeError = error
            }
        }
        if let error { throw error }
        if let writeError { throw writeError }
    }
}

struct Pack {
    var work: WorkFile
    var workouts: WorkoutsFile
    var journal: [JournalEntry]
    var calendar: CalendarFile
    var appearance: [String: Any]
    var folder: URL
}

struct WorkFile: Codable {
    var items: [WorkItem]
    var series: [FlexibleJSON]
    var exceptions: [FlexibleJSON]
    var goals: [GoalRow]?
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
    var due_at: String?
    var estimate_minutes: Int?
    var goal_id: String?
}

struct GoalRow: Codable, Identifiable {
    var id: String
    var title: String?
    var horizon: String?
    var spent_minutes: Int?
    var target_minutes: Int?
    var archived: Int?
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
    var updated_at: String?
    var tags: [String]?
    var kind: String?
}

struct CalendarFile: Codable {
    var week_start: String?
    var week_end: String?
    var day_start: String?
    var day_end: String?
    var days: [CalendarDay]
    var unplaced: [UnplacedItem]
    var hard_events: [HardEvent]
    var marks: [CalendarMark]

    init(
        week_start: String? = nil,
        week_end: String? = nil,
        day_start: String? = nil,
        day_end: String? = nil,
        days: [CalendarDay] = [],
        unplaced: [UnplacedItem] = [],
        hard_events: [HardEvent] = [],
        marks: [CalendarMark] = []
    ) {
        self.week_start = week_start
        self.week_end = week_end
        self.day_start = day_start
        self.day_end = day_end
        self.days = days
        self.unplaced = unplaced
        self.hard_events = hard_events
        self.marks = marks
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        week_start = try container.decodeIfPresent(String.self, forKey: .week_start)
        week_end = try container.decodeIfPresent(String.self, forKey: .week_end)
        day_start = try container.decodeIfPresent(String.self, forKey: .day_start)
        day_end = try container.decodeIfPresent(String.self, forKey: .day_end)
        days = try container.decodeIfPresent([CalendarDay].self, forKey: .days) ?? []
        unplaced = try container.decodeIfPresent([UnplacedItem].self, forKey: .unplaced) ?? []
        hard_events = try container.decodeIfPresent([HardEvent].self, forKey: .hard_events) ?? []
        marks = try container.decodeIfPresent([CalendarMark].self, forKey: .marks) ?? []
    }
}

struct CalendarMark: Codable, Identifiable, Equatable {
    var id: String
    var status: String
    var updated_at: String
}

struct CalendarDay: Codable {
    var date: String?
    var weekday: String?
    var is_today: Bool?
    var events: [CalendarItem]
    var blocks: [CalendarItem]
    var dues: [DueItem]

    init(
        date: String? = nil,
        weekday: String? = nil,
        is_today: Bool? = nil,
        events: [CalendarItem] = [],
        blocks: [CalendarItem] = [],
        dues: [DueItem] = []
    ) {
        self.date = date
        self.weekday = weekday
        self.is_today = is_today
        self.events = events
        self.blocks = blocks
        self.dues = dues
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        date = try container.decodeIfPresent(String.self, forKey: .date)
        weekday = try container.decodeIfPresent(String.self, forKey: .weekday)
        is_today = try container.decodeIfPresent(Bool.self, forKey: .is_today)
        events = try container.decodeIfPresent([CalendarItem].self, forKey: .events) ?? []
        blocks = try container.decodeIfPresent([CalendarItem].self, forKey: .blocks) ?? []
        dues = try container.decodeIfPresent([DueItem].self, forKey: .dues) ?? []
    }
}

struct CalendarItem: Codable, Identifiable {
    var itemId: String?
    var title: String?
    var kind: String?
    var status: String?
    var start_at: String?
    var end_at: String?
    var work_item_id: String?
    var updated_at: String?
    var occurrence_date: String?
    var id: String { itemId ?? "\(title ?? "event")-\(start_at ?? "")-\(end_at ?? "")" }

    /// What a check-off is filed under. Every occurrence of a repeating event
    /// shares one event id, so the day has to be part of the key or one tap
    /// reads as the whole series attended. Matches event_mark_key on the Mac.
    var markKey: String {
        let base = itemId ?? id
        guard let day = occurrence_date, day.count >= 10, !base.contains("@") else { return base }
        return "\(base)@\(day.prefix(10))"
    }

    enum CodingKeys: String, CodingKey {
        case itemId = "id"
        case title, kind, status, start_at, end_at, work_item_id, updated_at, occurrence_date
    }
}

struct DueItem: Codable, Identifiable {
    var itemId: String?
    var title: String?
    var due_at: String?
    var course: String?
    var estimate_minutes: Int?
    var status: String?
    var hue: Int?
    var id: String { itemId ?? "\(title ?? "due")-\(due_at ?? UUID().uuidString)" }

    enum CodingKeys: String, CodingKey {
        case itemId = "id"
        case title, due_at, course, estimate_minutes, status, hue
    }
}

struct HardEvent: Codable, Identifiable, Equatable {
    var id: String
    var title: String
    var start_at: String
    var end_at: String
    var weekdays: [Int]
    var source: String?
    var created_at: String?
    var updated_at: String?

    init(
        id: String,
        title: String,
        start_at: String,
        end_at: String,
        weekdays: [Int] = [],
        source: String? = "iphone",
        created_at: String? = nil,
        updated_at: String? = nil
    ) {
        self.id = id
        self.title = title
        self.start_at = start_at
        self.end_at = end_at
        self.weekdays = weekdays
        self.source = source
        self.created_at = created_at
        self.updated_at = updated_at
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        start_at = try container.decode(String.self, forKey: .start_at)
        end_at = try container.decode(String.self, forKey: .end_at)
        weekdays = try container.decodeIfPresent([Int].self, forKey: .weekdays) ?? []
        source = try container.decodeIfPresent(String.self, forKey: .source)
        created_at = try container.decodeIfPresent(String.self, forKey: .created_at)
        updated_at = try container.decodeIfPresent(String.self, forKey: .updated_at)
    }
}

struct UnplacedItem: Codable, Identifiable {
    var itemId: String?
    var title: String?
    var id: String { itemId ?? title ?? UUID().uuidString }

    enum CodingKeys: String, CodingKey {
        case itemId = "id"
        case title
    }
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

enum DayStamp {
    static func today() -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar.current
        formatter.locale = Locale.current
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: Date())
    }

    static func isoNow() -> String {
        ISO8601DateFormatter().string(from: Date())
    }

    static func localStamp(_ date: Date = Date()) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter.string(from: date)
    }

    static func clock(_ raw: String?) -> String {
        guard let raw, raw.count >= 16 else { return "" }
        let slice = String(raw.dropFirst(11).prefix(5))
        return slice
    }
}
