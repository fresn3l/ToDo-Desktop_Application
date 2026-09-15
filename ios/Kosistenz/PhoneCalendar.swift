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

    static func formatStamp(_ date: Date) -> String {
        stamp.string(from: date)
    }

    static func formatDay(_ date: Date) -> String {
        dayStamp.string(from: date)
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

    static let chunkMin = 50
    static let chunkMax = 90
    static let defaultEstimate = 60
    static let weekdayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    static func mondayOf(_ iso: String) -> String {
        guard let day = parseDay(iso) else { return String(iso.prefix(10)) }
        let weekday = pythonWeekday(day)
        let monday = gmt.date(byAdding: .day, value: -weekday, to: gmt.startOfDay(for: day)) ?? day
        return dayStamp.string(from: monday)
    }

    static func emptyWeek(weekStart: String, today: String) -> [CalendarDay] {
        guard let start = parseDay(mondayOf(weekStart)) else { return [] }
        let todayIso = String(today.prefix(10))
        return (0..<7).compactMap { offset -> CalendarDay? in
            guard let day = gmt.date(byAdding: .day, value: offset, to: start) else { return nil }
            let iso = dayStamp.string(from: day)
            return CalendarDay(
                date: iso,
                weekday: weekdayLabels[offset],
                is_today: iso == todayIso,
                events: [],
                blocks: [],
                dues: []
            )
        }
    }

    static func remainingMinutes(estimate: Int?, placed: Int, status: String?) -> Int {
        if (status ?? "").trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == "done" {
            return 0
        }
        let total = estimate ?? 0
        if total <= 0 { return 0 }
        return max(0, total - placed)
    }

    static func spanMinutes(startAt: String?, endAt: String?) -> Int {
        guard let start = parse(startAt), let end = parse(endAt), end > start else { return 0 }
        return max(0, Int(end.timeIntervalSince(start) / 60))
    }

    static func placedMinutes(blocks: [CalendarItem], itemId: String) -> Int {
        let key = itemId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !key.isEmpty else { return 0 }
        return blocks
            .filter { ($0.work_item_id ?? "") == key }
            .reduce(0) { $0 + spanMinutes(startAt: $1.start_at, endAt: $1.end_at) }
    }

    static func flattenBlocks(days: [CalendarDay]) -> [CalendarItem] {
        days.flatMap(\.blocks)
    }

    static func unplacedFromWork(items: [WorkItem], blocks: [CalendarItem]) -> [UnplacedItem] {
        items.compactMap { item -> UnplacedItem? in
            if item.status == "done" { return nil }
            if (item.source ?? "").lowercased() == "calendar" { return nil }
            let leftover = remainingMinutes(
                estimate: item.estimate_minutes,
                placed: placedMinutes(blocks: blocks, itemId: item.id),
                status: item.status
            )
            guard leftover > 0 else { return nil }
            return UnplacedItem(
                itemId: item.id,
                title: item.title,
                scheduled_date: item.scheduled_date,
                due_at: item.due_at,
                estimate_minutes: item.estimate_minutes,
                remaining_minutes: leftover
            )
        }
        .sorted { lhs, rhs in
            let left = lhs.due_at ?? "9999"
            let right = rhs.due_at ?? "9999"
            if left != right { return left < right }
            return (lhs.title ?? "") < (rhs.title ?? "")
        }
    }

    static func chunkMinutes(_ total: Int, chunkMin: Int = chunkMin, chunkMax: Int = chunkMax) -> [Int] {
        var remaining = max(0, total)
        if remaining <= 0 { return [] }
        let low = max(15, chunkMin)
        let high = max(low, chunkMax)
        var out: [Int] = []
        while remaining > 0 {
            if remaining <= high {
                out.append(remaining)
                break
            }
            out.append(high)
            remaining -= high
        }
        return out
    }

    static func findSlot(
        days: [CalendarDay],
        minutes: Int,
        from: Date,
        until: Date,
        dayStart: String?,
        dayEnd: String?
    ) -> (Date, Date)? {
        let need = TimeInterval(max(1, minutes) * 60)
        let byDate = Dictionary(uniqueKeysWithValues: days.compactMap { day -> (String, CalendarDay)? in
            guard let iso = day.date else { return nil }
            return (iso, day)
        })
        var cursor = gmt.startOfDay(for: from)
        let last = gmt.startOfDay(for: until)
        while cursor <= last {
            let iso = dayStamp.string(from: cursor)
            guard let row = byDate[iso] else {
                cursor = gmt.date(byAdding: .day, value: 1, to: cursor) ?? last.addingTimeInterval(86_400)
                continue
            }
            let startBound = combine(day: cursor, hhmm: dayStart, fallback: "05:30")
            var endBound = combine(day: cursor, hhmm: dayEnd, fallback: "21:30")
            if gmt.startOfDay(for: until) == cursor {
                endBound = min(endBound, until)
            }
            var windowStart = startBound
            if gmt.startOfDay(for: from) == cursor {
                windowStart = max(startBound, from)
            }
            if endBound <= windowStart {
                cursor = gmt.date(byAdding: .day, value: 1, to: cursor) ?? last.addingTimeInterval(86_400)
                continue
            }
            let busy = busyIntervals(day: row, startBound: startBound, endBound: endBound)
            for (gapStart, gapEnd) in gaps(busy: busy, windowStart: windowStart, windowEnd: endBound) {
                if gapEnd.timeIntervalSince(gapStart) >= need {
                    return (gapStart, gapStart.addingTimeInterval(need))
                }
            }
            cursor = gmt.date(byAdding: .day, value: 1, to: cursor) ?? last.addingTimeInterval(86_400)
        }
        return nil
    }

    static func clearProposed(_ days: [CalendarDay]) -> (days: [CalendarDay], removed: [String]) {
        var removed: [String] = []
        let painted = days.map { day -> CalendarDay in
            var next = day
            var kept: [CalendarItem] = []
            for block in day.blocks {
                let status = (block.status ?? "").lowercased()
                let kind = (block.kind ?? "").lowercased()
                if status == "proposed" && kind != "focus" {
                    if let id = block.itemId, !id.isEmpty { removed.append(id) }
                    else { removed.append(block.id) }
                    continue
                }
                kept.append(block)
            }
            next.blocks = kept
            return next
        }
        return (painted, removed)
    }

    static func fillWeek(
        days: [CalendarDay],
        items: [UnplacedItem],
        dayStart: String?,
        dayEnd: String?,
        now: Date = Date()
    ) -> (days: [CalendarDay], placed: [CalendarItem], removed: [String]) {
        var (painted, removed) = clearProposed(days)
        guard let first = painted.first?.date, let last = painted.last?.date,
              let start = parseDay(first), let end = parseDay(last) else {
            return (painted, [], removed)
        }
        let windowBegin = max(now, start)
        var clock = flattenBlocks(days: painted)
        var placed: [CalendarItem] = []
        for item in items {
            let workId = item.itemId ?? ""
            var leftover = remainingMinutes(
                estimate: item.estimate_minutes,
                placed: placedMinutes(blocks: clock, itemId: workId),
                status: nil
            )
            if leftover <= 0 { leftover = item.remaining_minutes ?? 0 }
            if leftover <= 0 { continue }
            var until = gmt.date(bySettingHour: 23, minute: 59, second: 0, of: end) ?? end
            var fromDt = windowBegin
            if let scheduled = item.scheduled_date, scheduled.count >= 10, let pinned = parseDay(scheduled) {
                if pinned < start || pinned > end { continue }
                fromDt = max(windowBegin, pinned)
                until = min(until, combine(day: pinned, hhmm: dayEnd, fallback: "21:30"))
            }
            if let dueRaw = item.due_at, let due = parse(dueRaw) {
                until = min(until, due)
            }
            let chunks = leftover <= chunkMax ? [leftover] : chunkMinutes(leftover)
            for chunk in chunks {
                guard let slot = findSlot(
                    days: painted,
                    minutes: chunk,
                    from: fromDt,
                    until: until,
                    dayStart: dayStart,
                    dayEnd: dayEnd
                ) else { break }
                let block = clockBlock(
                    id: UUID().uuidString,
                    title: item.title ?? "",
                    start: slot.0,
                    end: slot.1,
                    workItemId: workId.isEmpty ? nil : workId,
                    kind: "work",
                    now: now
                )
                painted = appendBlock(painted, block: block)
                clock.append(block)
                placed.append(block)
            }
        }
        return (painted, placed, removed)
    }

    static func placeWork(
        days: [CalendarDay],
        item: UnplacedItem,
        startAt: String,
        endAt: String = "",
        now: Date = Date()
    ) throws -> (days: [CalendarDay], block: CalendarItem) {
        guard let start = parse(startAt) else {
            throw PackActionError.message("Use a 24-hour time like 0930 or 09:30.")
        }
        let leftover = item.remaining_minutes ?? item.estimate_minutes ?? defaultEstimate
        let duration = max(15, min(leftover > 0 ? leftover : defaultEstimate, chunkMax))
        var end = parse(endAt) ?? start.addingTimeInterval(TimeInterval(duration * 60))
        if end <= start {
            end = start.addingTimeInterval(TimeInterval(duration * 60))
        }
        let hours = end.timeIntervalSince(start) / 3600
        if hours > 12 {
            throw PackActionError.message("Blocks longer than 12 hours need to be split")
        }
        let block = clockBlock(
            id: UUID().uuidString,
            title: item.title ?? "",
            start: start,
            end: end,
            workItemId: item.itemId,
            kind: "work",
            now: now
        )
        return (appendBlock(days, block: block), block)
    }

    static func duesForDay(items: [WorkItem], iso: String) -> [DueItem] {
        let day = String(iso.prefix(10))
        return items.compactMap { item -> DueItem? in
            let due = String((item.due_at ?? "").prefix(10))
            guard due == day, item.status != "done" else { return nil }
            return DueItem(
                itemId: item.id,
                title: item.title,
                due_at: item.due_at,
                course: nil,
                estimate_minutes: item.estimate_minutes,
                status: item.status,
                hue: nil
            )
        }
    }

    static func assembleWeek(
        weekStart: String,
        today: String,
        packedDays: [CalendarDay],
        hardEvents: [HardEvent],
        phoneBlocks: [CalendarItem],
        workItems: [WorkItem]
    ) -> [CalendarDay] {
        let start = mondayOf(weekStart)
        guard let last = parseDay(start).flatMap({ gmt.date(byAdding: .day, value: 6, to: $0) }) else {
            return emptyWeek(weekStart: start, today: today)
        }
        let end = dayStamp.string(from: last)
        let packedBy = Dictionary(uniqueKeysWithValues: packedDays.compactMap { day -> (String, CalendarDay)? in
            guard let iso = day.date else { return nil }
            return (iso, day)
        })
        var days = emptyWeek(weekStart: start, today: today)
        let packedThisWeek = packedDays.contains { $0.date == start }
        if packedThisWeek {
            for index in days.indices {
                let iso = days[index].date ?? ""
                if let src = packedBy[iso] {
                    days[index].events = src.events
                    days[index].blocks = src.blocks
                    days[index].dues = src.dues.isEmpty ? duesForDay(items: workItems, iso: iso) : src.dues
                } else {
                    days[index].dues = duesForDay(items: workItems, iso: iso)
                }
            }
            for block in phoneBlocks {
                days = appendBlock(days, block: block)
            }
            return days
        }
        for index in days.indices {
            days[index].dues = duesForDay(items: workItems, iso: days[index].date ?? "")
        }
        for event in hardEvents {
            days = paint(days: days, event: event, weekStart: start, weekEnd: end)
        }
        for block in phoneBlocks {
            days = appendBlock(days, block: block)
        }
        return days
    }

    static func monthWeeks(
        year: Int,
        month: Int,
        today: String,
        eventDates: [String: Int],
        blockDates: [String: Int],
        dueDates: [String: Int]
    ) -> [[MonthCell]] {
        guard let first = gmt.date(from: DateComponents(calendar: gmt, year: year, month: month, day: 1)) else {
            return []
        }
        let weekday = pythonWeekday(first)
        var cursor = gmt.date(byAdding: .day, value: -weekday, to: gmt.startOfDay(for: first)) ?? first
        let todayIso = String(today.prefix(10))
        var weeks: [[MonthCell]] = []
        for _ in 0..<6 {
            var week: [MonthCell] = []
            for _ in 0..<7 {
                let iso = dayStamp.string(from: cursor)
                let dayNum = gmt.component(.day, from: cursor)
                let inMonth = gmt.component(.month, from: cursor) == month
                let eventCount = eventDates[iso] ?? 0
                let blockCount = blockDates[iso] ?? 0
                let dueCount = dueDates[iso] ?? 0
                week.append(
                    MonthCell(
                        date: iso,
                        day: dayNum,
                        inMonth: inMonth,
                        isToday: iso == todayIso,
                        eventCount: eventCount,
                        blockCount: blockCount,
                        dueCount: dueCount
                    )
                )
                cursor = gmt.date(byAdding: .day, value: 1, to: cursor) ?? cursor.addingTimeInterval(86_400)
            }
            weeks.append(week)
        }
        return weeks
    }

    static func parseICSDatetime(_ raw: String) -> Date? {
        let digits = raw.filter(\.isNumber)
        guard digits.count >= 8 else { return parse(raw) }
        let year = Int(digits.prefix(4)) ?? 0
        let month = Int(digits.dropFirst(4).prefix(2)) ?? 0
        let day = Int(digits.dropFirst(6).prefix(2)) ?? 0
        let hour = digits.count >= 10 ? Int(digits.dropFirst(8).prefix(2)) ?? 0 : 0
        let minute = digits.count >= 12 ? Int(digits.dropFirst(10).prefix(2)) ?? 0 : 0
        let second = digits.count >= 14 ? Int(digits.dropFirst(12).prefix(2)) ?? 0 : 0
        return gmt.date(from: DateComponents(calendar: gmt, timeZone: gmt.timeZone, year: year, month: month, day: day, hour: hour, minute: minute, second: second))
    }

    static func parseICSEvents(_ text: String) -> [HardEvent] {
        let unfolded = text
            .replacingOccurrences(of: "\r\n ", with: "")
            .replacingOccurrences(of: "\n ", with: "")
            .replacingOccurrences(of: "\r\n", with: "\n")
        let chunks = unfolded.components(separatedBy: "BEGIN:VEVENT").dropFirst()
        let byDay = ["MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6]
        var out: [HardEvent] = []
        for chunk in chunks {
            let body = chunk.components(separatedBy: "END:VEVENT").first ?? chunk
            var fields: [String: String] = [:]
            for line in body.split(separator: "\n") {
                guard let colon = line.firstIndex(of: ":") else { continue }
                let key = String(line[..<colon]).split(separator: ";").first.map(String.init)?.uppercased() ?? ""
                fields[key] = String(line[line.index(after: colon)...]).trimmingCharacters(in: .whitespacesAndNewlines)
            }
            let title = (fields["SUMMARY"] ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            guard !title.isEmpty, let start = parseICSDatetime(fields["DTSTART"] ?? "") else { continue }
            var end = parseICSDatetime(fields["DTEND"] ?? "") ?? start.addingTimeInterval(50 * 60)
            if end <= start { end = start.addingTimeInterval(50 * 60) }
            if end.timeIntervalSince(start) / 3600 > 12 { continue }
            var weekdays: [Int] = []
            let rrule = fields["RRULE"] ?? ""
            if rrule.uppercased().contains("FREQ=WEEKLY") {
                for part in rrule.split(separator: ";") {
                    if part.uppercased().hasPrefix("BYDAY=") {
                        let raw = part.split(separator: "=", maxSplits: 1).last.map(String.init) ?? ""
                        for token in raw.split(separator: ",") {
                            let code = String(String(token).trimmingCharacters(in: .whitespaces).uppercased().prefix(2))
                            if let day = byDay[code], !weekdays.contains(day) {
                                weekdays.append(day)
                            }
                        }
                    }
                }
            }
            out.append(
                HardEvent(
                    id: UUID().uuidString,
                    title: String(title.prefix(200)),
                    start_at: stamp.string(from: start),
                    end_at: stamp.string(from: end),
                    weekdays: weekdays,
                    source: "iphone"
                )
            )
        }
        return out
    }

    private static func clockBlock(
        id: String,
        title: String,
        start: Date,
        end: Date,
        workItemId: String?,
        kind: String,
        now: Date
    ) -> CalendarItem {
        CalendarItem(
            itemId: id,
            title: title,
            kind: kind,
            status: "proposed",
            start_at: stamp.string(from: start),
            end_at: stamp.string(from: end),
            work_item_id: workItemId,
            updated_at: stamp.string(from: now),
            occurrence_date: dayStamp.string(from: start),
            source: "iphone"
        )
    }

    private static func appendBlock(_ days: [CalendarDay], block: CalendarItem) -> [CalendarDay] {
        let iso = String((block.start_at ?? "").prefix(10))
        var painted = days
        guard let index = painted.firstIndex(where: { $0.date == iso }) else { return painted }
        var blocks = painted[index].blocks.filter { $0.itemId != block.itemId }
        blocks.append(block)
        blocks.sort { ($0.start_at ?? "") < ($1.start_at ?? "") }
        painted[index].blocks = blocks
        return painted
    }

    private static func busyIntervals(
        day: CalendarDay,
        startBound: Date,
        endBound: Date
    ) -> [(Date, Date)] {
        var busy: [(Date, Date)] = []
        for item in day.events + day.blocks {
            let kind = (item.kind ?? "").lowercased()
            let status = (item.status ?? "").lowercased()
            if kind != "focus" && status == "skipped" { continue }
            guard let start = parse(item.start_at), let end = parse(item.end_at) else { continue }
            let lo = max(start, startBound)
            let hi = min(end, endBound)
            if hi > lo { busy.append((lo, hi)) }
        }
        busy.sort { $0.0 < $1.0 }
        var merged: [(Date, Date)] = []
        for span in busy {
            if let last = merged.last, span.0 <= last.1 {
                merged[merged.count - 1] = (last.0, max(last.1, span.1))
            } else {
                merged.append(span)
            }
        }
        return merged
    }

    private static func gaps(
        busy: [(Date, Date)],
        windowStart: Date,
        windowEnd: Date
    ) -> [(Date, Date)] {
        var out: [(Date, Date)] = []
        var cursor = windowStart
        for (start, end) in busy {
            if start > cursor { out.append((cursor, start)) }
            cursor = max(cursor, end)
        }
        if windowEnd > cursor { out.append((cursor, windowEnd)) }
        return out.filter { $0.1.timeIntervalSince($0.0) >= 15 * 60 }
    }

    private static func combine(day: Date, hhmm: String?, fallback: String) -> Date {
        let parsed = parseHHMM(hhmm, fallback: fallback)
        return gmt.date(bySettingHour: parsed.hour, minute: parsed.minute, second: 0, of: gmt.startOfDay(for: day)) ?? day
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
            end_at: stamp.string(from: occEnd),
            occurrence_date: dayStamp.string(from: day)
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
