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

import asyncio  # noqa: E402

from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402

import item_finder  # reuse ตัว parse template เดิม (read_template)  # noqa: E402
import aztek_core as core  # noqa: E402
from web import search_runner  # noqa: E402

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


@app.get("/api/games")
def games():
    return {"games": list(item_finder.GAME_NAMES)}


@app.websocket("/ws/search")
async def ws_search(ws: WebSocket):
    """รับ {game, web_mode, criteria} -> รันค้นหา headless แล้ว stream log/progress/result สด."""
    await ws.accept()
    try:
        req = await ws.receive_json()
    except Exception:
        await ws.close()
        return
    game = req.get("game") or ""
    web_mode = req.get("web_mode") or "any"
    criteria = req.get("criteria") or []

    async def send(m):
        await ws.send_json(m)

    if not criteria:
        await send({"type": "log", "msg": "ไม่มีรายการไอเทม (อัปโหลด template ก่อน)", "level": "ERROR"})
        await send({"type": "done", "count": 0})
        await ws.close()
        return
    try:
        data = search_runner.build_search_data(game, criteria, web_mode)
    except Exception as e:
        await send({"type": "log", "msg": str(e), "level": "ERROR"})
        await send({"type": "done", "count": 0})
        await ws.close()
        return

    q: asyncio.Queue = asyncio.Queue()
    hf = search_runner.HeadlessFinder(
        lambda msg, level="INFO": q.put_nowait({"type": "log", "msg": msg, "level": level}),
        lambda item: q.put_nowait({"type": "result", "item": search_runner.result_view(item)}),
        lambda cur, total, name: q.put_nowait(
            {"type": "progress", "cur": cur, "total": total, "name": name}),
    )

    async def run():
        try:
            await hf._auto(data)
            q.put_nowait({"type": "done", "count": len(hf._results)})
        except core.BrowserBusy:
            q.put_nowait({"type": "log",
                          "msg": "✋ Browser ถูกใช้อยู่ — ปิดแอป desktop / รอบก่อนหน้าก่อน",
                          "level": "ERROR"})
            q.put_nowait({"type": "done", "count": 0})
        except Exception as e:
            q.put_nowait({"type": "log", "msg": "error: " + str(e), "level": "ERROR"})
            q.put_nowait({"type": "done", "count": 0})
        finally:
            q.put_nowait(None)

    task = asyncio.create_task(run())
    try:
        while True:
            m = await q.get()
            if m is None:
                break
            await send(m)
    except WebSocketDisconnect:
        hf._cancel = True          # ผู้ใช้ปิดหน้า -> สั่งหยุดค้นหา
    finally:
        await task
        try:
            await ws.close()
        except Exception:
            pass
