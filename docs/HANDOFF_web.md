# Handoff — ความสวยงาม + animation เว็บเกม (Stage V5 → V6, session 4 พ.ย. 2026)

> คนละเรื่องกับ `docs/HANDOFF.md` (บอร์ดนำเสนอ) และ `docs/HANDOFF_forms.md` (แบบประเมิน)

## สถานะ

- **V5** commit **`c89b496`** push + ขึ้นเว็บจริงแล้ว (CACHE `codecoin-v28`)
- **V6 (รอบนี้) ยังไม่ commit** — user สั่ง "จัดการด้านความสวยงามต่อ และจัดการด้าน animation ต่อด้วย"
  ไฟล์ที่เป็นของงานนี้: `index.html`, `sw.js` (CACHE **`codecoin-v29`**), `docs/DESIGN_AUDIT.md` (หัวข้อ Stage V6),
  `docs/animation.md` (หัวข้อ Stage V6 + แก้หัวเอกสารที่ค้างสถานะเก่า), `docs/DEVELOPER.md` (เลข CACHE), ไฟล์นี้
- รายละเอียดเต็ม + ผลตรวจรับ: `docs/DESIGN_AUDIT.md` หัวข้อ **Stage V5** และ **Stage V6**

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

1. **ห้ามเปลี่ยนขนาดกล่อง** — padding / margin / border-width / font-size / line-height / letter-spacing / ฟอนต์ ห้ามแตะ เพราะ bugjam ยาก (631px) กับ upgrade-quiz (630.3px) เหลือ headroom ~9px ที่จอ 360×640 · ที่ใช้ได้: สี, background, box-shadow, outline, text-shadow, filter, transform ตอน `:active`
2. animation/transition = `transform`/`opacity` เท่านั้น duration ต้องเป็น token (`--dur-press` ฯลฯ) — ห้าม transition สี/เงา · ของประดับที่ไม่ผ่าน token (ตั้งเวลาเองใน JS) ต้องเช็ค `MOTION.reduced` เอง · ของประดับ T0 (`--dur-ambient`) โหมดลด = ปิดทั้งชิ้น
3. `var(--bad)` (แดง) = แย่สำหรับผู้เล่นเท่านั้น (กฎ V3b)
4. hex ดิบอยู่ใน `:root` เท่านั้น — ข้อยกเว้นเดียว: ใน data URI (`--pcb-traces`) ใช้ `var()` ไม่ได้ ต้องเขียน `%23xxxxxx`
5. `color:transparent` ของชื่อเกมต้องอยู่ใน `@supports (background-clip:text)` เท่านั้น ไม่งั้นเบราว์เซอร์เก่าชื่อหายทั้งคำ · ห้าม text-shadow กับตัวหนังสือ background-clip (เงาวาดทับ gradient) ใช้ `filter:drop-shadow` แทน
6. ลายวงจร: เส้นที่ทะลุขอบแผ่นมีแต่แนวนอน (เส้นวนแนวนอน + แนวตั้งบนแผ่นที่ต่อกันวนรอบ ตัดกันแน่นอน) · เส้นวิ่งกลางช่องกริด (14 + 28k) แผ่นต้องเป็นทวีคูณ 28
7. **ห้ามทำ `.choice:disabled` ให้จาง** — event speed ปิดปุ่มตัวเลือกตั้งแต่แรก (โชว์ให้อ่านอย่างเดียว) จะจางทั้งข้อ
8. แก้ `index.html` → บั๊ม `CACHE` ใน `sw.js` (ตอนนี้ v29 → ครั้งหน้า v30)
9. สีให้การ์ดตามบริบท → ใช้สีป้าย `.zone-tag` ผ่าน `background:inherit` ไม่ต้องส่งตัวแปรสีจาก JS · หน้าที่วาดทั้งก้อนใหม่ทุกคลิกเรียก `enterScreen()` แค่ครั้งแรก

## วิธีพิสูจน์ว่า layout ไม่ขยับ (ใช้ซ้ำได้)

1. `git show HEAD:index.html > __old_index.html` ที่รากรีโป (server เดียวกันเสิร์ฟได้ + same-origin ให้ iframe อ่าน DOM ได้)
2. `preview_start {name:"codecoin"}` (port 8123) แล้ว unregister service worker + `caches.delete()` ก่อน
3. วางสคริปต์ข้างล่างใน `javascript_tool` → ได้ผล 15 หน้า `same:true` ทุกหน้า = layout ตรงไฟล์เดิมทุก element
4. **ลบ `__old_index.html` ทิ้งเสมอ** ห้ามหลุดเข้า commit

```js
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function measure(page, cases) {
  const finishAll = d => d.getAnimations().forEach(a => { try { a.finish(); } catch (e) {} });
  const out = {};
  for (const c of cases) {
    sessionStorage.clear();
    try { localStorage.setItem('cc_player_asked', '1'); localStorage.removeItem('cc_player'); } catch (e) {}
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
    const rows = [...d.querySelectorAll('header, #screen *, .footer-note')].map(e => {
      const r = e.getBoundingClientRect();
      return e.tagName + ':' + r.top.toFixed(1) + ':' + r.height.toFixed(1) + ':' + r.left.toFixed(1) + ':' + r.width.toFixed(1);
    });
    const btns = [...d.querySelectorAll('#screen button, #screen .menu-item')].filter(b => b.offsetParent);
    out[c.name] = { rows, err, lastBottom: btns.length ? +Math.max(...btns.map(b => b.getBoundingClientRect().bottom)).toFixed(1) : null };
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
];
const A = await measure('/__old_index.html', cases), B = await measure('/', cases);
Object.fromEntries(cases.map(c => {
  const a = A[c.name], b = B[c.name];
  const diffs = a.rows.map((r, i) => r === b.rows[i] ? null : [r, b.rows[i]]).filter(Boolean);
  return [c.name, { same: !diffs.length && a.rows.length === b.rows.length,
    lastBottom: [a.lastBottom, b.lastBottom], err: [a.err, b.err], firstDiffs: diffs.slice(0, 3) }];
}))
```

ค่า `lastBottom` อ้างอิง ณ v28 = v29 (V6 ไม่ขยับสักหน้า) (สั่ง finish animation แล้ว): menu 1595.3 · mode_select 575.4 · quiz_buy 470 · upgrade_ready 543.6 · **upgrade_quiz 630.3** · bugjam_select 318.1 · **bugjam_hard 631** · bugjam_easy 593 · event_coding 649.1 · event_design 592.1 · cooling 1046.7 · rescue_landing 897.3 · rescue_final 1131.9 · rescue_solver 484.1 · rescue_guide 507.8

## ข้อควรรู้เรื่อง browser pane

- **เปิดหน้าตรง ๆ ใน tab หลักต้องเติม `&nc=<เลขใหม่>` ทุกครั้ง** — http.server ของ Python ส่ง Last-Modified แล้ว HTTP cache ของเบราว์เซอร์คืน index.html รุ่นเก่า (เห็นหน้าไม่มีลายวงจร) แม้ล้าง SW แล้ว สคริปต์วัดข้างบนใส่ `nocache=` ให้อยู่แล้ว
- อยากเห็น animation กลางทาง (เช่นแสงวิ่ง) ให้ใส่ `<style>` ชั่วคราวตรึง `transform` แทนการ `pause()` + `currentTime` — pane ไม่วาดเฟรมใหม่ให้ animation ที่หยุดไว้
- screenshot มักได้**เฟรมเก่า 1 จังหวะ** (เห็นสไตล์เก่า / หน้าก่อนกด / การ์ดพลิกค้างกลางทางจนเหมือนการ์ดหาย) → ถ่ายซ้ำ หรือถ่าย `scale:0.1` ทิ้งหนึ่งครั้งก่อนถ่ายจริง และเช็กด้วย `javascript_tool` ก่อนสรุปว่าพัง
- pane ที่ไม่ได้วาดเฟรม → WAAPI ค้างที่จุดเริ่ม → `enterScreen()` ค้างที่ `translateY(12px)` ตัวเลขทั้งหน้าคลาด 12px (ไม่ใช่ CSS เปลี่ยน) — ต้อง `finish()` ก่อนวัดเสมอ
- navigate ใน tab หลักเมื่อไร ตัวแปรที่แขวนไว้บน `window` (เช่น baseline) หายหมด — จดค่าที่ต้องเทียบไว้ใน output ก่อน
- คลิกด้วย `find` → `ref` แม่นกว่าพิกัด · เทสต์ขนาดมือถือแล้วคืนด้วย `resize_window preset:"desktop"`

## สถานะ repo ณ ตอนเขียน

- `main` = `origin/main` = `c89b496` (V5) · งาน V6 ยังอยู่ใน working tree
- **ค้างจาก session อื่น — ห้าม commit ปนกับงานเว็บ:** `M README.md` `M docs/BOX_DEMO.md` `M docs/PROJECT_SUMMARY.md` `M scripts/build_dashboard.py` `M tools/backdrop_3d.html` · `?? docs/HANDOFF_box.md` `?? docs/HANDOFF_forms.md` `?? print/box/` `?? print/forms/` `?? scripts/build_box.py`
- `?? docs/HANDOFF_web.md` = ไฟล์นี้
- บน remote มี branch `origin/claude/vigilant-mendel-7905kw` = งานบอร์ดนำเสนอ แตกออกไปก่อน `backdrop_3d.html` เข้า `main` → ถ้าจะรวมจะชน · ไม่แตะ `index.html`/`sw.js`

## งานค้าง

- [ ] **commit + push V6** (ไฟล์ตามรายการในหัวข้อสถานะเท่านั้น) แล้วเช็ก curl ว่า `sw.js` = v29
- [ ] **dashboard artifact "เวอร์ชันและสถิติ repo"** (https://claude.ai/artifact/FPwJk2whrenDjhGgKDvpAz) ยังไม่มี V5/V6 และเลข cache ยังเป็น v27 — เพิ่ม 2 บรรทัดต่อจาก Stage V4 ใน `scripts/build_dashboard.py` (~บรรทัด 67): `T("Design Stage V5: ความสวยงาม ลายวงจร/header ชิป/ปุ่มนูน (CACHE v28)", True)` + `T("Design Stage V6: แถบสีโซน/จอเทอร์มินัล/สายไฟ/หลอดพลัง + animation ผลลัพธ์/modal/แสงวิ่ง + แก้ confetti โหมดลด (CACHE v29)", True)` — ⚠️ ไฟล์นี้มีของ session งานกล่องค้างอยู่ (ยังไม่ commit) แก้ได้แต่ห้าม commit ปน · แล้วอัปเดต artifact วิธีเดิม: download asset → แก้ JSON → upload → `ArtifactData update` (ห้าม publish file_path)
- [x] `docs/DEVELOPER.md` เลข CACHE → v29 (ทำใน V6)
- [ ] (ค้างมาก่อนรอบนี้) `docs/PROJECT_SUMMARY.md` บรรทัด 358 ยังเขียน "ตอนนี้ `codecoin-v25` → ครั้งหน้า `v26`"
- [ ] ยังไม่ได้ลองบนมือถือจริงทั้ง V5/V6 — ดูว่าเงา/gradient/แสงฟุ้ง (`filter:blur` ใต้แถบสีโซน) ไม่ทำให้เลื่อนหน้าหรือวงล้อสะดุดบนเครื่องรุ่นถูก (หน้ามีวงล้อ + `&fps=1`) และกดปุ่ม 🐢 แล้วไม่มี confetti/แสงวิ่ง/จอสั่น
