# Handoff — ความสวยงาม + animation เว็บเกม (Stage V5 → V7, session 4 พ.ย. 2026)

> คนละเรื่องกับ `docs/HANDOFF.md` (บอร์ดนำเสนอ) และ `docs/HANDOFF_forms.md` (แบบประเมิน)

## สถานะ: V5 + V6 + V7 ขึ้นเว็บจริงแล้ว · dashboard ยังซิงก์ถึง V6

- **V5** commit **`c89b496`** (CACHE `codecoin-v28`) — user สั่ง "แก้ไข ปรับปรุงความสวยงามของเว็บ" = เว็บเกม `index.html`
- **V6** commit **`d0ce6b8`** (CACHE `codecoin-v29`) — user สั่ง "จัดการด้านความสวยงามต่อ และจัดการด้าน animation ต่อด้วย"
- push แล้ว (`c89b496..d0ce6b8`) · curl ~50 วิหลัง push: https://ballg-it.github.io/codecoin/ เสิร์ฟ `sw.js` = `codecoin-v29` + index.html ตัว V6
- **V7** = commit ถัดจาก `d0ce6b8` (CACHE **`codecoin-v30`**, หา hash: `git log -1 --format=%h -- sw.js`) — user สั่ง "ต่อไป ความสวยงามวงล้อ" = วงล้อ Fail Roulette · push แล้ว
  ไฟล์ของ V7: `index.html`, `sw.js`, `docs/DESIGN_AUDIT.md`, `docs/animation.md`, `docs/DEVELOPER.md`, ไฟล์นี้
- dashboard artifact ซิงก์ถึง V6 แล้ว — **V7 ยังไม่ซิงก์**
- รายละเอียดเต็ม + ผลตรวจรับ: `docs/DESIGN_AUDIT.md` หัวข้อ **Stage V5 / V6 / V7** · กฎ motion: `docs/animation.md` หัวข้อ Stage V6 / V7

## V7 ทำอะไร (สรุป) — วงล้อสุ่มผลแก้บั๊ก

| ส่วน | อะไร |
|---|---|
| โครง 3 ชั้น | ใน `.roulette-wheel-wrap` (168×168 เท่าเดิม) · `#rouletteWheelG` = **`<svg>` ตัวหมุน** (เดิมเป็น `<g>`) · `.roulette-wheel-top` = `<svg>` นิ่ง · `.roulette-pointer` = `<svg>` ลิ้นชี้ — ทุกชั้น absolute |
| ป้าย | `rouletteShort(entry)` คิดจาก `mult`: −60% −20% เต็ม +20% +40% +60% · ข้ามตา = ไอคอน ⏸ (rect) · ขาวขอบเข้ม `paint-order:stroke` · ขนาดตามจำนวนช่อง |
| สี | `rouletteTier(entry)` → class `.rw-good2/good1/even/bad1/bad2/bad3/skip` · token ใหม่ `--ok-deep` `--bad-soft` `--bad-hot` · ข้ามตา = `--bad` + แถบเฉียง (pattern `#rwHaz`) · `rouletteColor()` (hex ดิบ) ถูกลบ |
| ประดับ | pad ทอง+via บนรอยต่อช่อง (หมุนตาม) · กรอบ `--chrome` ขอบทอง · เงาไล่จากดุม · แสงวาว · ดุมทอง + รูปบั๊ก · เงาใต้จาน (box-shadow ของกรอบ) — ทุกอย่างที่ต้องนิ่งอยู่ชั้นนิ่ง |
| animation | `.spin-in` (`wheelIn`) เฉพาะหมุนสด · ลิ้นชี้สะบัด WAAPI ทุก tick · `.landed` → สปอตไลต์ `.rw-spot` (`rwDim` + `rwWin`) |
| JS | `spinRouletteWheel` ใส่/คืน `will-change` ตัวหมุน+ลิ้นชี้ · `showFinal` เก็บวงล้อเดิม (ไม่ `innerHTML` ทั้งกล่องแล้ว) + เติม `.landed` · `wheelMarkup(enter)` เป็นฟังก์ชัน |
| กรอบผล | `.roulette-frame` จอเทอร์มินัลแบบ `.code-box` · `.final` เรืองทอง · easing ดิบ → token |

## V6 ทำอะไร (สรุป)

| ส่วน | อะไร |
|---|---|
| แถบไฟสีโซน | `.card > .zone-tag::before/::after` `background:inherit` สีจากป้ายเอง ไม่แก้เทมเพลต · `.card` ได้ `position:relative` |
| กล่องผล | `.result` แถบซ้าย inset 3px (แยกจาก `.btn.ghost`) · `#result > .result` / `#rResult > .result` ลอยขึ้น `resultIn` |
| จอ | `.code-box` เส้นสแกน + เรืองฟอสฟอร์ · `.kp-display` เรือง LED · `.big-num`/`.countdown-big` เรืองทอง |
| สายไฟ | `.wire-bar::before` เงาทรงกระบอก · `.wire-row.cut` หรี่แบบ transition + ดีด (`wireTwang`) + รอยตัด (`wireGap`) |
| หลอดพลังบอส | `.hp-bar::after` ขีด 10 ช่อง + เงาวาว (ห้ามวาดบน `.hp-fill` — scaleX บีบขีด) |
| ป้ายเตือน | `.lockout` แถบเฉียงแดง · `.data-warn` แถบเฉียงทอง |
| T0 ambient | token `--dur-ambient` 900ms · `.chip-glint` (element ใหม่ใน header) แสงวิ่งตอนเปิดหน้า · `.boot-pulse` ข้อความโหลด · โหมดลด = ปิดทั้งชิ้น |
| modal | `.confirm-modal` `modalPop` · `.pl-modal` จางเข้า + `.pl-card` `modalRise` |
| JS | `popPicked(el)` เด้งชิปที่เพิ่งเลือก (cooling, เลือกด่านกู้บั๊ก, ปุ่มสลับเสียง/การเคลื่อนไหว) |
| บั๊ก | confetti/จอสั่น ไม่สนโหมดลด → return เมื่อ `MOTION.reduced` · หน้าเลือกด่านกู้บั๊ก `enterScreen()` ทุกแตะ → ธง `entered` |
| เก็บกวาด | hex ดิบในกฎ CSS → token ใหม่ `--ink-body` `--line-deep` `--win-deep` `--lose-deep` `--wire-dead` (นอก `:root` ไม่เหลือ hex แล้ว) |

## V5 เปลี่ยนอะไร (CSS ล้วน — ไม่แตะ JS/เนื้อหา/ขนาดกล่อง)

| ส่วน | ที่ไหนใน `index.html` | อะไร |
|---|---|---|
| token ใหม่ | `:root` บล็อก "Stage V5" (~บรรทัด 40) | `--grid` `--gold-hi` `--gold-lo` `--chip-top` `--ink-chip` `--sheen` `--lift` `--recess` `--pcb-traces` |
| พื้นหลัง | `body` | 5 ชั้น: แสงเขียวด้านบน · ขอบจอมืด · ลายวงจร SVG แผ่นละ 336px · กริด 2 แนว |
| header ชิป | `header`, `header::before/::after`, `header h1` | รอยบาก + หลุม pin 1, ขาชิปโลหะ (สว่าง/ทอง/มืด), ชื่อเกมทองไล่แสงใน `@supports` + `drop-shadow` |
| มิติกล่อง/ปุ่ม | `.card` `.choice` `.menu-item` `.pick` `.kp-key` `.wire-row` `.speed-player` `.bet-btn` | `--sheen` + เงา · `:active` ยุบด้วย transform |
| ปุ่มทอง | `.btn` | gradient + ขอบบนสว่าง + เงาทอง · `.btn:disabled` จาง .45 (เดิมดูเหมือนกดได้) |
| ช่องจม | `.code-box` `.rescue-code` `.rescue-input` `.kp-display` `.hp-wrap` `.point-wrap` `.roulette-frame` | `box-shadow:var(--recess)` · รหัสห้องเรืองแบบจอ LED |
| ปุ่มเลือกโหมด | `.bet-btn` | ตัวไม่ไฮไลต์ ("ตอบมั่นใจ 💎"/"ยาก 💎") `--muted` → `--text` เดิมดูเหมือนถูกปิด |
| บั๊ก | `.pl-card` | อ้าง `var(--card)` ที่ไม่มีใน `:root` → กล่องตั้งเลขผู้เล่นพื้นโปร่ง → `--panel` |
| ข้อความท้ายหน้า | `.footer-note` | text-shadow สีพื้น — ลายวงจรวิ่งผ่านทำ contrast ตกเหลือ ~3.9:1 |
| a11y | `button/input/summary:focus-visible`, `::selection` | ขอบทอง/ไฮไลต์ทอง |
| เก็บกวาด | `.card-cover` | `#0B2B22` → `var(--board)` (สีเท่าเดิม) |

## กฎที่ต้องยึดถ้าจะแต่งต่อ

1. **ห้ามเปลี่ยนขนาดกล่อง** — padding / margin / border-width / font-size / line-height / letter-spacing / ฟอนต์ ห้ามแตะ เพราะ bugjam ยาก (631px) กับ upgrade-quiz (630.3px) เหลือ headroom ~9px ที่จอ 360×640 · ที่ใช้ได้: สี, background, box-shadow, outline, text-shadow, filter, transform ตอน `:active`, pseudo-element แบบ absolute
2. animation/transition = `transform`/`opacity` เท่านั้น duration ต้องเป็น token (`--dur-press` ฯลฯ) — ห้าม transition สี/เงา · ของประดับที่ไม่ผ่าน token (ตั้งเวลาเองใน JS) ต้องเช็ค `MOTION.reduced` เอง · ของประดับ T0 (`--dur-ambient`) โหมดลด = ปิดทั้งชิ้น
3. `var(--bad)` (แดง) = แย่สำหรับผู้เล่นเท่านั้น (กฎ V3b)
4. hex ดิบอยู่ใน `:root` เท่านั้น — ข้อยกเว้นเดียว: ใน data URI (`--pcb-traces`) ใช้ `var()` ไม่ได้ ต้องเขียน `%23xxxxxx`
5. `color:transparent` ของชื่อเกมต้องอยู่ใน `@supports (background-clip:text)` เท่านั้น ไม่งั้นเบราว์เซอร์เก่าชื่อหายทั้งคำ · ห้าม text-shadow กับตัวหนังสือ background-clip (เงาวาดทับ gradient) ใช้ `filter:drop-shadow` แทน
6. ลายวงจร: เส้นที่ทะลุขอบแผ่นมีแต่แนวนอน (เส้นวนแนวนอน + แนวตั้งบนแผ่นที่ต่อกันวนรอบ ตัดกันแน่นอน) · เส้นวิ่งกลางช่องกริด (14 + 28k) แผ่นต้องเป็นทวีคูณ 28
7. **ห้ามทำ `.choice:disabled` ให้จาง** — event speed ปิดปุ่มตัวเลือกตั้งแต่แรก (โชว์ให้อ่านอย่างเดียว) จะจางทั้งข้อ
8. แก้ `index.html` → บั๊ม `CACHE` ใน `sw.js` (ตอนนี้ **v30** → ครั้งหน้า **v31**)
9. สีให้การ์ดตามบริบท → ใช้สีป้าย `.zone-tag` ผ่าน `background:inherit` ไม่ต้องส่งตัวแปรสีจาก JS · หน้าที่วาดทั้งก้อนใหม่ทุกคลิกเรียก `enterScreen()` แค่ครั้งแรก
10. animation เข้า `.result` ห้ามครอบ `.result` ทั่วไป — หน้า speed วาง `.result.info` ไว้ตั้งแต่เฟรมแรกของหน้าจับเวลา (ต้องโผล่ 0ms) · ใช้ selector `#result > .result` เท่านั้น
11. (V7) SVG ที่หมุนทุกเฟรม: หมุน **ทั้ง `<svg>`** (ยกเลเยอร์ GPU ได้ + `will-change` เฉพาะช่วงหมุน) ไม่ใช่ `<g>` ข้างใน · ของที่ต้องนิ่ง (แสง เงา ดุม) แยกไว้ `<svg>` อีกชั้น · ห้าม CSS `filter` บนชิ้นที่ขยับ (เงาลิ้นชี้วาดเป็น path ในตัว) · สีใน SVG ใส่ผ่าน class ใน CSS เท่านั้น (attribute `fill="var(..)"` ไม่ผ่านทุกเบราว์เซอร์)

## พิจารณาแล้ว ไม่ทำ (อย่าคิดใหม่ซ้ำ)

- **View Transitions ข้ามหน้า:** สแกน QR = เปิดจากแอปกล้อง (ไม่ใช่ same-origin navigation ไม่มีทรานซิชันอยู่ดี) + ภาพแรกของหน้าใหม่คือการ์ด "กำลังโหลด" เพราะ data.json ไม่ render-blocking
- **`.pick.on` เด้งด้วย CSS animation:** หน้า cooling วาดทั้งหน้าใหม่ทุกคลิก → ชิป `.on` ทุกตัวเด้งซ้ำทุกครั้ง → ใช้ `popPicked()` หา element ตัวใหม่หลังวาดแทน
- **ของวิ่งวนตลอด (แสงวิ่งบนหลอดพลัง / กระแสไฟบนลายวงจรพื้นหลัง):** กินเฟรมบนมือถือราคาถูกระหว่างหน้าจับเวลา + ดึงสายตาจากคำถาม
- **ไล่สี `background-position` / transition สีกรอบ:** ผิดกฎ transform/opacity — ทุกอย่างที่อยากให้ "เรือง" ใช้ pseudo-element + opacity แบบ `.code-box.fx-reveal::after`
- **`color-mix()` สำหรับแสงสีโซน:** เบราว์เซอร์ที่รองรับ `:has` แต่ไม่รองรับ color-mix จะได้พื้นโปร่ง (invalid at computed-value time) → ใช้ `background:inherit` แทน
- **(V7) confetti ตอนวงล้อได้ −60%:** วงล้อคือบทลงโทษของการตอบผิดแบบมั่นใจ ฉลองใหญ่ = ให้รางวัลการเดา (ขัดหลักบาลานซ์ "เดาสุ่มไม่คุ้มกว่าตั้งใจตอบ") — เสียง correct + แฟลชเขียวเดิมพอแล้ว
- **(V7) กรอบข้อความวิ่งตามช่องใต้ลิ้นชี้ระหว่างหมุน:** label ยาวไม่เท่ากัน (1–2 บรรทัด) กรอบจะสูงต่ำสลับ = ของข้างล่างกระตุกทุก tick · และเป็น text-cycling แบบเดิมที่ Stage 4 เพิ่งเลิกใช้
- **(V7) ไฟวิ่งรอบขอบวงล้อ:** หน้าตาคาสิโน — โปรเจคตั้งใจให้ธีม debug ไม่ใช่การพนัน (PROJECT_SUMMARY หัวข้อ Fail Roulette)
- **ยังพักไว้ (ไม่ได้ตัดทิ้ง):** ไฮไลต์บั๊กรายบรรทัดใน Bug Jam (โจทย์เป็น text node เดียวใน `.code-box` — ต้องแก้โครงข้อมูลก่อน)

## วิธีพิสูจน์ว่า layout ไม่ขยับ (ใช้ซ้ำได้)

1. `git show HEAD:index.html > __old_index.html` ที่รากรีโป (server เดียวกันเสิร์ฟได้ + same-origin ให้ iframe อ่าน DOM ได้)
2. `preview_start {name:"codecoin"}` (port 8123) แล้ว unregister service worker + `caches.delete()` ก่อน
3. วางสคริปต์ข้างล่างใน `javascript_tool` → ได้ผล 19 หน้า `same:true` ทุกหน้า = layout ตรงไฟล์เดิมทุก element (4 หน้าท้ายคือวงล้อ ตั้งสถานะผ่าน `sess` — ลูกข้างในกรอบวงล้อไม่นับ เพราะโครง SVG เปลี่ยนได้ แต่ตัวกรอบนับ)
4. **ลบ `__old_index.html` ทิ้งเสมอ** ห้ามหลุดเข้า commit

```js
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function measure(page, cases) {
  const finishAll = d => d.getAnimations().forEach(a => { try { a.finish(); } catch (e) {} });
  const out = {};
  for (const c of cases) {
    sessionStorage.clear();
    try { localStorage.setItem('cc_player_asked', '1'); localStorage.removeItem('cc_player'); } catch (e) {}
    if (c.sess) sessionStorage.setItem('cc_active', JSON.stringify({ route: 'space', key: 'coding_01', mode: 'confident',
      level: 4, phase: 'roulette', startedAt: Date.now(), deadlineTs: 0, ...c.sess }));   // หน้าวงล้อ = กู้สถานะ phase roulette
    const f = document.createElement('iframe');
    f.style.cssText = 'position:fixed;left:0;top:0;width:360px;height:640px;border:0;z-index:99999;visibility:hidden';
    document.body.appendChild(f);
    await new Promise(r => { f.onload = r; f.src = page + c.q + (c.q ? '&' : '?') + 'nocache=' + Date.now(); });
    await sleep(800);
    const w = f.contentWindow, d = f.contentDocument;
    let err = null;
    try {
      if (c.rerender) {   // สุ่มแบบมี seed → ได้คำถาม/ลำดับตัวเลือกเดียวกันทั้งสองไฟล์
        w.eval(`(function(){let s=${c.seed || 12345};Math.random=function(){s=(s*16807)%2147483647;return (s-1)/2147483646;};})()`);
        w.eval(c.rerender);
        await sleep(400);
      }
      for (const sel of (c.clicks || [])) {
        finishAll(d);
        const el = d.querySelector(sel);
        if (!el) { err = 'missing ' + sel; break; }
        el.click();
        await sleep(400);
      }
    } catch (e) { err = String(e); }
    finishAll(d);
    const tn = d.getElementById('timerNum'); if (tn) tn.textContent = '⏱ 20 วินาที';   // ตัวเลขนาฬิกาเปลี่ยนความกว้าง
    const rows = [...d.querySelectorAll('header, #screen *, .footer-note')]
      .filter(e => !(e.parentElement && e.parentElement.closest('.roulette-wheel-wrap')))
      .map(e => {
      const r = e.getBoundingClientRect();
      return e.tagName + ':' + r.top.toFixed(1) + ':' + r.height.toFixed(1) + ':' + r.left.toFixed(1) + ':' + r.width.toFixed(1);
    });
    const btns = [...d.querySelectorAll('#screen button, #screen .menu-item')].filter(b => b.offsetParent);
    out[c.name] = { rows, err, lastBottom: btns.length ? +Math.max(...btns.map(b => b.getBoundingClientRect().bottom)).toFixed(1) : null,
      screenBottom: +d.getElementById('screen').getBoundingClientRect().bottom.toFixed(1) };
    f.remove();
  }
  return out;
}
const cases = [
  { name: 'menu', q: '' },
  { name: 'mode_select', q: '?space=coding_01' },
  { name: 'quiz_buy', q: '?space=coding_01', rerender: "renderSpace('coding_01')", clicks: ['#modeNormal'] },
  { name: 'upgrade_ready', q: '?space=coding_01&upgrade=2' },
  { name: 'upgrade_quiz', q: '?space=coding_01&upgrade=2', rerender: "renderUpgrade('coding_01', 2)", clicks: ['#upStart'] },
  { name: 'bugjam_select', q: '?space=bugjam' },
  { name: 'bugjam_hard', q: '?space=bugjam', rerender: "renderBugjam()", clicks: ['#diffHard'] },
  { name: 'bugjam_easy', q: '?space=bugjam', rerender: "renderBugjam()", clicks: ['#diffEasy'] },
  { name: 'event_coding', q: '?space=event_coding', rerender: "renderEvent('coding')" },
  { name: 'event_design', q: '?space=event_design', rerender: "renderEvent('design')", seed: 777 },
  { name: 'cooling', q: '?space=cooling' },
  { name: 'rescue_landing', q: '?space=debug_rescue' },
  { name: 'rescue_final', q: '?space=debug_rescue&pattern=final_boss' },
  { name: 'rescue_solver', q: '?space=debug_rescue&role=solver&code=ABCD' },
  { name: 'rescue_guide', q: '?space=debug_rescue&role=guide&code=ABCD' },
  { name: 'roulette_stage', q: '?space=coding_01', sess: {} },
  { name: 'roulette_spin', q: '?space=coding_01', sess: {}, clicks: ['#spinBtn'] },
  { name: 'roulette_final', q: '?space=coding_01', sess: { rouletteFinalIdx: 5, roulettePay: 1600 } },
  { name: 'roulette_skip', q: '?space=coding_01', sess: { rouletteFinalIdx: 6, roulettePay: 1000 } },
];
const A = await measure('/__old_index.html', cases), B = await measure('/', cases);
Object.fromEntries(cases.map(c => {
  const a = A[c.name], b = B[c.name];
  const diffs = a.rows.map((r, i) => r === b.rows[i] ? null : [r, b.rows[i]]).filter(Boolean);
  return [c.name, { same: !diffs.length && a.rows.length === b.rows.length,
    lastBottom: [a.lastBottom, b.lastBottom], screenBottom: [a.screenBottom, b.screenBottom], err: [a.err, b.err], firstDiffs: diffs.slice(0, 3) }];
}))
```

ค่า `lastBottom` อ้างอิง ณ v28 = v29 = v30 (V6/V7 ไม่ขยับสักหน้า) (สั่ง finish animation แล้ว): menu 1595.3 · mode_select 575.4 · quiz_buy 470 · upgrade_ready 543.6 · **upgrade_quiz 630.3** · bugjam_select 318.1 · **bugjam_hard 631** · bugjam_easy 593 · event_coding 649.1 · event_design 592.1 · cooling 1046.7 · rescue_landing 897.3 · rescue_final 1131.9 · rescue_solver 484.1 · rescue_guide 507.8
- รอบ V7 ได้ upgrade_ready **517.5** และ rescue_final **1112.9** ทั้งไฟล์เดิมและใหม่ (สถานะเครื่อง/ข้อมูลต่างจากรอบก่อน ไม่ใช่ CSS) → **เทียบเดิม/ใหม่ในรอบเดียวกันเท่านั้น** อย่าเทียบกับตัวเลขในเอกสาร
- หน้าวงล้อ (V7): `#screen` ล่างสุด ก่อนหมุน 513.4 · กำลังหมุน 748.4 · ผล +60% 788.4 · ผลข้ามตา 843.4 (ปุ่มหมุนล่างสุด 494.4 ทุกสถานะ)

## ข้อควรรู้เรื่อง browser pane

- **เปิดหน้าตรง ๆ ใน tab หลักต้องเติม `&nc=<เลขใหม่>` ทุกครั้ง** — http.server ของ Python ส่ง Last-Modified แล้ว HTTP cache ของเบราว์เซอร์คืน index.html รุ่นเก่า (เห็นหน้าไม่มีลายวงจร) แม้ล้าง SW แล้ว สคริปต์วัดข้างบนใส่ `nocache=` ให้อยู่แล้ว
- อยากเห็น animation กลางทาง (เช่นแสงวิ่ง) ให้ใส่ `<style>` ชั่วคราวตรึง `transform` แทนการ `pause()` + `currentTime` — pane ไม่วาดเฟรมใหม่ให้ animation ที่หยุดไว้
- screenshot มักได้**เฟรมเก่า 1 จังหวะ** (เห็นสไตล์เก่า / หน้าก่อนกด / การ์ดพลิกค้างกลางทางจนเหมือนการ์ดหาย) → ถ่ายซ้ำ หรือถ่าย `scale:0.1` ทิ้งหนึ่งครั้งก่อนถ่ายจริง และเช็กด้วย `javascript_tool` ก่อนสรุปว่าพัง
- pane ที่ไม่ได้วาดเฟรม → WAAPI ค้างที่จุดเริ่ม → `enterScreen()` ค้างที่ `translateY(12px)` ตัวเลขทั้งหน้าคลาด 12px (ไม่ใช่ CSS เปลี่ยน) — ต้อง `finish()` ก่อนวัดเสมอ
- navigate ใน tab หลักเมื่อไร ตัวแปรที่แขวนไว้บน `window` (เช่น baseline) หายหมด — จดค่าที่ต้องเทียบไว้ใน output ก่อน
- คลิกด้วย `find` → `ref` แม่นกว่าพิกัด · เทสต์ขนาดมือถือแล้วคืนด้วย `resize_window preset:"desktop"`
- ตัวแปร/ฟังก์ชันระดับบนสุดของสคริปต์ (`MOTION`, `renderToken`, `confetti()`) เรียกจาก `javascript_tool` ได้ตรง ๆ แม้ไม่อยู่บน `window` — ใช้เทสต์โหมดลด: คลิก `#motionBtn` แล้วนับ `.confetti` (โหมดลด 0 / ปกติ 110 บนเครื่อง >4 core) · **เทสต์เสร็จต้อง `localStorage.removeItem('cc_motion')`** ไม่งั้นโปรไฟล์ pane ค้างค่าที่กดไว้
- **pane ซ่อนอยู่ (`tabs_context` บอก hidden) = rAF ไม่ยิงเลย** แม้ `document.hidden` เป็น false — วงล้อค้าง "กำลังหมุน..." ตลอด · เทสต์วงล้อ: แทน `requestAnimationFrame` ด้วยคิว (`window.__q`) แล้วป้อนเฟรมเอง 16.7ms ต่อรอบ · `finish()` จังหวะเด้งแล้วรอ ~0.5 วิ event `finish` ถึงมา · screenshot ยังถ่ายได้ตอน pane ซ่อน
- เปิดหน้าวงล้อตรง ๆ: `sessionStorage.setItem('cc_active', JSON.stringify({route:'space',key:'coding_01',mode:'confident',level:4,phase:'roulette',startedAt:Date.now(),deadlineTs:0}))` แล้วเปิด `?space=coding_01&nc=<ใหม่>` (ใส่ `rouletteFinalIdx` + `roulettePay` = ข้ามไปหน้าผล) · ดูหลายผลพร้อมกัน: ต่อ `buildRouletteWheelSvg(CONFIG.fail_roulette)` ใส่ `<div class="roulette-wheel-wrap landed">` ใน overlay แล้วตั้ง `transform` ของ `.roulette-wheel-svg` เอง · ขยายดูละเอียด: `style.zoom = 2.1` ที่กรอบชั่วคราว

## dashboard "เวอร์ชันและสถิติ repo" (Artifact ชนิด Dashboard)

https://claude.ai/artifact/FPwJk2whrenDjhGgKDvpAz — ซิงก์ล่าสุด 2026-11-04T11:46Z

- ข้อมูลอยู่ในเอกสาร `datasets/<id>` ของ store (แก้ด้วย `ArtifactData`) ชี้ไปไฟล์แนบ `/_blob/<id>` — **ห้าม publish `file_path`** ใส่ตัว artifact
- ชุดข้อมูล (version หลังรอบนี้): `progress_items` v11 (53 รายการ เสร็จ 43 · หมวดดีไซน์ 9/9) · `meta` v5 (rev 2.5, cache 29, commits 63) · `commits` v4 (12 ล่าสุด บนสุด `d0ce6b8`) · `activity` v4 (commit ต่อวันถึง 2026-11-04) · `backlog` v5 · `content` v4 · `questions` v2 (สองตัวหลังไม่ต้องแตะจนกว่า `data.json` จะเปลี่ยน — ล่าสุด 2026-07-28)
- วิธีอัปเดต:
  1. `ArtifactData list` collection `datasets` → ได้ `source.url` + `version`
  2. โหลดไฟล์เดิม: `Artifact read` + **`path`** = id 32 ตัวของ blob ทีละไฟล์ (`paths` หลายตัวใช้กับ blob ไม่ได้ — ขึ้น "no file is published")
  3. แก้ JSON ในโฟลเดอร์ scratchpad ใหม่ · สคริปต์ Python รันด้วย `py -I` ต้อง `sys.stdout.reconfigure(encoding='utf-8')` เอง (`-I` ไม่สน `PYTHONIOENCODING`)
  4. อัปโหลด: `Artifact` publish + `url` + `asset:true` + `file_path` — ไฟล์ JSON ต้องทีละไฟล์
  5. `ArtifactData batch` → `update` ทุกชุดพร้อม `if_version` = version ที่อ่านมา ใส่ `source {kind:"file", name, url ใหม่}` + `updated {at, by:"Claude"}` + `edit {via:"claude", at}`
  6. เช็ก `ArtifactData get` collection `data/users/me` doc `check` — ไม่มีเอกสารนี้จนกว่าจะมีคนเปิดหน้า (หน้า dashboard ไม่มีตัวเลขเขียนตายตัว ทุกค่ามาจาก datasets/calc)
- `scripts/build_dashboard.py` เพิ่ม 2 บรรทัด V5/V6 แล้ว **แต่ยังไม่ commit** — ไฟล์มีของ session งานกล่องค้างปนอยู่ (BACKLOG D + หมวดกล่องเกม) ให้ commit ไปพร้อมงานนั้น · เนื้อหาในสคริปต์กับใน artifact ไม่ได้ตรงกันทุกบรรทัดอยู่แล้ว (เช่น Events 20 vs 24 ใบ) artifact คือตัวจริงที่ user ดู

## สถานะ repo ณ ตอนเขียน

- `main` = `origin/main` = commit V7 (ต่อจาก `d0ce6b8` V6) — 6 ไฟล์: `index.html` `sw.js` (v30) `docs/DESIGN_AUDIT.md` `docs/animation.md` `docs/DEVELOPER.md` `docs/HANDOFF_web.md`
- ลบ `__old_index.html` (ไฟล์เทียบ layout) ทิ้งแล้วหลังวัด — ถ้าเห็นที่รากรีโปให้ลบ ห้าม commit
- **ค้างจาก session อื่น — ห้าม commit ปนกับงานเว็บ:** `M README.md` `M docs/BOX_DEMO.md` `M docs/PROJECT_SUMMARY.md` `M scripts/build_dashboard.py` (+ 2 บรรทัด V5/V6 ของรอบนี้) `M tools/backdrop_3d.html` · `?? docs/HANDOFF_box.md` `?? docs/HANDOFF_forms.md` `?? print/box/` `?? print/forms/` `?? scripts/build_box.py`
- บน remote มี branch `origin/claude/vigilant-mendel-7905kw` = งานบอร์ดนำเสนอ แตกออกไปก่อน `backdrop_3d.html` เข้า `main` → ถ้าจะรวมจะชน · ไม่แตะ `index.html`/`sw.js`
- push ด้วย `git -c credential.helper= -c credential.helper='!gh auth git-credential' push origin main` (GCM เปิดหน้าต่างที่ agent มองไม่เห็นแล้วค้าง) แล้วเช็ก `curl https://ballg-it.github.io/codecoin/sw.js` ว่าเลข CACHE ขึ้น (~40–60 วิ)

## งานค้าง

- [x] commit + push V6 (`d0ce6b8`) — เว็บจริงเสิร์ฟ v29 แล้ว
- [x] dashboard artifact ซิงก์ V5/V6 + cache v29 + commit ล่าสุด
- [x] `docs/DEVELOPER.md` เลข CACHE → v29
- [x] commit + push V7 (6 ไฟล์ข้างบน) — CACHE `codecoin-v30`
- [ ] **ซิงก์ dashboard V7:** `progress_items` เพิ่มแถว V7 (หมวดดีไซน์ 10/10) · `meta` cache 30 + จำนวน commit · `commits` · `activity`
- [ ] **ลองบนมือถือจริง V5/V6/V7** — เปิด `?space=coding_01&fps=1` แล้วเลือกโหมดมั่นใจ+ตอบผิดให้**วงล้อตัวใหม่**หมุน ดูว่ายัง ≥50 fps (V7 ควรดีขึ้น: หมุนเป็นเลเยอร์ GPU) + ลิ้นชี้สะบัดตามเสียงติ๊ก + ป้ายอ่านออก + หยุดแล้วสปอตไลต์ขึ้น · เลื่อนหน้าที่มีแถบสีโซน (แสงฟุ้ง `filter:blur`) ว่าไม่สะดุดบนเครื่องรุ่นถูก · กด 🐢 แล้วต้องไม่มี confetti / แสงวิ่งบน header / จอสั่นบอสไฟต์ / วงล้อไม่หมุน (ขึ้นผลทันที)
- [ ] commit `scripts/build_dashboard.py` (2 บรรทัด V5/V6) ไปพร้อมงานกล่องของ session นั้น
- [ ] (ค้างมาก่อน V5) `docs/PROJECT_SUMMARY.md` บรรทัด ~358 ยังเขียน "ตอนนี้ `codecoin-v25` → ครั้งหน้า `v26`" — ไฟล์นี้มีของ session อื่นค้างอยู่ แก้ได้แต่ห้าม commit ปน
