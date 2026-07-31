#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_demo_assets.py — ตัดของจริงจาก PDF ส่งโรงพิมพ์ใน Final/ ออกมาเป็นรูป
สำหรับ codecoin_box_demo_v4.html (แท็บ "กล่องประกอบ" / "ของในกล่อง")

ผลลัพธ์ลงที่ demo_assets/ (WebP q90 — เล็กกว่า PNG ~5 เท่าที่ความละเอียดเท่ากัน
เพราะพื้นหลังการ์ดเป็นเฉดไล่สี ซึ่ง PNG บีบไม่ลง)
    board.webp             กระดาน 50 x 50 ซม. ตัดขอบเผื่อพิมพ์ออกแล้ว
    cards/<id>_f.webp      การ์ดทรัพย์สินด้านหน้า 16 ใบ (ตัดเป็น 63 x 88 มม.)
    cards/<id>_b.webp      การ์ดทรัพย์สินด้านหลัง 16 ใบ
    cards/index.json       ลำดับการ์ด + ชื่อ + โซน + ราคา (ให้ HTML อ่านไปใช้)

รันซ้ำได้ทุกครั้งที่ export PDF ใหม่:
    python gen_demo_assets.py
"""
import json
import re
import shutil
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
FINAL = ROOT / "Final"
OUT = ROOT / "demo_assets"
CARDS_OUT = OUT / "cards"

PT = 72.0 / 25.4  # มม. -> point

BOARD_PDF = FINAL / "CodeCoin-Board-50x50-Final1.pdf"
FRONT_PDF = FINAL / "หน้า.pdf"
BACK_PDF = FINAL / "หลัง.pdf"

BOARD_TRIM_MM = 500.0  # กระดานจริงหลังตัด
CARD_W_MM, CARD_H_MM = 63.0, 88.0  # การ์ดจริงหลังตัด
BOARD_PPMM = 2.0  # 1000 x 1000 px
CARD_PPMM = 5.0  # 315 x 440 px
WEBP_Q = 90

ID_RE = re.compile(r"\b([a-z]+_\d{2})\b")
# ป้ายโซนบนการ์ดพิมพ์แบบเว้นวรรคทีละตัว เช่น "C O D I N G  AV E N U E"
ZONE_LINE_RE = re.compile(r"^[A-Z][A-Z\s]{6,}$")
ZONE_TH = {
    "coding": "CODING AVENUE",
    "office": "OFFICE STREET",
    "design": "DESIGN DISTRICT",
    "hardware": "HARDWARE TOWN",
}


def detect_card_boxes(page, dpi=72):
    """หากรอบการ์ดบนหน้ากระดาษ โดยดูแถบพิกเซลที่ไม่ใช่สีขาว

    ทนต่อการย้ายตำแหน่งจัดหน้า ไม่ต้องฮาร์ดโค้ดพิกัด
    """
    z = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    ink = arr.astype(int).sum(2) < 720

    def bands(mask):
        out, start = [], None
        for i, v in enumerate(mask):
            if v and start is None:
                start = i
            elif not v and start is not None:
                out.append((start, i))
                start = None
        if start is not None:
            out.append((start, len(mask)))
        return [b for b in out if b[1] - b[0] > 20]

    boxes = []
    for y0, y1 in bands(ink.any(1)):
        for x0, x1 in bands(ink.any(0)):
            if ink[y0:y1, x0:x1].mean() > 0.5:  # บล็อกทึบ ไม่ใช่เส้นบาง
                boxes.append(fitz.Rect(x0 / z, y0 / z, x1 / z, y1 / z))
    return boxes


def trim_rect(box, w_mm, h_mm):
    """ครอบตรงกลางกรอบที่ตรวจเจอ ให้ได้ขนาดหลังตัดพอดี (ตัด bleed ทิ้ง)"""
    cx, cy = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
    hw, hh = w_mm * PT / 2, h_mm * PT / 2
    return fitz.Rect(cx - hw, cy - hh, cx + hw, cy + hh)


def save_clip(page, clip, path, ppmm):
    zoom = ppmm * 25.4 / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img.save(str(path), "WEBP", quality=WEBP_Q, method=6)
    return pix.width, pix.height


def collect(pdf_path, label):
    """คืน dict: id -> (page, clip, text) ของการ์ดทุกใบในไฟล์"""
    doc = fitz.open(pdf_path)
    found = {}
    for page in doc:
        for box in detect_card_boxes(page):
            text = page.get_text("text", clip=box)
            m = ID_RE.search(text)
            if not m:
                print(f"  ! {label}: กรอบที่ ({box.x0:.0f},{box.y0:.0f}) หา id ไม่เจอ ข้าม")
                continue
            found[m.group(1)] = (page, trim_rect(box, CARD_W_MM, CARD_H_MM), text)
    return doc, found


def main():
    for p in (BOARD_PDF, FRONT_PDF, BACK_PDF):
        if not p.exists():
            raise SystemExit(f"ไม่พบไฟล์: {p}")

    if OUT.exists():
        shutil.rmtree(OUT)
    CARDS_OUT.mkdir(parents=True)

    # ---------- กระดาน ----------
    doc = fitz.open(BOARD_PDF)
    page = doc[0]
    clip = trim_rect(page.rect, BOARD_TRIM_MM, BOARD_TRIM_MM)
    w, h = save_clip(page, clip, OUT / "board.webp", BOARD_PPMM)
    bleed = (page.rect.width / PT - BOARD_TRIM_MM) / 2
    print(f"board.webp  {w} x {h} px  (ตัด bleed ด้านละ {bleed:.2f} มม.)")
    doc.close()

    # ---------- การ์ด ----------
    fdoc, fronts = collect(FRONT_PDF, "หน้า")
    bdoc, backs = collect(BACK_PDF, "หลัง")

    only_f = sorted(set(fronts) - set(backs))
    only_b = sorted(set(backs) - set(fronts))
    if only_f:
        print(f"  ! มีหน้าแต่ไม่มีหลัง: {only_f}")
    if only_b:
        print(f"  ! มีหลังแต่ไม่มีหน้า: {only_b}")

    order = {"coding": 0, "office": 1, "design": 2, "hardware": 3}
    ids = sorted(fronts, key=lambda k: (order.get(k.split("_")[0], 9), k))

    index = []
    for cid in ids:
        page, clip, text = fronts[cid]
        save_clip(page, clip, CARDS_OUT / f"{cid}_f.webp", CARD_PPMM)
        if cid in backs:
            bpage, bclip, _ = backs[cid]
            save_clip(bpage, bclip, CARDS_OUT / f"{cid}_b.webp", CARD_PPMM)

        # ดึงชื่อการ์ด + ราคา จากข้อความบนใบจริง
        # หมายเหตุ: ข้อความบนการ์ดถูกวางซ้ำสองรอบทุกบรรทัด และชื่อยาวจะขึ้น 2 บรรทัด
        # จึงต้องเก็บจนถึงป้ายโซน แล้วตัดบรรทัดที่ซ้ำติดกันออก
        lines = [t.strip() for t in text.split("\n") if t.strip()]
        price = next((t for t in lines if re.fullmatch(r"[\d,]{3,6}", t)), "")
        title = cid
        if "การ์ดทรัพย์สิน" in lines:
            parts = []
            for ln in lines[lines.index("การ์ดทรัพย์สิน") + 1:]:
                if ZONE_LINE_RE.match(ln):
                    break
                if not parts or parts[-1] != ln:
                    parts.append(ln)
            if parts:
                title = " ".join(parts)
        index.append({
            "id": cid,
            "zone": cid.split("_")[0],
            "zoneLabel": ZONE_TH.get(cid.split("_")[0], ""),
            "title": title,
            "price": price,
            "back": cid in backs,
        })

    (CARDS_OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    fdoc.close()
    bdoc.close()

    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"การ์ด {len(ids)} ใบ (มีหลัง {sum(1 for i in index if i['back'])} ใบ)")
    print(f"รวมทั้งหมด {total/1024/1024:.2f} MB -> {OUT}")


if __name__ == "__main__":
    main()
