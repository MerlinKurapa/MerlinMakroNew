import json
import os
import subprocess
import sys
import threading
import time

import webview

from auth_utils import (
    APPDATA_PATH,
    TOKEN_PATH,
    clear_session,
    get_remembered_email,
    login_async,
    try_auto_login,
)
from window_utils import center_position

MACRO_EXE = "MerlinMakro.exe"
WINDOW = None
DB = None


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def ui_path(*parts):
    return os.path.join(resource_path("ui"), "launcher", *parts)


def exe_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))





def launch_macro(email):
    directory = exe_dir()
    macro_path = os.path.join(directory, MACRO_EXE)
    if not os.path.exists(macro_path):
        _js_error(f"{MACRO_EXE} bulunamadı.")
        return

    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        f.write("ok")

    if WINDOW:
        WINDOW.evaluate_js("window.onLaunchReady && window.onLaunchReady()")

    subprocess.Popen(
        [macro_path, email],
        cwd=directory,
        shell=False,
    )

    if WINDOW:
        WINDOW.destroy()


def _js_error(message):
    safe = json.dumps(str(message))
    if WINDOW:
        WINDOW.evaluate_js(f"window.onLoginError && window.onLoginError({safe})")


def _js_success():
    if WINDOW:
        WINDOW.evaluate_js("window.onLoginSuccess && window.onLoginSuccess()")


class LauncherApi:
    def get_remembered_email(self):
        return get_remembered_email()

    def try_auto_login(self):
        def ok(email):
            _js_success()
            launch_macro(email)

        def err(msg):
            _js_error(msg)

        try_auto_login(ok, err)

    def login(self, email, password, remember_me):
        def ok(user_email):
            _js_success()
            launch_macro(user_email)

        def err(msg):
            _js_error(msg)

        login_async(email, password, remember_me, ok, err)

    def close_app(self):
        if WINDOW:
            WINDOW.destroy()


def main():
    global WINDOW
    os.makedirs(APPDATA_PATH, exist_ok=True)
    html = ui_path("index.html")
    w, h = 480, 620
    cx, cy = center_position(w, h)

    WINDOW = webview.create_window(
        "Merlin Makro Launcher",
        html,
        js_api=LauncherApi(),
        width=w,
        height=h,
        x=cx,
        y=cy,
        resizable=False,
        frameless=True,
        easy_drag=True,
        background_color="#060b16",
    )
    webview.start(gui="edgechromium", debug=False)


if __name__ == "__main__":
    main()
