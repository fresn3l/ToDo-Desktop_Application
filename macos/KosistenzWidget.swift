import SwiftUI
import WidgetKit

struct Snapshot: Codable {
    var date: String
    var openCount: Int
    var titles: [String]
    var workoutLogged: Bool
    var journalStreak: Int
    var journalToday: Bool
    var todayEmpty: Bool
    var activeTitle: String?
    var summary: String
    var stale: Bool = false

    static let placeholder = Snapshot(
        date: "",
        openCount: 0,
        titles: [],
        workoutLogged: false,
        journalStreak: 0,
        journalToday: false,
        todayEmpty: true,
        activeTitle: nil,
        summary: "Open Kosistenz",
        stale: true
    )

    static func parse(_ json: [String: Any], stale: Bool = false) -> Snapshot {
        Snapshot(
            date: json["date"] as? String ?? "",
            openCount: intValue(json, "open_count"),
            titles: json["titles"] as? [String] ?? [],
            workoutLogged: boolValue(json, "workout_logged"),
            journalStreak: intValue(json, "journal_streak"),
            journalToday: boolValue(json, "journal_today"),
            todayEmpty: boolValue(json, "today_empty"),
            activeTitle: json["active_title"] as? String,
            summary: json["summary"] as? String ?? "",
            stale: stale
        )
    }
}

private func intValue(_ json: [String: Any], _ key: String) -> Int {
    if let n = json[key] as? Int { return n }
    if let n = json[key] as? NSNumber { return n.intValue }
    return 0
}

private func boolValue(_ json: [String: Any], _ key: String) -> Bool {
    if let n = json[key] as? Bool { return n }
    if let n = json[key] as? NSNumber { return n.boolValue }
    return false
}

struct TodayEntry: TimelineEntry {
    let date: Date
    let snapshot: Snapshot

    static let placeholder = TodayEntry(date: Date(), snapshot: .placeholder)
}

struct KosistenzProvider: TimelineProvider {
    func placeholder(in context: Context) -> TodayEntry {
        .placeholder
    }

    func getSnapshot(in context: Context, completion: @escaping (TodayEntry) -> Void) {
        completion(loadEntry())
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<TodayEntry>) -> Void) {
        let entry = loadEntry()
        let next = Calendar.current.date(byAdding: .minute, value: 15, to: Date()) ?? Date().addingTimeInterval(900)
        completion(Timeline(entries: [entry], policy: .after(next)))
    }

    private func loadEntry() -> TodayEntry {
        if let live = fetchLive() {
            cache(live)
            return TodayEntry(date: Date(), snapshot: live)
        }
        if let cached = loadCache() {
            var stale = cached
            stale.stale = true
            return TodayEntry(date: Date(), snapshot: stale)
        }
        return .placeholder
    }

    private func fetchLive() -> Snapshot? {
        for port in 18741...18750 {
            guard let url = URL(string: "http://127.0.0.1:\(port)/api/widget") else { continue }
            var request = URLRequest(url: url, timeoutInterval: 1.2)
            request.httpMethod = "GET"
            var result: Snapshot?
            let sem = DispatchSemaphore(value: 0)
            URLSession.shared.dataTask(with: request) { data, response, _ in
                defer { sem.signal() }
                guard let data,
                      let http = response as? HTTPURLResponse,
                      (200..<300).contains(http.statusCode),
                      let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
                else { return }
                result = Snapshot.parse(json)
            }.resume()
            _ = sem.wait(timeout: .now() + 1.4)
            if let result { return result }
        }
        return nil
    }

    private func cache(_ snapshot: Snapshot) {
        if let data = try? JSONEncoder().encode(snapshot) {
            UserDefaults.standard.set(data, forKey: "kosistenz.widget.snapshot")
        }
    }

    private func loadCache() -> Snapshot? {
        guard let data = UserDefaults.standard.data(forKey: "kosistenz.widget.snapshot") else { return nil }
        return try? JSONDecoder().decode(Snapshot.self, from: data)
    }
}

struct KosistenzWidgetEntryView: View {
    var entry: KosistenzProvider.Entry
    @Environment(\.widgetFamily) var family

    var body: some View {
        switch family {
        case .systemMedium:
            mediumView
        case .accessoryRectangular:
            accessoryRect
        case .accessoryCircular:
            accessoryCircle
        default:
            smallView
        }
    }

    private var snap: Snapshot { entry.snapshot }

    private var smallView: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Kosistenz")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            HStack(alignment: .firstTextBaseline, spacing: 6) {
                Text("\(snap.openCount)")
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                Text(snap.openCount == 1 ? "open" : "open")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Text(snap.workoutLogged ? "Workout logged" : "No workout yet")
                .font(.caption)
            Text("Streak \(snap.journalStreak)")
                .font(.caption)
                .foregroundStyle(.secondary)
            if snap.todayEmpty {
                Text("Today is empty")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var mediumView: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Today")
                    .font(.headline)
                Spacer()
                Text("Streak \(snap.journalStreak)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if snap.titles.isEmpty {
                Text(snap.todayEmpty ? "Today is empty" : "No open to-dos")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(Array(snap.titles.prefix(3).enumerated()), id: \.offset) { _, title in
                    Text("• \(title)")
                        .font(.subheadline)
                        .lineLimit(1)
                }
            }
            Text(snap.workoutLogged ? "Workout logged" : "No workout yet")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var accessoryRect: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("\(snap.openCount) open · \(snap.workoutLogged ? "workout" : "no workout")")
                .font(.headline)
            Text("Streak \(snap.journalStreak)")
                .font(.caption)
        }
    }

    private var accessoryCircle: some View {
        ZStack {
            AccessoryWidgetBackground()
            VStack(spacing: 0) {
                Text("\(snap.openCount)")
                    .font(.system(size: 20, weight: .bold, design: .rounded))
                Text("open")
                    .font(.caption2)
            }
        }
    }
}

@main
struct KosistenzWidgets: WidgetBundle {
    var body: some Widget {
        KosistenzTodayWidget()
    }
}

struct KosistenzTodayWidget: Widget {
    let kind = "KosistenzToday"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: KosistenzProvider()) { entry in
            KosistenzWidgetEntryView(entry: entry)
                .widgetURL(URL(string: "kosistenz://open"))
        }
        .configurationDisplayName("Kosistenz Today")
        .description("Open to-dos, whether you logged a workout, and your journal streak.")
        .supportedFamilies(Self.families)
    }

    static var families: [WidgetFamily] {
        var list: [WidgetFamily] = [.systemSmall, .systemMedium]
        if #available(macOS 14.0, *) {
            list.append(contentsOf: [.accessoryRectangular, .accessoryCircular])
        }
        return list
    }
}
