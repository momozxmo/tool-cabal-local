"""all_for_cabal.py — All for Cabal Toolkit
รวมทุกเครื่องมือไว้ในโปรแกรมเดียว (รายการจริงดูที่ตัวแปร TOOLS = ทะเบียนใน tool_registry)
เพิ่มเครื่องมือใหม่ = สร้างไฟล์ที่ export ตัวแปร TOOL (ToolSpec) แล้วเพิ่ม .TOOL เข้า TOOLS

เปิดโปรแกรมเข้าเครื่องมือแรก (Item Finder = จุดเริ่ม pipeline) ตรง ๆ ทุกหน้าใช้ธีม
ttk 'clam' ธีมเดียว ไม่สลับ — ลื่น ไม่มีหน้า Home ให้ต้องโหลด

รัน:  python all_for_cabal.py
"""

import sys
import traceback
import tkinter as tk
from tkinter import ttk, messagebox

import item_finder
import new_tool
import itemcode_tool
import event_tool
import aztek_core as core
from ui_common import (C, FM, FB, _set_window_icon, fit_window, allow_wide_popdown,
                       install_thai_clipboard)

# ทะเบียนเครื่องมือ — แหล่งเดียว (เพิ่ม tool #5 = สร้างไฟล์ที่ export TOOL แล้วใส่ .TOOL ตรงนี้)
TOOLS = [item_finder.TOOL, new_tool.TOOL, itemcode_tool.TOOL, event_tool.TOOL]


class Launcher:
    def __init__(self, root):
        self.root = root
        root.title('All for Cabal — Toolkit')
        try:
            root.configure(bg=C['bg_dark'])
        except Exception:
            pass
        # ไอคอนต้องมา "ก่อน" fit_window: fit_window เรียก update_idletasks() ซึ่งทำให้ Tk สร้าง
        # หน้าต่างจริงขึ้นมาแล้ว -> iconbitmap ที่ตามมาทีหลังจะได้แค่ไอคอนใหญ่ (32) ส่วนช่อง
        # ไอคอนเล็ก (16 = ที่ title bar/taskbar ใช้) โดนยัด 32 ลงไปแทน ภาพเลยเบลอ/เพี้ยน
        _set_window_icon(root)
        # แพตช์ dropdown ทั้งโปรแกรมตั้งแต่เปิด: กว้างตามเนื้อหา + กันไปโผล่ผิดจอ (หลายจอ)
        allow_wide_popdown(root)
        # Ctrl+C/V/X/A ใช้ได้ทุกภาษา (คีย์บอร์ดไทยก็วางได้)
        install_thai_clipboard(root)
        # เปิดมาใหญ่ตามขนาดจอ (จอใหญ่ = ใหญ่ตาม, จอเล็ก = ไม่ล้นจอ) + จัดกลาง
        fit_window(root, min_w=760, min_h=820)
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')   # ธีมเดียวทั้งโปรแกรม — ไม่สลับ = ไม่หน่วง
        except Exception:
            pass
        # กัน dropdown ทุกตัวเปลี่ยนค่าตอนเลื่อนลูกกลิ้งเมาส์ผ่าน (ทุก tool ใช้ root เดียวกัน)
        for seq in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            root.bind_class('TCombobox', seq, lambda e: 'break')

        self._specs = {t.key: t for t in TOOLS}   # key -> ToolSpec
        self._apps = {t.key: None for t in TOOLS}
        self._frames = {}
        self._nav_btns = {}
        self._active = None
        # เกม/เซิร์ฟตัวเดียวแชร์ทุก tool — เลือกที่ไหนก็เปลี่ยนพร้อมกันหมด (prefs ไฟล์เดียวใน core)
        _g = core.load_prefs().get('game')
        self.game_var = tk.StringVar(value=_g if _g in core.GAME_NAMES else 'CabalPC SEA')
        self.game_var.trace_add('write', lambda *a: self._on_game_changed())
        # user/pass สำหรับ auto-login — โหลดค่าที่เคยเก็บ (เข้ารหัส DPAPI) มาเติมช่องให้อัตโนมัติ
        _cr = core.load_creds()
        self.user_var = tk.StringVar(value=_cr.get('user', ''))
        self.pw_var = tk.StringVar(value=_cr.get('password', ''))
        # คิว Event pipeline: bundle id ที่สร้างแล้ว แยกตามกลุ่ม (Code) เพื่อดึงไปใส่ Item Code
        self._bundle_ids = {}
        self._build_ui()
        self.show(TOOLS[0].key)          # เปิดตรงเข้าเครื่องมือแรก (Item Finder = จุดเริ่ม pipeline)
        # สร้าง UI ของ tool ที่เหลือล่วงหน้าตอนโปรแกรมว่าง (หลังหน้าแรกวาดเสร็จ) เพื่อให้กด
        # เปิดครั้งแรกไม่ค้าง — Item Code/Event สร้างช้า ~200-250ms ถ้าไปสร้างตอนคลิก
        self.root.after(350, self._prewarm)

    def _prewarm(self):
        # สร้างทีละ tool ต่อ tick เพื่อไม่ freeze ยาว (idempotent — ถ้าผู้ใช้คลิกเปิดเองก่อน
        # _ensure จะข้ามให้อยู่แล้ว) เฟรมยังไม่ถูก pack จึงสร้างเงียบ ๆ ไม่มีภาพกระพริบ
        for key in self._specs:
            if self._apps[key] is None:
                try:
                    self._ensure(key)
                except Exception:
                    pass
                self.root.after(80, self._prewarm)   # ตัวถัดไปตอน idle รอบหน้า
                return

    def _on_game_changed(self):
        # จำค่าเกมล่าสุด — prefs ไฟล์เดียว (.aztek_prefs.json) ใช้ร่วมทุก tool
        g = self.game_var.get()
        try:
            p = core.load_prefs(); p['game'] = g; core.save_prefs(p)
        except Exception:
            pass

    # ---- login ร่วม (จุดเดียว บนแถบบน) ----
    def _refresh_login_status(self):
        if core.has_creds():
            self.login_status.config(text='● จำ user/pass แล้ว (auto-login)', fg=C['teal'])
        elif core.has_session():
            self.login_status.config(text='● มี session', fg=C['teal'])
        else:
            self.login_status.config(text='○ ยังไม่ได้ตั้ง user/pass', fg=C['muted'])

    def _login_log(self, msg, level='INFO'):
        # อัปเดตข้อความสถานะสั้น ๆ (thread-safe)
        try:
            self.root.after(0, lambda: self.login_status.config(text=str(msg)[:40], fg=C['muted']))
        except Exception:
            pass

    def _run_login_async(self, coro_factory, done=True):
        import threading, asyncio
        def _run():
            try:
                asyncio.run(coro_factory())
            except Exception:
                pass
            if done:
                self.root.after(0, self._refresh_login_status)
        threading.Thread(target=_run, daemon=True).start()

    def _save_creds(self, *a):
        # เก็บ user/pass (เข้ารหัส DPAPI) เมื่อแก้ค่า — ว่างทั้งคู่ = ลืมรหัส, กรอกไม่ครบ = ไม่ทำอะไร
        u = self.user_var.get().strip()
        p = self.pw_var.get()
        if u and p:
            core.save_creds(u, p)
        elif not u and not p:
            core.clear_creds()
        self._refresh_login_status()

    def _toggle_pw(self):
        # ปุ่ม 👁 สลับแสดง/ซ่อนรหัสผ่าน (ไว้ตรวจว่าพิมพ์ถูก)
        self._pw_shown = not getattr(self, '_pw_shown', False)
        self.pw_entry.config(show='' if self._pw_shown else '●')

    def _open_login(self):
        # auto-login: เก็บ user/pass ล่าสุดก่อน แล้วให้ core เติม+กดเข้าสู่ระบบให้เอง
        # (ถ้ากรอกไม่ได้/ยังไม่ได้ตั้งรหัส core จะเปิด browser ค้างไว้ให้ล็อกอินมือ = fallback)
        self._save_creds()
        # หน้า bundle อยู่ใต้ /shop/ -> ใช้ game_url (build_url จะได้ /bundles เฉย ๆ = 404)
        url = core.game_url(self.game_var.get(), 'bundles')
        s = core.AztekSession(log=self._login_log)
        self._run_login_async(lambda: s.login(url))

    def _clear_session(self):
        ok = core.clear_profile()
        self.login_status.config(text='ล้าง session แล้ว' if ok else 'ล้างไม่สำเร็จ',
                                 fg=C['accent2'] if ok else C['danger'])
        self.root.after(1200, self._refresh_login_status)

    def _test_nav(self):
        url = core.game_url(self.game_var.get(), 'bundles')   # /shop/bundles (มี /shop/)
        s = core.AztekSession(log=self._login_log)

        async def run():
            async with s.context(url) as (browser, page):
                ok = await core.is_logged_in(page)
                self.root.after(0, lambda: self.login_status.config(
                    text='● login พร้อม' if ok else '○ ยังไม่ login',
                    fg=C['teal'] if ok else C['warn']))
                await page.wait_for_timeout(1500)
        self._run_login_async(run, done=False)

    # ---- UI ----
    def _build_ui(self):
        # แถบเมนู (ใช้ tk.* -> ไม่โดน ttk theme ทับ)
        nav = tk.Frame(self.root, bg=C['bg_med'])
        nav.pack(fill='x')
        tk.Label(nav, text='All for Cabal', bg=C['bg_med'], fg=C['teal'],
                 font=('Segoe UI', 13, 'bold')).pack(side='left', padx=14, pady=8)

        def navbtn(key, text):
            b = tk.Button(nav, text=text, command=lambda k=key: self.show(k),
                          bg=C['bg_card'], fg=C['muted'], font=FB, relief='flat',
                          padx=13, pady=6, cursor='hand2', activebackground=C['accent'],
                          activeforeground='#fff', bd=0)
            b.pack(side='left', padx=(6, 0), pady=6)
            self._nav_btns[key] = b

        for t in TOOLS:                       # ปุ่มเมนูมาจากทะเบียน (ไม่มีหน้าหลักแล้ว)
            navbtn(t.key, t.nav)

        # ----- แถบบนร่วม (2 แถว): แถว1 เกม/เซิร์ฟ+สถานะ | แถว2 user/pass + ปุ่ม login (จุดเดียวทุกหน้า) -----
        top = tk.Frame(self.root, bg=C['bg_med'])
        top.pack(fill='x')
        tk.Label(top, text='🎮 เกม/เซิร์ฟ:', bg=C['bg_med'], fg=C['text'], font=FM).pack(side='left', padx=(14, 4), pady=(6, 2))
        self.game_cb = ttk.Combobox(top, textvariable=self.game_var, values=core.GAME_NAMES,
                                    state='readonly', width=16, font=FM)
        self.game_cb.pack(side='left', padx=(0, 12))
        self.login_status = tk.Label(top, text='', bg=C['bg_med'], fg=C['muted'], font=FM)
        self.login_status.pack(side='right', padx=14)

        top2 = tk.Frame(self.root, bg=C['bg_med'])
        top2.pack(fill='x')
        tk.Label(top2, text='👤 User:', bg=C['bg_med'], fg=C['text'], font=FM).pack(side='left', padx=(14, 4), pady=(0, 8))
        self.user_entry = tk.Entry(top2, textvariable=self.user_var, width=16, font=FM,
                                   bg=C['bg_inp'], fg=C['text'], insertbackground=C['text'], relief='flat')
        self.user_entry.pack(side='left', padx=(0, 10), ipady=2)
        tk.Label(top2, text='🔑 Pass:', bg=C['bg_med'], fg=C['text'], font=FM).pack(side='left', padx=(0, 4))
        self.pw_entry = tk.Entry(top2, textvariable=self.pw_var, width=16, font=FM, show='●',
                                 bg=C['bg_inp'], fg=C['text'], insertbackground=C['text'], relief='flat')
        self.pw_entry.pack(side='left', padx=(0, 4), ipady=2)
        self._pw_shown = False
        self.pw_toggle = tk.Button(top2, text='👁', command=self._toggle_pw, bg=C['bg_card'], fg=C['muted'],
                                   font=FM, relief='flat', padx=6, pady=2, cursor='hand2', bd=0)
        self.pw_toggle.pack(side='left', padx=(0, 12))
        # เก็บค่าเมื่อคลิกออกจากช่อง (จำไว้อัตโนมัติ) / กด Enter ที่ช่องรหัส = เข้าสู่ระบบเลย
        self.user_entry.bind('<FocusOut>', self._save_creds)
        self.pw_entry.bind('<FocusOut>', self._save_creds)
        self.pw_entry.bind('<Return>', lambda e: self._open_login())
        tk.Button(top2, text='🔓 เข้าสู่ระบบ', command=self._open_login, bg=C['accent'], fg='#fff',
                  font=FB, relief='flat', padx=12, pady=4, cursor='hand2', bd=0).pack(side='left')
        tk.Button(top2, text='ทดสอบ', command=self._test_nav, bg=C['bg_card'], fg=C['warn'],
                  font=FM, relief='flat', padx=8, pady=4, cursor='hand2', bd=0).pack(side='left', padx=(6, 0))
        tk.Button(top2, text='ล้าง session', command=self._clear_session, bg=C['bg_card'], fg=C['muted'],
                  font=FM, relief='flat', padx=8, pady=4, cursor='hand2', bd=0).pack(side='left', padx=(6, 0))
        self._refresh_login_status()

        tk.Frame(self.root, bg=C['bg_card'], height=1).pack(fill='x')

        self.content = tk.Frame(self.root, bg=C['bg_dark'])
        self.content.pack(fill='both', expand=True)

        for t in TOOLS:
            self._frames[t.key] = tk.Frame(self.content, bg=C['bg_dark'])

    def _highlight(self, active_key):
        for key, btn in self._nav_btns.items():
            if key == active_key:
                btn.config(bg=C['accent'], fg='#ffffff')
            else:
                btn.config(bg=C['bg_card'], fg=C['muted'])

    def _ensure(self, key):
        # สร้าง tool ตอนกดเปิดครั้งแรก จาก factory ในทะเบียน (ไม่มี if/elif ต่อ tool อีก)
        if self._apps[key] is None:
            self._apps[key] = self._specs[key].make(self, self._frames[key])
        return self._apps[key]

    def _event_plans_provider(self):
        # โหมด Event: รวมกลุ่มรางวัล (จาก Item Finder) ตาม "ชื่อ Event" -> 1 Event หลายชุดรางวัล
        # แต่ละชุด = ชื่อรางวัล + bundle id ที่สร้างจากการค้นหา->ส่งบันเดิล
        finder = self._apps.get('finder')
        meta = dict(getattr(finder, '_event_group_meta', {}) or {}) if finder else {}
        events, order = {}, []
        for group, m in meta.items():
            if not m.get('is_event'):
                continue
            en = m.get('event_name') or group
            if en not in events:
                events[en] = {'name': en, 'rewards': [], 'start_dt': m.get('start_dt'),
                              'end_date': m.get('end_date'), 'end_time': m.get('end_time')}
                order.append(en)
            events[en]['rewards'].append({'name': m.get('reward') or group,
                                          'bundle_id': self._bundle_ids.get(group, '')})
        return [(en, events[en]) for en in order]

    def _event_queue(self):
        # รวมเงื่อนไขต่อกลุ่ม (จาก Item Finder) + bundle id ที่สร้างแล้ว -> ให้ Create Item Code ดึงไปเติม
        # (ข้ามกลุ่มโหมด Event ที่มี is_event)
        finder = self._apps.get('finder')
        meta = dict(getattr(finder, '_event_group_meta', {}) or {}) if finder else {}
        out = {}
        for g, m in meta.items():
            if m.get('is_event'):
                continue
            out[g] = {'meta': m, 'bundle_id': self._bundle_ids.get(g, '')}
        return out

    def _handoff_to_bundle(self, items, group=None):
        self._ensure('bundle')
        self.show('bundle')
        # เก็บ id คู่กับชื่อ -> ส่งชื่อไปโชว์ใน popup ด้วย (ให้รู้ว่าแต่ละ ID คือไอเทมอะไร)
        pairs = []
        for it in items:
            iid = str(it.get('id') or it.get('aztek_id') or '').strip()
            if iid:
                pairs.append((iid, str(it.get('name') or it.get('item_name') or '').strip()))
        ids = [p[0] for p in pairs]
        names = [p[1] for p in pairs]
        # ผูกกลุ่ม (Code) ไปกับ bundle ในคิวโดยตรง -> id ที่สร้างกลับมาถูกกลุ่มเสมอ
        # (ไม่พึ่ง state ค้างใน launcher แล้ว ไม่ว่าจะสลับ/แบตช์คิวยังไง)
        self._apps['bundle'].open_bundle_dialog(prefill_ids=ids, prefill_names=names, group=group or '')
        return len(ids)

    def _review_from_finder(self, bundles):
        # Item Finder: รวมผลค้นหาเป็นบันเดิลรายกลุ่ม -> เปิดหน้ารีวิว master-detail
        # ลิสต์ซ้าย (เลือก/สลับใช้-ไม่ใช้/ลบ) + ฟอร์มขวา (แก้ชื่อ/ตัดไอเทม/ตั้ง tier+รางวัล)
        # -> ปุ่มเดียว ส่งเข้าคิว Create Bundle ทีเดียว
        self._ensure('bundle')
        self.show('bundle')
        app = self._apps['bundle']
        queue = [b for b in bundles if b.get('items')]
        if not queue:
            return 0
        app.open_bundle_review(queue)
        return len(queue)

    def _on_bundle_created(self, bid, group=''):
        # new_tool เรียกเมื่อสร้าง bundle เสร็จ พร้อมกลุ่มต้นทางของ bundle นั้น -> ผูก id เข้ากลุ่มให้ถูก
        if group and bid:
            self._bundle_ids[group] = str(bid)

    def _go_next(self, target):
        # จาก Create Bundle -> ไป Item Code / Event + เปิดตัวเลือก "ดึงจากคิว" ให้อัตโนมัติ
        if target not in self._specs:
            return
        self.show(target)
        app = self._apps.get(target)
        if app is None:
            return
        # หน่วงนิด ให้หน้าเปลี่ยนก่อนค่อยเปิด picker
        self.root.after(250, lambda: self._auto_pull(target, app))

    def _auto_pull(self, target, app):
        try:
            if target == 'itemcode' and hasattr(app, '_event_prefill_picker'):
                app._event_prefill_picker()
            elif target == 'event' and hasattr(app, '_plan_picker'):
                app._plan_picker()
        except Exception:
            pass

    def show(self, key):
        if key == self._active:
            return
        try:
            self._ensure(key)            # สร้าง tool ถ้ายังไม่เคยเปิด (idempotent)
        except Exception:
            messagebox.showerror('เปิดเครื่องมือไม่สำเร็จ', traceback.format_exc())
            return

        if self._active is not None:
            self._frames[self._active].pack_forget()
        self._frames[key].pack(fill='both', expand=True)
        self._active = key
        self._highlight(key)


def main():
    try:
        root = tk.Tk()
        Launcher(root)
        root.mainloop()
    except Exception:
        err = traceback.format_exc()
        try:
            messagebox.showerror('Startup Error', err)
        except Exception:
            print(err, file=sys.stderr)


if __name__ == '__main__':
    main()
