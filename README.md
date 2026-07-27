# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.2](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.2/All.for.Cabal.Web.Setup-0.1.2.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.2/All.for.Cabal.Web.Setup-0.1.2.exe.sha256)
- [ดูหน้า Release](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.2)

SHA-256:

```text
BD82E06999079F502601D51A13CFA2864954F5422693DD26ABDEE638A24FD9F3
```

## คุณสมบัติของเวอร์ชัน Local

- เปิด Item Finder ในเว็บ local ให้อัตโนมัติ
- ไม่มีหน้าล็อกอินของ All for Cabal
- server ฟังเฉพาะ `127.0.0.1:8000`
- เก็บฐานข้อมูลและ config ไว้ที่ `%LOCALAPPDATA%\AllForCabalWeb`
- ติดตั้งทับหรือถอนโปรแกรมแล้วข้อมูล Local ยังอยู่
- รวม Chromium ที่ระบบอัตโนมัติต้องใช้ไว้ใน Setup แล้ว
- v0.1.2 อ่านบล็อกรางวัลถัดไปที่ไม่มีหัวตาราง Item Kind ซ้ำ และส่งต่อ Item Code ได้ครบ
- v0.1.1 แก้อาการ Controller ค้างที่ข้อความกำลังปิดโปรแกรม

อ่านขั้นตอนทั้งหมดได้ที่ [คู่มือติดตั้ง](docs/LOCAL_INSTALL.md)

> ตัวติดตั้ง v0.1.2 ยังไม่มี digital signature Windows อาจแสดง
> `Unknown publisher` หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
