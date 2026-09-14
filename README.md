# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.32](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.32/All.for.Cabal.Web.Setup-0.1.32.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.32/All.for.Cabal.Web.Setup-0.1.32.exe.sha256)
- [ดูหน้า Release v0.1.32](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.32)

SHA-256:

```text
2317A4B5F952981CC8B7484D4A2EDBAC770057625F4EE317A5D285F07A6C7043
```

## v0.1.32 — ทดลองอัปเดตผ่านโปรแกรม

รุ่นนี้ใช้ฟังก์ชันเดิมจาก v0.1.31 และเปลี่ยนหมายเลข build เพื่อทดลองอัปเดตจริง

- ผู้ใช้ v0.1.31 กด “อัปเดตโปรแกรม” → “ตรวจอัปเดต” → “อัปเดต”
- โปรแกรมดาวน์โหลด ตรวจไฟล์ ติดตั้ง และเปิดกลับเป็น v0.1.32
- ตรวจเลขรุ่นใน popup และตรวจว่าร่าง/คิวเดิมยังอยู่

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
- ตั้งแต่ v0.1.31 สามารถตรวจและติดตั้งเวอร์ชันถัดไปจากในโปรแกรมได้

อ่านขั้นตอนทั้งหมดได้ที่ [คู่มือติดตั้ง](docs/LOCAL_INSTALL.md)

> ตัวติดตั้ง v0.1.32 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
