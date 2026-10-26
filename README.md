# CodeCoin — QR System

ระบบ QR ประกอบบอร์ดเกมเพื่อการศึกษา CodeCoin (base จาก Monopoly) — Static ทั้งหมด host บน GitHub Pages

**🌐 เว็บจริง:** https://ballgamerzaman-code.github.io/codecoin/
**📦 Repo:** https://github.com/ballgamerzaman-code/codecoin (push ขึ้น main แล้วเว็บอัปเดตเองใน ~1 นาที)

## โครงสร้างโปรเจค

ไฟล์ที่ราก repo คือของที่ **เว็บจริงต้องใช้** (GitHub Pages เสิร์ฟจากรากตรง ๆ) — ห้ามย้ายเข้าโฟลเดอร์
ที่เหลือแยกตามงานว่าใครใช้ทำอะไร

```
index.html  data.json  sw.js  qrcode.js  manifest.webmanifest  icon-192/512.png   ← เว็บจริง (ห้ามย้าย)
codecoin_database.xlsx                                                 ← ต้นทางข้อมูลทีม content
docs/       PROJECT_SUMMARY.md · BOX_DEMO.md · animation.md · DESIGN_AUDIT.md  ← เอกสารสรุป
            BACKDROP_3D.md (บอร์ดนำเสนอ 3 มิติ — โครงไฟล์ วิธีแก้ กับดัก)
scripts/    build_data.py · gen_qr.py · gen_icons.py                   ← สคริปต์ Python
            gen_demo_assets.py · make_standalone.py · gen_banknotes.py · gen_final_boss_card.py
            prepare_board_print.py · build_dashboard.py (+ dashboard_template.html)
print/      Final/*.pdf (ไฟล์ส่งโรงพิมพ์) · qr_output/*.png            ← งานสิ่งพิมพ์
            codecoin_cards_rev3_1.html (การ์ด 16 ใบ) · banknotes/ (ธนบัตร 5 ราคา) · final_boss_card/
box_demo/   codecoin_box_demo_v4.html + demo_assets/                   ← เดโมกล่อง 3 มิติ
            codecoin_box_demo_standalone.html (ไฟล์เดียวจบ ส่งต่อได้)
tools/      hotspot_picker.html · motherboard.svg     ← เครื่องมือทีม content / สถานะโปรเจค
            backdrop_3d.html (ฉากหลังลายไทย 3 ตอน — โมเดล 3 มิติ + ไฟล์ตัดเลเซอร์)
```

| ไฟล์หลัก | หน้าที่ |
|---|---|
| `index.html` | ตัวแอป (SPA ไฟล์เดียว) — โหลดข้อมูลจาก `data.json` ตอนเปิดหน้า |
| `sw.js` | Service Worker ให้เล่นออฟไลน์ — **แก้ `index.html` ทีไร ต้องบั๊ม `CACHE`** (ตอนนี้ `codecoin-v25`) |
| `qrcode.js` | ไลบรารีสร้าง QR ในเบราว์เซอร์ (qrcode-generator 1.4.4, MIT) — ห้องรอ Debug Rescue ใช้โชว์ QR ให้เพื่อนสแกน |
| `codecoin_database.xlsx` | **ต้นทางข้อมูลของทีม content** (4 ชีต: spaces/questions/events/bugjam) |
| `scripts/build_data.py` | แปลง Excel → `data.json` (รันทุกครั้งหลังทีม content แก้ Excel) |
| `data.json` | ฐานข้อมูลที่เว็บใช้จริง — **อย่าแก้มือ ให้แก้ Excel แล้วรัน build_data.py** |
| `scripts/gen_qr.py` | สคริปต์ gen QR ทั้งชุดเป็น PNG (ลงโฟลเดอร์ `print/qr_output/`) |
| `tools/backdrop_3d.html` | ออกแบบบอร์ดนำเสนอ (ฉากพับ 3 ตอนลายไทย) — ปรับขนาด/มุมพับ/ลายกนก + จัดเนื้อหานำเสนอบนแผง + ของตกแต่ง แล้วส่งออก SVG · DXF (เส้นตัดเลเซอร์ 1:1 มม.) และ OBJ |

> สคริปต์ทุกตัวอ้าง path จากรากโปรเจคเสมอ (ผ่าน `__file__`) รันจากโฟลเดอร์ไหนก็ได้

## Routing

| URL | หน้า |
|---|---|
| ไม่มี `?space=` | เมนูทดสอบ (คลิกดูทุกช่องโดยไม่ต้องสแกน) |
| `?space=coding_02` | ช่องทรัพย์สิน: เลือกโหมด → ปกติ (คำถาม L1 ถูกลด 20%) / มั่นใจ 💎 (คำถาม L4 ถูกลด 40% ผิดหมุนวงล้อ) |
| `?space=coding_02&upgrade=2` | อัปเกรดระดับชำนาญ: หน้าเตรียมตัว (ออกได้ฟรี) → คำถาม L2 (ออกกลางคัน = ยอมแพ้) — `upgrade=3` = ผู้เชี่ยวชาญ |
| `?space=event_coding` | สุ่มเหตุการณ์โซน (coding/design/office/hardware) — เติม `&test=1` = มีปุ่มสุ่มใหม่ไว้ทดสอบ (เมนูทดสอบใส่ให้เอง) |
| `?space=bugjam` | โจทย์ debug จับเวลา (ง่าย/ยาก) ตอบถูกออกจาก "คุก" ฟรี ผิด = เสียค่าปรับ |
| `?space=cooling` | จุดพักเครื่อง — บอสไฟต์ Server Meltdown ทั้งโต๊ะ |
| `?space=debug_rescue` | มินิเกมกู้บั๊กด่วน 2 คน: เลือกด่าน (ตัดสายไฟ / คีย์แพด / จับคู่คำสั่ง / กู้ระบบขั้นสุด) → สร้างห้องรอ + QR ให้เพื่อน |
| `?space=debug_rescue&pattern=final_boss` | หน้าเลือกด่านโดยเลือก "กู้ระบบขั้นสุด" ไว้ให้ — QR บนการ์ดกู้ระบบขั้นสุดชี้มาที่นี่ (ต้องกดยืนยันว่าได้การ์ดจาก Banker ก่อนเริ่ม) |
| `?space=debug_rescue&role=solver&code=XXXX&pattern=keypad` | เข้าเกมตรง (โหมดพิมพ์รหัสเอง) — `role=guide` = ผู้อ่านคู่มือ · ไม่ใส่ `pattern` = ตัดสายไฟ · เติม `&lobby=1` = เข้าห้องรอก่อน |

## การแก้ไขข้อมูล

- ทีม content แก้ `codecoin_database.xlsx` (หัวตารางจริงอยู่แถวที่ 2 — แถวแรกเป็นหมายเหตุ ห้ามลบ) แล้วรัน:

```bash
py scripts/build_data.py    # ได้ data.json ใหม่
py scripts/gen_qr.py        # ถ้าเพิ่ม/ลบช่อง ให้ gen QR ใหม่ด้วย
```

- ในชีต questions กรอก `answer` เป็นตัวอักษร a/b/c/d — สคริปต์แปลงเป็น index ให้เอง `time_limit` เว้นว่าง = ไม่จับเวลา
- แถวคำถามที่ `question_th` หรือ `question_id` ขึ้นต้นด้วย `DRAFT` จะถูกซ่อนอัตโนมัติ
- สคริปต์เตือนถ้า answer ไม่ใช่ a-d หรือ space_id อ้างถึงช่องที่ไม่มีจริง
- ถ้าโหลด `data.json` ไม่สำเร็จ แอปจะใช้ข้อมูลสำรองที่ฝังใน `index.html` และแสดงแถบเตือน
- จะย้ายไป Google Sheet ภายหลังได้โดยเปลี่ยน `CONFIG.data_url` ใน `index.html` ให้ชี้ URL Apps Script (doGet คืน JSON) หรือ opensheet.elk.sh — โครงสร้าง JSON ต้องมี key ครบ 4 ก้อนเหมือน `data.json`
- เก็บสถิติการตอบ (optional): ใส่ URL Apps Script ใน `CONFIG.log_url` — แอปจะเข้าคิวใน localStorage แล้ว POST เป็น **array ของแถว** (เน็ตหลุดแล้วส่งตามให้เอง) รายละเอียดคอลัมน์ทั้งหมดอยู่ใน [`docs/PROJECT_SUMMARY.md`](docs/PROJECT_SUMMARY.md) หัวข้อ 10

## สร้าง QR

```bash
pip install "qrcode[pil]"
py scripts/gen_qr.py
```

ได้ PNG error correction ระดับ H ตั้งชื่อตาม space_id ลงใน `print/qr_output/` ขนาดพิมพ์คมชัดที่ ~3×3 ซม. (300 DPI)
(`BASE_URL` บนหัวไฟล์ `scripts/gen_qr.py` ชี้ URL เว็บจริงอยู่แล้ว)

## ทดสอบในเครื่อง

เปิดผ่าน local server ที่ **รากโปรเจค** (เพราะ `fetch` data.json ไม่ทำงานบน `file://` และ Service Worker ต้องการ localhost/https):

```bash
py -m http.server 8000
# แล้วเปิด http://localhost:8000
```

> ⚠️ ถ้าเคยเปิดเว็บในเบราว์เซอร์นั้นมาก่อน Service Worker อาจเสิร์ฟไฟล์ประกอบเก่าจากแคช — เห็นพฤติกรรมไม่ตรงกับโค้ดให้ Unregister SW + ล้าง Cache Storage (DevTools → Application) ก่อนเทสต์
> มือถือจริง: เช็กเลข `CACHE` ที่ `sw.js` บนเว็บก่อนทดสอบฟีเจอร์ใหม่ทุกครั้ง

## กติกาที่ห้ามเปลี่ยน

- Naming: space_id = `{zone}_{ลำดับ 2 หลัก}` (ตัวพิมพ์เล็ก + underscore), question_id = `{space_id}_L{ระดับ}_{ลำดับ}`
- รูปแบบ effect: `+1500` / `-800` / `skip:1` / `all:-500` / `collect:200` / `bet:1000:x3|safe:+300` / `quiz:{question_id}:+500`
- UI ภาษาไทย + ธีมสี PCB เดิม
