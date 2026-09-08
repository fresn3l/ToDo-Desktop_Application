import SwiftUI
import WidgetKit

@main
struct KosistenzWidgetBundle: WidgetBundle {
    var body: some Widget {
        KosistenzTodayWidget()
    }
}

struct KosistenzTodayWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "KosistenzToday", provider: TodayProvider()) { entry in
            TodayWidgetView(entry: entry)
                .containerBackground(.fill.tertiary, for: .widget)
        }
        .configurationDisplayName("Kosistenz")
        .description("Today’s to-dos. Tap a circle to check one off.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}

struct TodayEntry: TimelineEntry {
    let date: Date
    let snapshot: WidgetSnapshot
}

struct TodayProvider: TimelineProvider {
    func placeholder(in context: Context) -> TodayEntry {
        TodayEntry(date: Date(), snapshot: .empty)
    }

    func getSnapshot(in context: Context, completion: @escaping (TodayEntry) -> Void) {
        completion(TodayEntry(date: Date(), snapshot: PackActions.snapshot()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<TodayEntry>) -> Void) {
        let entry = TodayEntry(date: Date(), snapshot: PackActions.snapshot())
        let next = Calendar.current.date(byAdding: .minute, value: 15, to: Date()) ?? Date().addingTimeInterval(900)
        completion(Timeline(entries: [entry], policy: .after(next)))
    }
}

struct TodayWidgetView: View {
    var entry: TodayEntry
    @Environment(\.widgetFamily) private var family

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Today")
                .font(.headline)
            if !entry.snapshot.nextBlock.isEmpty {
                Text(entry.snapshot.nextBlock)
                    .font(.caption)
                    .lineLimit(1)
            }
            if entry.snapshot.todos.isEmpty {
                Text(entry.snapshot.access == "needsFolder" ? "Open Kosistenz and pick the folder." : "Nothing dated today.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(entry.snapshot.todos.prefix(family == .systemSmall ? 3 : 4)) { item in
                    HStack(spacing: 8) {
                        Button(intent: ToggleTodoIntent(id: item.id)) {
                            Image(systemName: item.done ? "checkmark.circle.fill" : "circle")
                        }
                        .buttonStyle(.plain)
                        Text(item.title)
                            .font(.caption)
                            .lineLimit(1)
                            .strikethrough(item.done)
                    }
                }
            }
            if family == .systemMedium, !entry.snapshot.expectedLabel.isEmpty {
                Text("Gym · \(entry.snapshot.expectedLabel)")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}
