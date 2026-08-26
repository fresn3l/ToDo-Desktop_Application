"""
Native macOS window for source runs: Cocoa + WKWebView.

The installed .app uses macos/KosistenzWindow.swift instead. This module is
the fallback when running `python main.py` / ./run_kosistenz.sh, or if the
Swift host could not be compiled into the bundle.
"""

from __future__ import annotations

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
    from AppKit import (
        NSApplication,
        NSApplicationActivationPolicyRegular,
        NSBackingStoreBuffered,
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

    class AppDelegate(NSObject):
        def applicationShouldTerminateAfterLastWindowClosed_(self, _app):
            return True

        def applicationWillTerminate_(self, _notification):
            try:
                on_close()
            except Exception:
                pass

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
    window.center()

    win_delegate = WindowDelegate.alloc().init()
    window.setDelegate_(win_delegate)

    config = WKWebViewConfiguration.alloc().init()
    script = None
    try:
        from WebKit import WKUserScriptInjectionTimeAtDocumentEnd

        inject_at = WKUserScriptInjectionTimeAtDocumentEnd
    except Exception:
        inject_at = 1
    try:
        script = WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
            "document.documentElement.classList.add('native-shell'); window.kosistenzNative = true;",
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

    web = WKWebView.alloc().initWithFrame_configuration_(
        _rect(0, 0, width, height),
        config,
    )
    web.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
    window.setContentView_(web)

    request = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
    web.loadRequest_(request)

    _KEEP.extend([app, app_delegate, window, win_delegate, config, web, script])

    window.makeKeyAndOrderFront_(None)
    app.activateIgnoringOtherApps_(True)
    app.run()
    try:
        on_close()
    except Exception:
        pass
    os._exit(0)
