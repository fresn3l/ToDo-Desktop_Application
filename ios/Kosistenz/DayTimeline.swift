import Foundation
import SwiftUI

/// Port of phone_today.py. Keep lockstep with tests/test_iphone_today_timeline.py.
enum DayTimeline {
    struct Block: Identifiable, Equatable {
        var id: String
        var title: String
        var kind: String
        var status: String
        var startAt: String?
        var endAt: String?
        var minutes: Int
        var label: String
        var isNow: Bool

        var height: CGFloat {
            CGFloat(min(148, max(56, minutes)))
        }
    }

    static func blocks(events: [CalendarItem], packed: [CalendarItem], now: Date = Date()) -> [Block] {
        (events + packed)
            .sorted(by: sortBefore)
            .map { item in
                let minutes = durationMinutes(startAt: item.start_at, endAt: item.end_at)
                return Block(
                    id: item.id,
                    title: item.title ?? "",
                    kind: item.kind ?? "",
                    status: item.status ?? "",
                    startAt: item.start_at,
                    endAt: item.end_at,
                    minutes: minutes,
                    label: kindLabel(kind: item.kind, status: item.status),
                    isNow: isNow(startAt: item.start_at, endAt: item.end_at, now: now)
                )
            }
    }

    static func durationMinutes(startAt: String?, endAt: String?) -> Int {
        guard let start = parse(startAt) else { return 30 }
        guard let end = parse(endAt), end > start else { return 30 }
        return max(1, Int(end.timeIntervalSince(start) / 60))
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

    static func clock(_ raw: String?) -> String {
        DayStamp.clock(raw)
    }

    private static func sortBefore(_ lhs: CalendarItem, _ rhs: CalendarItem) -> Bool {
        let leftMissing = (lhs.start_at ?? "").isEmpty
        let rightMissing = (rhs.start_at ?? "").isEmpty
        if leftMissing != rightMissing { return !leftMissing }
        if (lhs.start_at ?? "") != (rhs.start_at ?? "") {
            return (lhs.start_at ?? "") < (rhs.start_at ?? "")
        }
        return (lhs.title ?? "").localizedCaseInsensitiveCompare(rhs.title ?? "") == .orderedAscending
    }

    private static func isNow(startAt: String?, endAt: String?, now: Date) -> Bool {
        guard let start = parse(startAt) else { return false }
        if let end = parse(endAt) {
            return start <= now && now < end
        }
        return start <= now
    }

    private static func parse(_ iso: String?) -> Date? {
        let raw = (iso ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else { return nil }
        if let date = isoFractional.date(from: raw) { return date }
        if let date = isoBasic.date(from: raw) { return date }
        return localNaive.date(from: String(raw.prefix(19)))
    }

    private static let isoFractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let isoBasic: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    private static let localNaive: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter
    }()
}

struct DayTimelineView: View {
    var blocks: [DayTimeline.Block]
    var palette: KosistenzPalette

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(blocks) { block in
                HStack(alignment: .top, spacing: 10) {
                    VStack(alignment: .trailing, spacing: 2) {
                        Text(DayTimeline.clock(block.startAt))
                            .monospacedDigit()
                        Text(DayTimeline.clock(block.endAt))
                            .monospacedDigit()
                            .foregroundStyle(.secondary)
                    }
                    .font(.caption)
                    .frame(width: 44, alignment: .trailing)
                    RoundedRectangle(cornerRadius: 3)
                        .fill(barColor(block))
                        .frame(width: 5, height: block.height)
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(block.title.isEmpty ? "Untitled" : block.title)
                                .font(.headline)
                                .foregroundStyle(palette.titles)
                            if block.isNow {
                                Text("Now")
                                    .font(.caption2.weight(.semibold))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(palette.accent.opacity(0.25))
                                    .clipShape(Capsule())
                            }
                        }
                        Text("\(block.label) · \(block.minutes)m")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer(minLength: 0)
                }
                .frame(minHeight: block.height, alignment: .top)
                .padding(.vertical, 4)
            }
        }
    }

    private func barColor(_ block: DayTimeline.Block) -> Color {
        let kind = block.kind.lowercased()
        if kind == "hard" { return palette.accent }
        if kind == "workout" { return palette.openNext }
        if block.status == "done" { return palette.done }
        return palette.widgetBorder
    }
}
