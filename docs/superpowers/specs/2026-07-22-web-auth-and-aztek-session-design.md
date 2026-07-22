# All for Cabal Web Auth and Per-User Aztek Session Design

วันที่: 2026-07-22
สถานะ: อนุมัติแล้ว
ขอบเขต: ระบบล็อกอินเว็บ, บัญชีทีม, Chrome Extension สำหรับเชื่อม Aztek, session แยกต่อผู้ใช้ และ audit log

## 1. เป้าหมาย

เพิ่มระบบยืนยันตัวตนสองชั้นให้ All for Cabal Web:

1. ผู้ใช้ล็อกอินเข้าเว็บด้วยบัญชีที่ admin สร้างให้
2. ผู้ใช้เชื่อม session ของบัญชี Aztek ของตัวเองผ่าน Chrome Extension โดยระบบไม่เก็บรหัสผ่าน Aztek

Item Finder ต้องใช้ session ของผู้สั่งงาน ไม่ใช้ Chrome persistent profile ร่วมกัน และข้อมูล workspace, ผลค้นหา, export และ job ต้องแยกสิทธิ์ตามผู้ใช้

## 2. แนวทางที่เลือก

ใช้ FastAPI auth ที่ดูแลในแอปเอง, ฐานข้อมูลที่เข้าถึงผ่าน `DATABASE_URL`, session cookie แบบ HttpOnly และ Chrome Extension ที่ส่ง Aztek storage state ด้วย pairing token ใช้ครั้งเดียว

แนวทางนี้รองรับ SQLite ตอนพัฒนา และ PostgreSQL จาก Supabase หรือ Neon ตอน deploy โดยไม่ผูกระบบกับผู้ให้บริการรายใด สามารถย้ายจาก Render ไป Railway หรือ host อื่นได้โดยไม่เปลี่ยน flow หลัก

ไม่เลือก:

- Supabase Auth เพราะเพิ่มการผูกกับผู้ให้บริการและทำ admin-only provisioning ซับซ้อนขึ้น
- local-file auth เพราะไม่เหมาะกับ Render และทีมหลายคน

## 3. สถาปัตยกรรม

```text
[User] -> [All for Cabal Web] -> [FastAPI Auth] -> [Database]
                  |                    |
                  |                    +-> [Audit Log]
                  v
             [Job Queue] -> [Playwright Worker] -> [Aztek]
                                  ^
                                  |
[Chrome Extension] -> [One-time Pairing] -> [Encrypted Aztek Session Store]
```

องค์ประกอบหลัก:

- **Web Auth**: username/password, admin/member, server-side session
- **Authorization**: ตรวจเจ้าของ resource ทุก workspace, job, export และ WebSocket
- **Pairing Service**: สร้าง token อายุ 5 นาที ใช้ได้ครั้งเดียว
- **Aztek Session Store**: เข้ารหัส cookies/localStorage แยกต่อผู้ใช้
- **Playwright Worker**: สร้าง temporary browser context จาก storage state ของผู้สั่งงาน
- **Audit Service**: บันทึก action สำคัญโดยไม่บันทึก secret ดิบ
- **Chrome Extension**: อ่าน session เฉพาะ origin Aztek เมื่อผู้ใช้กดเชื่อมเอง

## 4. Roles และสิทธิ์

### Member

- ล็อกอิน/ล็อกเอาต์และเปลี่ยนรหัสผ่านของตัวเอง
- เชื่อม, เชื่อมใหม่ หรือยกเลิก session Aztek ของตัวเอง
- สร้างและเปิด workspace ของตัวเอง
- รัน Item Finder, ดูผล, export และสร้าง bundle preview จากงานของตัวเอง
- มองไม่เห็น resource ของผู้ใช้อื่น แม้รู้ URL หรือ ID

### Admin

- มีสิทธิ์ทั้งหมดของ member
- สร้างบัญชีผู้ใช้
- ปิด/เปิดใช้งานบัญชี
- ตั้งรหัสผ่านชั่วคราวหรือรีเซ็ตรหัสผ่าน
- ดูและค้นหา audit log
- ไม่สามารถดู cookies หรือ storage state ของ Aztek แบบ plaintext

ไม่มี public signup

## 5. Data model

### `users`

- `id`
- `username` (unique, normalized)
- `password_hash`
- `role` (`admin` / `member`)
- `is_active`
- `created_at`, `updated_at`, `last_login_at`
- `password_changed_at`

### `web_sessions`

- `id`
- `user_id`
- `token_hash` (ไม่เก็บ token ดิบ)
- `created_at`, `expires_at`, `revoked_at`
- `last_seen_at`
- metadata จำกัดเท่าที่จำเป็น เช่น IP และ User-Agent

### `pairing_tokens`

- `id`
- `user_id`
- `token_hash`
- `created_at`, `expires_at`, `used_at`

Token หมดอายุใน 5 นาทีและใช้ได้ครั้งเดียว การสร้าง token ใหม่ยกเลิก token เก่าที่ยังไม่ใช้ของผู้ใช้นั้น

### `aztek_sessions`

- `id`
- `user_id` (unique สำหรับ active session)
- `storage_state_encrypted`
- `aztek_account_label`
- `status` (`connected` / `expired` / `disconnected`)
- `created_at`, `updated_at`, `last_used_at`
- `expires_hint`

### `workspaces` และ `jobs`

- เพิ่ม `owner_user_id`
- Job เก็บ tool, config, status, result summary, log และเวลาที่เกี่ยวข้อง
- การค้นหา resource ต้องกรองด้วยเจ้าของเสมอ ไม่ตรวจเพียง ID

### `audit_logs`

- `id`, `user_id`
- `action`, `tool`, `resource_type`, `resource_id`
- `status`, `summary`
- `aztek_account_label`
- IP/User-Agent เท่าที่จำเป็น
- `created_at`

ห้ามบันทึก password, session cookie, pairing token, Aztek cookies หรือ storage state ดิบใน audit log

## 6. Web authentication

- Password hash ใช้ Argon2
- Login สำเร็จสร้าง random opaque session token
- Browser ได้รับ cookie แบบ `HttpOnly`, `Secure` ใน production และ `SameSite=Lax`
- Database เก็บเฉพาะ hash ของ session token
- Logout revoke session ปัจจุบัน
- เปลี่ยน/รีเซ็ตรหัสผ่าน revoke session เก่าของผู้ใช้นั้นทั้งหมด
- ปิดบัญชีแล้ว session เดิมใช้ต่อไม่ได้
- จำกัดความถี่และจำนวนครั้งของการ login ผิด
- Production บังคับ HTTPS

Admin คนแรกสร้างตอน startup จาก environment variables เมื่อฐานข้อมูลยังไม่มีผู้ใช้:

- `BOOTSTRAP_ADMIN_USERNAME`
- `BOOTSTRAP_ADMIN_PASSWORD`

ค่าที่เกี่ยวข้องเพิ่มเติม:

- `DATABASE_URL`
- `APP_SECRET_KEY`
- `AZTEK_SESSION_ENCRYPTION_KEY`
- `SESSION_COOKIE_SECURE`

## 7. Chrome Extension และ pairing flow

Extension ใช้ Manifest V3 และขอ permission เฉพาะ:

- `cookies`
- active tab/scripting เท่าที่จำเป็น
- host permission ของ Aztek และ backend ที่กำหนด

Flow:

1. ผู้ใช้ล็อกอินเว็บ
2. เปิดหน้า Connect Aztek และกดสร้าง pairing token
3. ผู้ใช้เปิด Aztek ใน Chrome และล็อกอินเอง รวม captcha/2FA ถ้ามี
4. เปิด Extension และกรอก pairing token
5. Extension อ่าน cookies ผ่าน `chrome.cookies` รวม HttpOnly ที่ permission อนุญาต
6. Extension อ่าน localStorage จาก origin Aztek ผ่าน content script
7. Extension POST storage state พร้อม pairing token ไป backend
8. Backend validate token, ทำเครื่องหมายว่าใช้แล้ว และเข้ารหัส storage state
9. หน้าเว็บแสดงสถานะเชื่อมแล้วและเวลาที่อัปเดต

Extension:

- ไม่อ่านหรือส่ง password
- ไม่ส่งข้อมูลจาก origin อื่น
- ไม่ทำงานอัตโนมัติ ผู้ใช้ต้องกดเอง
- ไม่เก็บ pairing token หลังสำเร็จ
- เวอร์ชันแรกแจกแบบ unpacked/private ให้ทีมติดตั้งเอง

## 8. การใช้ session ใน Playwright

เมื่อเริ่ม Item Finder job:

1. ตรวจ user และ ownership ของ workspace/job
2. โหลด encrypted storage state ของ user
3. ถอดรหัสในหน่วยความจำเฉพาะช่วงเริ่มงาน
4. สร้าง temporary Playwright browser context ด้วย storage state
5. รันงานด้วย queue concurrency เดิม
6. ปิด context และล้างข้อมูลชั่วคราวเมื่อจบ

Server ไม่ใช้ `.cabal_chrome_profile` หรือ persistent profile ร่วมกัน

ถ้าตรวจพบหน้า login, 401 หรือ state ใช้ไม่ได้:

- หยุดงานอย่างปลอดภัย
- ตั้ง job เป็น failed พร้อมเหตุผล `aztek_session_expired`
- เปลี่ยน session status เป็น `expired`
- แจ้งผู้ใช้ให้เชื่อม Aztek ใหม่
- บันทึก audit log โดยไม่มี session data ดิบ

## 9. API และ WebSocket security

Endpoint ที่เป็น public มีเพียง:

- หน้า login
- API login
- health check ที่ไม่เปิดเผยข้อมูลภายใน
- pairing endpoint ที่ยืนยัน one-time token และจำกัด rate

Endpoint อื่นต้องมี authenticated web session

- ทุก workspace query กรองด้วย `owner_user_id`
- export และ bundle preview ตรวจ owner ซ้ำ
- WebSocket ตรวจ session cookie ก่อน `accept`
- Search payload ไม่สามารถอ้าง workspace ของคนอื่น
- Admin endpoints ตรวจ role server-side
- ไม่เชื่อ role หรือ owner ที่ส่งมาจาก frontend

## 10. หน้าเว็บ

เพิ่มหน้า/มุมมอง:

- Login
- Account และเปลี่ยนรหัสผ่าน
- Connect Aztek พร้อม status/pair/reconnect/disconnect
- Admin Users
- Admin Audit Log

หน้า Item Finder เดิม:

- เปิดได้หลัง login
- แถบบนแสดง username, role, สถานะ Aztek และ Logout
- ปุ่มค้นหาถูกปิดถ้ายังไม่มี valid Aztek session
- ฟังก์ชัน import, plan selection, results, copy, export และ bundle preview คงอยู่

## 11. Audit actions

อย่างน้อยต้องบันทึก:

- `auth.login_succeeded`, `auth.login_failed`, `auth.logout`
- `user.created`, `user.disabled`, `user.enabled`, `user.password_reset`
- `aztek.pairing_created`, `aztek.connected`, `aztek.disconnected`, `aztek.expired`
- `workspace.created`, `workspace.deleted`
- `template.imported`, `plan.imported`
- `item_finder.started`, `item_finder.completed`, `item_finder.failed`, `item_finder.cancelled`
- `results.exported`, `bundle.previewed`

Summary ต้องลดข้อมูลให้เหลือเท่าที่ใช้ตรวจสอบ และไม่คัดลอก payload ลับทั้งหมด

## 12. Database และ migration

- Local development ใช้ SQLite
- Production ใช้ PostgreSQL ผ่าน `DATABASE_URL`
- รองรับ Supabase และ Neon
- ใช้ Alembic migration
- Schema และ query ต้องใช้ชนิดข้อมูลที่ทำงานได้ทั้ง SQLite/PostgreSQL ในส่วนที่ใช้ร่วม
- Render filesystem ไม่ถูกใช้เป็น source of truth ของบัญชี, session, job หรือ audit

## 13. การรักษาความเข้ากันได้

- Reuse Item Finder service/runner ที่มีอยู่
- Desktop tkinter app ยังทำงานแบบเดิมเป็น fallback
- Web เปลี่ยนจาก in-memory anonymous workspace เป็น authenticated owner-scoped persistence
- ไม่ย้าย Chrome profile จากเครื่องผู้ใช้ขึ้น server; ผู้ใช้เชื่อมใหม่ผ่าน Extension
- Tool ใหม่ในอนาคตใช้ auth, job ownership, session store และ audit service ชุดเดียวกัน

## 14. Error handling

- Login ผิดตอบข้อความกลาง ๆ ไม่บอกว่า username มีอยู่หรือไม่
- Pairing token ผิด/หมดอายุ/ใช้แล้วตอบสถานะชัดเจนแต่ไม่เปิดเผยเจ้าของ token
- Extension ส่ง payload ไม่ครบหรือ origin ไม่ตรงถูกปฏิเสธ
- Encryption key ผิดหรือ decrypt ไม่ได้ทำให้ session ใช้ไม่ได้ ไม่คืน ciphertext/plaintext ให้ client
- Database unavailable ตอบ service unavailable และไม่เริ่มงาน browser
- Worker crash ปิด context, ตั้ง job failed และปล่อย queue ไปงานถัดไป

## 15. Testing

### Unit

- password hashing/verification
- session token hashing/revocation/expiry
- pairing token one-time/expiry
- encryption/decryption และ ciphertext ไม่เท่ากับ plaintext
- role/ownership policies
- audit sanitization

### API integration

- login ถูก/ผิด/บัญชี disabled
- unauthenticated API ถูกปฏิเสธ
- member เปิด workspace/export ของคนอื่นไม่ได้
- admin user management ทำงานตามสิทธิ์
- pairing ใช้ซ้ำไม่ได้
- WebSocket ไม่มี auth หรืออ้าง workspace คนอื่นไม่ได้

### End-to-end

- bootstrap admin -> สร้าง member -> member login
- member pair Extension -> session connected
- member import -> search -> result -> export
- user อีกคนอ่านงานไม่ได้
- session หมดอายุ -> job failed -> reconnect prompt
- admin เห็น audit actions ที่คาดไว้โดยไม่มี secrets

Regression suite เดิมของ desktop และ Item Finder web ต้องยังผ่านทั้งหมด

## 16. ลำดับ implementation

1. เพิ่ม dependencies, configuration, database engine, models และ Alembic
2. เพิ่ม web session auth, bootstrap admin, login/logout/change-password
3. เพิ่ม authorization และ owner scope ครบทุก API/WebSocket
4. เพิ่ม admin user management
5. เพิ่ม pairing token และ encrypted Aztek session store
6. สร้าง Chrome Extension
7. เปลี่ยน Playwright web worker ให้ใช้ per-user storage state
8. เพิ่ม audit service และหน้า admin audit
9. เพิ่ม Docker/Render configuration และคู่มือ Supabase/Neon
10. รัน security/regression/e2e verification

## 17. เกณฑ์เสร็จ

- เปิดเว็บแล้วต้อง login ก่อนใช้ Item Finder
- Admin สร้าง, ปิดบัญชี และ reset password ได้
- Member เชื่อม session Aztek ผ่าน Extension ได้โดยไม่ส่ง password
- Item Finder ใช้ session Aztek ของผู้สั่งงาน
- ผู้ใช้เข้าถึง workspace/job/result/export ของคนอื่นไม่ได้
- Session Aztek ถูกเข้ารหัสในฐานข้อมูล
- Admin ตรวจ audit log ได้และ log ไม่มี secrets
- Local SQLite และ production PostgreSQL ทำงานผ่าน configuration เดียวกัน
- ชุดทดสอบเดิมและชุด auth ใหม่ผ่านทั้งหมด
- `.cabal_chrome_profile/`, local database, `.env`, encryption keys และ credentials ไม่ถูก commit
