# All for Cabal Web v0.1.40 — ตรวจเองครบแล้ว สร้างทุกบันเดิลต่อเนื่อง

- เพิ่มปุ่ม “ตรวจเองครบแล้ว — สร้างทุกบันเดิลต่อเนื่อง” พร้อมยืนยันครั้งเดียวสำหรับคิวและเกมปัจจุบัน
- สร้างรายการถัดไปได้เมื่อยืนยันว่ารายการก่อนหน้าบันทึกสำเร็จและมี Bundle ID แม้ Recheck ไม่ผ่านครบ
- เก็บผล Recheck จริง ไม่เปลี่ยนเป็นผ่าน และไม่อนุมัติส่งผลที่ไม่ผ่านไป Event/Product ให้อัตโนมัติ
- ยังคงหยุดเมื่อกรอกไม่ครบ บันทึกไม่สำเร็จ ผลสร้างไม่แน่นอน หรือไม่มี ID; ป้องกันการส่งสร้างซ้ำตาม checkpoint
- ปุ่มสร้างเดิมยังหยุดตาม Recheck เหมือนเดิม; การยืนยันตรวจเองไม่ค้างเป็นโหมดถาวรหลังเปิดหน้าใหม่
- คง workspace/group identity หลังส่งสร้าง และแก้การส่งต่อ Document Reference จาก Finder

ผู้ใช้เป็นผู้เลือกอัปเดตเองผ่าน “อัปเดตโปรแกรม” → “ตรวจอัปเดต” → “อัปเดต” เมื่อพร้อม
การเผยแพร่ครั้งนี้ไม่ติดตั้งทับหรือปิดโปรแกรมเดิมให้ ร่าง/คิวอยู่ในเบราว์เซอร์เดิมตามที่อยู่ local เดิม

Full exact-source **2,113 passed, 1 warning in 3168.61s**; failures/errors/skips0,
raw/signed exit0, JUnitaggregate+actual2113, evidence_errors empty และ source freeze147ตรงครบ
Warning เดิมเกี่ยวกับ process-local development secrets ในเทสต์ ไม่อ้างว่าไม่มี warning

แพ็กเกจจริงผ่าน health รุ่น0.1.40, Local session/bootstrap, ทุกหน้าเครื่องมือ,
ปุ่มใหม่/opt-in, การนำเข้าเรต0 และ historyว่างด้วย runtimeทดสอบแยก โดยไม่สร้างข้อมูลจริงบน Aztek
Runtime/Setup version0.1.40, updatehelperมีครบ, staticSHAตรงsource, releaseprivacyและchecksumผ่าน

ไม่รวม Event/Product/Item Code migrations และ Product visibility guard ที่ยังพัฒนาแยกอยู่
Actual user install/reopen/ร่างและคิวยังต้องตรวจหลังผู้ใช้เลือกอัปเดตเอง
ยังไม่ทดสอบติดตั้งบน clean VM หรือสร้างจริงบน Aztek; Setupยังไม่มี digital signature

Source snapshot: `2ff80782182f0dfca87e2df83aa2cb01ba712a34`
Setup: `All.for.Cabal.Web.Setup-0.1.40.exe` — 279,146,982 bytes
SHA-256: `31ABC0280BC9D055142884369C6A4E243E6DBCBC89807B10C44FE82BB6DD28FF`
