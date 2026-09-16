# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.35](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.35/All.for.Cabal.Web.Setup-0.1.35.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.35/All.for.Cabal.Web.Setup-0.1.35.exe.sha256)
- [ดูหน้า Release v0.1.35](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.35)

SHA-256:

```text
7F305FB0FC0CA3505BB631DE6143A964356312F5EC8935DDE6DFB962DB0C62F4
```

## v0.1.35 — รองรับ Excel 64 MB และตรวจรุ่นเซิร์ฟเวอร์

- เพิ่มเพดานนำเข้า Excel จาก 32 MB เป็น 64 MB รองรับไฟล์ Monthly Plan ขนาด 34.17 MB
- แจ้งเตือนเมื่อ Launcher พบเซิร์ฟเวอร์คนละรุ่นเปิดค้าง ป้องกันการเปิดหน้าเว็บผิดรุ่นและปุ่มอัปเดตหาย
- คง Interface และเครื่องมือทั้งหมดจาก v0.1.34
- ปรับ Desktop/Mobile ลดฟอร์มและตารางล้นจอ พร้อมพื้นที่เลื่อนแนวนอนที่ใช้งานง่ายขึ้น
- เพิ่มการใช้งานด้วย Keyboard สำหรับข้ามไปพื้นที่ทำงาน สลับแท็บภาษา และปิดปฏิทิน
- แสดงผลครั้งล่าสุดของ Product ใกล้รายการที่เลือก และแยกประวัติ Bundle ออกจากคิวปัจจุบัน
- รักษาพฤติกรรม import, preview, queue และ create เดิม ไม่สร้างข้อมูลจริงระหว่างอัปเดต
- ผู้ใช้ v0.1.31 ขึ้นไปกด “อัปเดตโปรแกรม” → “ตรวจอัปเดต” → “อัปเดต”

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

> ตัวติดตั้ง v0.1.35 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
