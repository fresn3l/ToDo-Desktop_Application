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
                # WKNavigationTypeOther == 5: paste/drop of a URL.
                nav_type = int(navigationAction.navigationType())
                if nav_type == 5 and scheme in ("http", "https", "webcal"):
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
            from AppKit import NSPasteboard, NSPasteboardTypeString
            from Foundation import NSURL

            text = None
            try:
                pb = NSPasteboard.generalPasteboard()
                types = [str(t) for t in (pb.types() or [])]
                if "public.url" in types or "NSURLPboardType" in types:
                    objs = pb.readObjectsForClasses_options_([NSURL], None)
                    if objs:
                        text = str(objs[0].absoluteString())
                if not text:
                    text = pb.stringForType_(NSPasteboardTypeString)
            except Exception:
                text = None
            if text and (
                "https://" in text.lower()
                or "http://" in text.lower()
                or "webcal://" in text.lower()
            ):
                js = f"window.kosistenzInsertText && window.kosistenzInsertText({json.dumps(str(text))})"
                try:
                    self.evaluateJavaScript_completionHandler_(js, None)
                    return
                except Exception:
                    pass
            WKWebView.paste_(self, sender)

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
    window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
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

    request = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
    web.loadRequest_(request)

    _KEEP.extend(
        [app, app_delegate, window, win_delegate, nav_delegate, ui_delegate, config, web, script, KosistenzWebView]
    )

    window.makeKeyAndOrderFront_(None)
    app.activateIgnoringOtherApps_(True)
    app.run()
    try:
        on_close()
    except Exception:
        pass
    os._exit(0)
