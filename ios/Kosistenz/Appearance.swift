import SwiftUI
import UIKit

/// Colors resolved on the Mac and written into appearance.json. No iPhone theme picker.
struct KosistenzPalette: Equatable {
    var pageBg: Color
    var widgetBg: Color
    var widgetBorder: Color
    var titles: Color
    var accent: Color
    var done: Color
    var openNext: Color
    var sidebar: Color
    var ink: Color
    var borderWidth: CGFloat

    static let ocean = KosistenzPalette(
        pageBg: Color(hex: "#121c26"),
        widgetBg: Color(hex: "#1d2c3b"),
        widgetBorder: Color(hex: "#2c3d4e"),
        titles: Color(hex: "#eef3f7"),
        accent: Color(hex: "#4f8fcf"),
        done: Color(hex: "#5ebb8e"),
        openNext: Color(hex: "#d4a054"),
        sidebar: Color(hex: "#0e1620"),
        ink: Color(hex: "#f7fafc"),
        borderWidth: 1
    )

    static func from(appearance json: [String: Any]?) -> KosistenzPalette {
        guard let resolved = json?["resolved"] as? [String: Any] else { return .ocean }
        let colors = resolved["colors"] as? [String: Any] ?? [:]
        let width = resolved["widgetBorderWidth"] as? Int ?? 1
        return KosistenzPalette(
            pageBg: Color(hex: string(colors["pageBg"]), fallback: ocean.pageBg),
            widgetBg: Color(hex: string(colors["widgetBg"]), fallback: ocean.widgetBg),
            widgetBorder: Color(hex: string(colors["widgetBorder"]), fallback: ocean.widgetBorder),
            titles: Color(hex: string(colors["titles"]), fallback: ocean.titles),
            accent: Color(hex: string(colors["accent"]), fallback: ocean.accent),
            done: Color(hex: string(colors["done"]), fallback: ocean.done),
            openNext: Color(hex: string(colors["openNext"]), fallback: ocean.openNext),
            sidebar: Color(hex: string(colors["sidebar"]), fallback: ocean.sidebar),
            ink: Color(hex: string(resolved["ink"]), fallback: ocean.ink),
            borderWidth: CGFloat(max(0, min(8, width)))
        )
    }

    private static func string(_ raw: Any?) -> String {
        raw as? String ?? ""
    }
}

extension Color {
    init(hex: String, fallback: Color = .primary) {
        var text = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.hasPrefix("#") { text.removeFirst() }
        guard text.count == 6, let value = UInt64(text, radix: 16) else {
            self = fallback
            return
        }
        let r = Double((value >> 16) & 0xFF) / 255
        let g = Double((value >> 8) & 0xFF) / 255
        let b = Double(value & 0xFF) / 255
        self = Color(red: r, green: g, blue: b)
    }
}
