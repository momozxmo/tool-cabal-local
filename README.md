# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.15](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.15/All.for.Cabal.Web.Setup-0.1.15.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.15/All.for.Cabal.Web.Setup-0.1.15.exe.sha256)
- [ดูหน้า Release v0.1.15](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.15)

SHA-256:

```text
F7CDA4753E844972570570E13481AC5FAF29E0B9262D0544CE190F1828577308
```

## สิ่งที่ปรับใน v0.1.15

- อ่านชื่อ Product จากช่อง `Product Name` โดยไม่หลุดไปใช้ชื่อฟิลด์ `Wallet Point`
- อ่านราคา Wallet Point จากไฟล์แผน พร้อมให้แก้ราคาเดิมหรือเพิ่มราคาเองในหน้า Product
- เพิ่มปุ่มเลือกทั้งหมดและล้างที่เลือกทั้งหมดในหน้าต่างเลือก Sheet ของ Product
- เปลี่ยนช่อง Bundle ID ให้ไม่มีลูกศรเพิ่ม/ลด และรองรับ Bundle popover รูปแบบปัจจุบันของ Aztek

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

> ตัวติดตั้ง v0.1.15 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
