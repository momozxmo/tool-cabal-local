# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.6](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.6/All.for.Cabal.Web.Setup-0.1.6.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.6/All.for.Cabal.Web.Setup-0.1.6.exe.sha256)
- [ดูหน้า Release v0.1.6](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.6)

SHA-256:

```text
76573ADB6AB6556340BD14BAC04E462BFCA1B155DD8943C93EAF3BCB4EC53D00
```

## สิ่งที่ปรับใน v0.1.6

- เพิ่มหน้า Product ตามตำแหน่งฟอร์มหลักของ Aztek พร้อมคิวหลายรายการและ layout สำหรับหน้าจอแคบ
- ใช้ข้อมูล Shop จากแผนที่ Import ใน Item Finder ต่อได้ทันที และยังเลือก Sheet ได้เมื่อพบหลายแท็บ
- Currency และ Category มาจากตัวเลือกที่ Fetch จาก Aztek เท่านั้น จับคู่แบบไม่ hardcode และกด Fetch ใหม่แยกกันได้
- มีโหมดกรอก Product เพื่อรีวิวโดยไม่ส่ง และโหมดสร้างจริงที่ต้องเลือก ตรวจข้อมูล และยืนยันอีกครั้ง
- เวลาเริ่มต้นเป็นวันปัจจุบันเวลา `00:00:00`; เวลาอื่นแสดงแบบ 24 ชั่วโมงโดยไม่มีตัว `T`

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

> ตัวติดตั้ง v0.1.6 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
