import base64
import hashlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
import urllib.request

import requests
from cryptography.fernet import Fernet

API_KEY = "AIzaSyBYD6vInN6WBN5HWuhKA6lgTgpqUyMt7xw"
APPDATA_PATH = os.path.join(os.getenv("LOCALAPPDATA", ""), "MerlinMakro")
SESSION_PATH = os.path.join(APPDATA_PATH, "session.json")
USER_PATH = os.path.join(APPDATA_PATH, "current_user.json")
TOKEN_PATH = os.path.join(APPDATA_PATH, "launcher.token")
KEY_PATH = os.path.join(APPDATA_PATH, ".session_key")


def ensure_appdata():
    os.makedirs(APPDATA_PATH, exist_ok=True)


def _machine_key():
    ensure_appdata()
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)
    return key


def _encrypt(text):
    if not text:
        return ""
    return base64.urlsafe_b64encode(
        Fernet(_machine_key()).encrypt(text.encode("utf-8"))
    ).decode("ascii")


def _decrypt(token):
    if not token:
        return ""
    try:
        raw = Fernet(_machine_key()).decrypt(base64.urlsafe_b64decode(token.encode("ascii")))
        return raw.decode("utf-8")
    except Exception:
        return ""


def get_hwid():
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-WindowStyle",
                "Hidden",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystemProduct).UUID",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        uuid = (result.stdout or "").strip()
        if uuid and uuid.lower() != "uuid":
            return hashlib.sha256(uuid.encode()).hexdigest()
    except Exception:
        pass
    fallback = f"{platform.node()}-{platform.processor()}"
    return hashlib.sha256(fallback.encode()).hexdigest()


def firebase_login(email, password):
    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        f"?key={API_KEY}"
    )
    payload = {
        "email": email.strip(),
        "password": password,
        "returnSecureToken": True,
    }
    r = requests.post(url, json=payload, timeout=20)
    if r.status_code != 200:
        err = r.json().get("error", {}).get("message", "Giriş başarısız.")
        raise RuntimeError(err)
    return r.json()


def firebase_refresh(refresh_token):
    url = f"https://securetoken.googleapis.com/v1/token?key={API_KEY}"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    r = requests.post(url, json=payload, timeout=20)
    if r.status_code != 200:
        raise RuntimeError("Oturum süresi doldu.")
    return r.json()


def save_session(email, id_token, refresh_token, remember_me):
    ensure_appdata()
    data = {
        "email": email.strip().lower(),
        "remember_me": bool(remember_me),
        "id_token": id_token,
        "refresh_token_enc": _encrypt(refresh_token) if remember_me else "",
        "saved_at": int(time.time()),
    }
    with open(SESSION_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    with open(USER_PATH, "w", encoding="utf-8") as f:
        json.dump({"email": data["email"]}, f)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        f.write("ok")


def load_session():
    if not os.path.exists(SESSION_PATH):
        return None
    try:
        with open(SESSION_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_remembered_email():
    session = load_session()
    if session and session.get("remember_me"):
        return session.get("email", "")
    return ""


def try_auto_login(on_success, on_error):
    def worker():
        try:
            session = load_session()
            if not session or not session.get("remember_me"):
                on_error("no_session")
                return

            refresh_enc = session.get("refresh_token_enc", "")
            refresh_token = _decrypt(refresh_enc)
            if not refresh_token:
                on_error("no_token")
                return

            data = firebase_refresh(refresh_token)
            email = data.get("user_id") or session.get("email", "")
            # refresh response uses localId sometimes; keep stored email
            email = session.get("email", email)
            save_session(
                email,
                data.get("id_token", ""),
                data.get("refresh_token", refresh_token),
                True,
            )
            on_success(email)
        except Exception as exc:
            on_error(str(exc))

    threading.Thread(target=worker, daemon=True).start()


def clear_session():
    ensure_appdata()
    for path in (SESSION_PATH, USER_PATH, TOKEN_PATH):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def login_async(email, password, remember_me, on_success, on_error):
    def worker():
        try:
            data = firebase_login(email, password)
            email_norm = email.strip().lower()
            save_session(
                email_norm,
                data.get("idToken", ""),
                data.get("refreshToken", ""),
                remember_me,
            )
            on_success(email_norm)
        except Exception as exc:
            on_error(str(exc))

    threading.Thread(target=worker, daemon=True).start()


# GitHub Update System
GITHUB_REPO = "MerlinKurapa/MerlinMakroNew"  # GitHub repository bilgisi
CURRENT_VERSION = "5.7"  # Mevcut sürüm - her güncellemede bunu değiştirin


def check_github_update():
    """GitHub'da yeni sürüm var mı kontrol et"""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            release_data = response.json()
            latest_version = release_data.get("tag_name", "").replace("v", "")
            
            # Sürüm karşılaştırma
            if latest_version != CURRENT_VERSION:
                return {
                    "has_update": True,
                    "current_version": CURRENT_VERSION,
                    "latest_version": latest_version,
                    "download_url": release_data.get("html_url", ""),
                    "release_notes": release_data.get("body", "")
                }
    except Exception as e:
        print(f"Update check failed: {e}")
    return {"has_update": False}


def download_update(save_path):
    """Güncellemeyi indir ve kur"""
    try:
        # GitHub assets'tan setup dosyasını bul
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            release_data = response.json()
            assets = release_data.get("assets", [])

            # Setup dosyasını bul
            setup_asset = None
            for asset in assets:
                if "setup" in asset.get("name", "").lower():
                    setup_asset = asset
                    break

            if setup_asset:
                download_url = setup_asset.get("browser_download_url")
                urllib.request.urlretrieve(download_url, save_path)

                # İndirme başarılı
                print("Update downloaded, starting uninstall...")

                # 1. Önce uninstall çalıştır (eski sürümü kaldır)
                uninstall_path = r"C:\Program Files (x86)\MerlinMakro\unins000.exe"
                if os.path.exists(uninstall_path):
                    subprocess.Popen([uninstall_path, "/SILENT"], shell=True)
                    time.sleep(3)  # Uninstall'ın tamamlanması için bekle

                # 2. Yeni setup'ı çalıştır
                print("Installing new version...")
                subprocess.Popen([save_path, "/VERYSILENT", "/SUPPRESSMSGBOXES"], shell=True)

                # 3. Uygulamayı kapat
                if getattr(sys, "frozen", False):
                    # PyInstaller ile derlenmiş
                    os.system("taskkill /F /IM MerlinMakro.exe")
                    os.system("taskkill /F /IM Launcher.exe")
                else:
                    # Geliştirme modu
                    os._exit(0)

                return True
    except Exception as e:
        print(f"Download failed: {e}")
    return False
