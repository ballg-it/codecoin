# -*- coding: utf-8 -*-
"""
gen_icons.py — สร้างไอคอน PWA ลาย PCB ให้ CodeCoin
ติดตั้งก่อนใช้:  pip install pillow
รัน:            py gen_icons.py
ผลลัพธ์:        icon-192.png, icon-512.png (วางที่ root เดียวกับ index.html)

ดีไซน์: พื้น PCB เขียวเข้ม + กริด + ลายเส้นทองแดงสีทองวิ่งเข้าหาเหรียญกลาง
เนื้อหาหลักอยู่ในวงกลางไม่เกิน 80% ของด้าน — ปลอดภัยกับไอคอนแบบ maskable
(Android จะครอบมุมทิ้ง ถ้าวางชิดขอบจะโดนตัด)
"""
import math
import sys

from PIL import Image, ImageDraw

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

BOARD = (11, 43, 34)     # --board  #0B2B22
GRID = (15, 76, 58)      # เส้นกริดบนแผ่นปริ๊นต์ #0F4C3A
GOLD = (251, 191, 36)    # --gold   #FBBF24
DARK = (5, 16, 12)       # สีตัวอักษรบนเหรียญ


def make(size):
    img = Image.new("RGB", (size, size), BOARD)
    d = ImageDraw.Draw(img)
    c = size / 2

    # ---- กริดพื้นหลัง ----
    step = size / 8
    gw = max(1, size // 200)
    for i in range(1, 8):
        d.line([(i * step, 0), (i * step, size)], fill=GRID, width=gw)
        d.line([(0, i * step), (size, i * step)], fill=GRID, width=gw)

    # ---- ลายเส้นทองแดง: วิ่งจากขอบ หักมุม 45° เข้าหาเหรียญ + จบด้วยแพด ----
    tw = max(2, int(size * 0.022))
    pad = max(3, int(size * 0.030))
    r_stop = size * 0.235 * 1.10   # เส้นจบพอดีขอบเหรียญ ไม่มุดเข้าไปใต้เหรียญ
    diag = size * 0.085          # ช่วงเฉียง 45° ก่อนหักเป็นแนวนอน
    for ang, x_pad in [(140, 0.07), (40, 0.93), (220, 0.07), (320, 0.93)]:
        rad = math.radians(ang)
        ex, ey = c + r_stop * math.cos(rad), c - r_stop * math.sin(rad)
        kx = ex + (diag if math.cos(rad) > 0 else -diag)
        ky = ey - (diag if math.sin(rad) > 0 else -diag)
        px = size * x_pad
        # ขอบเหรียญ → เฉียง 45° → แนวนอนออกไปจบที่แพดริมขอบ
        d.line([(ex, ey), (kx, ky), (px, ky)], fill=GOLD, width=tw, joint="curve")
        d.ellipse([px - pad, ky - pad, px + pad, ky + pad], fill=GOLD)

    # ---- เหรียญกลาง ----
    r = size * 0.235
    d.ellipse([c - r, c - r, c + r, c + r], fill=GOLD)
    ring = r * 0.86
    d.ellipse([c - ring, c - ring, c + ring, c + ring], outline=DARK, width=max(2, int(size * 0.012)))

    # ตัว C วาดด้วยส่วนโค้ง (ไม่พึ่งฟอนต์ในเครื่อง — ผลลัพธ์เหมือนกันทุกเครื่อง)
    cr = r * 0.52
    d.arc([c - cr, c - cr, c + cr, c + cr], start=40, end=320, fill=DARK, width=max(3, int(size * 0.055)))
    return img


for s in (192, 512):
    path = f"icon-{s}.png"
    make(s).save(path)
    print(f"[OK] {path} ({s}x{s})")
