import EventKit
import Foundation

extension AppDelegate {
    func importAppleCalendars() {
        let store = EKEventStore()
        let finish: (Bool, String?) -> Void = { granted, message in
            if !granted {
                self.notifyCalendarImport(error: message ?? "Calendar access was not allowed.")
                return
            }
            self.pushSubscribedCalendars(store: store)
        }
        if #available(macOS 14.0, *) {
            store.requestFullAccessToEvents { granted, error in
                DispatchQueue.main.async {
                    finish(granted, error?.localizedDescription)
                }
            }
        } else {
            store.requestAccess(to: .event) { granted, error in
                DispatchQueue.main.async {
                    finish(granted, error?.localizedDescription)
                }
            }
        }
    }

    func pushSubscribedCalendars(store: EKEventStore) {
        let start = Date().addingTimeInterval(-7 * 24 * 3600)
        let end = Date().addingTimeInterval(90 * 24 * 3600)
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        var created = 0
        var updated = 0
        var calendarsUsed = 0
        for calendar in store.calendars(for: .event) {
            guard shouldImport(calendar) else { continue }
            calendarsUsed += 1
            let predicate = store.predicateForEvents(withStart: start, end: end, calendars: [calendar])
            let ekEvents = store.events(matching: predicate)
            var payloadEvents: [[String: Any]] = []
            for event in ekEvents {
                let uid = event.calendarItemExternalIdentifier ?? event.eventIdentifier ?? UUID().uuidString
                let title = event.title?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                guard !title.isEmpty else { continue }
                var row: [String: Any] = [
                    "uid": uid,
                    "title": title,
                    "all_day": event.isAllDay,
                    "start_at": formatter.string(from: event.startDate),
                ]
                if let stop = event.endDate {
                    row["end_at"] = formatter.string(from: stop)
                }
                payloadEvents.append(row)
            }
            let body: [String: Any] = [
                "calendar_id": calendar.calendarIdentifier,
                "calendar_title": calendar.title,
                "role": "deadlines",
                "events": payloadEvents,
            ]
            if let result = postCalendarIngest(body) {
                created += intValue(result["created"])
                updated += intValue(result["updated"])
            }
        }
        if calendarsUsed == 0 {
            notifyCalendarImport(error: "No subscribed calendars found. Paste the ICS URL instead.")
            return
        }
        notifyCalendarImport(created: created, updated: updated)
    }

    private func shouldImport(_ calendar: EKCalendar) -> Bool {
        if calendar.type == .subscription {
            return true
        }
        let title = calendar.title.lowercased()
        let hints = ["canvas", "due", "course", "class", "assignment", "moodle", "blackboard"]
        return hints.contains { title.contains($0) }
    }

    private func postCalendarIngest(_ body: [String: Any]) -> [String: Any]? {
        let payload = (try? JSONSerialization.data(withJSONObject: body, options: [])) ?? Data()
        for port in apiPort...UInt16(min(Int(apiPort) + 9, 18750)) {
            guard let url = URL(string: "http://127.0.0.1:\(port)/api/calendar/ingest") else { continue }
            var request = URLRequest(url: url, timeoutInterval: 12)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = payload
            if let data = syncCalendarRequest(request),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                apiPort = port
                return json
            }
        }
        return nil
    }

    private func syncCalendarRequest(_ request: URLRequest) -> Data? {
        var result: Data?
        let sem = DispatchSemaphore(value: 0)
        URLSession.shared.dataTask(with: request) { data, response, _ in
            if let http = response as? HTTPURLResponse, (200..<500).contains(http.statusCode) {
                result = data
            }
            sem.signal()
        }.resume()
        _ = sem.wait(timeout: .now() + 15)
        return result
    }

    private func intValue(_ raw: Any?) -> Int {
        if let n = raw as? Int { return n }
        if let n = raw as? Double { return Int(n) }
        return 0
    }

    func notifyCalendarImport(created: Int = 0, updated: Int = 0, error: String? = nil) {
        let payload: [String: Any]
        if let error, !error.isEmpty {
            payload = ["error": error]
        } else {
            payload = ["created": created, "updated": updated]
        }
        guard let data = try? JSONSerialization.data(withJSONObject: payload),
              let json = String(data: data, encoding: .utf8) else { return }
        runInWebView("window.dispatchEvent(new CustomEvent('kosistenz:calendar-imported',{detail:\(json)}));")
    }
}
