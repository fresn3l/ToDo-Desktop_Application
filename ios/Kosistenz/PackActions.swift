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
        pack.work.items.insert(
            newItem(title: title, date: date, estimate: PhoneWork.parseMinutesFromTitle(title), now: now),
            at: 0
        )
        return try saveWork(pack)
    }

    @discardableResult
    static func toggle(id: String) throws -> Pack {
        var pack = try current()
        guard let index = pack.work.items.firstIndex(where: { $0.id == id }) else {
            throw PackActionError.message("That to-do is gone.")
        }
        let item = pack.work.items[index]
        let done = item.status != "done"
        pack.work.items[index].status = done ? "done" : "open"
        pack.work.items[index].finished_at = done ? DayStamp.isoNow() : nil
        pack.work.items[index].updated_at = DayStamp.isoNow()
        return try saveWork(pack)
    }

    @discardableResult
    static func assignToToday(id: String, date: String) throws -> Pack {
        var pack = try current()
        guard let index = pack.work.items.firstIndex(where: { $0.id == id }) else {
            throw PackActionError.message("That to-do is gone.")
        }
        pack.work.items[index].scheduled_date = date
        pack.work.items[index].updated_at = DayStamp.isoNow()
        return try saveWork(pack)
    }

    @discardableResult
    static func complete(_ entry: TodayList.Entry) throws -> Pack {
        var pack = try current()
        let now = DayStamp.isoNow()
        let markAt = DayStamp.localStamp()
        let makingDone = !entry.done
        if let workId = entry.workId, let index = pack.work.items.firstIndex(where: { $0.id == workId }) {
            pack.work.items[index].status = makingDone ? "done" : "open"
            pack.work.items[index].finished_at = makingDone ? now : nil
            pack.work.items[index].updated_at = now
        }
        if let clockId = entry.clockId {
            upsertMark(&pack, id: clockId, status: makingDone ? "done" : "open", at: markAt)
            paintClockStatus(&pack, id: clockId, status: makingDone ? "done" : "open")
            #if !WIDGET_EXTENSION
            EventAlerts.cancel(clockId: clockId)
            #endif
        }
        if entry.workId != nil {
            try SyncPack.saveWork(pack.work)
        }
        if entry.clockId != nil {
            try SyncPack.saveCalendar(pack.calendar)
        }
        ping(pack)
        return pack
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

    @discardableResult
    static func fillWeek(weekStart: String) throws -> Pack {
        var pack = try current()
        let today = DayStamp.today()
        let monday = PhoneCalendar.mondayOf(weekStart.isEmpty ? today : weekStart)
        var days = PhoneCalendar.assembleWeek(
            weekStart: monday,
            today: today,
            packedDays: pack.calendar.days,
            hardEvents: pack.calendar.hard_events,
            phoneBlocks: pack.calendar.phone_blocks,
            workItems: pack.work.items
        )
        let unplaced = PhoneCalendar.unplacedFromWork(
            items: pack.work.items,
            blocks: PhoneCalendar.flattenBlocks(days: days)
        )
        let filled = PhoneCalendar.fillWeek(
            days: days,
            items: unplaced,
            dayStart: pack.calendar.day_start,
            dayEnd: pack.calendar.day_end
        )
        days = filled.days
        var placed = filled.placed
        days = placeGym(days: days, pack: pack, monday: monday)
        placed += PhoneCalendar.flattenBlocks(days: days).filter { item in
            (item.source ?? "") == "iphone" && (item.kind ?? "") == "workout" &&
            !pack.calendar.phone_blocks.contains(where: { $0.itemId == item.itemId })
        }
        pack.calendar.phone_blocks = mergePhoneBlocks(pack.calendar.phone_blocks.filter { block in
            !filled.removed.contains(block.itemId ?? block.id)
        } + placed)
        pack.calendar.removed_block_ids = uniqueIds(pack.calendar.removed_block_ids + filled.removed)
        writeAssembled(monday, days: days, into: &pack)
        pack.calendar.unplaced = PhoneCalendar.unplacedFromWork(
            items: pack.work.items,
            blocks: PhoneCalendar.flattenBlocks(days: pack.calendar.days) + pack.calendar.phone_blocks
        )
        try SyncPack.saveCalendar(pack.calendar)
        ping(pack)
        return pack
    }

    @discardableResult
    static func placeWork(id: String, start: String, end: String = "") throws -> Pack {
        var pack = try current()
        guard let item = pack.work.items.first(where: { $0.id == id }) else {
            throw PackActionError.message("That to-do is gone.")
        }
        let today = DayStamp.today()
        let monday = PhoneCalendar.mondayOf(String(start.prefix(10)))
        var days = PhoneCalendar.assembleWeek(
            weekStart: monday,
            today: today,
            packedDays: pack.calendar.days,
            hardEvents: pack.calendar.hard_events,
            phoneBlocks: pack.calendar.phone_blocks,
            workItems: pack.work.items
        )
        let leftover = PhoneCalendar.remainingMinutes(
            estimate: item.estimate_minutes,
            placed: PhoneCalendar.placedMinutes(blocks: PhoneCalendar.flattenBlocks(days: days), itemId: item.id),
            status: item.status
        )
        let row = UnplacedItem(
            itemId: item.id,
            title: item.title,
            scheduled_date: item.scheduled_date,
            due_at: item.due_at,
            estimate_minutes: item.estimate_minutes,
            remaining_minutes: leftover
        )
        let placed = try PhoneCalendar.placeWork(days: days, item: row, startAt: start, endAt: end)
        days = placed.days
        if let index = pack.work.items.firstIndex(where: { $0.id == id }) {
            pack.work.items[index].scheduled_date = String(start.prefix(10))
            pack.work.items[index].updated_at = DayStamp.isoNow()
        }
        pack.calendar.phone_blocks = mergePhoneBlocks(pack.calendar.phone_blocks + [placed.block])
        writeAssembled(monday, days: days, into: &pack)
        pack.calendar.unplaced = PhoneCalendar.unplacedFromWork(
            items: pack.work.items,
            blocks: PhoneCalendar.flattenBlocks(days: pack.calendar.days) + pack.calendar.phone_blocks
        )
        try SyncPack.saveWork(pack.work)
        try SyncPack.saveCalendar(pack.calendar)
        ping(pack)
        return pack
    }

    @discardableResult
    static func parkClockItem(_ item: CalendarItem) throws -> Pack {
        var pack = try current()
        let now = DayStamp.isoNow()
        let blockId = item.itemId ?? item.id
        if let workId = item.work_item_id, let index = pack.work.items.firstIndex(where: { $0.id == workId }) {
            pack.work.items[index].scheduled_date = nil
            pack.work.items[index].updated_at = now
        }
        pack.calendar.days = removeBlock(pack.calendar.days, id: blockId)
        pack.calendar.phone_blocks.removeAll { ($0.itemId ?? $0.id) == blockId }
        pack.calendar.removed_block_ids = uniqueIds(pack.calendar.removed_block_ids + [blockId])
        pack.calendar.unplaced = PhoneCalendar.unplacedFromWork(
            items: pack.work.items,
            blocks: PhoneCalendar.flattenBlocks(days: pack.calendar.days) + pack.calendar.phone_blocks
        )
        if item.work_item_id != nil {
            try SyncPack.saveWork(pack.work)
        }
        try SyncPack.saveCalendar(pack.calendar)
        ping(pack)
        return pack
    }

    @discardableResult
    static func skipClockItem(_ item: CalendarItem) throws -> Pack {
        var pack = try current()
        let markAt = DayStamp.localStamp()
        upsertMark(&pack, id: item.markKey, status: "skipped", at: markAt)
        paintClockStatus(&pack, id: item.markKey, status: "skipped")
        try SyncPack.saveCalendar(pack.calendar)
        ping(pack)
        return pack
    }

    @discardableResult
    static func importICS(_ raw: String) throws -> Pack {
        let events = PhoneCalendar.parseICSEvents(raw)
        guard !events.isEmpty else { throw PackActionError.message("Paste a calendar event (BEGIN:VEVENT).") }
        var pack = try current()
        let weekStart = pack.calendar.week_start ?? pack.calendar.days.first?.date ?? DayStamp.today()
        let weekEnd = pack.calendar.week_end ?? pack.calendar.days.last?.date ?? weekStart
        for event in events {
            pack.calendar.hard_events.removeAll { $0.id == event.id }
            pack.calendar.hard_events.append(event)
            pack.calendar.days = PhoneCalendar.paint(
                days: pack.calendar.days,
                event: event,
                weekStart: PhoneCalendar.mondayOf(weekStart),
                weekEnd: weekEnd
            )
        }
        try SyncPack.saveCalendar(pack.calendar)
        ping(pack)
        return pack
    }

    @discardableResult
    static func addWork(_ raw: String, date: String?, due: String? = nil, estimate: Int? = nil) throws -> Pack {
        let title = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else { throw PackActionError.message("Type a to-do.") }
        var pack = try current()
        let now = DayStamp.isoNow()
        let minutes = estimate ?? PhoneWork.parseMinutesFromTitle(title)
        pack.work.items.insert(newItem(title: title, date: date, due: due, estimate: minutes, now: now), at: 0)
        return try saveWork(pack)
    }

    @discardableResult
    static func assignDate(id: String, date: String?) throws -> Pack {
        var pack = try current()
        guard let index = pack.work.items.firstIndex(where: { $0.id == id }) else {
            throw PackActionError.message("That to-do is gone.")
        }
        pack.work.items[index].scheduled_date = date
        pack.work.items[index].updated_at = DayStamp.isoNow()
        return try saveWork(pack)
    }

    @discardableResult
    static func finishWork(id: String) throws -> Pack {
        var pack = try current()
        guard let index = pack.work.items.firstIndex(where: { $0.id == id }) else {
            throw PackActionError.message("That to-do is gone.")
        }
        let done = pack.work.items[index].status != "done"
        pack.work.items[index].status = done ? "done" : "open"
        pack.work.items[index].finished_at = done ? DayStamp.isoNow() : nil
        pack.work.items[index].updated_at = DayStamp.isoNow()
        return try saveWork(pack)
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

    private static func upsertMark(_ pack: inout Pack, id: String, status: String, at: String) {
        pack.calendar.marks.removeAll { $0.id == id }
        pack.calendar.marks.append(CalendarMark(id: id, status: status, updated_at: at))
    }

    private static func paintClockStatus(_ pack: inout Pack, id: String, status: String) {
        for index in pack.calendar.days.indices {
            for eventIndex in pack.calendar.days[index].events.indices {
                if pack.calendar.days[index].events[eventIndex].markKey == id {
                    pack.calendar.days[index].events[eventIndex].status = status
                }
            }
            for blockIndex in pack.calendar.days[index].blocks.indices {
                if pack.calendar.days[index].blocks[blockIndex].markKey == id {
                    pack.calendar.days[index].blocks[blockIndex].status = status
                }
            }
        }
    }

    private static func ping(_ pack: Pack) {
        WidgetBridge.write(WidgetSnapshot.from(pack: pack, access: SyncPack.usingChosenFolder() ? .iCloudDrive : .needsFolder))
        #if !WIDGET_EXTENSION
        EventAlerts.sync(pack: pack)
        #endif
    }

    private static func newItem(title: String, date: String?, due: String? = nil, estimate: Int? = nil, now: String) -> WorkItem {
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
            due_at: due,
            estimate_minutes: estimate,
            goal_id: nil
        )
    }

    private static func writeAssembled(_ monday: String, days: [CalendarDay], into pack: inout Pack) {
        let sunday = PhoneCalendar.emptyWeek(weekStart: monday, today: "").last?.date ?? monday
        if pack.calendar.week_start == nil || pack.calendar.week_start == monday || pack.calendar.days.isEmpty {
            pack.calendar.days = days
            pack.calendar.week_start = monday
            pack.calendar.week_end = sunday
        }
    }

    private static func mergePhoneBlocks(_ blocks: [CalendarItem]) -> [CalendarItem] {
        var seen: [String: CalendarItem] = [:]
        for block in blocks where (block.source ?? "iphone") == "iphone" {
            seen[block.itemId ?? block.id] = block
        }
        return Array(seen.values).sorted { ($0.start_at ?? "") < ($1.start_at ?? "") }
    }

    private static func uniqueIds(_ ids: [String]) -> [String] {
        var seen = Set<String>()
        var out: [String] = []
        for id in ids where !id.isEmpty && seen.insert(id).inserted {
            out.append(id)
        }
        return out
    }

    private static func removeBlock(_ days: [CalendarDay], id: String) -> [CalendarDay] {
        days.map { day in
            var next = day
            next.blocks = day.blocks.filter { ($0.itemId ?? $0.id) != id }
            next.events = day.events.filter { ($0.itemId ?? $0.id) != id }
            return next
        }
    }

    private static func placeGym(days: [CalendarDay], pack: Pack, monday: String) -> [CalendarDay] {
        var painted = days
        for index in painted.indices {
            let iso = painted[index].date ?? ""
            guard iso >= DayStamp.today() else { continue }
            guard let dayDate = parseDay(iso) else { continue }
            let expected = WorkoutPlan.expectedKinds(on: dayDate, template: pack.workouts.template)
            guard !expected.isEmpty else { continue }
            let already = painted[index].blocks.contains { ($0.kind ?? "") == "workout" }
            let logged = pack.workouts.sessions.contains { $0.local_date == iso }
            if already || logged { continue }
            let label = expected
                .map { id in WorkoutPlan.chipKinds.first(where: { $0.id == id })?.label ?? id }
                .joined(separator: " · ")
            guard let start = PhoneCalendar.findSlot(
                days: painted,
                minutes: 60,
                from: dayDate,
                until: endOfDay(dayDate),
                dayStart: pack.calendar.day_start,
                dayEnd: pack.calendar.day_end
            ) else { continue }
            let block = CalendarItem(
                itemId: UUID().uuidString,
                title: "Gym · \(label)",
                kind: "workout",
                status: "proposed",
                start_at: PhoneCalendar.formatStamp(start.0),
                end_at: PhoneCalendar.formatStamp(start.1),
                work_item_id: nil,
                updated_at: PhoneCalendar.formatStamp(Date()),
                occurrence_date: iso,
                source: "iphone"
            )
            painted[index].blocks.append(block)
            painted[index].blocks.sort { ($0.start_at ?? "") < ($1.start_at ?? "") }
        }
        return painted
    }

    private static func parseDay(_ raw: String) -> Date? {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.date(from: String(raw.prefix(10)))
    }

    private static func endOfDay(_ day: Date) -> Date {
        Calendar.current.date(bySettingHour: 23, minute: 59, second: 0, of: day) ?? day.addingTimeInterval(23 * 3600)
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
