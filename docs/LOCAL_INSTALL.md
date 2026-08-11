# คู่มือติดตั้ง All for Cabal Web แบบ Local

## 1. ดาวน์โหลดและตรวจไฟล์

ดาวน์โหลดสองไฟล์จาก [Release v0.1.17](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.17):

- `All.for.Cabal.Web.Setup-0.1.17.exe`
- `All.for.Cabal.Web.Setup-0.1.17.exe.sha256`

เปิด PowerShell ในโฟลเดอร์ Downloads แล้วใช้คำสั่ง:

```powershell
Get-FileHash ".\All.for.Cabal.Web.Setup-0.1.17.exe" -Algorithm SHA256
Get-Content ".\All.for.Cabal.Web.Setup-0.1.17.exe.sha256"
```

ค่าที่ถูกต้องคือ:

```text
AF25B81495A213981F2A43854FBA19A992B41AF5CC92E2676560AAB20661FCFA
```

ถ้าค่าไม่ตรง ห้ามเปิด Setup และให้ดาวน์โหลดไฟล์ใหม่

## 2. ติดตั้งและเปิดโปรแกรม

1. ดับเบิลคลิก `All.for.Cabal.Web.Setup-0.1.17.exe`
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

## 5. การเปลี่ยนแปลงใน v0.1.17

- Sheet picker หน้า Item Finder, Product, Event และ Item Code แสดงและค้นหาชื่อแท็บ Excel จริงเท่านั้น
- Product รองรับ Bundle 1-20 อันโดยตรง สามารถกรอกเอง เพิ่ม แก้ไข ลบ และเลือก Primary Bundle ได้
- Queue รุ่นเก่าและ Bundle handoff ถูกปรับเป็นรายการหลาย Bundle โดยรักษาลำดับและไม่เพิ่ม ID ซ้ำ
- Runner ตรวจรายการ Bundle จำนวนที่เลือก และ Primary ก่อนอนุญาตให้สร้าง Product
- หน้า Event ไฮไลต์คำเตือนที่ต้องตรวจสอบให้เห็นชัดขึ้น

## 6. สถานะการตรวจ v0.1.17

- Automated tests: `569 passed`
- Product และ Sheet picker regression tests: `112 passed`
- ตรวจไฟล์ Setup ด้วยระบบตรวจ release artifact สำเร็จ
- SHA-256 จากไฟล์ Setup ตรงกับไฟล์ `.sha256`
- ขนาด Setup: `268,129,331` bytes (`255.71 MiB`)
- Setup สร้างจาก source snapshot `86b4730`
- Setup ยังไม่มี digital signature
- ยังไม่ได้ตรวจบน clean VM ที่ตัดอินเทอร์เน็ตทั้งหมด
- ยังไม่ได้ทดสอบอัปเกรดข้ามหมายเลขเวอร์ชันด้วยการติดตั้งจริงในรอบนี้
- ไม่ได้กดสร้างข้อมูลจริงใน Aztek ระหว่างการตรวจรุ่นนี้
