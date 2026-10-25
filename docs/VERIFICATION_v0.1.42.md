# v0.1.42 — หลักฐานตรวจรุ่น Bundle/Recheck

## ขอบเขต

แก้การจับคู่รายการซ้ำโดยใช้ Rarity/เรทที่ตรวจได้ แยกการอ่านไม่ครบจากความต่างที่พิสูจน์ได้ และเพิ่มตัวกรองแถวที่มีปัญหาทั้งผลล่าสุด/ประวัติ
ไม่เปลี่ยนผลตรวจจริง ไม่ข้ามการยืนยันส่งต่อ ไม่รวม WR ที่พักไว้หรือ New Item และไม่มี live Aztek operation ระหว่างตรวจรับ

Source snapshot: `d6a123c0d5df82ca72e5f4501d5ac1bffd550ac9`
WR source/tests ในรุ่นนี้เท่ากับฐานก่อนแก้รอบนี้ งานที่พักไว้ยังเก็บแยก ไม่ได้ลบทิ้ง

## การตรวจรับ

- Exact release-only full: **2,777 passed, 1 warning in 7386.46s**
- wrapper/raw/signed exit0; JUnit aggregate/actual unique2777, failures/errors/skips0; evidence_errors ว่าง
- Warning เดิมเกี่ยวกับ process-local development secrets ในเทสต์ ไม่ใช่ warning-free
- Freeze165 ตรงหลัง full/build/smoke; original source/user hashes คงเดิม
- Build0.1.42 exit0 โดยใช้ source ที่ผ่าน full แล้ว ไม่อัปเกรด dependencies
- Privacy/tree/checksum ผ่าน; embedded code12modules รวม Recheck/WR baseline/updater ตรง compiled tested source และ static19files SHA ตรง
- Runtime และ ProductVersion หลัง trim เป็น0.1.42; ProductVersion มี space padding และไม่อ้าง numeric FileVersion
- Isolated smoke2 exit0: health/Local session/bootstrap/ทุกหน้าเครื่องมือ/Recheck UI/นำเข้าเรท0/ประวัติว่างผ่าน
- ยืนยัน bundled headless Chromium ใช้ profile ทดสอบแยกจริงก่อนปิดเฉพาะ ownedPID/path/starttime; หลังจบไม่เหลือ candidateprocess และ port8000ว่าง
- Smoke1 เก็บเป็น wrapperexit1 เพราะตรวจ HTTP แล้วปิด launcher ก่อนยืนยัน browser/profile; ไม่แปลงเป็นผ่าน Smoke2 เพิ่ม condition wait โดยไม่แก้ production sourceหรือ rebuild
- ไม่มีการติดตั้งทับหรือปิดแอปผู้ใช้ และไม่มี Aztek request/create

## ไฟล์แจก

Setup: `All.for.Cabal.Web.Setup-0.1.42.exe` — **279167040 bytes**

SHA-256:
```text
DFA19F814791C221A0BBCBC1C523A663B6EB7C5B47F3E446BE961A7D741D0343
```

Sidecar102bytes SHA-256: `5E78780D4452D3B038234568E24762B84CEFF38C3D6F69EC7D55866ADDEB8F50`
ข้อความ checksum อ้างชื่อไฟล์ build ที่มีช่องว่าง; GitHub เปลี่ยนชื่อ asset เป็นจุดได้ ให้เทียบ digest กับไฟล์ที่ดาวน์โหลดจริง

## ข้อจำกัด

Setup ยัง unsigned; clean-VM installation และ actual user update/reopen/ร่างและคิวเดิมยังไม่ยืนยัน
การทดสอบ local/synthetic ไม่รับรองทุก live DOM/state/navigation variant และไม่ให้สิทธิ์สร้างข้อมูลจริงเพิ่ม
