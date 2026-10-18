#!/usr/bin/env python3
"""เตรียมไฟล์กระดานส่งโรงพิมพ์: ใส่ TrimBox/BleedBox + crop marks จาก Final1.pdf

ต้นฉบับ (Skia export) เป็นหน้า 510.12 mm = trim 500 + bleed 5.06 รอบด้าน แต่ไม่มี trim box/crop mark
สคริปต์นี้วางต้นฉบับลงหน้าใหญ่ขึ้น (slug 10 mm) แล้วเติม crop marks นอกเขต bleed
เวกเตอร์/ฟอนต์/QR ไม่ถูกแตะ — โหมดสียังเป็น RGB (ให้โรงพิมพ์แปลง CMYK ด้วยโปรไฟล์ของเขา)

รัน: py -3 scripts/prepare_board_print.py
"""
import os
import fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "print", "Final", "CodeCoin-Board-50x50-Final1.pdf")
DST = os.path.join(ROOT, "print", "Final", "CodeCoin-Board-50x50-PRINT.pdf")

MM = 72 / 25.4
TRIM = 500.0
SLUG = 10.0                      # มม. รอบหน้าต้นฉบับ สำหรับ crop marks
BOARD_RGB = (10 / 255, 42 / 255, 33 / 255)   # สีพื้นขอบกระดาน อุดช่องขาว 0.12 มม. ขวา/ล่างของต้นฉบับ


def main():
    src = fitz.open(SRC)
    sp = src[0]
    sw, sh = sp.rect.width, sp.rect.height
    bleed = (sw - TRIM * MM) / 2             # ~5.06 mm ใน pt
    off = SLUG * MM

    out = fitz.open()
    pg = out.new_page(width=sw + 2 * off, height=sh + 2 * off)
    pg.draw_rect(fitz.Rect(off, off, off + sw, off + sh), color=None, fill=BOARD_RGB)
    pg.show_pdf_page(fitz.Rect(off, off, off + sw, off + sh), src, 0)

    t = fitz.Rect(off + bleed, off + bleed, off + sw - bleed, off + sh - bleed)   # trim
    gap, ln = (bleed + 1.0 * MM), 3.0 * MM                                          # ห่างขอบตัด / ยาว
    for x in (t.x0, t.x1):
        for y0, y1 in ((t.y0 - gap - ln, t.y0 - gap), (t.y1 + gap, t.y1 + gap + ln)):
            pg.draw_line((x, y0), (x, y1), color=(0, 0, 0), width=0.25)
    for y in (t.y0, t.y1):
        for x0, x1 in ((t.x0 - gap - ln, t.x0 - gap), (t.x1 + gap, t.x1 + gap + ln)):
            pg.draw_line((x0, y), (x1, y), color=(0, 0, 0), width=0.25)

    pg.set_trimbox(t)
    pg.set_bleedbox(fitz.Rect(off, off, off + sw, off + sh))
    out.set_metadata({"title": "CodeCoin Board 500x500 mm PRINT (trim 500, bleed 5.06, RGB)"})
    out.save(DST, garbage=4, deflate=True)

    chk = fitz.open(DST)[0]
    f = lambda r: (round(r.width / MM, 2), round(r.height / MM, 2))
    print("page", f(chk.rect), "trim", f(chk.trimbox), "bleed", f(chk.bleedbox), "mm")


if __name__ == "__main__":
    main()
