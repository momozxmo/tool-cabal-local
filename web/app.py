# -*- coding: utf-8 -*-
"""All for Cabal — Web (มินิมอล, รันในเครื่อง)
สไลซ์แรก: เสิร์ฟหน้าเว็บ + อัปโหลด template แล้ว parse ด้วยตัวอ่านเดิม (item_finder.read_template)
รัน:  python -m uvicorn web.app:app --reload --port 8000   (จาก root ของ repo)
"""
import os
import sys
import tempfile

# ให้ import โมดูลใน repo root ได้ (item_finder / finder_core)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI, UploadFile, File, HTTPException  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402

import item_finder  # reuse ตัว parse template เดิม (read_template)  # noqa: E402

app = FastAPI(title="All for Cabal — Web")

_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(_STATIC, "index.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/upload-template")
async def upload_template(file: UploadFile = File(...)):
    """รับไฟล์ template (.xlsx/.csv) -> parse เป็นรายการไอเทม (criteria) ส่งกลับเป็น JSON."""
    suffix = os.path.splitext(file.filename or "")[1] or ".xlsx"
    raw = await file.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(raw)
        tmp.close()
        rows = item_finder.read_template(tmp.name)
    except Exception as e:
        raise HTTPException(status_code=400, detail="อ่าน template ไม่สำเร็จ: %s" % e)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    return {"filename": file.filename, "count": len(rows), "items": rows}
