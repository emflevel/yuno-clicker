import ctypes
import json
import math
import os
import random
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont

VERSION = "1.0"
IS_WIN = sys.platform.startswith("win")
CONFIG_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "yunoclicker")
ERROR_LOG = os.path.join(CONFIG_DIR, "yuno_error.log")


def show_error(msg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(ERROR_LOG, "w", encoding="utf-8") as f:
            f.write(msg)
    except OSError:
        pass
    if IS_WIN:
        ctypes.windll.user32.MessageBoxW(0, msg[-1500:], "Yuno Clicker", 0x10)
    else:
        print(msg)


if IS_WIN:
    try:
        _k32 = ctypes.windll.kernel32
        _con = _k32.GetConsoleWindow()
        if _con and _k32.GetConsoleProcessList((ctypes.c_uint * 4)(), 4) <= 1:
            ctypes.windll.user32.ShowWindow(_con, 0)
    except Exception:
        pass

try:
    from pynput import keyboard, mouse
except ImportError:
    show_error("pynput is not installed for this Python.\n\nFix: open cmd and run:\n"
               f"\"{sys.executable}\" -m pip install pynput")
    sys.exit(1)

if IS_WIN:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

BG = "#0e0e11"
HEAD = "#121216"
ROW_HOVER = "#18181e"
CHIP = "#17171c"
LINE = "#232329"
TEXT = "#ededf0"
MUTED = "#80808c"
FAINT = "#4c4c57"
UI_FONT = "Segoe UI" if IS_WIN else "Helvetica"
MONO_FONT = "Consolas" if IS_WIN else "Courier"

W = 300
HEAD_H = 40
FRAME_MS = 16

BUTTONS = ("left", "right", "middle")
CONFIG_PATH = os.path.join(CONFIG_DIR, "yuno_clicker.json")
_OLD_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yuno_clicker.json")
try:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.isfile(_OLD_CONFIG) and not os.path.isfile(CONFIG_PATH):
        os.replace(_OLD_CONFIG, CONFIG_PATH)
except OSError:
    pass
DEFAULTS = {
    "cps": 0,
    "jitter": 0,
    "mode": "toggle",
    "left_key": "f6",
    "right_key": None,
    "middle_key": None,
    "gui_key": "ctrl_r",
    "always_on_top": True,
    "expanded": True,
    "accent": "#ffffff",
    "setup_done": False,
    "x": 140,
    "y": 60,
}
CPS_MIN, CPS_MAX = 1, 50
READ_CONFIG = True
SLOTS = ("left_key", "right_key", "middle_key", "gui_key")


def load_config():
    cfg = dict(DEFAULTS)
    loaded = {}
    if READ_CONFIG:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (OSError, ValueError):
            pass
    cfg.update(loaded)
    if "toggle_key" in loaded and "left_key" not in loaded:
        cfg["left_key"] = loaded["toggle_key"]
    for old in ("toggle_key", "button", "presets", "preset_index", "cycle_key"):
        cfg.pop(old, None)
    cfg["cps"] = min(max(CPS_MIN, int(cfg["cps"])), CPS_MAX)
    cfg["jitter"] = min(max(0, int(cfg["jitter"])), 30)
    return cfg


def save_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except OSError:
        pass


if IS_WIN:
    _user32 = ctypes.windll.user32
    _winmm = ctypes.windll.winmm
    _winmm.timeBeginPeriod(1)
    _FLAGS = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010), "middle": (0x0020, 0x0040)}

    def press(btn):
        _user32.mouse_event(_FLAGS[btn][0], 0, 0, 0, 0)

    def release(btn):
        _user32.mouse_event(_FLAGS[btn][1], 0, 0, 0, 0)
else:
    _mouse = mouse.Controller()

    def press(btn):
        _mouse.press(getattr(mouse.Button, btn))

    def release(btn):
        _mouse.release(getattr(mouse.Button, btn))


def precise_sleep(seconds):
    end = time.perf_counter() + seconds
    while True:
        left = end - time.perf_counter()
        if left <= 0:
            return
        if left > 0.002:
            time.sleep(left - 0.0015)


MODS = {
    "shift": "shift", "shift_l": "shift", "shift_r": "shift",
    "ctrl": "ctrl", "ctrl_l": "ctrl", "ctrl_r": "ctrl",
    "alt": "alt", "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
    "cmd": "win", "cmd_l": "win", "cmd_r": "win",
}
MOD_ORDER = ("ctrl", "shift", "alt", "win")
NICE = {
    "ctrl_r": "RIGHT CTRL", "ctrl_l": "LEFT CTRL", "shift_r": "RIGHT SHIFT", "shift_l": "LEFT SHIFT",
    "alt_r": "RIGHT ALT", "alt_l": "LEFT ALT", "alt_gr": "ALT GR", "cmd": "WIN", "cmd_l": "WIN", "cmd_r": "WIN",
    "mouse4": "MOUSE 4", "mouse5": "MOUSE 5", "page_up": "PG UP", "page_down": "PG DN",
}

_SIDE_BUTTONS = {}
for _attr, _name in (("x1", "mouse4"), ("x2", "mouse5")):
    if hasattr(mouse.Button, _attr):
        _SIDE_BUTTONS[getattr(mouse.Button, _attr)] = _name


def key_name(key):
    if isinstance(key, keyboard.Key):
        return key.name
    if isinstance(key, keyboard.KeyCode):
        vk = getattr(key, "vk", None)
        if vk and (65 <= vk <= 90 or 48 <= vk <= 57):
            return chr(vk).lower()
        if key.char and key.char.isprintable():
            return key.char.lower()
        if vk:
            return f"vk{vk}"
    return None


def pretty(bind):
    if not bind:
        return "none"
    return " + ".join(NICE.get(p, p.replace("_", " ").upper()) for p in bind.split("+"))


def mix(c1, c2, t):
    t = min(max(t, 0.0), 1.0)
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class App:
    def __init__(self):
        self.cfg = load_config()
        self.active = {b: False for b in BUTTONS}
        self.boost = {b: 0 for b in BUTTONS}
        self.binding = "gui_key" if not self.cfg["setup_done"] else None
        self.pending_mod = None
        self.down = set()
        self.mouse_over = False
        self.running = True
        self.visible = True
        self.gui_toggle_req = False
        self.hits = []
        self.hover = None
        self.dragging = None
        self.moving = None
        self.anim = {}
        self.cur_geo = None
        self.last_sig = None
        self.content_h = HEAD_H

        self.root = tk.Tk()
        self.root.title(f"Yuno Clicker v{VERSION}")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", self.cfg["always_on_top"])
        self.root.configure(bg=BG)
        self.S = max(1.0, self.root.winfo_fpixels("1i") / 96.0)

        self.f_brand = tkfont.Font(family=UI_FONT, size=10, weight="bold")
        self.f_ui = tkfont.Font(family=UI_FONT, size=9)
        self.f_ui_b = tkfont.Font(family=UI_FONT, size=9, weight="bold")
        self.f_small = tkfont.Font(family=UI_FONT, size=8)
        self.f_section = tkfont.Font(family=UI_FONT, size=7, weight="bold")
        self.f_title = tkfont.Font(family=UI_FONT, size=11, weight="bold")
        self.f_mono = tkfont.Font(family=MONO_FONT, size=9)
        self.f_mono_b = tkfont.Font(family=MONO_FONT, size=9, weight="bold")
        self.f_mono_big = tkfont.Font(family=MONO_FONT, size=12, weight="bold")

        self.cv = tk.Canvas(self.root, width=round(W * self.S), height=round(600 * self.S), bg=BG,
                            highlightthickness=0)
        self.cv.place(x=0, y=0)
        self.cv.bind("<Button-1>", self.on_down)
        self.cv.bind("<B1-Motion>", self.on_motion)
        self.cv.bind("<ButtonRelease-1>", self.on_up)
        self.cv.bind("<Button-3>", self.on_right)
        self.cv.bind("<Motion>", self.on_hover)
        self.cv.bind("<Leave>", lambda e: setattr(self, "hover", None))
        self.draw()
        final_h = self.content_h if (not self.cfg["setup_done"] or self.cfg["expanded"]) else HEAD_H
        self.cfg["x"] = (self.root.winfo_screenwidth() - round(W * self.S)) // 2
        self.cfg["y"] = (self.root.winfo_screenheight() - round(final_h * self.S)) // 2
        self.set_geometry(final_h)
        self.root.after(60, self.round_corners)

        for b in BUTTONS:
            threading.Thread(target=self.click_loop, args=(b,), daemon=True).start()
        self.kb = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.ms = mouse.Listener(on_click=self.on_mouse_click)
        self.kb.start()
        self.ms.start()
        self.root.after(FRAME_MS, self.tick)

    @property
    def accent(self):
        return self.cfg.get("accent") or "#ffffff"

    def m(self, font, text):
        return font.measure(text) / self.S

    def lw(self, n=1):
        return max(1, round(n * self.S))

    def ease(self, key, target, k=0.22):
        self.anim[key] = target
        return target

    def hov(self, hid, k=0.3):
        return self.ease("hov:" + hid, 1.0 if self.hover == hid else 0.0, k)

    def set_geometry(self, h):
        geo = (round(W * self.S), round(h * self.S))
        if geo != self.cur_geo:
            self.cur_geo = geo
            self.root.geometry(f"{geo[0]}x{geo[1]}+{int(self.cfg['x'])}+{int(self.cfg['y'])}"
                               if self.anim.get("placed") is None else f"{geo[0]}x{geo[1]}")
            self.anim["placed"] = 1

    def round_corners(self):
        if not IS_WIN:
            return
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            dwm = ctypes.windll.dwmapi
            pref = ctypes.c_int(2)
            dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), 4)
            r, g, b = (int(LINE[i:i + 2], 16) for i in (1, 3, 5))
            colour = ctypes.c_int(r | (g << 8) | (b << 16))
            dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(colour), 4)
        except Exception:
            pass

    def add_hit(self, hid, box, click=None, right=None, drag=None):
        self.hits.append({"id": hid, "box": box, "click": click, "right": right, "drag": drag})

    def header(self, setup=False):
        c, a = self.cv, self.accent
        c.create_rectangle(0, 0, W, HEAD_H, fill=HEAD, width=0)
        c.create_line(0, HEAD_H, W, HEAD_H, fill=LINE, width=self.lw())
        cy = HEAD_H / 2
        c.create_text(14, cy, anchor="w", text="yuno", fill=a, font=self.f_brand)
        vx = 14 + self.m(self.f_brand, "yuno") + 5
        c.create_text(vx, cy + 1, anchor="w", text="clicker", fill=MUTED, font=self.f_small)
        c.create_text(vx + self.m(self.f_small, "clicker") + 5, cy + 1, anchor="w", text=f"v{VERSION}",
                      fill=FAINT, font=self.f_small)
        if setup:
            c.create_text(W - 14, cy, anchor="e", text="setup", fill=FAINT, font=self.f_small)
            return

        ex = W - 20
        hv = self.hov("chev")
        pt = self.anim.get("open", 0.0)
        ys, ym = cy - 2 + 4 * pt, cy + 2 - 4 * pt
        c.create_line(ex - 4, ys, ex, ym, ex + 4, ys, fill=mix(MUTED, TEXT, hv), width=self.lw(1.5),
                      capstyle="round", joinstyle="round")
        self.add_hit("chev", (ex - 12, 0, W, HEAD_H), click=self.toggle_expand)

        x = ex - 18
        for b, letter in (("middle", "M"), ("right", "R"), ("left", "L")):
            t = self.ease("ind:" + b, 1.0 if self.active[b] else 0.0)
            c.create_text(x, cy, anchor="e", text=letter, fill=mix(FAINT, a, t), font=self.f_mono_b)
            x -= self.m(self.f_mono_b, letter) + 6
        x -= 8
        paused = any(self.active.values()) and self.mouse_over
        live = any(self.active.values()) and not paused
        boost = max((self.boost[b] for b in BUTTONS if self.active[b]), default=0) if live else 0
        if paused:
            tag = "paused"
        elif boost:
            tag = f"+{boost}"
        else:
            tag = ""
        if tag:
            c.create_text(x, cy, anchor="e", text=tag, fill=MUTED if paused else a, font=self.f_mono)
            x -= self.m(self.f_mono, tag) + 6
        c.create_text(x, cy, anchor="e", text=f"{self.cfg['cps']} cps", fill=TEXT if live else MUTED,
                      font=self.f_mono)

    def section(self, y, title):
        self.cv.create_text(14, y + 16, anchor="w", text=title, fill=FAINT, font=self.f_section)
        return y + 26

    def row_bg(self, y, h, hid):
        t = self.hov(hid)
        if t > 0.01:
            self.cv.create_rectangle(0, y, W, y + h, fill=mix(BG, ROW_HOVER, t), width=0)

    def bind_row(self, y, label, slot, button=None):
        c, a = self.cv, self.accent
        hid = "row:" + slot
        self.row_bg(y, 28, hid)
        cy = y + 14
        x = 14
        if button:
            t = self.ease("on:" + button, 1.0 if self.active[button] else 0.0)
            s = 3.5
            c.create_rectangle(x, cy - s, x + 2 * s, cy + s, fill=mix(BG, a, t),
                               outline=mix(FAINT, a, t), width=self.lw())
            x += 14
        c.create_text(x, cy, anchor="w", text=label, fill=TEXT, font=self.f_ui)

        if self.binding == slot:
            mods = [m for m in MOD_ORDER if any(MODS.get(d) == m for d in self.down)]
            blink = int(time.perf_counter() * 2.5) % 2 == 0
            txt = (" + ".join(m.upper() for m in mods) + " + " if mods else "") + ("_" if blink else " ")
            col = a
        else:
            txt = pretty(self.cfg[slot])
            col = TEXT if self.cfg[slot] else FAINT
        c.create_text(W - 14, cy, anchor="e", text=f"[{txt}]", fill=col, font=self.f_mono)
        self.add_hit(hid, (0, y, W, y + 28), click=lambda: self.start_binding(slot),
                     right=lambda: self.clear_bind(slot))
        return y + 28

    def option_row(self, y, label, options, current, fn, hid):
        c, a = self.cv, self.accent
        cy = y + 14
        c.create_text(14, cy, anchor="w", text=label, fill=TEXT, font=self.f_ui)
        x = W - 14
        for key, text in reversed(options):
            w = self.m(self.f_ui, text)
            sel = self.ease(f"sel:{hid}:{key}", 1.0 if current == key else 0.0)
            hv = self.hov(f"{hid}:{key}")
            c.create_text(x, cy, anchor="e", text=text, fill=mix(mix(FAINT, MUTED, hv), TEXT, sel), font=self.f_ui)
            if sel > 0.01:
                mid = x - w / 2
                half = w / 2 * sel
                c.create_line(mid - half, cy + 9, mid + half, cy + 9, fill=a, width=self.lw())
            self.add_hit(f"{hid}:{key}", (x - w - 4, y, x + 4, y + 28), click=lambda k=key: fn(k))
            x -= w + 14
        return y + 28

    def slider_row(self, y, label, value, lo, hi, unit, fn, hid):
        c, a = self.cv, self.accent
        x1, x2 = 14, W - 14
        y1, y2 = y + 4, y + 26
        dv = self.ease("sl:" + hid, value, 0.3)
        frac = (dv - lo) / (hi - lo)
        hv = self.ease("hov:" + hid, 1.0 if self.hover == hid or self.drag_id == hid else 0.0, 0.3)
        c.create_rectangle(x1, y1, x2, y2, fill=mix(CHIP, ROW_HOVER, hv), outline=LINE, width=self.lw())
        fx = x1 + frac * (x2 - x1)
        if fx > x1 + 1:
            c.create_rectangle(x1, y1, fx, y2, fill=mix(CHIP, a, 0.16 + 0.06 * hv), width=0)
            c.create_line(fx, y1, fx, y2, fill=a, width=self.lw(2))
        c.create_text(x1 + 9, (y1 + y2) / 2, anchor="w", text=label, fill=TEXT, font=self.f_ui)
        c.create_text(x2 - 9, (y1 + y2) / 2, anchor="e", text=f"{value}{unit}", fill=TEXT, font=self.f_mono_b)

        def drag(ex):
            fn(int(round(lo + (min(max(ex, x1), x2) - x1) / (x2 - x1) * (hi - lo))))

        self.add_hit(hid, (x1, y1, x2, y2), drag=drag)
        return y + 32

    def check_row(self, y, label, on, fn, hid):
        c, a = self.cv, self.accent
        self.row_bg(y, 28, hid)
        cy = y + 14
        c.create_text(14, cy, anchor="w", text=label, fill=TEXT, font=self.f_ui)
        t = self.ease("chk:" + hid, 1.0 if on else 0.0)
        bx = W - 14
        c.create_rectangle(bx - 11, cy - 5.5, bx, cy + 5.5, fill=mix(BG, a, t), outline=mix(FAINT, a, t),
                           width=self.lw())
        self.add_hit(hid, (0, y, W, y + 28), click=fn)
        return y + 28

    def text_link(self, x, y, text, fn, hid, anchor="e"):
        hv = self.hov(hid)
        self.cv.create_text(x, y, anchor=anchor, text=text, fill=mix(MUTED, TEXT, hv), font=self.f_small)
        w = self.m(self.f_small, text)
        x1 = x - w if anchor == "e" else x
        self.add_hit(hid, (x1 - 4, y - 9, x1 + w + 4, y + 9), click=fn)
        return w

    def draw_main(self):
        cfg = self.cfg
        y = HEAD_H
        y = self.section(y, "CLICKING")
        y = self.bind_row(y, "Left click", "left_key", "left")
        y = self.bind_row(y, "Right click", "right_key", "right")
        y = self.bind_row(y, "Middle click", "middle_key", "middle")
        y = self.option_row(y, "Activation", (("toggle", "toggle"), ("hold", "hold")), cfg["mode"],
                            self.on_mode, "mode")
        y = self.section(y, "SPEED")
        y = self.slider_row(y, "CPS", cfg["cps"], CPS_MIN, CPS_MAX, "", self.on_cps, "cps")
        y = self.slider_row(y, "Randomise", cfg["jitter"], 0, 30, "%", self.on_jitter, "jit")
        y = self.section(y, "MENU")
        y = self.bind_row(y, "Show / hide", "gui_key")
        y = self.check_row(y, "Stay on top", cfg["always_on_top"], self.toggle_pin, "pin")
        y += 6
        self.cv.create_line(0, y, W, y, fill=LINE, width=self.lw())
        y += 18
        self.cv.create_text(14, y, anchor="w", text="right-click a bind to clear it", fill=FAINT, font=self.f_small)
        w = self.text_link(W - 14, y, "exit", self.quit, "exit")
        self.text_link(W - 14 - w - 14, y, "hide", self.request_toggle_gui, "hide")
        return y + 16

    def draw_setup(self):
        c, a = self.cv, self.accent
        y = HEAD_H + 20
        c.create_text(14, y, anchor="nw", text="Menu key", fill=TEXT, font=self.f_title)
        y += 26
        c.create_text(14, y, anchor="nw", width=round((W - 28) * self.S), fill=MUTED, font=self.f_small,
                      text="Yuno has no taskbar icon, so this key is how you show and hide it.")
        y += 42
        listening = self.binding == "gui_key"
        hv = self.hov("setkey")
        c.create_rectangle(14, y, W - 14, y + 44, fill=mix(CHIP, ROW_HOVER, hv),
                           outline=a if listening else LINE, width=self.lw())
        if listening:
            mods = [m for m in MOD_ORDER if any(MODS.get(d) == m for d in self.down)]
            blink = int(time.perf_counter() * 2.5) % 2 == 0
            txt = (" + ".join(m.upper() for m in mods) + " + " if mods else "press a key ") + \
                  ("_" if blink else " ")
            col = a if mods else MUTED
        else:
            txt, col = pretty(self.cfg["gui_key"]), TEXT
        c.create_text(W / 2, y + 22, text=txt, fill=col, font=self.f_mono_big)
        self.add_hit("setkey", (14, y, W - 14, y + 44), click=lambda: self.start_binding("gui_key"))
        y += 60

        hint = "default key " + pretty(self.cfg["gui_key"]).lower() if listening else "click the box to change it"
        c.create_text(14, y + 14, anchor="w", text=hint, fill=FAINT, font=self.f_small)
        ready = not listening and bool(self.cfg["gui_key"])
        t = self.ease("ready", 1.0 if ready else 0.0)
        hv = self.hov("done") if ready else 0.0
        bw = 64
        fill = mix(CHIP, mix(a, "#c9c9cf", hv), t)
        c.create_rectangle(W - 14 - bw, y, W - 14, y + 28, fill=fill, outline=mix(LINE, fill, t), width=self.lw())
        c.create_text(W - 14 - bw / 2, y + 14, text="done", fill=mix(FAINT, BG, t), font=self.f_ui_b)
        if ready:
            self.add_hit("done", (W - 14 - bw, y, W - 14, y + 28), click=self.finish_setup)
        return y + 28 + 16

    def draw(self):
        c = self.cv
        c.delete("all")
        self.hits = []
        if not self.cfg["setup_done"]:
            self.anim["open"] = 1.0
            self.header(setup=True)
            h = self.draw_setup()
        else:
            self.ease("open", 1.0 if self.cfg["expanded"] else 0.0, 0.2)
            self.header()
            h = self.draw_main()
        self.content_h = h
        c.scale("all", 0, 0, self.S, self.S)

    def redraw(self):
        sig = (
            tuple(self.active.values()),
            tuple(self.boost.values()),
            self.mouse_over and any(self.active.values()),
            self.binding,
            frozenset(self.down) if self.binding else None,
            int(time.perf_counter() * 2.5) % 2 if self.binding else 0,
            self.hover,
            self.drag_id,
            tuple((k, str(v)) for k, v in sorted(self.cfg.items()) if k not in ("x", "y")),
        )
        if sig == self.last_sig:
            return
        self.last_sig = sig
        self.draw()
        h = self.content_h if (not self.cfg["setup_done"] or self.cfg["expanded"]) else HEAD_H
        self.set_geometry(h)

    def tick(self):
        if not self.running:
            return
        try:
            if self.gui_toggle_req:
                self.gui_toggle_req = False
                self.visible = not self.visible
                if self.visible:
                    self.root.deiconify()
                    self.root.attributes("-topmost", self.cfg["always_on_top"])
                    self.root.lift()
                    self.root.after(30, self.round_corners)
                    self.last_sig = None
                else:
                    self.root.withdraw()
            if self.visible:
                px, py = self.root.winfo_pointerxy()
                x, y = self.root.winfo_rootx(), self.root.winfo_rooty()
                self.mouse_over = (x <= px < x + self.root.winfo_width() and
                                   y <= py < y + self.root.winfo_height())
                self.redraw()
            else:
                self.mouse_over = False
        except tk.TclError:
            return
        self.root.after(40, self.tick)

    @property
    def drag_id(self):
        return self.dragging[0] if self.dragging else None

    def hit_at(self, e, need):
        x, y = e.x / self.S, e.y / self.S
        for h in reversed(self.hits):
            x1, y1, x2, y2 = h["box"]
            if x1 <= x <= x2 and y1 <= y <= y2 and h.get(need):
                return h
        return None

    def on_down(self, e):
        h = self.hit_at(e, "drag")
        if h:
            self.dragging = (h["id"], h["drag"])
            h["drag"](e.x / self.S)
            self.redraw()
            return
        h = self.hit_at(e, "click")
        if h:
            h["click"]()
            self.redraw()
            return
        if e.y / self.S <= HEAD_H:
            self.moving = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def on_motion(self, e):
        if self.dragging:
            self.dragging[1](e.x / self.S)
            self.redraw()
        elif self.moving:
            dx, dy = self.moving
            self.root.geometry(f"+{e.x_root - dx}+{e.y_root - dy}")

    def on_up(self, e):
        if self.moving:
            self.cfg["x"], self.cfg["y"] = self.root.winfo_x(), self.root.winfo_y()
            self.changed()
        self.dragging = None
        self.moving = None
        self.redraw()

    def on_right(self, e):
        h = self.hit_at(e, "right")
        if h:
            h["right"]()
            self.redraw()

    def on_hover(self, e):
        h = self.hit_at(e, "click") or self.hit_at(e, "drag")
        new = h["id"] if h else None
        if new != self.hover:
            self.hover = new
            self.redraw()
        if h:
            cursor = "hand2"
        elif e.y / self.S <= HEAD_H:
            cursor = "fleur"
        else:
            cursor = ""
        self.cv.configure(cursor=cursor)

    def changed(self):
        save_config(self.cfg)

    def stop_all(self):
        for b in BUTTONS:
            self.active[b] = False

    def request_toggle_gui(self):
        self.gui_toggle_req = True

    def toggle_expand(self):
        self.cfg["expanded"] = not self.cfg["expanded"]
        self.changed()

    def on_cps(self, v):
        if v != self.cfg["cps"]:
            self.cfg["cps"] = v
            self.changed()

    def on_jitter(self, v):
        if v != self.cfg["jitter"]:
            self.cfg["jitter"] = v
            self.changed()

    def on_mode(self, v):
        self.cfg["mode"] = v
        self.stop_all()
        self.changed()

    def toggle_pin(self):
        self.cfg["always_on_top"] = not self.cfg["always_on_top"]
        self.root.attributes("-topmost", self.cfg["always_on_top"])
        self.changed()

    def start_binding(self, slot):
        self.stop_all()
        self.pending_mod = None
        self.binding = slot

    def clear_bind(self, slot):
        if slot == "gui_key":
            return
        if self.binding == slot:
            self.binding = None
        self.cfg[slot] = None
        btn = slot[:-4]
        if btn in self.active:
            self.active[btn] = False
        self.changed()

    def finish_setup(self):
        self.cfg["setup_done"] = True
        self.binding = None
        self.changed()

    def assign(self, combo):
        slot = self.binding
        for other in SLOTS:
            if other != slot and self.cfg[other] == combo:
                self.cfg[other] = self.cfg[slot]
        self.cfg[slot] = combo
        self.binding = None
        self.pending_mod = None
        self.changed()

    def combo_for(self, main):
        held = {MODS[d] for d in self.down if d in MODS}
        return "+".join([m for m in MOD_ORDER if m in held] + [main])

    def fire(self, combo):
        hit = False
        for b in BUTTONS:
            if self.cfg[f"{b}_key"] == combo:
                hit = True
                self.active[b] = True if self.cfg["mode"] == "hold" else not self.active[b]
        if self.cfg["gui_key"] == combo:
            hit = True
            self.gui_toggle_req = True
        return hit

    def handle_down(self, name):
        if name is None or name in self.down:
            return
        self.down.add(name)
        if self.binding:
            if name == "esc":
                self.binding = None
                self.pending_mod = None
            elif name in MODS:
                self.pending_mod = name
            else:
                self.assign(self.combo_for(name))
            return
        if not self.cfg["setup_done"]:
            return
        if name in MODS:
            self.fire(name)
        elif not self.fire(self.combo_for(name)):
            if any(d in MODS for d in self.down):
                self.fire(name)

    def handle_up(self, name):
        if name is None:
            return
        self.down.discard(name)
        if self.binding and name == self.pending_mod:
            self.assign(name)
            return
        if self.cfg["mode"] == "hold":
            for b in BUTTONS:
                bind = self.cfg[f"{b}_key"]
                if bind and bind.split("+")[-1] == name:
                    self.active[b] = False

    def on_key_press(self, key):
        self.handle_down(key_name(key))

    def on_key_release(self, key):
        self.handle_up(key_name(key))

    def on_mouse_click(self, x, y, button, pressed):
        name = _SIDE_BUTTONS.get(button)
        if name:
            (self.handle_down if pressed else self.handle_up)(name)

    def pick_boost(self):
        if self.cfg["jitter"] <= 0:
            return 0
        return random.choices([0, 1, 2], weights=[55, 30, 15])[0]

    def click_loop(self, btn):
        next_t = time.perf_counter()
        boost_until = 0.0
        while self.running:
            if not self.active[btn] or self.mouse_over:
                time.sleep(0.005)
                next_t = time.perf_counter()
                self.boost[btn] = 0
                continue
            now = time.perf_counter()
            if now >= boost_until or self.cfg["jitter"] <= 0:
                self.boost[btn] = self.pick_boost()
                boost_until = now + random.uniform(0.4, 1.2)
            j = self.cfg["jitter"] / 100
            cps = self.cfg["cps"] + self.boost[btn]
            period = (1.0 / max(1, cps)) * (1 + random.uniform(-j, j))
            press(btn)
            precise_sleep(min(0.008, period * 0.35))
            release(btn)
            next_t += period
            now = time.perf_counter()
            if next_t < now - period:
                next_t = now
            precise_sleep(next_t - time.perf_counter())

    def quit(self):
        self.running = False
        self.stop_all()
        save_config(self.cfg)
        self.kb.stop()
        self.ms.stop()
        if IS_WIN:
            _winmm.timeEndPeriod(1)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        App().run()
    except Exception:
        import traceback
        show_error("Yuno Clicker crashed:\n\n" + traceback.format_exc())
