# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.10](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.10/All.for.Cabal.Web.Setup-0.1.10.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.10/All.for.Cabal.Web.Setup-0.1.10.exe.sha256)
- [ดูหน้า Release v0.1.10](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.10)

SHA-256:

```text
1944DA93751A8D11EA87E4A113493B955138A3B2D5BB970FDD560F44F79AB672
```

## สิ่งที่ปรับใน v0.1.10

- ส่งข้อมูลจาก Bundle มาหน้า Item Code ครบทั้งชื่อไทย/อังกฤษ ชุดรางวัล และ Bundle ID ของทุกชุด
- รายการใหม่ใช้วันปัจจุบันเวลา `00:00:00` ตามเวลาไทย
- เปิด `จำกัดจำนวน` เฉพาะเมื่อข้อมูล Import มีจำนวนที่เป็นบวก หากไม่มีจำนวนจะคงเป็นแบบไม่จำกัด
- ส่งค่า `จำนวนครั้งที่สามารถใช้งานได้` และ `จำนวนคงเหลือ` ไปยังฟอร์ม Aztek เมื่อเปิดจำกัดจำนวน

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

> ตัวติดตั้ง v0.1.10 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
