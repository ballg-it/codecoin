#!/usr/bin/env python3
"""สร้างไฟล์ออกแบบธนบัตร TechCoin 5 ราคา -> print/banknotes/

ขนาดจริง 95 x 45 มม. (ผู้เล่นอ่านแนวนอน / ในถาดวางตะแคงกินพื้นที่ 45 x 95 มม.)
ไฟล์ SVG มี bleed รอบด้าน 3 มม. => ผืนผ้าใบ 101 x 51 มม. เส้นตัดอยู่ที่ 3 มม. จากขอบ
ตัวเลข/ข้อความเป็นฟอนต์ระบบ (sans-serif) ก่อนส่งโรงพิมพ์ให้เปิดใน Illustrator/Inkscape แล้ว
Create Outlines กันฟอนต์เพี้ยน

รัน: py scripts/gen_banknotes.py
"""
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "print", "banknotes")

W, H, BLEED = 95.0, 45.0, 3.0
CW, CH = W + 2 * BLEED, H + 2 * BLEED

# ราคา -> (สีหลัก, สีเข้ม, จำนวนขา pin บนชิป, จำนวนที่แนะนำพิมพ์ รวม 200 ใบ)
# ใช้สีโซนของเว็บ + ทอง; ต่างกันด้วยจำนวน pin และตัวเลขใหญ่ด้วย (ไม่พึ่งสีอย่างเดียว)
NOTES = [
    (10,   "#4ADE80", "#0B3A24", 1, 50),
    (50,   "#38BDF8", "#0A2F45", 2, 50),
    (100,  "#FB923C", "#4A2208", 3, 40),
    (500,  "#F472B6", "#4A1230", 4, 40),
    (1000, "#FBBF24", "#3F2C05", 5, 20),
]

BOARD = "#0B2B22"
DEEP = "#05100C"


def traces(rnd, color, x0, y0, x1, y1, n):
    """เส้นวงจร PCB แบบมุม 45 องศา สุ่มแบบ seed คงที่ (พิมพ์ซ้ำได้ผลเดิม)"""
    out = []
    for _ in range(n):
        x = rnd.uniform(x0, x1)
        y = rnd.uniform(y0, y1)
        pts = [(x, y)]
        for _ in range(rnd.randint(2, 4)):
            dx = rnd.choice([-1, 0, 1]) * rnd.uniform(2, 7)
            dy = rnd.choice([-1, 0, 1]) * rnd.uniform(2, 7)
            if dx == 0 and dy == 0:
                dx = 4
            x = min(max(x + dx, x0), x1)
            y = min(max(y + dy, y0), y1)
            pts.append((x, y))
        d = "M" + " L".join(f"{px:.2f} {py:.2f}" for px, py in pts)
        out.append(f'<path d="{d}" />')
        out.append(f'<circle cx="{pts[-1][0]:.2f}" cy="{pts[-1][1]:.2f}" r="0.55" />')
    return (f'<g fill="none" stroke="{color}" stroke-width="0.28" '
            f'stroke-linejoin="round" opacity="0.35">' + "".join(out) + "</g>")


def chip(cx, cy, size, pins, color, dark):
    """ชิปสี่เหลี่ยมมีขา — จำนวนขา/ด้าน = ราคา (1-5)"""
    h = size / 2
    legs = []
    for i in range(pins):
        t = -h + size * (i + 0.5) / pins
        for sx, sy, ex, ey in (
            (cx + t, cy - h, cx + t, cy - h - 1.6), (cx + t, cy + h, cx + t, cy + h + 1.6),
            (cx - h, cy + t, cx - h - 1.6, cy + t), (cx + h, cy + t, cx + h + 1.6, cy + t),
        ):
            legs.append(f'<line x1="{sx:.2f}" y1="{sy:.2f}" x2="{ex:.2f}" y2="{ey:.2f}" />')
    return (f'<g stroke="{color}" stroke-width="0.55" stroke-linecap="round">{"".join(legs)}</g>'
            f'<rect x="{cx - h:.2f}" y="{cy - h:.2f}" width="{size}" height="{size}" rx="1.6" '
            f'fill="{dark}" stroke="{color}" stroke-width="0.6" />')


def label(v):
    return f"{v:,}"


def front(v, color, dark, pins, seed):
    rnd = random.Random(seed)
    o = BLEED
    cx, cy = o + 20, o + H / 2          # ชิป/เหรียญซ้าย
    s = []
    s.append(f'<rect width="{CW}" height="{CH}" fill="{BOARD}" />')
    # แถบสีด้านขวา (ระบุราคาด้วยสี)
    s.append(f'<rect x="{o + W - 16}" y="0" width="{16 + o}" height="{CH}" fill="{dark}" />')
    s.append(f'<rect x="{o + W - 16}" y="0" width="0.8" height="{CH}" fill="{color}" />')
    s.append(traces(rnd, color, o + 36, o + 3, o + W - 18, o + H - 3, 16))
    s.append(traces(rnd, color, o + W - 14, o + 4, o + W - 2, o + H - 4, 6))
    # กรอบใน
    s.append(f'<rect x="{o + 2.2}" y="{o + 2.2}" width="{W - 4.4}" height="{H - 4.4}" rx="2.2" '
             f'fill="none" stroke="{color}" stroke-width="0.5" />')
    s.append(f'<rect x="{o + 3.4}" y="{o + 3.4}" width="{W - 6.8}" height="{H - 6.8}" rx="1.4" '
             f'fill="none" stroke="{color}" stroke-width="0.18" opacity="0.6" />')
    # เหรียญ + ชิป
    s.append(f'<circle cx="{cx}" cy="{cy}" r="13.2" fill="{DEEP}" stroke="{color}" stroke-width="0.7" />')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="11.2" fill="none" stroke="{color}" stroke-width="0.22" '
             f'stroke-dasharray="0.9 0.9" />')
    s.append(chip(cx, cy - 1.2, 9.0, pins, color, BOARD))
    s.append(f'<text x="{cx}" y="{cy + 0.6}" text-anchor="middle" font-size="3.4" font-weight="800" '
             f'fill="{color}" font-family="Consolas, monospace">{{ }}</text>')
    s.append(f'<text x="{cx}" y="{cy + 9.0}" text-anchor="middle" font-size="2.3" font-weight="700" '
             f'letter-spacing="0.5" fill="{color}" font-family="Arial, sans-serif">TECHCOIN</text>')
    # ตัวเลขใหญ่กลาง
    s.append(f'<text x="{o + 56}" y="{cy + 6.4}" text-anchor="middle" font-size="{15 if v < 1000 else 13}" '
             f'font-weight="900" fill="{color}" font-family="Arial Black, Arial, sans-serif">{label(v)}</text>')
    s.append(f'<text x="{o + 56}" y="{o + 9.6}" text-anchor="middle" font-size="2.6" font-weight="700" '
             f'letter-spacing="1.1" fill="#E2E8F0" font-family="Arial, sans-serif">CODECOIN BANK</text>')
    s.append(f'<text x="{o + 56}" y="{o + H - 6.2}" text-anchor="middle" font-size="2.4" '
             f'fill="#94A3B8" font-family="Arial, sans-serif">VALID IN-GAME ONLY</text>')
    # เลขมุม
    for x, anchor in ((o + 5.2, "start"), (o + W - 3.2, "end")):
        s.append(f'<text x="{x}" y="{o + 8}" text-anchor="{anchor}" font-size="4" font-weight="800" '
                 f'fill="{"#E2E8F0" if anchor == "start" else color}" font-family="Arial, sans-serif">{label(v)}</text>')
        s.append(f'<text x="{x}" y="{o + H - 5}" text-anchor="{anchor}" font-size="4" font-weight="800" '
                 f'fill="{"#E2E8F0" if anchor == "start" else color}" font-family="Arial, sans-serif">{label(v)}</text>')
    # แถบขวา: ชิปเล็กจำนวนเท่าราคา + รหัสรุ่น
    s.append(f'<text transform="translate({o + W - 8},{cy}) rotate(-90)" text-anchor="middle" '
             f'font-size="3.2" font-weight="800" letter-spacing="1.4" fill="{color}" '
             f'font-family="Arial, sans-serif">CC-{v:04d}</text>')
    return _wrap("".join(s), f"TechCoin {label(v)} - front")


def back(v, color, dark, pins, seed):
    rnd = random.Random(seed + 77)
    o = BLEED
    cx, cy = o + W / 2, o + H / 2
    s = []
    s.append(f'<rect width="{CW}" height="{CH}" fill="{dark}" />')
    s.append(traces(rnd, color, o + 3, o + 3, o + W - 3, o + H - 3, 34))
    s.append(f'<rect x="{o + 2.2}" y="{o + 2.2}" width="{W - 4.4}" height="{H - 4.4}" rx="2.2" '
             f'fill="none" stroke="{color}" stroke-width="0.5" />')
    s.append(f'<rect x="{o + 3.4}" y="{o + 3.4}" width="{W - 6.8}" height="{H - 6.8}" rx="1.4" '
             f'fill="none" stroke="{color}" stroke-width="0.18" opacity="0.6" />')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="17.5" fill="{BOARD}" stroke="{color}" stroke-width="0.7" />')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="15.5" fill="none" stroke="{color}" stroke-width="0.22" '
             f'stroke-dasharray="0.9 0.9" />')
    s.append(chip(cx, cy - 3, 11.0, pins, color, DEEP))
    s.append(f'<text x="{cx}" y="{cy + 12}" text-anchor="middle" font-size="5.2" font-weight="900" '
             f'fill="{color}" font-family="Arial Black, Arial, sans-serif">{label(v)}</text>')
    s.append(f'<text x="{cx}" y="{cy - 1.6}" text-anchor="middle" font-size="3.4" font-weight="800" '
             f'fill="{color}" font-family="Consolas, monospace">{{ }}</text>')
    s.append(f'<text x="{o + 7}" y="{cy + 1.3}" text-anchor="start" font-size="3.4" font-weight="800" '
             f'letter-spacing="1.2" fill="#E2E8F0" font-family="Arial, sans-serif">TECH</text>')
    s.append(f'<text x="{o + W - 7}" y="{cy + 1.3}" text-anchor="end" font-size="3.4" font-weight="800" '
             f'letter-spacing="1.2" fill="#E2E8F0" font-family="Arial, sans-serif">COIN</text>')
    return _wrap("".join(s), f"TechCoin {label(v)} - back")


def _wrap(body, title):
    # clipPath ตัดที่ขอบ bleed; ไม่มีเส้นตัดในไฟล์ (ใช้ crop marks ในแผ่น sheet)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW}mm" height="{CH}mm" '
            f'viewBox="0 0 {CW} {CH}"><title>{title}</title>{body}</svg>\n')


def sheet(pages):
    """A4 แนวตั้ง 2 คอลัมน์ x 5 แถว = 10 ใบ/แผ่น (6 แถวสูงเกิน A4) พร้อม crop marks; หน้า-หลังแยกคนละหน้า"""
    css = (
        "@page{size:A4;margin:0}*{margin:0;padding:0;box-sizing:border-box}"
        "body{background:#444}"
        ".pg{width:210mm;height:297mm;background:#fff;position:relative;page-break-after:always;margin:0 auto 6mm}"
        ".n{position:absolute;width:101mm;height:51mm}.n img{width:101mm;height:51mm;display:block}"
        ".cm{position:absolute;background:#000}"
        ".cap{position:absolute;left:0;right:0;bottom:2mm;text-align:center;font:3mm Arial;color:#666}"
        "@media print{body{background:none}.pg{margin:0}}"
    )
    gx, gy = 4.0, 3.5      # ระยะขอบกระดาษถึงใบแรก (นับรวม bleed)
    html = [f'<!doctype html><meta charset="utf-8"><title>TechCoin banknotes - print sheets</title>'
            f'<style>{css}</style>']
    for title, files, mirror in pages:
        cells = []
        for r in range(5):
            for c in range(2):
                f = files[(r * 2 + c) % len(files)]
                col = (1 - c) if mirror else c      # หลังสลับซ้าย-ขวา ให้ตรงกับหน้า (พลิกด้านยาว)
                x = gx + col * 101
                y = gy + r * 51 + (r * 2.2)
                cells.append((x, y, f))
        marks = []
        for x, y, _ in cells:
            for dx, dy in ((BLEED, BLEED), (BLEED + W, BLEED), (BLEED, BLEED + H), (BLEED + W, BLEED + H)):
                px, py = x + dx, y + dy
                sx = -1 if dx == BLEED else 1
                sy = -1 if dy == BLEED else 1
                marks.append(f'<div class="cm" style="left:{px + (sx * 2.4 if sx > 0 else -2.4):.2f}mm;'
                             f'top:{py - 0.1:.2f}mm;width:2.4mm;height:0.2mm"></div>')
                marks.append(f'<div class="cm" style="left:{px - 0.1:.2f}mm;'
                             f'top:{py + (sy * 2.4 if sy > 0 else -2.4):.2f}mm;width:0.2mm;height:2.4mm"></div>')
        imgs = "".join(f'<div class="n" style="left:{x}mm;top:{y}mm"><img src="{f}"></div>' for x, y, f in cells)
        html.append(f'<div class="pg">{imgs}{"".join(marks)}<div class="cap">{title}</div></div>')
    return "".join(html)


def main():
    os.makedirs(OUT, exist_ok=True)
    pages = []
    for v, color, dark, pins, qty in NOTES:
        seed = v * 31 + 7
        for side, fn in (("front", front), ("back", back)):
            with open(os.path.join(OUT, f"techcoin_{v}_{side}.svg"), "w", encoding="utf-8") as f:
                f.write(fn(v, color, dark, pins, seed))
        pages.append((f"TechCoin {v} - FRONT (10-up)", [f"techcoin_{v}_front.svg"], False))
        pages.append((f"TechCoin {v} - BACK (10-up, flip on long edge)", [f"techcoin_{v}_back.svg"], True))
    with open(os.path.join(OUT, "print_sheets.html"), "w", encoding="utf-8") as f:
        f.write(sheet(pages))
    print("wrote", len(NOTES) * 2, "svg + print_sheets.html -> print/banknotes")
    print("suggested qty:", ", ".join(f"{v}x{q}" for v, _, _, _, q in NOTES), "= %d notes" % sum(n[4] for n in NOTES))


if __name__ == "__main__":
    main()
