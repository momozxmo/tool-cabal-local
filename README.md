# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.18](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.18/All.for.Cabal.Web.Setup-0.1.18.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.18/All.for.Cabal.Web.Setup-0.1.18.exe.sha256)
- [ดูหน้า Release v0.1.18](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.18)

SHA-256:

```text
EB2A39A47DC458261AA2E6CEC54FA2B0D8593E4D017A79B2B900BC9C6A5822A9
```

## สิ่งที่ปรับใน v0.1.18

- ตัวเลือกเกม/เซิร์ฟเวอร์ซิงก์ทันทีระหว่าง Item Finder, Bundle, Item Code, Event และ Product ที่เปิดอยู่
- การโหลด Product workspace จะส่งเกม/เซิร์ฟเวอร์ที่กู้คืนไปยังหน้าอื่นด้วย
- Runner ของ Bundle, Item Code, Event และ Product กด `ยืนยัน` ในหน้าต่างยืนยันการสร้างก่อนรอผลบันทึก
- หน้า Aztek แบบเดิมที่สร้างทันทีโดยไม่มีหน้าต่างยืนยันยังใช้งานได้

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

> ตัวติดตั้ง v0.1.18 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
