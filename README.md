# All for Cabal Web — Local

เวอร์ชันติดตั้งสำหรับใช้งานในเครื่องของสมาชิกทีมบน Windows 10/11 x64
ผู้ใช้ไม่ต้องติดตั้ง Python, Docker หรือพิมพ์คำสั่งเพื่อเปิดโปรแกรม

## ดาวน์โหลด

- [ดาวน์โหลด Setup v0.1.21](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.21/All.for.Cabal.Web.Setup-0.1.21.exe)
- [ดาวน์โหลดไฟล์ SHA-256](https://github.com/momozxmo/tool-cabal-local/releases/download/v0.1.21/All.for.Cabal.Web.Setup-0.1.21.exe.sha256)
- [ดูหน้า Release v0.1.21](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.21)

SHA-256:

```text
B8664992AC5BC3AD6DFFDF8BA3C275E40D3A8CECC2DA42553DA4D612D4AE2F66
```

## สิ่งที่แก้ใน v0.1.21

- แก้การเชื่อม Aztek Local ที่แจ้งว่า `ข้อมูล session ที่จับมาไม่สมบูรณ์ — session เดิมยังอยู่` ทั้งที่เปิดหน้า Aztek dashboard สำเร็จแล้ว
- กรอง cookie และ localStorage ชั่วคราวจากผู้ให้บริการล็อกอินภายนอกออกจาก session ที่โปรแกรมจับ โดยเก็บเฉพาะข้อมูลของ Aztek และ SSO ที่อนุญาต
- คงการตรวจข้อมูล pairing จากภายนอกแบบเข้มงวด และใช้ Aztek v2 ที่ `aztek-tools-v2.combo-interactive.com/combo` ตามเดิม

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

> ตัวติดตั้ง v0.1.21 ยังไม่มี digital signature Windows อาจแสดง `Unknown publisher`
> หรือคำเตือน SmartScreen กรุณาตรวจ SHA-256 ก่อนเปิดไฟล์
