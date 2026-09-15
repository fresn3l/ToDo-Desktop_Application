import SwiftUI

struct PlaceWorkSheet: View {
    @Environment(\.dismiss) private var dismiss
    var item: UnplacedItem
    var palette: KosistenzPalette
    var defaultDate: String
    var dayStart: String?
    var dayEnd: String?
    var onSave: (Pack) -> Void
    var onError: (String) -> Void

    @State private var date = Date()
    @State private var startText = "09:30"
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text(item.title ?? "")
                    if let mins = item.remaining_minutes ?? item.estimate_minutes, mins > 0 {
                        Text("\(mins) min to place")
                            .foregroundStyle(.secondary)
                    }
                }
                Section("When") {
                    DatePicker("Day", selection: $date, displayedComponents: .date)
                    HStack {
                        Text("Start")
                        Spacer()
                        TextField("09:30", text: $startText)
                            .keyboardType(.numbersAndPunctuation)
                            .multilineTextAlignment(.trailing)
                            .monospacedDigit()
                            .frame(maxWidth: 96)
                    }
                    Text("24-hour times, same as the Mac — 0930 or 09:30. Fill week still packs the rest.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .scrollContentBackground(.hidden)
            .background(palette.pageBg)
            .navigationTitle("Place")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { save() }
                }
            }
            .onAppear {
                date = Self.parseDay(defaultDate) ?? Date()
                let window = PhoneCalendar.clockWindow(dayStart: dayStart, dayEnd: dayEnd)
                startText = PhoneCalendar.formatMilitary(window.startMin)
            }
        }
        .tint(palette.accent)
    }

    private func save() {
        do {
            guard let id = item.itemId else { throw PackActionError.message("That to-do is gone.") }
            let start = try PhoneCalendar.combine(date: Self.stampDay(date), time: startText)
            let pack = try PackActions.placeWork(id: id, start: start)
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
