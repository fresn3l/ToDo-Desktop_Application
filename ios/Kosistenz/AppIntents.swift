import AppIntents

struct ParkWorkIntent: AppIntent {
    static var title: LocalizedStringResource = "Park in To Do"
    static var description: IntentDescription = "Save a thought to Kosistenz To Do with no day yet."
    static var openAppWhenRun: Bool = true

    @Parameter(title: "Thought")
    var title: String

    static var parameterSummary: some ParameterSummary {
        Summary("Park \(\.$title) in To Do")
    }

    func perform() async throws -> some IntentResult & ProvidesDialog {
        _ = try PackActions.park(title)
        return .result(dialog: "Parked in To Do.")
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

#if !WIDGET_EXTENSION
struct KosistenzShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: ParkWorkIntent(),
            phrases: [
                "Park in \(.applicationName)",
                "Park a thought in \(.applicationName)",
            ],
            shortTitle: "Park in To Do",
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
    }
}
#endif
