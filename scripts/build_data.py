# -*- coding: utf-8 -*-
"""
build_data.py — แปลงฐานข้อมูล Excel ของทีม content เป็น data.json ให้เว็บใช้
ติดตั้งก่อนใช้:  pip install pandas openpyxl
รัน:            py scripts/build_data.py [path ไฟล์ .xlsx]
ถ้าไม่ระบุ path จะใช้ codecoin_database.xlsx ที่รากโปรเจค

โครงสร้าง Excel (หัวตารางจริงอยู่แถวที่ 2 — แถวแรกเป็นหมายเหตุ):
  spaces:    space_id, zone, name_th, price, rent_L0..rent_L3, upgrade_cost, content_th
  questions: question_id, space_id, level, question_th, choice_a..d, answer(a-d), time_limit,
             qtype, asset, payload   ← 3 คอลัมน์หลังเป็นของคำถามแบบ "ชี้" (ว่าง = ตัวเลือกแบบเดิม)
  events:    event_id, zone, mechanic, title_th, description_th, effect, weight
  bugjam:    bug_id, code_snippet, question_th, choice_a..c, answer(a-c), time_limit

คำถามแบบ "ชี้" — ความหมายของ answer/asset/payload ต่างกันตาม qtype:
  hotspot     answer='x,y,r' (เปอร์เซ็นต์) · asset=ชื่อภาพ · payload=ชื่อชิ้นส่วน (ใช้เฉลย)
  colorwheel  answer=องศา 0-359 · asset='wheel:<สีโจทย์>' · payload=ระยะผ่อนผัน (องศา)
  linepick    answer=เลขบรรทัดที่ผิด (เริ่ม 1) · payload=โค้ดหลายบรรทัด
ทั้งสามแบบต้องเว้น choice_a-d ว่าง — ถ้าผิดกติกา สคริปต์จะ error ไม่เขียน data.json
"""
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

# สคริปต์อยู่ใน scripts/ แต่ไฟล์ข้อมูลอยู่ที่รากโปรเจค — อ้างจาก __file__ เสมอ
# จะได้รันจากโฟลเดอร์ไหนก็ได้ ไม่ต้องระวังว่า cwd อยู่ตรงไหน
ROOT = Path(__file__).resolve().parent.parent
XLSX_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "codecoin_database.xlsx"
OUT_FILE = ROOT / "data.json"
ANSWER_INDEX = {"a": 0, "b": 1, "c": 2, "d": 3}
POINT_QTYPES = ("hotspot", "colorwheel", "linepick")   # กลุ่มคำถามที่ตอบด้วยการชี้ตำแหน่ง
HOTSPOT_RE = re.compile(r"^\d{1,3},\d{1,3},\d{1,3}$")


def cell(v, default=""):
    """NaN → ค่า default"""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default
    return v


def as_int(v, default=0):
    v = cell(v, default)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def choices_of(row, letters):
    """รวม choice_a..d เฉพาะช่องที่มีข้อมูล คืน (รายการตัวเลือก, ตำแหน่งใหม่ของแต่ละตัวอักษร)
    ตัวอย่าง: choice_b ว่าง → letter_index ของ 'c' จะเลื่อนมาเป็น 1 ให้เฉลยไม่เพี้ยน"""
    out, letter_index = [], {}
    for c in letters:
        v = str(cell(row.get(f"choice_{c}"))).strip()
        if v and v.lower() != "nan":
            letter_index[c] = len(out)
            out.append(v)
    return out, letter_index


def as_text(v, default=""):
    """คืนข้อความที่ตัดช่องว่างแล้ว — เลขที่ Excel เก็บเป็น float (225.0) คืนเป็น '225'"""
    v = cell(v, default)
    if isinstance(v, float) and not math.isnan(v) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def as_int_or_none(s):
    try:
        return int(str(s).strip())
    except (TypeError, ValueError):
        return None


def fix_newlines(s):
    """Excel บางเครื่องพิมพ์ \\n เป็นตัวอักษร — แปลงเป็นขึ้นบรรทัดจริง"""
    return str(s).replace("\\n", "\n")


def main():
    xl = pd.ExcelFile(XLSX_FILE)
    warns = []

    # ---------- spaces ----------
    df = xl.parse("spaces", header=1)
    spaces = {}
    for _, r in df.iterrows():
        sid = str(cell(r["space_id"])).strip()
        if not sid:
            continue
        spaces[sid] = {
            "zone": str(cell(r["zone"])).strip(),
            "name_th": str(cell(r["name_th"])).strip(),
            "price": as_int(r["price"]),
            "rent": [as_int(r[f"rent_L{i}"]) for i in range(4)],
            "upgrade_cost": as_int(r["upgrade_cost"]),
            "content_th": str(cell(r["content_th"])).strip(),
        }

    # ---------- questions ----------
    df = xl.parse("questions", header=1)
    questions = []
    errors = []   # ต่างจาก warns: มี error = ไม่เขียน data.json เลย (กันข้อมูลเพี้ยนหลุดขึ้นเว็บ)
    for _, r in df.iterrows():
        qth = str(cell(r["question_th"])).strip()
        if not qth:
            continue
        qid = as_text(r["question_id"])
        ans = as_text(r["answer"])
        is_draft = qth.startswith("DRAFT") or qid.startswith("DRAFT")
        sid = str(cell(r["space_id"])).strip()
        if not is_draft and sid not in spaces:
            warns.append(f"questions: {qid} อ้าง space_id '{sid}' ที่ไม่มีในชีต spaces")
        qtype = as_text(r.get("qtype")).lower()
        asset = as_text(r.get("asset"))
        payload = fix_newlines(as_text(r.get("payload"))) if as_text(r.get("payload")) else ""
        choices, letter_index = choices_of(r, "abcd")

        if qtype and qtype not in POINT_QTYPES:
            errors.append(f"{qid}: qtype '{qtype}' ไม่รู้จัก — ใช้ได้เฉพาะ (ว่าง) / {' / '.join(POINT_QTYPES)}")
            continue

        # ---------- คำถามแบบ "ชี้" ----------
        if qtype:
            if choices:
                errors.append(f"{qid}: qtype '{qtype}' ต้องเว้น choice_a-d ว่างทั้งหมด (พบ {len(choices)} ตัวเลือก)")
            if qtype == "hotspot":
                if not HOTSPOT_RE.match(ans):
                    errors.append(f"{qid}: answer ของ hotspot ต้องเป็นรูปแบบ 'x,y,r' ตัวเลขล้วน (พบ '{ans}')")
                elif any(not 0 <= int(n) <= 100 for n in ans.split(",")):
                    errors.append(f"{qid}: answer ของ hotspot ต้องอยู่ในช่วง 0-100 ทั้งสามค่า (พบ '{ans}')")
                if not asset:
                    errors.append(f"{qid}: hotspot ต้องระบุคอลัมน์ asset (ชื่อภาพ)")
            elif qtype == "colorwheel":
                deg, tol = as_int_or_none(ans), as_int_or_none(payload)
                if deg is None or not 0 <= deg <= 359:
                    errors.append(f"{qid}: answer ของ colorwheel ต้องเป็นองศาจำนวนเต็ม 0-359 (พบ '{ans}')")
                if tol is None or not 1 <= tol <= 45:
                    errors.append(f"{qid}: payload ของ colorwheel ต้องเป็นระยะผ่อนผัน 1-45 องศา (พบ '{payload}')")
                if not asset:
                    errors.append(f"{qid}: colorwheel ต้องระบุ asset เช่น 'wheel:orange'")
            elif qtype == "linepick":
                if not payload:
                    errors.append(f"{qid}: linepick ต้องมี payload (โค้ดที่ให้ชี้บรรทัด)")
                else:
                    n_lines = len(payload.split("\n"))
                    line = as_int_or_none(ans)
                    if line is None or not 1 <= line <= n_lines:
                        errors.append(f"{qid}: answer ของ linepick ต้องเป็นเลขบรรทัด 1-{n_lines} (พบ '{ans}')")
            q = {
                "question_id": qid, "space_id": sid, "level": as_int(r["level"], 1),
                "question_th": qth, "choices": [], "answer": ans,
                "time_limit": as_int(r["time_limit"]), "qtype": qtype,
            }
            if asset:                     # เซลล์ว่าง = ไม่ใส่คีย์ กัน data.json บวม
                q["asset"] = asset
            if payload:
                q["payload"] = payload
            questions.append(q)
            continue

        # ---------- คำถามตัวเลือกแบบเดิม ----------
        ans = ans.lower()
        if not is_draft and ans not in ANSWER_INDEX:
            warns.append(f"questions: {qid} answer '{ans}' ไม่ใช่ a-d — ข้ามแถวนี้")
            continue
        if not is_draft and ans not in letter_index:
            warns.append(f"questions: {qid} เฉลย '{ans}' ชี้ตัวเลือกที่ว่าง — ข้ามแถวนี้ "
                         f"(เช็คว่าเซลล์นั้นโดน Excel ตีความเป็นสูตรหรือไม่)")
            continue
        questions.append({
            "question_id": qid,
            "space_id": sid,
            "level": as_int(r["level"], 1),
            "question_th": qth,
            "choices": choices,
            "answer": letter_index.get(ans, 0),
            "time_limit": as_int(r["time_limit"]),
        })

    # ---------- events ----------
    df = xl.parse("events", header=1)
    events = []
    for _, r in df.iterrows():
        title = str(cell(r["title_th"])).strip()
        if not title:
            continue
        events.append({
            "event_id": str(cell(r["event_id"])).strip(),
            "zone": str(cell(r["zone"])).strip(),
            "mechanic": str(cell(r["mechanic"])).strip(),
            "weight": as_int(r["weight"], 1),
            "title_th": title,
            "description_th": str(cell(r["description_th"])).strip(),
            "effect": str(cell(r["effect"])).strip(),
        })

    # ---------- bugjam ----------
    df = xl.parse("bugjam", header=1)
    bugjam = []
    for _, r in df.iterrows():
        qth = str(cell(r["question_th"])).strip()
        if not qth:
            continue
        ans = str(cell(r["answer"])).strip().lower()
        choices, letter_index = choices_of(r, "abc")
        if ans not in letter_index:
            warns.append(f"bugjam: {cell(r['bug_id'])} เฉลย '{ans}' ชี้ตัวเลือกที่ว่าง — ข้ามแถวนี้")
            continue
        # difficulty/hint เป็นคอลัมน์ใหม่ — ไฟล์เก่าที่ไม่มีคอลัมน์นี้ให้ถือเป็น easy/ไม่มี hint
        difficulty = str(cell(r.get("difficulty"), "easy")).strip().lower() or "easy"
        bugjam.append({
            "bug_id": str(cell(r["bug_id"])).strip(),
            "code": fix_newlines(cell(r["code_snippet"])),
            "question_th": qth,
            "choices": choices,
            "answer": letter_index[ans],
            "time_limit": as_int(r["time_limit"]),
            "difficulty": difficulty if difficulty in ("easy", "hard") else "easy",
            "hint": str(cell(r.get("hint"))).strip(),
        })

    # ข้อมูลคำถามผิดกติกา = หยุดตั้งแต่ตอน build ไม่ปล่อยให้ไปพังบนเว็บ
    if errors:
        print(f"[ERROR] คำถามไม่ผ่านการตรวจ {len(errors)} รายการ — ไม่ได้เขียน {OUT_FILE}")
        for e in errors:
            print("   ✗", e)
        sys.exit(1)

    data = {"spaces": spaces, "questions": questions, "events": events, "bugjam": bugjam}
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] {OUT_FILE}: spaces {len(spaces)} | questions {len(questions)} "
          f"| events {len(events)} | bugjam {len(bugjam)}")
    zones = {}
    for e in events:
        zones[e["zone"]] = zones.get(e["zone"], 0) + 1
    print("     events ต่อโซน:", ", ".join(f"{z}={n}" for z, n in zones.items()))
    for w in warns:
        print("[!]", w)


if __name__ == "__main__":
    main()
