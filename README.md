# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.4](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.4/All.for.Cabal.Web.Setup-0.1.4.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.4/All.for.Cabal.Web.Setup-0.1.4.exe.sha256)
- [ดูหน้า Release v0.1.4](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.4)

SHA-256:

```text
973134C049BE14B933B91F4431412C5FB48E2DDE5DDC5B749F1B6FF1B9672DAB
```

## สิ่งที่ปรับใน v0.1.4

- หน้า Event จัดตำแหน่งฟอร์มให้ใกล้เคียงหน้า Aztek จริง โดยไม่เพิ่มช่องที่ไม่ได้ใช้งาน
- Event ที่มีชุดรางวัลเดียวจะนำชื่อ Event ไปกรอกเป็นชื่อชุดรางวัลให้อัตโนมัติ
- เวลารับรางวัลของ Event แสดงวันที่กับเวลาโดยใช้ช่องว่างแทนตัว `T`
- Item Code กำหนดจำนวนการใช้งานต่อ 1 User ของแต่ละชุดรางวัลให้เท่ากับจำนวน Code ของชุดนั้น
- หาก Item Code มีหลายชุดรางวัล ผลรวมจำนวนของทุกชุดจะเท่ากับจำนวน Item Code ทั้งหมด

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

> ตัวติดตั้ง v0.1.4 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
