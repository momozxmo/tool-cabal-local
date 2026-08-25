# คู่มือติดตั้ง All for Cabal Web แบบ Local

## 1. ดาวน์โหลดและตรวจไฟล์

ดาวน์โหลดสองไฟล์จาก [Release v0.1.21](https://github.com/momozxmo/tool-cabal-local/releases/tag/v0.1.21):

- `All.for.Cabal.Web.Setup-0.1.21.exe`
- `All.for.Cabal.Web.Setup-0.1.21.exe.sha256`

เปิด PowerShell ในโฟลเดอร์ Downloads แล้วใช้คำสั่ง:

```powershell
Get-FileHash ".\All.for.Cabal.Web.Setup-0.1.21.exe" -Algorithm SHA256
Get-Content ".\All.for.Cabal.Web.Setup-0.1.21.exe.sha256"
```

ค่าที่ถูกต้องคือ:

```text
B8664992AC5BC3AD6DFFDF8BA3C275E40D3A8CECC2DA42553DA4D612D4AE2F66
```

ถ้าค่าไม่ตรง ห้ามเปิด Setup และให้ดาวน์โหลดไฟล์ใหม่

## 2. ติดตั้งและเปิดโปรแกรม

1. ดับเบิลคลิก `All.for.Cabal.Web.Setup-0.1.21.exe`
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

## 5. การแก้ไขใน v0.1.21

- แก้การเชื่อม Aztek Local ที่แจ้งว่า `ข้อมูล session ที่จับมาไม่สมบูรณ์ — session เดิมยังอยู่` ทั้งที่เปิดหน้า Aztek dashboard สำเร็จแล้ว
- กรอง cookie และ localStorage ชั่วคราวจากผู้ให้บริการล็อกอินภายนอกออกจาก session ที่โปรแกรมจับ โดยเก็บเฉพาะข้อมูลของ Aztek และ SSO ที่อนุญาต
- คงการตรวจข้อมูล pairing จากภายนอกแบบเข้มงวด และใช้ Aztek v2 ที่ `aztek-tools-v2.combo-interactive.com/combo` ตามเดิม

## 6. สถานะการตรวจ v0.1.21

- Automated tests: `1393 passed`
- Regression tests ครอบคลุมการกรอง cookie และ localStorage จาก login provider ภายนอก โดยไม่ลดความเข้มงวดของ pairing API
- ตรวจไฟล์ Setup ด้วยระบบตรวจ release artifact สำเร็จ
- SHA-256 จากไฟล์ Setup ตรงกับไฟล์ `.sha256`
- ขนาด Setup: `268,164,384` bytes (`255.74 MiB`)
- Setup สร้างจาก source snapshot `c7e3e88`
- Setup ยังไม่มี digital signature
- ยังไม่ได้ตรวจบน clean VM ที่ตัดอินเทอร์เน็ตทั้งหมด
- ติดตั้งทับรุ่นเดิมและตรวจ health ของโปรแกรมที่ติดตั้งจริงสำเร็จ
- ไม่ได้กดสร้างข้อมูลจริงใน Aztek ระหว่างการตรวจรุ่นนี้
