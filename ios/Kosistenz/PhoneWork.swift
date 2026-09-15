import Foundation

/// Port of phone_work.py. Keep lockstep with tests/test_phone_work.py.
enum PhoneWork {
    static func parseMinutesFromTitle(_ raw: String) -> Int? {
        let text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return nil }
        var hours = 0.0
        var mins = 0.0
        var found = false
        let hourExpr = try? NSRegularExpression(pattern: #"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b"#, options: [.caseInsensitive])
        let minExpr = try? NSRegularExpression(pattern: #"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|min|m)\b"#, options: [.caseInsensitive])
        let ns = text as NSString
        let range = NSRange(location: 0, length: ns.length)
        hourExpr?.enumerateMatches(in: text, options: [], range: range) { match, _, _ in
            guard let match, match.numberOfRanges > 1 else { return }
            hours += Double(ns.substring(with: match.range(at: 1))) ?? 0
            found = true
        }
        var rest = text
        if let hourExpr {
            rest = hourExpr.stringByReplacingMatches(in: text, options: [], range: range, withTemplate: " ")
        }
        let restNS = rest as NSString
        minExpr?.enumerateMatches(in: rest, options: [], range: NSRange(location: 0, length: restNS.length)) { match, _, _ in
            guard let match, match.numberOfRanges > 1 else { return }
            mins += Double(restNS.substring(with: match.range(at: 1))) ?? 0
            found = true
        }
        guard found else { return nil }
        let total = Int((hours * 60 + mins).rounded())
        if total <= 0 { return nil }
        return min(total, 24 * 60)
    }

    static func normalizeFilter(_ raw: String) -> String {
        let key = raw.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if key == "backlog" || key == "allwork" || key == "all" { return "all" }
        if key == "unplaced" || key == "due" { return key }
        return "today"
    }

    static func filterItems(_ items: [WorkItem], kind: String, today: String, unplacedIds: Set<String> = []) -> [WorkItem] {
        let wanted = normalizeFilter(kind)
        let todayIso = String(today.prefix(10))
        var out: [WorkItem] = []
        for item in items {
            let scheduled = String((item.scheduled_date ?? "").prefix(10))
            let due = String((item.due_at ?? "").prefix(10))
            if wanted == "today" {
                if item.status == "done" { continue }
                if scheduled != todayIso { continue }
                out.append(item)
            } else if wanted == "all" {
                if item.status == "done" { continue }
                if !scheduled.isEmpty { continue }
                out.append(item)
            } else if wanted == "unplaced" {
                if unplacedIds.contains(item.id) { out.append(item) }
            } else if wanted == "due" {
                if item.status == "done" || due.isEmpty { continue }
                out.append(item)
            }
        }
        if wanted == "due" {
            return out.sorted { ($0.due_at ?? "") < ($1.due_at ?? "") }
        }
        if wanted == "all" {
            return out.sorted { ($0.updated_at ?? "") > ($1.updated_at ?? "") }
        }
        return out.sorted {
            if ($0.scheduled_date ?? "") != ($1.scheduled_date ?? "") {
                return ($0.scheduled_date ?? "") < ($1.scheduled_date ?? "")
            }
            return $0.title.localizedCaseInsensitiveCompare($1.title) == .orderedAscending
        }
    }
}
