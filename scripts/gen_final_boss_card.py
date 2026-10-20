#!/usr/bin/env python3
"""สร้างการ์ด "กู้ระบบขั้นสุด" (Final Boss) -> print/final_boss_card/

การ์ดใบนี้คือ "ตัวล็อกครั้งเดียวต่อเกม" ของด่าน final_boss ใน Debug Rescue:
เว็บไม่มี backend จึงรู้ไม่ได้ว่าโต๊ะนี้ใช้ด่านนี้ไปแล้วหรือยัง -> ใช้ของจริงบนโต๊ะแทน
(Banker ถือไว้ 1 ใบต่อเกม ใครจะเล่นต้องขอ+จ่ายค่าเข้า จบแล้วคืนลงกล่อง)

ขนาดเท่าการ์ดทรัพย์สิน 63 x 88 มม. + bleed 3 มม. รอบด้าน (ผืน 69 x 94 มม.)
ตัวเลขกติกา (ค่าเข้า/รางวัล/โทษ/รอบ/เวลา) อ่านจาก CONFIG ใน index.html เสมอ
-> แก้ตัวเลขที่ index.html แล้วรันสคริปต์นี้ใหม่ การ์ดกับเว็บจะตรงกันเอง
ข้อความเป็นฟอนต์ระบบ — ก่อนส่งโรงพิมพ์ให้เปิดใน Illustrator/Inkscape แล้ว Create Outlines

รัน: py scripts/gen_final_boss_card.py   (ต้องมี qrcode: pip install "qrcode[pil]")
"""
import os
import random
import re
import sys

import qrcode

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "print", "final_boss_card")
BASE_URL = "https://ballgamerzaman-code.github.io/codecoin"   # เดียวกับ scripts/gen_qr.py
QR_URL = f"{BASE_URL}/?space=debug_rescue&pattern=final_boss"  # เปิดหน้าเลือกด่านโดยเลือก final_boss ไว้ให้

W, H, BLEED = 63.0, 88.0, 3.0
CW, CH = W + 2 * BLEED, H + 2 * BLEED

BOARD, DEEP = "#0B2B22", "#05100C"
GOLD, GREEN, INK, MUTED = "#FBBF24", "#4ADE80", "#E2E8F0", "#94A3B8"
FONT = "Kanit, 'Noto Sans Thai', 'Leelawadee UI', Tahoma, sans-serif"


def read_config():
    """ดึงค่า final_boss จาก CONFIG ใน index.html — หาไม่เจอ = หยุดเลย ดีกว่าพิมพ์การ์ดตัวเลขผิด"""
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    m = re.search(r'\{\s*id:\s*"final_boss".*?\}', html, re.S)
    if not m:
        sys.exit("หา pattern final_boss ใน CONFIG ของ index.html ไม่เจอ")
    block = m.group(0)

    def num(key):
        v = re.search(rf"\b{key}:\s*(\d+)", block)
        if not v:
            sys.exit(f"final_boss ไม่มีค่า {key} ใน CONFIG")
        return int(v.group(1))

    rounds = re.search(r'unlock_rounds:\s*"([^"]+)"', block)
    name = re.search(r'name:\s*"([^"]+)"', block)
    return {
        "name": name.group(1) if name else "กู้ระบบขั้นสุด",
        "time": num("time_limit"), "reward": num("reward"), "penalty": num("penalty"),
        "fee": num("entry_fee"), "max": num("max_players"),
        "rounds": rounds.group(1) if rounds else "10–12",
    }


def traces(rnd, color, x0, y0, x1, y1, n, opacity=0.3):
    """ลายวงจร PCB แบบเดียวกับธนบัตร (seed คงที่ พิมพ์ซ้ำได้ผลเดิม)"""
    out = []
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        pts = [(x, y)]
        for _ in range(rnd.randint(2, 4)):
            dx = rnd.choice([-1, 0, 1]) * rnd.uniform(2, 6)
            dy = rnd.choice([-1, 0, 1]) * rnd.uniform(2, 6)
            if dx == 0 and dy == 0:
                dx = 4
            x, y = min(max(x + dx, x0), x1), min(max(y + dy, y0), y1)
            pts.append((x, y))
        out.append('<path d="M' + " L".join(f"{px:.2f} {py:.2f}" for px, py in pts) + '" />')
        out.append(f'<circle cx="{pts[-1][0]:.2f}" cy="{pts[-1][1]:.2f}" r="0.5" />')
    return (f'<g fill="none" stroke="{color}" stroke-width="0.25" stroke-linejoin="round" '
            f'opacity="{opacity}">' + "".join(out) + "</g>")


def qr_path(data, x, y, size):
    """QR เป็น path เดียว (เวกเตอร์ล้วน คมทุกขนาด) — error correction H เหมือน QR ชุดหลัก"""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=0)
    qr.add_data(data)
    qr.make(fit=True)
    m = qr.get_matrix()
    n = len(m)
    cell = size / n
    d = []
    for r, row in enumerate(m):
        for c, on in enumerate(row):
            if on:
                d.append(f"M{x + c * cell:.3f} {y + r * cell:.3f}h{cell:.3f}v{cell:.3f}h-{cell:.3f}z")
    return f'<path d="{"".join(d)}" fill="{DEEP}" />', n


def frame():
    o = BLEED
    return (f'<rect x="{o + 2.4}" y="{o + 2.4}" width="{W - 4.8}" height="{H - 4.8}" rx="3" '
            f'fill="none" stroke="{GOLD}" stroke-width="0.55" />'
            f'<rect x="{o + 3.6}" y="{o + 3.6}" width="{W - 7.2}" height="{H - 7.2}" rx="2.2" '
            f'fill="none" stroke="{GOLD}" stroke-width="0.18" opacity="0.6" />')


def text(x, y, s, size, color, weight=400, anchor="middle", spacing=0):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" font-family="{FONT}"{ls}>{s}</text>')


def front(cfg):
    rnd = random.Random(4242)
    o, cx = BLEED, CW / 2
    s = [f'<rect width="{CW}" height="{CH}" fill="{BOARD}" />',
         traces(rnd, GREEN, o + 4, o + 4, o + W - 4, o + H - 4, 26), frame()]
    # แถบหัว
    s.append(f'<rect x="{o + 6}" y="{o + 6.5}" width="{W - 12}" height="21" rx="2.4" fill="{DEEP}" '
             f'stroke="{GOLD}" stroke-width="0.35" />')
    s.append(text(cx, o + 11.2, "การ์ดพิเศษ · 1 ใบต่อเกม", 2.5, GOLD, 600, spacing=0.3))
    s.append(text(cx, o + 19.4, cfg["name"], 6.4, GOLD, 800))
    s.append(text(cx, o + 24.6, "FINAL BOSS · DEBUG RESCUE", 2.4, GREEN, 700, spacing=0.6))
    # QR บนพื้นขาว (ขอบขาว quiet zone ≥ 2 โมดูล)
    qs, qy = 30.0, o + 32.5
    qx = cx - qs / 2
    qr, n = qr_path(QR_URL, qx, qy, qs)
    pad = max(2.2, 2.5 * qs / n)
    s.append(f'<rect x="{qx - pad:.2f}" y="{qy - pad:.2f}" width="{qs + 2 * pad:.2f}" height="{qs + 2 * pad:.2f}" '
             f'rx="2" fill="#FFFFFF" stroke="{GOLD}" stroke-width="0.5" />')
    s.append(qr)
    s.append(text(cx, qy + qs + pad + 4.4, "จ่ายค่าเข้าให้ Banker แล้วค่อยสแกน", 2.6, INK, 500))
    # แถบรางวัล
    py = o + H - 17.5
    s.append(f'<rect x="{o + 7}" y="{py}" width="{W - 14}" height="9.6" rx="4.8" fill="{DEEP}" '
             f'stroke="{GOLD}" stroke-width="0.45" />')
    s.append(text(cx, py + 4.1, f"สำเร็จ +{cfg['reward']:,}  ·  พลาด −{cfg['penalty']:,}", 3.1, GOLD, 700))
    s.append(text(cx, py + 7.6, "ต่อคนในทีม (TechCoin)", 2.1, MUTED, 400))
    s.append(f'<text x="{cx}" y="{o + H - 4.6}" text-anchor="middle" font-size="1.9" fill="{MUTED}" '
             f'font-family="Consolas, monospace" opacity="0.8">final_boss</text>')
    return _wrap("".join(s), "Final Boss card - front")


def back(cfg):
    rnd = random.Random(777)
    o, cx = BLEED, CW / 2
    s = [f'<rect width="{CW}" height="{CH}" fill="{DEEP}" />',
         traces(rnd, GOLD, o + 4, o + 4, o + W - 4, o + H - 4, 18, 0.18), frame()]
    s.append(text(cx, o + 12.5, "วิธีใช้การ์ด", 5.2, GOLD, 800))
    s.append(text(cx, o + 17.2, f"เก็บไว้ที่ Banker ตั้งแต่เริ่มเกม", 2.4, MUTED, 400))
    team = f"1–{cfg['max'] - 1}" if cfg["max"] > 2 else "1"
    steps = [
        ("ขอได้เฉพาะช่วง Crash Round", f"(รอบ {cfg['rounds']}) ในตาของตัวเอง"),
        (f"จ่ายค่าเข้า {cfg['fee']:,} TechCoin", "ให้ Banker (คนขอจ่ายคนเดียว)"),
        (f"เลือกเพื่อนร่วมทีม {team} คน", "แล้วสแกน QR ด้านหน้า"),
        ("ผ่าน 2 ด่านติดกันใน " + f"{cfg['time']} วินาที", "ตัดสายไฟ → ป้อนรหัสคีย์แพด"),
        (f"สำเร็จ: ทีมได้คนละ {cfg['reward']:,}", f"พลาด: เสียคนละ {cfg['penalty']:,}"),
        ("จบแล้วคืนการ์ดลงกล่อง", "ใช้ได้ครั้งเดียวต่อเกม"),
    ]
    y = o + 24.5
    for i, (a, b) in enumerate(steps, 1):
        s.append(f'<circle cx="{o + 9.4}" cy="{y - 1.1}" r="2.3" fill="{BOARD}" stroke="{GOLD}" stroke-width="0.4" />')
        s.append(text(o + 9.4, y + 0.05, str(i), 2.6, GOLD, 800))
        s.append(text(o + 13.4, y, a, 2.75, INK, 600, anchor="start"))
        s.append(text(o + 13.4, y + 3.6, b, 2.3, MUTED, 400, anchor="start"))
        y += 9.6
    s.append(f'<line x1="{o + 8}" y1="{o + H - 9.5}" x2="{o + W - 8}" y2="{o + H - 9.5}" stroke="{GOLD}" '
             f'stroke-width="0.2" opacity="0.6" />')
    s.append(text(cx, o + H - 5.6, "CodeCoin · Debug Rescue", 2.2, MUTED, 500, spacing=0.3))
    return _wrap("".join(s), "Final Boss card - back")


def _wrap(body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW}mm" height="{CH}mm" '
            f'viewBox="0 0 {CW} {CH}"><title>{title}</title>{body}</svg>\n')


def sheet():
    """A4 แนวตั้ง 2x2 = 4 ใบ/แผ่น (ใช้ 1 ใบต่อชุดเกม ที่เหลือเป็นสำรอง/ชุดอื่น) + crop marks
    หน้าหลังวางตำแหน่งเดียวกันแบบสมมาตรซ้าย-ขวา -> พิมพ์ 2 หน้า flip on long edge แล้วตรงกัน"""
    gap = 8.0
    gx = (210 - (2 * CW + gap)) / 2
    gy = (297 - (2 * CH + gap)) / 2
    css = ("@page{size:A4;margin:0}*{margin:0;padding:0;box-sizing:border-box}body{background:#444}"
           ".pg{width:210mm;height:297mm;background:#fff;position:relative;page-break-after:always;margin:0 auto 6mm}"
           f".c{{position:absolute;width:{CW}mm;height:{CH}mm}}.c img{{width:{CW}mm;height:{CH}mm;display:block}}"
           ".cm{position:absolute;background:#000}"
           ".cap{position:absolute;left:0;right:0;bottom:4mm;text-align:center;font:3mm Arial;color:#666}"
           "@media print{body{background:none}.pg{margin:0}}")
    html = ['<!doctype html><meta charset="utf-8"><title>Final Boss card - print sheets</title>'
            f'<style>{css}</style>']
    for title, f in (("FINAL BOSS card - FRONT (4-up)", "final_boss_front.svg"),
                     ("FINAL BOSS card - BACK (4-up, flip on long edge)", "final_boss_back.svg")):
        cells = [(gx + c * (CW + gap), gy + r * (CH + gap)) for r in range(2) for c in range(2)]
        marks = []
        for x, y in cells:
            for dx, dy in ((BLEED, BLEED), (BLEED + W, BLEED), (BLEED, BLEED + H), (BLEED + W, BLEED + H)):
                px, py = x + dx, y + dy
                sx = 1 if dx > BLEED else -1
                sy = 1 if dy > BLEED else -1
                # เส้นยาว 2.4 มม. ชี้ออกนอกการ์ด อยู่ในเขต bleed/ช่องว่าง ไม่ทับเนื้อการ์ด
                marks.append(f'<div class="cm" style="left:{px + (0.6 if sx > 0 else -3.0):.2f}mm;top:{py - 0.1:.2f}mm;'
                             'width:2.4mm;height:0.2mm"></div>')
                marks.append(f'<div class="cm" style="left:{px - 0.1:.2f}mm;top:{py + (0.6 if sy > 0 else -3.0):.2f}mm;'
                             'width:0.2mm;height:2.4mm"></div>')
        imgs = "".join(f'<div class="c" style="left:{x:.2f}mm;top:{y:.2f}mm"><img src="{f}"></div>' for x, y in cells)
        html.append(f'<div class="pg">{imgs}{"".join(marks)}<div class="cap">{title} · Scale 100% / Actual size</div></div>')
    return "".join(html)


def main():
    cfg = read_config()
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("final_boss_front.svg", front), ("final_boss_back.svg", back)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(fn(cfg))
    with open(os.path.join(OUT, "print_sheet.html"), "w", encoding="utf-8") as f:
        f.write(sheet())
    print(f"เขียน 2 svg + print_sheet.html -> print/final_boss_card  (QR: {QR_URL})")
    print(f"ค่าจาก CONFIG: ค่าเข้า {cfg['fee']} · รางวัล {cfg['reward']} · โทษ {cfg['penalty']} · "
          f"รอบ {cfg['rounds']} · {cfg['time']} วิ · สูงสุด {cfg['max']} คน")


if __name__ == "__main__":
    main()
