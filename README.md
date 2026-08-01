# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.9](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.9/All.for.Cabal.Web.Setup-0.1.9.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.9/All.for.Cabal.Web.Setup-0.1.9.exe.sha256)
- [ดูหน้า Release v0.1.9](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.9)

SHA-256:

```text
9E2FBAAE49ABAE3437C71B8EB24E1BAED605A7E28BEE0C241BC3BB25B63A1E3B
```

## สิ่งที่ปรับใน v0.1.9

- จำกัดการอ่านข้อมูลไว้ที่บล็อก Product ปัจจุบัน ไม่ดึงข้อมูลจาก Product ก่อนหน้าหรือตารางไอเทมรอบข้าง
- อ่านชื่อ หมวดหมู่ วันจบ และข้อมูล Reset จากป้ายของ Product เท่านั้น
- ใช้ `Wallet Point` เป็นราคาและ Currency จากไฟล์ โดยไม่ตีความตัวเลขอื่นเป็นราคา
- อ่าน Reset Time จากข้อความ เช่น `เริ่มตั้งเวลา 00.01 น.` เป็น `00:01:00`
- ตั้งวันเริ่มรอบ Reset ย้อนหลังตามจำนวนวันของรอบ Reset

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

> ตัวติดตั้ง v0.1.9 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
