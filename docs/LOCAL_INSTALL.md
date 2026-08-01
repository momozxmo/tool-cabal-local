# คู่มือติดตั้ง All for Cabal Web แบบ Local

## 1. ดาวน์โหลดและตรวจไฟล์

ดาวน์โหลดสองไฟล์จาก [Release v0.1.8](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.8):

- `All.for.Cabal.Web.Setup-0.1.8.exe`
- `All.for.Cabal.Web.Setup-0.1.8.exe.sha256`

เปิด PowerShell ในโฟลเดอร์ Downloads แล้วใช้คำสั่ง:

```powershell
Get-FileHash ".\All.for.Cabal.Web.Setup-0.1.8.exe" -Algorithm SHA256
Get-Content ".\All.for.Cabal.Web.Setup-0.1.8.exe.sha256"
```

ค่าที่ถูกต้องคือ:

```text
836070339B4731941D98C60C48D3CA943AB2A4DEA7219AE124BD2E06737ED517
```

ถ้าค่าไม่ตรง ห้ามเปิด Setup และให้ดาวน์โหลดไฟล์ใหม่

## 2. ติดตั้งและเปิดโปรแกรม

1. ดับเบิลคลิก `All.for.Cabal.Web.Setup-0.1.8.exe`
2. ติดตั้งตามขั้นตอนปกติ
3. เลือกสร้างไอคอน Desktop ได้ตามต้องการ
4. หน้าสุดท้ายปล่อยเครื่องหมาย `เปิด All for Cabal Web` ไว้ แล้วกด Finish

Controller จะเปิด Item Finder ที่ `http://127.0.0.1:8000` ให้อัตโนมัติ โดยไม่ถามชื่อผู้ใช้หรือรหัสผ่านของ All for Cabal

Controller มีสามปุ่ม:

- `เปิดหน้าเว็บ` เปิดแท็บใหม่โดยใช้ server เดิม
- `เริ่มใหม่` หยุดและเริ่ม local server ใหม่
- `ปิดโปรแกรม` หยุด server และปิด Controller

## 3. เชื่อม Aztek

เปิดหน้า `เชื่อม Aztek` แล้วทำตามขั้นตอน Bookmarklet บนหน้า Aztek ที่ล็อกอินอยู่แล้ว โปรแกรมจะไม่ถามหรือเก็บรหัสผ่าน Aztek

การเชื่อม Aztek, Preview และการส่งคำสั่งไป Aztek ต้องใช้อินเทอร์เน็ต

## 4. ข้อมูลและการอัปเดต

ข้อมูล Local อยู่ที่:

```text
%LOCALAPPDATA%\AllForCabalWeb
```

ปิด Controller ก่อนสำรองข้อมูล แล้วคัดลอกทั้งโฟลเดอร์นี้ เมื่อมีรุ่นใหม่ให้ปิด Controller และติดตั้ง Setup รุ่นใหม่ทับรุ่นเดิม

การถอนการติดตั้งจะลบเฉพาะไฟล์โปรแกรม ส่วนฐานข้อมูล, config และ backup จะยังอยู่ หากต้องการลบข้อมูลถาวร ให้สำรองข้อมูลก่อนแล้วลบโฟลเดอร์ข้างต้นด้วยตนเอง

## 5. การเปลี่ยนแปลงใน v0.1.8

- Fetch Category และ Currency ของหน้า Product จาก custom dropdown รุ่นปัจจุบันของ Aztek โดยไม่หยิบค่าช่องจำกัดการซื้อ
- เลือก Category และ Currency ตอนกรอก Product ด้วย server ID ที่ Fetch มาจาก Aztek
- ล้าง cache และ ID เก่าที่ไม่อยู่ในรายการล่าสุด แล้วจับคู่ข้อมูลใหม่อัตโนมัติ
- Category จากไฟล์ เช่น `Highlight` จับคู่กับรายการ Aztek เช่น `Main Shop - Highlight` ได้
- ถ้ายังไม่ได้เลือก Category หรือ Currency จะแจ้งภาษาไทยก่อนส่ง โดยไม่แสดง Pydantic validation error

## 6. สถานะการตรวจ v0.1.8

- Automated tests: `452 passed`
- ตรวจไฟล์ Setup ด้วยระบบตรวจ release artifact สำเร็จ
- SHA-256 จากไฟล์ Setup ตรงกับไฟล์ `.sha256`
- ขนาด Setup: `268,072,640` bytes (`255.65 MiB`)
- ซอร์สของการแก้ไข v0.1.8 อยู่ที่ commit `23cdd24`
- Setup ยังไม่มี digital signature
- ยังไม่ได้ตรวจบน clean VM ที่ตัดอินเทอร์เน็ตทั้งหมด
- ยังไม่ได้ทดสอบอัปเกรดข้ามหมายเลขเวอร์ชันด้วยการติดตั้งจริงในรอบนี้
- ไม่ได้กดสร้างข้อมูลจริงใน Aztek ระหว่างการตรวจรุ่นนี้
