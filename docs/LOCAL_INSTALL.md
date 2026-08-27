# คู่มือติดตั้ง All for Cabal Web แบบ Local

## 1. ดาวน์โหลดและตรวจไฟล์

ดาวน์โหลดสองไฟล์จาก [Release v0.1.23](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.23):

- `All.for.Cabal.Web.Setup-0.1.23.exe`
- `All.for.Cabal.Web.Setup-0.1.23.exe.sha256`

เปิด PowerShell ในโฟลเดอร์ Downloads แล้วใช้คำสั่ง:

```powershell
Get-FileHash ".\All.for.Cabal.Web.Setup-0.1.23.exe" -Algorithm SHA256
Get-Content ".\All.for.Cabal.Web.Setup-0.1.23.exe.sha256"
```

ค่าที่ถูกต้องคือ:

```text
9AE6032505AA6CEBF818EA4964004E2F96AB7B3C7B207D45B87F12276B9D43B2
```

ถ้าค่าไม่ตรง ห้ามเปิด Setup และให้ดาวน์โหลดไฟล์ใหม่

## 2. ติดตั้งและเปิดโปรแกรม

1. ดับเบิลคลิก `All.for.Cabal.Web.Setup-0.1.23.exe`
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

## 5. การแก้ไขใน v0.1.23

- เพิ่มงานนำเข้า `Mastercode WR` จาก Sheet จริง พร้อมเลือก Sheet และ Preview ก่อนส่งเข้าคิว Item Code
- Preview แสดงลำดับ Code รายวัน, Mastercode, Bundle, Usage Limit และช่วงเวลาเต็มวัน
- บังคับ `Mastercode WR` ให้ใช้ Fix Codes หนึ่ง Code พร้อมตรวจข้อมูลบังคับก่อนสร้าง
- แก้หน้า Account และการอ่าน Session พร้อมกันไม่ให้ชนกันจนเกิด `database is locked`

## 6. สถานะการตรวจ v0.1.23

- Automated tests: `1407 passed`
- Regression tests ครอบคลุมการนำเข้า/Preview `Mastercode WR`, Fix Codes หนึ่ง Code และการอ่าน Session แบบไม่ล็อกฐานข้อมูล
- ตรวจไฟล์ Setup ด้วยระบบตรวจ release artifact สำเร็จ
- SHA-256 จากไฟล์ Setup ตรงกับไฟล์ `.sha256`
- ขนาด Setup: `268,161,194` bytes (`255.74 MiB`)
- Setup สร้างจาก source snapshot `79c1633`
- Setup ยังไม่มี digital signature
- ยังไม่ได้ตรวจบน clean VM ที่ตัดอินเทอร์เน็ตทั้งหมด
- ติดตั้งทับรุ่นเดิมและตรวจ health ของโปรแกรมที่ติดตั้งจริงสำเร็จ
- ไม่ได้กดสร้างข้อมูลจริงใน Aztek ระหว่างการตรวจรุ่นนี้
