import Foundation

/// Port of phone_calendar.py. Keep lockstep with tests/test_phone_calendar.py.
enum PhoneCalendar {
    static func parseHHMM(_ raw: String?, fallback: String = "05:30") -> (hour: Int, minute: Int) {
        var text = (raw ?? fallback).trimmingCharacters(in: .whitespacesAndNewlines)
        text = text.replacingOccurrences(of: ".", with: ":")
        text = text.replacingOccurrences(of: " ", with: "")
        if text.allSatisfy(\.isNumber), (3...4).contains(text.count) {
            text = String(repeating: "0", count: 4 - text.count) + text
            let index = text.index(text.startIndex, offsetBy: 2)
            text = "\(text[..<index]):\(text[index...])"
        }
        let parts = text.split(separator: ":")
        let hour = Int(parts.first.map(String.init) ?? "") ?? 5
        let minute = parts.count > 1 ? Int(String(parts[1])) ?? 0 : 0
        return (max(0, min(23, hour)), max(0, min(59, minute)))
    }

    static func clockWindow(dayStart: String?, dayEnd: String?) -> (startMin: Int, endMin: Int) {
        let start = parseHHMM(dayStart, fallback: "05:30")
        let end = parseHHMM(dayEnd, fallback: "21:30")
        let startMin = start.hour * 60 + start.minute
        var endMin = end.hour * 60 + end.minute
        if endMin <= startMin { endMin = startMin + 60 }
        return (startMin, endMin)
    }

    static func kindLabel(kind: String?, status: String?) -> String {
        let raw = (kind ?? "").trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let label: String
        if raw == "hard" {
            label = "Event"
        } else if raw == "workout" {
            label = "Gym"
        } else {
            label = "Work"
        }
        let state = (status ?? "").trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if ["locked", "done", "skipped"].contains(state) {
            return "\(label) · \(state)"
        }
        return label
    }

    static func formatHHMM(_ raw: String?) -> String {
        let parsed = parseHHMM(raw)
        return String(format: "%02d:%02d", parsed.hour, parsed.minute)
    }

    static func formatMilitary(_ minutes: Int) -> String {
        let wrapped = ((minutes % (24 * 60)) + 24 * 60) % (24 * 60)
        return String(format: "%02d:%02d", wrapped / 60, wrapped % 60)
    }

    static func hourMarks(startMin: Int, endMin: Int) -> [Int] {
        var marks = [startMin]
        var tick = (startMin / 60) * 60 + 60
        while tick < endMin {
            marks.append(tick)
            tick += 60
        }
        return marks
    }

    static func minutesOnClock(_ iso: String?) -> Int? {
        guard let raw = iso, raw.count >= 16 else { return nil }
        let slice = String(raw.dropFirst(11).prefix(5))
        let parts = slice.split(separator: ":")
        guard parts.count == 2, let hour = Int(parts[0]), let minute = Int(parts[1]) else { return nil }
        return hour * 60 + minute
    }

    static func combine(date: String, time: String) throws -> String {
        let day = String(date.prefix(10))
        guard day.count == 10 else { throw PackActionError.message("Pick a date.") }
        let parsed = parseHHMM(time, fallback: "")
        if time.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            throw PackActionError.message("Use a 24-hour time like 0930 or 09:30.")
        }
        return String(format: "%@T%02d:%02d:00", day, parsed.hour, parsed.minute)
    }

    static func expandHardEvent(_ event: HardEvent, weekStart: String, weekEnd: String) -> [CalendarItem] {
        guard let start = parse(event.start_at), let end = parse(event.end_at), end > start else { return [] }
        guard let first = parseDay(weekStart), let last = parseDay(weekEnd) else { return [] }
        let duration = end.timeIntervalSince(start)
        var allowed: [Int] = []
        for day in event.weekdays {
            if (0...6).contains(day), !allowed.contains(day) { allowed.append(day) }
        }
        if !allowed.isEmpty {
            var out: [CalendarItem] = []
            var cursor = first
            while cursor <= last {
                if allowed.contains(pythonWeekday(cursor)), gmt.startOfDay(for: cursor) >= gmt.startOfDay(for: start) {
                    let occStart = combine(day: cursor, timeFrom: start)
                    let occEnd = occStart.addingTimeInterval(duration)
                    out.append(contentsOf: splitOvernight(id: event.id, title: event.title, start: occStart, end: occEnd, weekStart: first, weekEnd: last))
                }
                cursor = gmt.date(byAdding: .day, value: 1, to: cursor) ?? last.addingTimeInterval(86_400)
            }
            return out
        }
        var lastDay = gmt.startOfDay(for: end)
        if isMidnight(end), lastDay > gmt.startOfDay(for: start) {
            lastDay = gmt.date(byAdding: .day, value: -1, to: lastDay) ?? lastDay
        }
        let startDay = gmt.startOfDay(for: start)
        var cursor = max(first, startDay)
        let stop = min(last, lastDay)
        var out: [CalendarItem] = []
        while cursor <= stop {
            if let occ = occurrence(id: event.id, title: event.title, start: start, end: end, day: cursor) {
                out.append(occ)
            }
            cursor = gmt.date(byAdding: .day, value: 1, to: cursor) ?? stop.addingTimeInterval(86_400)
        }
        return out
    }

    static func paint(days: [CalendarDay], event: HardEvent, weekStart: String, weekEnd: String) -> [CalendarDay] {
        var painted = days
        for occ in expandHardEvent(event, weekStart: weekStart, weekEnd: weekEnd) {
            let date = String((occ.start_at ?? "").prefix(10))
            guard let index = painted.firstIndex(where: { $0.date == date }) else { continue }
            var events = painted[index].events
            events.removeAll { $0.itemId == occ.itemId && $0.start_at == occ.start_at }
            events.append(occ)
            events.sort { ($0.start_at ?? "") < ($1.start_at ?? "") }
            painted[index].events = events
        }
        return painted
    }

    private static func splitOvernight(
        id: String,
        title: String,
        start: Date,
        end: Date,
        weekStart: Date,
        weekEnd: Date
    ) -> [CalendarItem] {
        var lastDay = gmt.startOfDay(for: end)
        if isMidnight(end), lastDay > gmt.startOfDay(for: start) {
            lastDay = gmt.date(byAdding: .day, value: -1, to: lastDay) ?? lastDay
        }
        var cursor = gmt.startOfDay(for: start)
        var rows: [CalendarItem] = []
        while cursor <= lastDay {
            if cursor >= weekStart && cursor <= weekEnd,
               let occ = occurrence(id: id, title: title, start: start, end: end, day: cursor) {
                rows.append(occ)
            }
            cursor = gmt.date(byAdding: .day, value: 1, to: cursor) ?? lastDay.addingTimeInterval(86_400)
        }
        return rows
    }

    private static func occurrence(id: String, title: String, start: Date, end: Date, day: Date) -> CalendarItem? {
        var lastDay = gmt.startOfDay(for: end)
        if isMidnight(end), lastDay > gmt.startOfDay(for: start) {
            lastDay = gmt.date(byAdding: .day, value: -1, to: lastDay) ?? lastDay
        }
        let startDay = gmt.startOfDay(for: start)
        if day < startDay || day > lastDay { return nil }
        let occStart = day == startDay ? start : day
        let occEnd: Date
        if day < lastDay {
            occEnd = gmt.date(byAdding: .day, value: 1, to: day) ?? end
        } else {
            occEnd = end
        }
        if occEnd <= occStart { return nil }
        return CalendarItem(
            itemId: id,
            title: title,
            kind: "hard",
            status: "locked",
            start_at: stamp.string(from: occStart),
            end_at: stamp.string(from: occEnd)
        )
    }

    private static func parse(_ iso: String) -> Date? {
        let raw = iso.trimmingCharacters(in: .whitespacesAndNewlines)
        if let date = stamp.date(from: String(raw.prefix(19))) { return date }
        return nil
    }

    private static func parseDay(_ raw: String) -> Date? {
        dayStamp.date(from: String(raw.prefix(10)))
    }

    private static func pythonWeekday(_ date: Date) -> Int {
        let weekday = gmt.component(.weekday, from: date)
        return (weekday + 5) % 7
    }

    private static func combine(day: Date, timeFrom: Date) -> Date {
        let hour = gmt.component(.hour, from: timeFrom)
        let minute = gmt.component(.minute, from: timeFrom)
        let second = gmt.component(.second, from: timeFrom)
        return gmt.date(bySettingHour: hour, minute: minute, second: second, of: gmt.startOfDay(for: day)) ?? day
    }

    private static func isMidnight(_ date: Date) -> Bool {
        gmt.component(.hour, from: date) == 0
            && gmt.component(.minute, from: date) == 0
            && gmt.component(.second, from: date) == 0
    }

    private static var gmt: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }

    private static let stamp: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter
    }()

    private static let dayStamp: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()
}
