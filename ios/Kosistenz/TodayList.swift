import Foundation

/// Today tab rows: timed clock items plus dated work that is not already on the clock.
enum TodayList {
    struct Entry: Identifiable, Equatable {
        enum Kind: String {
            case clock
            case task
        }

        var id: String
        var title: String
        var startAt: String?
        var endAt: String?
        var done: Bool
        var kind: Kind
        var workId: String?
        var clockId: String?

        var timeLabel: String {
            let start = DayStamp.clock(startAt)
            let end = DayStamp.clock(endAt)
            if start.isEmpty { return "Today" }
            if end.isEmpty { return start }
            return "\(start)–\(end)"
        }
    }

    static func entries(pack: Pack, today: String) -> [Entry] {
        let day = pack.calendar.days.first(where: { $0.date == today })
        var marked: [String: String] = [:]
        for mark in pack.calendar.marks {
            marked[mark.id] = mark.status.lowercased()
        }
        var clockByKey: [String: CalendarItem] = [:]
        func put(_ item: CalendarItem) {
            clockByKey[item.markKey] = item
        }
        for item in day?.events ?? [] where (item.kind ?? "").lowercased() == "hard" {
            put(item)
        }
        for event in pack.calendar.hard_events where live(id: event.id, updated: event.updated_at, deletions: pack.calendar.deleted) {
            for item in PhoneCalendar.expandHardEvent(event, weekStart: today, weekEnd: today) {
                put(item)
            }
        }
        var rows: [Entry] = []
        for item in clockByKey.values.sorted(by: clockOrder) {
            let eventId = item.itemId ?? ""
            let event = pack.calendar.hard_events.first(where: { $0.id == eventId })
            if !live(id: eventId, updated: event?.updated_at ?? item.updated_at, deletions: pack.calendar.deleted) {
                continue
            }
            let clockId = item.markKey
            let status = (item.status ?? marked[clockId] ?? marked[item.itemId ?? ""] ?? "").lowercased()
            rows.append(
                Entry(
                    id: "clock-\(clockId)",
                    title: item.title ?? "",
                    startAt: item.start_at,
                    endAt: item.end_at,
                    done: status == "done" || status == "skipped",
                    kind: .clock,
                    workId: item.work_item_id,
                    clockId: clockId
                )
            )
        }
        let tasks = pack.work.items
            .filter { $0.scheduled_date == today && $0.source != "calendar" }
            .filter { live(id: $0.id, updated: $0.updated_at, deletions: pack.work.deleted ?? []) }
            .sorted { $0.title.localizedCaseInsensitiveCompare($1.title) == .orderedAscending }
        for item in tasks {
            rows.append(
                Entry(
                    id: "task-\(item.id)",
                    title: item.title,
                    startAt: nil,
                    endAt: nil,
                    done: item.status == "done",
                    kind: .task,
                    workId: item.id,
                    clockId: nil
                )
            )
        }
        return rows
    }

    static func upcomingClockItems(pack: Pack, now: Date = Date()) -> [CalendarItem] {
        var marked: [String: String] = [:]
        for mark in pack.calendar.marks {
            marked[mark.id] = mark.status.lowercased()
        }
        var items: [CalendarItem] = []
        for day in pack.calendar.days {
            for item in (day.events + day.blocks) {
                let status = (item.status ?? marked[item.markKey] ?? "").lowercased()
                if status == "done" || status == "skipped" { continue }
                guard let start = parseLocal(item.start_at), start > now else { continue }
                items.append(item)
            }
        }
        return items
    }

    static func live(id: String, updated: String?, deletions: [PackDeletion]) -> Bool {
        guard !id.isEmpty, let tomb = deletions.first(where: { $0.id == id }) else { return true }
        return (updated ?? "") > tomb.deleted_at
    }

    private static func clockOrder(_ lhs: CalendarItem, _ rhs: CalendarItem) -> Bool {
        if (lhs.start_at ?? "") != (rhs.start_at ?? "") {
            return (lhs.start_at ?? "") < (rhs.start_at ?? "")
        }
        return (lhs.title ?? "").localizedCaseInsensitiveCompare(rhs.title ?? "") == .orderedAscending
    }

    static func parseLocal(_ raw: String?) -> Date? {
        guard let raw, raw.count >= 19 else { return nil }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter.date(from: String(raw.prefix(19)))
    }
}
