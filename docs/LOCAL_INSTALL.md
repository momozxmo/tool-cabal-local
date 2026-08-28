# คู่มือติดตั้ง All for Cabal Web แบบ Local

## 1. ดาวน์โหลดและตรวจไฟล์

ดาวน์โหลดสองไฟล์จาก [Release v0.1.24](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.24):

- `All.for.Cabal.Web.Setup-0.1.24.exe`
- `All.for.Cabal.Web.Setup-0.1.24.exe.sha256`

เปิด PowerShell ในโฟลเดอร์ Downloads แล้วใช้คำสั่ง:

```powershell
Get-FileHash ".\All.for.Cabal.Web.Setup-0.1.24.exe" -Algorithm SHA256
Get-Content ".\All.for.Cabal.Web.Setup-0.1.24.exe.sha256"
```

ค่าที่ถูกต้องคือ:

```text
B7E6585530F6DB70E9EAE97D4DA50CCBF14BC656CC9756139A181CE748BD0260
```

ถ้าค่าไม่ตรง ห้ามเปิด Setup และให้ดาวน์โหลดไฟล์ใหม่

## 2. ติดตั้งและเปิดโปรแกรม

1. ดับเบิลคลิก `All.for.Cabal.Web.Setup-0.1.24.exe`
2. ติดตั้งตามขั้นตอนปกติ
3. เลือกสร้างไอคอน Desktop ได้ตามต้องการ
4. หน้าสุดท้ายปล่อยเครื่องหมาย `เปิด All for Cabal Web` ไว้ แล้วกด Finish

Controller จะเปิด Item Finder ที่ `http://127.0.0.1:8000` ให้อัตโนมัติ โดยไม่ถามชื่อผู้ใช้หรือรหัสผ่านของ All for Cabal

Controller มีสามปุ่ม:

- `เปิดหน้าเว็บ` เปิดแท็บใหม่โดยใช้ server เดิม
- `เริ่มใหม่` หยุดและเริ่ม local server ใหม่
- `ปิดโปรแกรม` หยุด server และปิด Controller

## 3. เชื่อม Aztek

เปิดหน้า `เชื่อม Aztek` แล้วกด `เปิด Aztek และเชื่อม` โปรแกรมจะเปิด Chromium ให้ จากนั้นล็อกอิน IPA และ Aztek ด้วยตนเอง เมื่อเข้า Aztek สำเร็จโปรแกรมจะบันทึก Session สำหรับงานค้นหา Preview และสร้างข้อมูล โดยไม่ถามหรือเก็บรหัสผ่าน IPA/Aztek

หากเชื่อมไม่สำเร็จหรือหมดเวลา Session เดิมที่มีอยู่จะไม่ถูกลบทิ้ง สามารถกดเชื่อมใหม่ได้ภายหลัง

การเชื่อม Aztek, Preview และการส่งคำสั่งไป Aztek ต้องใช้อินเทอร์เน็ต

## 4. ข้อมูลและการอัปเดต

ข้อมูล Local อยู่ที่:

```text
%LOCALAPPDATA%\AllForCabalWeb
```

ปิด Controller ก่อนสำรองข้อมูล แล้วคัดลอกทั้งโฟลเดอร์นี้ เมื่อมีรุ่นใหม่ให้ปิด Controller และติดตั้ง Setup รุ่นใหม่ทับรุ่นเดิม

การถอนการติดตั้งจะลบเฉพาะไฟล์โปรแกรม ส่วนฐานข้อมูล, config และ backup จะยังอยู่ หากต้องการลบข้อมูลถาวร ให้สำรองข้อมูลก่อนแล้วลบโฟลเดอร์ข้างต้นด้วยตนเอง

## 5. การแก้ไขใน v0.1.24

- รองรับไฟล์ Excel สำหรับงาน Import ได้สูงสุด 32 MB พร้อมข้อความแจ้งเตือนภาษาไทยเมื่อไฟล์ใหญ่เกินกำหนด
- ปุ่ม `ส่งเข้าคิวสร้างบันเดิล` ส่งผลลัพธ์ทั้งหมดไปครบทุก Bundle แม้ไอเทมเดียวกันอยู่หลาย Bundle
- checkbox ใน Item Finder ยังคงใช้กรองเฉพาะหน้ารวม Bundle เพื่อรีวิว ไม่ตัดรายการออกจากปุ่มส่งทั้งคิว

## 6. สถานะการตรวจ v0.1.24

- Automated tests: `1413 passed`
- Regression tests ครอบคลุมเพดาน Import 32 MB, การส่งผลลัพธ์ทั้งหมดเข้าคิว Bundle และความเสถียรของ Pairing Session test
- ตรวจไฟล์ Setup ด้วยระบบตรวจ release artifact สำเร็จ
- SHA-256 จากไฟล์ Setup ตรงกับไฟล์ `.sha256`
- ขนาด Setup: `268,561,277` bytes (`256.12 MiB`)
- Setup สร้างจาก source snapshot `112a6c1`
- Setup ยังไม่มี digital signature
- ยังไม่ได้ตรวจบน clean VM ที่ตัดอินเทอร์เน็ตทั้งหมด
- ติดตั้งทับรุ่นเดิมและตรวจ health ของโปรแกรมที่ติดตั้งจริงสำเร็จ
- ไม่ได้กดสร้างข้อมูลจริงใน Aztek ระหว่างการตรวจรุ่นนี้
