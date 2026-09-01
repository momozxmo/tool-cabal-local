# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.27](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.27/All.for.Cabal.Web.Setup-0.1.27.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.27/All.for.Cabal.Web.Setup-0.1.27.exe.sha256)
- [ดูหน้า Release v0.1.27](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.27)

SHA-256:

```text
BAD5AE9E8AEE530065D2FAA445FB4F0DE17B6CD9539884832629E09D031FBAA5
```

## สิ่งที่แก้ใน v0.1.27

- ปรับการกรอก Product ให้ตรงกับหน้า Aztek ปัจจุบัน ทั้ง Category, รูปภาพ, สวิตช์, วันเวลา, Limit และ Primary Bundle
- รอรายการ Category และ Bundle โหลดครบก่อนกรอก และไม่บันทึก cache ว่างเมื่อหน้า Aztek ยังโหลดไม่สำเร็จ
- Preview ตรวจจับและลองเชื่อมหน้าใหม่เมื่อ Playwright target หลุด พร้อมแจ้งชัดเจนเมื่อ Aztek ไม่มีช่อง Tags
- เพิ่ม regression tests ครอบคลุม Product form และการกู้คืนจาก target ที่หลุด

## คุณสมบัติของเวอร์ชัน Local

- เปิด Item Finder ในเว็บ local ให้อัตโนมัติ
- ไม่มีหน้าล็อกอินของ All for Cabal
- server ฟังเฉพาะ `127.0.0.1:8000`
- เก็บฐานข้อมูลและ config ไว้ที่ `%LOCALAPPDATA%\AllForCabalWeb`
- ติดตั้งทับหรือถอนโปรแกรมแล้วข้อมูล Local ยังอยู่
- รวม Chromium ที่ระบบอัตโนมัติต้องใช้ไว้ใน Setup แล้ว
- เชื่อม Aztek แบบ Local ผ่าน Chromium ที่โปรแกรมเปิดให้ โดยไม่เก็บรหัสผ่าน IPA/Aztek
- รองรับปุ่ม `สร้าง Bundle` ของ Aztek v2 และชื่อปุ่มแบบเดิม
- อ่านบล็อกรางวัลต่อเนื่องที่ไม่มีหัวตาราง Item Kind ซ้ำ และส่ง Item Code หลายรายการได้ครบ
- Controller ปิด server และตัวโปรแกรมได้โดยไม่ค้างอยู่ที่ข้อความกำลังปิดโปรแกรม

อ่านขั้นตอนทั้งหมดได้ที่ [คู่มือติดตั้ง](docs/LOCAL_INSTALL.md)

> ตัวติดตั้ง v0.1.27 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
