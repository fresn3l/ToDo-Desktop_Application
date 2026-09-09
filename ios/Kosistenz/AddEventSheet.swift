import SwiftUI

struct AddEventSheet: View {
    @Environment(\.dismiss) private var dismiss
    var palette: KosistenzPalette
    var defaultDate: String
    var dayStart: String?
    var dayEnd: String?
    var onSave: (Pack) -> Void
    var onError: (String) -> Void

    @State private var title = ""
    @State private var date = Date()
    @State private var startText = "09:30"
    @State private var endText = "10:30"
    @State private var selectedDays: Set<Int> = []
    @State private var error: String?

    private let chips: [(label: String, day: Int)] = [
        ("Mon", 0), ("Tue", 1), ("Wed", 2), ("Thu", 3),
        ("Fri", 4), ("Sat", 5), ("Sun", 6),
    ]

    var body: some View {
        NavigationStack {
            Form {
                Section("Event") {
                    TextField("Office hours, class, shift…", text: $title)
                    DatePicker("Date", selection: $date, displayedComponents: .date)
                    HStack {
                        Text("Start")
                        Spacer()
                        TextField("09:30", text: $startText)
                            .keyboardType(.numbersAndPunctuation)
                            .multilineTextAlignment(.trailing)
                            .monospacedDigit()
                            .frame(maxWidth: 96)
                    }
                    HStack {
                        Text("End")
                        Spacer()
                        TextField("10:30", text: $endText)
                            .keyboardType(.numbersAndPunctuation)
                            .multilineTextAlignment(.trailing)
                            .monospacedDigit()
                            .frame(maxWidth: 96)
                    }
                    Text("24-hour times, same as the Mac — 0930 or 09:30.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Section("Repeats weekly") {
                    HStack(spacing: 6) {
                        ForEach(chips, id: \.day) { chip in
                            Button(chip.label) {
                                if selectedDays.contains(chip.day) {
                                    selectedDays.remove(chip.day)
                                } else {
                                    selectedDays.insert(chip.day)
                                }
                            }
                            .font(.caption.weight(.semibold))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 6)
                            .background(
                                selectedDays.contains(chip.day)
                                    ? palette.accent.opacity(0.35)
                                    : palette.widgetBorder.opacity(0.4)
                            )
                            .foregroundStyle(palette.ink)
                            .clipShape(Capsule())
                        }
                    }
                    .listRowBackground(palette.widgetBg)
                    Text(selectedDays.isEmpty ? "No chips — this is a one-off." : "Repeats on the selected days.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let error {
                    Section {
                        Text(error).foregroundStyle(.red)
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(palette.pageBg)
            .navigationTitle("Add event")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { save() }
                        .disabled(title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
            .onAppear {
                date = Self.parseDay(defaultDate) ?? Date()
                let window = PhoneCalendar.clockWindow(dayStart: dayStart, dayEnd: dayEnd)
                let start = 9 * 60 + 30
                if start < window.startMin || start >= window.endMin {
                    startText = PhoneCalendar.formatMilitary(window.startMin)
                    endText = PhoneCalendar.formatMilitary(min(window.endMin, window.startMin + 60))
                }
            }
        }
        .tint(palette.accent)
    }

    private func save() {
        do {
            let pack = try PackActions.addHardEvent(
                title: title,
                date: Self.stampDay(date),
                start: startText,
                end: endText,
                weekdays: selectedDays.sorted()
            )
            onSave(pack)
            dismiss()
        } catch {
            let text = error.localizedDescription
            self.error = text
            onError(text)
        }
    }

    private static func stampDay(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar.current
        formatter.locale = Locale.current
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }

    private static func parseDay(_ raw: String) -> Date? {
        let formatter = DateFormatter()
        formatter.calendar = Calendar.current
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.date(from: String(raw.prefix(10)))
    }
}
