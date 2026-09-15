# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.33](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.33/All.for.Cabal.Web.Setup-0.1.33.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.33/All.for.Cabal.Web.Setup-0.1.33.exe.sha256)
- [ดูหน้า Release v0.1.33](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.33)

SHA-256:

```text
1C8912D63A70854D3255239D3ADBA370B89AC86B95BF750C698046D4A19E417A
```

## v0.1.33 — Import Bundle จาก Excel และก็อปวาง

- ดาวน์โหลด Template แล้วใส่ Item ID บน Aztek ที่มีอยู่แล้ว
- ก็อปเซลล์จาก Excel มาวาง หรือ Import ไฟล์และเลือก Sheet ได้
- พรีวิวก่อนเพิ่มเข้าคิวเดิม รองรับ FIXED / CHOICE / RANDOM
- ระบุจำนวน, Rarity, เรทสุ่ม และ Currency ได้ โดย RANDOM ตรวจเรทรวม 100%
- Import เตรียมคิวเท่านั้น ไม่สร้างข้อมูลจริงบน Aztek อัตโนมัติ
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

> ตัวติดตั้ง v0.1.33 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
