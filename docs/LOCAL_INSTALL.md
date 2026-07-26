# ติดตั้ง All for Cabal Web แบบ Local

เวอร์ชัน Local ใช้กับ Windows 10/11 แบบ 64 บิต แต่ละคนติดตั้งและเก็บข้อมูล
ไว้ในเครื่องของตัวเอง ไม่ต้องติดตั้ง Python, Docker, Playwright หรือพิมพ์คำสั่ง
เพื่อเปิดโปรแกรม

## ดาวน์โหลดและตรวจไฟล์

1. ดาวน์โหลดไฟล์สองไฟล์จาก GitHub Release เดียวกัน:
   - `All for Cabal Web Setup-0.1.0.exe`
   - `All for Cabal Web Setup-0.1.0.exe.sha256`
2. เปิด PowerShell ในโฟลเดอร์ Downloads แล้วตรวจค่า:

   ```powershell
   Get-FileHash ".\All for Cabal Web Setup-0.1.0.exe" -Algorithm SHA256
   Get-Content ".\All for Cabal Web Setup-0.1.0.exe.sha256"
   ```

3. ค่า SHA256 จากสองคำสั่งต้องตรงกัน ถ้าไม่ตรง ห้ามเปิด Setup และให้ดาวน์โหลดใหม่

ตัวติดตั้ง 0.1.0 ยังไม่มีลายเซ็นดิจิทัลของผู้พัฒนา Windows จึงอาจแสดง
`Unknown publisher` หรือคำเตือน SmartScreen ให้ตรวจ SHA-256 และตรวจว่าไฟล์มา
จาก Release ของ repo นี้ก่อนดำเนินการติดตั้ง

## ติดตั้งและเปิดใช้งาน

1. ดับเบิลคลิก `All for Cabal Web Setup-0.1.0.exe`
2. ติดตั้งตามขั้นตอนปกติ และเลือกสร้างไอคอน Desktop ได้ตามต้องการ
3. หน้าสุดท้ายปล่อยเครื่องหมาย `เปิด All for Cabal Web` ไว้แล้วกด Finish
4. หน้าต่าง Controller จะเปิด Item Finder ในเบราว์เซอร์ให้อัตโนมัติ
   โดยไม่ถามชื่อผู้ใช้หรือรหัสผ่าน

Controller มีสามปุ่ม:

- `เปิดหน้าเว็บ` เปิดแท็บใหม่โดยใช้ server เดิม
- `เริ่มใหม่` หยุดและเริ่ม local server ใหม่
- `ปิดโปรแกรม` หยุด server และปิด Controller

ถ้ากดปิดหน้าต่าง โปรแกรมจะถามยืนยันหนึ่งครั้งก่อนหยุด server ข้อมูลทั้งหมด
ยังอยู่และจะกลับมาเมื่อเปิด shortcut ครั้งถัดไป

## เชื่อม Aztek

เปิดหน้า `เชื่อม Aztek` ใน All for Cabal แล้วทำตามขั้นตอน Bookmarklet บนหน้า
Aztek ที่ล็อกอินอยู่แล้ว โปรแกรม All for Cabal จะไม่ถามและไม่เก็บรหัสผ่าน Aztek
การเชื่อมและ Preview ต้องใช้อินเทอร์เน็ต แม้ตัว Setup และการเปิดโปรแกรมจะทำงาน
แบบ offline ได้

## อัปเดต

ปิด Controller แล้วติดตั้ง Setup เวอร์ชันใหม่ทับเวอร์ชันเดิมได้เลย ไม่ต้องถอน
เวอร์ชันเก่า ฐานข้อมูล ประวัติงาน และ Aztek session ที่เข้ารหัสจะคงอยู่ โปรแกรม
สร้าง backup ก่อน migration ไว้ใน:

```text
%LOCALAPPDATA%\AllForCabalWeb\backups
```

## สำรองและถอนการติดตั้ง

ข้อมูลทั้งหมดอยู่ที่:

```text
%LOCALAPPDATA%\AllForCabalWeb
```

ปิดโปรแกรมก่อน แล้วคัดลอกทั้งโฟลเดอร์นี้เพื่อสำรองข้อมูล การถอนการติดตั้งจะลบ
เฉพาะไฟล์โปรแกรมและจะเก็บโฟลเดอร์ข้อมูลนี้ไว้ เผื่อกลับมาติดตั้งใหม่

หากต้องการลบข้อมูลถาวรจริง ๆ หลังถอนการติดตั้ง ให้สำรองสิ่งที่ต้องการก่อน
ตรวจว่า Controller ปิดแล้ว จากนั้นลบโฟลเดอร์
`%LOCALAPPDATA%\AllForCabalWeb` ด้วยตัวเอง การลบนี้ย้อนกลับไม่ได้

## หลักฐานการตรวจ release 0.1.0

| รายการ | ผล |
|---|---|
| เครื่องที่ใช้ตรวจ | Windows client 25H2, build 26220.8925, x64 |
| Installer version | 0.1.0 |
| ขนาด Setup | 268,046,058 bytes |
| Setup SHA-256 | `45A047C6792057745FCB81D2538D8C92C01D4C3611F499343BF68186F6611933` |
| ลายเซ็นดิจิทัลของ Setup | ยังไม่มี (`NotSigned`) |
| ติดตั้งจริงจาก Setup | ผ่าน; installer exit code 0 |
| เริ่ม packaged server | ผ่าน; health product เป็น `all-for-cabal-local` |
| ที่อยู่ server | ผ่าน; listen เฉพาะ `127.0.0.1:8000` |
| เข้าใช้โดยไม่มีฟอร์มล็อกอิน | ผ่าน; session เป็น `local.owner`, `local_mode=true` และ cookie เป็น HttpOnly |
| local launch token | ผ่าน; ใช้ครั้งแรกได้และใช้ซ้ำไม่ได้ |
| เปิด shortcut ครั้งที่สอง | ผ่าน; process ที่สอง exit code 0 และใช้ server เดิม |
| หยุด packaged process แล้ว port 8000 หยุด | ผ่าน |
| ติดตั้ง 0.1.0 ทับแล้วข้อมูลเดิมยังอยู่ | ผ่าน; config/database hash เดิม เปิด server ได้ และมี pre-migration backup |
| ถอนแล้วข้อมูล LocalAppData ยังอยู่ | ผ่าน; config/database/backup ยังอยู่ครบ |
| Full automated tests | `356 passed` |
| เปิดครั้งแรกโดยตัดอินเทอร์เน็ตทั้งหมด | ยังไม่ได้ทดสอบบน clean VM |
| อัปเกรดจากเลขเวอร์ชันต่ำกว่าไปสูงกว่า | ยังไม่ได้ทดสอบบน clean VM |
| Clean Windows 10/11 ที่ไม่มีเครื่องมือพัฒนา | ยังไม่ได้ทดสอบ |
| Real Aztek create | ไม่ได้ทดสอบและจะไม่กดสร้างจริง |

รายการที่ระบุว่า clean VM ยังไม่ได้ทดสอบต้องตรวจเพิ่มก่อนอ้างว่า release นี้ผ่าน
การรับรองบนเครื่องสะอาดครบถ้วน ส่วนการเชื่อม Aztek และ Preview ต้องใช้อินเทอร์เน็ต
และ session Aztek ของผู้ใช้
