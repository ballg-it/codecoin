# CodeCoin — Motion System (สรุป Stage 0–4)

เอกสารนี้สรุปสิ่งที่ทำจริงในระบบ animation ของ CodeCoin (`index.html` + `sw.js`)
อ้างอิงจาก `codecoin_animation_handoff.md` และฉบับแก้ `codecoin_animation_handoff_v2.md`
Stage 5 (ตรวจรับรอบสุดท้าย) ยังไม่ได้ทำ — เอกสารนี้หยุดที่ Stage 4

สถานะ commit: `ca652dd` (Stage 1-2) → `b2b3ea1` (Stage 3) → `de37963` (Stage 4)
`sw.js` ปัจจุบัน: `codecoin-v12`

---

## Stage 0 — สำรวจ

อ่าน `index.html` ทั้งไฟล์ก่อนแตะโค้ด พบจุดสำคัญที่ทำให้ต้องแก้แผนจากเอกสารต้นฉบับ:

- dispatcher ของคำถามเป็น if/else ธรรมดา ไม่ใช่ `switch` — ทางกันจอขาวจริงคือ
  `return renderMCQ(q, onAnswer)` และกิ่ง "ไม่มีตัวเลือก" ใน `renderMCQ` (ห้ามแตะ 2 จุดนี้ตลอดทั้งโปรเจค)
- `renderEvent()` ไม่มีโครงการ์ดสองหน้าอยู่แล้ว ต้องเสริมด้วย overlay ไม่ใช่รื้อ
- Bug Jam เป็น text node เดียวใน `.code-box` → ตัดไอเดียไฮไลต์รายบรรทัดทิ้ง เปลี่ยนเป็น pulse ทั้งกล่อง
- `sw.js` เริ่มที่ `codecoin-v8` (ไม่ใช่ v4 ตามเอกสารเดิม)
- HP bar เดิมใช้ `width` (ผิดกฎ transform-only) — เก็บไว้แก้ Stage 4

---

## Stage 1 — วางรากฐาน (commit `ca652dd`)

ไม่มีอะไรเปลี่ยนตาเห็น เตรียมกลไกกลางให้ Stage หลังใช้ร่วมกัน

- **Motion tokens** ใน `:root` (`--dur-press/enter/state/cheer`, `--ease-out/io/pop`)
  + `html[data-motion="on"|"off"]` override ทับมีเดียควีรีได้ (specificity สูงกว่า `:root`)
- **`MOTION`** object — `reduced` เป็น 3 สถานะ (`on`/`off`/`null`=ตามเครื่อง),
  `d(ms)` ย่อเวลา, `run(el, frames, opt)` = `el.animate()` + เก็บกวาด `will-change` อัตโนมัติ
  (ใช้ `addEventListener('finish'/'cancel')` ไม่ใช่ `.onfinish=` เพราะจุดนั้นเป็นของผู้เรียก)
- **`animShim()`** — เบราว์เซอร์ไม่มี WAAPI ก็ไม่คืน `null` (กันจอขาว Stage 3-4 ที่ผูก `.onfinish` ต่อกัน)
- **`skippable(anim)`** — แตะจอที่ไหนก็ได้ = จบ animation ทันที (สำหรับของที่ยาวเกิน 400ms)
- ปุ่ม 🐇/🐢 "ลดการเคลื่อนไหว" ข้างปุ่ม mute เก็บค่าใน `localStorage['cc_motion']`

---

## Stage 2 — นาฬิกา + การกดปุ่ม (รวมใน commit `ca652dd`)

- **วงแหวนนาฬิกา** ใน `renderQuiz()` — SVG `stroke-dashoffset` ผ่าน `el.animate()` ตรง ๆ
  ด้วย `duration = time_limit*1000` เสมอ **ไม่ผ่าน `MOTION.run()`** (ย่อไม่ได้ ไม่งั้นนาฬิกาโกหกเวลา)
  รีเฟรชกลางคำถาม → `ringAnim.currentTime = เวลาที่ผ่านไปจริง`
  5 วิสุดท้าย: สีเปลี่ยนเสมอ, pulse scale ปิดเมื่อ `MOTION.reduced`
- **กดปุ่มตัวเลือก** — CSS `#choices button:active{transform:scale(.97)}` จุดเดียวครอบทั้ง 4 qtype
- **เข้าหน้าใหม่** — `enterScreen()` (`translateY(12px)`+fade 180ms) เฉพาะหน้าไม่มีนาฬิกา
- **บั๊กที่เจอระหว่างทำ**: `#screen` เป็น element ถาวร ไม่เคยถูกทำลาย — animation ค้างจากหน้าก่อน
  บวกกับหน้าใหม่ที่ไม่เรียก `enterScreen()` ทำให้จอว่างเปล่า (`opacity:0`) ยาวเป็นวินาที
  แก้ด้วย `cancelScreenEnter()` (กรองด้วย `id:"screen-enter"` เท่านั้น) เรียกที่ **ทุกจุด** ที่มีนาฬิกาเริ่มทันที —
  ทดสอบพบว่า "ดีเลย์ ≥3 วิก็ไม่ปลอดภัยเสมอ" เพราะแท็บถูกพักกลางคันจะหยุด timeline ค้างไว้ที่ 0
  จึงต้องเรียกไม่มีข้อยกเว้นแม้จุดที่คิดว่าดีเลย์นานพอ

---

## Stage 3 — จังหวะเฉลย (commit `b2b3ea1`)

ทำผ่าน delegation ล้วน **ไม่แตะ 4 renderer เลย** (`renderMCQ`/hotspot/colorwheel/linepick)

- **`renderToken`** — ตัวนับ global, +1 ทุกครั้งที่ `enterScreen()`/`playEventCardFlip()` ทำงาน
  ทุก rAF loop และ WAAPI `onfinish` ต้องจับ token ไว้ตอนเริ่มแล้วเทียบก่อนแตะ DOM ทุกเฟรม
- **`chosenEl`** — capture-phase listener บน `#choices` ใน `renderQuiz()` จับ element ที่ผู้เล่นแตะจริง
  โดยไม่ต้องรู้จักโครงสร้างภายในของ renderer (`.closest("button, .lp-row, svg")`)
- **`playAnswerFx(correct, chosenEl)`** — เรียกทันทีหลัง `logAnswer()` ที่ 3 จุด (`startQuiz`,
  `renderUpgrade`, `renderBugQuestion`): ถูก = scale pop 260ms + checkmark วาดเส้น (stroke-dashoffset),
  ผิด = shake 280ms, เฉลยข้อถูกแบบ generic ผ่าน `#choices .correct, .answer` fade เขียว delay:180ms (WAAPI ล้วน)
- **ตัวเลขเงิน** — `animateMoneyCount()` rAF 400ms + `tabular-nums`, สโคปที่ `startQuiz` (จุดเดียวที่ราคาเปลี่ยนจริง)
- **ป้าย +/-** — `floatBadge()` ลอยขึ้น 14px จาง 600ms

**ทดสอบยืนยัน**: ตอบถูกแล้วเรียก `renderMenu()` ทันที (จำลอง "รีบออกกลางนับเงิน") → รอเกิน 400ms →
ไม่มีเลขค้าง ไม่มี `.fx-*` หลงเหลือ ไม่มี console error

---

## Stage 4 — จังหวะรางวัล (commit `de37963`)

### Fail Roulette — เขียนใหม่ทั้งหมด
กฎเหล็ก: **ผลต้องเกิดก่อน animation เสมอ** ลำดับบังคับใน `spinFailRoulette()`:
`weightedPick()` → `Session.patch({rouletteFinalIdx, roulettePay})` → `logAnswer()` →
คำนวณมุมเป้า → `spinRouletteWheel()` (แค่ของประดับ ไม่ตัดสินอะไร)

- วงล้อ SVG จริง (ไม่ใช่ text-cycling แบบเดิม) — วาด wedge ครั้งเดียว, หมุนแค่ `transform` ทุกเฟรม
- `spinRouletteWheel()`: rAF, `easeOutQuart`, ≥3 รอบเต็ม, มุมเป้าคำนวณล่วงหน้า, เด้งเกิน 4° กลับ 180ms,
  tick ตามช่องที่ข้ามจริง, แตะข้ามได้ **หลัง 1.0 วิเท่านั้น** (เช็คด้วย `Date.now()` ไม่ใช่ `skippable()` ทั่วไป)
  เช็ค `renderToken` ทุกเฟรม + หยุดทำงาน (ไม่คำนวณ/ไม่มีเสียง) เมื่อ `document.hidden`
- รีเฟรชกลางหมุน → `renderRouletteStage()` เช็ค `resume.rouletteFinalIdx` → เด้งผลเดิมทันที
  ไม่หมุนใหม่ ไม่สุ่มใหม่ ไม่ log ซ้ำ
- reduced-motion = ข้ามการหมุนเสมอ แสดงผลทันที (path เดียวกับ resume)

### จอสั่นบอสไฟต์
`hitFx()` → `screenShake()` ใช้ `id:"screen-shake"` (คนละตัวกับ `"screen-enter"`)
`cancelScreenEnter()` กรองด้วย id จึงไม่แตะกัน — เก็บ `shakeAnim` reference ไว้ยกเลิกเองใน `finish()`

### การ์ดเหตุการณ์พลิก
`playEventCardFlip(cardEl)` แทน `enterScreen()` เฉพาะ mechanic `simple`/`choice`/`chain`
(`speed` คืนไปตั้งแต่ต้นฟังก์ชัน ไม่มี cover เด็ดขาด เพราะจับเวลา 15 วิ ต้องโผล่ 0ms)
คอนเทนต์จริงเรนเดอร์ไว้ก่อนแล้ว ซ่อนด้วย `rotateY(90deg)` → cover (`rotateY 0→-90°` 220ms, ลบทิ้งตอน
`onfinish`, `pointer-events:none` เสมอ) → การ์ดจริงพลิกเข้า (`rotateY 90°→0°` 260ms, delay 220ms)
`perspective:900px` อยู่ที่ `#screen` (บรรพบุรุษ) ไม่ใช่ตัวการ์ด

### HP bar
`width` → `transform:scaleX()` + `transform-origin:left` ตัวเลข `#dmgNum`/`#tgtNum` อยู่ใน `.hp-row`
แยกจาก `.hp-fill` มาตั้งแต่โครงเดิม จึงไม่ถูกบีบตามเวลาเลือดลด

### อื่น ๆ
- Bug Jam เฉลย: `.code-box.fx-reveal` — pulse scale + เรืองขอบผ่าน `::after` opacity (ห้าม `box-shadow`
  ตรง ๆ เพราะผิดกฎ transform/opacity-only) ไม่แตะ text node เลย
- confetti: `N = hardwareConcurrency <= 4 ? 40 : 110`

---

## กฎที่ยึดตลอดทั้งโปรเจค

1. animate เฉพาะ `transform`/`opacity` (ยกเว้น `stroke-dashoffset` ที่วงแหวนนาฬิกา+checkmark)
2. ห้าม `await`/`setTimeout`/`.finished` ระหว่าง `Session.done()` กับ `logAnswer()`
3. ห้ามแตะ `renderMCQ`/hotspot/colorwheel/linepick และ 2 จุดกันจอขาว
4. ทุก rAF/onfinish ที่แตะ DOM ผ่าน id ที่ถูกใช้ซ้ำข้ามหน้า ต้องเช็ค `renderToken` ก่อนเสมอ
5. `sw.js` บั๊มทุก Stage ที่แก้ `index.html`

## งานที่ยังไม่ทำ / พักไว้

- **Stage 5** (ตรวจรับรอบสุดท้ายตาม checklist) — ยังไม่ได้รัน
- **CPU throttle 4x ≥50fps สำหรับ Roulette** — ยืนยันไม่ได้ในรอบทดสอบล่าสุดเพราะ browser pane
  ของ session ไม่ compositing frame จริง (ข้อจำกัดเครื่องมือทดสอบ ไม่ใช่ข้อสงสัยในโค้ด) ควรเปิดดูจริงอีกรอบ
- `.fx-flash`/`#hit-fx`/`.result.pop`/`.countdown-big` ยังใช้ duration ตายตัวไม่ผ่าน token
  (โค้ดเดิมตั้งแต่ก่อน Stage 1 ไม่ได้อยู่ใน checklist ข้อไหนของ Stage 1-4 เลยไม่ได้แตะ)
- ไฮไลต์บั๊กรายบรรทัดใน Bug Jam ที่พักไว้ตั้งแต่ Stage 0
- View Transitions API สำหรับเปลี่ยนหน้า (ของแถม)
