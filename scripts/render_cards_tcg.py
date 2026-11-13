"""เรนเดอร์ต้นแบบการ์ดแนว TCG -> print/cards_tcg/concept_*.png

ต้นฉบับ = print/cards_tcg/concept.html (เปิดด้วย ?sheet=1…13) — ต้นแบบเพื่อเลือกแนวทาง ยังไม่ใช่ไฟล์ส่งพิมพ์
วิธี: Edge headless พิมพ์ PDF (ขนาดหน้า = @page ที่ JS ท้าย concept.html ใส่ตามจำนวนแถว) แล้ว PyMuPDF แปลงเป็น PNG 192 dpi (= 2x)
ต้องต่อเน็ต (Sarabun / JetBrains Mono โหลดจาก Google Fonts; Kanit มีในเครื่อง)

รัน: py scripts/render_cards_tcg.py [เลขแผ่น ...]     (ไม่ใส่ = ทุกแผ่น)
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import time

import fitz

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "print" / "cards_tcg"
EDGE = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
SHEETS = [("1", "concept_1_directions.png"), ("2", "concept_2_zones.png"), ("3", "concept_3_backs.png"),
          ("4", "concept_4_A_variants.png"), ("5", "concept_5_B_variants.png"), ("6", "concept_6_AB_zones.png"),
          ("7", "concept_7_artstyles.png"), ("8", "concept_8_art_designs.png"), ("9", "concept_9_artstyles_zones.png"),
          ("10", "concept_10_action.png"), ("11", "concept_11_rich.png"), ("12", "concept_12_items.png"),
          ("13", "concept_13_all16.png")]


def main():
    exe = next((p for p in EDGE if os.path.exists(p)), None)
    if not exe:
        sys.exit("ไม่พบ Microsoft Edge")
    only = sys.argv[1:]
    for sheet, name in [x for x in SHEETS if not only or x[0] in only]:
        # โปรไฟล์ + PDF อยู่ใน temp (พาธ ASCII) — Edge เขียนไฟล์ลงพาธภาษาไทยไม่ได้ทุกครั้ง
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            pdf = pathlib.Path(tmp) / "sheet.pdf"
            url = (OUT / "concept.html").as_uri() + "?sheet=" + sheet
            subprocess.run([exe, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                            f"--user-data-dir={pathlib.Path(tmp) / 'prof'}", "--virtual-time-budget=20000",
                            f"--print-to-pdf={pdf}", url],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Edge คืน exit 0 ก่อนเขียนไฟล์เสร็จ ต้องรอจนขนาดไฟล์นิ่ง
            last, deadline = -1, time.time() + 90
            while time.time() < deadline:
                size = pdf.stat().st_size if pdf.exists() else -1
                if size > 0 and size == last:
                    break
                last = size
                time.sleep(1)
            else:
                sys.exit(f"Edge พิมพ์แผ่น {sheet} ไม่สำเร็จภายใน 90 วินาที")
            doc = fitz.open(pdf)
            if doc.page_count != 1:
                sys.exit(f"แผ่น {sheet} ล้นเป็น {doc.page_count} หน้า — เพิ่มความสูงหน้าใน JS ท้าย concept.html")
            pm = doc[0].get_pixmap(dpi=192)
            pm.save(OUT / name)
            doc.close()
            print(f"[OK] {name} {pm.width}x{pm.height}")


if __name__ == "__main__":
    main()
