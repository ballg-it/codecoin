"""สร้างไฟล์ส่งพิมพ์การ์ดทรัพย์สินแนว TCG (กรอบ A2) -> print/cards_tcg/final/

ต้นฉบับ = print/cards_tcg/concept.html?print=1 (A4 แนวตั้ง 2 x 3 ใบ/หน้า · การ์ด 63 x 88 มม. + ตัดตก 3 มม. + เครื่องหมายตัด)
ได้ 3 ไฟล์: หน้า (3 หน้า) · หลัง (3 หน้า คอลัมน์สลับซ้าย-ขวา) · หน้า+หลัง (6 หน้า สลับกัน สำหรับพิมพ์สองหน้า กลับด้านขอบยาว)
ตัวหนังสือเป็นเวกเตอร์ ฝังฟอนต์ในไฟล์ (ไม่ได้แปลงเป็นเส้น — กรอบการ์ดใช้ clip-path / gradient ซึ่งขั้นแปลงเป็นเส้นของ MuPDF ทำพัง)

ตรวจก่อนเขียนไฟล์: ข้อมูลใน concept.html ตรง data.json · ฟอนต์ฝังครบไม่มีฟอนต์สำรอง · QR ทุกใบถอดรหัสได้ตรงกับ print/qr_output
· ตำแหน่งการ์ดหน้า-หลังทับกันเมื่อกลับด้านขอบยาว
ต้องมี: Edge, pymupdf, numpy, opencv-python, ต่อเน็ต (Sarabun / JetBrains Mono จาก Google Fonts), ฟอนต์ Kanit ในเครื่อง

รัน: py scripts/build_cards.py
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

import cv2
import fitz
import numpy as np

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "print" / "cards_tcg"
OUT = SRC / "final"
QR = ROOT / "print" / "qr_output"
EDGE = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
MM = 72 / 25.4
IDS = [f"{z}_0{i}" for z in ("coding", "office", "design", "hardware") for i in range(1, 5)]
GROUPS = [IDS[0:6], IDS[6:12], IDS[12:16]]
X0, Y0, CW, CH, BL = 36, 7.5, 69, 94, 3          # ต้องตรงกับค่าในโหมดพิมพ์ของ concept.html
FONT_OK = ("Kanit", "Sarabun", "JetBrainsMono")
FILES = {"front": "CodeCoin_การ์ดทรัพย์สิน_หน้า.pdf", "back": "CodeCoin_การ์ดทรัพย์สิน_หลัง.pdf",
         "duplex": "CodeCoin_การ์ดทรัพย์สิน_หน้า+หลัง.pdf"}


def check_data():
    """ข้อมูลการ์ดใน concept.html (const C) ต้องตรง data.json ทุกใบ"""
    sp = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))["spaces"]
    html = (SRC / "concept.html").read_text(encoding="utf-8")
    for cid in IDS:
        m = re.search(cid + r":\s*\{z:'(\w+)', n:(\d), name:'((?:[^'\\]|\\.)*)', price:(\d+), rent:\[([\d,]+)\], up:(\d+),", html)
        if not m:
            sys.exit(f"ไม่พบ {cid} ใน const C ของ concept.html")
        d = sp[cid]
        got = (m[1], m[3].replace("\\'", "'"), int(m[4]), [int(x) for x in m[5].split(",")], int(m[6]))
        want = (d["zone"], d["name_th"], d["price"], list(d["rent"]), d["upgrade_cost"])
        if got != want:
            sys.exit(f"{cid}: concept.html ไม่ตรง data.json\n  concept: {got}\n  data:    {want}")
        for f in (SRC / "img" / f"art_{cid}.jpg", QR / f"{cid}.png"):
            if not f.exists():
                sys.exit(f"ไม่พบไฟล์ {f}")
    print("[OK] ข้อมูล 16 ใบตรง data.json · ภาพประกอบและ QR ครบ")


def edge_pdf(pdf):
    exe = next((p for p in EDGE if os.path.exists(p)), None)
    if not exe:
        sys.exit("ไม่พบ Microsoft Edge")
    url = (SRC / "concept.html").as_uri() + "?print=1"
    subprocess.run([exe, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={pdf.parent / 'prof'}", "--virtual-time-budget=30000",
                    f"--print-to-pdf={pdf}", url], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    last, deadline = -1, time.time() + 120          # Edge คืน exit 0 ก่อนเขียนไฟล์เสร็จ
    while time.time() < deadline:
        size = pdf.stat().st_size if pdf.exists() else -1
        if size > 0 and size == last:
            return
        last = size
        time.sleep(1.5)
    sys.exit("Edge พิมพ์ PDF ไม่สำเร็จภายใน 120 วินาที")


def cell(k, back):
    """กรอบช่อง (รวมตัดตก) ของใบลำดับ k ในหน้า หน่วย มม."""
    col, row = (1 - k % 2 if back else k % 2), k // 2
    return X0 + CW * col, Y0 + CH * row


def check_pdf(doc):
    if doc.page_count != 6:
        sys.exit(f"ได้ {doc.page_count} หน้า (ต้องได้ 6)")
    for p in doc:
        if abs(p.rect.width - 210 * MM) > 1 or abs(p.rect.height - 297 * MM) > 1:
            sys.exit(f"หน้า {p.number + 1} ไม่ใช่ A4: {p.rect}")
    # Type3 (ไม่มีชื่อ) = ตัวอักษร mono บรรทัดรหัสใบ ที่ Edge ฝังเป็นรูปร่างตัวอักษรโดยตรง — พิมพ์ได้ ไม่ต้องมีฟอนต์
    allf = [f for p in doc for f in p.get_fonts() if f[2] != "Type3"]
    fonts = {f[3].split("+", 1)[-1] for f in allf}
    bad = sorted(n for n in fonts if not n.startswith(FONT_OK))
    if bad:
        sys.exit(f"มีฟอนต์สำรองหลุดเข้ามา {bad} — โหลด Google Fonts ไม่ทัน หรือมีอักขระที่ฟอนต์ไม่มี")
    loose = sorted({f[3] for f in allf if "+" not in f[3]})
    if loose:
        sys.exit(f"ฟอนต์ไม่ได้ฝังในไฟล์: {loose}")
    print(f"[OK] 6 หน้า A4 · ฟอนต์ฝังครบ {len(fonts)} ตัว: {', '.join(sorted(fonts))}")

    det = cv2.QRCodeDetector()
    for g, ids in enumerate(GROUPS):
        front, back = doc[g * 2], doc[g * 2 + 1]
        for k, cid in enumerate(ids):
            for page, is_back in ((front, False), (back, True)):
                x, y = cell(k, is_back)
                trim = fitz.Rect((x + BL) * MM, (y + BL) * MM, (x + CW - BL) * MM, (y + CH - BL) * MM)
                hits = page.search_for(cid, clip=trim)
                if len(hits) != 1:
                    sys.exit(f"{cid} {'หลัง' if is_back else 'หน้า'}: ไม่อยู่ในช่องที่ควรอยู่ (พบ {len(hits)})")
            # หน้า-หลังทับกันเมื่อกลับด้านขอบยาว: x ของช่องหน้า + x ของช่องหลัง + ความกว้างช่อง = ความกว้างกระดาษ
            if abs(cell(k, False)[0] + cell(k, True)[0] + CW - 210) > 1e-6:
                sys.exit(f"{cid}: ตำแหน่งหน้า-หลังไม่ทับกัน")
            x, y = cell(k, False)
            pix = front.get_pixmap(dpi=600, clip=fitz.Rect((x + BL) * MM, (y + BL + 40) * MM, (x + BL + 34) * MM, (y + CH - BL) * MM), alpha=False)
            arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
            txt = det.detectAndDecode(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))[0]
            src = cv2.imdecode(np.fromfile(str(QR / f"{cid}.png"), np.uint8), cv2.IMREAD_COLOR)
            src = cv2.copyMakeBorder(cv2.resize(src, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST), 60, 60, 60, 60, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            want = det.detectAndDecode(src)[0]
            if not txt or txt != want or cid not in txt:
                sys.exit(f"{cid}: QR บนการ์ดถอดรหัสได้ '{txt}' ไม่ตรงต้นฉบับ '{want}'")
    print("[OK] QR ครบ 16 ใบ ถอดรหัสจากไฟล์พิมพ์ที่ 600 dpi ได้ตรงต้นฉบับ · ตำแหน่งหน้า-หลังทับกัน")


def save(doc, pages, name):
    out = fitz.open()
    for i in pages:
        out.insert_pdf(doc, from_page=i, to_page=i)
    out.set_metadata({"title": name[:-4], "author": "CodeCoin", "creator": "scripts/build_cards.py"})
    out.save(OUT / name, garbage=4, deflate=True)
    print(f"[OK] {name}  {out.page_count} หน้า  {(OUT / name).stat().st_size / 1e6:.1f} MB")
    out.close()


def main():
    check_data()
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:      # พาธ ASCII — Edge เขียนลงพาธไทยไม่ได้ทุกครั้ง
        pdf = pathlib.Path(tmp) / "cards.pdf"
        edge_pdf(pdf)
        doc = fitz.open(pdf)
        check_pdf(doc)
        save(doc, [0, 2, 4], FILES["front"])
        save(doc, [1, 3, 5], FILES["back"])
        save(doc, range(6), FILES["duplex"])
        for i, n in ((0, "preview_front_1.png"), (1, "preview_back_1.png")):
            doc[i].get_pixmap(dpi=110).save(OUT / n)
        doc.close()


if __name__ == "__main__":
    main()
