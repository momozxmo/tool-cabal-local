# -*- coding: utf-8 -*-
"""
config.py — กฎธุรกิจรวมศูนย์ (เปลี่ยนที่นี่ที่เดียว)

รวมค่าที่ต้องแก้บ่อยไว้ที่เดียว เพื่อไม่ต้องไล่แก้หลายไฟล์:
  - เวลาสิ้นสุดตามภูมิภาคเซิร์ฟ (TH 23:59:59 / SEA 22:59:59)
  - buffer จำนวนโค้ด (PCTH +10, เซิร์ฟอื่น +5)
  - server-code สำหรับ slug (CabalPC TH -> pcth)
  - ตาราง keyword ของ template ไทย/อังกฤษ (เพิ่ม wording ใหม่ = เพิ่ม 1 บรรทัด)

โมดูลนี้ pure (ไม่ import tk/playwright/core) — เทสต์ได้ตรงๆ
"""

import re

# --------------------------------------------------------------------------- server code / slug
def server_code(game):
    """'CabalPC TH' -> 'pcth' | 'CabalM SEA' -> 'msea' (ตัดคำว่า cabal + ช่องว่าง)"""
    return re.sub(r"cabal", "", str(game or ""), flags=re.I).replace(" ", "").lower()


def is_sea(game):
    return "sea" in str(game or "").lower()


# --------------------------------------------------------------------------- เวลาสิ้นสุดตามภูมิภาค
# (ชม., นาที, วิ) ของ "สิ้นวัน" ตามเซิร์ฟ — แก้ที่นี่ถ้ากติกาเวลาเปลี่ยน
REGION_END_OF_DAY = {
    "sea": (22, 59, 59),
    "th":  (23, 59, 59),
}


def region_end_of_day(game, d):
    """คืน datetime d ที่ถูกตั้งเวลาเป็น 'สิ้นวัน' ตามภูมิภาคของ game"""
    h, m, s = REGION_END_OF_DAY["sea" if is_sea(game) else "th"]
    return d.replace(hour=h, minute=m, second=s, microsecond=0)


# --------------------------------------------------------------------------- buffer จำนวนโค้ด
# buffer พิเศษต่อ server-code (นอกเหนือจากนี้ใช้ DEFAULT_CODE_BUFFER)
CODE_BUFFER = {
    "pcth": 10,
}
DEFAULT_CODE_BUFFER = 5


def code_buffer(game):
    """จำนวนโค้ดที่บวกเพิ่ม (เฉพาะ 2 ชุดแรก) — PCTH +10, เซิร์ฟอื่น +5"""
    return CODE_BUFFER.get(server_code(game), DEFAULT_CODE_BUFFER)


# --------------------------------------------------------------------------- keyword ของ template (Event/ItemCode)
# ทุกตัวเทียบแบบ "substring หลัง normalize" (ตัดช่องว่าง+ตัวเล็ก) ยกเว้นที่ระบุ exact
# เพิ่ม wording ใหม่ของ template = เพิ่มสมาชิกในทูเพิลเดียว
KW_EXPIRE      = ("codeexpiredate", "วันหมดอายุ")                 # วันหมดอายุโค้ด
KW_CODES_PER_SET = ("codesperset",)                              # + เงื่อนไขไทย 'โค้ด'+'ชุด' (เช็คแยกในโค้ด)
KW_UNIQUE_CODE = ("uniquecode",)                                 # server generate
KW_TOTAL_EXACT = ("total", "รวม")                                # เทียบแบบ exact-key เท่านั้น (รวม เป็นคำกว้าง)

# เงื่อนไขเติมซ้ำ/ข้ามเซ็ต — ไทย+อังกฤษ
KW_REPEAT_NO   = ("cannot be repeat", "เติมซ้ำไม่ได้", "เติมซํ้าไม่ได้", "ห้ามเติมซ้ำ")   # cannot be repeated
KW_REPEAT_YES  = ("can be repeat", "เติมซ้ำได้", "เติมซํ้าได้")                          # can be repeated
KW_CROSS_NO    = ("even different", "ข้ามเซ็ตไม่ได้", "ข้ามเซ็ทไม่ได้")                    # cannot repeat even different sets
KW_CROSS_YES   = ("ข้ามได้", "ข้ามเซ็ตได้", "ข้ามเซ็ทได้")                                # เติมข้ามเซ็ตได้
KW_ONCE_PER_SET = ("once per set", "ครั้งเดียวต่อชุด")                                    # use code once per set


def _norm(s):
    return re.sub(r"\s+", "", str(s or "")).lower()


def kw_hit(key, phrases):
    """True ถ้า normalize(key) มี phrase ใด ๆ (phrase ถูก normalize ด้วย)"""
    k = _norm(key)
    return any(_norm(p) in k for p in phrases)
