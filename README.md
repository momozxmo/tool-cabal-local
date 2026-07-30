# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.5](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.5/All.for.Cabal.Web.Setup-0.1.5.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.5/All.for.Cabal.Web.Setup-0.1.5.exe.sha256)
- [ดูหน้า Release v0.1.5](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.5)

SHA-256:

```text
370084628DDBA120CA18CFD4DDC3BA86FDC5529D4A321AF5F3A57F332CF52E2F
```

## สิ่งที่ปรับใน v0.1.5

- หน้า Item Code จัดข้อมูลทั่วไป/ตั้งค่าไว้ฝั่งซ้ายและชุดรางวัลไว้ฝั่งขวาให้ใกล้เคียงหน้า Aztek
- เมื่อหน้าจอแคบ Item Code จะเรียงข้อมูลทั่วไป → ตั้งค่า → ชุดรางวัลให้อัตโนมัติ
- Item Code และ Event ที่มีหลายชุดรางวัลใช้แท็บแบบ `1 ชุดที่ 1`, `2 ชุดที่ 2`
- แสดงฟอร์มทีละชุดรางวัล แต่ยังเก็บและส่งข้อมูลของทุกชุดครบตามลำดับเดิม
- เมื่อเพิ่มชุดใหม่จะเปิดแท็บนั้นทันที; เมื่อลบหรือเปลี่ยนรายการในคิวจะเลือกแท็บที่ถูกต้องให้อัตโนมัติ

## คุณสมบัติของเวอร์ชัน Local

- เปิด Item Finder ในเว็บ local ให้อัตโนมัติ
- ไม่มีหน้าล็อกอินของ All for Cabal
- server ฟังเฉพาะ `127.0.0.1:8000`
- เก็บฐานข้อมูลและ config ไว้ที่ `%LOCALAPPDATA%\AllForCabalWeb`
- ติดตั้งทับหรือถอนโปรแกรมแล้วข้อมูล Local ยังอยู่
- รวม Chromium ที่ระบบอัตโนมัติต้องใช้ไว้ใน Setup แล้ว
- รองรับปุ่ม `สร้าง Bundle` ของ Aztek v2 และชื่อปุ่มแบบเดิม
- อ่านบล็อกรางวัลต่อเนื่องที่ไม่มีหัวตาราง Item Kind ซ้ำ และส่ง Item Code หลายรายการได้ครบ
- Controller ปิด server และตัวโปรแกรมได้โดยไม่ค้างอยู่ที่ข้อความกำลังปิดโปรแกรม

อ่านขั้นตอนทั้งหมดได้ที่ [คู่มือติดตั้ง](docs/LOCAL_INSTALL.md)

> ตัวติดตั้ง v0.1.5 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
