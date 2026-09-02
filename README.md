# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.28](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.28/All.for.Cabal.Web.Setup-0.1.28.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.28/All.for.Cabal.Web.Setup-0.1.28.exe.sha256)
- [ดูหน้า Release v0.1.28](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.28)

SHA-256:

```text
4753D412B754E7C009ADD273A150A58C6B4714BF31DDD46D7E4A798AC2F1E3AB
```

## สิ่งที่แก้ใน v0.1.28

- เพิ่มปุ่ม Undo ไอเทมล่าสุดที่ลบในหน้า Bundle โดยคืนข้อมูลและตำแหน่งเดิม
- ปรับหน้า Product: เอา Tags ออก, กำหนดวินาทีสิ้นสุดเป็น 59 และเพิ่มช่องค้นหา Currency
- ชื่อ Thumbnail เปลี่ยนตามไฟล์ล่าสุดและซิงก์ทันทีระหว่างแท็บ Product ที่เปิดอยู่ โดยไฟล์ยังคงอยู่ในแท็บที่เลือก
- เอาปุ่ม Import Template สีน้ำเงินออกจาก Item Finder และเพิ่ม regression tests ครอบคลุมการทำงานใหม่

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

> ตัวติดตั้ง v0.1.28 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
