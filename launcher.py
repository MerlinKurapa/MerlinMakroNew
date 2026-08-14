import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

import webview

import firebase_admin
from firebase_admin import credentials, firestore

from auth_utils import (
    APPDATA_PATH,
    TOKEN_PATH,
    clear_session,
    get_hwid,
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


def init_firebase():
    firebase_json = resource_path(
        "merlinmakroauth-firebase-adminsdk-fbsvc-df7571c065.json"
    )
    cred = credentials.Certificate(firebase_json)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()


def check_firebase_hwid(db, user_email):
    hwid = get_hwid()
    user_doc = db.collection("users").document(user_email).get()
    if not user_doc.exists:
        raise RuntimeError("Kullanıcı Firebase'de bulunamadı.")

    data = user_doc.to_dict()
    doc_ref = db.collection("users").document(user_email)

    if not data.get("aktif"):
        raise RuntimeError("Hesap aktif değil.")

    son_kullanma = data.get("son_kullanma_tarihi")
    if son_kullanma:
        bitis = datetime.strptime(son_kullanma, "%Y-%m-%d")
        if datetime.now() > bitis:
            raise RuntimeError("Makro lisans süreniz sona ermiş.")

    saved_hwid = data.get("hwid")
    if not saved_hwid:
        doc_ref.update({"hwid": hwid})
    elif saved_hwid != hwid:
        raise RuntimeError("Bu lisans başka bir bilgisayara ait.")


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
