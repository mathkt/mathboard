"""도형그리기 - 평면도형 도구: 이름 있는 평면도형 만들기와 '모양 유지' (점을 끌어도 정사각형은 정사각형)

좌표는 cm, 위쪽이 +y (화면에 놓을 때 뒤집음).
"""
import math

# (키, 이름, [(값 키, 이름, 기본값, 최소, 최대)])
SHAPES = {
    "eq_tri": ("정삼각형", [("a", "한 변", 4.0, 0.5, 30)]),
    "iso_tri": ("이등변삼각형", [("a", "밑변", 4.0, 0.5, 30), ("b", "같은 두 변", 4.5, 0.5, 30)]),
    "right_tri": ("직각삼각형", [("a", "밑변", 4.0, 0.5, 30), ("b", "높이", 3.0, 0.5, 30)]),
    "right_iso_tri": ("직각이등변삼각형", [("a", "직각을 낀 변", 3.5, 0.5, 30)]),
    "tri306090": ("30°·60°·90° 삼각형", [("a", "빗변", 5.0, 0.5, 30)]),
    "obtuse_tri": ("둔각삼각형", [("a", "밑변", 4.0, 0.5, 30), ("b", "다른 변", 2.5, 0.5, 30),
                              ("ang", "둔각 (°)", 120.0, 91, 175)]),
    "square": ("정사각형", [("a", "한 변", 3.0, 0.5, 30)]),
    "rect": ("직사각형", [("w", "가로", 4.5, 0.5, 30), ("h", "세로", 2.5, 0.5, 30)]),
    "para": ("평행사변형", [("w", "밑변", 4.0, 0.5, 30), ("s", "옆변", 2.5, 0.5, 30), ("ang", "끼인각 (°)", 60.0, 5, 175)]),
    "rhombus": ("마름모", [("a", "한 변", 3.0, 0.5, 30), ("ang", "한 각 (°)", 60.0, 5, 175)]),
    "trap": ("사다리꼴", [("a", "아랫변", 5.0, 0.5, 30), ("b", "윗변", 2.5, 0.1, 30), ("h", "높이", 2.5, 0.5, 30),
                       ("off", "윗변 왼쪽 위치", 0.8, -20, 20)]),
    "iso_trap": ("등변사다리꼴", [("a", "아랫변", 5.0, 0.5, 30), ("b", "윗변", 3.0, 0.1, 30), ("h", "높이", 2.5, 0.5, 30)]),
    "kite": ("연꼴", [("w", "너비", 3.0, 0.5, 30), ("t", "위쪽 높이", 1.3, 0.2, 30), ("u", "아래쪽 높이", 3.0, 0.2, 30)]),
    "circle": ("원", [("r", "반지름", 2.0, 0.2, 30)]),
    "semicircle": ("반원", [("r", "반지름", 2.5, 0.2, 30)]),
    "sector": ("부채꼴", [("r", "반지름", 3.0, 0.2, 30), ("ang", "중심각 (°)", 60.0, 1, 359)]),
    "arcseg": ("활꼴", [("r", "반지름", 3.0, 0.2, 30), ("ang", "중심각 (°)", 100.0, 1, 359)]),
    "concentric": ("동심원", [("r", "작은 원 반지름", 1.5, 0.2, 30), ("R", "큰 원 반지름", 2.5, 0.2, 30)]),
}
for _n in range(5, 13):
    SHAPES[f"reg{_n}"] = (f"정{['', '', '', '', '', '오', '육', '칠', '팔', '구', '십', '십일', '십이'][_n]}각형",
                          [("a", "한 변", 2.5 if _n < 9 else 1.8, 0.3, 30)])

GROUPS = [
    ("삼각형", ["eq_tri", "iso_tri", "right_tri", "right_iso_tri", "tri306090", "obtuse_tri"]),
    ("사각형", ["square", "rect", "para", "rhombus", "trap", "iso_trap", "kite"]),
    ("정다각형", [f"reg{n}" for n in range(5, 13)]),
    ("원", ["circle", "semicircle", "sector", "arcseg", "concentric"]),
]

# 모양 유지 규칙
CONSTRAINT = {"eq_tri": "similar", "iso_tri": "iso", "right_tri": "right", "right_iso_tri": "similar",
              "tri306090": "similar", "obtuse_tri": None, "square": "similar", "rect": "rect", "para": "para",
              "rhombus": "rhombus", "trap": "trap", "iso_trap": "isotrap", "kite": "kite",
              "semicircle": "arcfix", "sector": "arcfix", "arcseg": "arcfix"}
for _n in range(5, 13):
    CONSTRAINT[f"reg{_n}"] = "similar"


def defaults(kind):
    return {k: v for k, _n, v, _a, _b in SHAPES[kind][1]}


def _pol(r, deg):
    t = math.radians(deg)
    return (r * math.cos(t), r * math.sin(t))


def geometry(kind, p):
    """→ {"pts": [(x, y)], "kind": "poly"|"circle"|"arc"|"concentric", ...} (cm, 위가 +y)
    marks: [("right", i), ("tick", [(i, j), ...], 개수), ("par", [(i, j), (k, l)], 개수)]  (i→j 방향)"""
    g = lambda k: float(p.get(k, defaults(kind).get(k, 1)))
    if kind == "eq_tri":
        a = g("a")
        pts = [(0, a * math.sqrt(3) / 2), (-a / 2, 0), (a / 2, 0)]
        return {"kind": "poly", "pts": pts, "marks": [("tick", [(0, 1), (1, 2), (2, 0)], 1)]}
    if kind == "iso_tri":
        a, b = g("a"), g("b")
        h = math.sqrt(max(b * b - a * a / 4, 0.01))
        return {"kind": "poly", "pts": [(0, h), (-a / 2, 0), (a / 2, 0)], "marks": [("tick", [(0, 1), (0, 2)], 1)]}
    if kind == "right_tri":
        a, b = g("a"), g("b")
        return {"kind": "poly", "pts": [(0, b), (a, 0), (0, 0)], "marks": [("right", 2)]}
    if kind == "right_iso_tri":
        a = g("a")
        return {"kind": "poly", "pts": [(0, a), (a, 0), (0, 0)], "marks": [("right", 2), ("tick", [(2, 0), (2, 1)], 1)]}
    if kind == "tri306090":
        c = g("a")
        return {"kind": "poly", "pts": [(0, c * math.sqrt(3) / 2), (c / 2, 0), (0, 0)], "marks": [("right", 2)]}
    if kind == "obtuse_tri":
        a, b, ang = g("a"), g("b"), g("ang")
        B = (0, 0)
        A = _pol(b, ang)
        return {"kind": "poly", "pts": [A, B, (a, 0)], "marks": []}
    if kind == "square":
        a = g("a")
        return {"kind": "poly", "pts": [(0, a), (0, 0), (a, 0), (a, a)],
                "marks": [("right", 1), ("tick", [(0, 1), (1, 2), (2, 3), (3, 0)], 1)]}
    if kind == "rect":
        w, h = g("w"), g("h")
        return {"kind": "poly", "pts": [(0, h), (0, 0), (w, 0), (w, h)], "marks": [("right", 1)]}
    if kind == "para":
        w, s, ang = g("w"), g("s"), g("ang")
        dx, dy = _pol(s, ang)
        A, B, C, D = (dx, dy), (0, 0), (w, 0), (w + dx, dy)
        return {"kind": "poly", "pts": [A, B, C, D],
                "marks": [("par", [(1, 2), (0, 3)], 1), ("par", [(1, 0), (2, 3)], 2)]}
    if kind == "rhombus":
        a, ang = g("a"), g("ang")
        dx, dy = _pol(a, ang)
        pts = [(dx, dy), (0, 0), (a, 0), (a + dx, dy)]
        return {"kind": "poly", "pts": pts, "marks": [("tick", [(0, 1), (1, 2), (2, 3), (3, 0)], 1)]}
    if kind == "trap":
        a, b, h, off = g("a"), g("b"), g("h"), g("off")
        return {"kind": "poly", "pts": [(off, h), (0, 0), (a, 0), (off + b, h)], "marks": [("par", [(1, 2), (0, 3)], 1)]}
    if kind == "iso_trap":
        a, b, h = g("a"), g("b"), g("h")
        off = (a - b) / 2
        return {"kind": "poly", "pts": [(off, h), (0, 0), (a, 0), (off + b, h)],
                "marks": [("par", [(1, 2), (0, 3)], 1), ("tick", [(0, 1), (3, 2)], 1)]}
    if kind == "kite":
        w, t, u = g("w"), g("t"), g("u")
        pts = [(0, t), (-w / 2, 0), (0, -u), (w / 2, 0)]
        return {"kind": "poly", "pts": pts, "marks": [("tick", [(0, 1), (0, 3)], 1), ("tick", [(2, 1), (2, 3)], 2)]}
    if kind.startswith("reg"):
        n = int(kind[3:])
        a = g("a")
        R = a / (2 * math.sin(math.pi / n))
        pts = [_pol(R, -90 - 180 / n + 360 * (k + 1) / n) for k in range(n)]
        pts = pts[-1:] + pts[:-1]
        return {"kind": "poly", "pts": pts, "marks": []}
    if kind == "circle":
        r = g("r")
        return {"kind": "circle", "pts": [(0, 0), (r, 0)], "marks": []}
    if kind == "concentric":
        r, R = g("r"), g("R")
        return {"kind": "concentric", "pts": [(0, 0), _pol(r, 45), _pol(R, 30)], "marks": []}
    if kind in ("semicircle", "sector", "arcseg"):
        r = g("r")
        ang = 180.0 if kind == "semicircle" else g("ang")
        st = 90 - ang / 2
        return {"kind": "arc", "pts": [(0, 0), _pol(r, st), _pol(r, st + ang)], "ang": ang,
                "sector": kind == "sector", "chord": kind in ("semicircle", "arcseg"), "marks": []}
    raise KeyError(kind)


def outline(kind, p):
    """미리보기용 선: [[(x, y), ...], ...] (cm, 위가 +y), 가운데가 원점"""
    gm = geometry(kind, p)
    P = gm["pts"]
    lines = []
    if gm["kind"] == "poly":
        lines.append(P + [P[0]])
    elif gm["kind"] in ("circle", "concentric"):
        C = P[0]
        for q in P[1:]:
            r = math.dist(C, q)
            lines.append([(C[0] + r * math.cos(2 * math.pi * k / 72), C[1] + r * math.sin(2 * math.pi * k / 72)) for k in range(73)])
    else:
        C, A = P[0], P[1]
        r = math.dist(C, A)
        a0 = math.degrees(math.atan2(A[1] - C[1], A[0] - C[0]))
        arc = [(C[0] + r * math.cos(math.radians(a0 + gm["ang"] * k / 48)),
                C[1] + r * math.sin(math.radians(a0 + gm["ang"] * k / 48))) for k in range(49)]
        if gm["sector"]:
            lines.append([C] + arc + [C])
        else:
            lines.append(arc + ([arc[0]] if gm["chord"] else []))
    xs = [x for ln in lines for x, _ in ln]
    ys = [y for ln in lines for _, y in ln]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    return [[(x - cx, y - cy) for x, y in ln] for ln in lines], (cx, cy)


# ---------------------------------------------------------------- 모양 유지
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _mul(a, s):
    return (a[0] * s, a[1] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _len(a):
    return math.hypot(a[0], a[1])


def _unit(a):
    L = _len(a)
    return (a[0] / L, a[1] / L) if L > 1e-9 else (1.0, 0.0)


def _perp(a):
    return (-a[1], a[0])


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _reflect(p, a, b):
    """점 p 를 직선 ab 에 대칭"""
    d = _unit(_sub(b, a))
    v = _sub(p, a)
    proj = _add(a, _mul(d, _dot(v, d)))
    return _sub(_mul(proj, 2), p)


def _similar(P, k, old, anchor):
    """anchor 를 고정하고 old→P[k] 로 가는 닮음 변환을 나머지 점에 적용"""
    A = P[anchor]
    u, v = _sub(old, A), _sub(P[k], A)
    den = u[0] * u[0] + u[1] * u[1]
    if den < 1e-12:
        return P
    # 복소수 v/u
    ar = (v[0] * u[0] + v[1] * u[1]) / den
    ai = (v[1] * u[0] - v[0] * u[1]) / den
    out = list(P)
    for j in range(len(P)):
        if j in (k, anchor):
            continue
        z = _sub(P[j], A)
        out[j] = _add(A, (ar * z[0] - ai * z[1], ar * z[1] + ai * z[0]))
    return out


def enforce(rule, P, k, old):
    """P: 점 좌표 목록 (P[k] 는 이미 새 위치), old: 끌기 전 P[k].  → 새 좌표 목록"""
    n = len(P)
    P = list(P)
    if rule == "similar":
        return _similar(P, k, old, (k - 1) % n)
    if rule == "rect" and n == 4:
        o = P[(k + 2) % 4]
        u = _unit(_sub(P[(k + 1) % 4], o))
        v = _unit(_sub(P[(k - 1) % 4], o))
        d = _sub(P[k], o)
        P[(k + 1) % 4] = _add(o, _mul(u, _dot(d, u)))
        P[(k - 1) % 4] = _add(o, _mul(v, _dot(d, v)))
        return P
    if rule == "para" and n == 4:
        P[(k + 3) % 4] = _add(P[k], _sub(P[(k + 2) % 4], P[(k + 1) % 4]))
        return P
    if rule == "rhombus" and n == 4:
        o = P[(k + 2) % 4]
        Mold = _mul(_add(old, o), 0.5)
        h = _len(_sub(P[(k + 1) % 4], P[(k - 1) % 4])) / 2
        M = _mul(_add(P[k], o), 0.5)
        nn = _perp(_unit(_sub(P[k], o)))
        s = 1 if _dot(_sub(P[(k + 1) % 4], Mold), _perp(_unit(_sub(old, o)))) >= 0 else -1
        P[(k + 1) % 4] = _add(M, _mul(nn, h * s))
        P[(k - 1) % 4] = _sub(M, _mul(nn, h * s))
        return P
    if rule in ("trap", "isotrap") and n == 4:
        # 점 순서 A(0) B(1) C(2) D(3): 아랫변 BC, 윗변 AD 가 평행
        pair = {0: 3, 3: 0, 1: 2, 2: 1}[k]
        other = (1, 2) if k in (0, 3) else (0, 3)
        if rule == "trap":
            w = _unit(_sub(P[other[1]], P[other[0]]))
            L = _len(_sub(old, P[pair]))
            # k 가 왼쪽 끝(A 또는 B)이면 짝은 오른쪽(+w), 아니면 왼쪽(-w)
            left = k in (0, 1)
            P[pair] = _add(P[k], _mul(w, L if left else -L))
        else:
            a, b = P[other[0]], P[other[1]]
            M = _mul(_add(a, b), 0.5)
            axis_b = _add(M, _perp(_unit(_sub(b, a))))
            P[pair] = _reflect(P[k], M, axis_b)
        return P
    if rule == "kite" and n == 4:
        if k in (1, 3):
            P[4 - k] = _reflect(P[k], P[0], P[2])
        else:
            P[3] = _reflect(P[1], P[0], P[2])
        return P
    if rule == "iso" and n == 3:
        if k == 0:
            M = _mul(_add(P[1], P[2]), 0.5)
            ax = _perp(_unit(_sub(P[2], P[1])))
            P[0] = _add(M, _mul(ax, _dot(_sub(P[0], M), ax)))
        else:
            j = 3 - k
            Mold = _mul(_add(old, P[j]), 0.5)
            P[j] = _reflect(P[k], P[0], Mold) if _len(_sub(Mold, P[0])) > 1e-9 else P[j]
        return P
    if rule == "right" and n == 3:
        if k == 2:
            M = _mul(_add(P[0], P[1]), 0.5)
            R = _len(_sub(P[1], P[0])) / 2
            P[2] = _add(M, _mul(_unit(_sub(P[2], M)), R))
        else:
            j = 1 - k
            s = 1 if _cross(_sub(old, P[2]), _sub(P[j], P[2])) >= 0 else -1
            u = _unit(_sub(P[k], P[2]))
            dirv = _perp(u) if s > 0 else _mul(_perp(u), -1)
            P[j] = _add(P[2], _mul(dirv, _len(_sub(P[j], P[2]))))
        return P
    if rule == "arcfix" and n == 3:
        # 중심 O(0), 양 끝 A(1) B(2): 중심을 끌면 함께 이동, 끝을 끌면 중심각·모양 유지
        if k == 0:
            d = _sub(P[0], old)
            P[1], P[2] = _add(P[1], d), _add(P[2], d)
            return P
        return _similar(P, k, old, 0)
    return P
