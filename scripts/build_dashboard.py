#!/usr/bin/env python3
"""สร้าง tools/dashboard.html — แดชบอร์ดสถานะโปรเจค CodeCoin (ไฟล์เดียว เปิดดับเบิลคลิกได้)

อ่านจาก data.json, sw.js, index.html, print/qr_output, git log แล้วฝังเป็น JSON ในหน้า
รัน: py scripts/build_dashboard.py  (รันซ้ำทุกครั้งที่ข้อมูลเปลี่ยนเพื่ออัปเดตตัวเลข)
"""
import json, re, subprocess, datetime, sys
from collections import Counter
from pathlib import Path

# console Windows (cp1252) พิมพ์ภาษาไทยไม่ได้ — เขียนไฟล์เสร็จแล้วแต่จบด้วย traceback (เหมือนสคริปต์ตัวอื่นที่แก้ไปแล้ว)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
ZONES = ["coding", "office", "design", "hardware"]
ZONE_TH = {"coding": "Coding", "office": "Office", "design": "Design", "hardware": "Hardware"}

# งานค้าง — แก้ตรงนี้เมื่อสถานะเปลี่ยน (ต้นทาง: memory/docs/BOX_DEMO.md)
BACKLOG = [
    {"id": "D", "title": "งานกล่อง/สิ่งพิมพ์ 14 ข้อ (docs/BOX_DEMO.md)", "level": "block",
     "note": "ตัวบล็อกส่งโรงพิมพ์: เลขจำนวนคำถาม 3 แผงไม่ตรง, ถาดไม่ลงช่อง, คู่มือ A4 ล้นกล่อง, ยังไม่มีโทเค็น/คลิป (ธนบัตรเสร็จแล้ว)"},
    {"id": "B", "title": "Stage V4 — เก็บ 🟡 จาก design audit", "level": "mid",
     "note": "duration 6 จุดเข้า motion token, ปุ่มลอย 44→48px, fx เข้า token"},
    {"id": "C", "title": "Motion Stage 5 — วัด fps Roulette บนมือถือจริง", "level": "mid",
     "note": "โค้ดยืนยันแล้ว เหลือวัดบนเครื่องจริง"},
    {"id": "A", "title": "เก็บสถิติผ่าน Apps Script (optional)", "level": "low",
     "note": "มี hook CONFIG.log_url รอไว้ใน index.html"},
]


def build_progress(t, log_ready):
    """ความคืบหน้าแยกหัวข้อ — น้ำหนักเท่ากันทุกรายการ (1 รายการเสร็จ = 1 หน่วย)
    รายการที่ผูกกับตัวเลขจริงใน data.json คำนวณอัตโนมัติ ที่เหลือแก้มือตรงนี้เมื่อสถานะเปลี่ยน
    (ต้นทาง: docs/PROJECT_SUMMARY.md หัวข้อ 'งานที่เหลือ' + docs/BOX_DEMO.md หัวข้อ 5)"""
    T = lambda label, done: {"label": label, "done": bool(done)}
    sections = [
        ("เนื้อหาเกม", "ข้อมูลช่อง คำถาม events Bug Jam", [
            T("16 ช่องทรัพย์สิน ครบ 4 โซน", t["spaces"] == 16),
            T("คำถาม 81 ข้อ (L1–L4 ทุกช่อง)", t["questions"] >= 81),
            T("Events 20 ใบ (โซนละ 5)", t["events"] >= 20),
            T("Bug Jam 19 โจทย์", t["bugjam"] >= 19),
            T("review hint Bug Jam hard 4 ข้อ (bug_16–19 มี hint ครบ ตรวจแล้ว)", True),
            T("แก้ Excel ต้นทาง (คอลัมน์ hint + office_02_L1_01 เก็บเป็นข้อความถูกต้อง)", True),
        ]),
        ("เว็บเกม (ฟีเจอร์)", "index.html + GitHub Pages", [
            T("ระบบหลัก: ซื้อ / อัปเกรด / ค่าเช่า ผ่าน QR", True),
            T("ควิซเดิมพัน + เสียง + visual effect", True),
            T("Fail Roulette (เดิมพันมั่นใจแล้วตอบผิด)", True),
            T("Bug Jam (ระดับง่าย/ยาก, ค่าปรับ, สลับตัวเลือก)", True),
            T("Event แข่งตอบเร็ว (speed)", True),
            T("Debug Rescue 2 เครื่อง — pattern wire_cut", True),
            T("Debug Rescue อีก 3 pattern (keypad / command_match / final_boss)", True),
            T("Debug Rescue ห้องรอ + QR เริ่มพร้อมกัน", True),
            T("รอบ debug เว็บเกม 20 ต.ค. (5 บั๊ก + ปิดช่องโหว่ reroll 2 จุด, CACHE v24)", True),
            T("Cooling Zone บอสไฟต์ทั้งวง", True),
            T("รองรับสถานการณ์จริงในห้องเรียน (REV 2.2)", True),
            T("Deploy ขึ้นเว็บจริง + PWA/Service Worker", True),
            T("ทดสอบห้องรอ Debug Rescue บนมือถือ 2 เครื่องจริง (ผ่าน 21 ต.ค.)", True),
            T("กู้ระบบขั้นสุด: ล็อกครั้งเดียว/เกมด้วยการ์ดจริง (CACHE v25)", True),
            T("กำหนดจุดบนกระดานที่สั่งเล่น Debug Rescue ด่านอื่น", False),
        ]),
        ("ดีไซน์ & Motion", "UI, animation, design audit", [
            T("Motion Stage 1–2: token + วงแหวนเวลา + screen enter", True),
            T("Motion Stage 3: feedback ตอบถูก/ผิด + renderToken", True),
            T("Motion Stage 4: roulette / boss shake / การ์ดพลิก / HP", True),
            T("Design Stage V0–V1: ตรวจสภาพ + CSS color token", True),
            T("Design Stage V2–V3b: แก้ล้นจอมือถือ + แยกความหมายสีแดง", True),
            T("Motion Stage 5: วัด fps Roulette บนมือถือจริง", False),
            T("Design Stage V4: duration / ปุ่มลอย 48px / fx เข้า token", False),
        ]),
        ("สื่อสิ่งพิมพ์", "กระดาน การ์ด QR คู่มือ", [
            T("กระดานเกม 50×50 (PDF final)", True),
            T("กระดานพร้อมส่งพิมพ์ (trim/bleed + crop marks)", True),
            T("การ์ดทรัพย์สิน 16 ใบ หน้า-หลัง", True),
            T("QR ครบ 23 จุด", t["qr"] >= 23),
            T("ตรวจ QR บนกระดาน (6 ใบ)", True),
            T("เขียนคู่มือกติกา ส่วนจุดพักเครื่อง (Server Meltdown) ใหม่", False),
            T("เขียนคู่มือกติกา ส่วนการ์ดกู้ระบบขั้นสุด", False),
            T("สั่งพิมพ์จริง (Scale 100%)", False),
        ]),
        ("กล่องเกม", "เดโม 3 มิติ + งานพิมพ์กล่อง", [
            T("เดโมกล่อง 3 มิติ (v4 + standalone)", True),
            T("ข้อมูลไม่ตรงกันระหว่างแผง 5 ข้อ (จำนวนคำถาม/เวลา/รหัสรุ่น/การ์ดเหตุการณ์/คลิป)", False),
            T("ของไม่ลงช่อง 4 ข้อ (ถาดการ์ด/ธนบัตร/คลิป/คู่มือ A5)", False),
            T("งานพิมพ์ 3 ข้อ (เส้นชมพู/ข้อความสัน/สันซ้ำ+รูสกรู)", False),
            T("ออกแบบธนบัตร TechCoin 5 ราคา (print/banknotes)", True),
            T("ออกแบบการ์ดกู้ระบบขั้นสุด (print/final_boss_card)", True),
            T("ออกแบบโทเค็นผู้เล่น 4 ตัว", False),
            T("ออกแบบคลิปอัปเกรด 24 ตัว", False),
        ]),
        ("เก็บสถิติ (บทที่ 4)", "ระบบ log การตอบ", [
            T("ฝั่งเว็บ: Logger + คิว + retry (REV 2.5)", True),
            T("เขียน Apps Script รับ POST + deploy", False),
            T("ใส่ URL ลง CONFIG.log_url", log_ready),
            T("ทดลองเก็บจริง 1 คาบ", False),
        ]),
    ]
    out, dn, tot = [], 0, 0
    for name, sub, items in sections:
        d = sum(i["done"] for i in items)
        out.append({"name": name, "sub": sub, "items": items, "done": d, "total": len(items),
                    "pct": round(d / len(items) * 100)})
        dn += d; tot += len(items)
    return {"sections": out, "done": dn, "total": tot, "pct": round(dn / tot * 100),
            "avg_pct": round(sum(s["pct"] for s in out) / len(out))}


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", check=True).stdout.strip()
    except Exception:
        return ""


def main():
    d = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    spaces, qs, evs, bugs = d["spaces"], d["questions"], d["events"], d["bugjam"]

    # คำถามต่อโซน × ระดับ
    sp_zone = {k: v["zone"] for k, v in spaces.items()}
    levels = sorted({q["level"] for q in qs})
    matrix = {z: {str(l): 0 for l in levels} for z in ZONES}
    for q in qs:
        matrix[sp_zone[q["space_id"]]][str(q["level"])] += 1

    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    cache = re.search(r'codecoin-v(\d+)', sw)
    rev = re.search(r'REV\s*([0-9.]+)', html)

    commits = []
    for line in git("log", "-8", "--pretty=%h\t%ad\t%s", "--date=short").splitlines():
        h, dt, s = line.split("\t", 2)
        commits.append({"hash": h, "date": dt, "subject": s})

    out = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "site": "https://ballgamerzaman-code.github.io/codecoin/",
        "rev": rev.group(1) if rev else "?",
        "cache": int(cache.group(1)) if cache else None,
        "zones": [{"id": z, "name": ZONE_TH[z]} for z in ZONES],
        "levels": [str(l) for l in levels],
        "totals": {
            "spaces": len(spaces), "questions": len(qs), "events": len(evs), "bugjam": len(bugs),
            "qr": len(list((ROOT / "print" / "qr_output").glob("*.png"))),
        },
        "matrix": matrix,
        "spaces": [{"id": k, "zone": v["zone"], "name": v["name_th"], "price": v["price"],
                    "rent": v["rent"], "upgrade": v["upgrade_cost"]} for k, v in spaces.items()],
        "events": {z: dict(Counter(e["mechanic"] for e in evs if e["zone"] == z)) for z in ZONES},
        "bugjam": dict(Counter(b.get("difficulty", "?") for b in bugs)),
        "log_ready": bool(re.search(r'log_url:\s*"https?://', html)),
        "progress": None,
        "backlog": BACKLOG,
        "commits": commits,
    }
    out["progress"] = build_progress(out["totals"], out["log_ready"])
    tpl = (ROOT / "scripts" / "dashboard_template.html").read_text(encoding="utf-8")
    page = tpl.replace("/*__DATA__*/null", json.dumps(out, ensure_ascii=False))
    dest = ROOT / "tools" / "dashboard.html"
    dest.write_text(page, encoding="utf-8")
    print(f"เขียน {dest} ({len(page)//1024} KB) — คำถาม {len(qs)}, events {len(evs)}, bugjam {len(bugs)}")


if __name__ == "__main__":
    main()
