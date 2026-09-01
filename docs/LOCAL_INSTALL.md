# คู่มือติดตั้ง All for Cabal Web แบบ Local

## 1. ดาวน์โหลดและตรวจไฟล์

ดาวน์โหลดสองไฟล์จาก [Release v0.1.27](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.27):

- `All.for.Cabal.Web.Setup-0.1.27.exe`
- `All.for.Cabal.Web.Setup-0.1.27.exe.sha256`

เปิด PowerShell ในโฟลเดอร์ Downloads แล้วใช้คำสั่ง:

```powershell
Get-FileHash ".\All.for.Cabal.Web.Setup-0.1.27.exe" -Algorithm SHA256
Get-Content ".\All.for.Cabal.Web.Setup-0.1.27.exe.sha256"
```

ค่าที่ถูกต้องคือ:

```text
BAD5AE9E8AEE530065D2FAA445FB4F0DE17B6CD9539884832629E09D031FBAA5
```

ถ้าค่าไม่ตรง ห้ามเปิด Setup และให้ดาวน์โหลดไฟล์ใหม่

## 2. ติดตั้งและเปิดโปรแกรม

1. ดับเบิลคลิก `All.for.Cabal.Web.Setup-0.1.27.exe`
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

## 5. การแก้ไขใน v0.1.27

- ปรับการกรอก Product ให้ตรงกับหน้า Aztek ปัจจุบัน ทั้ง Category, รูปภาพ, สวิตช์, วันเวลา, Limit และ Primary Bundle
- รอรายการ Category และ Bundle โหลดครบก่อนกรอก และไม่บันทึก cache ว่างเมื่อหน้า Aztek ยังโหลดไม่สำเร็จ
- Preview ตรวจจับและลองเชื่อมหน้าใหม่เมื่อ Playwright target หลุด พร้อมแจ้งชัดเจนเมื่อ Aztek ไม่มีช่อง Tags
- เพิ่ม regression tests ครอบคลุม Product form และการกู้คืนจาก target ที่หลุด

## 6. สถานะการตรวจ v0.1.27

- Automated tests: `1423 passed`
- Regression tests ครอบคลุม Product form ปัจจุบัน การรอ catalog และการกู้คืนจาก Playwright target ที่หลุด
- ตรวจไฟล์ Setup ด้วยระบบตรวจ release artifact สำเร็จ
- SHA-256 จากไฟล์ Setup ตรงกับไฟล์ `.sha256`
- ขนาด Setup: `268,558,116` bytes (`256.12 MiB`)
- Setup สร้างจาก source snapshot `99b7051`
- Setup ยังไม่มี digital signature
- ยังไม่ได้ตรวจบน clean VM ที่ตัดอินเทอร์เน็ตทั้งหมด
- ติดตั้งทับรุ่นเดิมและตรวจ health ของโปรแกรมที่ติดตั้งจริงสำเร็จ
- ไม่ได้กดสร้างข้อมูลจริงใน Aztek ระหว่างการตรวจรุ่นนี้
