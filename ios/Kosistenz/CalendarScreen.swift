import SwiftUI

struct CalendarScreen: View {
    @EnvironmentObject private var store: PackStore
    @State private var showAdd = false
    @State private var showICS = false
    @State private var icsText = ""
    @State private var view: CalView = .week
    @State private var weekStart = ""
    @State private var monthCursor = MonthCursor.now
    @State private var yearCursor = Calendar.current.component(.year, from: Date())
    @State private var selectedDay: String?
    @State private var placing: UnplacedItem?
    @State private var acting: CalendarItem?
    @State private var icsError: String?

    private enum CalView: String, CaseIterable, Identifiable {
        case week = "Week"
        case month = "Month"
        case year = "Year"
        var id: String { rawValue }
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Picker("View", selection: $view) {
                        ForEach(CalView.allCases) { item in
                            Text(item.rawValue).tag(item)
                        }
                    }
                    .pickerStyle(.segmented)
                    .listRowBackground(store.palette.widgetBg)
                    HStack {
                        Button { shift(-1) } label: { Image(systemName: "chevron.left") }
                        Spacer()
                        Text(heading)
                            .font(.subheadline.weight(.semibold))
                        Spacer()
                        Button { shift(1) } label: { Image(systemName: "chevron.right") }
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
                if view == .week {
                    weekSection
                    unplacedSection
                } else if view == .month {
                    monthSection
                } else {
                    yearSection
                }
                if let error = store.error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .scrollContentBackground(.hidden)
            .background(store.palette.pageBg)
            .navigationTitle("Calendar")
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    SyncToolbarButton()
                }
                ToolbarItemGroup(placement: .primaryAction) {
                    Button("Fill week") { fillWeek() }
                    Button("Add") { showAdd = true }
                    Button("ICS") { showICS = true }
                }
            }
            .sheet(isPresented: $showAdd) {
                AddEventSheet(
                    palette: store.palette,
                    defaultDate: selectedDay ?? store.today,
                    dayStart: store.pack?.calendar.day_start,
                    dayEnd: store.pack?.calendar.day_end,
                    onSave: { pack in
                        store.pack = pack
                        store.error = nil
                    },
                    onError: { store.error = $0 }
                )
            }
            .sheet(item: $placing) { item in
                PlaceWorkSheet(
                    item: item,
                    palette: store.palette,
                    defaultDate: selectedDay ?? store.today,
                    dayStart: store.pack?.calendar.day_start,
                    dayEnd: store.pack?.calendar.day_end,
                    onSave: { pack in
                        store.pack = pack
                        store.error = nil
                    },
                    onError: { store.error = $0 }
                )
            }
            .sheet(isPresented: $showICS) { icsSheet }
            .confirmationDialog(acting?.title ?? "Block", isPresented: Binding(
                get: { acting != nil },
                set: { if !$0 { acting = nil } }
            ), titleVisibility: .visible) {
                Button("Done") { completeActing() }
                Button("Skip") { skipActing() }
                if acting?.kind != "hard" {
                    Button("Park") { parkActing() }
                }
                Button("Cancel", role: .cancel) { acting = nil }
            }
            .refreshable { store.reload() }
            .onAppear { syncWeekStart() }
        }
    }

    @ViewBuilder
    private var weekSection: some View {
        Section {
            if weekDays.isEmpty {
                Text("No week clock in the pack yet. Add an event here, or open Kosistenz on the Mac and Push to iCloud.")
                    .foregroundStyle(.secondary)
            } else if let selected = selectedDayObject {
                DayClockView(
                    day: selected,
                    dayStart: store.pack?.calendar.day_start,
                    dayEnd: store.pack?.calendar.day_end,
                    palette: store.palette,
                    height: 420,
                    nowMinutes: selected.date == store.today ? currentMinutes : nil,
                    onSelectItem: { acting = $0 }
                )
                .frame(minHeight: 440)
                Button("Whole week") { selectedDay = nil }
                    .font(.caption.weight(.semibold))
            } else {
                WeekClockView(
                    file: assembledFile,
                    palette: store.palette,
                    nowMinutes: currentMinutes,
                    today: store.today,
                    onSelectDay: { selectedDay = $0.date },
                    onSelectItem: { acting = $0 }
                )
                .frame(minHeight: 430)
            }
        }
        .listRowBackground(store.palette.widgetBg)
        .listRowInsets(EdgeInsets(top: 10, leading: 16, bottom: 10, trailing: 16))
    }

    @ViewBuilder
    private var unplacedSection: some View {
        Section("Unplaced") {
            if unplaced.isEmpty {
                Text("Nothing with minutes left off the clock. Add minutes on Work, then Fill week or Place.")
                    .foregroundStyle(.secondary)
                    .listRowBackground(store.palette.widgetBg)
            } else {
                ForEach(unplaced) { item in
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(item.title ?? "")
                            Text(unplacedSubtitle(item))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button("Place") { placing = item }
                            .font(.caption.weight(.semibold))
                    }
                    .listRowBackground(store.palette.widgetBg)
                }
            }
        }
    }

    private var monthSection: some View {
        Section {
            monthGrid(weeks: monthWeeks, compact: false)
        }
        .listRowBackground(store.palette.widgetBg)
        .listRowInsets(EdgeInsets(top: 8, leading: 12, bottom: 8, trailing: 12))
    }

    private var yearSection: some View {
        Section {
            VStack(alignment: .leading, spacing: 16) {
                ForEach(1...12, id: \.self) { month in
                    VStack(alignment: .leading, spacing: 6) {
                        Text(monthLabel(month))
                            .font(.subheadline.weight(.semibold))
                        monthGrid(weeks: PhoneCalendar.monthWeeks(
                            year: yearCursor,
                            month: month,
                            today: store.today,
                            eventDates: eventDates,
                            blockDates: blockDates,
                            dueDates: dueDates
                        ), compact: true)
                    }
                }
            }
        }
        .listRowBackground(store.palette.widgetBg)
    }

    private var icsSheet: some View {
        NavigationStack {
            Form {
                Section("Paste ICS") {
                    TextEditor(text: $icsText)
                        .frame(minHeight: 160)
                    Text("Paste a BEGIN:VCALENDAR blob. Weekly BYDAY chips become repeating events.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let icsError {
                    Section { Text(icsError).foregroundStyle(.red) }
                }
            }
            .navigationTitle("ICS")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { showICS = false }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Import") { importICS() }
                }
            }
        }
        .tint(store.palette.accent)
    }

    private func monthGrid(weeks: [[MonthCell]], compact: Bool) -> some View {
        let names = ["M", "T", "W", "T", "F", "S", "S"]
        return VStack(spacing: compact ? 2 : 4) {
            HStack {
                ForEach(0..<7, id: \.self) { index in
                    Text(names[index])
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity)
                }
            }
            ForEach(Array(weeks.enumerated()), id: \.offset) { _, week in
                HStack(spacing: compact ? 2 : 4) {
                    ForEach(week) { cell in
                        Button {
                            openDay(cell.date)
                        } label: {
                            VStack(spacing: 2) {
                                Text("\(cell.day)")
                                    .font(compact ? .caption2 : .caption)
                                    .foregroundStyle(cell.inMonth ? store.palette.titles : store.palette.titles.opacity(0.35))
                                HStack(spacing: 2) {
                                    if cell.eventCount > 0 { Circle().fill(store.palette.accent).frame(width: 4, height: 4) }
                                    if cell.blockCount > 0 { Circle().fill(store.palette.widgetBorder).frame(width: 4, height: 4) }
                                    if cell.dueCount > 0 { Circle().fill(store.palette.openNext).frame(width: 4, height: 4) }
                                }
                                .frame(height: 6)
                            }
                            .frame(maxWidth: .infinity, minHeight: compact ? 28 : 36)
                            .background(cell.isToday ? store.palette.accent.opacity(0.25) : Color.clear)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private var heading: String {
        if view == .year { return String(yearCursor) }
        if view == .month {
            return monthLabel(monthCursor.month) + " \(monthCursor.year)"
        }
        return weekLabel
    }

    private var weekLabel: String {
        let start = resolvedWeekStart
        guard let first = parseDay(start), let last = Calendar.current.date(byAdding: .day, value: 6, to: first) else {
            return start
        }
        let fmt = DateFormatter()
        fmt.dateFormat = "MMM d"
        return "\(fmt.string(from: first)) – \(fmt.string(from: last))"
    }

    private var resolvedWeekStart: String {
        if !weekStart.isEmpty { return PhoneCalendar.mondayOf(weekStart) }
        return PhoneCalendar.mondayOf(store.pack?.calendar.week_start ?? store.today)
    }

    private var weekDays: [CalendarDay] {
        guard let pack = store.pack else { return [] }
        return PhoneCalendar.assembleWeek(
            weekStart: resolvedWeekStart,
            today: store.today,
            packedDays: pack.calendar.days,
            hardEvents: pack.calendar.hard_events,
            phoneBlocks: pack.calendar.phone_blocks,
            workItems: pack.work.items
        )
    }

    private var assembledFile: CalendarFile {
        var file = store.pack?.calendar ?? CalendarFile()
        file.days = weekDays
        return file
    }

    private var selectedDayObject: CalendarDay? {
        guard let selectedDay else { return nil }
        return weekDays.first(where: { $0.date == selectedDay })
    }

    private var unplaced: [UnplacedItem] {
        guard let pack = store.pack else { return [] }
        return PhoneCalendar.unplacedFromWork(
            items: pack.work.items,
            blocks: PhoneCalendar.flattenBlocks(days: weekDays) + pack.calendar.phone_blocks
        )
    }

    private var monthWeeks: [[MonthCell]] {
        PhoneCalendar.monthWeeks(
            year: monthCursor.year,
            month: monthCursor.month,
            today: store.today,
            eventDates: eventDates,
            blockDates: blockDates,
            dueDates: dueDates
        )
    }

    private var eventDates: [String: Int] {
        var counts: [String: Int] = [:]
        for event in store.pack?.calendar.hard_events ?? [] {
            let start = view == .year ? String(format: "%04d-01-01", yearCursor) : monthCursor.firstDay
            let endYear = view == .year ? yearCursor : monthCursor.year
            let endMonth = view == .year ? 12 : monthCursor.month
            let end = lastDay(year: endYear, month: endMonth)
            for occ in PhoneCalendar.expandHardEvent(event, weekStart: start, weekEnd: end) {
                let iso = occ.occurrence_date ?? String((occ.start_at ?? "").prefix(10))
                counts[iso, default: 0] += 1
            }
        }
        for day in store.pack?.calendar.days ?? [] {
            for item in day.events {
                let iso = String((item.start_at ?? day.date ?? "").prefix(10))
                counts[iso, default: 0] += 1
            }
        }
        return counts
    }

    private var blockDates: [String: Int] {
        var counts: [String: Int] = [:]
        for day in store.pack?.calendar.days ?? [] {
            counts[day.date ?? "", default: 0] += day.blocks.count
        }
        for block in store.pack?.calendar.phone_blocks ?? [] {
            counts[String((block.start_at ?? "").prefix(10)), default: 0] += 1
        }
        return counts
    }

    private var dueDates: [String: Int] {
        var counts: [String: Int] = [:]
        for item in store.pack?.work.items ?? [] where item.status != "done" {
            let due = String((item.due_at ?? "").prefix(10))
            if due.count == 10 { counts[due, default: 0] += 1 }
        }
        for day in store.pack?.calendar.days ?? [] {
            counts[day.date ?? "", default: 0] += day.dues.count
        }
        return counts
    }

    private var currentMinutes: Int {
        let now = Calendar.current.dateComponents([.hour, .minute], from: Date())
        return (now.hour ?? 0) * 60 + (now.minute ?? 0)
    }

    private func unplacedSubtitle(_ item: UnplacedItem) -> String {
        let mins = item.remaining_minutes ?? item.estimate_minutes ?? 0
        let due = String((item.due_at ?? "").prefix(10))
        if due.count == 10 { return "\(mins) min · due \(due)" }
        if let scheduled = item.scheduled_date, !scheduled.isEmpty { return "\(mins) min · \(scheduled)" }
        return "\(mins) min left"
    }

    private func shift(_ dir: Int) {
        if view == .year {
            yearCursor += dir
            return
        }
        if view == .month {
            var month = monthCursor.month + dir
            var year = monthCursor.year
            if month < 1 { month = 12; year -= 1 }
            if month > 12 { month = 1; year += 1 }
            monthCursor = MonthCursor(year: year, month: month)
            return
        }
        guard let start = parseDay(resolvedWeekStart),
              let next = Calendar.current.date(byAdding: .day, value: dir * 7, to: start) else { return }
        weekStart = PhoneCalendar.formatDay(next)
        selectedDay = nil
    }

    private func openDay(_ iso: String) {
        weekStart = PhoneCalendar.mondayOf(iso)
        selectedDay = iso
        view = .week
    }

    private func fillWeek() {
        do {
            store.pack = try PackActions.fillWeek(weekStart: resolvedWeekStart)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func importICS() {
        do {
            store.pack = try PackActions.importICS(icsText)
            store.error = nil
            icsError = nil
            icsText = ""
            showICS = false
        } catch {
            icsError = error.localizedDescription
        }
    }

    private func completeActing() {
        guard let item = acting else { return }
        acting = nil
        let entry = TodayList.Entry(
            id: item.markKey,
            title: item.title ?? "",
            startAt: item.start_at,
            endAt: item.end_at,
            done: false,
            kind: .clock,
            workId: item.work_item_id,
            clockId: item.markKey
        )
        do {
            store.pack = try PackActions.complete(entry)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func skipActing() {
        guard let item = acting else { return }
        acting = nil
        do {
            store.pack = try PackActions.skipClockItem(item)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func parkActing() {
        guard let item = acting else { return }
        acting = nil
        do {
            store.pack = try PackActions.parkClockItem(item)
            store.error = nil
        } catch {
            store.error = error.localizedDescription
        }
    }

    private func syncWeekStart() {
        if weekStart.isEmpty {
            weekStart = PhoneCalendar.mondayOf(store.pack?.calendar.week_start ?? store.today)
        }
    }

    private func monthLabel(_ month: Int) -> String {
        let fmt = DateFormatter()
        fmt.dateFormat = "MMMM"
        var comps = DateComponents()
        comps.year = view == .year ? yearCursor : monthCursor.year
        comps.month = month
        comps.day = 1
        return fmt.string(from: Calendar.current.date(from: comps) ?? Date())
    }

    private func lastDay(year: Int, month: Int) -> String {
        var comps = DateComponents()
        comps.year = year
        comps.month = month + 1
        comps.day = 0
        let date = Calendar.current.date(from: comps) ?? Date()
        return PhoneCalendar.formatDay(date)
    }

    private func parseDay(_ raw: String) -> Date? {
        let formatter = DateFormatter()
        formatter.calendar = Calendar.current
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.date(from: String(raw.prefix(10)))
    }
}

private struct MonthCursor {
    var year: Int
    var month: Int
    var firstDay: String {
        String(format: "%04d-%02d-01", year, month)
    }
    static var now: MonthCursor {
        let cal = Calendar.current
        let now = Date()
        return MonthCursor(year: cal.component(.year, from: now), month: cal.component(.month, from: now))
    }
}
