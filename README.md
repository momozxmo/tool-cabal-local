# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.19](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.19/All.for.Cabal.Web.Setup-0.1.19.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.19/All.for.Cabal.Web.Setup-0.1.19.exe.sha256)
- [ดูหน้า Release v0.1.19](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.19)

SHA-256:

```text
83B8D9C4C72F2BD76F84BA82D1F9D7D64D771048A7550AC7B35E5A5B08E9C8A5
```

## สิ่งที่ปรับใน v0.1.19

- เพิ่มข้อความแจ้งสถานะที่เข้าใจง่ายใน Item Finder, Bundle, Item Code, Event และ Product ทั้งระหว่างทำงาน สำเร็จ คำเตือน และข้อผิดพลาด
- ข้อความผิดพลาดระบุรายการหรือช่องที่ต้องแก้ พร้อมแนวทางดำเนินการต่อ โดยคงรายการที่ยังสร้างไม่สำเร็จไว้ในคิว
- การสร้าง Item Code ทั้งคิวจะข้ามรายการที่ข้อมูลไม่ครบและทำรายการที่พร้อมต่อได้ โดยไม่ทำให้ทั้งคิวหยุดทันที
- เพิ่มการตรวจสอบข้อมูล คำขอ และสิทธิ์ของงาน Local พร้อมปรับการจัดการฐานข้อมูลและการเชื่อม Aztek ให้รัดกุมขึ้น
- รวมการซิงก์เกม/เซิร์ฟเวอร์ระหว่างทุกหน้า และรองรับหน้าต่างยืนยันการสร้างของ Aztek

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

> ตัวติดตั้ง v0.1.19 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
