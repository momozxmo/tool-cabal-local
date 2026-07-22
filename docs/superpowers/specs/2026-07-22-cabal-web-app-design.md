# All for Cabal — Web Application (MVP: Item Finder) — Design Spec

- **วันที่**: 2026-07-22
- **สถานะ**: อนุมัติดีไซน์แล้ว (รอรีวิว spec ก่อนทำแผน implementation)
- **ขอบเขต v1**: พอร์ต **Item Finder** ขึ้นเว็บให้ทีมเล็กใช้ร่วมกัน (tool อื่นเพิ่มทีหลังผ่าน plugin)

---

## 1. เป้าหมาย

เปลี่ยน toolkit เดสก์ท็อป "All for Cabal" (Python/tkinter + Playwright ที่ควบคุม aztek-tools.combo-interactive.com อัตโนมัติ) ให้เป็น **web application ที่ทีมเล็ก 2-5 คนใช้ร่วมกันได้** โดยยังทำงานได้เหมือนเดิม เริ่มจาก tool ที่ใช้บ่อยสุดคือ Item Finder

## 2. บริบทของโค้ดเดิม (ที่จะ reuse)

- Launcher: `all_for_cabal.py` — เปิด 4 tool: Item Finder (`item_finder.py`), Create Bundle (`new_tool.py`), Item Code (`itemcode_tool.py`), Event (`event_tool.py`)
- ใช้ร่วม: `aztek_core.py` (session/browser + `acquire_browser`/`release_browser` lock + `CHROME_PROFILE`), `ui_common.py`, `config.py`, `tool_registry.py` (pattern `TOOL = ToolSpec(...)`)
- Item Finder logic หลัก: `_start` → `_run_thread` → `_auto` → `_search_all` → `_check_item_detail`; ตัว parse template (`read_template`, `parse_shop_workbook`, `parse_event_workbook`); deep-check params; โหมด Shop (อ่านคำอธิบายไอเทมจาก `textarea[name="detail"]`, `img=yes` ทุกตัว); การดึงค่าจริงบนเว็บ; export xlsx/csv
- ปัจจุบัน login aztek = เปิด Chrome จริงให้ผู้ใช้ล็อกอินเอง แล้วเก็บ persistent profile (`CHROME_PROFILE`)

## 3. การตัดสินใจที่ lock แล้ว

| หัวข้อ | ผล |
|---|---|
| ผู้ใช้ | ทีมเล็ก 2-5 คน, พร้อมกันไม่กี่คน |
| บัญชี aztek | **แต่ละคนมีบัญชีของตัวเอง** |
| Login aztek | **import session ผ่าน browser extension** (ผู้ใช้ล็อกอิน aztek ในเบราว์เซอร์ตัวเอง → กด extension → ส่ง cookies+localStorage มาเก็บ) |
| แนวทาง | **Approach A**: reuse โค้ด Python เดิม + FastAPI + Playwright + async queue + WebSocket |
| โหมด browser | **headless** (มี de-risk spike กับ aztek ก่อน; fallback = headful+Xvfb บน host ใหญ่ หรือใช้ desktop) |
| ต่อยอด tool | **plugin registry** (ต่อจาก `ToolSpec` เดิม) |
| Audit log | มี — ใคร/ทำอะไร/บัญชี aztek/เมื่อไหร่/ผล |
| DB | **Supabase หรือ Neon** (Postgres ฟรีถาวร) |
| Hosting | เริ่ม Render free (512MB) → ย้าย GCP e2-micro/Hetzner ได้ (Docker portable) |
| บัญชีเว็บแอป | admin สร้างให้ ไม่เปิดสมัครเอง |
| Concurrency | รันทีละ 1 งานบน free tier, ที่เหลือเข้าคิว (ผู้ใช้เห็นสถานะ) |
| Desktop app | **เก็บไว้ใช้ได้** (แชร์ core เดียวกัน = fallback) |
| ข้อมูลงาน | เก็บ **template + ประวัติงาน** ใน DB ให้ทีมใช้ร่วม |
| MVP v1 | **Item Finder** ก่อน |
| Frontend | แนะนำ React+Vite (หรือ HTMX) — ยังเลือกได้ทีหลัง |

## 4. สถาปัตยกรรม

```
[Browser Extension] --(cookies + localStorage ของ origin aztek)--> [Backend]
[Web Frontend (SPA)] <---- REST + WebSocket ----> [Backend: FastAPI]
                                                    ├── Auth (บัญชีเว็บแอป)
                                                    ├── Tool Registry (plugin)
                                                    ├── Job Queue (async, รันทีละ 1)
                                                    ├── Automation Core (reuse โค้ดเดิม, แยกจาก tkinter)
                                                    └── Playwright Worker (headless + storageState ต่อ user)
[Postgres: Supabase / Neon]
   users · aztek_sessions(เข้ารหัส) · jobs(คิว+ผล+ประวัติ) · templates · audit_log
```

**หน่วยย่อยและหน้าที่ (แต่ละตัวเข้าใจ/เทสต์แยกได้):**

- **Automation Core** (โมดูล Python ล้วน, ไม่มี GUI): รับ config + page + log callback → คืนผลลัพธ์. reuse logic ค้นหา/deep-check/parse เดิม
- **Tool Registry**: แต่ละ tool ประกาศ `input schema` + `job handler` + `result shape`; เพิ่ม tool ใหม่ = drop โมดูล ไม่แตะ core
- **Job Queue / Worker**: คิว async, จำกัด concurrency, เรียก Automation Core ผ่าน Playwright Worker
- **Playwright Worker**: เปิด headless Chromium, inject `storageState` ของ user, รันงาน, ยิง progress ผ่าน callback → WebSocket
- **Session Store**: เก็บ/ถอด `storageState` ต่อ user (เข้ารหัส)
- **Frontend**: หน้า login, เชื่อม aztek, หน้า Item Finder, คิว/ประวัติ, templates, audit (admin)
- **Extension**: ดึง cookies+localStorage ของ aztek แล้ว POST เข้า backend

## 5. Flow การใช้งาน (Item Finder)

1. ผู้ใช้ login เว็บแอป (บัญชีที่ admin สร้าง)
2. **เชื่อม aztek**: ล็อกอิน aztek ในเบราว์เซอร์ตัวเอง (ผ่าน captcha/2FA ที่นั่น) → กดปุ่ม extension "ส่ง session" → backend เก็บ `storageState` เข้ารหัสต่อ user
3. เลือก/อัปโหลด template Excel + ตั้งค่าค้นหา (deep-check, โหมด shop/event/itemcode, แสดงผลบนเว็บ) → submit
4. งานเข้า **คิว** → worker รับเมื่อมี slot ว่าง → เปิด headless Chromium ด้วย storageState ของ user
5. รันค้นหา (reuse: `_search_all`/`_check_item_detail`, deep-check, คำอธิบาย Shop, ค่าจริงบนเว็บ) → **stream log/progress สดผ่าน WebSocket** (แทนแท็บ Log เดิม)
6. ผลขึ้น **ตาราง** (คอลัมน์เหมือน Treeview เดิม + คอลัมน์คำอธิบายไอเทมโหมด Shop) → **export xlsx/csv** → บันทึกผลใน `jobs`
7. ทุก action → `audit_log`

## 6. งานหลัก: refactor tkinter → service layer (ความเสี่ยงสูงสุด)

แยก automation logic ออกจาก class GUI ให้เป็นโมดูลใช้ซ้ำได้:

| เดิม (ผูก GUI) | ใหม่ (service) |
|---|---|
| `self.log(msg, lvl)` → Text widget | log callback/async emitter → WebSocket |
| `self.vgame.get()` ฯลฯ | รับเป็น config object (มี `_start` build `data` dict อยู่แล้ว = ฐานดี) |
| Playwright persistent `CHROME_PROFILE` | inject `storageState` ต่องาน (จาก session ที่ import) |
| `_search_all`/`_check_item_detail`/parsers อยู่ใน class `App` | ย้ายออกเป็นโมดูล รับ `(page, config, log_cb)` |
| `acquire_browser` lock (โปรไฟล์ร่วม) | คุมด้วย job queue แทน (แต่ละ user คนละ storageState) |

หลัก refactor: **ทำครั้งเดียว ใช้ได้ทั้งเว็บและ desktop** — desktop เดิมผูก GUI เข้ากับ core ตัวเดียวกัน (fallback)

## 7. Browser extension

- Manifest v3, ขอ permission `cookies` + host ของ aztek เท่านั้น
- ปุ่มเดียว: อ่าน cookies (รวม httpOnly ที่ extension เข้าถึงได้) + localStorage ของ origin aztek → ประกอบเป็น `storageState` → POST เข้า backend (แนบ token ของผู้ใช้เว็บแอป)
- แจกแบบ private (unpacked/developer mode หรือไฟล์ให้ทีมติดตั้งเอง) — ไม่ต้องขึ้น store
- ไม่เก็บ/ส่งรหัสผ่าน aztek — ส่งแค่ session

## 8. Data model (Postgres)

- **users**: id, email/username, password_hash, role (admin/member), created_at
- **aztek_sessions**: id, user_id, storage_state_encrypted, aztek_account_label, updated_at, expires_hint
- **jobs**: id, user_id, tool ('item_finder'), status (queued/running/done/failed), config_json, template_ref, result_json (ผลค้นหา), log_ref, created_at, finished_at
- **templates**: id, owner_user_id, name, tool, content (parsed rows/ไฟล์), shared (bool), created_at
- **audit_log**: id, user_id, aztek_account_label, action, tool, params_summary, status, result_summary, created_at

หมายเหตุ: `aztek_sessions.storage_state_encrypted` เข้ารหัส at-rest; `audit_log` ไม่เก็บ cookie/ข้อมูลลับดิบ

## 9. Job queue & concurrency

- Queue แบบ async ใน process (พอสำหรับ 2-5 คน — ไม่ต้อง Redis/Celery)
- **concurrency = 1** บน free tier (512MB) → งานอื่นเข้าคิว, ผู้ใช้เห็นตำแหน่งคิว/สถานะ
- ปรับ concurrency ขึ้นได้เมื่อย้าย host RAM มากขึ้น (config เดียว)
- งานยกเลิกได้ (เทียบ `_cancel` เดิม)

## 10. Live progress (WebSocket)

- ต่อ WebSocket ต่อ job → รับ log line + progress (%) + ผลลัพธ์ทีละแถว (แบบ `add_result_row` เดิม)
- reconnect ได้ (ถ้าหลุด ดึง log/สถานะล่าสุดจาก DB)

## 11. ความปลอดภัย & ความเป็นส่วนตัว

- session aztek เข้ารหัส at-rest, แยก per-user, ผู้ใช้เห็น/ใช้ได้แค่ของตัวเอง
- บัญชีเว็บแอป: admin สร้าง, password hash (argon2/bcrypt), ไม่มี public signup
- audit ครบทุก action ที่แตะ aztek (accountability)
- extension เข้าถึงเฉพาะ origin aztek, ส่งเฉพาะ session
- ไม่เก็บรหัสผ่าน aztek ที่ใดเลย

## 12. จัดการ error

- **session หมดอายุ** (โดนเด้ง login/401 ระหว่างรัน) → job = failed + ข้อความ "connect aztek ใหม่" + ปุ่มพาไป import
- **headless โดนบล็อก** → ตรวจจับ (login ไม่ผ่านทั้งที่ session valid / เจอหน้า bot) → แจ้งชัด + เสนอ fallback
- **worker OOM/crash** → job = failed, log ไว้, queue ไปต่อ
- **launch browser ล้มเหลว** → retry มีเพดาน แล้ว fail

## 13. ความเสี่ยง headless & ทางแก้

- เสี่ยง: aztek อาจตรวจจับ headless แล้วทำงานต่างออกไป
- ลดเสี่ยง: ใช้ Chromium **new-headless mode**; ถ้ายังโดน → headful + Xvfb (RAM เยอะ = host ใหญ่ขึ้น) หรือใช้ desktop app (headful ในเครื่อง) เป็น fallback
- **ต้องเทสต์เป็นสเตปแรก** ก่อนลงแรงหนัก (ดูเฟส 0)

## 14. Hosting & deployment

- ทุกอย่าง Docker (backend + worker + static frontend) → portable
- เริ่ม **Render free (512MB)** + **Supabase/Neon** (DB)
- ถ้า headless ไม่รอด/RAM ตึง → ย้าย GCP e2-micro (1GB, ฟรี) หรือ Hetzner (4GB, ~$5) โดยไม่แก้โค้ด
- HTTPS: platform ให้มาเอง หรือ Cloudflare Tunnel (ถ้า self-host)

## 15. Testing

- **เฟส 0 spike**: เทสต์ headless + inject storageState กับ aztek จริง (login + ค้น 1 ตัว) — de-risk อันดับ 1
- unit test service layer (parsers, deep-check, ตัวจัดคอลัมน์) — ต่อยอด `tests/test_pure.py`
- integration test job flow ด้วย fake/mock page (แนวเดียวกับ `verify_*.py` ที่ทำมา)
- e2e เบา ๆ: submit job → queue → result ครบ

## 16. แผนเป็นเฟส (v1 = Item Finder)

0. **Spike**: headless vs aztek (de-risk) — ถ้าไม่รอด ตัดสินใจ host/โหมดก่อนไปต่อ
1. **Refactor** Item Finder core ออกจาก tkinter → service layer (desktop ยังใช้ได้)
2. **Backend skeleton**: FastAPI + DB schema + auth + tool registry
3. **Extension** + import/เก็บ session (เข้ารหัส)
4. **Queue + Worker + WebSocket** (รัน Item Finder ผ่าน service layer)
5. **Frontend**: หน้า Item Finder (template/ค่า/รัน/log สด/ตารางผล/export) + templates + audit + admin
6. **Deploy** (Docker → Render + Supabase/Neon) + e2e

## 17. อนาคต (หลัง v1)

เพิ่ม **Create Bundle / Item Code / Event** เป็น plugin ทีละตัว (แต่ละตัว = โมดูลที่ประกาศ schema+handler+result) — ไม่แตะ core; รวมถึง flow "รวมผลค้นหาเป็นบันเดิล" ที่ปัจจุบันส่งจาก Item Finder ไป Create Bundle

## 18. เรื่องที่ยังเลือกได้ทีหลัง (ไม่ blocking)

- **Frontend stack**: React+Vite (แนะนำ) vs HTMX+server-rendered (Python ล้วน)
- host สุดท้าย (Render vs GCP vs Hetzner) — ขึ้นกับผล spike headless

## 19. นอกขอบเขต v1

- tool อื่นนอกจาก Item Finder (Create Bundle / Item Code / Event)
- login-stream (ตัดออก ใช้ import session แทน)
- multi-tenant/ทีมหลายทีม, billing, mobile app
- concurrency สูง/หลาย worker (ไว้ตอนสเกลใหญ่ขึ้น)
