# ================= ANTI DEBUG =================
import ctypes
import hashlib
import json
import os
import random
import subprocess
import sys
import threading
import time

import keyboard
import psutil
import pydirectinput as pdi
import webview
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore

from auth_utils import TOKEN_PATH, clear_session, get_hwid, check_github_update, download_update
from window_utils import center_position

pdi.PAUSE = 0
pdi.FAILSAFE = False


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def ui_path(*parts):
    return os.path.join(resource_path("ui"), "macro", *parts)


APPDATA_PATH = os.path.join(os.getenv("LOCALAPPDATA", ""), "MerlinMakro")
os.makedirs(APPDATA_PATH, exist_ok=True)
CONFIG_PATH = os.path.join(APPDATA_PATH, "MerlinMakro_ayarlar.json")

DEFAULT_POINTS = [
    (1778, 261),
    (1779, 292),
    (1815, 259),
    (1815, 294),
    (1845, 258),
    (1846, 293),
]

DEFAULT_SETTINGS = {
    "move_pause": 0.020,
    "hold_time": 0.015,
    "gap_between_clicks": 0.015,
    "delay_min": 0.008,
    "delay_max": 0.010,
}


def anti_debug():
    if sys.gettrace():
        os._exit(1)
    try:
        if ctypes.windll.kernel32.IsDebuggerPresent():
            os._exit(1)
    except Exception:
        pass

    blacklist = {
        "cheatengine.exe",
        "cheat engine.exe",
        "x64dbg.exe",
        "x32dbg.exe",
        "ollydbg.exe",
        "ida.exe",
        "ida64.exe",
        "wireshark.exe",
        "processhacker.exe",
    }
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info["name"]
            if name and name.lower() in blacklist:
                os._exit(1)
        except Exception:
            pass


anti_debug()


# ================= LAUNCHER LOCK =================
if not os.path.exists(TOKEN_PATH):
    sys.exit(1)
try:
    os.remove(TOKEN_PATH)
except Exception:
    pass

if len(sys.argv) < 2:
    sys.exit(1)

USER_EMAIL = sys.argv[1].strip().lower()
WINDOW = None


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
        # HWID yoksa kaydet
        doc_ref.update({"hwid": hwid})
    elif saved_hwid != hwid:
        # HWID uyuşmazlığı - ama kapatma, sadece uyarı ver
        print(f"HWID uyuşmazlığı: Kayıtlı={saved_hwid[:8]}..., Mevcut={hwid[:8]}...")
        # Kullanıcıya izin ver, log tut


class MacroEngine:
    def __init__(self):
        self.running = False
        self.bag_running = False
        self.skill_running = False
        self.move_pause = DEFAULT_SETTINGS["move_pause"]
        self.hold_time = DEFAULT_SETTINGS["hold_time"]
        self.gap_between_clicks = DEFAULT_SETTINGS["gap_between_clicks"]
        self.delay_min = DEFAULT_SETTINGS["delay_min"]
        self.delay_max = DEFAULT_SETTINGS["delay_max"]
        self.run_count = 1
        self.points = list(DEFAULT_POINTS)
        self.slot_meta = [{"locked": False, "disabled": False} for _ in self.points]
        self.capture_active = False
        self.capture_slot = 0
        self.status = "🟢 Hazır"
        self.top_status = "Hazır"
        self._capture_thread = None
        self._load_config()

    def _sync_meta(self):
        while len(self.slot_meta) < len(self.points):
            self.slot_meta.append({"locked": False, "disabled": False})
        self.slot_meta = self.slot_meta[: len(self.points)]

    def _load_config(self):
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.move_pause = data.get("move_pause", self.move_pause)
            self.hold_time = data.get("hold_time", self.hold_time)
            self.gap_between_clicks = data.get("gap_between_clicks", self.gap_between_clicks)
            self.delay_min = data.get("delay_min", self.delay_min)
            self.delay_max = data.get("delay_max", self.delay_max)
            pts = data.get("points")
            if isinstance(pts, list) and pts:
                self.points = [tuple(p) for p in pts]
            meta = data.get("slot_meta")
            if isinstance(meta, list) and meta:
                self.slot_meta = meta
            self._sync_meta()
        except Exception:
            pass

    def save_config(self):
        self._sync_meta()
        data = {
            "move_pause": self.move_pause,
            "hold_time": self.hold_time,
            "gap_between_clicks": self.gap_between_clicks,
            "delay_min": self.delay_min,
            "delay_max": self.delay_max,
            "points": self.points,
            "slot_meta": self.slot_meta,
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _push_coords(self):
        if WINDOW:
            pts = json.dumps(self.points)
            meta = json.dumps(self.slot_meta)
            WINDOW.evaluate_js(
                f"window.onCoordsUpdated && window.onCoordsUpdated({pts}, {meta})"
            )

    def _push_capture(self):
        if WINDOW:
            active = "true" if self.capture_active else "false"
            WINDOW.evaluate_js(f"window.onCaptureState && window.onCaptureState({active})")

    def _push_status(self):
        if WINDOW:
            safe = json.dumps(self.status)
            WINDOW.evaluate_js(f"window.onStatus && window.onStatus({safe})")

    def _push_top(self):
        if WINDOW:
            safe = json.dumps(self.top_status)
            WINDOW.evaluate_js(f"window.onTopStatus && window.onTopStatus({safe})")

    def set_coord(self, slot, x, y):
        if 0 <= slot < len(self.points):
            pts = list(self.points)
            pts[slot] = (int(x), int(y))
            self.points = pts

    def add_coord(self):
        x, y = pdi.position()
        self.points.append((int(x), int(y)))
        self.slot_meta.append({"locked": False, "disabled": False})
        self.capture_slot = len(self.points) - 1
        self._push_coords()

    def delete_coord(self, slot):
        if len(self.points) <= 1:
            return
        if 0 <= slot < len(self.points):
            self.points.pop(slot)
            self.slot_meta.pop(slot)
            self.capture_slot = min(self.capture_slot, len(self.points) - 1)
            self._push_coords()

    def toggle_lock(self, slot):
        if 0 <= slot < len(self.slot_meta):
            self.slot_meta[slot]["locked"] = not self.slot_meta[slot]["locked"]
            self._push_coords()

    def toggle_disable(self, slot):
        if 0 <= slot < len(self.slot_meta):
            self.slot_meta[slot]["disabled"] = not self.slot_meta[slot]["disabled"]
            self._push_coords()

    def select_slot(self, slot):
        if 0 <= slot < len(self.points):
            self.capture_slot = slot

    def save_coords(self):
        self.save_config()

    def save_settings(self):
        self.save_config()

    def reset_settings(self):
        self.move_pause = DEFAULT_SETTINGS["move_pause"]
        self.hold_time = DEFAULT_SETTINGS["hold_time"]
        self.gap_between_clicks = DEFAULT_SETTINGS["gap_between_clicks"]
        self.delay_min = DEFAULT_SETTINGS["delay_min"]
        self.delay_max = DEFAULT_SETTINGS["delay_max"]
        self.save_config()
        return self.get_settings_payload()

    def get_settings_payload(self):
        return [
            {"key": "move_pause", "label": "Move", "min": 1, "max": 100, "value": int(self.move_pause * 1000), "display": f"{self.move_pause:.3f}"},
            {"key": "hold_time", "label": "Hold", "min": 1, "max": 100, "value": int(self.hold_time * 1000), "display": f"{self.hold_time:.3f}"},
            {"key": "gap_between_clicks", "label": "Gap", "min": 1, "max": 100, "value": int(self.gap_between_clicks * 1000), "display": f"{self.gap_between_clicks:.3f}"},
            {"key": "delay_min", "label": "Delay Min", "min": 1, "max": 100, "value": int(self.delay_min * 1000), "display": f"{self.delay_min:.3f}"},
            {"key": "delay_max", "label": "Delay Max", "min": 1, "max": 100, "value": int(self.delay_max * 1000), "display": f"{self.delay_max:.3f}"},
        ]

    def _capture_loop(self):
        print("Capture loop started")
        while self.capture_active:
            try:
                x, y = pdi.position()
                slot = self.capture_slot
                if 0 <= slot < len(self.points):
                    pts = list(self.points)
                    pts[slot] = (int(x), int(y))
                    self.points = pts
                    self._push_coords()
                    print(f"Updated slot {slot} to ({x}, {y})")
            except Exception as e:
                print(f"Capture loop error: {e}")
                pass
            time.sleep(0.08)
        print("Capture loop stopped")

    def toggle_capture(self):
        self.capture_active = not self.capture_active
        self.status = "Canlı takip açık" if self.capture_active else "🟢 Hazır"
        self._push_status()
        self._push_capture()
        print(f"Toggle capture: {self.capture_active}")
        if self.capture_active and (not self._capture_thread or not self._capture_thread.is_alive()):
            print("Starting capture thread")
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()

    def capture_once(self):
        x, y = pdi.position()
        slot = self.capture_slot
        if 0 <= slot < len(self.points):
            pts = list(self.points)
            pts[slot] = (int(x), int(y))
            self.points = pts
            self._push_coords()
            self.status = f"Slot {slot + 1} yakalandı"
            self._push_status()

    def set_setting(self, key, value):
        mapped = {
            "move_pause": "move_pause",
            "hold_time": "hold_time",
            "gap_between_clicks": "gap_between_clicks",
            "delay_min": "delay_min",
            "delay_max": "delay_max",
        }
        attr = mapped.get(key)
        if attr:
            setattr(self, attr, value / 1000.0)

    def active_points(self):
        pts = []
        for i, p in enumerate(self.points):
            if i < len(self.slot_meta) and self.slot_meta[i].get("disabled"):
                continue
            pts.append(p)
        return pts

    def macro_worker(self, coords):
        for _ in range(self.run_count):
            for x, y in coords:
                if not self.running:
                    return
                pdi.moveTo(x, y, duration=0)
                time.sleep(self.move_pause)
                for _ in range(2):
                    pdi.mouseDown(button="right")
                    time.sleep(self.hold_time)
                    pdi.mouseUp(button="right")
                    time.sleep(self.gap_between_clicks)
                time.sleep(random.uniform(self.delay_min, self.delay_max))
        self.status = "Bitti."
        self.running = False
        self._push_status()

    def bag_worker(self):
        open_x, open_y = 956, 6855
        loot_x, loot_y = 223, 1405
        while self.bag_running:
            pdi.moveTo(open_x, open_y, duration=0)
            pdi.mouseDown(button="left")
            time.sleep(0.02)
            pdi.mouseUp(button="left")
            time.sleep(1.0)
            pdi.moveTo(loot_x, loot_y, duration=0)
            pdi.mouseDown(button="right")
            time.sleep(0.02)
            pdi.mouseUp(button="right")
            time.sleep(1.0)

    def skill_worker(self):
        keys_fast = ["1", "2"]
        keys_slow = ["tab", "`"]
        space_interval = 4
        slow_interval = 8
        space_timer = time.time()

        for key in keys_slow:
            if not self.skill_running:
                return
            keyboard.press(key)
            time.sleep(0.02)
            keyboard.release(key)
            time.sleep(0.05)

        keyboard.press_and_release("space")
        keyboard.press_and_release("tab")
        keyboard.press_and_release("tab")
        slow_timer = time.time()

        while self.skill_running:
            for key in keys_fast:
                if not self.skill_running:
                    return
                keyboard.press(key)
                time.sleep(0.01)
                keyboard.release(key)
                time.sleep(0.03)

            if time.time() - slow_timer >= slow_interval:
                for key in keys_slow:
                    if not self.skill_running:
                        return
                    keyboard.press(key)
                    time.sleep(0.02)
                    keyboard.release(key)
                    time.sleep(0.05)
                keyboard.press_and_release("tab")
                slow_timer = time.time()

            if time.time() - space_timer >= space_interval:
                if self.skill_running:
                    keyboard.press_and_release("space")
                space_timer = time.time()

    def start_item(self, run_count=1):
        if self.running:
            return
        self.bag_running = False
        self.skill_running = False
        self.run_count = max(1, int(run_count))
        self.running = True
        self.status = "Item Aktif"
        self._push_status()
        coords = self.active_points()
        if not coords:
            self.status = "Aktif koordinat yok"
            self.running = False
            self._push_status()
            return
        threading.Thread(target=self.macro_worker, args=(coords,), daemon=True).start()

    def toggle_bag(self):
        self.bag_running = not self.bag_running
        if self.bag_running:
            self.top_status = "Torba Açık"
            self._push_top()
            threading.Thread(target=self.bag_worker, daemon=True).start()
        else:
            self.status = "Torba Kapalı"
            self._push_status()

    def toggle_skill(self):
        self.skill_running = not self.skill_running
        if self.skill_running:
            self.status = "Skill Açık"
            self._push_status()
            threading.Thread(target=self.skill_worker, daemon=True).start()
        else:
            self.status = "Skill Kapalı"
            self._push_status()

    def stop_all(self):
        self.running = False
        self.bag_running = False
        self.skill_running = False
        self.status = "🟢 Hazır"
        self.top_status = "Hazır"
        self._push_status()
        self._push_top()


ENGINE = MacroEngine()
DB = None


class MacroApi:
    def get_state(self):
        return {
            "email": USER_EMAIL,
            "points": ENGINE.points,
            "slot_meta": ENGINE.slot_meta,
            "capture_active": ENGINE.capture_active,
            "settings": ENGINE.get_settings_payload(),
            "status": ENGINE.status,
            "top_status": ENGINE.top_status,
        }

    def check_update(self):
        """Güncelleme kontrolü yap"""
        def worker():
            try:
                update_info = check_github_update()
                if WINDOW:
                    WINDOW.evaluate_js(f"window.onUpdateCheck && window.onUpdateCheck({json.dumps(update_info)})")
            except Exception as e:
                print(f"Update check error: {e}")
                if WINDOW:
                    WINDOW.evaluate_js(f"window.onUpdateCheck && window.onUpdateCheck({json.dumps({'has_update': False, 'error': str(e)})})")

        threading.Thread(target=worker, daemon=True).start()

    def download_update(self):
        """Güncellemeyi indir"""
        def worker():
            try:
                import tempfile
                temp_dir = tempfile.gettempdir()
                setup_path = os.path.join(temp_dir, "MerlinMakro_Setup.exe")
                
                if download_update(setup_path):
                    if WINDOW:
                        WINDOW.evaluate_js(f"window.onUpdateDownload && window.onUpdateDownload({json.dumps({'success': True, 'path': setup_path})})")
                else:
                    if WINDOW:
                        WINDOW.evaluate_js(f"window.onUpdateDownload && window.onUpdateDownload({json.dumps({'success': False})})")
            except Exception as e:
                print(f"Download error: {e}")
                if WINDOW:
                    WINDOW.evaluate_js(f"window.onUpdateDownload && window.onUpdateDownload({json.dumps({'success': False, 'error': str(e)})})")

        threading.Thread(target=worker, daemon=True).start()

    def open_file(self, file_path):
        """Dosyayı aç"""
        try:
            os.startfile(file_path)
        except Exception:
            subprocess.Popen([file_path], shell=True)

    def set_coord(self, slot, x, y):
        ENGINE.set_coord(slot, x, y)

    def add_coord(self):
        ENGINE.add_coord()

    def delete_coord(self, slot):
        ENGINE.delete_coord(slot)

    def toggle_lock(self, slot):
        ENGINE.toggle_lock(slot)

    def toggle_disable(self, slot):
        ENGINE.toggle_disable(slot)

    def select_slot(self, slot):
        ENGINE.select_slot(slot)

    def save_coords(self):
        ENGINE.save_coords()

    def save_settings(self):
        ENGINE.save_settings()

    def reset_settings(self):
        return {"settings": ENGINE.reset_settings()}

    def set_setting(self, key, value):
        ENGINE.set_setting(key, value)

    def start_item(self, run_count):
        ENGINE.start_item(run_count)

    def toggle_bag(self):
        ENGINE.toggle_bag()

    def toggle_skill(self):
        ENGINE.toggle_skill()

    def stop_all(self):
        ENGINE.stop_all()

    def logout(self):
        clear_session()
        directory = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
        launcher = os.path.join(directory, "Launcher.exe")
        if os.path.exists(launcher):
            subprocess.Popen([launcher], cwd=directory, shell=False)
        if WINDOW:
            WINDOW.destroy()
        os._exit(0)


def setup_hotkeys():
    keyboard.add_hotkey("f2", ENGINE.start_item)
    keyboard.add_hotkey("f3", ENGINE.toggle_bag)
    keyboard.on_press_key(79, lambda _: ENGINE.toggle_skill())
    keyboard.add_hotkey("f6", ENGINE.capture_once)


def bootstrap_and_run():
    global WINDOW, DB

    def worker():
        global DB
        try:
            DB = init_firebase()
            check_firebase_hwid(DB, USER_EMAIL)
        except Exception as exc:
            print("Firebase:", exc)
            # HWID uyuşmazlığı durumunda kapatma, sadece logla
            if "başka bir bilgisayara ait" not in str(exc):
                # Sadece kritik hatalarda kapat
                if WINDOW:
                    WINDOW.destroy()
                os._exit(1)

    threading.Thread(target=worker, daemon=True).start()
    setup_hotkeys()

    html = ui_path("index.html")
    w, h = 1080, 700
    cx, cy = center_position(w, h)
    WINDOW = webview.create_window(
        "Merlin Makro",
        html,
        js_api=MacroApi(),
        width=w,
        height=h,
        x=cx,
        y=cy,
        min_size=(900, 620),
        background_color="#060b16",
    )
    webview.start(gui="edgechromium", debug=False)


if __name__ == "__main__":
    bootstrap_and_run()
