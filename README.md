# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.23](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.23/All.for.Cabal.Web.Setup-0.1.23.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.23/All.for.Cabal.Web.Setup-0.1.23.exe.sha256)
- [ดูหน้า Release v0.1.23](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.23)

SHA-256:

```text
9AE6032505AA6CEBF818EA4964004E2F96AB7B3C7B207D45B87F12276B9D43B2
```

## สิ่งที่แก้ใน v0.1.23

- เพิ่มงานนำเข้า `Mastercode WR` จาก Sheet จริง พร้อมเลือก Sheet และ Preview ก่อนส่งเข้าคิว Item Code
- Preview แสดงลำดับ Code รายวัน, Mastercode, Bundle, Usage Limit และช่วงเวลาเต็มวัน
- บังคับ `Mastercode WR` ให้ใช้ Fix Codes หนึ่ง Code พร้อมตรวจข้อมูลบังคับก่อนสร้าง
- แก้หน้า Account และการอ่าน Session พร้อมกันไม่ให้ชนกันจนเกิด `database is locked`

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

> ตัวติดตั้ง v0.1.23 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
