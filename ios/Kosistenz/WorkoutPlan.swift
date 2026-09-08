import Foundation

/// Port of workouts.expected_kinds_for_date. Keep lockstep with
/// tests/test_iphone_expected_kinds.py (Monday 2026-08-24 → push).
enum WorkoutPlan {
    static let chipKinds: [(id: String, label: String)] = [
        ("push", "Push"),
        ("pull", "Pull"),
        ("legs", "Legs"),
        ("running", "Run"),
        ("other", "Other"),
    ]

    static let liftKinds: Set<String> = ["legs", "push", "pull"]

    static func expectedKinds(on day: Date, template: FlexibleJSON?) -> [String] {
        expectedKinds(on: day, object: template?.value.objectValue ?? [:])
    }

    static func expectedKinds(on day: Date, object: [String: AnyJSON]) -> [String] {
        var kinds: [String] = []
        let weekday = Calendar.current.component(.weekday, from: day)
        // Python date.weekday(): Monday = 0. Calendar: Sunday = 1.
        let pythonWeekday = (weekday + 5) % 7
        let lifts = object["lifts"]?.objectValue ?? [:]
        if let lift = lifts[String(pythonWeekday)]?.stringValue, liftKinds.contains(lift) {
            kinds.append(lift)
        }
        let running = object["running"]?.objectValue ?? [:]
        let enabled = running["enabled"]?.boolValue ?? true
        guard enabled else { return kinds }
        let mode = running["mode"]?.stringValue ?? "interval"
        if mode == "weekdays" {
            let days = running["weekdays"]?.numberArray ?? []
            if days.contains(Double(pythonWeekday)) {
                kinds.append("running")
            }
        } else {
            let every = max(1, Int(running["every_days"]?.numberValue ?? 2))
            let anchorText = String((running["anchor"]?.stringValue ?? "2020-01-06").prefix(10))
            let formatter = DateFormatter()
            formatter.calendar = Calendar(identifier: .gregorian)
            formatter.locale = Locale(identifier: "en_US_POSIX")
            formatter.dateFormat = "yyyy-MM-dd"
            guard let anchor = formatter.date(from: anchorText) else { return kinds }
            let start = Calendar.current.startOfDay(for: anchor)
            let target = Calendar.current.startOfDay(for: day)
            let delta = Calendar.current.dateComponents([.day], from: start, to: target).day ?? -1
            if delta >= 0, delta % every == 0 {
                kinds.append("running")
            }
        }
        return kinds
    }

    static func sessionLabel(_ session: WorkoutSession) -> String {
        if session.kind == "running", let miles = session.miles, miles > 0 {
            return String(format: "Run · %.1f mi", miles)
        }
        if session.kind == "other", let name = session.other_label, !name.isEmpty {
            return name
        }
        return chipKinds.first(where: { $0.id == session.kind })?.label ?? session.kind.capitalized
    }
}

extension AnyJSON {
    var objectValue: [String: AnyJSON] {
        if case .object(let value) = self { return value }
        return [:]
    }

    var stringValue: String? {
        if case .string(let value) = self { return value }
        return nil
    }

    var boolValue: Bool? {
        if case .bool(let value) = self { return value }
        if case .number(let value) = self { return value != 0 }
        return nil
    }

    var numberValue: Double? {
        if case .number(let value) = self { return value }
        return nil
    }

    var numberArray: [Double] {
        if case .array(let values) = self {
            return values.compactMap(\.numberValue)
        }
        return []
    }
}
