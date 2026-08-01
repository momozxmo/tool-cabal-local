# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.8](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.8/All.for.Cabal.Web.Setup-0.1.8.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.8/All.for.Cabal.Web.Setup-0.1.8.exe.sha256)
- [ดูหน้า Release v0.1.8](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.8)

SHA-256:

```text
836070339B4731941D98C60C48D3CA943AB2A4DEA7219AE124BD2E06737ED517
```

## สิ่งที่ปรับใน v0.1.8

- Fetch Category และ Currency ของหน้า Product จาก custom dropdown รุ่นปัจจุบันของ Aztek โดยไม่หยิบค่าช่องจำกัดการซื้อ
- เลือก Category และ Currency ตอนกรอก Product ด้วย server ID ที่ Fetch มาจาก Aztek
- ล้าง cache และ ID เก่าที่ไม่อยู่ในรายการล่าสุด แล้วจับคู่ข้อมูลใหม่อัตโนมัติ
- Category จากไฟล์ เช่น `Highlight` จับคู่กับรายการ Aztek เช่น `Main Shop - Highlight` ได้
- ถ้ายังไม่ได้เลือก Category หรือ Currency จะแจ้งภาษาไทยก่อนส่ง โดยไม่แสดง Pydantic validation error

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

> ตัวติดตั้ง v0.1.8 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
