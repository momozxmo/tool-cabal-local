# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.14](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.14/All.for.Cabal.Web.Setup-0.1.14.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.14/All.for.Cabal.Web.Setup-0.1.14.exe.sha256)
- [ดูหน้า Release v0.1.14](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.14)

SHA-256:

```text
A562E3B3C41DC24C59EC26442ABFC7CE0DF259490561B879D41833216100B04B
```

## สิ่งที่ปรับใน v0.1.14

- แก้ Bundle ให้กรอก Tier/จำนวน/อัตราสุ่มของแต่ละไอเทมได้ตรงชุด และไม่บันทึกเมื่อข้อมูลจำเป็นยังไม่ครบ
- ปรับ Item Finder ให้เก็บคำอธิบาย ลำดับ และผลของแต่ละ Product group ได้ครบ รวมถึงทางส่งต่อเพื่อรวมหลาย Bundle
- ปรับ Product reset, คิวสร้าง Item Code และการตรวจผลบันทึก ให้รายการที่ล้มเหลวยังคงอยู่สำหรับลองใหม่

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

> ตัวติดตั้ง v0.1.14 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
