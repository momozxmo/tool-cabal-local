# -*- coding: utf-8 -*-
"""
ui_common.py — ชุด UI กลาง (ธีม + ฟอนต์ + วิดเจ็ต + ไอคอน + log pane + dialog)

ก่อนหน้านี้ palette/ฟอนต์/วิดเจ็ตถูกก๊อปในหลายไฟล์ และ event_tool ต้อง import UI จาก
itemcode_tool (tool พึ่ง tool). ย้ายมารวมที่นี่ -> ทุก tool + launcher import จากที่เดียว
เครื่องมือใหม่ (tool #5) ก็หยิบใช้ได้ทันทีโดยไม่ต้องไปขุดจาก tool อื่น

โมดูลนี้ import tkinter เท่านั้น (ไม่พึ่ง core/playwright/tool ใด ๆ)
"""

import os
import sys
import traceback
import tkinter as tk
from tkinter import ttk, messagebox

# --------------------------------------------------------------------------- palette + fonts
C = {
    "bg_dark": "#0d1117", "bg_med": "#161b22", "bg_card": "#21262d", "bg_inp": "#2d333b",
    "accent": "#388bfd", "accent2": "#3fb950", "danger": "#f85149", "warn": "#d29922",
    "text": "#c9d1d9", "muted": "#8b949e", "teal": "#56d8b1",
}
# alias ฟอนต์ (ชื่อเดิมของแต่ละไฟล์ต่างกัน — รวมไว้ให้ครบเพื่อ import ได้ตรงชื่อ)
FM = ("Segoe UI", 10)
FB = ("Segoe UI", 10, "bold")
F9 = ("Segoe UI", 9)
F = FM
FB_ = FB
MONO = ("Consolas", 9)
SM = ("Segoe UI", 8)

LOG_LEVELS = (("SUCCESS", "accent2"), ("WARNING", "warn"), ("ERROR", "danger"),
              ("INFO", "text"), ("STEP", "accent"))


# --------------------------------------------------------------------------- icon
def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _find_icon():
    """หา icon.ico (รองรับ onefile _MEIPASS, ข้าง .exe, และข้างซอร์ส)"""
    bases = []
    if getattr(sys, "frozen", False):
        bases.append(getattr(sys, "_MEIPASS", ""))
        bases.append(os.path.dirname(sys.executable))
    bases.append(os.path.dirname(os.path.abspath(__file__)))
    for b in bases:
        if not b:
            continue
        p = os.path.join(b, "icon.ico")
        if os.path.exists(p):
            return p
    return None


def _set_window_icon(root):
    """ตั้งไอคอนหน้าต่าง (title bar/taskbar) — default=... ให้ Toplevel ลูกใช้ไอคอนเดียวกัน"""
    ico = _find_icon()
    if not ico:
        return
    try:
        root.iconbitmap(default=ico)
    except Exception:
        try:
            root.iconbitmap(ico)
        except Exception:
            pass


# --------------------------------------------------------------------------- widgets
def make_button(parent, text, command, kind="accent"):
    m = {"accent": (C["accent"], "#fff"), "warn": (C["warn"], "#000"), "green": (C["accent2"], "#000"),
         "danger": (C["danger"], "#fff"), "muted": (C["bg_inp"], C["text"])}
    bg, fg = m.get(kind, m["accent"])
    return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, font=FB_, relief="flat",
                     bd=0, padx=12, pady=5, activebackground=bg, activeforeground=fg, cursor="hand2")


def card(parent, title):
    return tk.LabelFrame(parent, text=title, bg=C["bg_card"], fg=C["muted"], font=F, bd=1,
                         relief="solid", labelanchor="nw", padx=10, pady=8, highlightthickness=0)


def labeled_entry(parent, label, default="", width=26):
    fr = tk.Frame(parent, bg=parent["bg"]); fr.pack(fill="x", pady=2)
    tk.Label(fr, text=label, bg=parent["bg"], fg=C["text"], font=F, width=20, anchor="w").pack(side="left")
    v = tk.StringVar(value=default)
    tk.Entry(fr, textvariable=v, bg=C["bg_inp"], fg=C["text"], insertbackground=C["text"],
             relief="flat", font=F, width=width).pack(side="left", padx=4)
    return v


class DateTimePicker:
    """เลือกวันเวลาแบบ dropdown: ปี-เดือน-วัน ชม:นาที:วิ -> 'YYYY-MM-DD HH:MM:SS'"""
    def __init__(self, parent, label, dt):
        bg = parent["bg"]
        fr = tk.Frame(parent, bg=bg); fr.pack(fill="x", pady=2)
        tk.Label(fr, text=label, bg=bg, fg=C["text"], font=F, width=20, anchor="w").pack(side="left")
        yrs = [str(y) for y in range(dt.year, dt.year + 4)]
        self.y = self._cb(fr, yrs, str(dt.year), 6)
        self.y_cb = self._last_cb
        self._sep(fr, "-")
        self.mo = self._cb(fr, ["%02d" % i for i in range(1, 13)], "%02d" % dt.month, 4)
        self._sep(fr, "-")
        self.d = self._cb(fr, ["%02d" % i for i in range(1, 32)], "%02d" % dt.day, 4)
        self._sep(fr, "  ")
        self.h = self._cb(fr, ["%02d" % i for i in range(0, 24)], "%02d" % dt.hour, 4)
        self._sep(fr, ":")
        self.mi = self._cb(fr, ["%02d" % i for i in range(0, 60)], "%02d" % dt.minute, 4)
        self._sep(fr, ":")
        self.s = self._cb(fr, ["%02d" % i for i in range(0, 60)], "%02d" % dt.second, 4)

    def _sep(self, parent, t):
        tk.Label(parent, text=t, bg=parent["bg"], fg=C["muted"], font=F).pack(side="left")

    def _cb(self, parent, values, default, width):
        v = tk.StringVar(value=default)
        cb = ttk.Combobox(parent, textvariable=v, values=values, state="readonly", width=width, font=F)
        cb.pack(side="left", padx=1)
        self._last_cb = cb
        return v

    def get(self):
        return "%s-%s-%s %s:%s:%s" % (self.y.get(), self.mo.get(), self.d.get(),
                                      self.h.get(), self.mi.get(), self.s.get())

    def set(self, dt):
        cur = list(self.y_cb["values"])
        if str(dt.year) not in cur:
            self.y_cb["values"] = sorted(set(cur) | {str(dt.year)})
        self.y.set(str(dt.year))
        self.mo.set("%02d" % dt.month)
        self.d.set("%02d" % dt.day)
        self.h.set("%02d" % dt.hour)
        self.mi.set("%02d" % dt.minute)
        self.s.set("%02d" % dt.second)


# --------------------------------------------------------------------------- log pane (thread-safe)
class LogPane:
    """Log Text pane พร้อมสี level + ปุ่มล้าง — .log(msg, level) เรียกจาก thread ไหนก็ได้ (ใช้ root.after)"""
    def __init__(self, parent, root, clear_label="ล้าง Log"):
        self.root = root
        top = tk.Frame(parent, bg=C["bg_dark"]); top.pack(fill="x", padx=8, pady=(8, 0))
        make_button(top, clear_label, self.clear, "muted").pack(side="right")
        self.text = tk.Text(parent, bg=C["bg_med"], fg=C["text"], font=MONO, relief="flat",
                            wrap="word", insertbackground=C["text"])
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        for lvl, ckey in LOG_LEVELS:
            self.text.tag_config(lvl, foreground=C[ckey])

    def log(self, msg, level="INFO"):
        try:
            self.root.after(0, self._log_main, str(msg), level)
        except Exception:
            pass

    def _log_main(self, msg, level):
        self.text.insert("end", msg + "\n", level); self.text.see("end")

    def clear(self):
        self.text.delete("1.0", "end")


# --------------------------------------------------------------------------- list picker dialog
def pick_from_list(root, title, hint, rows, on_pick, multiselect=False, width=560, height=460):
    """Toplevel modal เลือกจาก list ของ string. on_pick(indexes) — indexes เป็น list เสมอ
    คืน object window (มี .listbox, .do ให้เทสต์เรียกได้)"""
    win = tk.Toplevel(root)
    win.title(title)
    win.configure(bg=C["bg_dark"])
    win.geometry("%dx%d" % (width, height))
    win.transient(root)
    try:
        win.grab_set()
    except Exception:
        pass
    tk.Label(win, text=hint, bg=C["bg_dark"], fg=C["muted"], font=FM,
             wraplength=width - 40, justify="left").pack(fill="x", padx=14, pady=(12, 6))
    body = tk.Frame(win, bg=C["bg_dark"]); body.pack(fill="both", expand=True, padx=14)
    sb = ttk.Scrollbar(body, orient="vertical")
    sb.pack(side="right", fill="y")
    lb = tk.Listbox(body, bg=C["bg_inp"], fg=C["text"], font=("Consolas", 10), relief="flat",
                    selectbackground=C["accent"], selectforeground="#fff",
                    selectmode=("extended" if multiselect else "browse"),
                    yscrollcommand=sb.set, activestyle="none")
    lb.pack(side="left", fill="both", expand=True)
    sb.config(command=lb.yview)
    for r in rows:
        lb.insert("end", r)
    if rows:
        lb.selection_set(0)

    def do():
        sel = list(lb.curselection())
        if not sel:
            return
        win.destroy()
        on_pick(sel)

    btns = tk.Frame(win, bg=C["bg_dark"]); btns.pack(fill="x", padx=14, pady=12)
    make_button(btns, "ยกเลิก", win.destroy, "muted").pack(side="right")
    make_button(btns, "ตกลง", do, "accent").pack(side="right", padx=(0, 8))
    win.listbox = lb
    win.do = do
    return win


# --------------------------------------------------------------------------- คัดลอก/วาง ข้ามภาษา
# Windows virtual-key ของปุ่มจริง (ไม่ขึ้นกับ layout): A=65 C=67 V=86 X=88
_CLIP_VK = {65: 'all', 67: 'copy', 86: 'paste', 88: 'cut'}


def _clip_action(event):
    """ทำ copy/paste/cut/select-all แม้สลับเป็นภาษาไทย

    Tk แมป <<Paste>> จาก 'keysym' ของ Ctrl+v -> พอเป็น layout ไทย ปุ่ม V ส่ง keysym 'ฟ'
    การแมปเลยไม่ตรง วางไม่ได้ · ตัวนี้ดักด้วย keycode (ปุ่มจริง) แต่ทำงานเฉพาะตอน keysym
    'ไม่ใช่' ตัวละตินอยู่แล้ว -> layout อังกฤษยังใช้ของเดิม (ไม่วางซ้ำซ้อน)"""
    action = _CLIP_VK.get(getattr(event, 'keycode', None))
    if not action:
        return None
    if (getattr(event, 'keysym', '') or '').lower() in ('a', 'c', 'v', 'x'):
        return None                      # layout อังกฤษ -> ปล่อยให้ Tk จัดการเอง
    w = event.widget
    try:
        if action == 'all':
            try:
                w.selection_range(0, 'end')            # Entry / Combobox
            except Exception:
                w.tag_add('sel', '1.0', 'end')         # Text
        else:
            w.event_generate({'copy': '<<Copy>>', 'paste': '<<Paste>>',
                              'cut': '<<Cut>>'}[action])
    except Exception:
        return None
    return 'break'


def install_thai_clipboard(root):
    """ผูก Ctrl+A/C/V/X ให้ทำงานทุกภาษา บนช่องกรอกทุกชนิดทั้งโปรแกรม (ทำครั้งเดียว)"""
    for cls in ('Entry', 'Text', 'TEntry', 'TCombobox', 'TSpinbox'):
        try:
            root.bind_class(cls, '<Control-KeyPress>', _clip_action, add='+')
        except Exception:
            pass


# --------------------------------------------------------------------------- ttk dark style
def apply_dark_style(root, style=None):
    """ตั้งธีม ttk (clam) + สี Combobox/Notebook + กัน dropdown เปลี่ยนค่าตอนเลื่อนเมาส์"""
    style = style or ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    root.option_add("*TCombobox*Listbox.background", C["bg_inp"])
    root.option_add("*TCombobox*Listbox.foreground", C["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    try:
        style.configure("TCombobox", fieldbackground=C["bg_inp"], background=C["bg_inp"],
                        foreground=C["text"], arrowcolor=C["text"])
    except Exception:
        pass
    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        root.bind_class("TCombobox", seq, lambda e: "break")
    return style


# --------------------------------------------------------------------------- ขนาดหน้าต่างตอนเปิด
def fit_size(sw, sh, w_frac=0.62, h_frac=0.88, min_w=760, min_h=820, max_w=1400, max_h=1300):
    """คำนวณขนาด+ตำแหน่งหน้าต่างจากขนาดจอ (แยกออกมาให้เทสต์ได้โดยไม่ต้องมีจอจริง)
    จอใหญ่ = เปิดมาใหญ่ตามสัดส่วน · จอเล็ก = ไม่ล้นจอ (เหลือขอบให้ taskbar)"""
    w = max(min_w, min(int(sw * w_frac), max_w))
    h = max(min_h, min(int(sh * h_frac), max_h))
    w = min(w, max(320, sw - 40))          # กันล้นจอเล็ก
    h = min(h, max(320, sh - 80))
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 3)              # ค่อนไปทางบนนิดหน่อย ดูสมดุลกว่ากึ่งกลางพอดี
    return w, h, x, y


def fit_window(root, **kw):
    """ตั้งขนาดหน้าต่างตอนเปิดให้พอดีจอ + จัดกลาง แล้วคืน (w, h)"""
    try:
        root.update_idletasks()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    except Exception:
        sw, sh = 1920, 1080
    w, h, x, y = fit_size(sw, sh, **kw)
    try:
        root.geometry('%dx%d+%d+%d' % (w, h, x, y))
        root.minsize(min(kw.get('min_w', 760), w), min(kw.get('min_h', 820), h))
    except Exception:
        pass
    return w, h


# --------------------------------------------------------------------------- combobox กว้างตามเนื้อหา
_POPDOWN_PATCHED = [False]


def _monitor_workarea(x, y):
    """work area (พื้นที่ใช้งานจริงของจอ ไม่รวม taskbar) ของ 'จอที่มีจุด (x,y)' บน Windows
    คืนสตริง 'left right top bottom' (พิกัดรวมทุกจอ) · '' ถ้าไม่ใช่ Windows/หาไม่ได้

    ทำไมต้องมี: winfo screenwidth/screenheight ของ Tk = ขนาด 'จอหลัก' จอเดียว
    -> ตอน combobox อยู่บนจอที่ 2 (rootx เกินความกว้างจอหลัก) การ clamp X ด้วย screenwidth
       จะเด้ง popup กลับไปโผล่บนจอหลัก = บั๊ก 'dropdown ไปโผล่คนละจอ'
    ตัวนี้ให้ขอบเขตของ 'จอที่ช่องอยู่จริง' -> clamp ในจอเดิม ไม่ข้ามจอ"""
    if not sys.platform.startswith("win"):
        return ""
    try:
        import ctypes
        from ctypes import wintypes

        class RECT(ctypes.Structure):
            _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                        ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                        ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

        u = ctypes.windll.user32
        u.MonitorFromPoint.restype = ctypes.c_void_p
        u.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
        u.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        pt = wintypes.POINT(int(float(x)), int(float(y)))
        hmon = u.MonitorFromPoint(pt, 2)          # MONITOR_DEFAULTTONEAREST
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if u.GetMonitorInfoW(ctypes.c_void_p(hmon), ctypes.byref(mi)):
            r = mi.rcWork
            return "%d %d %d %d" % (r.left, r.right, r.top, r.bottom)
    except Exception:
        pass
    return ""


def allow_wide_popdown(widget):
    """ปลดล็อกความกว้างของ 'รายการที่กางลงมา' ของ ttk.Combobox + กันไปโผล่ผิดจอ

    Tk บังคับ  wm geometry $popdown ${w}x${H}  โดย w = ความกว้างของช่อง combobox
    -> ต่อให้ตั้ง -width ของ listbox ข้างในไว้เท่าไหร่ ข้อความก็ยังโดนตัดอยู่ดี
    แพตช์นี้เปลี่ยนเป็น max(ความกว้างช่อง, ความกว้างที่เนื้อหาต้องการ) แล้ว clamp ให้อยู่
    ใน work area ของ 'จอที่ช่องอยู่จริง' (รองรับหลายจอ · math อยู่ใน ::af_popdown_geom
    เพื่อให้เทสต์ได้) · ทำครั้งเดียวต่อ interpreter"""
    if _POPDOWN_PATCHED[0]:
        return True
    try:
        try:
            widget.tk.createcommand("af_monitor_workarea", _monitor_workarea)
        except Exception:
            pass
        widget.tk.eval("""
# คำนวณ geometry ของ popdown (แยกออกมาให้เทสต์ math ได้ตรง ๆ)
#   x y w h : ตำแหน่ง/ขนาดช่อง combobox (พิกัดหน้าจอ)
#   H W     : สูง/กว้างที่ popdown ต้องการ
#   fbR fbB : ขอบขวา/ล่าง สำรอง (ใช้เมื่อหา work area ของจอไม่ได้)
proc ::af_popdown_geom {x y w h H W fbR fbB} {
    if {$W < $w} { set W $w }
    set L 0; set R $fbR; set T 0; set B $fbB
    set cx [expr {$x + $w / 2}]
    set cy [expr {$y + $h / 2}]
    if {![catch {af_monitor_workarea $cx $cy} area] && [llength $area] == 4} {
        lassign $area L R T B
    }
    set avail [expr {$R - $L}]
    if {$W > $avail} { set W $avail }
    set X $x
    if {$X + $W > $R} { set X [expr {$R - $W}] }
    if {$X < $L} { set X $L }
    if {$y + $h + $H > $B} {
        set Y [expr {$y - $H}]
    } else {
        set Y [expr {$y + $h}]
    }
    if {$Y < $T} { set Y $T }
    return "${W}x${H}+${X}+${Y}"
}
proc ttk::combobox::PlacePopdown {cb popdown} {
    set x [winfo rootx $cb]
    set y [winfo rooty $cb]
    set w [winfo width $cb]
    set h [winfo height $cb]
    set style [$cb cget -style]
    if { $style eq {} } { set style TCombobox }
    set postoffset [ttk::style lookup $style -postoffset {} {0 0 0 0}]
    foreach var {x y w h} delta $postoffset { incr $var $delta }
    set H [winfo reqheight $popdown]
    set W [winfo reqwidth $popdown]
    wm geometry $popdown [::af_popdown_geom $x $y $w $h $H $W \
        [winfo screenwidth $popdown] [winfo screenheight $popdown]]
}
""")
        _POPDOWN_PATCHED[0] = True
    except Exception:
        pass
    return _POPDOWN_PATCHED[0]


# --------------------------------------------------------------------------- standalone bootstrap
def run_standalone(AppClass, title="Tool"):
    """รัน tool เดี่ยว ๆ: สร้าง Tk + icon + App + error dialog (main() ของแต่ละ tool เหลือ 1 บรรทัด)"""
    try:
        root = tk.Tk()
        root.title(title)
        _set_window_icon(root)
        AppClass(root)
        root.mainloop()
    except Exception:
        err = traceback.format_exc()
        try:
            messagebox.showerror("Startup Error", err)
        except Exception:
            print(err, file=sys.stderr)
