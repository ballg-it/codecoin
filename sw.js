/* =====================================================================
   sw.js — Service Worker ของ CodeCoin (เน็ตโรงเรียนล่มกลางคาบก็ยังเล่นต่อได้)
   ---------------------------------------------------------------------
   ⚠️ สำคัญ: แก้ index.html / sw.js / ไอคอน เมื่อไร ต้อง "บั๊มเลขท้าย CACHE
      ข้างล่างขึ้น 1" ทุกครั้ง ไม่งั้นเครื่องที่เคยเปิดแล้วจะยังเห็นของเก่าจาก
      cache (data.json ไม่ต้องบั๊ม — เป็น network-first อยู่แล้ว)

   กติกา cache:
     - หน้าเว็บที่เปิดผ่าน QR/ลิงก์ (navigate)  = network-first รอไม่เกิน 3 วิ → ได้โค้ดล่าสุดเสมอเมื่อมีเน็ต
                                                  (เก็บลงแคชเฉพาะหน้าเกม / กับ /index.html — v23)
     - ไฟล์ประกอบ (qrcode.js + ไอคอน + manifest) = cache-first  → เปิดไวและออฟไลน์ได้
     - data.json                                = network-first → เนื้อหาอัปเดตบ่อย
   ทุก path เป็น relative ล้วน เพราะ deploy บน GitHub Pages แบบ subpath (/codecoin/)
   ===================================================================== */
const CACHE = 'codecoin-v26';

const SHELL = [
  './',
  './index.html',
  './qrcode.js',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
];

const isData = url => url.pathname.endsWith('data.json');
const SCOPE_PATH = new URL('./', self.location).pathname;   // '/codecoin/' บน Pages · '/' ตอนรันในเครื่อง
const isShellPage = url => url.pathname === SCOPE_PATH || url.pathname === SCOPE_PATH + 'index.html';

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    // ใส่ทีละไฟล์ (ไม่ใช้ addAll) — ไฟล์เดียวพลาดจะได้ไม่ทำให้ติดตั้งล้มทั้งชุด
    await Promise.all(SHELL.map(u => c.add(u).catch(err => console.warn('[sw] ข้าม', u, err))));
    await c.add('./data.json').catch(() => {});  // เก็บสำรองไว้ตั้งแต่แรก เผื่อเน็ตหลุดก่อนเล่นรอบสอง
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));  // ล้างเวอร์ชันเก่า
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;          // POST/beacon (logAnswer) ปล่อยผ่านตามปกติ
  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;

  // ---------- data.json: เอาของใหม่ก่อน ถ้าเน็ตล่มค่อยใช้ของที่เก็บไว้ ----------
  if (sameOrigin && isData(url)) {
    e.respondWith((async () => {
      try {
        const res = await fetch(req);
        if (res && res.ok) (await caches.open(CACHE)).put(req, res.clone());
        return res;
      } catch (err) {
        return (await caches.match(req, { ignoreSearch: true }))
            || (await caches.match('./data.json'))
            || new Response('{}', { headers: { 'Content-Type': 'application/json' } });
      }
    })());
    return;
  }

  // ---------- ไฟล์ในโดเมนเดียวกัน: cache-first + อัปเดตเงียบเบื้องหลัง ----------
  // ignoreSearch สำคัญมาก — ทุก route ของแอปเป็น query string (?space=coding_01)
  // ถ้าไม่เปิดไว้ '/codecoin/?space=x' จะไม่ match กับ './' ที่ cache ไว้ → ออฟไลน์แล้วจอขาว
  //
  // ที่ยิงเน็ตซ้ำเบื้องหลังทั้งที่ตอบจากแคชไปแล้ว เพราะกันเคส "ลืมบั๊ม CACHE":
  // ถ้าไม่ทำ เครื่องที่เคยเปิดเว็บจะติดโค้ดเวอร์ชันเก่าถาวรจนกว่า sw.js จะเปลี่ยน
  // ทำแบบนี้แล้วอย่างช้าสุดคือได้ของใหม่ตอนเปิดรอบถัดไป
  // ---------- หน้าเว็บ (เปิดผ่าน QR/ลิงก์): เน็ตก่อน รอไม่เกิน 3 วิ แล้วค่อยใช้แคช ----------
  // เหตุผล: cache-first ด้านล่างทำให้เครื่องที่เคยเปิดเว็บ "สแกน QR แล้วได้โค้ดเก่า" 1 รอบหลังทุกครั้งที่ deploy
  // (เจอจริงกับห้องรอกู้บั๊กด่วน: เครื่องเพื่อนสแกน QR แล้วเข้าเกมตรง ๆ ข้ามห้องรอ) — ออฟไลน์/เน็ตช้ายังได้แคชเหมือนเดิม
  if (sameOrigin && req.mode === 'navigate') {
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      try {
        const res = await Promise.race([
          fetch(req),
          new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 3000)),
        ]);
        // เก็บเป็น app shell เฉพาะหน้าเกมจริง (/ หรือ /index.html) — scope ครอบทั้ง repo
        // ถ้าไม่กรอง เปิด tools/dashboard.html หรือ box_demo/*.html ในเครื่องเดียวกันแล้ว
        // หน้านั้นจะไปทับแคชหน้าเกม → เน็ตล่มแล้วสแกน QR ได้หน้าเดโมแทนเกม
        if (res && res.ok && res.type === 'basic' && isShellPage(url)) {
          await cache.put('./', res.clone());
          await cache.put('./index.html', res.clone());
        }
        return res;
      } catch (err) {
        return (await caches.match(req, { ignoreSearch: true }))
            || (await cache.match('./index.html', { ignoreSearch: true }))
            || Response.error();
      }
    })());
    return;
  }

  if (sameOrigin) {
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const hit = await caches.match(req, { ignoreSearch: true });

      const fresh = fetch(req).then(async res => {
        if (res && res.ok && res.type === 'basic') {
          // หน้าเว็บเข้าได้หลาย URL (?space=...) — เขียนทับทั้ง './' และ './index.html'
          // ไม่งั้นตัวที่ ignoreSearch ไปเจอก่อนจะยังเป็นของเก่า
          if (req.mode === 'navigate') {
            await cache.put('./', res.clone());
            await cache.put('./index.html', res.clone());
          } else {
            await cache.put(req, res.clone());
          }
        }
        return res;
      }).catch(() => null);

      if (hit) { e.waitUntil(fresh); return hit; }   // มีในแคช = ตอบทันที ค่อยอัปเดตทีหลัง

      const res = await fresh;
      if (res) return res;
      if (req.mode === 'navigate') {
        const shell = await cache.match('./index.html', { ignoreSearch: true });
        if (shell) return shell;
      }
      return Response.error();
    })());
    return;
  }

  // ---------- ข้ามโดเมน (ฟอนต์ Google): เน็ตก่อน ล่มแล้วใช้ของเก่า ----------
  // ไม่มีในแคชก็ไม่เป็นไร — CSS มี fallback เป็นฟอนต์ระบบอยู่แล้ว
  e.respondWith((async () => {
    try {
      const res = await fetch(req);
      if (res && (res.ok || res.type === 'opaque')) (await caches.open(CACHE)).put(req, res.clone());
      return res;
    } catch (err) {
      const hit = await caches.match(req);
      if (hit) return hit;
      throw err;
    }
  })());
});
