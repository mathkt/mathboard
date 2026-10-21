"""도형그리기 - 입체도형 (모양, 투영, 숨은 선, 자르기, 쌓기, 겉넓이·부피)

좌표: x 오른쪽, y 위, z 뒤쪽(화면 안쪽). 단위 cm. 도형 중심이 원점.
입체는 면(다각형)으로 표현하고, 곡면은 잘게 나눕니다.
"""
import math

KINDS = [
    ("cube", "정육면체"),
    ("cuboid", "직육면체"),
    ("prism", "각기둥"),
    ("pyramid", "각뿔"),
    ("frustum", "각뿔대"),
    ("cylinder", "원기둥"),
    ("cone", "원뿔"),
    ("cone_frustum", "원뿔대"),
    ("sphere", "구"),
    ("stack", "쌓기(회전체)"),
]
KIND_NAMES = dict(KINDS)
CURVED = {"cylinder", "cone", "cone_frustum", "sphere"}

# (키, 이름, 기본값, 최소, 최대, 정수?)
PARAMS = {
    "cube": [("a", "한 모서리", 3.0, 0.5, 30, False)],
    "cuboid": [("w", "가로", 4.0, 0.5, 30, False), ("d", "세로", 3.0, 0.5, 30, False),
               ("h", "높이", 3.0, 0.5, 30, False)],
    "prism": [("n", "밑면 변의 수", 3, 3, 12, True), ("s", "밑면 한 변", 3.0, 0.5, 30, False),
              ("h", "높이", 4.0, 0.5, 30, False)],
    "pyramid": [("n", "밑면 변의 수", 4, 3, 12, True), ("s", "밑면 한 변", 4.0, 0.5, 30, False),
                ("h", "높이", 4.0, 0.5, 30, False)],
    "frustum": [("n", "밑면 변의 수", 4, 3, 12, True), ("s1", "아랫면 한 변", 4.0, 0.5, 30, False),
                ("s2", "윗면 한 변", 2.0, 0.2, 30, False), ("h", "높이", 3.0, 0.5, 30, False)],
    "cylinder": [("r", "반지름", 2.0, 0.3, 20, False), ("h", "높이", 4.0, 0.5, 30, False)],
    "cone": [("r", "반지름", 2.0, 0.3, 20, False), ("h", "높이", 4.0, 0.5, 30, False)],
    "cone_frustum": [("r1", "아랫면 반지름", 2.5, 0.3, 20, False), ("r2", "윗면 반지름", 1.2, 0.1, 20, False),
                     ("h", "높이", 3.0, 0.5, 30, False)],
    "sphere": [("r", "반지름", 2.5, 0.3, 20, False)],
    "stack": [],
}

# 쌓기: 층 하나 = {"shape": "line"|"dome"|"bowl", "r1": 아래 반지름, "r2": 위 반지름, "h": 높이}
#   line: 원기둥(r1=r2), 원뿔(r2=0), 거꾸로 원뿔(r1=0), 원뿔대
#   dome: 위로 볼록한 반구(반지름 r1), bowl: 아래로 볼록한 반구(반지름 r2)
LAYER_SHAPES = [("line", "원기둥·원뿔·원뿔대"), ("dome", "반구 (위로 볼록)"), ("bowl", "반구 (아래로 볼록)")]
STACK_PRESETS = {
    "연필 (원기둥+원뿔)": [{"shape": "line", "r1": 1.5, "r2": 1.5, "h": 4.0}, {"shape": "line", "r1": 1.5, "r2": 0.0, "h": 2.5}],
    "팽이 (원뿔+원뿔)": [{"shape": "line", "r1": 0.0, "r2": 2.0, "h": 2.5}, {"shape": "line", "r1": 2.0, "r2": 0.0, "h": 2.5}],
    "캡슐 (반구+원기둥+반구)": [{"shape": "bowl", "r1": 0.0, "r2": 1.5, "h": 1.5}, {"shape": "line", "r1": 1.5, "r2": 1.5, "h": 3.0},
                          {"shape": "dome", "r1": 1.5, "r2": 0.0, "h": 1.5}],
    "아이스크림 (원뿔+반구)": [{"shape": "line", "r1": 0.0, "r2": 1.8, "h": 4.0}, {"shape": "dome", "r1": 1.8, "r2": 0.0, "h": 1.8}],
    "계단 (원기둥+작은 원기둥)": [{"shape": "line", "r1": 2.5, "r2": 2.5, "h": 2.0}, {"shape": "line", "r1": 1.2, "r2": 1.2, "h": 2.5}],
}

SEG = 72          # 곡면을 나누는 개수
OBL = 0.5 * math.cos(math.radians(45))   # 겨냥도: 깊이 방향 45°, 길이 1/2


def default_params(kind):
    if kind == "stack":
        return {"layers": [dict(l) for l in STACK_PRESETS["연필 (원기둥+원뿔)"]], "n": 0}
    return {k: v for k, _n, v, _a, _b, _i in PARAMS[kind]}


def is_curved(o):
    return o["kind"] in CURVED or (o["kind"] == "stack" and int(o["params"].get("n", 0)) == 0)


def letters(n, start=0):
    out = []
    for k in range(start, start + n):
        ch = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[k % 26]
        out.append(ch if k < 26 else f"{ch}{k // 26}")
    return out


# ---------------------------------------------------------------- 모양 만들기
class Mesh:
    def __init__(self):
        self.v = []          # [(x, y, z)]
        self.faces = []      # [[i, ...]] 바깥에서 볼 때 반시계
        self.groups = []     # 면마다 색칠 단위 이름 (곡면은 '옆면' 하나로)
        self.smooth = set()  # 곡면 안쪽의 이음선 (윤곽일 때만 그림)
        self.named = []      # 이름 붙일 점의 번호
        self.names = []      # 기본 이름
        self.centers = []    # 원의 중심 (named 안의 순서 번호)
        self.sphere_r = None
        self.convex = True

    def add(self, x, y, z):
        self.v.append((x, y, z))
        return len(self.v) - 1

    def face(self, f, group):
        self.faces.append(list(f))
        self.groups.append(group)


def _ring(m, n, R, y, start_front=True):
    """정n각형/원 둘레의 점 (각기둥은 앞쪽 변이 가로로 놓이게)"""
    if R <= 1e-9:
        return [m.add(0.0, y, 0.0)]
    ids = []
    for k in range(n):
        t = math.radians(-90 - 180 / n + k * 360 / n) if start_front else 2 * math.pi * k / n
        ids.append(m.add(R * math.cos(t), y, R * math.sin(t)))
    return ids


def _band(m, bot, top, group, smooth_v=False):
    """두 고리(또는 점) 사이의 옆면"""
    if len(bot) == 1 and len(top) == 1:
        return
    if len(bot) == 1:
        a = bot[0]
        for k in range(len(top)):
            m.face([top[(k + 1) % len(top)], top[k], a], group)
            if smooth_v:
                m.smooth.add(frozenset((a, top[k])))
        return
    if len(top) == 1:
        a = top[0]
        for k in range(len(bot)):
            m.face([bot[k], bot[(k + 1) % len(bot)], a], group)
            if smooth_v:
                m.smooth.add(frozenset((bot[k], a)))
        return
    n = len(bot)
    for k in range(n):
        k2 = (k + 1) % n
        m.face([bot[k], bot[k2], top[k2], top[k]], group)
        if smooth_v:
            m.smooth.add(frozenset((bot[k2], top[k2])))


def build(kind, p, sphere_mesh=False):
    m = Mesh()
    if kind in ("cube", "cuboid"):
        if kind == "cube":
            w = d = h = float(p["a"])
        else:
            w, d, h = float(p["w"]), float(p["d"]), float(p["h"])
        bot = [m.add(-w / 2, -h / 2, -d / 2), m.add(w / 2, -h / 2, -d / 2),
               m.add(w / 2, -h / 2, d / 2), m.add(-w / 2, -h / 2, d / 2)]
        top = [m.add(x, h / 2, z) for (x, _y, z) in (m.v[i] for i in bot)]
        m.face(list(reversed(bot)), "f0")
        m.face(list(top), "f1")
        for k in range(4):
            m.face([bot[k], bot[(k + 1) % 4], top[(k + 1) % 4], top[k]], f"f{k + 2}")
        m.named = bot + top
        m.names = letters(8)
    elif kind in ("prism", "frustum"):
        n = int(p["n"])
        h = float(p["h"])
        s1 = float(p["s"] if kind == "prism" else p["s1"])
        s2 = float(p["s"] if kind == "prism" else p["s2"])
        R1, R2 = s1 / (2 * math.sin(math.pi / n)), s2 / (2 * math.sin(math.pi / n))
        bot = _ring(m, n, R1, -h / 2)
        top = _ring(m, n, R2, h / 2)
        m.face(list(reversed(bot)), "f0")
        m.face(list(top), "f1")
        for k in range(n):
            m.face([bot[k], bot[(k + 1) % n], top[(k + 1) % n], top[k]], f"f{k + 2}")
        m.named = bot + top
        m.names = letters(2 * n)
    elif kind == "pyramid":
        n = int(p["n"])
        h, s = float(p["h"]), float(p["s"])
        R = s / (2 * math.sin(math.pi / n))
        bot = _ring(m, n, R, -h / 2)
        apex = m.add(0, h / 2, 0)
        m.face(list(reversed(bot)), "f0")
        for k in range(n):
            m.face([bot[k], bot[(k + 1) % n], apex], f"f{k + 1}")
        m.named = bot + [apex]
        m.names = letters(n + 1)
    elif kind in ("cylinder", "cone_frustum", "cone"):
        h = float(p["h"])
        if kind == "cylinder":
            r1 = r2 = float(p["r"])
        elif kind == "cone":
            r1, r2 = float(p["r"]), 0.0
        else:
            r1, r2 = float(p["r1"]), float(p["r2"])
        bot = _ring(m, SEG, r1, -h / 2, start_front=False)
        top = _ring(m, SEG, r2, h / 2, start_front=False)
        m.face(list(reversed(bot)), "아랫면")
        if len(top) > 1:
            m.face(list(top), "윗면")
        _band(m, bot, top, "옆면", smooth_v=True)
        c1, c2 = m.add(0, -h / 2, 0), m.add(0, h / 2, 0)
        if kind == "cone":
            m.named = [top[0], c1]
            m.names = ["A", "O"]
            m.centers = [1]
        else:
            m.named = [c1, c2]
            m.names = ["O", "O′"]
            m.centers = [0, 1]
    elif kind == "sphere":
        r = float(p["r"])
        m.sphere_r = r
        if sphere_mesh:
            NL = 36
            rings = [[m.add(0, -r, 0)]]
            for i in range(1, NL):
                t = -math.pi / 2 + math.pi * i / NL
                rings.append(_ring(m, SEG, r * math.cos(t), r * math.sin(t), start_front=False))
            rings.append([m.add(0, r, 0)])
            for i in range(NL):
                _band(m, rings[i], rings[i + 1], "구면", smooth_v=True)
                if 0 < i < NL - 1:
                    ring = rings[i + 1]
                    for k in range(len(ring)):
                        m.smooth.add(frozenset((ring[k], ring[(k + 1) % len(ring)])))
            for k in range(SEG):   # 맨 아래 첫 고리도 매끈하게
                ring = rings[1]
                m.smooth.add(frozenset((ring[k], ring[(k + 1) % SEG])))
        c = m.add(0, 0, 0)
        m.named = [c]
        m.names = ["O"]
        m.centers = [0]
    elif kind == "stack":
        build_stack(m, p)
    return m


def stack_profile(p):
    """[(y, 반지름, 이음매인지)] 아래부터, 높이 가운데가 0"""
    pts = []
    y = 0.0
    for L in p.get("layers", []):
        shape = L.get("shape", "line")
        if shape == "line":
            h = max(0.05, float(L.get("h", 1)))
            seg = [(y, float(L.get("r1", 1)), True), (y + h, float(L.get("r2", 1)), True)]
        else:
            r = max(0.05, float(L.get("r1", 1) if shape == "dome" else L.get("r2", 1)))
            h = r
            seg = []
            N = 12
            for i in range(N + 1):
                t = math.pi / 2 * i / N
                if shape == "dome":
                    seg.append((y + r * math.sin(t), r * math.cos(t), i in (0, N)))
                else:
                    seg.append((y + r - r * math.cos(t), r * math.sin(t), i in (0, N)))
        for q in seg:
            if pts and abs(pts[-1][0] - q[0]) < 1e-9 and abs(pts[-1][1] - q[1]) < 1e-9:
                continue
            pts.append(q)
        y += h
    return [(yy - y / 2, r, j) for yy, r, j in pts], y


def build_stack(m, p):
    prof, H = stack_profile(p)
    n = int(p.get("n", 0))
    curved = n == 0
    N = SEG if curved else n
    rings = [_ring(m, N, r, y, start_front=not curved) for y, r, _j in prof]
    if len(rings[0]) > 1:
        m.face(list(reversed(rings[0])), "아랫면")
    if len(rings[-1]) > 1:
        m.face(list(rings[-1]), "윗면")
    for i in range(len(rings) - 1):
        y0, r0, _ = prof[i]
        y1, r1, _ = prof[i + 1]
        flat = abs(y1 - y0) < 1e-9
        _band(m, rings[i], rings[i + 1], f"층{i}" if not curved else ("평면" if flat else "옆면"),
              smooth_v=curved)
        if curved and not prof[i + 1][2] and len(rings[i + 1]) > 1:
            ring = rings[i + 1]
            for k in range(len(ring)):
                m.smooth.add(frozenset((ring[k], ring[(k + 1) % len(ring)])))
    # 볼록한지 (오목하면 숨은 선을 정밀하게 따집니다)
    poly = [(0.0, prof[0][0])] + [(r, y) for y, r, _ in prof] + [(0.0, prof[-1][0])]
    sgn = 0
    for k in range(len(poly)):
        (x1, y1), (x2, y2), (x3, y3) = poly[k], poly[(k + 1) % len(poly)], poly[(k + 2) % len(poly)]
        c = (x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2)
        if abs(c) > 1e-9:
            s = 1 if c > 0 else -1
            if sgn and s != sgn:
                m.convex = False
            sgn = sgn or s
    c1, c2 = m.add(0, prof[0][0], 0), m.add(0, prof[-1][0], 0)
    m.named = [c1, c2]
    m.names = ["O", "O′"]
    m.centers = [0, 1]
    if not curved:
        named = [i for ring in rings for i in ring if len(ring) > 1 or True]
        m.named = named
        m.names = letters(len(named))
        m.centers = []


def newell(m, f):
    nx = ny = nz = 0.0
    for k in range(len(f)):
        x1, y1, z1 = m.v[f[k]]
        x2, y2, z2 = m.v[f[(k + 1) % len(f)]]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    # x 오른쪽·y 위·z 안쪽은 왼손 좌표계라 부호를 뒤집어 바깥 방향으로
    return -nx, -ny, -nz


def face_area(m, f):
    nx, ny, nz = newell(m, f)
    return math.sqrt(nx * nx + ny * ny + nz * nz) / 2


# ---------------------------------------------------------------- 자르기
def clip(m, n, d):
    """평면 n·x = d 로 자름 → (아래 조각, 위 조각, 단면 [(x,y,z)...] 순서대로, 단면이 지나는 면 목록)
    아래: n·x ≤ d,  위: n·x ≥ d"""
    dist = [n[0] * x + n[1] * y + n[2] * z - d for x, y, z in m.v]
    eps = 1e-7
    out = {}
    for side in (-1, 1):
        q = Mesh()
        q.convex = m.convex
        q.sphere_r = None
        vmap, emap = {}, {}

        def keep(i):
            if i not in vmap:
                vmap[i] = q.add(*m.v[i])
            return vmap[i]

        def cut(i, j):
            key = frozenset((i, j))
            if key not in emap:
                t = dist[i] / (dist[i] - dist[j])
                a, b = m.v[i], m.v[j]
                emap[key] = q.add(*(a[k] + (b[k] - a[k]) * t for k in range(3)))
            return emap[key]

        inside = (lambda s: s <= eps) if side < 0 else (lambda s: s >= -eps)
        sec_edges = []
        for fi, f in enumerate(m.faces):
            poly = []
            for k in range(len(f)):
                i, j = f[k], f[(k + 1) % len(f)]
                di, dj = dist[i], dist[j]
                if inside(di):
                    poly.append(keep(i))
                if (di < -eps and dj > eps) or (di > eps and dj < -eps):
                    poly.append(cut(i, j))
            clean = []
            for v in poly:
                if not clean or clean[-1] != v:
                    clean.append(v)
            if len(clean) > 1 and clean[0] == clean[-1]:
                clean.pop()
            if len(clean) >= 3:
                q.face(clean, m.groups[fi])
                # 매끈한 이음선 물려받기
                for k in range(len(f)):
                    i, j = f[k], f[(k + 1) % len(f)]
                    if frozenset((i, j)) in m.smooth:
                        a = vmap.get(i)
                        b = vmap.get(j)
                        c = emap.get(frozenset((i, j)))
                        for u, w in ((a, b), (a, c), (b, c)):
                            if u is not None and w is not None:
                                q.smooth.add(frozenset((u, w)))
        out[side] = (q, vmap, emap)
    # 단면 다각형
    pts = []
    for (q, vmap, emap) in [out[-1]]:
        for i, vi in vmap.items():
            if abs(dist[i]) <= eps:
                pts.append(q.v[vi])
        for vi in emap.values():
            pts.append(q.v[vi])
    sec = order_plane_points(pts, n)
    sec_faces = []
    for fi, f in enumerate(m.faces):
        ds = [dist[i] for i in f]
        if min(ds) < -eps and max(ds) > eps:
            sec_faces.append(fi)
    for side in (-1, 1):
        q = out[side][0]
        if len(sec) >= 3:
            ids = [q.add(*p_) for p_ in sec]
            # 아래 조각의 단면 = 법선 +n 쪽을 향함
            face = ids if side < 0 else list(reversed(ids))
            nn = newell_pts([q.v[i] for i in face])
            want = n if side < 0 else (-n[0], -n[1], -n[2])
            if nn[0] * want[0] + nn[1] * want[1] + nn[2] * want[2] < 0:
                face = list(reversed(face))
            q.face(face, "단면")
    return out[-1][0], out[1][0], sec, sec_faces


def newell_pts(P):
    nx = ny = nz = 0.0
    for k in range(len(P)):
        x1, y1, z1 = P[k]
        x2, y2, z2 = P[(k + 1) % len(P)]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return -nx, -ny, -nz


def plane_basis(n):
    a = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 0.0, 1.0)
    u = cross(n, a)
    L = math.sqrt(sum(c * c for c in u))
    u = tuple(c / L for c in u)
    v = cross(n, u)
    return u, v


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def order_plane_points(pts, n):
    """평면 위 점들을 볼록 껍질 순서로 (같은 점, 한 직선 위의 점은 빼고)"""
    if len(pts) < 3:
        return []
    u, v = plane_basis(n)
    pp = {}
    for p_ in pts:
        key = (round(sum(p_[k] * u[k] for k in range(3)), 6), round(sum(p_[k] * v[k] for k in range(3)), 6))
        pp[key] = p_
    h = hull(list(pp.keys()))
    out = [pp[k] for k in h]
    return out


def hull(points):
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def crs(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and crs(lower[-2], lower[-1], p) <= 1e-12:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and crs(upper[-2], upper[-1], p) <= 1e-12:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def cut_plane(o, mesh, attached=None):
    """o['cut'] 설정 → (n, d) 또는 None.  attached: 점 번호 → (x,y,z)"""
    c = o.get("cut")
    if not c:
        return None
    if c.get("mode") == "points":
        P = [attached.get(i) for i in c.get("pts", [])] if attached else []
        if len(P) < 3 or any(q is None for q in P):
            return None
        a, b, cc = P[:3]
        n = cross(tuple(b[k] - a[k] for k in range(3)), tuple(cc[k] - a[k] for k in range(3)))
        L = math.sqrt(sum(q * q for q in n))
        if L < 1e-9:
            return None
        n = tuple(q / L for q in n)
        if n[1] < -1e-9 or (abs(n[1]) < 1e-9 and (n[0] < 0 or (abs(n[0]) < 1e-9 and n[2] < 0))):
            n = tuple(-q for q in n)
        return n, sum(n[k] * a[k] for k in range(3))
    th, ph = math.radians(float(c.get("tilt", 0))), math.radians(float(c.get("turn", 0)))
    n = (math.sin(th) * math.cos(ph), math.cos(th), math.sin(th) * math.sin(ph))
    vals = [n[0] * x + n[1] * y + n[2] * z for x, y, z in mesh.v] or [0, 0]
    lo, hi = min(vals), max(vals)
    pos = max(-0.999, min(0.999, float(c.get("pos", 0))))
    return n, (lo + hi) / 2 + pos * (hi - lo) / 2


def section_name(sec, kind, curved):
    """단면 모양 이름"""
    n = len(sec)
    if n < 3:
        return ""
    if curved and n > 8:
        # 곡선: 중심에서의 거리가 일정하면 원, 아니면 타원(또는 곡선 도형)
        cx = [sum(p[k] for p in sec) / n for k in range(3)]
        ds = [math.dist(p, cx) for p in sec]
        straight = 0
        for k in range(n):
            a, b, c = sec[k - 1], sec[k], sec[(k + 1) % n]
            if math.dist(a, c) > 0 and abs(math.dist(a, b) + math.dist(b, c) - math.dist(a, c)) < 1e-6:
                straight += 1
        if max(ds) - min(ds) < 0.02 * max(ds):
            return "원"
        long_edge = max(math.dist(sec[k], sec[(k + 1) % n]) for k in range(n))
        if long_edge > 3 * (2 * math.pi * max(ds) / SEG) + 0.05:
            return "곡선과 선분으로 둘러싸인 도형"
        return "타원"
    L = [math.dist(sec[k], sec[(k + 1) % n]) for k in range(n)]

    def ang(k):
        a, b, c = sec[k - 1], sec[k], sec[(k + 1) % n]
        u = [a[i] - b[i] for i in range(3)]
        v = [c[i] - b[i] for i in range(3)]
        cu = sum(u[i] * v[i] for i in range(3)) / (math.sqrt(sum(x * x for x in u)) * math.sqrt(sum(x * x for x in v)))
        return math.degrees(math.acos(max(-1, min(1, cu))))
    A = [ang(k) for k in range(n)]
    eq = lambda a, b, t=1e-3: abs(a - b) < t * max(1, a, b)
    if n == 3:
        if eq(L[0], L[1]) and eq(L[1], L[2]):
            return "정삼각형"
        if any(abs(a - 90) < 0.05 for a in A):
            return "직각삼각형" + (" (직각이등변삼각형)" if eq(L[0], L[1]) or eq(L[1], L[2]) or eq(L[0], L[2]) else "")
        if eq(L[0], L[1]) or eq(L[1], L[2]) or eq(L[0], L[2]):
            return "이등변삼각형"
        return "삼각형"
    if n == 4:
        def par(i, j):
            a, b = sec[i], sec[(i + 1) % 4]
            c, d = sec[j], sec[(j + 1) % 4]
            u = [b[k] - a[k] for k in range(3)]
            v = [d[k] - c[k] for k in range(3)]
            cr = cross(u, v)
            return math.sqrt(sum(x * x for x in cr)) < 1e-4 * (L[i] * L[j] + 1e-9)
        p1, p2 = par(0, 2), par(1, 3)
        right = all(abs(a - 90) < 0.05 for a in A)
        alleq = all(eq(L[0], x) for x in L)
        if right and alleq:
            return "정사각형"
        if right:
            return "직사각형"
        if p1 and p2:
            return "마름모" if alleq else "평행사변형"
        if p1 or p2:
            if (p1 and eq(L[1], L[3])) or (p2 and eq(L[0], L[2])):
                return "등변사다리꼴"
            return "사다리꼴"
        return "사각형"
    names = {5: "오각형", 6: "육각형", 7: "칠각형", 8: "팔각형"}
    reg = all(eq(L[0], x) for x in L) and all(eq(A[0], a, 1e-3) for a in A)
    return ("정" if reg else "") + names.get(n, f"{n}각형")


# ---------------------------------------------------------------- 투영
def effective_view(o):
    """곡면 입체의 '겨냥도'는 살짝 위에서 본 모습으로 그립니다."""
    if o.get("view") == "oblique" and is_curved(o):
        return "rot", 0.0, 20.0
    return o.get("view", "rot"), float(o.get("yaw", -30)), float(o.get("pitch", 20))


class Projector:
    def __init__(self, o):
        self.view, yaw, pitch = effective_view(o)
        a, b = math.radians(yaw), math.radians(pitch)
        self.cy, self.sy, self.cp, self.sp = math.cos(a), math.sin(a), math.cos(b), math.sin(b)

    def rot(self, x, y, z):
        if self.view == "oblique":
            return x, y, z
        x1 = x * self.cy + z * self.sy
        z1 = -x * self.sy + z * self.cy
        y2 = y * self.cp + z1 * self.sp
        z2 = -y * self.sp + z1 * self.cp
        return x1, y2, z2

    def screen(self, x, y, z):
        """cm → 화면(오른쪽 x, 아래 y) cm"""
        if self.view == "oblique":
            return x + OBL * z, -(y + OBL * z)
        x1, y1, _ = self.rot(x, y, z)
        return x1, -y1

    def facing(self, n):
        """면의 바깥 법선 n 이 보는 사람 쪽이면 True"""
        if self.view == "oblique":
            v = (-OBL, -OBL, 1.0)
            nx, ny, nz = n
        else:
            v = (0.0, 0.0, 1.0)
            nx, ny, nz = self.rot(*n)
        return nx * v[0] + ny * v[1] + nz * v[2] < -1e-9

    def depth(self, x, y, z):
        if self.view == "oblique":
            return z - OBL * x - OBL * y
        return self.rot(x, y, z)[2]


def chains(segs):
    """[(i, j)] 를 이어진 꺾은선 [[i, j, k, ...]] 으로 (점선이 끊기지 않게)"""
    adj = {}
    for i, j in segs:
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
    used = set()
    out = []

    def walk(start):
        line = [start]
        cur = start
        while True:
            nxt = None
            for q in adj[cur]:
                e = frozenset((cur, q))
                if e not in used:
                    nxt = q
                    used.add(e)
                    break
            if nxt is None:
                break
            line.append(nxt)
            cur = nxt
            if len(adj[cur]) != 2:
                break
        return line

    for v in adj:
        if len(adj[v]) != 2:
            while any(frozenset((v, q)) not in used for q in adj[v]):
                out.append(walk(v))
    for v in adj:
        if any(frozenset((v, q)) not in used for q in adj[v]):
            out.append(walk(v))
    return out


def _occluded_flags(m, pr, offset, fronts, samples):
    """samples: [(x,y,z)] → 앞쪽 면에 가려졌는지 [bool] (오목한 입체용, numpy 사용)"""
    try:
        import numpy as np
    except Exception:
        return [False] * len(samples)
    ox, oy, oz = offset
    tris = []
    for fi, f in enumerate(m.faces):
        if not fronts[fi]:
            continue
        for k in range(1, len(f) - 1):
            tris.append((f[0], f[k], f[k + 1]))
    if not tris or not samples:
        return [False] * len(samples)
    S = np.array([pr.screen(x + ox, y + oy, z + oz) + (pr.depth(x + ox, y + oy, z + oz),) for x, y, z in m.v])
    T = np.array(tris)
    A, B, C = S[T[:, 0]], S[T[:, 1]], S[T[:, 2]]
    P = np.array([pr.screen(x + ox, y + oy, z + oz) + (pr.depth(x + ox, y + oy, z + oz),) for x, y, z in samples])
    v0 = (C - A)[:, :2]
    v1 = (B - A)[:, :2]
    d00 = (v0 * v0).sum(1)
    d01 = (v0 * v1).sum(1)
    d11 = (v1 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    ok = np.abs(den) > 1e-12
    out = []
    for p_ in P:
        v2 = p_[:2] - A[:, :2]
        d02 = (v0 * v2).sum(1)
        d12 = (v1 * v2).sum(1)
        with np.errstate(divide="ignore", invalid="ignore"):
            u = (d11 * d02 - d01 * d12) / den
            v = (d00 * d12 - d01 * d02) / den
        inside = ok & (u >= 1e-4) & (v >= 1e-4) & (u + v <= 1 - 1e-4)
        if not inside.any():
            out.append(False)
            continue
        z = A[:, 2] + u * (C[:, 2] - A[:, 2]) + v * (B[:, 2] - A[:, 2])
        out.append(bool((inside & (z < p_[2] - 1e-4)).any()))
    return out


def analyze_mesh(m, pr, offset=(0.0, 0.0, 0.0)):
    """한 덩어리의 화면 좌표(cm)와 보이는/숨은 꺾은선, 모서리, 면"""
    ox, oy, oz = offset
    pts = [pr.screen(x + ox, y + oy, z + oz) for x, y, z in m.v]
    fronts = [pr.facing(newell(m, f)) for f in m.faces]
    adj = {}
    for fi, f in enumerate(m.faces):
        for k in range(len(f)):
            e = frozenset((f[k], f[(k + 1) % len(f)]))
            adj.setdefault(e, []).append(fi)
    vis, hid, edges = [], [], []
    for e, fs in adj.items():
        if len(e) < 2:
            continue
        i, j = tuple(e)
        fr = [fronts[k] for k in fs]
        if e in m.smooth:
            if any(fr) and not all(fr):
                vis.append((i, j))
            continue
        if any(fr):
            vis.append((i, j))
            edges.append((i, j, True))
        else:
            hid.append((i, j))
            edges.append((i, j, False))
    extra = []     # (점1, 점2, 보이는지) 화면 좌표로 바로 그릴 조각 (오목한 입체)
    if not m.convex and vis:
        # 앞을 향한 선이라도 다른 면에 가려질 수 있음 → 조각 내어 하나하나 따짐
        pieces, samples = [], []
        for i, j in vis:
            a, b = m.v[i], m.v[j]
            L = math.dist(a, b)
            k = max(1, min(8, int(L / 0.35) + 1))
            for s in range(k):
                t0, t1 = s / k, (s + 1) / k
                pa = tuple(a[c] + (b[c] - a[c]) * t0 for c in range(3))
                pb = tuple(a[c] + (b[c] - a[c]) * t1 for c in range(3))
                pieces.append((pa, pb, (i, j)))
                samples.append(tuple((pa[c] + pb[c]) / 2 for c in range(3)))
        occ = _occluded_flags(m, pr, offset, fronts, samples)
        vis = []
        hid_extra = []
        for (pa, pb, _e), o_ in zip(pieces, occ):
            sa = pr.screen(pa[0] + ox, pa[1] + oy, pa[2] + oz)
            sb = pr.screen(pb[0] + ox, pb[1] + oy, pb[2] + oz)
            (hid_extra if o_ else extra).append((sa, sb))
        vis_chains = []
        extra = [(a, b, True) for a, b in extra] + [(a, b, False) for a, b in hid_extra]
        edges = [(i, j, v) for i, j, v in edges]
    else:
        vis_chains = chains(vis)
    dep = [pr.depth(x + ox, y + oy, z + oz) for x, y, z in m.v] or [0.0]
    return {"mesh": m, "pts": pts, "fronts": fronts, "vis": vis_chains, "hid": chains(hid),
            "edges": edges, "extra": extra, "offset": offset, "depth": sum(dep) / len(dep)}


# ---------------------------------------------------------------- 한 입체 전체 (자르기·벌리기 포함)
def frame_of(o, doc_objects):
    """회전·위치를 정하는 입체 (안에 넣은 입체는 바깥 입체를 따름)"""
    h = o.get("host")
    if h is not None and h in doc_objects and doc_objects[h].get("type") == "solid":
        return doc_objects[h]
    return o


def host_shift(o, doc_objects):
    """안에 넣은 입체를 바깥 입체와 밑면을 맞추기 위한 y 이동"""
    h = o.get("host")
    if h is None or h not in doc_objects:
        return 0.0
    ho = doc_objects[h]
    if o.get("align", "bottom") == "center":
        return 0.0
    return model_height(ho) / -2 + model_height(o) / 2


def model_height(o):
    m = build(o["kind"], o["params"])
    ys = [v[1] for v in m.v] or [0]
    return max(ys) - min(ys)


def analyze(o, doc_objects=None, attached=None):
    """그리기 정보: whole(통째), parts(그릴 덩어리들), section(단면)"""
    doc_objects = doc_objects or {}
    fr = frame_of(o, doc_objects)
    pr = Projector(fr if fr is not o else o)
    if fr is not o:
        # 바깥 입체의 투영을 쓰되, 곡면 여부는 바깥 기준
        pr = Projector(fr)
    sy = host_shift(o, doc_objects)
    m = build(o["kind"], o["params"])
    whole = analyze_mesh(m, pr, (0.0, sy, 0.0)) if m.sphere_r is None else None
    res = {"proj": pr, "mesh": m, "whole": whole, "parts": [], "section": None, "shift": sy,
           "sphere": None}
    plane = cut_plane(o, m if m.sphere_r is None else build(o["kind"], o["params"], sphere_mesh=True), attached)
    if m.sphere_r is not None and plane is None:
        r = m.sphere_r
        N = 120
        ring = [(r * math.cos(2 * math.pi * k / N), sy, r * math.sin(2 * math.pi * k / N)) for k in range(N)]
        res["sphere"] = {"r": r, "ring": [pr.screen(*q) for q in ring],
                         "front": [pr.depth(q[0], 0, q[2]) <= 1e-9 for q in ring]}
        res["whole"] = {"mesh": m, "pts": [pr.screen(x, y + sy, z) for x, y, z in m.v], "fronts": [],
                        "vis": [], "hid": [], "edges": [], "extra": [], "offset": (0, sy, 0)}
        return res
    if plane is None:
        res["parts"] = [whole]
        return res
    n, d = plane
    mm = m if m.sphere_r is None else build(o["kind"], o["params"], sphere_mesh=True)
    if m.sphere_r is not None:
        res["whole"] = {"mesh": m, "pts": [pr.screen(x, y + sy, z) for x, y, z in m.v], "fronts": [],
                        "vis": [], "hid": [], "edges": [], "extra": [], "offset": (0, sy, 0)}
    low, up, sec, sec_faces = clip(mm, n, d)
    c = o["cut"]
    gap = float(c.get("gap", 0.0))
    show = c.get("show", "both")
    res["section"] = {"pts3d": sec, "n": n, "d": d,
                      "name": section_name(sec, o["kind"], is_curved(o)),
                      "area": face_area_pts(sec)}
    sec_info = res["section"]
    if gap < 1e-9 and show == "both":
        # 벌리지 않으면 통째로 그리고, 단면만 겹쳐 그림
        base = whole if m.sphere_r is None else analyze_mesh(mm, pr, (0.0, sy, 0.0))
        segs = []
        for k in range(len(sec)):
            a, b = sec[k], sec[(k + 1) % len(sec)]
            mid = tuple((a[c] + b[c]) / 2 for c in range(3))
            vis = True
            for fi in sec_faces:
                f = mm.faces[fi]
                nn = newell(mm, f)
                L = math.sqrt(sum(q * q for q in nn)) or 1
                p0 = mm.v[f[0]]
                if abs(sum((mid[c] - p0[c]) * nn[c] for c in range(3)) / L) < 1e-5:
                    vis = base["fronts"][fi]
                    break
            segs.append((pr.screen(a[0], a[1] + sy, a[2]), pr.screen(b[0], b[1] + sy, b[2]), vis))
        sec_info["overlay"] = segs
        sec_info["poly"] = [pr.screen(q[0], q[1] + sy, q[2]) for q in sec]
        res["parts"] = [base]
        return res
    low_off = (-n[0] * gap / 2, sy - n[1] * gap / 2, -n[2] * gap / 2) if show == "both" else (0, sy, 0)
    up_off = (n[0] * gap / 2, sy + n[1] * gap / 2, n[2] * gap / 2) if show == "both" else (0, sy, 0)
    if m.sphere_r is None:
        o0 = pr.screen(0, sy, 0)
        sl = [a - b for a, b in zip(pr.screen(*low_off), o0)]
        su = [a - b for a, b in zip(pr.screen(*up_off), o0)]
        res["vshift"] = [su if (n[0] * x + n[1] * y + n[2] * z) > d + 1e-7 else sl for x, y, z in m.v]
    sec_info["poly"] = [pr.screen(q[0] + low_off[0], q[1] + low_off[1], q[2] + low_off[2]) for q in sec]
    parts = []
    if show in ("both", "low"):
        off = (-n[0] * gap / 2, sy - n[1] * gap / 2, -n[2] * gap / 2) if show == "both" else (0, sy, 0)
        parts.append(analyze_mesh(low, pr, off))
    if show in ("both", "up"):
        off = (n[0] * gap / 2, sy + n[1] * gap / 2, n[2] * gap / 2) if show == "both" else (0, sy, 0)
        parts.append(analyze_mesh(up, pr, off))
    res["parts"] = parts
    return res


def face_area_pts(P):
    if len(P) < 3:
        return 0.0
    nx, ny, nz = newell_pts(P)
    return math.sqrt(nx * nx + ny * ny + nz * nz) / 2


def point3d(o, sv=None, edge=None, t=0.5):
    """입체의 꼭짓점(sv) 또는 모서리(edge=(i,j)) 위 t 위치의 3D 좌표 (모델 좌표)"""
    m = build(o["kind"], o["params"])
    if sv is not None:
        return m.v[sv] if 0 <= sv < len(m.v) else None
    i, j = edge
    if not (0 <= i < len(m.v) and 0 <= j < len(m.v)):
        return None
    a, b = m.v[i], m.v[j]
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))


# ---------------------------------------------------------------- 겉넓이·부피
def _reg_area(n, s):
    return n * s * s / (4 * math.tan(math.pi / n))


def _apothem(n, s):
    return s / (2 * math.tan(math.pi / n))


def mesh_metrics(m):
    S = sum(face_area(m, f) for f in m.faces)
    V = 0.0
    for f in m.faces:
        a = m.v[f[0]]
        for k in range(1, len(f) - 1):
            b, c = m.v[f[k]], m.v[f[k + 1]]
            V += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                  + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
    return S, abs(V)


def metrics(kind, p):
    """(겉넓이, 부피, 겉넓이의 π 계수 또는 None, 부피의 π 계수 또는 None)"""
    g = lambda k: float(p[k])
    if kind == "cube":
        a = g("a")
        return 6 * a * a, a ** 3, None, None
    if kind == "cuboid":
        w, d, h = g("w"), g("d"), g("h")
        return 2 * (w * d + d * h + h * w), w * d * h, None, None
    if kind == "prism":
        n, s, h = int(p["n"]), g("s"), g("h")
        B = _reg_area(n, s)
        return 2 * B + n * s * h, B * h, None, None
    if kind == "pyramid":
        n, s, h = int(p["n"]), g("s"), g("h")
        B = _reg_area(n, s)
        slant = math.hypot(h, _apothem(n, s))
        return B + n * s * slant / 2, B * h / 3, None, None
    if kind == "frustum":
        n, s1, s2, h = int(p["n"]), g("s1"), g("s2"), g("h")
        B1, B2 = _reg_area(n, s1), _reg_area(n, s2)
        slant = math.hypot(h, _apothem(n, s1) - _apothem(n, s2))
        return B1 + B2 + n * (s1 + s2) / 2 * slant, h / 3 * (B1 + B2 + math.sqrt(B1 * B2)), None, None
    if kind == "stack":
        if int(p.get("n", 0)):
            S, V = mesh_metrics(build("stack", p))
            return S, V, None, None
        sk = vk = 0.0
        layers = p.get("layers", [])
        prev_top = None
        for idx, L in enumerate(layers):
            shape = L.get("shape", "line")
            if shape == "line":
                r1, r2, h = float(L.get("r1", 0)), float(L.get("r2", 0)), float(L.get("h", 1))
                vk += h / 3 * (r1 * r1 + r1 * r2 + r2 * r2)
                sk += (r1 + r2) * math.hypot(h, r1 - r2)
            elif shape == "dome":
                r1 = r = float(L.get("r1", 1))
                r2 = 0.0
                vk += 2 * r ** 3 / 3
                sk += 2 * r * r
            else:
                r1 = 0.0
                r2 = r = float(L.get("r2", 1))
                vk += 2 * r ** 3 / 3
                sk += 2 * r * r
            if idx == 0:
                sk += r1 * r1
            else:
                sk += abs(prev_top * prev_top - r1 * r1)
            prev_top = r2
        if prev_top:
            sk += prev_top * prev_top
        return sk * math.pi, vk * math.pi, sk, vk
    if kind == "cylinder":
        r, h = g("r"), g("h")
        sk, vk = 2 * r * r + 2 * r * h, r * r * h
    elif kind == "cone":
        r, h = g("r"), g("h")
        l = math.hypot(r, h)
        sk, vk = r * r + r * l, r * r * h / 3
    elif kind == "cone_frustum":
        r1, r2, h = g("r1"), g("r2"), g("h")
        l = math.hypot(h, r1 - r2)
        sk, vk = r1 * r1 + r2 * r2 + (r1 + r2) * l, h / 3 * (r1 * r1 + r1 * r2 + r2 * r2)
    else:  # sphere
        r = g("r")
        sk, vk = 4 * r * r, 4 * r ** 3 / 3
    return sk * math.pi, vk * math.pi, sk, vk


def edge_length(o, i, j):
    m = build(o["kind"], o["params"])
    return math.dist(m.v[i], m.v[j])


# ---------------------------------------------------------------- 전개도
NET_LAYOUTS = [("flower", "밑면 둘레에 펼치기"), ("strip", "옆면을 한 줄로")]


def net_supported(o):
    if o["kind"] == "sphere":
        return False
    if o["kind"] == "stack":
        return False
    return True


def _net_tree(m, kind, n_sides, layout):
    """면 번호 → (부모 면, 공유 모서리) . 뿌리는 부모 None"""
    adj = {}
    for fi, f in enumerate(m.faces):
        for k in range(len(f)):
            e = frozenset((f[k], f[(k + 1) % len(f)]))
            adj.setdefault(e, []).append(fi)

    def shared(a, b):
        fa = m.faces[a]
        for k in range(len(fa)):
            e = frozenset((fa[k], fa[(k + 1) % len(fa)]))
            if b in adj.get(e, []):
                return tuple(e)
        return None
    parent = {}
    if layout == "strip" and kind in ("cube", "cuboid", "prism", "frustum") and len(m.faces) >= 4:
        sides = list(range(2, len(m.faces)))
        root = sides[0]
        parent[root] = None
        for a, b in zip(sides, sides[1:]):
            parent[b] = (a, shared(a, b))
        parent[0] = (root, shared(root, 0))
        parent[1] = (root, shared(root, 1))
        return root, parent
    root = 0
    parent[root] = None
    queue = [root]
    while queue:
        a = queue.pop(0)
        fa = m.faces[a]
        for k in range(len(fa)):
            e = frozenset((fa[k], fa[(k + 1) % len(fa)]))
            for b in adj.get(e, []):
                if b not in parent:
                    parent[b] = (a, tuple(e))
                    queue.append(b)
    return root, parent


def _vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vnorm(a):
    L = math.sqrt(_vdot(a, a)) or 1
    return (a[0] / L, a[1] / L, a[2] / L)


def net_poly(o, layout="flower"):
    """다면체 전개도: [{"face": 번호, "pts": [(x,y)], "vids": [...], "fold": set(모서리 번호)}], 단위 cm"""
    m = build(o["kind"], o["params"])
    root, parent = _net_tree(m, o["kind"], 0, layout)
    order = [root]
    k = 0
    while k < len(order):
        a = order[k]
        for b, pa in parent.items():
            if pa and pa[0] == a and b not in order:
                order.append(b)
        k += 1
    pos = {}
    # 뿌리 면: 바깥에서 본 모양 그대로 평면에
    f = m.faces[root]
    n = _vnorm(newell(m, f))
    p0 = m.v[f[0]]
    e1 = _vnorm(_vsub(m.v[f[1]], p0))
    e2 = cross(n, e1)
    pos[root] = {vi: (_vdot(_vsub(m.v[vi], p0), e1), _vdot(_vsub(m.v[vi], p0), e2)) for vi in f}
    for b in order[1:]:
        a, (u, v) = parent[b]
        U, V = pos[a][u], pos[a][v]
        cen = [sum(q[c] for q in pos[a].values()) / len(pos[a]) for c in (0, 1)]
        E = (V[0] - U[0], V[1] - U[1])
        L = math.hypot(*E) or 1
        E = (E[0] / L, E[1] / L)
        N = (-E[1], E[0])
        if (cen[0] - U[0]) * N[0] + (cen[1] - U[1]) * N[1] > 0:
            N = (-N[0], -N[1])
        e = _vnorm(_vsub(m.v[v], m.v[u]))
        pts = {}
        for w in m.faces[b]:
            d = _vsub(m.v[w], m.v[u])
            s = _vdot(d, e)
            perp_ = _vsub(d, (e[0] * s, e[1] * s, e[2] * s))
            t = math.sqrt(_vdot(perp_, perp_))
            pts[w] = (U[0] + E[0] * s + N[0] * t, U[1] + E[1] * s + N[1] * t)
        pos[b] = pts
    faces = []
    for fi in order:
        f = m.faces[fi]
        fold = set()
        for k2 in range(len(f)):
            e = frozenset((f[k2], f[(k2 + 1) % len(f)]))
            pa = parent.get(fi)
            if pa and frozenset(pa[1]) == e:
                fold.add(k2)
            for c, pc in parent.items():
                if pc and pc[0] == fi and frozenset(pc[1]) == e:
                    fold.add(k2)
        faces.append({"face": fi, "pts": [pos[fi][vi] for vi in f], "vids": list(f), "fold": fold})
    return {"faces": faces, "mesh": m, "parent": parent, "root": root, "order": order, "pos": pos}


def net_curved(o):
    """곡면 입체 전개도: [("poly", 점들) | ("circle", 중심, r) | ("sector", 중심, r1, r2, 시작각, 크기)] 단위 cm"""
    k, p = o["kind"], o["params"]
    out = []
    if k == "cylinder":
        r, h = float(p["r"]), float(p["h"])
        W = 2 * math.pi * r
        out.append(("poly", [(0, 0), (W, 0), (W, h), (0, h)]))
        out.append(("circle", (W / 2, -r), r))
        out.append(("circle", (W / 2, h + r), r))
    elif k in ("cone", "cone_frustum"):
        if k == "cone":
            r1, r2, h = float(p["r"]), 0.0, float(p["h"])
        else:
            r1, r2, h = float(p["r1"]), float(p["r2"]), float(p["h"])
        if r1 < r2:
            r1, r2 = r2, r1
        l = math.hypot(h, r1 - r2)
        L1 = l * r1 / (r1 - r2) if r1 - r2 > 1e-9 else 1e9
        L2 = L1 - l
        ang = 360.0 * r1 / L1
        start = 270 - ang / 2          # 부채꼴이 아래로 열리게
        out.append(("sector", (0.0, 0.0), L2, L1, start, ang))
        mid = math.radians(270)
        cx, cy = (L1 + r1) * math.cos(mid), -(L1 + r1) * math.sin(mid)
        out.append(("circle", (cx, cy), r1))
        if r2 > 1e-9:
            cx2, cy2 = (L2 - r2) * math.cos(mid), -(L2 - r2) * math.sin(mid)
            out.append(("circle", (cx2, cy2), r2))
    return out


def _rot_about(pt, a, b, ang):
    """점 pt 를 직선 ab 둘레로 ang 라디안 회전 (로드리게스)"""
    k_ = _vnorm(_vsub(b, a))
    v = _vsub(pt, a)
    c, s = math.cos(ang), math.sin(ang)
    kv = cross(k_, v)
    kd = _vdot(k_, v)
    r = tuple(v[i] * c + kv[i] * s + k_[i] * kd * (1 - c) for i in range(3))
    return (r[0] + a[0], r[1] + a[1], r[2] + a[2])


def net_fold3d(o, layout, f):
    """접는 중인 전개도: [(면 번호, [(x,y,z) 3D])]  f=0 평평, f=1 다 접힘. 뿌리 면이 바닥(y=0)"""
    info = net_poly(o, layout)
    m, parent, order = info["mesh"], info["parent"], info["order"]
    flat = {}
    for fc in info["faces"]:
        flat[fc["face"]] = {vi: (x, 0.0, y) for vi, (x, y) in zip(fc["vids"], fc["pts"])}
    normals = {fi: _vnorm(newell(m, m.faces[fi])) for fi in order}
    children = {}
    for b, pa in parent.items():
        if pa:
            children.setdefault(pa[0], []).append(b)

    def subtree(fi):
        out = [fi]
        for c in children.get(fi, []):
            out += subtree(c)
        return out
    cur = {fi: dict(v) for fi, v in flat.items()}
    for b in order[1:]:
        a, (u, v) = parent[b]
        ang = math.acos(max(-1, min(1, _vdot(normals[a], normals[b])))) * f
        A_, B_ = cur[b][u], cur[b][v]
        sub = subtree(b)
        # 위(+y)로 접히는 방향 고르기
        test = [p_ for vi, p_ in cur[b].items() if vi not in (u, v)]
        sign = 1
        if test and ang > 1e-9:
            t1 = _rot_about(test[0], A_, B_, 0.2)
            t2 = _rot_about(test[0], A_, B_, -0.2)
            ref = cur[a]
            cen = [sum(q[c] for q in ref.values()) / len(ref) for c in range(3)]
            n_a = _vnorm(newell_pts(list(ref.values())))
            sign = 1 if _vdot(_vsub(t1, cen), n_a) < _vdot(_vsub(t2, cen), n_a) else -1
        for s_ in sub:
            cur[s_] = {vi: _rot_about(p_, A_, B_, sign * ang) for vi, p_ in cur[s_].items()}
    return [(fi, [cur[fi][vi] for vi in m.faces[fi]]) for fi in order], m
