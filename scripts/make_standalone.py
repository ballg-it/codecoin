#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_standalone.py — ทำไฟล์เดโมรุ่น "ไฟล์เดียวจบ" เอาไปส่งต่อได้เลย

ปกติ box_demo/codecoin_box_demo_v4.html อ่านรูปจากโฟลเดอร์ demo_assets/ ที่อยู่ข้าง ๆ
ถ้าก๊อปไปแต่ไฟล์ HTML เฉย ๆ รูปกระดานกับการ์ดจะไม่ขึ้น
สคริปต์นี้ฝังรูปทั้งหมดเป็น data URI ลงในไฟล์เลย จะเหลือไฟล์เดียวที่เปิดที่ไหนก็ได้

    py scripts/make_standalone.py

ผลลัพธ์: box_demo/codecoin_box_demo_standalone.html
(ต้องรัน scripts/gen_demo_assets.py ให้มี box_demo/demo_assets/ ก่อน)
"""
import base64
import json
import sys
from pathlib import Path

# console Windows บางเครื่องเป็น cp1252 — บังคับ UTF-8 ให้พิมพ์ภาษาไทยได้
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent   # สคริปต์อยู่ scripts/ ไฟล์เดโมอยู่ box_demo/
DEMO = ROOT / "box_demo"
SRC = DEMO / "codecoin_box_demo_v4.html"
ASSETS = DEMO / "demo_assets"
DST = DEMO / "codecoin_box_demo_standalone.html"

# ฝังทุกไฟล์รูปใน demo_assets/ ไม่ใช่เฉพาะที่ตอนนี้เรียกใช้
# เผื่อวันหลังแก้เดโมให้โชว์การ์ดใบอื่น ไฟล์ standalone จะได้ไม่พังเงียบ ๆ
# กำหนด mime เองแทน mimetypes.guess_type เพราะบางเครื่องไม่รู้จัก .webp
# แล้วจะได้ application/octet-stream ซึ่งเบราว์เซอร์บางตัวไม่ยอมแสดงผล
MIME = {".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}


def main():
    if not SRC.exists():
        raise SystemExit(f"ไม่พบไฟล์ต้นทาง: {SRC}")
    if not ASSETS.exists():
        raise SystemExit(f"ไม่พบ {ASSETS} — รัน gen_demo_assets.py ก่อน")

    html = SRC.read_text(encoding="utf-8")
    if "window.EMBED" not in html:
        raise SystemExit("ไฟล์ต้นทางไม่มีตัวอ่าน window.EMBED ใน artwork() — อัปเดต HTML ก่อน")

    embed, total = {}, 0
    for f in sorted(ASSETS.rglob("*")):
        mime = MIME.get(f.suffix.lower())
        if not f.is_file() or not mime:
            continue
        # key ต้องตรงกับ path ที่ HTML เรียก (ASSET = 'demo_assets/') จึงอิงจากโฟลเดอร์ box_demo/
        key = f.relative_to(DEMO).as_posix()          # เช่น demo_assets/cards/coding_01_f.webp
        data = base64.b64encode(f.read_bytes()).decode("ascii")
        embed[key] = f"data:{mime};base64,{data}"
        total += f.stat().st_size

    tag = ("<script>window.EMBED=" +
           json.dumps(embed, ensure_ascii=False, separators=(",", ":")) +
           ";</script>")
    out = html.replace("<body>", "<body>\n" + tag, 1)
    if out == html:
        raise SystemExit("หาแท็ก <body> ไม่เจอ ฝังรูปไม่ได้")

    DST.write_text(out, encoding="utf-8")
    print(f"ฝังรูป {len(embed)} ไฟล์ ({total/1024:.0f} KB)")
    print(f"{DST.name}  {DST.stat().st_size/1024/1024:.2f} MB  (ต้นฉบับ {SRC.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
