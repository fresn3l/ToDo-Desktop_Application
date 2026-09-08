import AppIntents

struct ParkWorkIntent: AppIntent {
    static var title: LocalizedStringResource = "Park in All Work"
    static var description: IntentDescription = "Save a thought to Kosistenz All Work with no day yet."
    static var openAppWhenRun: Bool = true

    @Parameter(title: "Thought")
    var title: String

    static var parameterSummary: some ParameterSummary {
        Summary("Park \(\.$title) in All Work")
    }

    func perform() async throws -> some IntentResult & ProvidesDialog {
        _ = try PackActions.park(title)
        return .result(dialog: "Parked in All Work.")
    }
}

struct ToggleFirstTodoIntent: AppIntent {
    static var title: LocalizedStringResource = "Check off today’s to-do"
    static var description: IntentDescription = "Marks the first open to-do dated today."
    static var openAppWhenRun: Bool = true

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let name = try PackActions.toggleFirstOpen(on: DayStamp.today())
        return .result(dialog: "Checked off \(name).")
    }
}

struct ToggleTodoIntent: AppIntent {
    static var title: LocalizedStringResource = "Toggle a to-do"
    static var openAppWhenRun: Bool = false

    @Parameter(title: "To-do id")
    var id: String

    init() { id = "" }
    init(id: String) { self.id = id }

    func perform() async throws -> some IntentResult {
        _ = try PackActions.toggle(id: id)
        return .result()
    }
}

struct LogExpectedWorkoutIntent: AppIntent {
    static var title: LocalizedStringResource = "Log today’s workout"
    static var description: IntentDescription = "Logs the expected session. Runs need miles; Other needs a name."
    static var openAppWhenRun: Bool = true

    @Parameter(title: "Miles")
    var miles: Double?

    @Parameter(title: "Other name")
    var other: String?

    static var parameterSummary: some ParameterSummary {
        Summary("Log today’s workout")
    }

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let message = try PackActions.logExpected(miles: miles, other: other, date: DayStamp.today())
        return .result(dialog: IntentDialog(stringLiteral: message))
    }
}

#if !WIDGET_EXTENSION
struct KosistenzShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: ParkWorkIntent(),
            phrases: [
                "Park in \(.applicationName)",
                "Park a thought in \(.applicationName)",
            ],
            shortTitle: "Park in All Work",
            systemImageName: "tray"
        )
        AppShortcut(
            intent: ToggleFirstTodoIntent(),
            phrases: [
                "Check off a to-do in \(.applicationName)",
                "Finish a to-do in \(.applicationName)",
            ],
            shortTitle: "Check off to-do",
            systemImageName: "checkmark.circle"
        )
        AppShortcut(
            intent: LogExpectedWorkoutIntent(),
            phrases: [
                "Log today’s workout in \(.applicationName)",
                "Log a workout in \(.applicationName)",
            ],
            shortTitle: "Log workout",
            systemImageName: "figure.strengthtraining.traditional"
        )
    }
}
#endif
