# CodeCoin — QR System

ระบบ QR ประกอบบอร์ดเกมเพื่อการศึกษา CodeCoin (base จาก Monopoly) — Static ทั้งหมด host บน GitHub Pages

**🌐 เว็บจริง:** https://ballgamerzaman-code.github.io/codecoin/
**📦 Repo:** https://github.com/ballgamerzaman-code/codecoin (push ขึ้น main แล้วเว็บอัปเดตเองใน ~1 นาที)

## โครงสร้างโปรเจค

ไฟล์ที่ราก repo คือของที่ **เว็บจริงต้องใช้** (GitHub Pages เสิร์ฟจากรากตรง ๆ) — ห้ามย้ายเข้าโฟลเดอร์
ที่เหลือแยกตามงานว่าใครใช้ทำอะไร

```
index.html  data.json  sw.js  manifest.webmanifest  icon-192/512.png   ← เว็บจริง (ห้ามย้าย)
codecoin_database.xlsx                                                 ← ต้นทางข้อมูลทีม content
docs/       PROJECT_SUMMARY.md · BOX_DEMO.md · animation.md            ← เอกสารสรุป
scripts/    build_data.py · gen_qr.py · gen_icons.py                   ← สคริปต์ Python
            gen_demo_assets.py · make_standalone.py
print/      Final/*.pdf (ไฟล์ส่งโรงพิมพ์) · qr_output/*.png            ← งานสิ่งพิมพ์
            codecoin_cards_rev3_1.html (การ์ด 16 ใบ)
box_demo/   codecoin_box_demo_v4.html + demo_assets/                   ← เดโมกล่อง 3 มิติ
            codecoin_box_demo_standalone.html (ไฟล์เดียวจบ ส่งต่อได้)
tools/      hotspot_picker.html · motherboard.svg                      ← เครื่องมือทีม content
```

| ไฟล์หลัก | หน้าที่ |
|---|---|
| `index.html` | ตัวแอป (SPA ไฟล์เดียว) — โหลดข้อมูลจาก `data.json` ตอนเปิดหน้า |
| `sw.js` | Service Worker ให้เล่นออฟไลน์ — **แก้ `index.html` ทีไร ต้องบั๊ม `CACHE`** |
| `codecoin_database.xlsx` | **ต้นทางข้อมูลของทีม content** (4 ชีต: spaces/questions/events/bugjam) |
| `scripts/build_data.py` | แปลง Excel → `data.json` (รันทุกครั้งหลังทีม content แก้ Excel) |
| `data.json` | ฐานข้อมูลที่เว็บใช้จริง — **อย่าแก้มือ ให้แก้ Excel แล้วรัน build_data.py** |
| `scripts/gen_qr.py` | สคริปต์ gen QR ทั้งชุดเป็น PNG (ลงโฟลเดอร์ `print/qr_output/`) |

> สคริปต์ทุกตัวอ้าง path จากรากโปรเจคเสมอ (ผ่าน `__file__`) รันจากโฟลเดอร์ไหนก็ได้

## Routing

| URL | หน้า |
|---|---|
| ไม่มี `?space=` | เมนูทดสอบ (คลิกดูทุกช่องโดยไม่ต้องสแกน) |
| `?space=coding_02` | ช่องทรัพย์สิน: เนื้อหา → คำถาม L1 → ตอบถูกลด 20% |
| `?space=coding_02&upgrade=2` | อัปเกรดระดับชำนาญ (คำถาม L2) — `upgrade=3` = ผู้เชี่ยวชาญ |
| `?space=event_coding` | สุ่มเหตุการณ์โซน (coding/design/office/hardware) |
| `?space=bugjam` | โจทย์ debug จับเวลา ออกจาก "คุก" ฟรีเมื่อตอบถูก |

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

## กติกาที่ห้ามเปลี่ยน

- Naming: space_id = `{zone}_{ลำดับ 2 หลัก}` (ตัวพิมพ์เล็ก + underscore), question_id = `{space_id}_L{ระดับ}_{ลำดับ}`
- รูปแบบ effect: `+1500` / `-800` / `skip:1` / `all:-500` / `collect:200` / `bet:1000:x3|safe:+300` / `quiz:{question_id}:+500`
- UI ภาษาไทย + ธีมสี PCB เดิม
