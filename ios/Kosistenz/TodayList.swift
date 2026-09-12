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
        var usedWork = Set<String>()
        var rows: [Entry] = []
        let clockItems = (day?.events ?? []) + (day?.blocks ?? [])
        for item in clockItems.sorted(by: clockOrder) {
            let clockId = item.markKey
            let status = (item.status ?? marked[clockId] ?? "").lowercased()
            if let workId = item.work_item_id, !workId.isEmpty {
                usedWork.insert(workId)
            }
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
        for item in pack.work.items where item.scheduled_date == today {
            if usedWork.contains(item.id) { continue }
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
        return rows.sorted(by: rowOrder)
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

    private static func clockOrder(_ lhs: CalendarItem, _ rhs: CalendarItem) -> Bool {
        if (lhs.start_at ?? "") != (rhs.start_at ?? "") {
            return (lhs.start_at ?? "") < (rhs.start_at ?? "")
        }
        return (lhs.title ?? "").localizedCaseInsensitiveCompare(rhs.title ?? "") == .orderedAscending
    }

    private static func rowOrder(_ lhs: Entry, _ rhs: Entry) -> Bool {
        let leftTime = lhs.startAt ?? "z"
        let rightTime = rhs.startAt ?? "z"
        if leftTime != rightTime { return leftTime < rightTime }
        return lhs.title.localizedCaseInsensitiveCompare(rhs.title) == .orderedAscending
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
