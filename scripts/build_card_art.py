"""ภาพประกอบ 3 มิติของการ์ดแนว TCG ด้วย Blender (Cycles) -> print/cards_tcg/img/

ได้ 2 ไฟล์ต่อใบ:
  art_<id>.jpg       ฉากเต็ม (พื้นแผงวงจร + แสงสีโซน) ใช้ในช่องภาพของแนว A / C
  art_<id>_hero.png  เฉพาะวัตถุ พื้นโปร่ง ใช้กับแนว B (ฟูลอาร์ต)
ใส่ --tall = เรนเดอร์ฉากเดียวกันเป็นแนวตั้งเต็มใบ (วัตถุอยู่ครึ่งบน ครึ่งล่างเป็นพื้นว่างไว้วาง QR)
  art_<id>_tall.jpg  ใช้กับแบบฟูลอาร์ตฉากจริง (B2 / B3) และช่องภาพสูง (A3)

ไฟล์นี้ทำงาน 2 โหมด: รันด้วย py = หา blender.exe แล้วสั่งเรนเดอร์ + แต่งภาพด้วย PIL
รันข้างใน Blender (มี bpy) = สร้างฉากแล้วเรนเดอร์ลงโฟลเดอร์ temp ที่ส่งมา

ใส่ --style <ชื่อ|all> = เรนเดอร์ฉากเดียวกันเป็นสไตล์ภาพอื่น (ดู STYLES) ได้ภาพกว้างอย่างเดียว
  styles/<สไตล์>_<id>.jpg

รัน: py scripts/build_card_art.py [--draft] [--tall] [--style ชื่อ] [id ...]     (ไม่ใส่ id = ทุกใบใน SCENES)
"""
import math
import os
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile

try:
    import bmesh
    import bpy
    from mathutils import Vector
except ImportError:
    bpy = None

# zb สว่าง / zm กลาง / zk เข้ม — ต้องตรงกับ concept.html
ZONE = {
    "coding": ("#4ADE80", "#15803D", "#052E1B"),
    "office": ("#38BDF8", "#1D4ED8", "#0B1B45"),
    "design": ("#FB923C", "#C2410C", "#3B1206"),
    "hardware": ("#F472B6", "#BE185D", "#450A26"),
}
GOLD = "#FBBF24"
W, H = 1320, 800          # ช่องภาพ 54.9 x 33.3 มม. ที่ ~600 dpi
TW, TH = 945, 1320        # ทั้งใบ 63 x 88 มม. ที่ ~380 dpi (โหมด --tall)
TALL = False              # ตั้งใน in_blender()
TALL_DIST, TALL_SHIFT = 1.65, -0.19
R = math.radians

# สไตล์ภาพ — glossy คือชุดเดิม (พลาสติกเงา + นีออน) ที่เหลือคือทางเลือกรอบ 4
STYLES = {
    "toon": "การ์ตูนตัดเส้น",
    "clay": "ดินปั้นพาสเทล",
    "iso": "ไอโซเมตริกโลว์โพลี",
    "blueprint": "พิมพ์เขียว",
    "holo": "โฮโลแกรม",
    "pixel": "พิกเซลอาร์ต",
    "riso": "ภาพพิมพ์เรโทร",
}
STYLE = "glossy"          # ตั้งใน in_blender()
BASE = "glossy"           # วิธีเรนเดอร์ใน Blender (pixel ใช้ toon เส้นหนา)
ZC = ZONE["coding"]       # สีโซนของฉากปัจจุบัน ตั้งใน stage()
PCT = 1.0                 # สัดส่วนความละเอียด (draft = 0.5) ใช้คูณความหนาเส้น
NOLINE = None             # collection ของวัตถุที่ไม่ตัดเส้น (ตัวหนังสือเล็ก) ตั้งใน ink()
RISO_INK = {"coding": "#F59E0B", "office": "#F43F5E", "design": "#0E7490", "hardware": "#1E3A8A"}


def mix(a, b, t):
    A = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    B = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(A, B))


# ───────────────────────── ส่วนที่รันใน Blender ─────────────────────────
_mats = {}


def lin(h):
    """hex sRGB -> linear RGBA"""
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1.0,)


def lum(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def node(nt, kind, inputs=None, **props):
    """สร้างโหนด — inputs = {ชื่อหรือลำดับช่อง: ค่า หรือ ช่องขาออกของโหนดอื่น}"""
    n = nt.nodes.new("ShaderNode" + kind)
    for k, v in props.items():
        setattr(n, k, v)
    for k, v in (inputs or {}).items():
        if isinstance(v, bpy.types.NodeSocket):
            nt.links.new(v, n.inputs[k])
        else:
            n.inputs[k].default_value = v
    return n


def styled(nt, color, rough, emit):
    """โหนดวัสดุของสไตล์ที่ไม่ใช่ Principled — คืนช่องขาออกของ shader"""
    zb, zm, zk = ZC
    if BASE == "toon":
        if emit:
            return node(nt, "Emission", {"Color": lin(color), "Strength": 1.0}).outputs[0]
        d = node(nt, "BsdfToon", {"Color": lin(color), "Size": 0.6, "Smooth": 0.0}, component="DIFFUSE")
        if rough > 0.3:
            return d.outputs[0]
        g = node(nt, "BsdfToon", {"Color": (1, 1, 1, 1), "Size": 0.22, "Smooth": 0.0}, component="GLOSSY")
        return node(nt, "MixShader", {0: 0.1, 1: d.outputs[0], 2: g.outputs[0]}).outputs[0]
    if BASE == "blueprint":     # สีพื้นเดียวทั้งฉาก ให้เส้นเป็นตัวเล่า ส่วนที่เรืองแสงเดิม = ถมสีเส้น
        c = mix(zb, "#FFFFFF", 0.7) if emit else mix(mix(zm, zk, 0.45), zb, 0.13)
        return node(nt, "Emission", {"Color": lin(c), "Strength": 1.0}).outputs[0]
    # holo: ขอบสว่าง กลางโปร่ง
    if emit:
        return node(nt, "Emission", {"Color": lin(mix(color, "#FFFFFF", 0.25)), "Strength": 2.6}).outputs[0]
    c = mix(zb, "#FFFFFF", 0.15) if lum(color) < 0.2 else mix(color, zb, 0.35)
    face = node(nt, "LayerWeight", {"Blend": 0.32}).outputs["Facing"]
    power = node(nt, "Math", {0: face, 1: 5.0, 2: 0.22}, operation="MULTIPLY_ADD").outputs[0]
    fac = node(nt, "Math", {0: face, 1: 1.1, 2: 0.2}, operation="MULTIPLY_ADD", use_clamp=True).outputs[0]
    em = node(nt, "Emission", {"Color": lin(c), "Strength": power}).outputs[0]
    return node(nt, "MixShader", {0: fac, 1: node(nt, "BsdfTransparent").outputs[0], 2: em}).outputs[0]


def mat(color, rough=0.35, metal=0.0, emit=0.0, raw=False):
    """raw = ใช้ Principled ตรง ๆ ไม่แปลงตามสไตล์ (พื้นของสไตล์ holo)"""
    key = (color, rough, metal, emit, raw)
    if key not in _mats:
        m = bpy.data.materials.new(color)
        if m.node_tree is None:        # Blender < 5 ต้องเปิดโหนดเอง
            m.use_nodes = True
        nt = m.node_tree
        if not raw and BASE in ("toon", "blueprint", "holo"):
            nt.nodes.clear()
            nt.links.new(styled(nt, color, rough, emit), nt.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
            _mats[key] = m
            return m
        if not raw and BASE == "clay":      # ด้าน ไม่มีโลหะ สีดำ -> สีโซน แล้วผสมขาวให้นุ่ม
            color = mix(mix(color, ZC[1], 0.6) if lum(color) < 0.1 else color, "#FFFFFF", 0.2)
            rough, metal, emit = 0.92, 0.0, emit * 0.12
        if not raw and BASE == "iso":
            rough, metal, emit = 0.85, 0.0, emit * 0.5
        b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = lin(color)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        if emit:
            b.inputs["Emission Color"].default_value = lin(color)
            b.inputs["Emission Strength"].default_value = emit
        _mats[key] = m
    return _mats[key]


def obj(data, m=None, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    o = bpy.data.objects.new("o", data)
    o.location = loc
    o.rotation_euler = rot
    if parent is not None:
        o.parent = parent
    if m is not None:
        data.materials.append(m)
    bpy.context.scene.collection.objects.link(o)
    return o


def empty(**kw):
    return obj(None, **kw)


def mesh(bm, m, smooth=None, bevel=0.0, **kw):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("m")
    bm.to_mesh(me)
    bm.free()
    if smooth and BASE != "iso":           # iso = โลว์โพลี หน้าเหลี่ยมทั้งหมด
        for p in me.polygons:
            p.use_smooth = smooth == "all" or len(p.vertices) == 4
    o = obj(me, m, **kw)
    if bevel and BASE not in ("toon", "blueprint", "iso"):      # สไตล์ตัดเส้นต้องการสันคม
        md = o.modifiers.new("bevel", "BEVEL")
        md.width = bevel
        md.segments = 5 if BASE == "clay" else 3
    return o


def box(sx, sy, sz, m, bevel=0.03, **kw):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts[:])
    k = 2.2 if BASE == "clay" else 1.0      # ดินปั้น = มุมมนอ้วน
    return mesh(bm, m, bevel=min(bevel * k, 0.45 * min(sx, sy, sz)), **kw)


def cyl(r, h, m, r2=None, seg=64, **kw):
    if BASE == "iso":
        seg = min(seg, 12)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r if r2 is None else r2, depth=h)
    return mesh(bm, m, smooth="all" if r2 == 0 else "side", **kw)


def sphere(r, m, **kw):
    bm = bmesh.new()
    u, v = (10, 6) if BASE == "iso" else (48, 24)
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    return mesh(bm, m, smooth="all", **kw)


def torus(R_, r, m, seg=72, ring=14, **kw):
    if BASE == "iso":
        seg, ring = 14, 5
    bm = bmesh.new()
    vs = [[bm.verts.new(((R_ + r * math.cos(b)) * math.cos(a), (R_ + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
           for b in (2 * math.pi * j / ring for j in range(ring))]
          for a in (2 * math.pi * i / seg for i in range(seg))]
    for i in range(seg):
        for j in range(ring):
            i2, j2 = (i + 1) % seg, (j + 1) % ring
            bm.faces.new((vs[i][j], vs[i2][j], vs[i2][j2], vs[i][j2]))
    return mesh(bm, m, smooth="all", **kw)


def prism(pts, h, m, bevel=0.02, **kw):
    """แท่งจากรูปหลายเหลี่ยม 2 มิติ (ระนาบ XY) หนา h ตามแกน Z"""
    bm = bmesh.new()
    b = [bm.verts.new((x, y, 0)) for x, y in pts]
    t = [bm.verts.new((x, y, h)) for x, y in pts]
    bm.faces.new(b[::-1])
    bm.faces.new(t)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((b[i], b[j], t[j], t[i]))
    return mesh(bm, m, bevel=bevel, **kw)


def wedge(r0, r1, a0, a1, h, m, seg=10, **kw):
    arc = [a0 + (a1 - a0) * i / seg for i in range(seg + 1)]
    pts = [(r1 * math.cos(a), r1 * math.sin(a)) for a in arc] + [(r0 * math.cos(a), r0 * math.sin(a)) for a in arc[::-1]]
    return prism(pts, h, m, **kw)


def font(fn):
    p = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", fn)
    return bpy.data.fonts.load(p, check_existing=True) if os.path.exists(p) else None


def text(body, size, depth, m, fn=None, bevel=0.015, **kw):
    cu = bpy.data.curves.new("t", "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = depth / 2
    cu.bevel_depth = 0 if BASE in ("toon", "blueprint", "iso") else bevel
    cu.bevel_resolution = 2
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    f = font(fn) if fn else None
    if f:
        cu.font = f
    o = obj(cu, m, **kw)
    if NOLINE is not None and size < 0.6:
        NOLINE.objects.link(o)
    return o


def tube(pts, radius, m, **kw):
    cu = bpy.data.curves.new("c", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    cu.resolution_u = 24
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    return obj(cu, m, **kw)


def aim(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()


def light(kind, loc, energy, color, target=(0, 0, 1), size=4.0, spot=70):
    L = bpy.data.lights.new("L", kind)
    L.energy = energy
    L.color = lin(color)[:3]
    if kind == "SUN":
        L.angle = R(size)
    if kind == "AREA":
        L.size = size
    if kind == "SPOT":
        L.spot_size = R(spot)
        L.spot_blend = 1.0
        L.shadow_soft_size = 1.0
    o = obj(L, loc=loc)
    aim(o, target)
    return o


def stage(zone, az=-18, el=27, dist=12.5, target=(0, 0, 1.05), draft=False):
    """ล้างฉาก ตั้งค่าเรนเดอร์ กล้อง ไฟ พื้นแผงวงจร — คืนรายการวัตถุพื้น (ซ่อนตอนเรนเดอร์แบบพื้นโปร่ง)"""
    global ZC, NOLINE
    NOLINE = None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()
    zb, zm, zk = ZC = ZONE[zone]
    if BASE != "glossy":
        return stage_styled(zone, az, el, dist, target, draft)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 40 if draft else 128
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = (TW, TH) if TALL else (W, H)
    sc.render.resolution_percentage = 50 if draft else 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"      # สีตรงกับพาเลตต์ (AgX ทำสีซีด)

    world = bpy.data.worlds.new("w")
    if world.node_tree is None:
        world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = lin(mix(zm, "#FFFFFF", 0.35))
    bg.inputs["Strength"].default_value = 0.16
    sc.world = world

    cam = bpy.data.cameras.new("cam")
    cam.lens = 70
    cam.sensor_width = 36
    co = obj(cam)
    if TALL:                  # ถอยกล้องให้ความกว้างฉากเท่าเดิม แล้วเลื่อนเฟรมลงให้วัตถุอยู่ครึ่งบน
        dist *= TALL_DIST
        cam.shift_y = TALL_SHIFT
    a, e = R(az), R(el)
    co.location = Vector(target) + dist * Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    aim(co, target)
    sc.camera = co

    light("AREA", (-5.5, -6.5, 7.5), 1700, "#FFF4E0", target, size=6)          # หลัก อุ่น
    light("AREA", (6.5, 5.0, 5.0), 2000, zb, target, size=5)                    # ขอบ สีโซน
    light("AREA", (5.0, -7.0, 2.0), 300, "#FFFFFF", target, size=6)             # เติมเงา
    light("SPOT", (0.0, -0.5, 9.0), 3800, mix(zb, "#FFFFFF", 0.2), (0, -0.2, 0), spot=62)   # วงแสงบนพื้น

    floor = [box(80, 80, 0.2, mat(mix(zm, zk, 0.78), rough=0.4), bevel=0, loc=(0, 0, -0.1))]
    trace, pad = mat(zb, rough=0.4, emit=1.6), mat(GOLD, rough=0.3, metal=0.9)
    rng = random.Random(zone)
    w = 0.075
    for i in range(18):
        th = 2 * math.pi * i / 18 + rng.uniform(-0.1, 0.1)
        r0 = rng.uniform(2.2, 3.8)
        p = Vector((r0 * math.cos(th), r0 * math.sin(th) * 0.85, 0))
        d = round(th / (math.pi / 4)) * (math.pi / 4)
        floor.append(cyl(0.14, 0.03, pad, loc=(p.x, p.y, 0.012)))
        for length, turn in ((rng.uniform(0.7, 1.9), 0), (40, rng.choice((-1, 1)))):
            d += turn * math.pi / 4
            q = p + length * Vector((math.cos(d), math.sin(d), 0))
            mid = (p + q) / 2
            floor.append(box(length + w, w, 0.014, trace, bevel=0, loc=(mid.x, mid.y, 0.006), rot=(0, 0, d)))
            p = q
    return floor


def ink(color, px, crease=True):
    """เส้นขอบ Freestyle (เงาร่าง + ขอบ + สันคม) หนา px ที่ความละเอียดเต็ม"""
    global NOLINE
    sc = bpy.context.scene
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = 1.0
    fs = bpy.context.view_layer.freestyle_settings
    fs.use_smoothness = True
    ls = fs.linesets.new("ink")
    ls.select_silhouette = ls.select_border = True
    ls.select_crease = crease
    ls.linestyle.color = lin(color)[:3]
    ls.linestyle.thickness = max(1.0, px * PCT)
    if BASE == "toon":          # พิมพ์เขียวตัดเส้นทุกชิ้น ส่วนการ์ตูนเว้นตัวหนังสือเล็ก
        NOLINE = bpy.data.collections.new("noline")
        sc.collection.children.link(NOLINE)
        ls.select_by_collection = True
        ls.collection = NOLINE
        ls.collection_negation = "EXCLUSIVE"


def stage_styled(zone, az, el, dist, target, draft):
    """ฉากของสไตล์ทางเลือก (BASE = toon / clay / iso / blueprint / holo) — กล้องมุมเดิม ยกเว้น iso"""
    zb, zm, zk = ZC
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = (24 if draft else 96) if BASE in ("clay", "iso", "holo") else (12 if draft else 48)
    sc.cycles.use_denoising = True
    sc.cycles.transparent_max_bounces = 24
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 50 if draft else 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.film_transparent = BASE in ("blueprint", "iso")
    sc.view_settings.view_transform = "Standard"

    world = bpy.data.worlds.new("w")
    if world.node_tree is None:
        world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    wcol, wstr = {"toon": ("#FFFFFF", 0.62), "clay": (mix(zb, "#FFFFFF", 0.8), 0.42), "iso": (mix(zb, "#FFFFFF", 0.7), 0.6),
                  "blueprint": ("#000000", 0.0), "holo": ("#000000", 0.0)}[BASE]
    bg.inputs["Color"].default_value = lin(wcol)
    bg.inputs["Strength"].default_value = wstr
    sc.world = world

    cam = bpy.data.cameras.new("cam")
    cam.lens = 70
    cam.sensor_width = 36
    co = obj(cam)
    if BASE == "iso":
        cam.type = "ORTHO"
        cam.ortho_scale = 10.7
        az, el, target = math.copysign(27, az), 31, (0, -0.1, 0.75)
    a, e = R(az), R(el)
    co.location = Vector(target) + dist * Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    aim(co, target)
    sc.camera = co

    if BASE == "blueprint":
        ink(mix(zb, "#FFFFFF", 0.7), 2.6)
        return []
    floor, rng, w = [], random.Random(zone), 0.075
    if BASE == "toon":
        ink(mix(zk, "#000000", 0.45), 8.0 if STYLE == "pixel" else 3.8)
        light("SUN", (-5, -6, 9), 2.1, "#FFFFFF", target, size=0.8)
        floor_m, trace, pad, th = mat(mix(zm, zk, 0.42), rough=0.6), mat(mix(zb, zm, 0.25), emit=1), mat(GOLD, rough=0.6), 0.014
        if STYLE == "riso":     # พื้นสว่าง = กระดาษ ให้หมึกไปอยู่ที่วัตถุ
            floor_m, trace = mat(mix(zb, "#FFFFFF", 0.86), rough=0.6), mat(mix(zb, "#FFFFFF", 0.45), emit=1)
    elif BASE == "clay":
        light("AREA", (-5.5, -6.5, 8.5), 1150, "#FFF6E8", target, size=9)
        light("AREA", (6.5, 4.0, 5.0), 260, mix(zb, "#FFFFFF", 0.5), target, size=7)
        floor_m, trace, pad, th = mat(mix(zb, "#FFFFFF", 0.42), rough=1), mat(mix(zb, "#FFFFFF", 0.05), rough=1), mat("#FFFFFF", rough=1), 0.07
    elif BASE == "iso":
        light("SUN", (-6, -5, 9), 3.2, "#FFF4E0", target, size=2.5)
        floor.append(box(7.5, 5.6, 0.5, mat(mix(zm, zk, 0.62)), loc=(0, -0.1, -0.25)))
        floor.append(box(8.0, 6.1, 0.3, mat(GOLD), loc=(0, -0.1, -0.65)))
        floor_m, trace, pad, th = None, mat(zb, emit=1.2), mat(GOLD), 0.03
    else:   # holo
        light("AREA", (0, -4, 9), 250, zb, target, size=8)
        floor_m, trace, pad, th = mat(mix(zk, "#000000", 0.72), rough=0.16, raw=True), mat(zb, emit=1), mat(mix(zb, "#FFFFFF", 0.4), emit=1), 0.014
    if floor_m:
        floor.append(box(80, 80, 0.2, floor_m, bevel=0, loc=(0, 0, -0.1)))
    inside = lambda v: abs(v.x) < 3.6 and abs(v.y + 0.1) < 2.65
    for i in range(18):
        ang = 2 * math.pi * i / 18 + rng.uniform(-0.1, 0.1)
        r0 = rng.uniform(2.2, 3.8)
        p = Vector((r0 * math.cos(ang), r0 * math.sin(ang) * 0.85, 0))
        d = round(ang / (math.pi / 4)) * (math.pi / 4)
        if BASE == "iso" and not inside(p):
            continue
        floor.append(cyl(0.14, th + 0.03, pad, loc=(p.x, p.y, (th + 0.03) / 2)))
        for length, turn in ((rng.uniform(0.7, 1.9), 0), (40, rng.choice((-1, 1)))):
            d += turn * math.pi / 4
            if BASE == "iso":                   # ตัดลายวงจรให้จบในแท่น
                length = min(length, 1.2)
            q = p + length * Vector((math.cos(d), math.sin(d), 0))
            if BASE == "iso" and not inside(q):
                break
            mid = (p + q) / 2
            floor.append(box(length + w, w, th, trace, bevel=0, loc=(mid.x, mid.y, th / 2), rot=(0, 0, d)))
            p = q
    return floor


# ───────────────────────── ฉากรายใบ ─────────────────────────
def scene_coding_01(draft):
    """HTML & CSS เบื้องต้น — หน้าต่างเบราว์เซอร์ + </> ตัวนูน + ป้ายแท็ก"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", dist=14.6, target=(0, 0, 1.2), draft=draft)
    win = box(3.9, 0.24, 2.7, mat("#06231A", rough=0.25), bevel=0.07, loc=(0, 0.75, 1.5), rot=(R(-10), 0, 0))
    box(3.9, 0.28, 0.46, mat("#22A95C", rough=0.35), bevel=0.07, loc=(0, -0.01, 1.12), parent=win)
    for i, c in enumerate(("#F87171", GOLD, "#86EFAC")):
        sphere(0.095, mat(c, rough=0.3, emit=0.6), loc=(-1.65 + 0.3 * i, -0.15, 1.12), parent=win)
    box(3.55, 0.05, 1.95, mat("#0D3B2A", rough=0.5), bevel=0.02, loc=(0, -0.12, -0.2), parent=win)
    for i, (x0, wd, c) in enumerate(((-1.55, 1.1, zb), (-1.25, 1.7, "#E2F9EA"), (-1.25, 1.2, GOLD), (-1.25, 2.0, "#E2F9EA"),
                                     (-1.55, 0.8, zb))):
        box(wd, 0.04, 0.1, mat(c, rough=0.4, emit=0.5), bevel=0.02, loc=(x0 + wd / 2, -0.16, 0.5 - 0.3 * i), parent=win)
    code, gold = mat(zb, rough=0.28), mat(GOLD, rough=0.22, metal=0.85)
    for ch, x, m in (("<", -1.22, code), ("/", 0.0, gold), (">", 1.22, code)):
        text(ch, 2.3, 0.34, m, "consolab.ttf", bevel=0.03, loc=(x, -0.95, 0.95), rot=(R(82), 0, 0))
    chip, white = mat("#082A1D", rough=0.3), mat("#F0FFF6", rough=0.4, emit=0.8)
    for label, loc, rz in (("<h1>", (-2.9, -0.4, 2.0), 14), ("{ }", (2.95, -1.0, 0.6), -16), (".css", (-2.75, -1.3, 0.55), 18)):
        t = box(1.15, 0.14, 0.52, chip, bevel=0.06, loc=loc, rot=(R(-10), 0, R(rz)))
        text(label, 0.36, 0.05, white, "consolab.ttf", bevel=0.004, loc=(0, -0.085, -0.01), rot=(R(90), 0, 0), parent=t)
    return floor


def scene_office_01(draft):
    """Word จัดหน้าเอกสาร — หน้ากระดาษจัดรูปแบบ + ตัวอักษร Aa + ดินสอ"""
    zb, zm, zk = ZONE["office"]
    floor = stage("office", dist=14.6, target=(-0.1, 0, 1.25), draft=draft)
    box(2.35, 0.05, 3.05, mat("#C7D2E4", rough=0.6), bevel=0.02, loc=(-0.95, 1.05, 1.62), rot=(R(-13), 0, R(-5)))
    page = box(2.35, 0.06, 3.05, mat("#F8FAFC", rough=0.55), bevel=0.02, loc=(-1.25, 0.6, 1.62), rot=(R(-13), 0, R(7)))
    y = -0.045
    box(1.35, 0.04, 0.22, mat(zm, rough=0.4), bevel=0.02, loc=(-0.3, y, 1.18), parent=page)
    grey = mat("#94A3B8", rough=0.6)
    for i, wd in enumerate((1.95, 1.75, 1.95, 1.2)):
        box(wd, 0.03, 0.075, grey, bevel=0.01, loc=(-0.975 + wd / 2, y, 0.86 - 0.16 * i), parent=page)
    box(0.85, 0.05, 0.62, mat(zb, rough=0.35), bevel=0.03, loc=(-0.55, y, -0.1), parent=page)
    for i, wd in enumerate((0.95, 0.8, 0.95, 0.6)):
        box(wd, 0.03, 0.075, grey, bevel=0.01, loc=(0.03 + wd / 2, y, 0.14 - 0.16 * i), parent=page)
    for i, wd in enumerate((1.95, 1.95, 1.05)):
        box(wd, 0.03, 0.075, grey, bevel=0.01, loc=(-0.975 + wd / 2, y, -0.68 - 0.16 * i), parent=page)
    box(0.5, 0.03, 0.06, mat(GOLD, rough=0.4), bevel=0.01, loc=(0, y, -1.3), parent=page)
    text("A", 2.5, 0.4, mat("#2563EB", rough=0.25), "ariblk.ttf", bevel=0.035, loc=(1.25, -0.75, 0.93), rot=(R(84), 0, R(-8)))
    text("a", 1.9, 0.34, mat(GOLD, rough=0.22, metal=0.85), "ariblk.ttf", bevel=0.03, loc=(2.6, -1.1, 0.54), rot=(R(84), 0, R(-14)))
    tile = box(1.1, 0.14, 1.1, mat("#0B1B45", rough=0.3), bevel=0.07, loc=(3.0, 0.4, 1.55), rot=(R(-10), 0, R(-14)))
    for i, wd in enumerate((0.74, 0.5, 0.66, 0.38)):
        box(wd, 0.05, 0.1, mat("#F0F9FF", rough=0.4, emit=0.8), bevel=0.02, loc=(-0.37 + wd / 2, -0.08, 0.3 - 0.2 * i), parent=tile)
    pen = empty(loc=(0.2, -1.5, 0.105), rot=(0, R(90), R(16)))
    cyl(0.1, 1.9, mat(GOLD, rough=0.35), seg=6, parent=pen)
    cyl(0.1, 0.3, mat("#F2CFA0", rough=0.6), r2=0.03, seg=24, loc=(0, 0, 1.1), parent=pen)
    cyl(0.03, 0.09, mat("#1E293B", rough=0.4), r2=0, seg=24, loc=(0, 0, 1.295), parent=pen)
    cyl(0.105, 0.16, mat("#CBD5E1", rough=0.25, metal=1), seg=24, loc=(0, 0, -1.03), parent=pen)
    cyl(0.1, 0.2, mat("#FB7185", rough=0.6), seg=24, loc=(0, 0, -1.2), parent=pen)
    return floor


def scene_design_01(draft):
    """ทฤษฎีสีและองค์ประกอบศิลป์ — วงล้อสี 12 สี + แม่สี 3 ลูก + กรอบกฎสามส่วน"""
    zb, zm, zk = ZONE["design"]
    floor = stage("design", dist=14.6, target=(-0.1, 0, 1.25), draft=draft)
    hub = empty(loc=(-1.25, 0.45, 1.72), rot=(R(66), 0, 0))
    cols = ("#EF4444", "#F97316", "#FBBF24", "#A3E635", "#22C55E", "#14B8A6",
            "#06B6D4", "#3B82F6", "#6366F1", "#A855F7", "#EC4899", "#F43F5E")
    for i, c in enumerate(cols):
        a0 = R(90 - 30 * i - 14)
        wedge(0.72, 1.62, a0, a0 + R(28), 0.36, mat(c, rough=0.22), bevel=0.035, loc=(0, 0, -0.18), parent=hub)
    cyl(0.6, 0.3, mat("#F3E3CF", rough=0.45), loc=(0, 0, 0), parent=hub)
    torus(1.71, 0.05, mat(GOLD, rough=0.25, metal=0.9), loc=(0, 0, 0.05), parent=hub)
    for c, r, loc in (("#EF4444", 0.46, (0.95, -1.35, 0.46)), ("#FBBF24", 0.36, (1.8, -0.8, 0.36)), ("#3B82F6", 0.54, (2.5, -1.6, 0.54))):
        sphere(r, mat(c, rough=0.18), loc=loc)
    fr = empty(loc=(1.85, 1.3, 1.2), rot=(R(-9), 0, R(-14)))
    fw, fh, t = 2.2, 1.5, 0.12
    white, gold = mat("#FFF7ED", rough=0.35), mat(GOLD, rough=0.3, metal=0.85, emit=0.3)
    for z in (fh / 2, -fh / 2):
        box(fw + t, t, t, white, bevel=0.02, loc=(0, 0, z), parent=fr)
    for x in (fw / 2, -fw / 2):
        box(t, t, fh, white, bevel=0.02, loc=(x, 0, 0), parent=fr)
    for x in (fw / 6, -fw / 6):
        box(0.04, 0.04, fh, gold, bevel=0, loc=(x, 0, 0), parent=fr)
    for z in (fh / 6, -fh / 6):
        box(fw, 0.04, 0.04, gold, bevel=0, loc=(0, 0, z), parent=fr)
    sphere(0.2, mat("#F97316", rough=0.2, emit=0.25), loc=(fw / 6, 0, fh / 6), parent=fr)     # จุดเด่นบนจุดตัดสามส่วน
    return floor


def scene_hardware_03(draft):
    """Power Supply และการต่อสายไฟ — ตัว PSU + พัดลม + สายไฟ + หัว 24-pin + สายฟ้า"""
    zb, zm, zk = ZONE["hardware"]
    floor = stage("hardware", az=20, dist=14.6, target=(0.15, 0, 1.05), draft=draft)
    steel = mat("#2B3442", rough=0.38, metal=0.9)
    psu = box(3.0, 2.3, 1.55, steel, bevel=0.06, loc=(-1.0, 0.55, 0.775), rot=(0, 0, R(-16)))
    top = 0.775
    cyl(0.9, 0.02, mat("#0A0D12", rough=0.6), loc=(0, 0, top + 0.005), parent=psu)
    blade = mat(zm, rough=0.35)
    for i in range(7):
        a = 2 * math.pi * i / 7
        box(0.62, 0.3, 0.012, blade, bevel=0, loc=(0.5 * math.cos(a), 0.5 * math.sin(a), top + 0.02), rot=(R(12), 0, a + R(25)), parent=psu)
    chrome = mat("#D6DEE8", rough=0.2, metal=1.0)
    torus(0.92, 0.055, mat(GOLD, rough=0.25, metal=0.9), loc=(0, 0, top + 0.05), parent=psu)
    for rr in (0.7, 0.5, 0.3):
        torus(rr, 0.022, chrome, ring=8, loc=(0, 0, top + 0.07), parent=psu)
    for a in (0, 90):
        box(1.8, 0.04, 0.03, chrome, bevel=0, loc=(0, 0, top + 0.07), rot=(0, 0, R(a + 45)), parent=psu)
    cyl(0.2, 0.06, mat(zb, rough=0.3, emit=0.4), loc=(0, 0, top + 0.08), parent=psu)
    box(1.7, 0.03, 0.72, mat(zb, rough=0.4), bevel=0.02, loc=(-0.35, -1.155, 0.0), parent=psu)
    text("650W", 0.52, 0.04, mat("#1A0610", rough=0.5), "ariblk.ttf", bevel=0.003, loc=(-0.35, -1.18, 0.0), rot=(R(90), 0, 0), parent=psu)
    for i in range(4):
        box(0.07, 0.03, 0.9, mat("#0A0D12", rough=0.6), bevel=0, loc=(0.85 + 0.16 * i, -1.155, 0.0), parent=psu)
    plug = box(1.45, 0.5, 0.42, mat("#EEF1F5", rough=0.4), bevel=0.04, loc=(1.9, -1.2, 0.21), rot=(0, 0, R(12)))
    hole = mat("#11151B", rough=0.6)
    for i in range(12):
        for j in range(2):
            box(0.075, 0.03, 0.105, hole, bevel=0, loc=(-0.605 + 0.11 * i, -0.25, -0.075 + 0.15 * j), parent=plug)
            box(0.03, 0.03, 0.03, mat(GOLD, rough=0.3, metal=1), bevel=0, loc=(-0.605 + 0.11 * i, -0.25, -0.075 + 0.15 * j), parent=plug)
    box(0.3, 0.06, 0.12, mat("#EEF1F5", rough=0.4), bevel=0.02, loc=(0, 0.0, 0.25), parent=plug)
    cable = (mat("#111418", rough=0.45), mat(GOLD, rough=0.4), mat(zb, rough=0.4), mat("#111418", rough=0.45),
             mat("#EF4444", rough=0.4), mat("#111418", rough=0.45))
    M = psu.matrix_basis
    for i, m in enumerate(cable):
        yi = -0.5 + 0.2 * i
        a = M @ Vector((1.45, yi, 0.2))
        b = M @ Vector((2.15, yi, 0.2))
        c = Vector((2.55 + 0.1 * i, -0.2 + 0.05 * i, 0.12))
        d = plug.matrix_basis @ Vector((-0.5 + 0.2 * i, 0.22, 0.02))
        tube([a, b, c, d], 0.062, m)
    bolt = [(0.12, 0.85), (-0.5, -0.08), (-0.08, -0.08), (-0.24, -0.85), (0.5, 0.12), (0.06, 0.12), (0.34, 0.85)]
    prism(bolt, 0.2, mat(GOLD, rough=0.22, metal=0.6, emit=0.9), bevel=0.03, loc=(-2.75, -1.1, 1.15), rot=(R(80), 0, R(14)))
    return floor


def tag(label, loc, rz, zb):
    """ป้ายแท็กโค้ดลอย (ใช้ร่วมกันในฉากทางเลือกของ coding_01)"""
    t = box(1.15, 0.14, 0.52, mat("#082A1D", rough=0.3), bevel=0.06, loc=loc, rot=(R(-10), 0, R(rz)))
    text(label, 0.36, 0.05, mat("#F0FFF6", rough=0.4, emit=0.8), "consolab.ttf", bevel=0.004,
         loc=(0, -0.085, -0.01), rot=(R(90), 0, 0), parent=t)
    return t


def scene_coding_01b(draft):
    """ดีไซน์ภาพ B · ตัวต่อหน้าเว็บ — HTML = บล็อกโครงสร้างที่ลอยออกจากแผ่นหน้าเว็บ, CSS = ลูกกลิ้งทาสี"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", dist=14.6, target=(0, 0, 1.2), draft=draft)
    page = box(4.1, 0.16, 2.9, mat("#06231A", rough=0.3), bevel=0.06, loc=(-0.35, 0.95, 1.55), rot=(R(-10), 0, 0))
    white, pale = mat("#F0FFF6", rough=0.45), mat("#BBF7D0", rough=0.4)
    # ชิ้นส่วนหน้าเว็บ: (กว้าง, สูง, x, z, ระยะลอยออกมาด้านหน้า, วัสดุ)
    parts = ((3.7, 0.5, 0.0, 1.1, 0.35, mat(zb, rough=0.3)),                # header
             (2.25, 1.25, -0.72, 0.08, 0.75, white),                         # ภาพหลัก
             (1.25, 1.25, 1.22, 0.08, 0.5, mat(zm, rough=0.35)),             # แถบข้าง
             (3.7, 0.4, 0.0, -1.1, 0.3, mat("#0D3B2A", rough=0.4)))          # footer
    for wd, ht, x, z, lift, m in parts:
        box(wd, 0.26, ht, m, bevel=0.05, loc=(x, -0.08 - lift, z), parent=page)
    for i in range(3):          # เมนูบน header
        box(0.5, 0.06, 0.14, mat(GOLD if i == 0 else "#F0FFF6", rough=0.4, emit=0.5), bevel=0.02,
            loc=(0.35 + 0.62 * i, -0.6, 1.1), parent=page)
    sphere(0.2, mat(GOLD, rough=0.3, emit=0.4), loc=(-1.4, -1.0, 0.4), parent=page)       # ดวงอาทิตย์ในภาพหลัก
    prism([(-0.95, -0.5), (0.25, -0.5), (-0.35, 0.3)], 0.08, mat(zm, rough=0.4), bevel=0.01,
          loc=(-0.45, -0.98, 0.07), rot=(R(90), 0, 0), parent=page)
    prism([(-0.5, -0.5), (0.45, -0.5), (0.0, 0.05)], 0.08, mat(zb, rough=0.4), bevel=0.01,
          loc=(-0.05, -1.0, 0.07), rot=(R(90), 0, 0), parent=page)
    for i, wd in enumerate((0.85, 0.6, 0.85, 0.45)):        # บรรทัดข้อความบนแถบข้าง
        box(wd, 0.05, 0.1, pale, bevel=0.02, loc=(0.75 + wd / 2, -0.74, 0.46 - 0.24 * i), parent=page)
    # ลูกกลิ้งทาสี + รอยสีบนพื้น
    roll = empty(loc=(2.35, -1.45, 0), rot=(0, 0, R(-20)))
    box(1.05, 2.3, 0.02, mat(zb, rough=0.35, emit=0.35), bevel=0, loc=(0, 1.3, 0.012), parent=roll)
    cyl(0.25, 1.1, mat(zb, rough=0.5), loc=(0, 0, 0.26), rot=(0, R(90), 0), parent=roll)
    chrome = mat("#D6DEE8", rough=0.25, metal=1)
    for x in (-0.58, 0.58):
        cyl(0.09, 0.06, chrome, loc=(x, 0, 0.26), rot=(0, R(90), 0), parent=roll)
    tube([(0.6, 0, 0.26), (0.84, 0, 0.3), (0.82, -0.1, 0.78), (0.2, -0.2, 0.98), (0, -0.25, 1.02)], 0.04, chrome, parent=roll)
    tube([(0, -0.25, 1.02), (-0.12, -0.7, 1.8)], 0.1, mat(GOLD, rough=0.35), parent=roll)
    tag("<div>", (-3.0, -0.5, 2.05), 14, zb)
    tag("color:", (-2.85, -1.45, 0.5), 18, zb)
    return floor


def scene_coding_01c(draft):
    """ดีไซน์ภาพ C · หุ่นยนต์มาสคอต — ตัวละครประจำโซนถือป้ายแท็ก ข้าง ๆ เป็นลูกบาศก์โค้ดกับถังสี"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", dist=14.6, target=(0, 0, 1.3), draft=draft)
    shell, dark = mat("#F0FFF6", rough=0.35), mat("#06231A", rough=0.3)
    glow, gold = mat(zb, rough=0.3, emit=1.2), mat(GOLD, rough=0.25, metal=0.85)
    bot = empty(loc=(-0.25, 0.1, 0), rot=(0, 0, R(-8)))
    for x in (-0.36, 0.36):                                  # ขา + เท้า
        cyl(0.17, 0.5, mat(zm, rough=0.4), loc=(x, 0, 0.3), parent=bot)
        box(0.5, 0.7, 0.2, shell, bevel=0.08, loc=(x, -0.1, 0.1), parent=bot)
    box(1.45, 1.0, 1.1, shell, bevel=0.16, loc=(0, 0, 1.05), parent=bot)              # ตัว
    box(0.95, 0.06, 0.6, dark, bevel=0.05, loc=(0, -0.5, 1.08), parent=bot)
    text("</>", 0.44, 0.05, glow, "consolab.ttf", bevel=0.004, loc=(0, -0.55, 1.07), rot=(R(90), 0, 0), parent=bot)
    cyl(0.22, 0.16, mat(zm, rough=0.4), loc=(0, 0, 1.66), parent=bot)                # คอ
    box(1.95, 1.25, 1.15, shell, bevel=0.22, loc=(0, 0, 2.3), parent=bot)             # หัว
    box(1.6, 0.06, 0.78, dark, bevel=0.1, loc=(0, -0.63, 2.3), parent=bot)            # หน้าจอ
    for x in (-0.42, 0.42):                                  # ตา
        cyl(0.17, 0.06, glow, loc=(x, -0.68, 2.4), rot=(R(90), 0, 0), parent=bot)
    box(0.42, 0.05, 0.08, glow, bevel=0.02, loc=(0, -0.68, 2.08), parent=bot)         # ปาก
    for x in (-1.03, 1.03):                                  # หู
        cyl(0.2, 0.14, mat(zb, rough=0.35), loc=(x, 0, 2.3), rot=(0, R(90), 0), parent=bot)
    cyl(0.035, 0.34, gold, loc=(0, 0, 3.04), parent=bot)                              # เสาอากาศ
    sphere(0.13, mat(GOLD, rough=0.3, emit=0.9), loc=(0, 0, 3.28), parent=bot)
    arm = mat(zm, rough=0.4)
    tube([(-0.74, 0, 1.3), (-1.15, -0.1, 1.05), (-1.25, -0.3, 0.72)], 0.11, arm, parent=bot)      # แขนซ้ายห้อย
    sphere(0.2, shell, loc=(-1.25, -0.32, 0.62), parent=bot)
    tube([(0.74, 0, 1.3), (1.2, -0.15, 1.45), (1.42, -0.35, 1.9)], 0.11, arm, parent=bot)         # แขนขวาชูป้าย
    sphere(0.2, shell, loc=(1.45, -0.38, 1.98), parent=bot)
    sign = box(1.55, 0.14, 0.78, mat(zb, rough=0.3), bevel=0.07, loc=(2.25, -0.55, 2.42), rot=(R(-8), 0, R(-12)))
    text("<h1>", 0.5, 0.06, dark, "consolab.ttf", bevel=0.004, loc=(0, -0.09, -0.01), rot=(R(90), 0, 0), parent=sign)
    cyl(0.045, 0.75, gold, loc=(1.72, -0.4, 1.85), rot=(0, R(-14), 0))
    # ลูกบาศก์โค้ดซ้อนกัน
    for label, size, loc, rz, m, ink_c in (("{ }", 1.05, (-2.55, -0.1, 0.525), 14, mat(zm, rough=0.35), "#F0FFF6"),
                                           ("#", 0.78, (-2.5, -0.1, 1.44), -12, mat(GOLD, rough=0.3), "#231A02")):
        c = box(size, size, size, m, bevel=0.07, loc=loc, rot=(0, 0, R(rz)))
        text(label, size * 0.5, 0.04, mat(ink_c, rough=0.4, emit=0.7 if ink_c == "#F0FFF6" else 0), "consolab.ttf", bevel=0.004,
             loc=(0, -size / 2 - 0.02, 0), rot=(R(90), 0, 0), parent=c)
    tag(".css", (-2.75, -1.4, 0.5), 18, zb)
    # ถังสี CSS + พู่กัน
    cyl(0.42, 0.62, mat("#D6DEE8", rough=0.3, metal=0.9), loc=(2.35, -1.35, 0.31))
    cyl(0.37, 0.03, mat(zb, rough=0.3, emit=0.8), loc=(2.35, -1.35, 0.625))
    brush = empty(loc=(2.5, -1.3, 0.95), rot=(R(-20), R(28), 0))
    cyl(0.055, 0.9, gold, parent=brush)
    box(0.26, 0.1, 0.3, mat(zb, rough=0.5), bevel=0.03, loc=(0, 0, -0.55), parent=brush)
    return floor


def scene_coding_01d(draft):
    """ดีไซน์ภาพ D · ตราไอเทม — วัตถุชิ้นเดียวเด่นกลางภาพ: ตราหกเหลี่ยม </> บนแท่น แบบไอคอนไอเทมในเกม"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", dist=14.6, target=(0, 0, 1.3), draft=draft)
    gold = mat(GOLD, rough=0.22, metal=0.85)
    cyl(1.75, 0.26, mat("#06231A", rough=0.3), loc=(0, 0.1, 0.13))                    # แท่น
    torus(1.75, 0.065, gold, loc=(0, 0.1, 0.26))
    cyl(1.3, 0.02, mat(zb, rough=0.3, emit=1.4), loc=(0, 0.1, 0.27))
    hub = empty(loc=(0, 0.1, 2.0), rot=(R(80), 0, 0))
    hexa = lambda r: [(r * math.cos(R(60 * k + 30)), r * math.sin(R(60 * k + 30))) for k in range(6)]
    prism(hexa(1.62), 0.34, gold, bevel=0.05, loc=(0, 0, -0.17), parent=hub)
    prism(hexa(1.4), 0.2, mat("#0D3B2A", rough=0.3), bevel=0.04, loc=(0, 0, 0.17), parent=hub)
    prism(hexa(1.22), 0.06, mat("#06231A", rough=0.35), bevel=0.02, loc=(0, 0, 0.37), parent=hub)
    for ch, x, m in (("<", -0.62, mat(zb, rough=0.28)), ("/", 0.0, gold), (">", 0.62, mat(zb, rough=0.28))):
        text(ch, 1.3, 0.24, m, "consolab.ttf", bevel=0.02, loc=(x, 0, 0.55), parent=hub)
    star = [(0, 1), (0.22, 0.22), (1, 0), (0.22, -0.22), (0, -1), (-0.22, -0.22), (-1, 0), (-0.22, 0.22)]
    for s, loc in ((0.3, (-2.15, -0.2, 3.0)), (0.2, (2.2, 0.2, 2.75)), (0.24, (1.95, -0.9, 1.15)), (0.16, (-1.95, -0.8, 1.45))):
        prism([(x * s, y * s) for x, y in star], 0.06, mat("#FFF7D6", rough=0.3, emit=1.6), bevel=0.01, loc=loc, rot=(R(80), 0, 0))
    tag("<h1>", (-3.0, -0.3, 2.1), 14, zb)
    tag("{ }", (3.0, -0.9, 0.62), -16, zb)
    tag(".css", (-2.8, -1.35, 0.55), 18, zb)
    return floor


STAR = [(0, 1), (0.22, 0.22), (1, 0), (0.22, -0.22), (0, -1), (-0.22, -0.22), (-1, 0), (-0.22, 0.22)]


def sparkle(s, loc):
    prism([(x * s, y * s) for x, y in STAR], 0.06, mat("#FFF7D6", rough=0.3, emit=1.6), bevel=0.01, loc=loc, rot=(R(80), 0, 0))


def scene_coding_01e(draft):
    """ดีไซน์ภาพ E · ร้านบนถนนโค้ด — การ์ดทรัพย์สิน = อาคาร 1 หลังบน Coding Avenue: ร้าน HTML & CSS"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", dist=14.6, target=(0, 0, 1.45), draft=draft)
    white, dark = mat("#F0FFF6", rough=0.4), mat("#06231A", rough=0.3)
    gold = mat(GOLD, rough=0.25, metal=0.85)
    box(5.0, 3.2, 0.14, mat("#BFE8CF", rough=0.5), bevel=0.05, loc=(0, 0.35, 0.07))            # ทางเท้า
    box(3.3, 2.0, 2.0, white, bevel=0.06, loc=(0, 0.6, 1.14))                                 # ตัวร้าน
    box(3.6, 2.3, 0.2, mat(zm, rough=0.35), bevel=0.05, loc=(0, 0.6, 2.24))                    # หลังคา
    fy = -0.42
    box(0.78, 0.08, 1.25, dark, bevel=0.03, loc=(0.95, fy, 0.77))                             # ประตู
    box(0.5, 0.05, 0.5, mat(zb, rough=0.2, emit=0.5), bevel=0.02, loc=(0.95, fy - 0.03, 1.0))
    sphere(0.06, gold, loc=(0.68, fy - 0.07, 0.7))
    box(1.65, 0.08, 0.95, dark, bevel=0.03, loc=(-0.62, fy, 0.9))                             # หน้าต่างร้าน = จอโค้ด
    for i, (x0, wd, c) in enumerate(((-1.3, 0.6, zb), (-1.15, 1.0, "#E2F9EA"), (-1.15, 0.7, GOLD), (-1.3, 0.45, zb))):
        box(wd, 0.04, 0.09, mat(c, rough=0.4, emit=0.6), bevel=0.02, loc=(x0 + wd / 2, fy - 0.05, 1.2 - 0.2 * i))
    for i in range(7):                                                                         # กันสาดลายทาง
        box(0.47, 0.75, 0.07, mat(zb if i % 2 == 0 else "#F0FFF6", rough=0.4), bevel=0.02,
            loc=(-1.41 + 0.47 * i, fy - 0.3, 1.62), rot=(R(-24), 0, 0))
    sign = box(2.5, 0.1, 0.44, dark, bevel=0.04, loc=(0, fy - 0.02, 1.98))                    # ป้ายร้าน
    text("HTML & CSS", 0.27, 0.04, mat("#F0FFF6", rough=0.4, emit=0.9), "ariblk.ttf", bevel=0.003,
         loc=(0, -0.07, 0), rot=(R(90), 0, 0), parent=sign)
    for ch, x, m in (("<", -0.62, mat(zb, rough=0.28)), ("/", 0.0, gold), (">", 0.62, mat(zb, rough=0.28))):   # ป้ายบนหลังคา
        text(ch, 1.15, 0.22, m, "consolab.ttf", bevel=0.02, loc=(x, 0.3, 2.82), rot=(R(86), 0, 0))
    cyl(0.05, 2.1, mat("#2B3442", rough=0.4, metal=0.8), loc=(2.75, -0.8, 1.19))               # เสาไฟ
    sphere(0.2, mat("#FFF3C4", rough=0.3, emit=2.2), loc=(2.75, -0.8, 2.36))
    cyl(0.11, 0.7, mat("#8B5E34", rough=0.6), loc=(-2.75, -0.5, 0.49))                         # ต้นไม้
    sphere(0.58, mat(zb, rough=0.5), loc=(-2.75, -0.5, 1.25))
    sphere(0.4, mat(mix(zb, "#FFFFFF", 0.2), rough=0.5), loc=(-2.6, -0.55, 1.85))
    box(0.55, 0.05, 0.7, mat(GOLD, rough=0.4), bevel=0.02, loc=(2.0, -1.25, 0.47), rot=(R(-14), 0, R(-10)))   # ป้ายตั้งหน้าร้าน
    return floor


def scene_coding_01f(draft):
    """ดีไซน์ภาพ F · โต๊ะนักพัฒนา — จอแสดงโค้ดคู่กับหน้าเว็บ คีย์บอร์ด แก้ว ต้นไม้ โน้ต"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", dist=14.6, target=(0, 0, 1.35), draft=draft)
    white, dark = mat("#F0FFF6", rough=0.4), mat("#06231A", rough=0.3)
    box(6.4, 2.7, 0.2, mat("#E7CFA0", rough=0.5), bevel=0.05, loc=(0, 0, 0.55))                # ท็อปโต๊ะ
    box(6.2, 0.12, 0.45, mat("#0D3B2A", rough=0.4), bevel=0.02, loc=(0, -1.15, 0.24))
    z0 = 0.65
    box(1.0, 0.6, 0.07, mat("#D6DEE8", rough=0.25, metal=1), bevel=0.03, loc=(0, 0.55, z0 + 0.035))   # ขาจอ
    cyl(0.08, 0.5, mat("#D6DEE8", rough=0.25, metal=1), loc=(0, 0.6, z0 + 0.3))
    mon = box(3.3, 0.16, 1.95, dark, bevel=0.06, loc=(0, 0.5, z0 + 1.4), rot=(R(-7), 0, 0))
    box(3.05, 0.05, 1.7, mat("#0D3B2A", rough=0.5), bevel=0.02, loc=(0, -0.08, 0), parent=mon)
    for i, (x0, wd, c) in enumerate(((-1.4, 0.7, zb), (-1.25, 1.0, "#E2F9EA"), (-1.25, 0.75, GOLD), (-1.25, 1.05, "#E2F9EA"), (-1.4, 0.5, zb))):
        box(wd, 0.04, 0.09, mat(c, rough=0.4, emit=0.6), bevel=0.02, loc=(x0 + wd / 2, -0.12, 0.55 - 0.26 * i), parent=mon)
    page = box(1.35, 0.05, 1.45, white, bevel=0.03, loc=(0.72, -0.12, 0), parent=mon)          # หน้าเว็บที่ได้
    box(1.35, 0.04, 0.26, mat(zb, rough=0.35), bevel=0.02, loc=(0, -0.03, 0.6), parent=page)
    box(0.55, 0.04, 0.5, mat(GOLD, rough=0.35), bevel=0.03, loc=(-0.3, -0.03, 0.1), parent=page)
    for i in range(3):
        box(0.5, 0.04, 0.08, mat("#94A3B8", rough=0.6), bevel=0.01, loc=(0.33, -0.03, 0.28 - 0.17 * i), parent=page)
    box(1.1, 0.04, 0.2, mat(zm, rough=0.35), bevel=0.02, loc=(0, -0.03, -0.5), parent=page)
    box(0.42, 0.03, 0.42, mat(GOLD, rough=0.5), bevel=0.01, loc=(1.45, -0.12, 0.85), rot=(0, R(8), 0), parent=mon)   # โน้ตแปะจอ
    kb = box(2.1, 0.72, 0.09, white, bevel=0.04, loc=(-0.1, -0.7, z0 + 0.045))                 # คีย์บอร์ด
    key = mat("#0D3B2A", rough=0.4)
    for r_ in range(3):
        for c_ in range(11):
            box(0.14, 0.14, 0.05, mat(zb, rough=0.35) if (r_, c_) in ((0, 10), (2, 0)) else key, bevel=0.02,
                loc=(-0.9 + 0.18 * c_, 0.2 - 0.2 * r_, 0.06), parent=kb)
    box(0.34, 0.5, 0.14, white, bevel=0.07, loc=(1.5, -0.7, z0 + 0.07))                        # เมาส์
    cyl(0.25, 0.48, mat(GOLD, rough=0.3), loc=(-2.25, -0.55, z0 + 0.24))                       # แก้ว
    cyl(0.2, 0.02, mat("#3B2412", rough=0.3), loc=(-2.25, -0.55, z0 + 0.485))
    torus(0.14, 0.04, mat(GOLD, rough=0.3), seg=32, ring=10, loc=(-2.52, -0.55, z0 + 0.24), rot=(R(90), 0, 0))
    cyl(0.22, 0.4, mat("#F0FFF6", rough=0.4), r2=0.3, loc=(2.55, 0.1, z0 + 0.2))               # กระถางต้นไม้
    for dx, dz, r_ in ((0, 0.75, 0.34), (-0.25, 0.55, 0.24), (0.27, 0.6, 0.26)):
        sphere(r_, mat(zb, rough=0.5), loc=(2.55 + dx, 0.1, z0 + dz))
    for i, (c, wd) in enumerate(((zm, 1.3), (GOLD, 1.15), ("#F0FFF6", 1.25))):                 # กองหนังสือ
        box(wd, 0.85, 0.2, mat(c, rough=0.45), bevel=0.03, loc=(-2.45, 0.55, z0 + 0.1 + 0.2 * i), rot=(0, 0, R(8 - 9 * i)))
    return floor


def scene_coding_01g(draft):
    """ดีไซน์ภาพ G · คัมภีร์สกิล — หนังสือกางออก มีเครื่องหมาย </> เรืองแสงลอยขึ้นจากหน้ากระดาษ แบบการ์ดสกิลในเกม"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", dist=14.6, target=(0, 0, 1.35), draft=draft)
    gold = mat(GOLD, rough=0.22, metal=0.85)
    paper = mat("#F8FFF9", rough=0.5)
    book = empty(loc=(0, 0.25, 0.75), rot=(R(32), 0, 0))
    box(4.2, 2.7, 0.14, mat(zm, rough=0.35), bevel=0.05, loc=(0, 0, 0), parent=book)           # ปก
    for sgn in (-1, 1):
        pg = box(1.95, 2.45, 0.2, paper, bevel=0.04, loc=(sgn * 1.0, 0, 0.17), rot=(0, R(-7 * sgn), 0), parent=book)
        for i in range(6):
            wd = (1.4, 1.2, 1.45, 0.9, 1.35, 1.1)[i]
            box(wd, 0.07, 0.02, mat(zb if i == 0 else "#94A3B8", rough=0.5), bevel=0,
                loc=(-0.72 + wd / 2, 0.85 - 0.3 * i, 0.105), parent=pg)
    box(0.14, 2.7, 0.3, gold, bevel=0.04, loc=(0, 0, 0.12), parent=book)                       # สัน
    box(0.2, 0.9, 0.03, mat("#EF4444", rough=0.4), bevel=0, loc=(0.35, -1.5, 0.3), parent=book)   # ที่คั่น
    for x, y in ((-2.0, -1.25), (2.0, -1.25), (-2.0, 1.25), (2.0, 1.25)):                      # มุมปกทอง
        box(0.3, 0.3, 0.17, gold, bevel=0.03, loc=(x, y, 0.0), parent=book)
    glow, gslash = mat(zb, rough=0.25, emit=1.3), mat(GOLD, rough=0.22, metal=0.6, emit=0.7)
    for ch, x, m in (("<", -0.78, glow), ("/", 0.0, gslash), (">", 0.78, glow)):
        text(ch, 1.6, 0.26, m, "consolab.ttf", bevel=0.025, loc=(x, -0.25, 2.35), rot=(R(84), 0, 0))
    torus(1.25, 0.03, mat(zb, rough=0.3, emit=2.0), loc=(0, 0.0, 1.35), rot=(R(-58), 0, 0))    # วงเวท
    torus(1.6, 0.018, mat(GOLD, rough=0.3, emit=1.5), loc=(0, 0.0, 1.3), rot=(R(-58), 0, 0))
    for s, loc in ((0.3, (-2.2, -0.2, 2.9)), (0.2, (2.15, 0.1, 2.85)), (0.24, (2.5, -0.8, 1.5)), (0.17, (-2.6, -0.7, 1.7)), (0.14, (1.3, -0.4, 3.15))):
        sparkle(s, loc)
    tag("<h1>", (-3.05, -1.0, 0.75), 16, zb)
    tag(".css", (3.0, -1.15, 0.6), -16, zb)
    return floor


def scene_coding_01h(draft):
    """ดีไซน์ภาพ H · ต้นไม้แท็ก — โครงสร้างหน้าเว็บโตเป็นต้นไม้: <html> เป็นราก แตกกิ่งเป็น <head> <body> แล้วเป็นแท็กย่อย"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", dist=14.6, target=(0, 0, 1.4), draft=draft)
    wood, leaf = mat("#B7791F", rough=0.5), mat(zb, rough=0.5)
    cyl(0.9, 0.5, mat("#F0FFF6", rough=0.4), r2=1.1, loc=(0, 0, 0.25))                         # กระถาง
    cyl(1.0, 0.04, mat("#3B2412", rough=0.7), loc=(0, 0, 0.5))
    torus(1.1, 0.06, mat(GOLD, rough=0.25, metal=0.85), loc=(0, 0, 0.5))
    nodes = {"<html>": (0, -0.15, 1.05, 0), "<head>": (-1.75, -0.15, 1.75, 8), "<body>": (1.45, -0.15, 1.8, -8),
             ".css": (-2.75, -0.15, 2.7, 12), "<h1>": (0.15, -0.15, 2.75, 4), "<p>": (1.6, -0.15, 2.95, -4), "<img>": (2.95, -0.15, 2.5, -12)}
    links = (("<html>", "<head>"), ("<html>", "<body>"), ("<head>", ".css"), ("<body>", "<h1>"), ("<body>", "<p>"), ("<body>", "<img>"))
    tube([(0, 0, 0.5), (0, 0, 0.9)], 0.13, wood)
    for a, b in links:
        (ax, ay, az, _), (bx, by, bz, _) = nodes[a], nodes[b]
        p0, p1 = Vector((ax, ay + 0.2, az + 0.2)), Vector((bx, by + 0.2, bz - 0.25))
        tube([p0, (p0.x * 0.6 + p1.x * 0.4, p0.y, p0.z * 0.35 + p1.z * 0.65), p1], 0.075, wood)
        m = (p0 + p1) / 2
        sphere(0.17, leaf, loc=(m.x + 0.22, m.y - 0.1, m.z + 0.12))
        sphere(0.12, mat(mix(zb, "#FFFFFF", 0.3), rough=0.5), loc=(m.x - 0.2, m.y - 0.1, m.z - 0.02))
    for label, (x, y, z, rz) in nodes.items():
        t = tag(label, (x, y, z), rz, zb)
        if label == "<html>":
            t.scale = (1.35, 1.35, 1.35)
    sparkle(0.2, (-0.9, -0.3, 3.2))
    sparkle(0.15, (2.3, -0.3, 3.3))
    return floor


def action_stage(zone, draft, cam_loc=(0.6, -7.2, 0.7), look=(0, 0, 1.75), lens=22, burst=("#FDE047", "#A3E635")):
    """ฉากแอ็กชันแนวการ์ด TCG: ไม่มีพื้น กล้องเลนส์กว้างมุมต่ำ ฉากหลังเส้นสปีดแผ่รัศมี + แผ่นระเบิดสีเข้มหลังตัวละคร
    (ออกแบบให้รันกับ --style toon)"""
    zb, zm, zk = ZONE[zone]
    for o in stage(zone, draft=draft):
        o.hide_render = True
    co = bpy.context.scene.camera
    co.data.lens = lens
    co.location = cam_loc
    aim(co, look)
    back = empty(loc=(look[0], 7.0, look[2] + 0.4), rot=(R(90), 0, 0))
    n = 36
    wedge(0.0, 40, 0, 2 * math.pi, 0.02, mat(burst[1], emit=1), bevel=0, seg=36, loc=(0, 0, -0.1), parent=back)
    for i in range(n):
        a0 = 2 * math.pi * i / n
        c = (burst[0], burst[1], mix(zb, "#FFFFFF", 0.25))[i % 3]
        wedge(0.0, 40, a0, a0 + 2 * math.pi / n * (0.62 if i % 2 else 1.0), 0.02, mat(c, emit=1), bevel=0, seg=2, loc=(0, 0, 0), parent=back)
    rng = random.Random(zone + "burst")
    pts = []
    for i in range(22):                                  # แผ่นระเบิดหยัก
        a = 2 * math.pi * i / 22
        r = rng.uniform(5.2, 7.5) if i % 2 == 0 else rng.uniform(2.8, 3.6)
        pts.append((r * math.cos(a), r * math.sin(a)))
    prism(pts, 0.02, mat(mix(zk, "#3B0764", 0.45), emit=1), bevel=0, loc=(0, 0, 0.6), parent=back)
    prism([(x * 0.8, y * 0.8) for x, y in pts], 0.02, mat(zm, emit=1), bevel=0, loc=(0, 0, 1.0), parent=back)
    return rng


def robot(parent, zone, hands, stand=False):
    """หุ่นยนต์มาสคอต — hands = ตำแหน่งมือ (ซ้าย, ขวา) ในพิกัดของ parent; คืนวัตถุมือ 2 ข้าง"""
    zb, zm, zk = ZONE[zone]
    shell, dark = mat("#F0FFF6", rough=0.35), mat(mix(zk, "#000000", 0.2), rough=0.6)
    glow, joint = mat(zb, rough=0.3, emit=1.2), mat(zm, rough=0.4)
    box(1.45, 1.0, 1.1, shell, bevel=0.16, loc=(0, 0, 1.05), parent=parent)
    box(0.95, 0.06, 0.6, dark, bevel=0.05, loc=(0, -0.5, 1.08), parent=parent)
    text("</>", 0.44, 0.05, glow, "consolab.ttf", bevel=0.004, loc=(0, -0.55, 1.07), rot=(R(90), 0, 0), parent=parent)
    cyl(0.22, 0.16, joint, loc=(0, 0, 1.66), parent=parent)
    box(1.95, 1.25, 1.15, shell, bevel=0.22, loc=(0, 0, 2.3), parent=parent)
    box(1.6, 0.06, 0.78, dark, bevel=0.1, loc=(0, -0.63, 2.3), parent=parent)
    for x, rz in ((-0.42, 14), (0.42, -14)):             # ตาเฉียง = หน้าเอาจริง
        if stand:                                        # ตากลม = ใจดี
            cyl(0.17, 0.06, glow, loc=(x, -0.68, 2.4), rot=(R(90), 0, 0), parent=parent)
        else:
            box(0.42, 0.06, 0.2, glow, bevel=0.03, loc=(x, -0.68, 2.42), rot=(0, R(rz), 0), parent=parent)
    box(0.62, 0.05, 0.16, glow, bevel=0.03, loc=(0, -0.68, 2.06), parent=parent)      # ปากยิ้มกว้าง
    for x in (-1.03, 1.03):
        cyl(0.2, 0.14, mat(zb, rough=0.35), loc=(x, 0, 2.3), rot=(0, R(90), 0), parent=parent)
    cyl(0.035, 0.34, mat(GOLD, rough=0.3), loc=(0, 0, 3.04), parent=parent)
    sphere(0.13, mat(GOLD, rough=0.3, emit=0.9), loc=(0, 0, 3.28), parent=parent)
    out = []
    for sx, hand in zip((-1, 1), hands):
        sh = Vector((sx * 0.74, 0, 1.3))
        h = Vector(hand)
        el = (sh + h) / 2 + Vector((sx * 0.35, 0.25, -0.2))
        tube([sh, el, h], 0.12, joint, parent=parent)
        out.append(box(0.62, 0.62, 0.56, shell, bevel=0.14, loc=h, parent=parent))
    if stand:
        for x in (-0.36, 0.36):
            cyl(0.17, 0.5, joint, loc=(x, 0, 0.3), parent=parent)
            box(0.5, 0.7, 0.2, shell, bevel=0.08, loc=(x, -0.1, 0.1), parent=parent)
        return out
    for sx, kn, ft in ((-1, (-0.5, 0.5, 0.3), (-0.75, 1.3, 0.55)), (1, (0.5, -0.2, 0.05), (0.75, 0.5, -0.5))):   # ขางอแบบกระโดด
        tube([(sx * 0.36, 0, 0.5), kn, ft], 0.13, joint, parent=parent)
        box(0.5, 0.75, 0.24, shell, bevel=0.08, loc=ft, rot=(R(35), 0, 0), parent=parent)
    return out


def scene_coding_01x(draft):
    """ดีไซน์ภาพ X · แอ็กชัน — หุ่นยนต์โค้ดกระโดดพุ่งเข้ากล้อง ชกหมัด </> ออกมา อีกมือถือลูกกลิ้งสี เศษแท็กและบล็อกหน้าเว็บกระจาย"""
    zb, zm, zk = ZONE["coding"]
    rng = action_stage("coding", draft)
    bot = empty(loc=(0.9, 0.2, -0.75), rot=(R(-24), R(-10), R(-16)))
    bot.scale = (1.5, 1.5, 1.5)
    lh, rh = robot(bot, "coding", ((-1.45, -2.2, 0.95), (1.75, 0.3, 2.35)))
    lh.scale = (1.45, 1.45, 1.45)                              # หมัดที่ยื่นเข้ากล้อง
    gold = mat(GOLD, rough=0.25, metal=0.6)
    for ch, x, m in (("<", -0.55, mat(zb, rough=0.28, emit=1)), ("/", 0.0, mat(GOLD, emit=1)), (">", 0.55, mat(zb, rough=0.28, emit=1))):
        text(ch, 1.0, 0.2, m, "consolab.ttf", bevel=0.02, loc=(-1.45 + x, -2.75, 0.95), rot=(R(90), 0, 0), parent=bot)
    roll = empty(loc=(1.75, 0.3, 2.35), rot=(R(20), R(30), 0), parent=bot)       # ลูกกลิ้งสีในมือขวา
    cyl(0.07, 1.3, gold, loc=(0, 0, 0.6), parent=roll)
    cyl(0.26, 1.0, mat("#F472B6", rough=0.5), loc=(0, 0, 1.4), rot=(0, R(90), 0), parent=roll)
    chip = mat(mix(zk, "#000000", 0.2), rough=0.6)
    for label, loc, rot in (("<h1>", (-2.9, -1.2, 3.0), (-20, 10, 24)), ("{ }", (3.1, -1.6, 0.4), (-10, -20, -30)),
                            (".css", (-3.0, -0.5, 0.2), (-15, 15, -18)), ("<p>", (2.9, 0.5, 3.4), (-10, 0, 20))):
        t = box(1.3, 0.16, 0.6, chip, bevel=0.06, loc=loc, rot=tuple(R(v) for v in rot))
        text(label, 0.42, 0.05, mat("#F0FFF6", emit=0.8), "consolab.ttf", bevel=0.004, loc=(0, -0.095, -0.01), rot=(R(90), 0, 0), parent=t)
    for i in range(26):                                  # เศษกระจายออกจากศูนย์กลาง
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(2.6, 5.5)
        loc = (r * math.cos(a) * 1.2, rng.uniform(-2.5, 3.5), 1.7 + r * math.sin(a) * 0.75)
        rot = tuple(rng.uniform(0, math.pi) for _ in range(3))
        c = rng.choice((zb, GOLD, "#F0FFF6", "#F472B6", zm))
        if i % 3 == 0:
            cyl(0.09, 0.34, mat(GOLD, rough=0.3), seg=12, loc=loc, rot=rot)
        elif i % 3 == 1:
            s = rng.uniform(0.25, 0.5)
            prism([(0, 0), (s * 1.6, s * 0.3), (s * 0.5, s)], 0.05, mat(c, rough=0.4), bevel=0, loc=loc, rot=rot)
        else:
            s = rng.uniform(0.22, 0.4)
            box(s, s, s, mat(c, rough=0.4), bevel=0.03, loc=loc, rot=rot)
    return []


def scene_coding_01r(draft):
    """ดีไซน์ภาพ R · แนวเดิมแต่แน่นขึ้น — หน้าต่างโค้ดที่หน้าเว็บ "งอก" ออกจากจอ + </> + หุ่นยนต์ผู้ช่วย + เคอร์เซอร์ + หยดสี
    + หน้าต่างซ้อนด้านหลัง + วงแหวนเรืองแสงบนพื้น + ประกาย"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", az=-22, el=23, dist=16.6, target=(-0.1, 0, 1.45), draft=draft)
    dark, gold = mat("#06231A", rough=0.25), mat(GOLD, rough=0.22, metal=0.85)
    for r_, c, e in ((2.7, zb, 2.2), (3.25, GOLD, 1.4), (3.6, zb, 1.0)):                # วงแหวนบนพื้น
        torus(r_, 0.025, mat(c, rough=0.3, emit=e), loc=(-0.4, 0.3, 0.02))
    for loc, rz, sc_ in (((-2.9, 2.6, 2.35), 14, 0.55), ((2.7, 2.9, 2.75), -12, 0.5)):  # หน้าต่างซ้อนด้านหลัง
        w = box(3.9 * sc_, 0.16, 2.7 * sc_, mat("#0A2E22", rough=0.3), bevel=0.05, loc=loc, rot=(R(-8), 0, R(rz)))
        box(3.9 * sc_, 0.18, 0.4 * sc_, mat(zm, rough=0.4), bevel=0.05, loc=(0, -0.01, 1.15 * sc_), parent=w)
        for i, wd in enumerate((1.6, 2.4, 1.2, 2.0)):
            box(wd * sc_, 0.03, 0.12 * sc_, mat(zb if i % 2 == 0 else "#E2F9EA", rough=0.4, emit=0.35), bevel=0.01,
                loc=((-1.5 + wd / 2) * sc_, -0.1, (0.5 - 0.42 * i) * sc_), parent=w)
    win = box(4.3, 0.24, 2.95, dark, bevel=0.07, loc=(-0.55, 0.9, 1.68), rot=(R(-10), 0, R(5)))    # หน้าต่างหลัก
    box(4.3, 0.28, 0.46, mat("#22A95C", rough=0.35), bevel=0.07, loc=(0, -0.01, 1.245), parent=win)
    for i, c in enumerate(("#F87171", GOLD, "#86EFAC")):
        sphere(0.095, mat(c, rough=0.3, emit=0.6), loc=(-1.85 + 0.3 * i, -0.15, 1.245), parent=win)
    box(1.5, 0.06, 0.2, mat("#06231A", rough=0.4), bevel=0.05, loc=(0.6, -0.15, 1.245), parent=win)      # ช่อง URL
    box(3.95, 0.05, 2.2, mat("#0D3B2A", rough=0.5), bevel=0.02, loc=(0, -0.12, -0.2), parent=win)
    for i, (x0, wd, c) in enumerate(((-1.8, 0.75, zb), (-1.6, 1.1, "#E2F9EA"), (-1.6, 0.8, GOLD), (-1.4, 1.0, "#F9A8D4"),
                                     (-1.6, 0.9, "#E2F9EA"), (-1.8, 0.55, zb))):       # โค้ดฝั่งซ้าย
        box(wd, 0.04, 0.09, mat(c, rough=0.4, emit=0.55), bevel=0.02, loc=(x0 + wd / 2, -0.16, 0.6 - 0.27 * i), parent=win)
    box(0.03, 0.05, 2.0, mat(zb, rough=0.4, emit=0.8), bevel=0, loc=(-0.1, -0.16, -0.2), parent=win)      # เส้นแบ่ง
    white = mat("#F0FFF6", rough=0.4)
    # หน้าเว็บ "งอก" ออกจากจอฝั่งขวา: ยิ่งชิ้นล่างยิ่งลอยออกมามาก
    box(1.75, 0.2, 0.34, mat(zb, rough=0.3), bevel=0.05, loc=(0.95, -0.35, 0.62), parent=win)
    img = box(1.05, 0.26, 0.85, white, bevel=0.05, loc=(0.6, -0.6, -0.08), parent=win)
    sphere(0.13, mat(GOLD, rough=0.3, emit=0.5), loc=(-0.28, -0.16, 0.2), parent=img)
    prism([(-0.45, -0.32), (0.2, -0.32), (-0.12, 0.12)], 0.06, mat(zm, rough=0.4), bevel=0.01, loc=(0, -0.13, 0), rot=(R(90), 0, 0), parent=img)
    prism([(-0.1, -0.32), (0.45, -0.32), (0.18, 0.0)], 0.06, mat(zb, rough=0.4), bevel=0.01, loc=(0, -0.15, 0), rot=(R(90), 0, 0), parent=img)
    for i, wd in enumerate((0.55, 0.42, 0.55)):
        box(wd, 0.1, 0.09, mat("#BBF7D0", rough=0.4), bevel=0.02, loc=(1.28 + wd / 2, -0.5, 0.2 - 0.22 * i), parent=win)
    btn = box(0.95, 0.3, 0.36, gold, bevel=0.1, loc=(1.2, -0.95, -0.92), parent=win)                    # ปุ่ม
    box(0.5, 0.04, 0.08, mat("#231A02", rough=0.5), bevel=0.02, loc=(0, -0.16, 0), parent=btn)
    arrow = [(0, 0), (0, -1.0), (0.26, -0.76), (0.44, -1.16), (0.6, -1.08), (0.42, -0.69), (0.74, -0.69)]   # เคอร์เซอร์
    prism([(x * 0.62, y * 0.62) for x, y in arrow], 0.1, white, bevel=0.02, loc=(1.42, -1.25, 0.72), rot=(R(78), 0, R(-8)))
    code, slash = mat(zb, rough=0.28), gold
    for ch, x, m in (("<", -2.35, code), ("/", -1.45, slash), (">", -0.55, code)):
        text(ch, 1.75, 0.3, m, "consolab.ttf", bevel=0.03, loc=(x, -1.15, 0.74), rot=(R(82), 0, R(4)))
    bot = empty(loc=(2.75, -0.75, 0), rot=(0, 0, R(-24)))                                # หุ่นยนต์ผู้ช่วย
    bot.scale = (0.62, 0.62, 0.62)
    lh, rh = robot(bot, "coding", ((-1.45, -0.5, 2.0), (1.3, -0.35, 0.85)), stand=True)
    roll = empty(loc=(1.3, -0.35, 0.85), rot=(R(-12), R(18), 0), parent=bot)
    cyl(0.07, 1.4, gold, loc=(0, 0, 0.75), parent=roll)
    cyl(0.28, 1.0, mat("#F472B6", rough=0.5), loc=(0, 0, 1.55), rot=(0, R(90), 0), parent=roll)
    for c, r_, loc in (("#F472B6", 0.2, (3.2, 0.3, 2.55)), ("#38BDF8", 0.15, (2.75, 0.5, 3.0)), (GOLD, 0.12, (3.35, 0.2, 3.05)),
                       ("#F472B6", 0.1, (2.35, 0.2, 2.6))):                              # หยดสี CSS
        sphere(r_, mat(c, rough=0.15, emit=0.25), loc=loc)
    tag("<h1>", (-3.15, -0.2, 2.15), 14, zb)
    tag(".css", (-3.2, -1.2, 0.55), 18, zb)
    tag("{ }", (0.95, -1.9, 0.38), -10, zb)
    for s_, loc in ((0.28, (-3.3, 0.0, 3.3)), (0.18, (1.9, 0.3, 3.45)), (0.2, (-3.5, -0.9, 1.3)), (0.14, (0.4, -1.4, 2.0))):
        sparkle(s_, loc)
    rng = random.Random("coding_r")
    for i in range(12):                                                                  # ชิ้นเล็กลอย
        s_ = rng.uniform(0.08, 0.16)
        box(s_, s_, s_, mat(rng.choice((zb, GOLD, "#F0FFF6")), rough=0.3, emit=0.6), bevel=0.02,
            loc=(rng.uniform(-3.4, 3.4), rng.uniform(-1.2, 1.8), rng.uniform(0.4, 3.3)), rot=tuple(rng.uniform(0, 1.5) for _ in range(3)))
    return floor


def streak(length, width, m, **kw):
    """เส้นความเร็วปลายแหลม (ระนาบ XY ชี้ไปทาง +X)"""
    return prism([(0, -width / 2), (length, 0), (0, width / 2)], 0.03, m, bevel=0, **kw)


def scene_coding_01j(draft):
    """ไอเทม J · ตรา </> กระแทกพื้น — ตราหกเหลี่ยมพุ่งเฉียงลงมา มีเส้นความเร็วด้านหลัง คลื่นกระแทกและเศษแตกบนพื้น"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", az=-14, el=24, dist=14.6, target=(0, 0, 1.45), draft=draft)
    gold = mat(GOLD, rough=0.22, metal=0.85)
    hit = Vector((-0.9, -0.5, 0))
    for r_, e in ((1.0, 3.0), (1.9, 1.8), (2.9, 0.9)):                                   # คลื่นกระแทก
        torus(r_, 0.05 - 0.01 * r_, mat(zb, rough=0.3, emit=e), loc=(hit.x, hit.y, 0.03))
    rng = random.Random("slam")
    pts = [((2.0 if i % 2 == 0 else 0.75) * rng.uniform(0.8, 1.15) * math.cos(2 * math.pi * i / 18),
            (2.0 if i % 2 == 0 else 0.75) * rng.uniform(0.8, 1.15) * math.sin(2 * math.pi * i / 18) * 0.8) for i in range(18)]
    prism(pts, 0.02, mat(GOLD, rough=0.3, emit=1.6), bevel=0, loc=(hit.x, hit.y, 0.02))
    hub = empty(loc=(-0.2, 0.1, 1.62), rot=(R(72), 0, 0))
    hexa = lambda r: [(r * math.cos(R(60 * k + 30)), r * math.sin(R(60 * k + 30))) for k in range(6)]
    prism(hexa(1.72), 0.36, gold, bevel=0.05, loc=(0, 0, -0.18), parent=hub)
    prism(hexa(1.48), 0.22, mat("#0D3B2A", rough=0.3), bevel=0.04, loc=(0, 0, 0.18), parent=hub)
    prism(hexa(1.28), 0.06, mat("#06231A", rough=0.35), bevel=0.02, loc=(0, 0, 0.4), parent=hub)
    for ch, x, m in (("<", -0.66, mat(zb, rough=0.28, emit=0.4)), ("/", 0.0, gold), (">", 0.66, mat(zb, rough=0.28, emit=0.4))):
        text(ch, 1.4, 0.26, m, "consolab.ttf", bevel=0.02, loc=(x, 0, 0.6), parent=hub)
    for i, (ln, wd, off) in enumerate(((4.6, 0.5, 0.0), (3.6, 0.3, 0.75), (3.9, 0.34, -0.7), (2.6, 0.2, 1.3), (2.8, 0.2, -1.25))):   # เส้นความเร็ว
        streak(ln, wd, mat(zb if i % 2 == 0 else "#E2F9EA", rough=0.3, emit=1.4), loc=(1.0, 0.55 + off * 0.9, -0.5 - 0.1 * i),
               rot=(0, 0, R(27)), parent=hub)
    for i in range(9):                                                                    # เศษแตกกระเด็น
        a = rng.uniform(-0.3, math.pi + 0.3)
        r_ = rng.uniform(1.6, 3.0)
        s_ = rng.uniform(0.18, 0.36)
        prism([(0, 0), (s_ * 1.5, s_ * 0.3), (s_ * 0.5, s_)], 0.07, mat(rng.choice((zb, GOLD, "#0D3B2A")), rough=0.35), bevel=0,
              loc=(hit.x + r_ * math.cos(a), hit.y - abs(r_ * math.sin(a)) * 0.6, rng.uniform(0.25, 1.0)),
              rot=tuple(rng.uniform(0, 2) for _ in range(3)))
    sparkle(0.26, (-2.9, -0.3, 2.7))
    sparkle(0.16, (-1.9, -0.4, 3.1))
    return floor


def scene_coding_01k(draft):
    """ไอเทม K · ลูกกลิ้ง CSS — ลูกกลิ้งทาสีกลิ้งผ่านหน้าเว็บโครงเทา ส่วนที่ผ่านแล้วกลายเป็นหน้าเว็บมีสี"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", az=-16, el=24, dist=14.6, target=(0, 0, 1.45), draft=draft)
    gold = mat(GOLD, rough=0.25, metal=0.85)
    page = box(5.0, 0.2, 3.0, mat("#12362A", rough=0.35), bevel=0.07, loc=(-0.25, 0.75, 1.65), rot=(R(-12), 0, R(3)))
    cut, grey = 0.45, mat("#5B6E66", rough=0.7)

    def band(x0, x1, z, h, color, emit=0.0, y=-0.14, t=0.1):          # ซ้ายของลูกกลิ้ง = ทาสีแล้ว ขวา = โครงเทา
        if x0 < cut:
            xe = min(x1, cut)
            box(xe - x0, t, h, mat(color, rough=0.35, emit=emit), bevel=0.03, loc=((x0 + xe) / 2, y, z), parent=page)
        if x1 > cut:
            xs = max(x0, cut)
            box(x1 - xs, 0.05, h, grey, bevel=0.02, loc=((xs + x1) / 2, -0.12, z), parent=page)

    band(-2.3, 2.3, 1.08, 0.46, zb)
    band(-2.3, -0.75, 0.05, 1.35, "#F0FFF6", t=0.16)
    sphere(0.17, mat(GOLD, rough=0.3, emit=0.5), loc=(-1.9, -0.26, 0.4), parent=page)
    prism([(-0.6, -0.5), (0.3, -0.5), (-0.15, 0.2)], 0.06, mat(zm, rough=0.4), bevel=0.01, loc=(-1.5, -0.25, -0.05), rot=(R(90), 0, 0), parent=page)
    for i, x1 in enumerate((2.2, 1.7, 2.2, 1.2)):
        band(-0.5, x1, 0.55 - 0.3 * i, 0.12, "#BBF7D0", emit=0.3)
    band(-0.5, 0.9, -0.85, 0.36, GOLD)
    band(-2.3, 2.3, -1.2, 0.2, zm)
    rl = empty(loc=(cut + 0.42, -0.62, 0.0), parent=page)                                 # ลูกกลิ้ง
    cyl(0.42, 2.7, mat(zb, rough=0.22, emit=0.15), loc=(0, 0, 0), parent=rl)
    chrome = mat("#D6DEE8", rough=0.2, metal=1)
    for z in (-1.4, 1.4):
        cyl(0.16, 0.1, chrome, loc=(0, 0, z), parent=rl)
    tube([(0, 0, 1.45), (0.1, -0.2, 1.85), (0.9, -0.7, 1.7), (1.25, -1.0, 0.7), (1.3, -1.1, 0.2)], 0.075, chrome, parent=rl)
    tube([(1.3, -1.1, 0.2), (1.75, -1.75, -1.15)], 0.19, gold, parent=rl)
    for i, (z, ln) in enumerate(((1.0, 2.0), (0.25, 2.6), (-0.5, 1.7), (-1.1, 2.3))):     # เส้นความเร็วตามรอยกลิ้ง
        streak(ln, 0.12, mat("#F0FFF6", rough=0.3, emit=1.5), loc=(-0.6, -0.55, z), rot=(R(90), 0, R(180)), parent=rl)
    rng = random.Random("roller")
    for i in range(11):                                                                   # หยดสีกระเด็น
        sphere(rng.uniform(0.06, 0.17), mat(rng.choice((zb, zb, GOLD, "#F0FFF6")), rough=0.15, emit=0.3),
               loc=(rng.uniform(0.2, 1.3), rng.uniform(-1.0, -0.5), rng.uniform(-1.9, 1.9)), parent=rl)
    sparkle(0.24, (-3.1, -0.3, 2.9))
    sparkle(0.15, (2.9, -0.6, 3.0))
    return floor


def scene_coding_01l(draft):
    """ไอเทม L · กล่องแท็ก — กล่องสมบัติเปิดฝา แสงพุ่งขึ้น แท็กโค้ดกระเด็นออกมา"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", az=-20, el=24, dist=14.6, target=(0, 0, 1.5), draft=draft)
    gold, dark = mat(GOLD, rough=0.22, metal=0.85), mat("#0D3B2A", rough=0.3)
    for r_, e in ((1.8, 2.2), (2.5, 1.0)):
        torus(r_, 0.03, mat(zb, rough=0.3, emit=e), loc=(0, 0, 0.02))
    bx = empty(loc=(0, 0, 0), rot=(0, 0, R(-18)))
    box(2.3, 1.7, 1.15, dark, bevel=0.08, loc=(0, 0, 0.6), parent=bx)
    for x in (-0.95, 0.95):                                                               # แถบทอง
        box(0.22, 1.76, 1.2, gold, bevel=0.04, loc=(x, 0, 0.6), parent=bx)
    box(2.36, 1.76, 0.14, gold, bevel=0.04, loc=(0, 0, 1.13), parent=bx)
    box(0.5, 0.1, 0.5, gold, bevel=0.06, loc=(0, -0.88, 0.75), parent=bx)                 # กลอน
    text("</>", 0.3, 0.04, mat("#231A02", rough=0.5), "consolab.ttf", bevel=0.003, loc=(0, -0.94, 0.75), rot=(R(90), 0, 0), parent=bx)
    box(1.95, 1.4, 0.06, mat(mix(zb, "#FFFFFF", 0.45), rough=0.3, emit=1.1), bevel=0, loc=(0, 0, 1.18), parent=bx)   # แสงในกล่อง
    lid = empty(loc=(0, 0.85, 1.2), rot=(R(-62), 0, 0), parent=bx)                        # ฝาเปิดไปด้านหลัง
    box(2.3, 1.7, 0.42, dark, bevel=0.1, loc=(0, -0.85, 0.21), parent=lid)
    for x in (-0.95, 0.95):
        box(0.22, 1.76, 0.46, gold, bevel=0.04, loc=(x, -0.85, 0.21), parent=lid)
    for i, (ang, ln, wd) in enumerate(((-34, 2.3, 0.5), (-16, 2.9, 0.4), (0, 3.2, 0.6), (17, 2.8, 0.4), (35, 2.2, 0.5))):   # ลำแสง
        fan = empty(loc=(0, 0.25, 1.2), rot=(0, R(-90 + ang), 0), parent=bx)
        streak(ln, wd, mat(zb if i % 2 else "#E8FFF0", rough=0.3, emit=1.3), rot=(R(90), 0, 0), parent=fan)
    chip = mat("#082A1D", rough=0.3)
    for label, loc, rot, sc_ in (("<h1>", (-1.9, -0.9, 2.2), (-14, 18, 22), 1.25), ("<p>", (-0.5, -0.6, 3.05), (-10, -8, -12), 1.0),
                                 (".css", (1.75, -1.1, 2.35), (-12, -14, -24), 1.2), ("{ }", (0.9, -0.4, 3.3), (-8, 10, 14), 0.85)):
        t = box(1.15, 0.14, 0.52, chip, bevel=0.06, loc=loc, rot=tuple(R(v) for v in rot))
        text(label, 0.36, 0.05, mat("#F0FFF6", rough=0.4, emit=0.8), "consolab.ttf", bevel=0.004, loc=(0, -0.085, -0.01), rot=(R(90), 0, 0), parent=t)
        t.scale = (sc_, sc_, sc_)
    for s_, loc in ((0.26, (-2.9, -0.5, 3.0)), (0.18, (2.7, -0.4, 3.2)), (0.14, (0.1, -1.0, 2.2)), (0.2, (2.4, -0.9, 1.0))):
        sparkle(s_, loc)
    return floor


# ───────────────────────── ฉาก 12 ใบที่เหลือ (แนวเดียวกับ 4 ใบแรก: แผ่นหลัง + ของหลักตัวนูน + ป้ายลอย) ─────────────────────────
def panel(w, h, col, loc, rz=0, th=0.24, rx=-10, rough=0.3):
    """แผ่นตั้งเอนหลัง หน้าแผ่นหันเข้ากล้อง (-Y) ลูกวางที่ y = -(th/2 + นิดหน่อย)"""
    return box(w, th, h, mat(col, rough=rough), bevel=0.06, loc=loc, rot=(R(rx), 0, R(rz)))


def chip(label, loc, rz, zone, w=1.15, size=0.36, fn="consolab.ttf"):
    """ป้ายคำลอย พื้นสีเข้มของโซน"""
    t = box(w, 0.14, 0.52, mat(mix(ZONE[zone][2], "#000000", 0.2), rough=0.3), bevel=0.06, loc=loc, rot=(R(-10), 0, R(rz)))
    text(label, size, 0.05, mat("#FFFFFF", rough=0.4, emit=0.8), fn, bevel=0.004, loc=(0, -0.085, -0.01), rot=(R(90), 0, 0), parent=t)
    return t


def facing(loc, rz=0, rx=84):
    """จุดยึดสำหรับของแบน (ระนาบ XY ของลูก) ให้ตั้งหันเข้ากล้อง — แยกหมุน Z กับ X คนละชั้น ตัวหนังสือไม่เอียง"""
    return empty(rot=(R(rx), 0, 0), parent=empty(loc=loc, rot=(0, 0, R(rz))))


def arrow_arc(r, a0, a1, rad, m, n=9, **kw):
    """ลูกศรโค้ง (ระนาบ XY ของ hub) จากมุม a0 ไป a1"""
    hub = empty(**kw)
    tube([(r * math.cos(a0 + (a1 - a0) * i / n), r * math.sin(a0 + (a1 - a0) * i / n), 0) for i in range(n + 1)], rad, m, parent=hub)
    s = 1 if a1 > a0 else -1
    head = cyl(rad * 2.8, rad * 6, m, r2=0, seg=24, loc=(r * math.cos(a1), r * math.sin(a1), 0), parent=hub)
    head.rotation_euler = Vector((-math.sin(a1) * s, math.cos(a1) * s, 0)).to_track_quat("Z", "Y").to_euler()
    return hub


def heart(s):
    return [(s * 16 * math.sin(t) ** 3 / 17, s * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 17)
            for t in (2 * math.pi * i / 30 for i in range(30))]


def code_window(loc, zone="coding"):
    """หน้าต่างโค้ดพื้นเข้ม + แถบหัว + ปุ่ม 3 จุด (เหมือนใบ coding_01)"""
    win = panel(3.9, 2.7, "#06231A", loc)
    box(3.9, 0.28, 0.46, mat("#22A95C", rough=0.35), bevel=0.07, loc=(0, -0.01, 1.12), parent=win)
    for i, c in enumerate(("#F87171", GOLD, "#86EFAC")):
        sphere(0.095, mat(c, rough=0.3, emit=0.6), loc=(-1.65 + 0.3 * i, -0.15, 1.12), parent=win)
    box(3.55, 0.05, 1.95, mat("#0D3B2A", rough=0.5), bevel=0.02, loc=(0, -0.12, -0.2), parent=win)
    return win


def scene_coding_02(draft):
    """Python พื้นฐาน — หน้าต่างโค้ดย่อหน้า + บล็อก for / if / print() เรียงขั้นบันไดตามการย่อหน้า + ลูกศรวนลูป"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", dist=14.6, target=(0, 0, 1.2), draft=draft)
    win = code_window((0.45, 0.85, 1.5))
    for i, (ind, wd, c) in enumerate(((0, 1.5, zb), (1, 1.9, "#E2F9EA"), (2, 1.2, GOLD), (2, 0.8, "#E2F9EA"), (1, 1.4, zb), (0, 1.0, "#E2F9EA"))):
        box(wd, 0.04, 0.1, mat(c, rough=0.4, emit=0.5), bevel=0.02, loc=(-1.55 + 0.42 * ind + wd / 2, -0.16, 0.55 - 0.3 * i), parent=win)
    dark = mat("#06231A", rough=0.4)
    for k, (label, wd, x0, c) in enumerate((("print()", 2.55, -1.3, "#E2F9EA"), ("if", 1.45, -2.0, GOLD), ("for", 1.7, -2.7, zb))):
        b = box(wd, 0.55, 0.64, mat(c, rough=0.26), bevel=0.09, loc=(x0 + wd / 2, -1.05, 0.34 + 0.7 * k), rot=(0, 0, R(5)))
        text(label, 0.44, 0.05, dark, "consolab.ttf", bevel=0.004, loc=(0, -0.285, -0.01), rot=(R(90), 0, 0), parent=b)
    arrow_arc(0.62, R(210), R(-70), 0.075, mat(GOLD, rough=0.22, metal=0.85, emit=0.25), parent=facing((2.55, -1.15, 0.95), -10))
    chip("x = 5", (2.95, -0.1, 2.4), -14, "coding", w=1.5)
    return floor


def scene_coding_03(draft):
    """JavaScript เชิงโต้ตอบ — ปุ่ม CLICK ตัวนูนถูกเคอร์เซอร์กด มีประกายคลิก + หน้าเว็บ + แผ่น JS"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", dist=14.6, target=(0, 0, 1.2), draft=draft)
    win = code_window((-0.55, 0.9, 1.5))
    box(1.25, 0.05, 0.95, mat(zm, rough=0.35), bevel=0.04, loc=(-0.95, -0.16, 0.2), parent=win)
    for i, wd in enumerate((1.5, 1.1, 1.35)):
        box(wd, 0.04, 0.1, mat("#E2F9EA", rough=0.4, emit=0.5), bevel=0.02, loc=(-0.05 + wd / 2, -0.16, 0.55 - 0.3 * i), parent=win)
    box(0.72, 0.06, 0.3, mat(zb, rough=0.3, emit=0.6), bevel=0.14, loc=(0.35, -0.16, -0.72), parent=win)
    sphere(0.13, mat("#FFFFFF", rough=0.3, emit=0.4), loc=(0.55, -0.2, -0.72), parent=win)
    hub = empty(loc=(0.25, -1.05, 0.98), rot=(R(-16), 0, 0), parent=empty(rot=(0, 0, R(-5))))
    box(3.35, 0.3, 1.35, mat("#082A1D", rough=0.3), bevel=0.12, parent=hub)
    box(3.0, 0.36, 1.0, mat(zb, rough=0.22), bevel=0.15, loc=(0, -0.2, 0.03), parent=hub)
    text("CLICK", 0.64, 0.08, mat("#06231A", rough=0.4), "ariblk.ttf", bevel=0.006, loc=(-0.25, -0.4, 0.03), rot=(R(90), 0, 0), parent=hub)
    cur = [(0, 0), (0, -1.0), (0.26, -0.76), (0.45, -1.18), (0.6, -1.11), (0.41, -0.7), (0.72, -0.7)]
    tx, tz = 1.0, 0.2
    prism([(x * 0.95, y * 0.95) for x, y in cur], 0.16, mat("#F8FAFC", rough=0.22), bevel=0.035, loc=(tx, -0.6, tz), rot=(R(90), 0, 0), parent=hub)
    ray = mat(GOLD, rough=0.3, emit=2.2)
    for a in (55, 95, 135, 175):
        box(0.34, 0.06, 0.075, ray, bevel=0.02, loc=(tx + 0.5 * math.cos(R(a)), -0.62, tz + 0.5 * math.sin(R(a))), rot=(0, -R(a), 0), parent=hub)
    js = box(1.0, 0.14, 1.0, mat(GOLD, rough=0.25), bevel=0.07, loc=(2.7, 0.55, 1.75), rot=(R(-10), 0, R(-14)))
    text("JS", 0.52, 0.05, mat("#06231A", rough=0.4), "ariblk.ttf", bevel=0.004, loc=(0.12, -0.085, -0.2), rot=(R(90), 0, 0), parent=js)
    chip("onclick", (-2.6, -1.35, 0.5), 16, "coding", w=1.75)
    chip("DOM", (2.95, -1.0, 0.55), -16, "coding")
    return floor


def scene_coding_04(draft):
    """ฐานข้อมูล SQL — ถังฐานข้อมูล 3 ชั้น + ตารางที่แถวผลลัพธ์ของ SELECT ยื่นออกมาเป็นสีทอง"""
    zb, zm, zk = ZONE["coding"]
    floor = stage("coding", dist=14.6, target=(0, 0, 1.2), draft=draft)
    tb = panel(3.8, 2.7, "#06231A", (0.95, 0.9, 1.5), rz=-6)
    line, dline = mat("#E2F9EA", rough=0.4, emit=0.5), mat("#3B1206", rough=0.5)
    rng = random.Random(4)
    for r in range(5):
        for c in range(3):
            hit = r == 2
            col = zm if r == 0 else GOLD if hit else "#0D3B2A"
            y = -0.3 if hit else -0.14
            box(1.12, 0.06, 0.4, mat(col, rough=0.35, emit=0.25 if hit else 0), bevel=0.03, loc=(-1.2 + 1.2 * c, y, 1.0 - 0.5 * r), parent=tb)
            wd = rng.uniform(0.4, 0.85)
            box(wd, 0.03, 0.09, dline if hit else line, bevel=0.02, loc=(-1.65 + 1.2 * c + wd / 2, y - 0.035, 1.0 - 0.5 * r), parent=tb)
    cx, cy = -1.55, -0.35
    ring, led = mat(zb, rough=0.3, emit=1.4), mat(GOLD, rough=0.3, emit=1.5)
    for k in range(3):
        z = 0.28 + 0.62 * k
        cyl(1.0, 0.52, mat(zm, rough=0.22), loc=(cx, cy, z))
        torus(1.0, 0.045, ring, loc=(cx, cy, z + 0.26))
        for j in range(3):
            a = R(-108 - 13 * j)
            sphere(0.06, led, loc=(cx + 1.01 * math.cos(a), cy + 1.01 * math.sin(a), z - 0.05))
    cyl(0.82, 0.04, mat("#0D3B2A", rough=0.3), loc=(cx, cy, 1.79))
    chip("SELECT", (0.9, -1.35, 0.5), -10, "coding", w=1.75)
    chip("WHERE", (2.6, -0.75, 0.8), -18, "coding", w=1.5)
    chip("JOIN", (-2.55, 0.3, 2.6), 14, "coding")
    return floor


def scene_office_02(draft):
    """Excel สูตรคำนวณ — ตารางเซลล์ที่มีเซลล์ผลรวมถูกเลือก + เครื่องหมาย = และ Σ ตัวนูน"""
    zb, zm, zk = ZONE["office"]
    floor = stage("office", dist=14.6, target=(-0.1, 0, 1.25), draft=draft)
    sh = panel(4.1, 2.9, "#F8FAFC", (-0.75, 0.9, 1.65), rz=6, th=0.12, rough=0.55)
    y = -0.07
    box(4.1, 0.04, 0.36, mat(zm, rough=0.4), bevel=0.02, loc=(0, y, 1.27), parent=sh)
    box(0.42, 0.04, 2.54, mat("#C7D2E4", rough=0.6), bevel=0.02, loc=(-1.84, y, -0.18), parent=sh)
    grid, ink_, white = mat("#B6C2D6", rough=0.6), mat("#1E293B", rough=0.5), mat("#F0F9FF", rough=0.4, emit=0.8)
    for i, ch in enumerate("ABCD"):
        text(ch, 0.24, 0.03, white, "arialbd.ttf", bevel=0.003, loc=(-1.17 + 0.92 * i, y - 0.03, 1.27), rot=(R(90), 0, 0), parent=sh)
        box(0.02, 0.03, 2.54, grid, bevel=0, loc=(-0.71 + 0.92 * i, y, -0.18), parent=sh)
    for j in range(6):
        z = 0.88 - 0.42 * j
        box(3.68, 0.03, 0.02, grid, bevel=0, loc=(0.21, y, z - 0.21), parent=sh)
        text(str(j + 1), 0.2, 0.03, ink_, "arialbd.ttf", bevel=0.003, loc=(-1.84, y - 0.03, z), rot=(R(90), 0, 0), parent=sh)
        if j < 4:
            box((0.62, 0.5, 0.7, 0.44)[j], 0.03, 0.09, mat("#94A3B8", rough=0.6), bevel=0.01, loc=(-1.25, y, z), parent=sh)
            text(("20", "35", "45", "50")[j], 0.26, 0.03, ink_, "arialbd.ttf", bevel=0.003, loc=(-0.05, y - 0.03, z), rot=(R(90), 0, 0), parent=sh)
    z = 0.88 - 0.42 * 4
    box(0.92, 0.05, 0.42, mat("#DBEAFE", rough=0.5), bevel=0.01, loc=(-0.25, y - 0.01, z), parent=sh)
    text("150", 0.3, 0.04, mat(zm, rough=0.4), "ariblk.ttf", bevel=0.003, loc=(-0.25, y - 0.05, z), rot=(R(90), 0, 0), parent=sh)
    gold = mat(GOLD, rough=0.3, metal=0.85, emit=0.3)
    for dz in (0.21, -0.21):
        box(0.98, 0.07, 0.05, gold, bevel=0, loc=(-0.25, y - 0.03, z + dz), parent=sh)
    for dx in (0.46, -0.46):
        box(0.05, 0.07, 0.47, gold, bevel=0, loc=(-0.25 + dx, y - 0.03, z), parent=sh)
    text("=", 2.5, 0.38, mat(GOLD, rough=0.22, metal=0.85), "ariblk.ttf", bevel=0.035, loc=(0.75, -0.8, 0.95), rot=(R(84), 0, R(-6)))
    text("Σ", 2.7, 0.4, mat("#2563EB", rough=0.25), "arialbd.ttf", bevel=0.035, loc=(2.35, -1.1, 1.02), rot=(R(84), 0, R(-12)))
    chip("=SUM()", (-2.3, -1.0, 0.5), 16, "office", w=1.75)
    chip("IF", (3.0, 0.5, 2.5), -14, "office", w=0.95)
    return floor


def scene_office_03(draft):
    """Excel Pivot Table & กราฟ — ข้อมูลดิบหลายแถว -> กราฟแท่งตัวนูน + ลูกศรแนวโน้ม + กราฟวงแหวน"""
    zb, zm, zk = ZONE["office"]
    floor = stage("office", dist=14.6, target=(-0.1, 0, 1.25), draft=draft)
    raw = panel(2.7, 3.0, "#F8FAFC", (-2.0, 1.05, 1.65), rz=10, th=0.1, rough=0.55)
    y = -0.06
    box(2.7, 0.04, 0.34, mat(zm, rough=0.4), bevel=0.02, loc=(0, y, 1.33), parent=raw)
    grey, rng = mat("#94A3B8", rough=0.6), random.Random(3)
    for j in range(10):
        for c in range(3):
            wd = rng.uniform(0.35, 0.7)
            box(wd, 0.03, 0.075, grey, bevel=0.01, loc=(-1.15 + 0.85 * c + wd / 2, y, 0.98 - 0.24 * j), parent=raw)
    base = box(3.6, 1.5, 0.18, mat("#0B1B45", rough=0.3), bevel=0.06, loc=(0.25, -0.75, 0.09), rot=(0, 0, R(-6)))
    hs = (0.8, 1.35, 1.1, 2.1)
    for i, (h, c) in enumerate(zip(hs, ("#BAE6FD", zb, "#2563EB", GOLD))):
        box(0.6, 0.6, h, mat(c, rough=0.22, metal=0.6 if c == GOLD else 0), bevel=0.06, loc=(-1.26 + 0.84 * i, 0, 0.09 + h / 2), parent=base)
    arrow = mat("#F0F9FF", rough=0.3, emit=0.9)
    pts = [(-1.26 + 0.84 * i, -0.38, 0.4 + h) for i, h in enumerate(hs)]
    pts[2] = (pts[2][0], -0.38, pts[2][2] + 0.25)
    tube(pts, 0.05, arrow, parent=base)
    head = cyl(0.15, 0.36, arrow, r2=0, seg=24, loc=pts[3], parent=base)
    head.rotation_euler = (Vector(pts[3]) - Vector(pts[2])).to_track_quat("Z", "Y").to_euler()
    pie = facing((2.6, 0.75, 1.9), -14, 80)
    for a0, a1, c, out in ((95, 240, "#2563EB", 0), (240, 330, "#7DD3FC", 0), (330, 455, GOLD, 0.14)):
        am = R((a0 + a1) / 2)
        wedge(0.36, 0.95, R(a0 + 2), R(a1 - 2), 0.3, mat(c, rough=0.22), seg=18, bevel=0.035,
              loc=(out * math.cos(am), out * math.sin(am), 0), parent=pie)
    chip("PIVOT", (-2.7, -1.35, 0.5), 16, "office", w=1.5)
    chip("SUM", (2.65, -1.2, 0.55), -16, "office")
    return floor


def scene_office_04(draft):
    """PowerPoint นำเสนองาน — จอสไลด์ (หัวข้อ + 3 บรรทัด + ภาพ) + ปุ่มเล่นตัวนูน + รีโมตยิงเลเซอร์ไปที่จอ"""
    zb, zm, zk = ZONE["office"]
    floor = stage("office", dist=14.6, target=(-0.1, 0, 1.3), draft=draft)
    fr = panel(4.4, 2.85, "#0B1B45", (-0.65, 0.95, 1.8), rz=5, th=0.16)
    box(4.1, 0.06, 2.55, mat("#F8FAFC", rough=0.55), bevel=0.03, loc=(0, -0.1, 0), parent=fr)
    y = -0.15
    box(2.1, 0.04, 0.32, mat(zm, rough=0.4), bevel=0.03, loc=(-0.8, y, 0.85), parent=fr)
    grey = mat("#94A3B8", rough=0.6)
    for i, wd in enumerate((1.5, 1.2, 1.4)):
        sphere(0.075, mat(GOLD, rough=0.3), loc=(-1.75, y, 0.3 - 0.4 * i), parent=fr)
        box(wd, 0.03, 0.11, grey, bevel=0.01, loc=(-1.55 + wd / 2, y, 0.3 - 0.4 * i), parent=fr)
    box(1.35, 0.05, 1.45, mat(zb, rough=0.35), bevel=0.04, loc=(1.2, y, -0.25), parent=fr)
    for i, h in enumerate((0.4, 0.7, 1.0)):
        box(0.26, 0.05, h, mat("#F0F9FF", rough=0.4), bevel=0.02, loc=(0.82 + 0.38 * i, y - 0.04, -0.82 + h / 2), parent=fr)
    play = facing((1.95, -1.05, 1.02), -12, 80)
    cyl(1.0, 0.32, mat("#2563EB", rough=0.2), parent=play)
    torus(1.0, 0.07, mat(GOLD, rough=0.25, metal=0.9), loc=(0, 0, 0.16), parent=play)
    prism([(-0.34, -0.52), (0.62, 0), (-0.34, 0.52)], 0.2, mat(GOLD, rough=0.22, metal=0.85, emit=0.25), bevel=0.06, loc=(0, 0, 0.16), parent=play)
    a, b = Vector((-2.0, -0.75, 0.34)), Vector((-0.75, 0.62, 2.15))
    d = b - a
    rem = box(0.5, 1.25, 0.28, mat("#0B1B45", rough=0.25), bevel=0.11, loc=(a.x - 0.3 * d.normalized().x, a.y - 0.45, 0.16),
              rot=(0, 0, -math.atan2(d.x, d.y)))
    sphere(0.11, mat("#EF4444", rough=0.3, emit=0.6), loc=(0, 0.15, 0.15), parent=rem)
    red = mat("#F87171", rough=0.3, emit=5.0)
    tube([tuple(a), tuple(b)], 0.02, red)
    sphere(0.1, red, loc=tuple(b))
    chip("F5", (3.0, 0.4, 2.55), -14, "office", w=0.95)
    chip("6 x 6", (-0.35, -1.75, 0.45), 8, "office", w=1.4)
    return floor


def scene_design_02(draft):
    """Photoshop ตกแต่งภาพ — เลเยอร์ 3 ชั้นแยกลอย (พื้นโปร่งลายตาราง / ภูเขา / ดวงอาทิตย์) + พู่กัน"""
    zb, zm, zk = ZONE["design"]
    floor = stage("design", dist=14.6, target=(-0.1, 0, 1.3), draft=draft)
    hub = empty(rot=(R(28), 0, 0), parent=empty(loc=(-0.6, 0.35, 0.62), rot=(0, 0, R(-20))))
    w, h = 3.0, 2.0
    white = mat("#FFF7ED", rough=0.35)

    def frame(z):
        for s in (1, -1):
            box(w + 0.1, 0.1, 0.12, white, bevel=0.02, loc=(0, s * h / 2, z), parent=hub)
            box(0.1, h + 0.1, 0.12, white, bevel=0.02, loc=(s * w / 2, 0, z), parent=hub)

    for i in range(8):
        for j in range(5):
            box(w / 8, h / 5, 0.06, mat("#F1F5F9" if (i + j) % 2 else "#94A3B8", rough=0.5), bevel=0,
                loc=(-w / 2 + w / 16 + w / 8 * i, -h / 2 + h / 10 + h / 5 * j, 0), parent=hub)
    frame(0)
    box(w, h, 0.06, mat("#38BDF8", rough=0.3), bevel=0, loc=(0, 0, 1.05), parent=hub)
    prism([(-1.45, -0.97), (-0.55, 0.45), (0.55, -0.97)], 0.12, mat("#15803D", rough=0.35), loc=(0, 0, 1.08), parent=hub)
    prism([(-0.25, -0.97), (0.7, 0.1), (1.45, -0.97)], 0.16, mat("#4ADE80", rough=0.35), loc=(0, 0, 1.08), parent=hub)
    frame(1.05)
    cyl(0.44, 0.14, mat(GOLD, rough=0.25, emit=0.5), loc=(0.85, 0.45, 2.1), parent=hub)
    for dx, r in ((-1.05, 0.26), (-0.72, 0.34), (-0.38, 0.24)):
        cyl(r, 0.12, mat("#FFFFFF", rough=0.4), loc=(dx, 0.38 + r * 0.4, 2.1), parent=hub)
    frame(2.1)
    br = empty(loc=(1.55, -1.7, 0.12), rot=(0, R(90), R(22)))
    cyl(0.085, 1.8, mat(zb, rough=0.3), seg=24, parent=br)
    cyl(0.1, 0.3, mat("#D6DEE8", rough=0.2, metal=1), seg=24, loc=(0, 0, 1.05), parent=br)
    cyl(0.11, 0.5, mat("#2563EB", rough=0.4), r2=0.02, seg=24, loc=(0, 0, 1.45), parent=br)
    chip(".PSD", (2.9, 0.3, 2.3), -14, "design")
    chip("Layer", (-2.55, -1.2, 0.5), 16, "design", w=1.45)
    return floor


def scene_design_03(draft):
    """Illustrator วาดเวกเตอร์ — หัวปากกา Pen tool ลากเส้นโค้งที่มีจุดยึดและแขนปรับ + โลโก้หกเหลี่ยมบนอาร์ตบอร์ด"""
    zb, zm, zk = ZONE["design"]
    floor = stage("design", dist=14.6, target=(-0.1, 0, 1.3), draft=draft)
    ab = panel(3.5, 2.8, "#FFF7ED", (1.0, 0.95, 1.7), rz=-6, th=0.12, rough=0.5)
    blue = mat("#38BDF8", rough=0.3, emit=1.2)
    hx = [(0.9 * math.cos(R(90 + 60 * i)), 0.9 * math.sin(R(90 + 60 * i))) for i in range(6)]
    prism(hx, 0.1, mat(zb, rough=0.25), bevel=0.03, loc=(0, -0.06, 0.05), rot=(R(90), 0, 0), parent=ab)
    prism([(x * 0.48, y * 0.48) for x, y in STAR], 0.08, mat("#FFF7ED", rough=0.3), bevel=0.02, loc=(0, -0.16, 0.05), rot=(R(90), 0, 0), parent=ab)
    for x, y in hx:
        box(0.15, 0.08, 0.15, mat("#FFFFFF", rough=0.3, emit=0.5), bevel=0.02, loc=(x, -0.2, 0.05 + y), parent=ab)
    for s in (1, -1):
        box(2.15, 0.03, 0.025, blue, bevel=0, loc=(0, -0.08, 0.05 + s * 1.02), parent=ab)
        box(0.025, 0.03, 2.05, blue, bevel=0, loc=(s * 1.07, -0.08, 0.05), parent=ab)
    path = [(2.95, -1.0, 0.09), (1.7, -1.8, 0.09), (0.35, -0.95, 0.09), (-1.0, -1.6, 0.09)]
    tube(path, 0.075, mat(zb, rough=0.3, emit=0.8))
    anchor = mat("#FFFFFF", rough=0.3, emit=0.4)
    for p, ang in ((path[1], 8), (path[2], -8)):
        box(0.27, 0.27, 0.22, anchor, bevel=0.03, loc=(p[0], p[1], 0.11), rot=(0, 0, R(ang)))
        hd = Vector((math.cos(R(ang)), math.sin(R(ang)), 0)) * 0.85
        box(1.7, 0.03, 0.03, blue, bevel=0, loc=(p[0], p[1], 0.24), rot=(0, 0, R(ang)))
        for s in (1, -1):
            sphere(0.085, blue, loc=(p[0] + s * hd.x, p[1] + s * hd.y, 0.24))
    nib = empty(rot=(R(84), 0, 0), parent=empty(loc=(-1.0, -1.6, 0.16), rot=(0, R(-27), 0)))
    gold = mat(GOLD, rough=0.22, metal=0.85)
    prism([(0, 0), (0.52, 0.8), (0.52, 1.5), (-0.52, 1.5), (-0.52, 0.8)], 0.2, gold, bevel=0.03, loc=(0, 0, -0.1), parent=nib)
    dark = mat("#1C0A03", rough=0.4)
    box(0.04, 0.85, 0.03, dark, bevel=0, loc=(0, 0.5, 0.105), parent=nib)
    cyl(0.11, 0.03, dark, loc=(0, 0.98, 0.105), parent=nib)
    cyl(0.5, 0.16, gold, loc=(0, 1.58, 0), rot=(R(90), 0, 0), parent=nib)
    cyl(0.42, 1.5, mat("#7C2D12", rough=0.22), loc=(0, 2.4, 0), rot=(R(90), 0, 0), parent=nib)
    chip(".AI", (-2.7, -1.25, 0.5), 16, "design")
    chip("Vector", (2.25, -1.85, 0.5), -10, "design", w=1.6)
    return floor


def scene_design_04(draft):
    """Canva ออกแบบสื่อโซเชียล — มือถือโชว์โพสต์สี่เหลี่ยมจัตุรัส + เทมเพลตเรียงพัดด้านหลัง + หัวใจลอย"""
    zb, zm, zk = ZONE["design"]
    floor = stage("design", dist=14.6, target=(-0.1, 0, 1.35), draft=draft)
    cream, grey = mat("#FFF7ED", rough=0.5), mat("#D6C7B8", rough=0.6)
    for k, (c, rz, x) in enumerate((("#A855F7", 18, -2.55), ("#14B8A6", 10, -1.75), ("#F43F5E", 2, -0.95))):
        cd = panel(1.75, 2.45, c, (x, 1.25 - 0.22 * k, 1.5), rz=rz, th=0.08)
        box(1.35, 0.03, 1.0, cream, bevel=0.03, loc=(0, -0.05, 0.5), parent=cd)
        for i, wd in enumerate((1.2, 0.8)):
            box(wd, 0.03, 0.12, cream, bevel=0.02, loc=(-0.675 + wd / 2, -0.05, -0.35 - 0.28 * i), parent=cd)
    ph = box(1.95, 0.2, 3.4, mat("#1C1917", rough=0.22), bevel=0.16, loc=(0.9, -0.55, 1.78), rot=(R(-12), 0, R(-8)))
    box(1.72, 0.04, 3.15, cream, bevel=0.1, loc=(0, -0.1, 0), parent=ph)
    y = -0.13
    sphere(0.14, mat(zb, rough=0.3), loc=(-0.6, y, 1.3), parent=ph)
    box(0.75, 0.03, 0.11, grey, bevel=0.02, loc=(-0.02, y, 1.3), parent=ph)
    box(1.6, 0.05, 1.6, mat(zb, rough=0.3), bevel=0.04, loc=(0, y, 0.28), parent=ph)
    text("SALE", 0.44, 0.05, mat("#FFFFFF", rough=0.4, emit=0.7), "ariblk.ttf", bevel=0.004, loc=(0, y - 0.05, 0.58), rot=(R(90), 0, 0), parent=ph)
    text("50%", 0.56, 0.06, mat("#3B1206", rough=0.4), "ariblk.ttf", bevel=0.004, loc=(0, y - 0.05, 0.02), rot=(R(90), 0, 0), parent=ph)
    red = mat("#F43F5E", rough=0.22, emit=0.35)
    prism(heart(0.16), 0.06, red, bevel=0.015, loc=(-0.6, y, -0.78), rot=(R(90), 0, 0), parent=ph)
    for i in range(2):
        sphere(0.085, grey, loc=(-0.28 + 0.26 * i, y, -0.78), parent=ph)
    for i, wd in enumerate((1.35, 0.9)):
        box(wd, 0.03, 0.1, grey, bevel=0.02, loc=(-0.72 + wd / 2, y, -1.08 - 0.22 * i), parent=ph)
    prism(heart(0.62), 0.3, red, bevel=0.06, loc=(0, 0, -0.15), parent=facing((2.75, -0.9, 2.15), -14, 82))
    prism(heart(0.3), 0.18, red, bevel=0.04, loc=(0, 0, -0.09), parent=facing((3.1, -0.3, 3.0), -6, 82))
    aa = box(1.05, 0.14, 1.05, mat("#1C0A03", rough=0.3), bevel=0.07, loc=(2.7, -1.35, 0.62), rot=(R(-10), 0, R(-16)))
    text("Aa", 0.62, 0.06, mat(GOLD, rough=0.3, emit=0.4), "ariblk.ttf", bevel=0.004, loc=(0, -0.09, -0.02), rot=(R(90), 0, 0), parent=aa)
    chip("1080x1080", (-1.6, -1.45, 0.5), 12, "design", w=2.3)
    return floor


def scene_hardware_01(draft):
    """CPU และเมนบอร์ด — ซีพียูลอยเหนือซ็อกเก็ตกำลังจะลงล็อก บนเมนบอร์ด (ช่องแรม ฮีตซิงก์ ชิปเซ็ต)"""
    zb, zm, zk = ZONE["hardware"]
    floor = stage("hardware", az=20, el=31, dist=14.6, target=(0.1, 0, 0.95), draft=draft)
    mb = box(5.2, 3.8, 0.16, mat("#2A0F1E", rough=0.35), bevel=0.04, loc=(-0.35, 0.55, 0.08), rot=(0, 0, R(-14)))
    t = 0.08
    steel, chrome = mat("#2B3442", rough=0.38, metal=0.9), mat("#D6DEE8", rough=0.2, metal=1.0)
    gold, black = mat(GOLD, rough=0.3, metal=0.9), mat("#0A0D12", rough=0.5)
    sx, sy = -0.75, -0.35
    box(1.8, 1.8, 0.05, gold, bevel=0, loc=(sx, sy, t + 0.025), parent=mb)
    for i in range(9):
        box(1.8, 0.03, 0.06, black, bevel=0, loc=(sx, sy - 0.8 + 0.2 * i, t + 0.03), parent=mb)
        box(0.03, 1.8, 0.06, black, bevel=0, loc=(sx - 0.8 + 0.2 * i, sy, t + 0.03), parent=mb)
    for s in (1, -1):
        box(0.17, 2.2, 0.18, chrome, bevel=0.03, loc=(sx + s * 1.02, sy, t + 0.09), parent=mb)
        box(2.2, 0.17, 0.18, chrome, bevel=0.03, loc=(sx, sy + s * 1.02, t + 0.09), parent=mb)
    for i in range(7):
        box(2.0, 0.07, 0.5, steel, bevel=0.01, loc=(sx, 1.05 + 0.115 * i, t + 0.25), parent=mb)
    for i in range(4):
        box(0.15, 2.9, 0.16, mat(zm if i % 2 else "#0A0D12", rough=0.35), bevel=0.02, loc=(1.15 + 0.27 * i, 0.15, t + 0.08), parent=mb)
    box(0.3, 1.4, 0.3, mat("#EEF1F5", rough=0.4), bevel=0.03, loc=(2.38, 0.3, t + 0.15), parent=mb)
    box(0.95, 0.95, 0.14, steel, bevel=0.04, loc=(-2.0, -1.2, t + 0.07), parent=mb)
    box(0.55, 0.55, 0.03, mat(zb, rough=0.3, emit=1.6), bevel=0, loc=(-2.0, -1.2, t + 0.15), parent=mb)
    for x, y_ in ((-2.2, 0.2), (-2.2, 0.55), (-1.95, 1.5), (0.55, -1.55), (0.85, -1.55)):
        cyl(0.11, 0.3, black, seg=24, loc=(x, y_, t + 0.15), parent=mb)
        cyl(0.1, 0.02, chrome, seg=24, loc=(x, y_, t + 0.305), parent=mb)
    cpu = box(1.72, 1.72, 0.1, mat("#14532D", rough=0.35), bevel=0.02, loc=(sx, sy - 0.1, 1.55), rot=(R(20), 0, 0), parent=mb)
    box(1.36, 1.36, 0.16, mat("#C3CCD8", rough=0.5, metal=0.6), bevel=0.06, loc=(0, 0, 0.1), parent=cpu)
    text("CPU", 0.5, 0.04, mat(zm, rough=0.4, emit=0.5), "ariblk.ttf", bevel=0.003, loc=(0, 0, 0.19), parent=cpu)
    prism([(0, 0), (0.24, 0), (0, 0.24)], 0.02, gold, bevel=0, loc=(-0.83, -0.83, 0.05), parent=cpu)
    guide = mat(zb, rough=0.3, emit=2.5)
    for dx in (0.86, -0.86):
        for dy in (0.86, -0.86):
            box(0.035, 0.035, 0.95, guide, bevel=0, loc=(sx + dx, sy + dy, t + 0.62), parent=mb)
    chip("LGA1700", (1.7, -1.75, 0.5), 14, "hardware", w=1.95)
    chip("Socket", (-2.6, -0.9, 1.6), 24, "hardware", w=1.6)
    return floor


def scene_hardware_02(draft):
    """RAM และหน่วยเก็บข้อมูล — แท่งแรมตั้งเอียง (ชิปดำ + ขาทอง) + SSD + ฮาร์ดดิสก์จานหมุน"""
    zb, zm, zk = ZONE["hardware"]
    floor = stage("hardware", az=20, dist=14.6, target=(0.1, 0, 1.15), draft=draft)
    steel, chrome = mat("#2B3442", rough=0.38, metal=0.9), mat("#D6DEE8", rough=0.2, metal=1.0)
    gold, black = mat(GOLD, rough=0.3, metal=0.9), mat("#0A0D12", rough=0.45)

    def stick(loc, rz, roll, label):
        e = empty(rot=(0, R(roll), 0), parent=empty(rot=(R(-12), 0, 0), parent=empty(loc=loc, rot=(0, 0, R(rz)))))
        box(4.3, 0.09, 1.1, mat(zm, rough=0.32), bevel=0.02, parent=e)
        for i in range(8):
            if label and i in (3, 4):
                continue
            box(0.38, 0.08, 0.55, black, bevel=0.02, loc=(-1.75 + 0.5 * i, -0.07, 0.12), parent=e)
        for i in range(40):
            if i not in (17, 18):
                box(0.065, 0.11, 0.17, gold, bevel=0, loc=(-1.95 + 0.1 * i, 0, -0.47), parent=e)
        if label:
            box(0.92, 0.03, 0.5, mat("#F8FAFC", rough=0.5), bevel=0.02, loc=(0, -0.06, 0.12), parent=e)
            text(label, 0.3, 0.03, mat("#1A0610", rough=0.5), "ariblk.ttf", bevel=0.003, loc=(0, -0.085, 0.12), rot=(R(90), 0, 0), parent=e)

    stick((0.7, 1.5, 1.05), -8, -6, "")
    stick((-0.3, 0.6, 1.7), -8, 9, "DDR")
    ssd = box(2.5, 1.75, 0.3, steel, bevel=0.05, loc=(1.35, -1.2, 0.15), rot=(0, 0, R(-12)))
    box(2.1, 1.35, 0.02, mat(zb, rough=0.35), bevel=0, loc=(0, 0, 0.155), parent=ssd)
    text("SSD", 0.66, 0.04, mat("#1A0610", rough=0.5), "ariblk.ttf", bevel=0.003, loc=(-0.1, 0.12, 0.18), parent=ssd)
    text("1TB", 0.34, 0.03, mat("#FFFFFF", rough=0.4, emit=0.5), "ariblk.ttf", bevel=0.003, loc=(-0.6, -0.42, 0.18), parent=ssd)
    hdd = box(1.8, 1.8, 0.26, steel, bevel=0.05, loc=(-1.75, -0.95, 0.13), rot=(0, 0, R(16)))
    cyl(0.76, 0.04, chrome, loc=(-0.05, 0.05, 0.15), parent=hdd)
    cyl(0.2, 0.08, gold, loc=(-0.05, 0.05, 0.19), parent=hdd)
    box(0.85, 0.1, 0.05, mat("#EEF1F5", rough=0.3), bevel=0.02, loc=(0.35, -0.42, 0.2), rot=(0, 0, R(150)), parent=hdd)
    cyl(0.12, 0.1, black, seg=24, loc=(0.7, -0.62, 0.19), parent=hdd)
    chip("RAM", (2.7, 0.5, 2.6), 14, "hardware")
    return floor


def scene_hardware_04(draft):
    """ประกอบเครื่อง & ลงวินโดวส์ — เคสฝาข้างกระจกเห็นชิ้นส่วนเรืองแสง + แฟลชไดรฟ์ USB Boot + ไขควง"""
    zb, zm, zk = ZONE["hardware"]
    floor = stage("hardware", az=20, dist=15.8, target=(0.1, 0, 1.3), draft=draft)
    steel, chrome = mat("#2B3442", rough=0.38, metal=0.9), mat("#D6DEE8", rough=0.2, metal=1.0)
    black, glow = mat("#07090D", rough=0.15), mat(zb, rough=0.3, emit=2.2)
    case = box(3.2, 1.55, 3.3, steel, bevel=0.08, loc=(-0.7, 0.55, 1.75), rot=(0, 0, R(-12)))
    for sx in (1.25, -1.25):
        for sy in (0.5, -0.5):
            box(0.4, 0.3, 0.12, black, bevel=0.03, loc=(sx, sy, -1.69), parent=case)
    box(2.85, 0.03, 2.95, black, bevel=0, loc=(0.05, -0.775, 0), parent=case)
    y = -0.8
    box(1.95, 0.03, 2.05, mat("#3A1226", rough=0.4), bevel=0.02, loc=(0.4, y, 0.35), parent=case)
    cyl(0.4, 0.2, mat("#141922", rough=0.3, metal=0.8), loc=(0.4, y - 0.1, 0.8), rot=(R(90), 0, 0), parent=case)
    torus(0.44, 0.055, glow, loc=(0.4, y - 0.2, 0.8), rot=(R(90), 0, 0), parent=case)
    for i in range(2):
        box(0.09, 0.07, 0.9, mat(GOLD, rough=0.3, emit=0.9), bevel=0.01, loc=(1.05 + 0.16 * i, y - 0.03, 0.8), parent=case)
    box(1.85, 0.24, 0.42, mat("#1B2230", rough=0.3, metal=0.8), bevel=0.04, loc=(0.25, y - 0.12, -0.12), parent=case)
    box(1.85, 0.03, 0.05, glow, bevel=0, loc=(0.25, y - 0.25, -0.26), parent=case)
    box(2.85, 0.08, 0.62, mat("#1B2230", rough=0.3, metal=0.8), bevel=0.02, loc=(0.05, y, -1.16), parent=case)
    box(0.9, 0.03, 0.06, glow, bevel=0, loc=(-0.6, y - 0.05, -1.16), parent=case)
    for z in (0.85, -0.1):
        torus(0.36, 0.05, glow, loc=(-1.0, y - 0.03, z), rot=(R(90), 0, 0), parent=case)
        cyl(0.12, 0.05, mat("#141922", rough=0.3, metal=0.8), loc=(-1.0, y - 0.03, z), rot=(R(90), 0, 0), parent=case)
    cyl(0.11, 0.05, mat(GOLD, rough=0.3, emit=0.8), loc=(-1.2, -0.45, 1.66), parent=case)
    usb = box(1.25, 0.52, 0.2, mat("#F8FAFC", rough=0.3), bevel=0.07, loc=(2.1, -0.95, 0.1), rot=(0, 0, R(28)))
    box(0.48, 0.4, 0.13, chrome, bevel=0.01, loc=(0.85, 0, 0), parent=usb)
    box(0.6, 0.3, 0.02, mat(zb, rough=0.35, emit=0.4), bevel=0, loc=(-0.12, 0, 0.105), parent=usb)
    sd = empty(loc=(-0.6, -1.25, 0.15), rot=(0, R(90), R(-12)))
    cyl(0.15, 0.95, mat(zb, rough=0.28), seg=8, parent=sd)
    cyl(0.045, 1.25, chrome, seg=24, loc=(0, 0, 1.1), parent=sd)
    box(0.13, 0.03, 0.16, chrome, bevel=0, loc=(0, 0, 1.78), parent=sd)
    chip("BIOS", (2.85, 0.5, 2.75), 14, "hardware")
    chip("USB BOOT", (2.6, -0.1, 1.05), 18, "hardware", w=2.1)
    return floor


SCENES = {
    "coding_01j": scene_coding_01j,
    "coding_01k": scene_coding_01k,
    "coding_01l": scene_coding_01l,
    "coding_01r": scene_coding_01r,
    "coding_01x": scene_coding_01x,
    "coding_01e": scene_coding_01e,
    "coding_01f": scene_coding_01f,
    "coding_01g": scene_coding_01g,
    "coding_01h": scene_coding_01h,
    "coding_01": scene_coding_01,
    "coding_01b": scene_coding_01b,
    "coding_01c": scene_coding_01c,
    "coding_01d": scene_coding_01d,
    "office_01": scene_office_01,
    "design_01": scene_design_01,
    "hardware_03": scene_hardware_03,
    "coding_02": scene_coding_02,
    "coding_03": scene_coding_03,
    "coding_04": scene_coding_04,
    "office_02": scene_office_02,
    "office_03": scene_office_03,
    "office_04": scene_office_04,
    "design_02": scene_design_02,
    "design_03": scene_design_03,
    "design_04": scene_design_04,
    "hardware_01": scene_hardware_01,
    "hardware_02": scene_hardware_02,
    "hardware_04": scene_hardware_04,
}


def in_blender():
    args = sys.argv[sys.argv.index("--") + 1:]
    global TALL, STYLE, BASE, PCT
    out, draft, TALL, STYLE, ids = args[0], args[1] == "draft", args[2] == "tall", args[3], args[4:]
    BASE = "toon" if STYLE in ("pixel", "riso") else STYLE
    PCT = 0.5 if draft else 1.0
    for cid in ids:
        floor = SCENES[cid](draft)
        sc = bpy.context.scene
        if STYLE != "glossy":
            sc.render.filepath = os.path.join(out, f"{cid}_{STYLE}.png")
            bpy.ops.render.render(write_still=True)
            continue
        passes = ((False, f"{cid}_tall.png"),) if TALL else ((False, f"{cid}_full.png"), (True, f"{cid}_hero.png"))
        for transparent, name in passes:
            for o in floor:
                o.hide_render = transparent
            sc.render.film_transparent = transparent
            sc.render.filepath = os.path.join(out, name)
            bpy.ops.render.render(write_still=True)


# ───────────────────────── ส่วนที่รันด้วย py ─────────────────────────
def find_blender():
    roots = [pathlib.Path(os.environ.get(v, "")) / "Blender Foundation" for v in ("ProgramFiles", "ProgramW6432")]
    exes = sorted({p for r in roots if r.is_dir() for p in r.glob("Blender*/blender.exe")}, reverse=True)
    return exes[0] if exes else shutil.which("blender")


def polish(src, dst):
    """แสงฟุ้งรอบจุดสว่าง (แทน bloom) แล้วเซฟ JPEG"""
    from PIL import Image, ImageChops, ImageFilter
    im = Image.open(src).convert("RGB")
    bright = im.point(lambda v: 0 if v < 205 else int((v - 205) * 5))
    glow = bright.filter(ImageFilter.GaussianBlur(im.width / 90)).point(lambda v: int(v * 0.4))
    ImageChops.screen(im, glow).save(dst, quality=92, subsampling=0)


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def bloom(im, cut=205, gain=5.0, amount=0.4, radius=90):
    from PIL import ImageChops, ImageFilter
    bright = im.point(lambda v: 0 if v < cut else min(255, int((v - cut) * gain)))
    glow = bright.filter(ImageFilter.GaussianBlur(im.width / radius)).point(lambda v: int(v * amount))
    return ImageChops.screen(im, glow)


def restyle(style, src, zone):
    """แต่งภาพเรนเดอร์ของสไตล์ทางเลือก -> PIL RGB"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    zb, zm, zk = ZONE[zone]
    im = Image.open(src)
    w, h = im.size
    if style in ("toon", "clay"):
        return im.convert("RGB")
    if style == "holo":         # แสงฟุ้งแรง + เส้นสแกนแนวนอน
        out = bloom(bloom(im.convert("RGB"), 120, 2.2, 0.55, 60), 60, 1.6, 0.35, 16)
        a = np.asarray(out).astype(np.float32)
        a[(np.arange(h) % max(2, h // 160)) == 0] *= 0.72
        return Image.fromarray(a.clip(0, 255).astype(np.uint8))
    if style == "pixel":        # ย่อเหลือกว้าง 165 พิกเซล ลดสีเหลือ 32 สี แล้วขยายแบบไม่เกลี่ย
        small = im.convert("RGB").resize((165, round(165 * h / w)), Image.BOX)
        small = ImageEnhance.Color(ImageEnhance.Brightness(small).enhance(1.12)).enhance(1.15)
        small = small.quantize(32, method=Image.FASTOCTREE, dither=Image.NONE).convert("RGB")
        return small.resize((w, h), Image.NEAREST)
    if style == "blueprint":    # กระดาษพิมพ์เขียวสีโซน + ตาราง แล้ววางภาพเส้น (พื้นโปร่ง) ทับ
        line = rgb(mix(zb, "#FFFFFF", 0.7))
        yy, xx = np.mgrid[0:h, 0:w]
        r2 = ((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2
        base = np.array(rgb(mix(zm, zk, 0.45)), np.float32)[None, None] * (1.08 - 0.3 * r2[..., None]).clip(0, 1.1)
        bg = Image.fromarray(base.clip(0, 255).astype(np.uint8)).convert("RGBA")
        grid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(grid)
        step = w / 40
        for i in range(1, 40):
            major = i % 5 == 0
            x = round(i * step)
            dr.line([(x, 0), (x, h)], fill=line + ((58 if major else 22),), width=max(1, round(w / 660)) if major else 1)
        for j in range(1, int(h / step) + 1):
            major = j % 5 == 0
            y = round(j * step)
            dr.line([(0, y), (w, y)], fill=line + ((58 if major else 22),), width=max(1, round(w / 660)) if major else 1)
        m = round(w / 44)       # กรอบเส้นคู่ + ขีดมุมแบบแบบแปลน
        dr.rectangle([m, m, w - m, h - m], outline=line + (150,), width=max(1, round(w / 500)))
        return Image.alpha_composite(Image.alpha_composite(bg, grid), im.convert("RGBA")).convert("RGB")
    if style == "iso":          # พื้นไล่สีโซนอ่อน + เงาใต้แท่น
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.sqrt(((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h * 0.48) / (h * 0.75)) ** 2).clip(0, 1)[..., None]
        c0, c1 = np.array(rgb(mix(zb, "#FFFFFF", 0.72)), np.float32), np.array(rgb(mix(zb, zm, 0.45)), np.float32)
        bg = Image.fromarray((c0 + (c1 - c0) * r ** 1.6).astype(np.uint8)).convert("RGBA")
        im = im.convert("RGBA")
        alpha = im.getchannel("A")
        sh = Image.new("RGBA", (w, h), rgb(mix(zk, zm, 0.3)) + (0,))
        sh.putalpha(alpha.filter(ImageFilter.GaussianBlur(w / 55)).point(lambda v: int(v * 0.5)))
        off = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        off.paste(sh, (0, round(h * 0.055)))
        return Image.alpha_composite(Image.alpha_composite(bg, off), im).convert("RGB")
    # riso: พิมพ์ 2 สี (หมึกสีโซน + หมึกสีรอง) เม็ดสกรีนบนกระดาษครีม — จากภาพ toon พื้นสว่าง
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-3)
    dark = 1 - (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])
    warm = ((a[..., 0] - a[..., 2]) * 1.6).clip(0, 1) * sat if zone != "design" else ((a[..., 2] - a[..., 0]) * 1.8 + 0.1).clip(0, 1) * sat
    if zone in ("design", "hardware"):          # โซนสีอุ่น: ใช้ความอิ่มสีที่ไม่ใช่สีโซนแทน
        warm = ((a[..., 1] + a[..., 2]) / 2 - a[..., 0] * 0.55).clip(0, 1) * 1.5 * sat
    cov2 = warm.clip(0, 1)
    cov1 = ((dark - 0.16) * 1.45 + (sat - 0.3).clip(0, 1) * 2.5).clip(0, 1) * (1 - 0.75 * cov2)     # สีสด = หมึกหนาขึ้น
    cell = w / 200

    def screen(cov, deg, dx=0.0):
        t = math.radians(deg)
        u = ((xx + dx) * math.cos(t) + yy * math.sin(t)) / cell
        v = (-(xx + dx) * math.sin(t) + yy * math.cos(t)) / cell
        thr = (np.cos(2 * math.pi * u) + np.cos(2 * math.pi * v)) / 4 + 0.5
        return ((cov - thr) * cell * 0.9 + 0.5).clip(0, 1)      # ขอบเม็ดสกรีนนุ่ม ~1 พิกเซล

    k1 = np.maximum(screen(cov1, 45), (cov1 > 0.86).astype(np.float32))
    k2 = screen(cov2, 15, dx=w / 400)
    rng = np.random.default_rng(7)
    paper = np.array(rgb("#F3E9D2"), np.float32) / 255 + rng.normal(0, 0.012, (h, w, 1)).astype(np.float32)
    i1, i2 = (np.array(rgb(c), np.float32) / 255 for c in (mix(zm, zk, 0.4), RISO_INK[zone]))
    out = paper * (1 - k1[..., None] * 0.94 * (1 - i1)) * (1 - k2[..., None] * 0.9 * (1 - i2))
    return Image.fromarray((out.clip(0, 1) * 255).astype(np.uint8))


def host():
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    draft, tall = "--draft" in args, "--tall" in args
    style = None
    if "--style" in args:
        i = args.index("--style")
        style = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
        if style != "all" and style not in STYLES:
            sys.exit(f"ไม่มีสไตล์ {style} — มี: all, {', '.join(STYLES)}")
    ids = [a for a in args if not a.startswith("--")] or list(SCENES)
    bad = [i for i in ids if i not in SCENES]
    if bad:
        sys.exit(f"ไม่มีฉากของ {', '.join(bad)} — มี: {', '.join(SCENES)}")
    exe = find_blender()
    if not exe:
        sys.exit("ไม่พบ Blender — ติดตั้งด้วย: winget install BlenderFoundation.Blender")
    out = pathlib.Path(__file__).resolve().parent.parent / "print" / "cards_tcg" / "img"
    out.mkdir(parents=True, exist_ok=True)
    # สคริปต์ + ผลเรนเดอร์อยู่ใน temp (พาธ ASCII) กันปัญหาพาธภาษาไทย
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        script = pathlib.Path(tmp) / "card_art.py"
        shutil.copy(__file__, script)

        def blender(st):
            subprocess.run([str(exe), "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(script),
                            "--", tmp, "draft" if draft else "final",
                            "tall" if tall else "wide", st, *ids], check=True,
                           stdout=None if "--verbose" in args else subprocess.DEVNULL)

        if style:               # สไตล์ทางเลือก
            want = list(STYLES) if style == "all" else [style]
            (out / "styles").mkdir(exist_ok=True)
            for st in want:
                blender(st)
            for st in want:
                for cid in ids:
                    src = pathlib.Path(tmp) / f"{cid}_{st}.png"
                    restyle(st, src, cid.split("_")[0]).save(out / "styles" / f"{st}_{cid}.jpg", quality=92, subsampling=0)
                    print(f"[OK] styles/{st}_{cid}.jpg")
            return
        blender("glossy")
        from PIL import Image
        for cid in ids:
            if tall:
                polish(pathlib.Path(tmp) / f"{cid}_tall.png", out / f"art_{cid}_tall.jpg")
                print(f"[OK] art_{cid}_tall.jpg")
                continue
            polish(pathlib.Path(tmp) / f"{cid}_full.png", out / f"art_{cid}.jpg")
            hero = Image.open(pathlib.Path(tmp) / f"{cid}_hero.png")
            hero.save(out / f"art_{cid}_hero.png", optimize=True)
            print(f"[OK] art_{cid}.jpg + art_{cid}_hero.png {hero.width}x{hero.height}")


if __name__ == "__main__":
    in_blender() if bpy else host()
