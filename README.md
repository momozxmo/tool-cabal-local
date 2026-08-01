# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.7](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.7/All.for.Cabal.Web.Setup-0.1.7.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.7/All.for.Cabal.Web.Setup-0.1.7.exe.sha256)
- [ดูหน้า Release v0.1.7](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.7)

SHA-256:

```text
65DE86B6C89F5963EE78BB219B35367780AFEF3ADE02F38AA9703B92BCB13897
```

## สิ่งที่ปรับใน v0.1.7

- อ่านไฟล์ Reward PVE2 ที่มีแถวชื่อแพ็กเกจใต้หัวตารางได้ และตั้งชื่อกลุ่มจากอันดับกับ `Platinum Wing`
- รักษาลำดับไอเทมตอนส่งผลค้นหาและรายการที่หาไม่เจอเข้าคิว Bundle
- ไอเทมชื่อซ้ำในหลาย Bundle ใช้ค่า `Amt` ของแต่ละรายการได้ถูกต้อง
- ช่องจำนวนใน Bundle พิมพ์เลขหลายหลักได้ตามปกติ
- ผลและเลข Bundle ที่สร้างล่าสุดยังอยู่เมื่อสลับหน้าแล้วกลับมา
- ปฏิทินในหน้าฟอร์มไม่ถูกขอบการ์ดตัด

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

> ตัวติดตั้ง v0.1.7 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
