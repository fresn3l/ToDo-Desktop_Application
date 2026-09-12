import Foundation
import UserNotifications

/// Local alerts 30 / 15 / 5 minutes before a timed event. Rescheduled from the pack.
enum EventAlerts {
    static let offsets = [30, 15, 5]
    static let prefix = "kosistenz.event."

    static func request() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
    }

    static func sync(pack: Pack) {
        let center = UNUserNotificationCenter.current()
        center.getPendingNotificationRequests { pending in
            let ours = pending.map(\.identifier).filter { $0.hasPrefix(prefix) }
            center.removePendingNotificationRequests(withIdentifiers: ours)
            let now = Date()
            for item in TodayList.upcomingClockItems(pack: pack, now: now) {
                guard let start = TodayList.parseLocal(item.start_at) else { continue }
                let title = (item.title ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
                guard !title.isEmpty else { continue }
                let clockId = item.markKey
                for minutes in offsets {
                    let fire = start.addingTimeInterval(TimeInterval(-minutes * 60))
                    guard fire > now else { continue }
                    let content = UNMutableNotificationContent()
                    content.title = title
                    content.body = minutes == 1 ? "Starts in 1 minute." : "Starts in \(minutes) minutes."
                    content.sound = .default
                    let comps = Calendar.current.dateComponents(
                        [.year, .month, .day, .hour, .minute],
                        from: fire
                    )
                    let trigger = UNCalendarNotificationTrigger(dateMatching: comps, repeats: false)
                    let request = UNNotificationRequest(
                        identifier: identifier(clockId: clockId, minutes: minutes),
                        content: content,
                        trigger: trigger
                    )
                    center.add(request)
                }
            }
        }
    }

    static func cancel(clockId: String) {
        let ids = offsets.map { identifier(clockId: clockId, minutes: $0) }
        let center = UNUserNotificationCenter.current()
        center.removePendingNotificationRequests(withIdentifiers: ids)
        center.removeDeliveredNotifications(withIdentifiers: ids)
    }

    static func identifier(clockId: String, minutes: Int) -> String {
        "\(prefix)\(clockId).\(minutes)"
    }
}
