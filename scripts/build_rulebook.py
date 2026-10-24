#!/usr/bin/env python3
"""สร้างเล่มคู่มือกติกา A5 -> print/rulebook/

ต้นฉบับคือ Claude Doc "คู่มือกติกา CodeCoin" (https://claude.ai/artifact/MdtrB4zxWJhtMWmuHnj1ZL)
export เป็น markdown มาเก็บที่ print/rulebook/rulebook.md -> แก้ใน doc แล้ว export ทับไฟล์นี้ แล้วรันใหม่
กล่องรับคู่มือได้แค่ A5 (docs/BOX_DEMO.md ข้อ 9) จึงจัดหน้าเป็น A5 148 x 210 มม.
ฟอนต์ Kanit/Sarabun โหลดจาก Google Fonts ตอนพิมพ์ (ต้องต่อเน็ต) ถ้าโหลดไม่ได้จะตกไปใช้ Leelawadee UI

รัน: py scripts/build_rulebook.py   (ใช้ Microsoft Edge แบบ headless พิมพ์ PDF)
"""
import html
import os
import re
import subprocess
import time
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "print", "rulebook")
SRC = os.path.join(OUT, "rulebook.md")
HTML_OUT = os.path.join(OUT, "rulebook.html")
PDF_OUT = os.path.join(OUT, "คู่มือกติกา_CodeCoin_A5.pdf")
BOARD_IMG = "../../box_demo/demo_assets/board.webp"   # อ้างจาก print/rulebook/
EDGE = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
EDITION = "ฉบับ 24 ต.ค. 2026"


def inline(s):
    """markdown แบบบรรทัดเดียว -> html (escape, ตัวหนา, ลิงก์)"""
    s = s.replace("\\", "\x00")            # backslash escape ของ export (\~ \_ \]) -> ตัดทิ้ง
    s = re.sub(r"\x00(.)", r"\1", s).replace("\x00", "")
    s = html.escape(s, quote=False).replace("&amp;#91;", "[")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def md_to_html(md):
    lines = md.splitlines()
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("#"):
            lvl = len(ln) - len(ln.lstrip("#"))
            text = ln[lvl:].strip()
            if lvl == 1:
                i += 1
                continue                    # หัวเรื่องหลักอยู่บนปกแล้ว
            out.append(f"<h{lvl}>{inline(text)}</h{lvl}>")
            i += 1
            continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            rows = [r for r in rows if any(r)]   # แถวว่างท้ายตารางใน doc
            t = ["<table>", "<tr>" + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr>"]
            t += ["<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:]]
            out.append("\n".join(t) + "</table>")
            continue
        m = re.match(r"(\s*)(\d+\.|-) ", ln)
        if m:
            out.append(parse_list(lines, i))
            while i < len(lines) and (re.match(r"\s*(\d+\.|-) ", lines[i]) or lines[i].startswith("   ")):
                i += 1
            continue
        if "image:" in ln:
            out.append(f'<figure><img src="{BOARD_IMG}" alt="กระดาน CodeCoin"></figure>')
            i += 1
            continue
        if re.match(r"\w{3} \d+, \d{4} · @", ln):   # บรรทัดวันที่/ผู้เขียนจาก doc
            i += 1
            continue
        cls = ' class="src"' if ln.startswith("ที่มา:") else ""
        out.append(f"<p{cls}>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)


def parse_list(lines, i, indent=0):
    tag = "ol" if re.match(r"\s*\d+\.", lines[i]) else "ul"
    items = []
    while i < len(lines):
        m = re.match(r"(\s*)(\d+\.|-) (.*)", lines[i])
        if not m or len(m.group(1)) < indent:
            break
        if len(m.group(1)) > indent:
            items[-1] += parse_list(lines, i, len(m.group(1)))
            while i < len(lines) and re.match(r"\s{%d,}(\d+\.|-) " % (indent + 1), lines[i]):
                i += 1
            continue
        items.append(inline(m.group(3)))
        i += 1
    return f"<{tag}>" + "".join(f"<li>{x}</li>" for x in items) + f"</{tag}>"


CSS = """
@page{size:148mm 210mm;margin:12mm 11mm 13mm;@bottom-center{content:counter(page);font:8pt 'Kanit',sans-serif;color:#5b6461}}
@page:first{margin:0}
:root{--ink:#1d2321;--soft:#5b6461;--line:#cfd6d3;--pcb:#0f5c3f;--pcb2:#e6f1ec;--gold:#b8860b}
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;font:9.4pt/1.55 'Sarabun','Leelawadee UI',sans-serif;color:var(--ink);background:#fff}
.cover{height:210mm;padding:16mm 12mm 12mm;background:var(--pcb);color:#fff;display:flex;flex-direction:column;page-break-after:always}
.cover .kicker{font:500 9pt 'Kanit',sans-serif;letter-spacing:.2em;opacity:.8}
.cover h1{font:600 30pt/1.15 'Kanit',sans-serif;margin:3mm 0 2mm}
.cover .sub{font:300 11pt 'Kanit',sans-serif;opacity:.9}
.cover img{margin:auto 0 0;width:100%;border-radius:2mm;box-shadow:0 2mm 6mm rgba(0,0,0,.35)}
.cover .ed{margin-top:6mm;font:400 8.5pt 'Kanit',sans-serif;opacity:.75}
h2{font:600 14pt/1.25 'Kanit',sans-serif;color:var(--pcb);margin:0 0 3mm;padding-bottom:1.5mm;border-bottom:.6mm solid var(--pcb);break-after:avoid}
h2:not(:first-of-type){break-before:page}
h3{font:500 11pt/1.3 'Kanit',sans-serif;color:var(--pcb);margin:5mm 0 1.5mm;break-after:avoid}
p{margin:0 0 2.2mm}
ol,ul{margin:0 0 2.5mm;padding-left:5.5mm}
li{margin:0 0 1.2mm}
li>ol,li>ul{margin-top:1.2mm}
b{font-weight:700}
a{color:var(--pcb)}
table{width:100%;border-collapse:collapse;margin:1mm 0 3mm;font-size:8.6pt;line-height:1.45;break-inside:auto}
tr{break-inside:avoid}
th{background:var(--pcb);color:#fff;font:500 8.6pt 'Kanit',sans-serif;text-align:left}
th,td{padding:1.3mm 1.8mm;border:.25mm solid var(--line);vertical-align:top}
tr:nth-child(odd) td{background:var(--pcb2)}
figure{margin:2mm 0 3mm;text-align:center}
figure img{width:100%;border-radius:1.5mm}
.src{margin-top:6mm;font-size:7.6pt;color:var(--soft)}
"""


def main():
    md = open(SRC, encoding="utf-8").read()
    body = md_to_html(md)
    page = f"""<!doctype html><html lang="th"><head><meta charset="utf-8">
<title>คู่มือกติกา CodeCoin</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&family=Sarabun:wght@400;700&display=block" rel="stylesheet">
<style>{CSS}</style></head><body>
<section class="cover">
  <div class="kicker">BOARD GAME · RULEBOOK</div>
  <h1>คู่มือกติกา<br>CodeCoin</h1>
  <div class="sub">บอร์ดเกมเพื่อการศึกษา · 2–4 ผู้เล่น + Banker · ~50 นาที</div>
  <img src="{BOARD_IMG}" alt="กระดาน CodeCoin">
  <div class="ed">{EDITION}</div>
</section>
{body}
</body></html>"""
    open(HTML_OUT, "w", encoding="utf-8").write(page)
    edge = next((p for p in EDGE if os.path.exists(p)), None)
    if not edge:
        sys.exit("ไม่พบ Microsoft Edge — เปิด rulebook.html แล้วสั่งพิมพ์เป็น PDF (A5) เอง")
    if os.path.exists(PDF_OUT):
        os.remove(PDF_OUT)
    subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=15000", f"--print-to-pdf={PDF_OUT}",
                    "file:///" + HTML_OUT.replace("\\", "/")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # msedge.exe คืนค่ากลับก่อนเขียน PDF เสร็จ -> รอจนไฟล์ขนาดนิ่ง
    last, deadline = -1, time.time() + 60
    while time.time() < deadline:
        size = os.path.getsize(PDF_OUT) if os.path.exists(PDF_OUT) else -1
        if size > 0 and size == last:
            break
        last = size
        time.sleep(1)
    else:
        sys.exit("Edge พิมพ์ PDF ไม่สำเร็จภายใน 60 วินาที")
    print("เขียน", os.path.relpath(HTML_OUT, ROOT))
    print("เขียน", os.path.relpath(PDF_OUT, ROOT))


if __name__ == "__main__":
    main()
