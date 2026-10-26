#!/usr/bin/env python3
"""เปลี่ยน QR บนไฟล์กระดาน Final1.pdf ให้ชี้ BASE_URL ปัจจุบัน (ใช้ตอนเปลี่ยนชื่อ GitHub / โดเมน)

หา QR ทุกจุดบนหน้าด้วย OpenCV → อ่าน space id เดิม → ลบของเดิมด้วย redaction (เติมขาว)
→ วาด QR ใหม่เป็นเวกเตอร์ทับตำแหน่งเดิมพอดี (เฉพาะโมดูล ไม่รวมขอบเงียบ ซึ่งการ์ดบนกระดานเป็นขาวอยู่แล้ว)
เสร็จแล้วรัน prepare_board_print.py ต่อเพื่อสร้าง PRINT.pdf ใหม่

รัน: py -3 scripts/swap_board_qr.py
"""
import os
import re
import sys

import cv2
import fitz
import numpy as np
import qrcode
from qrcode.constants import ERROR_CORRECT_H

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_qr import BASE_URL  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "print", "Final", "CodeCoin-Board-50x50-Final1.pdf")
DPI = 300
TILE, STEP = 900, 450


def find_qrs(page):
    """คืน {space_id: Rect ของโมดูล QR ในพิกัด PDF}"""
    pix = page.get_pixmap(dpi=DPI)
    im = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].copy()
    det = cv2.QRCodeDetector()
    found = {}
    for y in range(0, pix.h - STEP, STEP):
        for x in range(0, pix.w - STEP, STEP):
            ok, texts, pts, _ = det.detectAndDecodeMulti(im[y:y + TILE, x:x + TILE])
            if not ok:
                continue
            for t, p in zip(texts, pts):
                m = re.search(r"[?&]space=(\w+)", t or "")
                if m and m.group(1) not in found:
                    xs, ys = p[:, 0] + x, p[:, 1] + y
                    s = 72 / DPI
                    found[m.group(1)] = (t, fitz.Rect(xs.min() * s, ys.min() * s, (xs.max() + 1) * s, (ys.max() + 1) * s))
    return found


def draw_qr(page, rect, url):
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=0)
    qr.add_data(url)
    qr.make(fit=True)
    mods = qr.get_matrix()
    n = len(mods)
    size = min(rect.width, rect.height)
    cell = size / n
    shape = page.new_shape()
    for r, row in enumerate(mods):
        c = 0
        while c < n:                       # รวมโมดูลดำติดกันในแถวเป็นสี่เหลี่ยมเดียว ลดจำนวน path
            if row[c]:
                c0 = c
                while c < n and row[c]:
                    c += 1
                shape.draw_rect(fitz.Rect(rect.x0 + c0 * cell, rect.y0 + r * cell,
                                          rect.x0 + c * cell, rect.y0 + (r + 1) * cell))
            else:
                c += 1
    shape.finish(color=None, fill=(0, 0, 0), width=0)
    shape.commit()


def main():
    doc = fitz.open(SRC)
    page = doc[0]
    qrs = find_qrs(page)
    todo = {sid: v for sid, v in qrs.items() if not v[0].startswith(BASE_URL)}
    print(f"พบ QR {len(qrs)} จุด ต้องเปลี่ยน {len(todo)} จุด")
    if not todo:
        return
    for sid, (_, rect) in todo.items():
        page.add_redact_annot(rect, fill=(1, 1, 1))
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS,
                          graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED)
    for sid, (old, rect) in todo.items():
        draw_qr(page, rect, f"{BASE_URL}/?space={sid}")
        print(f"  {sid:<16} {old}  ->  {BASE_URL}/?space={sid}")
    doc.save(SRC + ".tmp", garbage=3, deflate=True)
    doc.close()
    os.replace(SRC + ".tmp", SRC)
    print(f"บันทึก {SRC}")


if __name__ == "__main__":
    main()
