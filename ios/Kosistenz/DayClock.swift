import SwiftUI

/// Awake-window week clock. App target only — the widget keeps DayTimelineView.
struct WeekClockView: View {
    var file: CalendarFile
    var palette: KosistenzPalette

    private var window: (startMin: Int, endMin: Int) {
        PhoneCalendar.clockWindow(dayStart: file.day_start, dayEnd: file.day_end)
    }

    var body: some View {
        let height: CGFloat = 360
        let headerHeight: CGFloat = 44
        VStack(alignment: .leading, spacing: 8) {
            Text("\(PhoneCalendar.formatHHMM(file.day_start))–\(PhoneCalendar.formatHHMM(file.day_end))")
                .font(.caption)
                .foregroundStyle(.secondary)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(alignment: .top, spacing: 6) {
                    VStack(spacing: 6) {
                        Color.clear.frame(height: headerHeight)
                        HourGutter(startMin: window.startMin, endMin: window.endMin, height: height)
                    }
                    ForEach(file.days, id: \.dateValue) { day in
                        DayClockColumn(
                            day: day,
                            startMin: window.startMin,
                            endMin: window.endMin,
                            palette: palette,
                            height: height,
                            headerHeight: headerHeight
                        )
                        .frame(width: 78)
                    }
                }
            }
        }
    }
}

struct DayClockView: View {
    var day: CalendarDay
    var dayStart: String?
    var dayEnd: String?
    var palette: KosistenzPalette
    var height: CGFloat = 360

    private var window: (startMin: Int, endMin: Int) {
        PhoneCalendar.clockWindow(dayStart: dayStart, dayEnd: dayEnd)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            DueChipRow(dues: day.dues, palette: palette)
            HStack(alignment: .top, spacing: 8) {
                HourGutter(startMin: window.startMin, endMin: window.endMin, height: height)
                ClockLane(
                    items: day.events + day.blocks,
                    startMin: window.startMin,
                    endMin: window.endMin,
                    palette: palette,
                    height: height
                )
                .frame(maxWidth: .infinity)
                .clipShape(RoundedRectangle(cornerRadius: 10))
            }
        }
    }
}

private struct DayClockColumn: View {
    var day: CalendarDay
    var startMin: Int
    var endMin: Int
    var palette: KosistenzPalette
    var height: CGFloat
    var headerHeight: CGFloat

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 4) {
                    Text(day.weekday ?? "")
                        .font(.caption.weight(.semibold))
                    Text(dayNumber)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .foregroundStyle(day.is_today == true ? palette.accent : palette.titles)
                DueStrip(dues: day.dues, palette: palette)
            }
            .frame(height: headerHeight, alignment: .topLeading)
            ClockLane(
                items: day.events + day.blocks,
                startMin: startMin,
                endMin: endMin,
                palette: palette,
                height: height
            )
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(day.is_today == true ? palette.accent.opacity(0.7) : palette.widgetBorder, lineWidth: 1)
            )
        }
    }

    private var dayNumber: String {
        String((day.date ?? "").suffix(2))
    }
}

private struct HourGutter: View {
    var startMin: Int
    var endMin: Int
    var height: CGFloat

    var body: some View {
        let span = CGFloat(max(60, endMin - startMin))
        ZStack(alignment: .topTrailing) {
            ForEach(PhoneCalendar.hourMarks(startMin: startMin, endMin: endMin), id: \.self) { mark in
                Text(PhoneCalendar.formatMilitary(mark))
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundStyle(.secondary)
                    .offset(y: CGFloat(mark - startMin) / span * height - 6)
            }
        }
        .frame(width: 36, height: height, alignment: .top)
    }
}

private struct ClockLane: View {
    var items: [CalendarItem]
    var startMin: Int
    var endMin: Int
    var palette: KosistenzPalette
    var height: CGFloat

    private var span: Int { max(60, endMin - startMin) }

    var body: some View {
        ZStack(alignment: .topLeading) {
            palette.pageBg.opacity(0.45)
            ForEach(Array(PhoneCalendar.hourMarks(startMin: startMin, endMin: endMin).dropFirst()), id: \.self) { mark in
                Rectangle()
                    .fill(palette.widgetBorder.opacity(0.55))
                    .frame(height: 1)
                    .offset(y: y(for: mark))
            }
            ForEach(items) { item in
                block(item)
            }
        }
        .frame(maxWidth: .infinity, minHeight: height, maxHeight: height)
        .clipped()
    }

    private func block(_ item: CalendarItem) -> some View {
        let start = PhoneCalendar.minutesOnClock(item.start_at) ?? startMin
        let end = PhoneCalendar.minutesOnClock(item.end_at) ?? (start + 30)
        let duration = max(15, end > start ? end - start : end + 24 * 60 - start)
        var top = CGFloat(start - startMin) / CGFloat(span) * height
        var blockHeight = CGFloat(duration) / CGFloat(span) * height
        if top + blockHeight <= 0 {
            top = 0
            blockHeight = 18
        } else if top >= height {
            blockHeight = 18
            top = height - blockHeight
        } else {
            if top < 0 {
                blockHeight += top
                top = 0
            }
            if top + blockHeight > height {
                blockHeight = height - top
            }
            blockHeight = max(16, blockHeight)
        }
        let kind = (item.kind ?? "").lowercased()
        let color: Color
        if kind == "hard" {
            color = palette.accent
        } else if kind == "workout" {
            color = palette.openNext
        } else if item.status == "done" {
            color = palette.done
        } else {
            color = palette.widgetBorder
        }
        return VStack(alignment: .leading, spacing: 1) {
            Text(DayStamp.clock(item.start_at))
                .font(.system(size: 9, design: .monospaced))
            Text(item.title ?? "")
                .font(.system(size: 10, weight: .semibold))
                .lineLimit(2)
        }
        .foregroundStyle(palette.titles)
        .padding(.horizontal, 4)
        .padding(.vertical, 3)
        .frame(maxWidth: .infinity, minHeight: blockHeight, maxHeight: blockHeight, alignment: .topLeading)
        .background(color.opacity(0.85))
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .offset(y: top)
    }

    private func y(for mark: Int) -> CGFloat {
        CGFloat(mark - startMin) / CGFloat(span) * height
    }
}

struct DueChipRow: View {
    var dues: [DueItem]
    var palette: KosistenzPalette

    var body: some View {
        if dues.isEmpty {
            Text("No dues")
                .font(.caption)
                .foregroundStyle(.secondary)
        } else {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(dues) { due in
                        DueChip(due: due, palette: palette)
                    }
                }
            }
        }
    }
}

private struct DueStrip: View {
    var dues: [DueItem]
    var palette: KosistenzPalette

    var body: some View {
        if dues.isEmpty {
            Color.clear.frame(height: 18)
        } else {
            HStack(spacing: 4) {
                Text("\(dues.count)")
                    .font(.caption2.weight(.bold))
                    .padding(.horizontal, 5)
                    .padding(.vertical, 1)
                    .background(chipColor(dues[0]).opacity(0.85))
                    .clipShape(Capsule())
                Text(shortTitle(dues[0].title))
                    .font(.caption2)
                    .lineLimit(1)
            }
            .foregroundStyle(palette.titles)
        }
    }

    private func chipColor(_ due: DueItem) -> Color {
        if let hue = due.hue {
            return Color(hue: Double(hue) / 360, saturation: 0.45, brightness: 0.62)
        }
        return palette.accent
    }
}

private struct DueChip: View {
    var due: DueItem
    var palette: KosistenzPalette

    var body: some View {
        HStack(spacing: 4) {
            if let course = due.course, !course.isEmpty {
                Text(course)
                    .font(.caption2.weight(.bold))
            }
            Text(shortTitle(due.title))
                .font(.caption)
                .lineLimit(1)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 5)
        .foregroundStyle(palette.titles)
        .background(background.opacity(due.status == "done" ? 0.35 : 0.9))
        .clipShape(Capsule())
        .strikethrough(due.status == "done")
    }

    private var background: Color {
        if let hue = due.hue {
            return Color(hue: Double(hue) / 360, saturation: 0.42, brightness: 0.55)
        }
        return palette.accent
    }
}

private func shortTitle(_ title: String?) -> String {
    let raw = (title ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    guard !raw.isEmpty else { return "Due" }
    let stripped = raw.replacingOccurrences(of: #"\s*\[[^\]]+\]\s*"#, with: " ", options: .regularExpression)
    let compact = stripped.replacingOccurrences(of: #"\s+"#, with: " ", options: .regularExpression)
        .trimmingCharacters(in: .whitespacesAndNewlines)
    return compact.isEmpty ? raw : compact
}

private extension CalendarDay {
    var dateValue: String { date ?? UUID().uuidString }
}
