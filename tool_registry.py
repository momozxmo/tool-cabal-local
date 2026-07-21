# -*- coding: utf-8 -*-
"""
tool_registry.py — ทะเบียนเครื่องมือ (single source of truth ของรายการ tool)

เดิม launcher hardcode รายการ tool ไว้ 6 จุด (import, _apps, navbtn, _ensure if/elif,
tuple ใน show(), การ์ด Home) เพิ่ม tool ใหม่ต้องแก้ครบทุกจุด (ลืมจุดใดจุดหนึ่ง = บั๊กเงียบ)

ตอนนี้แต่ละ tool export ตัวแปร TOOL (ToolSpec) ปลายไฟล์ของตัวเอง แล้ว launcher เอามาไล่
สร้างทุกอย่างจากทะเบียนนี้ -> เพิ่ม tool #5 = เขียน mytool.py + ใส่ mytool.TOOL ใน TOOLS
(ไฟล์นี้เล็ก ไม่ import tk/tool ใด ๆ จึงให้ .spec/สคริปต์อื่น import ได้ปลอดภัย)
"""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ToolSpec:
    key: str            # id ภายใน (frame/nav key) เช่น 'finder'
    icon: str           # emoji บนการ์ด + เมนู
    title: str          # ชื่อบนการ์ด Home
    nav: str            # ข้อความบนแถบเมนู (มี emoji นำ)
    desc: str           # คำอธิบายบนการ์ด
    boot: str           # bootstyle ปุ่มการ์ด (info/success/warning/danger)
    make: Callable      # (launcher, frame) -> App instance  (สร้างตอนกดเปิดครั้งแรก)
