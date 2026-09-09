import Foundation
import WidgetKit

/// Mutates the iCloud pack. Used by Today, Inbox, App Intents, and the widget.
enum PackActions {
    static func current() throws -> Pack {
        try SyncPack.load().pack
    }

    static func snapshot() -> WidgetSnapshot {
        do {
            let loaded = try SyncPack.load()
            let snap = WidgetSnapshot.from(pack: loaded.pack, access: loaded.access)
            WidgetBridge.write(snap)
            return snap
        } catch {
            if let cached = WidgetBridge.read() { return cached }
            return .empty
        }
    }

    @discardableResult
    static func park(_ raw: String) throws -> Pack {
        let title = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else { throw PackActionError.message("Type a thought to park.") }
        var pack = try current()
        let now = DayStamp.isoNow()
        pack.work.items.insert(newItem(title: title, date: nil, now: now), at: 0)
        return try saveWork(pack)
    }

    @discardableResult
    static func addTodo(_ raw: String, date: String) throws -> Pack {
        let title = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else { throw PackActionError.message("Type a to-do.") }
        var pack = try current()
        let now = DayStamp.isoNow()
        pack.work.items.insert(newItem(title: title, date: date, now: now), at: 0)
        return try saveWork(pack)
    }

    @discardableResult
    static func toggle(id: String) throws -> Pack {
        var pack = try current()
        guard let index = pack.work.items.firstIndex(where: { $0.id == id }) else {
            throw PackActionError.message("That to-do is gone.")
        }
        let item = pack.work.items[index]
        pack.work.items[index].status = item.status == "done" ? "open" : "done"
        pack.work.items[index].updated_at = DayStamp.isoNow()
        return try saveWork(pack)
    }

    static func toggleFirstOpen(on date: String) throws -> String {
        let pack = try current()
        guard let item = pack.work.items.first(where: { $0.scheduled_date == date && $0.status != "done" }) else {
            throw PackActionError.message("Nothing open for today.")
        }
        _ = try toggle(id: item.id)
        return item.title
    }

    @discardableResult
    static func logSession(kind: String, miles: Double?, other: String, date: String) throws -> Pack {
        if kind == "running" {
            guard let miles, miles > 0 else { throw PackActionError.message("Add miles for a run.") }
        }
        if kind == "other" {
            let name = other.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !name.isEmpty else { throw PackActionError.message("Name the other activity.") }
        }
        var pack = try current()
        pack.workouts.sessions.append(
            WorkoutSession(
                id: UUID().uuidString,
                local_date: date,
                kind: kind,
                other_label: other,
                miles: miles,
                minutes: nil,
                created_at: DayStamp.isoNow()
            )
        )
        try SyncPack.saveWorkouts(pack.workouts)
        ping(pack)
        return pack
    }

    static func logExpected(miles: Double?, other: String?, date: String) throws -> String {
        let pack = try current()
        let expected = WorkoutPlan.expectedKinds(on: Date(), template: pack.workouts.template)
        let logged = Set(pack.workouts.sessions.filter { $0.local_date == date }.map(\.kind))
        guard let kind = expected.first(where: { !logged.contains($0) }) ?? expected.first else {
            throw PackActionError.message("No expected workout today.")
        }
        let name = other ?? ""
        _ = try logSession(kind: kind, miles: miles, other: name, date: date)
        if kind == "running" { return "Logged the run." }
        if kind == "other" { return "Logged \(name)." }
        return "Logged \(WorkoutPlan.chipKinds.first(where: { $0.id == kind })?.label ?? kind)."
    }

    @discardableResult
    static func addHardEvent(title: String, date: String, start: String, end: String, weekdays: [Int]) throws -> Pack {
        let clean = title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { throw PackActionError.message("Name the event") }
        let startAt = try PhoneCalendar.combine(date: date, time: start)
        var endAt = try PhoneCalendar.combine(date: date, time: end)
        guard let startDate = localDate(startAt), var endDate = localDate(endAt) else {
            throw PackActionError.message("Use a 24-hour time like 0930 or 09:30.")
        }
        if endDate <= startDate {
            endDate = endDate.addingTimeInterval(24 * 3600)
            endAt = DayStamp.localStamp(endDate)
        }
        let hours = endDate.timeIntervalSince(startDate) / 3600
        guard hours > 0 else { throw PackActionError.message("End must be after start") }
        if hours > 12 {
            throw PackActionError.message("Events longer than 12 hours need to be split")
        }
        var pack = try current()
        let now = DayStamp.localStamp()
        let days = weekdays.filter { (0...6).contains($0) }
        let event = HardEvent(
            id: UUID().uuidString,
            title: String(clean.prefix(200)),
            start_at: startAt,
            end_at: endAt,
            weekdays: days,
            source: "iphone",
            created_at: now,
            updated_at: now
        )
        var calendar = pack.calendar
        calendar.hard_events.removeAll { $0.id == event.id }
        calendar.hard_events.append(event)
        let weekStart = calendar.week_start ?? calendar.days.first?.date ?? String(date.prefix(10))
        let weekEnd = calendar.week_end ?? calendar.days.last?.date ?? String(date.prefix(10))
        calendar.days = PhoneCalendar.paint(
            days: calendar.days,
            event: event,
            weekStart: weekStart,
            weekEnd: weekEnd
        )
        pack.calendar = calendar
        try SyncPack.saveCalendar(calendar)
        ping(pack)
        return pack
    }

    private static func localDate(_ iso: String) -> Date? {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter.date(from: String(iso.prefix(19)))
    }

    private static func saveWork(_ pack: Pack) throws -> Pack {
        try SyncPack.saveWork(pack.work)
        ping(pack)
        return pack
    }

    private static func ping(_ pack: Pack) {
        WidgetBridge.write(WidgetSnapshot.from(pack: pack, access: SyncPack.usingChosenFolder() ? .iCloudDrive : .needsFolder))
    }

    private static func newItem(title: String, date: String?, now: String) -> WorkItem {
        WorkItem(
            id: UUID().uuidString,
            title: title,
            notes: "",
            scheduled_date: date,
            status: "open",
            active_started_at: nil,
            finished_at: nil,
            duration_seconds: 0,
            sort_order: 0,
            created_at: now,
            updated_at: now,
            source: "iphone",
            series_id: nil,
            occurrence_date: date,
            due_at: nil,
            estimate_minutes: nil,
            goal_id: nil
        )
    }
}

enum PackActionError: LocalizedError {
    case message(String)
    var errorDescription: String? {
        if case .message(let text) = self { return text }
        return nil
    }
}

struct WidgetSnapshot: Codable, Equatable {
    var todos: [WidgetTodo]
    var nextBlock: String
    var expectedLabel: String
    var access: String
    var today: String

    static let empty = WidgetSnapshot(todos: [], nextBlock: "", expectedLabel: "", access: "needsFolder", today: DayStamp.today())

    struct WidgetTodo: Codable, Equatable, Identifiable {
        var id: String
        var title: String
        var done: Bool
    }

    static func from(pack: Pack, access: SyncPack.Access) -> WidgetSnapshot {
        let today = DayStamp.today()
        let todos = pack.work.items
            .filter { $0.scheduled_date == today }
            .prefix(4)
            .map { WidgetTodo(id: $0.id, title: $0.title, done: $0.status == "done") }
        let day = pack.calendar.days.first(where: { $0.date == today })
        let lanes = DayTimeline.blocks(events: day?.events ?? [], packed: day?.blocks ?? [])
        let next = lanes.first(where: { $0.isNow }) ?? lanes.first
        let expected = WorkoutPlan.expectedKinds(on: Date(), template: pack.workouts.template)
        let expectedLabel = expected
            .map { id in WorkoutPlan.chipKinds.first(where: { $0.id == id })?.label ?? id }
            .joined(separator: " · ")
        let accessName: String
        switch access {
        case .iCloudDrive: accessName = "iCloudDrive"
        case .localOnly: accessName = "localOnly"
        case .needsFolder: accessName = "needsFolder"
        }
        return WidgetSnapshot(
            todos: Array(todos),
            nextBlock: next.map { "\(DayTimeline.clock($0.startAt)) \($0.title)" } ?? "",
            expectedLabel: expectedLabel,
            access: accessName,
            today: today
        )
    }
}

enum WidgetBridge {
    static let groupId = "group.com.kosistenz.app"
    static let fileName = "widget_snapshot.json"

    static var container: URL? {
        FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: groupId)
    }

    static func write(_ snapshot: WidgetSnapshot) {
        guard let container else { return }
        do {
            try FileManager.default.createDirectory(at: container, withIntermediateDirectories: true)
            let data = try JSONEncoder().encode(snapshot)
            try data.write(to: container.appendingPathComponent(fileName), options: .atomic)
            WidgetCenter.shared.reloadAllTimelines()
        } catch {
            return
        }
    }

    static func read() -> WidgetSnapshot? {
        guard let container else { return nil }
        guard let data = try? Data(contentsOf: container.appendingPathComponent(fileName)) else { return nil }
        return try? JSONDecoder().decode(WidgetSnapshot.self, from: data)
    }
}
