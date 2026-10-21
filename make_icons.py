# -*- coding: utf-8 -*-
"""生成两个网页图标（PNG 180x180，内联为 data URI），并给 4 个 HTML 打补丁：
   1) 顶部互跳导航按钮  2) favicon / apple-touch-icon
"""
import zlib, struct, base64, re, math, os

SIZE = 180          # 输出尺寸
SS = 3              # 超采样倍数（抗锯齿）
W = SIZE * SS
C1 = (0x3a, 0x8d, 0xde)   # 渐变起：蓝
C2 = (0x34, 0xb3, 0xa0)   # 渐变止：绿
WHITE = (255, 255, 255)


def lerp(a, b, t):
    return a + (b - a) * t


def grad(x, y):
    """模拟 CSS linear-gradient(135deg)：左上 -> 右下"""
    t = (x + y) / (2.0 * (W - 1))
    t = max(0.0, min(1.0, t))
    return tuple(int(round(lerp(C1[i], C2[i], t))) for i in range(3))


def new_canvas():
    return bytearray(W * W * 3)


def put(buf, x, y, rgb):
    if 0 <= x < W and 0 <= y < W:
        i = (y * W + x) * 3
        buf[i] = rgb[0]
        buf[i + 1] = rgb[1]
        buf[i + 2] = rgb[2]


# ---------- 形状判定 ----------
def in_round_rect(x, y, x0, y0, x1, y1, r):
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_circle(x, y, cx, cy, r):
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_rot_rect(x, y, cx, cy, w, h, ang):
    ca, sa = math.cos(-ang), math.sin(-ang)
    dx, dy = x - cx, y - cy
    lx = dx * ca - dy * sa
    ly = dx * sa + dy * ca
    return abs(lx) <= w / 2.0 and abs(ly) <= h / 2.0


def fill(buf, pred, color_fn, bbox):
    x0, y0, x1, y1 = bbox
    for y in range(int(x0), int(y0) + 1) if False else range(max(0, int(y0)), min(W, int(y1) + 1)):
        for x in range(max(0, int(x0)), min(W, int(x1) + 1)):
            if pred(x, y):
                put(buf, x, y, color_fn(x, y))


def segment(buf, p1, p2, width, color_fn):
    """画一条有宽度的线段（旋转矩形）"""
    (x1, y1), (x2, y2) = p1, p2
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    L = math.hypot(x2 - x1, y2 - y1)
    ang = math.atan2(y2 - y1, x2 - x1)
    R = L / 2.0 + width
    bbox = (cx - R, cy - R, cx + R, cy + R)
    fill(buf, lambda x, y: in_rot_rect(x, y, cx, cy, L, width, ang), color_fn, bbox)


def downsample(buf):
    """SS x SS 平均降采样到 SIZE"""
    out = bytearray(SIZE * SIZE * 3)
    n = SS * SS
    for y in range(SIZE):
        for x in range(SIZE):
            r = g = b = 0
            for dy in range(SS):
                base = ((y * SS + dy) * W + x * SS) * 3
                for dx in range(SS):
                    i = base + dx * 3
                    r += buf[i]
                    g += buf[i + 1]
                    b += buf[i + 2]
            o = (y * SIZE + x) * 3
            out[o] = r // n
            out[o + 1] = g // n
            out[o + 2] = b // n
    return out


def write_png(path, px):
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)
        raw += px[y * SIZE * 3:(y + 1) * SIZE * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', SIZE, SIZE, 8, 2, 0, 0, 0)
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', comp) + chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(data)
    return data


def b64(png_bytes):
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode('ascii')


# ---------- 图标 1：日历（学习计划 / 打卡） ----------
def icon_plan():
    buf = new_canvas()
    fill(buf, lambda x, y: True, grad, (0, 0, W - 1, W - 1))          # 渐变底
    x0, y0, x1, y1 = 0.215 * W, 0.265 * W, 0.785 * W, 0.815 * W
    r = 0.065 * W
    # 先画两个白色挂环（下半截会被卡片压住）
    for cx in (0.375, 0.625):
        hx0, hx1 = (cx - 0.031) * W, (cx + 0.031) * W
        hy0, hy1 = 0.175 * W, 0.325 * W
        fill(buf, lambda x, y, a=hx0, b=hx1, c=hy0, d=hy1: in_round_rect(x, y, a, c, b, d, 0.030 * W),
             lambda x, y: WHITE, (hx0, hy0, hx1, hy1))
    # 白色卡片
    fill(buf, lambda x, y: in_round_rect(x, y, x0, y0, x1, y1, r), lambda x, y: WHITE,
         (x0, y0, x1, y1))
    # 日历头：卡片内一条深色横条（跟随圆角裁切）
    hy0, hy1 = 0.345 * W, 0.435 * W
    dark = lambda x, y: tuple(int(c * 0.80) for c in grad(x, y))
    fill(buf, lambda x, y: in_round_rect(x, y, x0, y0, x1, y1, r) and hy0 <= y <= hy1,
         dark, (x0, hy0, x1, hy1))
    # 日期点 3 列 x 2 行
    for cy in (0.550, 0.690):
        for cx in (0.350, 0.50, 0.650):
            rr = 0.032 * W
            fill(buf, lambda x, y, a=cx * W, b=cy * W, c=rr: in_circle(x, y, a, b, c), dark,
                 (cx * W - rr, cy * W - rr, cx * W + rr, cy * W + rr))
    return downsample(buf)


# ---------- 图标 2：对勾（练习 / 判分） ----------
def icon_drill():
    buf = new_canvas()
    fill(buf, lambda x, y: True, grad, (0, 0, W - 1, W - 1))
    x0, y0, x1, y1 = 0.22 * W, 0.235 * W, 0.78 * W, 0.80 * W
    r = 0.075 * W
    fill(buf, lambda x, y: in_round_rect(x, y, x0, y0, x1, y1, r), lambda x, y: WHITE,
         (x0, y0, x1, y1))
    w = 0.085 * W
    segment(buf, (0.355 * W, 0.560 * W), (0.455 * W, 0.668 * W), w, grad)
    segment(buf, (0.455 * W, 0.668 * W), (0.690 * W, 0.418 * W), w, grad)
    return downsample(buf)


os.makedirs("deploy/html", exist_ok=True)
p_png = write_png("deploy/html/icon-plan.png", icon_plan())
d_png = write_png("deploy/html/icon-drill.png", icon_drill())
P_URI = b64(p_png)
D_URI = b64(d_png)
print("icon-plan.png  %d bytes -> dataURI %d chars" % (len(p_png), len(P_URI)))
print("icon-drill.png %d bytes -> dataURI %d chars" % (len(d_png), len(D_URI)))

# ---------------------------------------------------------------- 打补丁
CSS_ADD = """
  .navlink{display:flex;justify-content:flex-end;margin:0 0 10px}
  .nl{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:800;
    text-decoration:none;color:#1565c0;background:rgba(255,255,255,.94);
    border:1px solid rgba(255,255,255,.9);border-radius:999px;padding:5px 13px;
    box-shadow:0 1px 3px rgba(0,0,0,.12)}
  .nl:hover{background:#fff;color:#0d47a1}
  @media print{ .navlink{display:none !important} }"""

NAV_JS = """
<script>
/* ===== 页面互跳导航：资料库环境用 space 链接，自部署(同目录)用相对路径 ===== */
(function(){
  var SPACE={
    plan:"https://www.workbuddy.cn/space/d/caxEmKJABbraYJf8XCU0LL",
    drill:"https://www.workbuddy.cn/space/d/lvcPwY2W1LM0fUxuWP2IQs"
  };
  var inSpace=/workbuddy\\.cn|codebuddy\\.work/i.test(location.hostname||"");
  var map={
    navToDrill:["drill","语文数学练习生成器.html"],
    navToPlan:["plan","学习周计划与每日打卡.html"]
  };
  Object.keys(map).forEach(function(id){
    var el=document.getElementById(id); if(!el)return;
    var k=map[id][0], f=map[id][1];
    if(inSpace&&SPACE[k]){ el.href=SPACE[k]; el.target="_blank"; el.rel="noopener"; }
    else{ el.href=f; }
  });
})();
</script>
"""

NAV_HTML = {
    "plan": '<div class="navlink"><a class="nl" id="navToDrill">🔢 语文 · 数学练习生成器 →</a></div>',
    "drill": '<div class="navlink"><a class="nl" id="navToPlan">📅 学习计划与每日打卡 →</a></div>',
}


def patch(path, kind, uri, title):
    with open(path, encoding="utf-8", newline="") as fh:
        s = fh.read()
    nl = "\r\n" if "\r\n" in s else "\n"
    before = len(s.encode("utf-8"))
    pnid0 = s.count("data-page-node-id")

    # 1) 图标（幂等：已存在则替换为新 URI，否则插到 title 之后）
    icon_links = (
        '<link rel="icon" type="image/png" sizes="180x180" href="%s">' % uri + nl +
        '<link rel="apple-touch-icon" href="%s">' % uri + nl +
        '<link rel="shortcut icon" href="%s">' % uri
    )
    pat = re.compile(r'<link rel="icon" type="image/png"[^>]*>\s*'
                     r'<link rel="apple-touch-icon"[^>]*>\s*'
                     r'<link rel="shortcut icon"[^>]*>')
    if pat.search(s):
        s = pat.sub(lambda _m: icon_links, s, count=1)
    else:
        m = re.search(r'<title[^>]*>.*?</title>', s, re.S)
        assert m, "未找到 title: " + path
        s = s[:m.end()] + nl + icon_links + s[m.end():]

    # 2) CSS（幂等）
    if '.navlink{' not in s:
        m = re.search(r'\r?\n([ \t]*)\.sub\{[^}]*\}\r?\n', s)
        assert m, "未找到 .sub 样式: " + path
        s = s[:m.end()] + CSS_ADD + nl + s[m.end():]

    # 3) 导航按钮（幂等）
    if 'class="navlink"' not in s:
        m2 = re.search(r'\r?\n([ \t]*)(<h1[^>]*>)', s)
        assert m2, "未找到 h1: " + path
        s = s[:m2.start()] + nl + m2.group(1) + NAV_HTML[kind] + s[m2.start():]

    # 4) 导航脚本（幂等）
    if 'navToDrill' not in s:
        m3 = re.search(r'\r?\n</body>', s)
        assert m3, "未找到 </body>: " + path
        s = s[:m3.start()] + nl + NAV_JS + s[m3.start():]

    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)
    after = len(s.encode("utf-8"))
    print("%-42s %6d -> %6d (+%d) | pnid %d->%d | icon:%s nav:%s js:%s" % (
        title, before, after, after - before, pnid0, s.count("data-page-node-id"),
        'apple-touch-icon' in s, 'class="navlink"' in s, 'navToDrill' in s or 'navToPlan' in s))


patch("学习周计划与每日打卡.html", "plan", P_URI, "本地·计划页")
patch("语文数学练习生成器.html", "drill", D_URI, "本地·生成器页")
patch("page_tmp8/plan.html", "plan", P_URI, "云端基线·计划页")
patch("page_tmp8/drill.html", "drill", D_URI, "云端基线·生成器页")
