"""
Native macOS window for source runs: Cocoa + WKWebView.

The installed .app uses macos/KosistenzWindow.swift instead. This module is
the fallback when running `python main.py` / ./run_kosistenz.sh, or if the
Swift host could not be compiled into the bundle.
"""

from __future__ import annotations

import json
import os
import sys

_KEEP: list = []


def available() -> bool:
    if sys.platform != "darwin":
        return False
    try:
        import AppKit  # noqa: F401
        import WebKit  # noqa: F401
    except Exception:
        return False
    return True


def _rect(x: float, y: float, w: float, h: float):
    try:
        from Foundation import NSMakeRect

        return NSMakeRect(x, y, w, h)
    except Exception:
        return ((float(x), float(y)), (float(w), float(h)))


def _size(w: float, h: float):
    try:
        from Foundation import NSMakeSize

        return NSMakeSize(w, h)
    except Exception:
        return (float(w), float(h))


def run_mac_window(url: str, width: int, height: int, min_width: int, min_height: int, on_close) -> None:
    from urllib.parse import urlparse

    from AppKit import (
        NSAlert,
        NSAlertFirstButtonReturn,
        NSApplication,
        NSApplicationActivationPolicyRegular,
        NSBackingStoreBuffered,
        NSTextField,
        NSViewHeightSizable,
        NSViewWidthSizable,
        NSWindow,
        NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable,
        NSWindowStyleMaskResizable,
        NSWindowStyleMaskTitled,
    )
    from Foundation import NSObject, NSURL, NSURLRequest
    from WebKit import WKUserScript, WKWebView, WKWebViewConfiguration

    allowed = urlparse(url)
    allowed_port = int(allowed.port or 0)

    class AppDelegate(NSObject):
        def applicationShouldTerminateAfterLastWindowClosed_(self, _app):
            return True

        def applicationWillTerminate_(self, _notification):
            try:
                on_close()
            except Exception:
                pass

    class NavigationDelegate(NSObject):
        def webView_decidePolicyForNavigationAction_decisionHandler_(
            self, webView, navigationAction, decisionHandler
        ):
            allow = 1
            cancel = 0
            try:
                url = navigationAction.request().URL()
                host = str(url.host() or "").lower()
                scheme = str(url.scheme() or "").lower()
                port_val = url.port()
                if port_val is None:
                    port_int = 443 if scheme == "https" else 80
                else:
                    port_int = int(port_val)
                if (
                    scheme in ("http", "https")
                    and host in ("127.0.0.1", "localhost")
                    and port_int == allowed_port
                ):
                    decisionHandler(allow)
                    return
                # Any off-app http(s)/webcal load is a paste/drop, not a page.
                if scheme in ("http", "https", "webcal"):
                    pasted = str(url.absoluteString())
                    js = f"window.kosistenzInsertText && window.kosistenzInsertText({json.dumps(pasted)})"
                    try:
                        webView.evaluateJavaScript_completionHandler_(js, None)
                    except Exception:
                        pass
                    decisionHandler(cancel)
                    return
            except Exception:
                pass
            decisionHandler(cancel)

    class KosistenzWebView(WKWebView):
        def paste_(self, sender):
            self._paste_from_clipboard()

        def performKeyEquivalent_(self, event):
            try:
                if int(event.type()) == 10 and event.modifierFlags() & (1 << 20):
                    if event.modifierFlags() & ((1 << 17) | (1 << 19)):
                        return WKWebView.performKeyEquivalent_(self, event)
                    chars = str(event.charactersIgnoringModifiers() or "").lower()
                    if chars == "v":
                        self._paste_from_clipboard()
                        return True
            except Exception:
                pass
            return WKWebView.performKeyEquivalent_(self, event)

        def _paste_from_clipboard(self):
            from AppKit import NSPasteboard, NSPasteboardTypeString, NSPasteboardTypeHTML
            from Foundation import NSURL

            text = None
            ics = None
            try:
                pb = NSPasteboard.generalPasteboard()
                types = [str(t) for t in (pb.types() or [])]
                raw = pb.stringForType_(NSPasteboardTypeString)
                if raw and "BEGIN:VCALENDAR" in str(raw).upper():
                    ics = str(raw)
                if "public.url" in types or "NSURLPboardType" in types:
                    objs = pb.readObjectsForClasses_options_([NSURL], None)
                    if objs:
                        text = str(objs[0].absoluteString())
                if not text:
                    try:
                        html = pb.stringForType_(NSPasteboardTypeHTML)
                    except Exception:
                        html = None
                    if not html:
                        try:
                            data = pb.dataForType_(NSPasteboardTypeHTML)
                            if data:
                                html = bytes(data).decode("utf-8", errors="ignore")
                        except Exception:
                            html = None
                    if html:
                        import re

                        match = re.search(r"(?:https?|webcal)://[^\s<>\"']+", str(html), re.I)
                        if match:
                            text = match.group(0).rstrip(".,;)]}>\"'")
                if not text and raw:
                    text = str(raw)
            except Exception:
                text = None
            if ics:
                js = f"window.kosistenzImportIcsText && window.kosistenzImportIcsText({json.dumps(ics)})"
                try:
                    self.evaluateJavaScript_completionHandler_(js, None)
                    return
                except Exception:
                    pass
            if text:
                js = (
                    "(function(){try{return !!(window.kosistenzInsertText && "
                    f"window.kosistenzInsertText({json.dumps(str(text))}));"
                    "}catch(e){return false;}})()"
                )
                try:
                    self.evaluateJavaScript_completionHandler_(js, None)
                    return
                except Exception:
                    pass
            WKWebView.paste_(self, None)

    class PasteWindow(NSWindow):
        webView = None

        def sendEvent_(self, event):
            try:
                if int(event.type()) == 10 and event.modifierFlags() & (1 << 20):
                    if not (event.modifierFlags() & ((1 << 17) | (1 << 19))):
                        chars = str(event.charactersIgnoringModifiers() or "").lower()
                        if chars == "v" and self.webView is not None:
                            self.webView._paste_from_clipboard()
                            return
                        if chars == "c" and self.webView is not None:
                            self.webView.copy_(None)
                            return
            except Exception:
                pass
            NSWindow.sendEvent_(self, event)

    class UIDelegate(NSObject):
        def webView_runJavaScriptAlertPanelWithMessage_initiatedByFrame_completionHandler_(
            self, _webView, message, _frame, completionHandler
        ):
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Kosistenz")
            alert.setInformativeText_(str(message or ""))
            alert.addButtonWithTitle_("OK")
            alert.runModal()
            completionHandler()

        def webView_runJavaScriptConfirmPanelWithMessage_initiatedByFrame_completionHandler_(
            self, _webView, message, _frame, completionHandler
        ):
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Kosistenz")
            alert.setInformativeText_(str(message or ""))
            alert.addButtonWithTitle_("OK")
            alert.addButtonWithTitle_("Cancel")
            completionHandler(alert.runModal() == NSAlertFirstButtonReturn)

        def webView_runJavaScriptTextInputPanelWithPrompt_defaultText_initiatedByFrame_completionHandler_(
            self, _webView, prompt, defaultText, _frame, completionHandler
        ):
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Kosistenz")
            alert.setInformativeText_(str(prompt or ""))
            alert.addButtonWithTitle_("OK")
            alert.addButtonWithTitle_("Cancel")
            field = NSTextField.alloc().initWithFrame_(_rect(0, 0, 280, 24))
            field.setStringValue_(str(defaultText or ""))
            alert.setAccessoryView_(field)
            try:
                alert.window().setInitialFirstResponder_(field)
            except Exception:
                pass
            if alert.runModal() == NSAlertFirstButtonReturn:
                completionHandler(field.stringValue())
            else:
                completionHandler(None)

    class WindowDelegate(NSObject):
        def windowWillClose_(self, _notification):
            try:
                on_close()
            except Exception:
                pass
            NSApplication.sharedApplication().terminate_(None)

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    app_delegate = AppDelegate.alloc().init()
    app.setDelegate_(app_delegate)

    style = (
        NSWindowStyleMaskTitled
        | NSWindowStyleMaskClosable
        | NSWindowStyleMaskMiniaturizable
        | NSWindowStyleMaskResizable
    )
    window = PasteWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        _rect(0, 0, width, height),
        style,
        NSBackingStoreBuffered,
        False,
    )
    window.setTitle_("Kosistenz")
    window.setMinSize_(_size(min_width, min_height))
    try:
        window.setTitlebarAppearsTransparent_(True)
        window.setTitleVisibility_(1)
    except Exception:
        pass
    window.center()

    win_delegate = WindowDelegate.alloc().init()
    window.setDelegate_(win_delegate)

    nav_delegate = NavigationDelegate.alloc().init()
    ui_delegate = UIDelegate.alloc().init()

    config = WKWebViewConfiguration.alloc().init()
    script = None
    try:
        from WebKit import WKUserScriptInjectionTimeAtDocumentStart

        inject_at = WKUserScriptInjectionTimeAtDocumentStart
    except Exception:
        try:
            from WebKit import WKUserScriptInjectionTimeAtDocumentEnd

            inject_at = WKUserScriptInjectionTimeAtDocumentEnd
        except Exception:
            inject_at = 0
    try:
        script = WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
            "document.documentElement.classList.add('native-shell');window.kosistenzNative=true;",
            inject_at,
            True,
        )
        config.userContentController().addUserScript_(script)
    except Exception:
        script = None
    try:
        config.preferences().setJavaScriptEnabled_(True)
    except Exception:
        pass

    web = KosistenzWebView.alloc().initWithFrame_configuration_(
        _rect(0, 0, width, height),
        config,
    )
    web.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
    try:
        web.setNavigationDelegate_(nav_delegate)
    except Exception:
        pass
    try:
        web.setUIDelegate_(ui_delegate)
    except Exception:
        pass
    try:
        web.setValue_forKey_(True, "drawsBackground")
    except Exception:
        pass
    window.setContentView_(web)
    window.webView = web

    request = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
    web.loadRequest_(request)

    _KEEP.extend(
        [app, app_delegate, window, win_delegate, nav_delegate, ui_delegate, config, web, script, KosistenzWebView, PasteWindow]
    )

    window.makeKeyAndOrderFront_(None)
    app.activateIgnoringOtherApps_(True)
    app.run()
    try:
        on_close()
    except Exception:
        pass
    os._exit(0)
