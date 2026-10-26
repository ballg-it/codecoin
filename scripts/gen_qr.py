# -*- coding: utf-8 -*-
"""
gen_qr.py — สร้าง QR Code ทั้งชุดของ CodeCoin จาก data.json
ติดตั้งก่อนใช้:  pip install "qrcode[pil]"
รัน:            py scripts/gen_qr.py
ผลลัพธ์:        โฟลเดอร์ print/qr_output/ มี PNG ตั้งชื่อตาม space_id
"""
import json
import math
import os
import sys
from pathlib import Path

import qrcode

# console Windows บางเครื่องเป็น cp1252 — บังคับ UTF-8 ให้พิมพ์ภาษาไทยได้
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")
from qrcode.constants import ERROR_CORRECT_H

# ================== ตั้งค่าได้ที่นี่ที่เดียว ==================
BASE_URL = "https://ballg-it.github.io/codecoin"
ROOT = Path(__file__).resolve().parent.parent   # สคริปต์อยู่ scripts/ ข้อมูลอยู่รากโปรเจค
DATA_FILE = ROOT / "data.json"
OUT_DIR = ROOT / "print" / "qr_output"
TARGET_CM = 3.0    # ขนาดพิมพ์ ~3x3 ซม.
DPI = 300          # ความละเอียดพิมพ์
ZONES = ["coding", "design", "office", "hardware"]  # โซนเหตุการณ์ (ตายตัวตามกติกา)
# ============================================================

TARGET_PX = round(TARGET_CM / 2.54 * DPI)  # 3 ซม. @300DPI ≈ 354 px


def make_qr(url: str, path: str) -> int:
    """สร้าง QR หนึ่งใบ (error correction ระดับ H เผื่อพิมพ์บนการ์ด) คืนค่าขนาด px"""
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=4, box_size=1)
    qr.add_data(url)
    qr.make(fit=True)
    modules = qr.modules_count + qr.border * 2
    qr.box_size = max(1, math.ceil(TARGET_PX / modules))
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(path, dpi=(DPI, DPI))
    return img.size[0]


def main():
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # รายการ QR: ทุกช่องทรัพย์สินใน data.json + event 4 โซน + bugjam + cooling/debug_rescue
    space_ids = list(data["spaces"].keys())
    space_ids += [f"event_{z}" for z in ZONES]
    space_ids += ["bugjam", "cooling", "debug_rescue"]

    os.makedirs(OUT_DIR, exist_ok=True)
    for sid in space_ids:
        url = f"{BASE_URL}/?space={sid}"
        path = os.path.join(OUT_DIR, f"{sid}.png")
        px = make_qr(url, path)
        print(f"[OK] {sid:<18} {url}  ->  {path} ({px}px)")

    print(f"\nสร้างเสร็จ {len(space_ids)} ใบ ในโฟลเดอร์ {OUT_DIR}/")
    print(f"พิมพ์ที่ {DPI} DPI จะได้ขนาดประมาณ {TARGET_CM}x{TARGET_CM} ซม.")
    if "USERNAME" in BASE_URL:
        print("!! อย่าลืมแก้ BASE_URL บนหัวไฟล์เป็น URL จริงก่อนพิมพ์ใช้งาน")


if __name__ == "__main__":
    main()
