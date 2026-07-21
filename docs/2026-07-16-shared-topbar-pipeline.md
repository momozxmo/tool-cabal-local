# Spec: แถบบนร่วม + Login จุดเดียว + Pipeline ส่งต่อ

วันที่: 2026-07-16 · สถานะ: ✅ ทำเสร็จแล้ว (คอมไพล์ผ่าน + 15/15 tests + smoke embedded/standalone)

## เป้าหมาย
ทำให้ 4 tool (Item Finder / Create Bundle / Item Code / Event) รู้สึกเป็น "ระบบเดียว":
1. **Login จุดเดียว** — เลิกปุ่ม Login/ล้าง session/ทดสอบ ที่ซ้ำในทุก tool → รวมบนแถบบน
2. **เกม/เซิร์ฟ ตัวเดียว** — dropdown บนแถบบน (ผูก `game_var` เดิม)
3. **Pipeline เห็นชัด + ส่งต่อคลิกเดียว** — Item Finder → Create Bundle → (แยก) Item Code / Event
4. **แก้ไขข้อมูลได้ทุกจุด** — ข้อมูลที่ส่งต่อมาลงเป็นช่องกรอกปกติ ไม่ล็อก

## รูปแบบที่เลือก
"แถบบนร่วม + ส่งต่อฉลาด" (เก็บโค้ด tool เดิมไว้ เพิ่มแถบบน + ปุ่มส่งต่อ) — เปลี่ยนน้อย เสี่ยงต่ำ

## รายละเอียดการเปลี่ยน

### 1) แถบบนร่วมใน launcher (`all_for_cabal.py`)
เพิ่มแถวใต้แถบเมนู มี:
- **เกม/เซิร์ฟ combobox** ผูก `self.game_var` (ตัวเดิม)
- **🔑 เข้าสู่ระบบ** → เปิด browser login ตาม URL ของเกมที่เลือก (ใช้ `aztek_core.AztekSession.open_login`
  บน `core.build_url(game, 'bundles')`) รันใน thread + ผ่าน browser-lock ที่มีอยู่
- **สถานะ**: `● มี session` (teal) ถ้า `core.has_session()` / `○ ยังไม่ login` (เทา) — refresh หลัง login/ล้าง
- ปุ่มรอง: **ล้าง session** (`core.clear_profile`) · **ทดสอบเข้าหน้า** (เปิด browser เช็ก `is_logged_in`)
- ใส่ลูกศร/ลำดับในเมนูบอกทาง: `🔍 หาไอเทม → 📦 Bundle → 🎟️/🎉` (cosmetic)

### 2) ซ่อน เกม + Login ในแต่ละ tool ตอน embedded
ทุก App: `self._embedded = container is not None`
- **embedded (เปิดผ่าน launcher)** → ไม่สร้าง dropdown เกม + ไม่สร้าง section Login ของตัวเอง (ใช้แถบบนแทน)
- **standalone (รันไฟล์ tool ตรงๆ)** → สร้างครบเหมือนเดิม (ไม่พัง)
- `game_var` ยังส่งมาจาก launcher เหมือนเดิม (แค่ซ่อน widget ไม่ตัด logic)
- ไฟล์ที่แตะ: `item_finder.py`, `new_tool.py`, `itemcode_tool.py`, `event_tool.py` (เฉพาะส่วน build UI ของเกม/login)

### 3) ส่งต่อคลิกเดียว
- launcher เพิ่ม callback `on_go_next(target_key)` ส่งให้ Create Bundle
- **Create Bundle**: หลังสร้าง bundle เสร็จ โผล่กล่อง "ขั้นต่อไป" ปุ่ม `🎟️ ไปสร้าง Item Code` / `🎉 ไปสร้าง Event`
  → เรียก `on_go_next('itemcode'|'event')`
- **launcher.`_go_next`**: `show(target)` + เรียก method ดึงคิวของ tool ปลายทางอัตโนมัติ
- **Item Code / Event**: เปิด method public สำหรับ "ดึงจากคิว" (ที่ปุ่มเดิมเรียกอยู่) ให้ launcher เรียกได้

### 4) แก้ไขได้ทุกจุด
ตรวจว่าข้อมูลที่ส่งต่อ (ไอเทม → bundle id → รางวัล) ลงเป็นช่องกรอกปกติ ไม่มี readonly เพิ่ม (ส่วนใหญ่เป็นอยู่แล้ว)

## ตัดสินใจแล้ว
- ไฟสถานะ = `has_session()` (มีโปรไฟล์ไหม) ไม่เช็ค login จริงอัตโนมัติ (เช็คจริงต้องกด "ทดสอบ")
- ตอน embedded ซ่อน เกม+Login ในทุก tool (standalone ยังครบ)

## นอกขอบเขต (ยังไม่ทำ)
- browser-lock ใน new_tool/item_finder (คนละเรื่อง — follow-up เดิม)
- เปลี่ยนโครง tool เป็น wizard/workbench (เลือกไม่เอา)

## แผนตรวจ (verify)
- คอมไพล์ทุกไฟล์ + smoke launcher (สร้าง UI ทั้ง 4 tool)
- ตรวจ embedded: เปิดผ่าน launcher แล้ว tool ไม่มี dropdown เกม/ปุ่ม login ของตัวเอง
- ตรวจ standalone: เปิด tool ตรงๆ ยังมี เกม+login ครบ
- ตรวจส่งต่อ: Bundle → ปุ่มไป Item Code/Event → หน้าเปลี่ยน + ดึงข้อมูลเข้า
- ไฟสถานะเปลี่ยนตาม has_session หลัง login/ล้าง
