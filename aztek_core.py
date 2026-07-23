# -*- coding: utf-8 -*-
"""
aztek_core.py  -  โมดูลแกน (reusable core) สำหรับ tool อัตโนมัติบนเว็บ aztek-tools
ระบบเก็บค่า login แบบถาวร (Playwright + Chrome profile) + รายชื่อเกม/เซิร์ฟ + prefs/options
ต้องมี:  pip install playwright  แล้ว  playwright install chromium
"""

import os
import sys
import re
import json
import base64
import ctypes
import ctypes.wintypes
import threading

try:
    from playwright.async_api import async_playwright
    PW_OK = True
except ImportError:
    async_playwright = None
    PW_OK = False

# Chrome persistent profile ล็อกไดเรกทอรีแบบ exclusive — เปิด 2 browser พร้อมกันบน profile
# เดียวกันจะ crash. ล็อกตัวนี้กันทุก tool ที่เปิดผ่าน AztekSession เปิดชนกัน (non-blocking)
BROWSER_LOCK = threading.Lock()
_browser_holder = [None]


class BrowserBusy(RuntimeError):
    """ยกขึ้นเมื่อมี browser ของ tool อื่นเปิดค้างอยู่บน profile เดียวกัน"""


def acquire_browser(tool_name=""):
    if not BROWSER_LOCK.acquire(blocking=False):
        raise BrowserBusy("Browser กำลังถูกใช้โดย: %s — ปิด browser เดิมก่อน"
                          % (_browser_holder[0] or "อีก tool หนึ่ง"))
    _browser_holder[0] = tool_name or "tool"


def release_browser():
    _browser_holder[0] = None
    try:
        BROWSER_LOCK.release()
    except RuntimeError:
        pass


# --------------------------------------------------------------------------- เกม/เซิร์ฟ
GAME_BASES = {
    "CabalM TH":   "https://aztek-tools-v2.combo-interactive.com/combo/cabalm",
    "CabalM SEA":  "https://aztek-tools-v2.combo-interactive.com/combo/cabalmsea",
    "CabalPC TH":  "https://aztek-tools-v2.combo-interactive.com/combo/cabalpc",
    "CabalPC SEA": "https://aztek-tools-v2.combo-interactive.com/combo/cabalpcsea",
}
GAME_NAMES = list(GAME_BASES.keys())


def game_base(game):
    """base URL ของเกม/เซิร์ฟ (เช่น .../combo/cabalpc) หรือ '' ถ้าไม่รู้จัก"""
    return GAME_BASES.get(game, "")


def build_url(game, path=""):
    """สร้าง URL เต็มจาก base + path (path เช่น 'itemcodes', 'itemcodes/create')
    ตัวอย่าง: build_url('CabalPC TH','itemcodes/create')
              -> '.../combo/cabalpc/itemcodes/create'
    """
    base = GAME_BASES.get(game)
    if not base:
        return ""
    path = path.lstrip("/")
    return base + "/" + path if path else base


def game_url(game, page=""):
    """URL หน้าใน Shop V2 (มี /shop/ คั่น) - ใช้กับ tool bundle เดิม"""
    base = GAME_BASES.get(game)
    return base + "/shop/" + page if base else ""


# --------------------------------------------------------------------------- ไฟล์
def _get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = _get_app_dir()
# ใช้โปรไฟล์ Chrome เดียวกับ Item Finder / Create Bundle -> login ครั้งเดียวใช้ได้ทุก tool
CHROME_PROFILE = os.path.join(APP_DIR, ".cabal_chrome_profile")
PREF_FILE = os.path.join(APP_DIR, ".aztek_prefs.json")
OPTIONS_FILE = os.path.join(APP_DIR, ".aztek_options.json")
CREDS_FILE = os.path.join(APP_DIR, ".aztek_creds.dat")


def load_prefs():
    try:
        with open(PREF_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_prefs(d):
    try:
        with open(PREF_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_options():
    try:
        with open(OPTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_options(d):
    try:
        with open(OPTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# --------------------------------------------------------------------------- ข้อมูล login (DPAPI)
# เข้ารหัสรหัสผ่านด้วย Windows DPAPI (ผูกกับ Windows user account เครื่องนี้เท่านั้น) —
# ไม่ต้องพึ่ง lib เพิ่ม, ย้ายไฟล์ไปเครื่อง/ผู้ใช้อื่นจะถอดไม่ได้ (ต้องกรอกใหม่)
class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi_protect(data):
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _dpapi_unprotect(data):
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def has_creds():
    return os.path.isfile(CREDS_FILE)


def load_creds():
    """คืน {'user':..., 'password':...} ถ้าถอดรหัสสำเร็จ, {} ถ้าไม่มี/ถอดไม่ได้
    (เช่น ไฟล์ถูกย้ายไปเครื่องอื่น หรือ Windows user อื่น)"""
    try:
        with open(CREDS_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        pw = _dpapi_unprotect(base64.b64decode(d.get("pass_b64", ""))).decode("utf-8")
        return {"user": d.get("user", ""), "password": pw}
    except Exception:
        return {}


def save_creds(user, password):
    try:
        enc = _dpapi_protect(password.encode("utf-8"))
        d = {"user": user, "pass_b64": base64.b64encode(enc).decode("ascii")}
        with open(CREDS_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        return True
    except Exception:
        return False


def clear_creds():
    try:
        if os.path.isfile(CREDS_FILE):
            os.remove(CREDS_FILE)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- Chrome
def find_chrome_exe():
    candidates = (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    )
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def launch_kwargs():
    chrome_exe = find_chrome_exe()
    kw = dict(user_data_dir=CHROME_PROFILE, headless=False,
              args=["--start-maximized"], no_viewport=True)
    if chrome_exe:
        kw["executable_path"] = chrome_exe
    return kw


# --------------------------------------------------------------------------- helper
async def first_visible(page, selectors, timeout_each=3000):
    """คืน locator ตัวแรกที่ visible จาก list ของ selector, None ถ้าไม่เจอ"""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=timeout_each)
            return loc
        except Exception:
            continue
    return None


async def _find_login_link(page):
    """หา element ลิงก์/ปุ่ม 'Login' (ข้อความตรงตัว อังกฤษ/ไทย) ที่มองเห็น -> คืน locator หรือ None
    เว็บ aztek เมื่อยังไม่ login จะโชว์ลิงก์นี้มุมขวาบน (URL ยังเป็นหน้าเดิม ไม่มีคำว่า login/auth
    และไม่มีช่อง password จนกว่าจะคลิกลิงก์นี้)"""
    pat = re.compile(r"^\s*(log\s?in|sign\s?in|เข้าสู่ระบบ)\s*$", re.I)
    getters = (
        lambda: page.get_by_role("link", name=pat),
        lambda: page.get_by_role("button", name=pat),
        lambda: page.get_by_text(pat),           # เผื่อ 'Login' เป็นแค่ข้อความ/ปุ่มที่ไม่ใช่ role มาตรฐาน
    )
    for getter in getters:
        try:
            loc = getter().first
            if await loc.count() > 0 and await loc.is_visible():
                return loc
        except Exception:
            continue
    return None


async def is_logged_in(page):
    try:
        url = page.url.lower()
    except Exception:
        return False
    if any(k in url for k in ("login", "signin", "sign-in", "auth")):
        return False
    # มีช่อง password โผล่ = ยังอยู่หน้าฟอร์ม login (SPA)
    try:
        pw = page.locator("input[type='password']")
        if await pw.count() > 0 and await pw.first.is_visible():
            return False
    except Exception:
        pass
    # ตัวชี้หลัก: เว็บ aztek ยังไม่ login จะโชว์ลิงก์ 'Login' + หน้า 'No Permission Here' (URL เป็นหน้า
    # เดิม ไม่มีคำว่า login/auth และยังไม่มีช่อง password) — โค้ดเดิมไม่ดักตรงนี้เลยเข้าใจผิดว่า login แล้ว
    try:
        if await _find_login_link(page) is not None:
            return False
    except Exception:
        pass
    return True


LOGIN_SELECTORS = {
    "user": ['input[name="username"]', 'input[name="email"]', 'input[autocomplete="username"]',
             'input[type="email"]', 'input[type="text"]'],
    "pass": ['input[name="password"]', 'input[autocomplete="current-password"]',
             'input[type="password"]'],
    "submit": ['button[type="submit"]', 'button:has-text("เข้าสู่ระบบ")', 'button:has-text("Login")',
               'button:has-text("Sign in")', 'input[type="submit"]'],
}


async def _goto_login_form(page, dbg=None, timeout_ms=15000):
    """พาไปยังฟอร์ม login จริง (หน้าที่มีช่อง password): ถ้าตอนนี้เป็นหน้า 'No Permission' ที่มีแค่
    ลิงก์ 'Login' -> คลิกลิงก์เพื่อไปหน้า auth ของเซิร์ฟนั้นก่อน
    คืน  'form'      = ถึงฟอร์มแล้ว (มีช่อง password ให้กรอก)
         'logged_in' = auth ยังจำ session ได้ คลิกแล้วเด้งกลับมา login ให้เลย (ไม่มีฟอร์มให้กรอก)
         ''          = ไปไม่ถึงไหน
    เคส 'logged_in' สำคัญ: เดิมรอฟอร์มจนหมดเวลาแล้วคืน False ทั้งที่ login สำเร็จแล้ว
    -> ผู้เรียกไปรายงานว่า 'ยังไม่ได้ login' ทั้งที่เข้าได้ปกติ"""
    async def _pw_ready():
        try:
            pw = page.locator("input[type='password']")
            return await pw.count() > 0 and await pw.first.is_visible()
        except Exception:
            return False
    if await _pw_ready():
        return "form"
    link = await _find_login_link(page)
    if link is None:
        if dbg:
            dbg("goto_form: หาลิงก์ 'Login' ไม่เจอ")
        return ""
    if dbg:
        dbg("goto_form: คลิกลิงก์ 'Login' เพื่อไปหน้าฟอร์ม")
    try:
        await link.click()
    except Exception as e:
        if dbg:
            dbg("goto_form: คลิก EXC %r" % e)
        return ""
    ok_streak = 0
    for _ in range(max(1, timeout_ms // 500)):
        await page.wait_for_timeout(500)
        if await _pw_ready():
            if dbg:
                dbg("goto_form: ถึงฟอร์ม login แล้ว url=%s" % page.url)
            return "form"
        # เด้งกลับมาแบบ login แล้ว (SSO) — เช็คติดกัน 2 ครั้งกันจังหวะหน้ากำลังเปลี่ยน
        if await is_logged_in(page):
            ok_streak += 1
            if ok_streak >= 2:
                if dbg:
                    dbg("goto_form: auth จำ session ได้ กลับมา login แล้ว url=%s" % page.url)
                return "logged_in"
        else:
            ok_streak = 0
    if dbg:
        dbg("goto_form: คลิกแล้วแต่ฟอร์มไม่โผล่ url=%s" % page.url)
    return ""


async def try_auto_login(page, creds, log=None, timeout_ms=15000, dbg=None):
    """กรอก user/pass ในหน้า login ปัจจุบันแล้วกดเข้าสู่ระบบให้อัตโนมัติ
    คืน True ถ้าหลุดออกจากหน้า login สำเร็จ (session ใช้ได้แล้ว), False ถ้าทำไม่ได้
    (หาช่องไม่เจอ / กรอกแล้วไม่ผ่าน) — ผู้เรียกควรปล่อยให้ผู้ใช้กรอกเองต่อเมื่อ False
    dbg = ฟังก์ชัน log(msg) ไว้เขียน trace ลงไฟล์ (ถ้ามี)"""
    if not creds or not creds.get("user") or not creds.get("password"):
        if dbg:
            dbg("auto_login: ไม่มี creds")
        return False
    # ก้าว 0: ยังไม่ login เว็บจะเป็นหน้า 'No Permission' + ลิงก์ 'Login' (ยังไม่ใช่ฟอร์ม)
    #         ต้องคลิก 'Login' ไปหน้า auth ของเซิร์ฟนั้นก่อน แล้วค่อยกรอก user/pass
    state = await _goto_login_form(page, dbg=dbg)
    if state == "logged_in":      # auth จำ session ได้ -> ไม่ต้องกรอกอะไรเลย ถือว่าสำเร็จ
        if log:
            log("  ● login กลับมาแล้ว (auth จำ session ได้)", "SUCCESS")
        return True
    if state != "form":
        if dbg:
            dbg("auto_login: ไปหน้าฟอร์ม login ไม่ได้")
        return False
    try:
        u = await first_visible(page, LOGIN_SELECTORS["user"], timeout_each=2500)
        p = await first_visible(page, LOGIN_SELECTORS["pass"], timeout_each=2500)
        if dbg:
            dbg("auto_login: เจอช่อง user=%s pass=%s" % (bool(u), bool(p)))
        if not u or not p:
            return False
        await u.fill(creds["user"])
        await p.fill(creds["password"])
        btn = await first_visible(page, LOGIN_SELECTORS["submit"], timeout_each=1500)
        if dbg:
            dbg("auto_login: ปุ่ม submit=%s -> %s" % (bool(btn), "click" if btn else "Enter"))
        if btn:
            await btn.click()
        else:
            await p.press("Enter")
    except Exception as e:
        if log:
            log("  ! auto-login กรอกฟอร์มไม่สำเร็จ", "WARNING")
        if dbg:
            dbg("auto_login: กรอกฟอร์ม EXC %r" % e)
        return False
    for _ in range(max(1, timeout_ms // 500)):
        try:
            await page.wait_for_timeout(500)
            if await is_logged_in(page):
                if dbg:
                    dbg("auto_login: login สำเร็จ url=%s" % page.url)
                return True
        except Exception as e:
            if dbg:
                dbg("auto_login: รอ EXC %r" % e)
            return False
    if dbg:
        dbg("auto_login: หมดเวลา ยังอยู่หน้า login url=%s" % page.url)
    return False


async def ensure_logged_in(page, log=None, dbg=None):
    """เช็ค + ซ่อม session ให้อัตโนมัติ: ถ้ายังไม่ login และมี user/pass เก็บไว้ (DPAPI)
    -> auto-login เงียบ ๆ ในหน้าเดิม แก้ปัญหา session หลุดกลางทาง โดยไม่ต้องกดปุ่ม login เอง
    ใช้ _settle_login_state (ไม่ใช่เช็ค is_logged_in ครั้งเดียว) กันเช็คเร็วเกินไปก่อนหน้าจะเรนเดอร์เสร็จ
    dbg = ฟังก์ชันเขียน trace ลง .aztek_login_debug.log (ไว้ไล่ปัญหาเวลา auto-login พลาด)"""
    if await _settle_login_state(page, dbg=dbg) == "ready":
        return True
    creds = load_creds()
    if not creds.get("user") or not creds.get("password"):
        if dbg:
            dbg("ensure: ยังไม่ login และไม่มี creds เก็บไว้")
        return False
    if log:
        log("  session หลุด — กำลัง login ใหม่ให้อัตโนมัติ...", "INFO")
    ok = await try_auto_login(page, creds, log=log, dbg=dbg)
    if log:
        log("  ● login กลับมาแล้ว (auto)" if ok else "  ! auto-login ไม่สำเร็จ", "SUCCESS" if ok else "WARNING")
    return ok


def _login_debugger():
    """คืนฟังก์ชัน log(msg) ที่เขียน trace การ login ลง .aztek_login_debug.log
    (ทับของเดิมทุกครั้ง -> ไฟล์เก็บเฉพาะครั้งล่าสุด อ่านง่าย) ไว้ debug ตอน auto-login มีปัญหา"""
    path = os.path.join(APP_DIR, ".aztek_login_debug.log")
    import datetime
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("===== login attempt %s =====\n"
                    % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        pass

    def _dbg(msg):
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write("  " + str(msg) + "\n")
        except Exception:
            pass
    return _dbg


async def _settle_login_state(page, dbg=None, timeout_ms=9000):
    """รอให้ SPA ตัดสินสถานะ auth ให้นิ่งก่อน แล้วบอกว่าตอนนี้อยู่ที่:
      'login' = เจอช่อง password หรือ url เป็นหน้า login/auth  ->  ต้อง auto-login
      'ready' = ไม่เจอสัญญาณ login จนครบเวลา (ถือว่า login อยู่แล้ว)
    แก้ต้นเหตุ 'เด้งออก': โค้ดเดิมเช็คเร็วเกินไปหลัง domcontentloaded ทั้งที่ SPA
    กำลังจะ redirect ไปหน้า login (client-side) -> เข้าใจผิดว่า login อยู่แล้วเลยปิด browser"""
    try:
        await page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 8000))
    except Exception:
        pass
    # หลัง networkidle: ถ้ายังไม่ login (เจอลิงก์ 'Login'/ช่อง password/url auth) รีบคืน 'login'
    # ถ้าเห็นว่า login แล้ว เช็คซ้ำอีกไม่กี่ครั้ง (~1 วิ) กันลิงก์ 'Login' เรนเดอร์ช้า แล้วค่อยสรุป 'ready'
    for i in range(4):
        if not await is_logged_in(page):
            if dbg:
                dbg("settle@%d: ยังไม่ login url=%s" % (i, page.url))
            return "login"
        await page.wait_for_timeout(300)
    if dbg:
        dbg("settle: login อยู่แล้ว url=%s" % page.url)
    return "ready"


# --------------------------------------------------------------------------- form helpers (ใช้ร่วมทุก tool)
async def _find(page, selectors, last=False, timeout=2500):
    """คืน locator ตัวแรก (หรือ last) ที่ visible จาก list ของ selector, None ถ้าไม่เจอ"""
    for sel in selectors:
        try:
            loc = page.locator(sel)
            loc = loc.last if last else loc.first
            await loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:
            continue
    return None


async def _fill(page, value, selectors, last=False, log=None, label=""):
    """กรอกค่าลงช่องแรกที่เจอ — คืน True/False ตามสำเร็จ (value ว่าง = False)"""
    if value is None or str(value).strip() == "":
        return False
    loc = await _find(page, selectors, last=last)
    if not loc:
        if log:
            log("  ! หาช่องไม่เจอ: " + (label or selectors[0]), "WARNING")
        return False
    try:
        await loc.fill(str(value)); return True
    except Exception:
        try:
            await loc.click(); await loc.type(str(value)); return True
        except Exception:
            if log:
                log("  ! กรอกไม่สำเร็จ: " + (label or selectors[0]), "WARNING")
            return False


async def _set_datetime(page, value, label_th, log=None):
    """เซ็ตช่องวันเวลา (หา input ถัดจาก label) — คืน True/False"""
    if not value:
        return False
    loc = await _find(page, [
        'xpath=//*[contains(normalize-space(.),"%s")]/following::input[1]' % label_th,
        'input[placeholder*="%s"]' % label_th], timeout=2500)
    if not loc:
        if log:
            log("  ! หาช่องเวลาไม่เจอ: " + label_th, "WARNING")
        return False
    try:
        await loc.fill(str(value)); return True
    except Exception:
        try:
            await loc.evaluate(
                "(el,v)=>{el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}));"
                "el.dispatchEvent(new Event('change',{bubbles:true}));}", str(value))
            return True
        except Exception:
            if log:
                log("  ! เซ็ตเวลาไม่สำเร็จ: " + label_th, "WARNING")
            return False


async def _add_bundle(page, i0, bundle_id, log=None):
    """ค้นหา+กดเพิ่ม bundle เฉพาะภายในกล่องชุดรางวัลที่ i0 (กัน id ซ้ำข้ามชุด)"""
    block = page.locator(
        'xpath=(//input[@name="rewards.%d.name_th"]/ancestor::*[.//input[@type="search"]])[last()]' % i0)
    try:
        box = block.locator('input[type="search"]').first
        await box.wait_for(state="visible", timeout=3000)
        await box.fill(str(bundle_id))
    except Exception:
        if log:
            log("  ! หาช่องค้นหา Bundle (ชุดที่ %d) ไม่เจอ" % (i0 + 1), "WARNING")
        return False
    try:
        await block.locator('button', has_text="ค้นหา").first.click()
    except Exception:
        pass
    await page.wait_for_timeout(1300)
    try:
        add = block.locator("tr", has_text=str(bundle_id)).locator('button', has_text="เพิ่ม").first
        await add.wait_for(state="visible", timeout=3000)
        await add.click()
        if log:
            log("    + bundle %s (ชุดที่ %d)" % (bundle_id, i0 + 1), "INFO")
        await page.wait_for_timeout(400)
        return True
    except Exception:
        try:
            add = block.locator('xpath=.//*[contains(normalize-space(.),"%s")]'
                                 '/following::button[contains(normalize-space(.),"เพิ่ม")][1]' % bundle_id).first
            await add.click()
            if log:
                log("    + bundle %s (ชุดที่ %d)" % (bundle_id, i0 + 1), "INFO")
            await page.wait_for_timeout(400)
            return True
        except Exception:
            if log:
                log("  ! เพิ่ม bundle %s (ชุดที่ %d) ไม่สำเร็จ (ค้นหาไม่เจอ?)" % (bundle_id, i0 + 1), "WARNING")
            return False


# --------------------------------------------------------------------------- session
def _default_log(msg, level="INFO"):
    print("[%s] %s" % (level, msg))


def clear_profile():
    import shutil
    try:
        if os.path.isdir(CHROME_PROFILE):
            shutil.rmtree(CHROME_PROFILE, ignore_errors=True)
        return True
    except Exception:
        return False


def has_session():
    return os.path.isdir(CHROME_PROFILE)


class AztekSession:
    """เปิด/ปิด Playwright context ที่ผูกกับ persistent profile

    open_login(url)   -> เปิด browser ให้ผู้ใช้ login เอง แล้วรอจนปิด (เก็บ session)
    context(url)      -> async context manager คืน (browser, page) ที่ login แล้ว
    """

    def __init__(self, log=None, should_cancel=None):
        self.log = log or _default_log
        self.should_cancel = should_cancel or (lambda: False)

    async def open_login(self, url):
        if not PW_OK:
            self.log("ไม่พบ playwright - รัน: pip install playwright แล้ว playwright install chromium", "ERROR")
            return
        self.log("กำลังเปิดหน้า login: " + url, "INFO")
        try:
            acquire_browser(getattr(self, "tool_name", ""))
        except BrowserBusy as e:
            self.log("✋ " + str(e), "ERROR")
            return
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch_persistent_context(**launch_kwargs())
                page = browser.pages[0] if browser.pages else await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                self.log("  Login แล้วปิด browser ได้เลย", "SUCCESS")
                await self._idle_until_closed(browser, page)
                self.log("  Profile saved", "SUCCESS")
        finally:
            release_browser()

    async def login(self, url):
        """เข้าสู่ระบบแบบ auto + เขียน trace ละเอียดลง .aztek_login_debug.log
        ต่างจากเดิม 2 จุดที่แก้อาการ 'เด้งออก':
          (1) รอ SPA เช็ค auth/redirect ให้เสร็จก่อนตัดสิน (_settle_login_state) — กันเข้าใจ
              ผิดว่า 'login อยู่แล้ว' ทั้งที่กำลังจะเด้งไปหน้า login แล้วปิด browser ทิ้ง
          (2) ไม่ปิด browser เอง — ค้างไว้ให้เห็นผล/ปิดเองเสมอ"""
        if not PW_OK:
            self.log("ไม่พบ playwright - รัน: pip install playwright แล้ว playwright install chromium", "ERROR")
            return
        dbg = _login_debugger()
        try:
            acquire_browser(getattr(self, "tool_name", ""))
        except BrowserBusy as e:
            self.log("✋ " + str(e), "ERROR")
            dbg("BUSY: " + str(e))
            return
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch_persistent_context(**launch_kwargs())
                page = browser.pages[0] if browser.pages else await browser.new_page()
                dbg("goto " + url)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    dbg("goto EXC %r" % e)
                dbg("after goto url=" + (page.url or ""))
                # รอ SPA ตัดสิน auth เสร็จก่อน (client-side redirect ไป auth ใช้เวลานิดนึง)
                state = await _settle_login_state(page, dbg=dbg, timeout_ms=9000)
                dbg("settled=%s url=%s" % (state, page.url))
                if state == "ready":
                    self.log("● login พร้อมอยู่แล้ว (session ใช้ได้)", "SUCCESS")
                else:
                    creds = load_creds()
                    dbg("creds user=%r haspw=%s" % (creds.get("user"), bool(creds.get("password"))))
                    if creds.get("user") and creds.get("password"):
                        self.log("กำลังกรอก user/pass ให้อัตโนมัติ...", "INFO")
                        ok = await try_auto_login(page, creds, log=self.log, dbg=dbg)
                        dbg("auto_login ok=%s final_url=%s" % (ok, page.url))
                        if ok:
                            self.log("● Login สำเร็จ (auto)", "SUCCESS")
                        else:
                            self.log("  ! auto-login ไม่สำเร็จ — ล็อกอินมือในหน้าต่างนี้ได้เลย", "WARNING")
                    else:
                        self.log("  ยังไม่ได้เก็บ user/pass — ล็อกอินมือในหน้าต่างนี้ได้เลย", "INFO")
                        dbg("ไม่มี creds")
                # ค้าง browser ไว้เสมอ ให้เห็นผล + ปิดเอง (session เซฟตอนปิด) — ไม่เด้งออก
                self.log("  ตรวจผลในหน้าต่างเว็บได้ แล้วปิด browser เมื่อเสร็จ", "INFO")
                await self._idle_until_closed(browser, page)
                self.log("  Profile saved", "SUCCESS")
                dbg("ปิดโดยผู้ใช้")
        finally:
            release_browser()

    async def _idle_until_closed(self, browser, page):
        """รอจนผู้ใช้ปิด browser (หรือกดยกเลิก) แล้ว 'ปิดให้เรียบร้อย' เสมอ
        สำคัญ: ต้อง close() ทุกเส้นทาง — เดิมพอผู้ใช้ปิดหน้าต่างเองจะ return เฉย ๆ
        ทำให้ Chrome โดนฆ่าตอน playwright teardown ก่อนเขียน cookie ลง profile
        -> รอบถัดไปเปิดมาแล้วกลายเป็น 'login หลุด' ทั้งที่เพิ่ง login ไป"""
        try:
            while not self.should_cancel():
                if not browser.pages:
                    break
                await page.wait_for_timeout(500)
        except Exception:
            pass
        finally:
            try:
                await browser.close()      # flush cookie/session ลง profile
            except Exception:
                pass

    async def _wait_user_login(self, browser, page, timeout_ms=300000):
        """รอผู้ใช้ login เองในหน้าต่างที่เปิดค้างอยู่ (auto-login ซ่อมไม่ได้)
        คืน True ทันทีที่ login ผ่าน / False เมื่อผู้ใช้ปิด browser, กดยกเลิก หรือหมดเวลา"""
        waited = 0
        while waited < timeout_ms:
            if self.should_cancel() or not browser.pages:
                return False
            try:
                if await is_logged_in(page):
                    return True
            except Exception:
                return False
            await page.wait_for_timeout(1000)
            waited += 1000
        return False

    async def run_page(self, url, coro, hold=False):
        """เปิด context ที่ login แล้ว, goto url, เรียก coro(page) 1 ครั้ง
        hold=True -> ค้าง browser ไว้จนผู้ใช้ปิดเอง (ไว้ตรวจ/กดบันทึกเอง)
        hold=False -> ปิด browser หลังทำงานเสร็จ
        """
        if not PW_OK:
            self.log("ไม่พบ playwright - รัน: pip install playwright แล้ว playwright install chromium", "ERROR")
            return
        try:
            acquire_browser(getattr(self, "tool_name", ""))
        except BrowserBusy as e:
            self.log("✋ " + str(e), "ERROR")
            return
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch_persistent_context(**launch_kwargs())
                page = browser.pages[0] if browser.pages else await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                if not await ensure_logged_in(page, log=self.log, dbg=_login_debugger()):
                    # auto-login ซ่อมไม่ได้ -> เปิดค้างให้ login มือ "แล้วทำงานต่อให้เอง"
                    # (เดิมแค่รอจนปิด browser แล้วเลิก = ผู้ใช้เห็นเป็นค้างไปเฉย ๆ)
                    if hold:
                        self.log("✋ ยังไม่ได้ login — ล็อกอินในหน้าต่างที่เปิดอยู่ได้เลย "
                                 "เดี๋ยวทำงานต่อให้อัตโนมัติ", "WARNING")
                        if not await self._wait_user_login(browser, page):
                            self.log("  หยุดไว้ก่อน: ยังไม่ได้ login (ปิด browser / หมดเวลา)", "ERROR")
                            await self._idle_until_closed(browser, page)
                            return
                        self.log("● login แล้ว — ทำงานต่อ", "SUCCESS")
                    else:
                        self.log("✋ ยังไม่ได้ login — กดปุ่ม 'เข้าสู่ระบบ' ก่อน แล้วค่อยลองใหม่", "ERROR")
                        try:
                            await browser.close()
                        except Exception:
                            pass
                        return
                if url.split("?")[0].rstrip("/") not in page.url:
                    # auto-login เมื่อกี้อาจพาไปหน้าอื่น (เช่น dashboard) -> กลับไปหน้าที่ต้องการทำงานจริง
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    except Exception:
                        pass
                try:
                    await coro(page)
                finally:
                    if hold:
                        self.log("  ตรวจฟอร์มในหน้าเว็บได้เลย แล้วกดบันทึกเอง / ปิด browser เมื่อเสร็จ", "SUCCESS")
                        await self._idle_until_closed(browser, page)
                    else:
                        try:
                            await browser.close()
                        except Exception:
                            pass
        finally:
            release_browser()

    def context(self, url):
        return _AztekContext(self, url)


class _AztekContext:
    def __init__(self, session, url):
        self.session = session
        self.url = url
        self._pw = None
        self._browser = None

    async def __aenter__(self):
        if not PW_OK:
            raise RuntimeError("playwright ไม่ได้ติดตั้ง - รัน: pip install playwright && playwright install chromium")
        acquire_browser(getattr(self.session, "tool_name", ""))   # กัน browser ชนกัน (อาจ raise BrowserBusy)
        try:
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch_persistent_context(**launch_kwargs())
            page = self._browser.pages[0] if self._browser.pages else await self._browser.new_page()
            await page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
            if not await ensure_logged_in(page, log=self.session.log):
                # ยังไม่ได้ login (และ auto-login ซ่อมไม่ได้) -> abort (ไม่ให้ bulk loop ทำงานลงหน้า login)
                raise RuntimeError("ยังไม่ได้ login — กดปุ่ม 'เข้าสู่ระบบ' ก่อน แล้วลองใหม่")
            if self.url.split("?")[0].rstrip("/") not in page.url:
                try:
                    await page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    pass
            return self._browser, page
        except Exception:
            await self._cleanup()
            release_browser()
            raise

    async def _cleanup(self):
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        try:
            if self._pw:
                await self._pw.stop()
        except Exception:
            pass
        self._browser = None
        self._pw = None

    async def __aexit__(self, exc_type, exc, tb):
        await self._cleanup()
        release_browser()
        return False
