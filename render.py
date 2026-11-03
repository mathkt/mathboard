"""도형그리기 - 모양 계산(Geo)과 그리기(Renderer)"""
import math

from PySide6.QtCore import Qt, QPointF, QRectF, QLineF
from PySide6.QtGui import (QPainter, QPen, QBrush, QColor, QFont, QFontMetricsF,
                           QPainterPath, QPolygonF)

import model as M
import solid as S

HALO = QColor(40, 140, 255, 90)
SEL_EDGE = QColor(40, 140, 255)


# ---------------------------------------------------------------- 벡터 도우미
def dot(a, b):
    return a.x() * b.x() + a.y() * b.y()


def length(a):
    return math.hypot(a.x(), a.y())


def norm(a):
    L = length(a)
    return QPointF(a.x() / L, a.y() / L) if L > 1e-9 else QPointF(0, 0)


def perp(a):
    """화면 기준으로 왼쪽(진행 방향에서 반시계 90°)"""
    return QPointF(a.y(), -a.x())


def dir_deg(deg):
    r = math.radians(deg)
    return QPointF(math.cos(r), -math.sin(r))


# ---------------------------------------------------------------- 글꼴/펜
def qfont(fd):
    f = QFont(fd.get("family") or "맑은 고딕")
    f.setPixelSize(max(1, int(round(float(fd.get("size", 14)) * 4 / 3))))
    f.setBold(bool(fd.get("bold")))
    f.setItalic(bool(fd.get("italic")))
    return f


_fm = {}


def metrics(fd):
    key = (fd.get("family"), fd.get("size"), fd.get("bold"), fd.get("italic"))
    if key not in _fm:
        _fm[key] = QFontMetricsF(qfont(fd))
    return _fm[key]


def text_size(text, fd):
    fm = metrics(fd)
    lines = text.split("\n")
    w = max((fm.horizontalAdvance(l) for l in lines), default=0)
    return w + 2, fm.height() * max(1, len(lines))


# ---------------------------------------------------------------- 수식처럼 쓰기 (교과서 스타일)
import re

_TOKEN = re.compile(r"[A-Za-z]+|[\u0370-\u03FF]|°|[^A-Za-z\u0370-\u03FF°]+")


def math_runs(line):
    """[(글자, 종류)] 종류: 'n' 보통, 'i' 기울임, 'deg' 도(°)
    - 소문자 한 글자(x, a)와 그리스 문자는 기울임
    - 대문자(점 이름 A, B)와 두 글자 이상(cm, sin)은 곧게"""
    out = []
    def _op(m_):
        op = m_.group(1).replace("-", "−")
        before = m_.string[:m_.start()].rstrip()
        if op == "−" and (not before or before[-1] in "=(+−×÷<>±,"):
            return (" " if m_.group(0)[:1].isspace() and before else "") + "−"     # 음수 부호(−5)는 붙여 씀
        return "\u2009" + op + "\u2009"
    line = re.sub(r"\s*([+=<>±×÷−]|(?<=[\w)°])-(?=[\w(]))\s*", _op, line)
    for t in _TOKEN.findall(line):
        if t == "°":
            kind = "deg"
        elif "\u0370" <= t[0] <= "\u03FF":
            kind = "i"
        elif t.isalpha() and t.isascii() and len(t) == 1 and t.islower():
            kind = "i"
        else:
            kind = "n"
        if out and out[-1][1] == kind and kind != "deg":
            out[-1] = (out[-1][0] + t, kind)
        else:
            out.append((t, kind))
    return out


MATH_FAMILY = "KaTeX_Math"     # TeX 수식용 기울임 (미지수 x, y, a, θ)


_has_math = None


def _italic(fd):
    global _has_math
    d = dict(fd)
    if _has_math is None:
        from PySide6.QtGui import QFontDatabase
        _has_math = MATH_FAMILY in QFontDatabase.families()
    if _has_math:
        d["family"] = MATH_FAMILY
        d["italic"] = True
        d["bold"] = False
    else:
        d["italic"] = not fd.get("italic")
    return d


def _deg_w(fd):
    return metrics(fd).height() * 0.30


def _run_w(t, kind, fd):
    if kind == "deg":
        return _deg_w(fd)
    return metrics(_italic(fd) if kind == "i" else fd).horizontalAdvance(t)


def line_width(line, fd, math):
    if not math:
        return metrics(fd).horizontalAdvance(line)
    return sum(_run_w(t, k, fd) for t, k in math_runs(line))


def rich_size(text, fd, math):
    if not math:
        return text_size(text, fd)
    fm = metrics(fd)
    lines = text.split("\n")
    w = max((line_width(l, fd, True) for l in lines), default=0)
    return w + 2, fm.height() * max(1, len(lines))


def draw_rich(p, rect, text, fd, color, align, math):
    if not math:
        p.setFont(qfont(fd))
        p.setPen(QColor(color))
        p.drawText(rect, align, text)
        return
    fm = metrics(fd)
    lines = text.split("\n")
    top = rect.top() + (rect.height() - fm.height() * len(lines)) / 2
    col = QColor(color)
    for k, line in enumerate(lines):
        w = line_width(line, fd, True)
        x = rect.left() + 1 if align & Qt.AlignLeft else rect.center().x() - w / 2
        base = top + k * fm.height() + fm.ascent()
        for t, kind in math_runs(line):
            if kind == "deg":
                em = fm.height()
                r = em * 0.085
                cap = fm.capHeight() if hasattr(fm, "capHeight") else fm.ascent() * 0.7
                c = QPointF(x + r + em * 0.04, base - cap + r)
                pen = QPen(col, max(0.6, em * 0.035))
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(c, r, r)
                x += _deg_w(fd)
                continue
            f = _italic(fd) if kind == "i" else fd
            p.setFont(qfont(f))
            p.setPen(col)
            p.drawText(QPointF(x, base), t)
            x += _run_w(t, kind, fd)


def qpen(st, extra=0.0, color=None):
    w = float(st.get("width", 2))
    pen = QPen(QColor(color or st.get("color", "#000000")))
    pen.setWidthF(w + extra)
    pen.setJoinStyle(Qt.RoundJoin)
    dash = st.get("dash", "solid")
    if extra or dash == "solid":
        pen.setStyle(Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        return pen
    b = max(w, 0.5)
    if dash == "dash":
        pat = [max(7 / b, 1.5), max(5 / b, 1.5)]
        pen.setCapStyle(Qt.FlatCap)
    elif dash == "dot":
        pat = [0.01, max(4.5 / b, 2.0)]
        pen.setCapStyle(Qt.RoundCap)
    else:
        pat = [max(10 / b, 2), max(4 / b + 1, 2), 0.01, max(4 / b + 1, 2)]
        pen.setCapStyle(Qt.RoundCap)
    pen.setDashPattern(pat)
    return pen


def alpha_color(hexcolor, alpha_percent):
    c = QColor(hexcolor)
    c.setAlpha(int(255 * max(0, min(100, alpha_percent)) / 100))
    return c


# ---------------------------------------------------------------- 모양 계산
class Geo:
    def __init__(self, doc):
        self.doc = doc
        self.math = bool(doc.settings.get("math_style"))
        self._solids = {}
        self.undef = set()
        self.sync_points()
        self.vcent = {}
        self.edge_cent = {}
        for poly in doc.items("polygon"):
            ids = [i for i in poly["pts"] if i in doc.objects]
            if len(ids) < 2:
                continue
            c = QPointF(sum(doc.objects[i]["x"] for i in ids) / len(ids),
                        sum(doc.objects[i]["y"] for i in ids) / len(ids))
            for i in ids:
                self.vcent.setdefault(i, c)
            for k in range(len(ids)):
                self.edge_cent.setdefault(frozenset((ids[k], ids[(k + 1) % len(ids)])), c)

    # ---- 작도로 생긴 점·입체에 붙은 점 위치 계산 (만든 순서대로)
    def sync_points(self):
        doc = self.doc
        for q in sorted(doc.items("point"), key=lambda o: o["id"]):
            q.pop("undef", None)
            if q.get("solid") is not None:
                so = doc.objects.get(q["solid"])
                if not so:
                    continue
                P = self.solid(so)["P"]
                if q.get("sv") is not None and q["sv"] < len(P):
                    q["x"], q["y"] = P[q["sv"]].x(), P[q["sv"]].y()
                elif q.get("edge") and max(q["edge"]) < len(P):
                    A, B = P[q["edge"][0]], P[q["edge"][1]]
                    t = float(q.get("t", 0.5))
                    q["x"], q["y"] = A.x() + (B.x() - A.x()) * t, A.y() + (B.y() - A.y()) * t
                elif q.get("dep3") or q.get("face") is not None or q.get("ring") is not None:
                    xyz = M.attached_xyz(doc, q)
                    if xyz is None:
                        self.undef.add(q["id"])
                        q["undef"] = True
                        continue
                    S_ = self.solid_screen(so, xyz)
                    q["x"], q["y"] = S_.x(), S_.y()
            elif q.get("dep"):
                pos = self.dep_pos(q["dep"])
                if pos is None:
                    self.undef.add(q["id"])
                    q["undef"] = True
                else:
                    q["x"], q["y"] = pos.x(), pos.y()
        if self.undef:
            self.undef = doc.dependents(self.undef)

    def seg_hidden3d(self, o):
        """같은 입체에 붙은 두 점을 잇는 선분이 보이지 않는 곳(입체 안, 뒤쪽 면)에 있으면 True"""
        key = ("h3", o["id"])
        if key in self._solids:
            return self._solids[key]
        res = False
        doc = self.doc
        qa, qb = doc.objects.get(o.get("a")), doc.objects.get(o.get("b"))
        sid_ = None
        if qa and qb:
            sa = qa.get("solid") if qa.get("solid") is not None else M.mid_solid(doc, qa)
            sb = qb.get("solid") if qb.get("solid") is not None else M.mid_solid(doc, qb)
            if sa is not None and sa == sb:
                sid_ = sa
        so = doc.objects.get(sid_) if sid_ is not None else None
        if so and not so.get("cut") and o.get("kind", "segment") == "segment":
            A, B = M.attached_xyz(doc, qa), M.attached_xyz(doc, qb)
            info = self.solid(so)
            whole = info["a"].get("whole")
            mesh = info["a"]["mesh"]
            if A is not None and B is not None and whole and whole.get("fronts") and mesh.sphere_r is None:
                common = []
                for fi, f in enumerate(mesh.faces):
                    n = S.newell(mesh, f)
                    L = math.sqrt(sum(c * c for c in n)) or 1.0
                    n = tuple(c / L for c in n)
                    p0 = mesh.v[f[0]]
                    d = sum(n[k] * p0[k] for k in range(3))
                    if all(abs(sum(n[k] * X[k] for k in range(3)) - d) < 1e-5 and S.inside_face(mesh, f, n, X)
                           for X in (A, B)):
                        common.append(fi)
                if common:
                    res = not any(whole["fronts"][fi] for fi in common if fi < len(whole["fronts"]))
                else:
                    res = True
        self._solids[key] = res
        return res

    # ---- 좌표평면·그래프
    def axes(self, o):
        G = M.GRID
        u = float(o.get("unit", 1)) * G
        O = QPointF(o["x"], o["y"])
        x0, x1 = float(o.get("xmin", -5)), float(o.get("xmax", 5))
        y0, y1 = float(o.get("ymin", -5)), float(o.get("ymax", 5))
        if x1 <= x0:
            x1 = x0 + 1
        if y1 <= y0:
            y1 = y0 + 1
        rect = QRectF(O.x() + x0 * u, O.y() - y1 * u, (x1 - x0) * u, (y1 - y0) * u)
        return {"O": O, "u": u, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "rect": rect,
                "to": lambda x, y: QPointF(O.x() + x * u, O.y() - y * u)}

    def graph_paths(self, o):
        """그래프 선(끊어진 곳마다 따로)과 식 글자 자리"""
        import graphs as GR
        ax = self.doc.objects.get(o.get("axes"))
        if not ax:
            return None
        a = self.axes(ax)
        f = GR.func(o)
        x0, x1, y0, y1 = a["x0"], a["x1"], a["y0"], a["y1"]
        N = 600
        path = QPainterPath()
        down = False
        prev = None
        last_in = None
        span = y1 - y0
        for i in range(N + 1):
            x = x0 + (x1 - x0) * i / N
            try:
                y = f(x)
            except Exception:
                y = None
            if y is None or not math.isfinite(y) or (prev is not None and abs(y - prev) > span * 2):
                down = False
                prev = y if (y is not None and math.isfinite(y)) else None
                if prev is None:
                    continue
            prev = y
            yc = max(y0 - span, min(y1 + span, y))
            P = a["to"](x, yc)
            if down:
                path.lineTo(P)
            else:
                path.moveTo(P)
                down = True
            if y0 <= y <= y1:
                last_in = P
        return {"path": path, "rect": a["rect"], "end": last_in}

    def solid_screen(self, so, xyz):
        a = self.solid(so)["a"]
        fr = S.frame_of(so, self.doc.objects)
        sx, sy = a["proj"].screen(xyz[0], xyz[1] + a["shift"], xyz[2])
        return QPointF(fr["x"] + sx * M.GRID, fr["y"] + sy * M.GRID)

    def pt(self, pid):
        o = self.doc.objects.get(pid)
        if not o or pid in self.undef:
            return None
        return QPointF(o["x"], o["y"])

    def prim(self, oid):
        """교점 계산용 기본 모양: ('line', A, B, 종류) 또는 ('circle', 중심, 반지름)"""
        o = self.doc.objects.get(oid)
        if not o or oid in self.undef:
            return None
        t = o["type"]
        if t == "segment":
            A, B = self.pt(o["a"]), self.pt(o["b"])
            return ("line", A, B, o.get("kind", "segment")) if A and B else None
        if t == "circle":
            C, P = self.pt(o["c"]), self.pt(o["p"])
            return ("circle", C, length(P - C)) if C and P else None
        if t == "arc":
            C = self.pt(o["c"])
            if not C:
                return None
            R = M.arc_radius(self.doc, o) * M.GRID if o.get("r") is not None else length(self.pt(o["p"]) - C)
            return ("circle", C, R)
        return None

    def intersections(self, p1, p2):
        out = []
        if p1[0] == "line" and p2[0] == "line":
            A, B, C, D = p1[1], p1[2], p2[1], p2[2]
            d1, d2 = B - A, D - C
            den = d1.x() * d2.y() - d1.y() * d2.x()
            if abs(den) < 1e-9:
                return []
            t = ((C.x() - A.x()) * d2.y() - (C.y() - A.y()) * d2.x()) / den
            return [A + d1 * t]
        if p1[0] == "circle" and p2[0] == "line":
            p1, p2 = p2, p1
        if p1[0] == "line" and p2[0] == "circle":
            A, B = p1[1], p1[2]
            C, R = p2[1], p2[2]
            d = B - A
            L2 = dot(d, d)
            if L2 < 1e-12:
                return []
            t0 = dot(C - A, d) / L2
            F = A + d * t0
            h2 = R * R - dot(C - F, C - F)
            if h2 < -1e-6:
                return []
            s = math.sqrt(max(0.0, h2) / L2)
            return [A + d * (t0 - s), A + d * (t0 + s)]
        C1, R1, C2, R2 = p1[1], p1[2], p2[1], p2[2]
        d = length(C2 - C1)
        if d < 1e-9 or d > R1 + R2 + 1e-6 or d < abs(R1 - R2) - 1e-6:
            return []
        a = (R1 * R1 - R2 * R2 + d * d) / (2 * d)
        h = math.sqrt(max(0.0, R1 * R1 - a * a))
        u = (C2 - C1) * (1 / d)
        M_ = C1 + u * a
        n = perp(u)
        return [M_ + n * h, M_ - n * h]

    def dep_pos(self, dep):
        t = dep.get("t")
        G = M.GRID
        if t == "coord":
            ax = self.doc.objects.get(dep.get("axes"))
            if not ax:
                return None
            u = float(ax.get("unit", 1)) * G
            return QPointF(ax["x"] + float(dep["x"]) * u, ax["y"] - float(dep["y"]) * u)
        if t == "mid":
            A, B = self.pt(dep["a"]), self.pt(dep["b"])
            return (A + B) * 0.5 if A and B else None
        if t == "foot":
            P, A, B = self.pt(dep["p"]), self.pt(dep["a"]), self.pt(dep["b"])
            if not (P and A and B):
                return None
            d = B - A
            L2 = dot(d, d)
            return A + d * (dot(P - A, d) / L2) if L2 > 1e-12 else A
        if t == "dir":
            P, A, B = self.pt(dep["base"]), self.pt(dep["a"]), self.pt(dep["b"])
            if not (P and A and B):
                return None
            u = norm(B - A)
            if length(u) < 0.5:
                return None
            return P + (perp(u) if dep.get("mode") == "perp" else u) * G
        if t == "bis":
            A, V, B = self.pt(dep["a"]), self.pt(dep["v"]), self.pt(dep["b"])
            if not (A and V and B):
                return None
            u = norm(A - V) + norm(B - V)
            if length(u) < 1e-6:
                u = perp(norm(A - V))
            return V + norm(u) * G
        if t == "inter":
            p1, p2 = self.prim(dep["o1"]), self.prim(dep["o2"])
            if not p1 or not p2:
                return None
            pts = self.intersections(p1, p2)
            k = int(dep.get("k", 0))
            return pts[k] if k < len(pts) else (pts[0] if pts and len(pts) == 1 else None)
        if t == "tan":           # 원 밖의 점에서 그은 접선의 접점
            P = self.pt(dep["p"])
            pr = self.prim(dep["obj"])
            if not P or not pr or pr[0] != "circle":
                return None
            C, R = pr[1], pr[2]
            d = length(P - C)
            if d < R - 1e-6:
                return None
            if d < R + 1e-6:
                return P
            u = norm(P - C)
            th = math.acos(R / d) * (1 if int(dep.get("k", 0)) == 0 else -1)
            rot = QPointF(u.x() * math.cos(th) - u.y() * math.sin(th), u.x() * math.sin(th) + u.y() * math.cos(th))
            return C + rot * R
        if t == "center":        # 삼각형의 외심·내심·무게중심·수심
            A, B, C = self.pt(dep["a"]), self.pt(dep["b"]), self.pt(dep["v"])
            if not (A and B and C):
                return None
            kind = dep.get("kind")
            if kind == "centroid":
                return (A + B + C) * (1 / 3)
            a, b, c = length(B - C), length(C - A), length(A - B)
            if kind == "in":
                s = a + b + c
                return (A * a + B * b + C * c) * (1 / s) if s > 1e-9 else None
            D = 2 * (A.x() * (B.y() - C.y()) + B.x() * (C.y() - A.y()) + C.x() * (A.y() - B.y()))
            if abs(D) < 1e-9:
                return None
            ux = ((A.x() ** 2 + A.y() ** 2) * (B.y() - C.y()) + (B.x() ** 2 + B.y() ** 2) * (C.y() - A.y())
                  + (C.x() ** 2 + C.y() ** 2) * (A.y() - B.y())) / D
            uy = ((A.x() ** 2 + A.y() ** 2) * (C.x() - B.x()) + (B.x() ** 2 + B.y() ** 2) * (A.x() - C.x())
                  + (C.x() ** 2 + C.y() ** 2) * (B.x() - A.x())) / D
            O = QPointF(ux, uy)
            if kind == "circum":
                return O
            return A + B + C - O * 2        # 수심 = A + B + C - 2·외심
        if t == "copylen":       # 길이가 같은 선분 옮기기
            P, Q, A, B = self.pt(dep["p"]), self.pt(dep["q"]), self.pt(dep["a"]), self.pt(dep["b"])
            if not (P and Q and A and B):
                return None
            u = norm(Q - P)
            return P + u * length(B - A) if length(u) > 0.5 else None
        if t == "copyang":       # 크기가 같은 각 옮기기
            A, V, B = self.pt(dep["a"]), self.pt(dep["v"]), self.pt(dep["b"])
            P, Q = self.pt(dep["p"]), self.pt(dep["q"])
            if not (A and V and B and P and Q):
                return None
            a1 = math.atan2(A.y() - V.y(), A.x() - V.x())
            a2 = math.atan2(B.y() - V.y(), B.x() - V.x())
            ang = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
            base = math.atan2(Q.y() - P.y(), Q.x() - P.x())
            L = max(length(Q - P), M.GRID)
            return P + QPointF(math.cos(base + ang), math.sin(base + ang)) * L
        if t == "on":
            pr = self.prim(dep["obj"])
            if not pr:
                return None
            u = float(dep.get("u", 0))
            if pr[0] == "line":
                return pr[1] + (pr[2] - pr[1]) * u
            return pr[1] + QPointF(math.cos(u), -math.sin(u)) * pr[2]
        return None

    def on_param(self, oid, wp):
        """선·원 위의 점: 마우스 위치 → 매개변수"""
        pr = self.prim(oid)
        if not pr:
            return None
        if pr[0] == "line":
            d = pr[2] - pr[1]
            u = dot(wp - pr[1], d) / max(dot(d, d), 1e-9)
            kind = pr[3]
            if kind == "segment":
                u = max(0.0, min(1.0, u))
            elif kind == "ray":
                u = max(0.0, u)
            return u
        return math.atan2(-(wp.y() - pr[1].y()), wp.x() - pr[1].x())

    # ---- 작도 흔적 (컴퍼스로 그린 짧은 호)
    def trace_path(self, o):
        path = QPainterPath()
        k = o.get("kind")

        def mark(C, X, deg=13):
            """중심 C, 지나는 점 X 둘레의 짧은 호"""
            R = length(X - C)
            if R < 1:
                return
            a = math.degrees(math.atan2(-(X.y() - C.y()), X.x() - C.x()))
            rc = QRectF(C.x() - R, C.y() - R, 2 * R, 2 * R)
            path.arcMoveTo(rc, a - deg)
            path.arcTo(rc, a - deg, 2 * deg)

        def cc(C1, R1, C2, R2):
            return self.intersections(("circle", C1, R1), ("circle", C2, R2))
        if k == "pbis":
            A, B = self.pt(o["a"]), self.pt(o["b"])
            if not (A and B):
                return path
            r = 0.62 * length(B - A)
            for X in cc(A, r, B, r):
                mark(A, X)
                mark(B, X)
        elif k == "abis":
            A, V, B = self.pt(o["a"]), self.pt(o["v"]), self.pt(o["b"])
            if not (A and V and B):
                return path
            r1 = 0.45 * min(length(A - V), length(B - V))
            ua, ub = norm(A - V), norm(B - V)
            P1, P2 = V + ua * r1, V + ub * r1
            a1 = math.degrees(math.atan2(-ua.y(), ua.x()))
            a2 = math.degrees(math.atan2(-ub.y(), ub.x()))
            span = (a2 - a1) % 360
            if span > 180:
                a1, span = a2, 360 - span
            rc = QRectF(V.x() - r1, V.y() - r1, 2 * r1, 2 * r1)
            path.arcMoveTo(rc, a1 - 8)
            path.arcTo(rc, a1 - 8, span + 16)
            r2 = 0.8 * length(P2 - P1)
            xs = cc(P1, r2, P2, r2)
            if xs:
                X = max(xs, key=lambda q: length(q - V))
                mark(P1, X)
                mark(P2, X)
        elif k == "mark":        # 중심 c, 점 p 를 지나는 짧은 호 (삼각형 작도 등)
            C, P = self.pt(o["c"]), self.pt(o["p"])
            if C and P:
                mark(C, P, o.get("deg", 14))
        elif k == "copyang":
            A, V, B, P, Q = (self.pt(o.get(k_)) for k_ in ("a", "v", "b", "p", "q"))
            if not (A and V and B and P and Q):
                return path
            r1 = 0.45 * min(length(A - V), length(B - V))
            X1, X2 = V + norm(A - V) * r1, V + norm(B - V) * r1
            Y1 = P + norm(Q - P) * r1
            d = self.dep_pos({"t": "copyang", "a": o["a"], "v": o["v"], "b": o["b"], "p": o["p"], "q": o["q"]})
            if not d:
                return path
            Y2 = P + norm(d - P) * r1
            for C_, S_, E_ in ((V, X1, X2), (P, Y1, Y2)):
                a1 = math.degrees(math.atan2(-(S_.y() - C_.y()), S_.x() - C_.x()))
                a2 = math.degrees(math.atan2(-(E_.y() - C_.y()), E_.x() - C_.x()))
                sp = (a2 - a1 + 180) % 360 - 180
                rc = QRectF(C_.x() - r1, C_.y() - r1, 2 * r1, 2 * r1)
                lo = a1 if sp >= 0 else a1 + sp
                path.arcMoveTo(rc, lo - 8)
                path.arcTo(rc, lo - 8, abs(sp) + 16)
            mark(X1, X2, 12)
            mark(Y1, Y2, 12)
        elif k == "perp":
            P, A, B = self.pt(o["p"]), self.pt(o["a"]), self.pt(o["b"])
            if not (P and A and B):
                return path
            d = norm(B - A)
            F = A + d * dot(P - A, d)
            dist = length(P - F)
            if dist < 2:
                r = 0.3 * length(B - A)
                X1, X2 = P - d * r, P + d * r
                mark(P, X1)
                mark(P, X2)
            else:
                r = dist * 1.25
                xs = self.intersections(("line", A, B, "line"), ("circle", P, r))
                if len(xs) < 2:
                    return path
                X1, X2 = xs
                mark(P, X1)
                mark(P, X2)
            r2 = 0.62 * length(X2 - X1)
            ys = cc(X1, r2, X2, r2)
            if ys:
                Y = max(ys, key=lambda q: length(q - P)) if dist >= 2 else ys[0]
                mark(X1, Y)
                mark(X2, Y)
        return path

    def tsize(self, text, fd):
        return rich_size(text, fd, self.math)

    def P(self, pid):
        o = self.doc.objects[pid]
        return QPointF(o["x"], o["y"])

    # ---- 점 이름
    def label_text(self, o):
        """점 이름 (좌표평면 위 점은 '좌표 함께'면 A(2, 3))"""
        t = o.get("label", "")
        dep = o.get("dep") or {}
        if t and dep.get("t") == "coord" and o.get("show_xy"):
            from graphs import nice
            t += f"({nice(dep['x'])}, {nice(dep['y'])})".replace("-", "−")
        return t

    def point_label(self, pid):
        o = self.doc.objects[pid]
        if not o.get("show_label", True) or not o.get("label"):
            return None
        w, h = self.tsize(self.label_text(o), o["font"])
        P = self.P(pid)
        if o.get("label_auto", True):
            if pid in self.vcent:
                d = norm(P - self.vcent[pid])
                if length(d) < 0.5:
                    d = QPointF(0.7071, -0.7071)
            else:
                d = QPointF(0.7071, -0.7071)
            ext = w / 2 * abs(d.x()) + h / 2 * abs(d.y())
            c = P + d * (ext + o.get("size", 3.5) + 3)
        else:
            c = P + QPointF(o.get("label_dx", 0), o.get("label_dy", 0))
        return QRectF(c.x() - w / 2, c.y() - h / 2, w, h)

    # ---- 선
    def seg_line(self, o, K=20000.0):
        A, B = self.P(o["a"]), self.P(o["b"])
        t = norm(B - A)
        kind = o.get("kind", "segment")
        if kind == "line":
            return QLineF(A - t * K, B + t * K)
        if kind == "ray":
            return QLineF(A, B + t * K)
        return QLineF(A, B)

    # ---- 중괄호
    def ends(self, o):
        """길이 표시의 두 끝점 (평면: 점, 입체: 꼭짓점의 화면 위치, 전개도: 모서리)"""
        if "net" in o:
            no = self.doc.objects.get(o["net"])
            info = self.net(no) if no else None
            edges = (info or {}).get("net_edges")
            k = int(o.get("ne", -1))
            if not edges or not (0 <= k < len(edges)):
                return None
            return edges[k]
        if "solid" in o:
            so = self.doc.objects.get(o["solid"])
            if not so:
                return None
            info = self.solid(so)
            i, j = o["sv"]
            return info["P"][i], info["P"][j]
        return self.P(o["a"]), self.P(o["b"])

    def base_normal(self, o, A, B, t):
        n = perp(t)
        if "net" in o:
            no = self.doc.objects.get(o["net"])
            info = self.net(no) if no else None
            if info and info.get("hull") is not None:
                c = info["hull"].boundingRect().center()
                # 모서리 바로 옆(안쪽)의 면 중심 쪽이 아닌 바깥으로
                mid = (A + B) * 0.5
                side = None
                for poly in info.get("polys", []):
                    if poly.containsPoint(mid + n * 3, Qt.OddEvenFill):
                        side = -1
                        break
                    if poly.containsPoint(mid - n * 3, Qt.OddEvenFill):
                        side = 1
                        break
                if side is None:
                    side = 1 if dot(mid - c, n) >= 0 else -1
                n = n * side
            return n
        if "solid" in o:
            so = self.doc.objects.get(o["solid"])
            if so and dot((A + B) * 0.5 - self.solid(so)["center"], n) < 0:
                n = n * -1
        return n

    def brace_frame(self, o):
        e = self.ends(o)
        if not e:
            return None
        A, B = e
        d = B - A
        L = length(d)
        if L < 1:
            return None
        t = QPointF(d.x() / L, d.y() / L)
        gap = 3 + float(o["style"].get("width", 1.5))
        return A, B, L, t, self.base_normal(o, A, B, t), gap

    def brace_text(self, o):
        mode = o.get("text_mode", "auto")
        if mode == "none":
            return ""
        if mode == "custom":
            return o.get("text", "")
        return M.fmt_len(self.doc, M.brace_len(self.doc, o))

    def arc_height(self, o, L):
        h = o.get("arc_height")
        return float(h) if h else max(8.0, L * 0.18)

    def arc(self, o):
        """양 끝점을 잇는 원호. 글자가 있으면 가운데를 비우고 그 자리에 글자."""
        e = self.ends(o)
        if not e:
            return None
        A, B = e
        d = B - A
        L = length(d)
        if L < 1:
            return None
        t = QPointF(d.x() / L, d.y() / L)
        n = self.base_normal(o, A, B, t) * (1 if o.get("side", 1) >= 0 else -1)
        h = max(2.0, self.arc_height(o, L))
        R = (L * L / 4 + h * h) / (2 * h)
        mid = (A + B) * 0.5
        C = mid + n * (h - R)
        apex = mid + n * h
        ang = lambda P: math.atan2(P.y() - C.y(), P.x() - C.x())
        a0, a1, am = ang(A), ang(B), ang(apex)
        s = (a1 - a0) % (2 * math.pi)
        if abs(((a0 + s / 2) - am + math.pi) % (2 * math.pi) - math.pi) > 1e-3:
            s -= 2 * math.pi
        N = max(32, int(abs(s) * R / 3))
        pts = [C + QPointF(math.cos(a0 + s * i / N), math.sin(a0 + s * i / N)) * R for i in range(N + 1)]
        pts[0], pts[-1] = A, B
        text = self.brace_text(o)
        rect = gap = None
        if text:
            w, th = self.tsize(text, o["font"])
            c = apex + QPointF(o.get("label_dx", 0), o.get("label_dy", 0))
            rect = QRectF(c.x() - w / 2, c.y() - th / 2, w, th)
            gap = rect.adjusted(-4, -1, 4, 1)
        path = QPainterPath()
        pen_down = False
        for P in pts:
            if gap is not None and gap.contains(P):
                pen_down = False
                continue
            if pen_down:
                path.lineTo(P)
            else:
                path.moveTo(P)
                pen_down = True
        return {"path": path, "tip": apex, "rect": rect, "text": text, "n": n}

    def brace(self, o):
        if o.get("shape") == "arc":
            return self.arc(o)
        fr = self.brace_frame(o)
        if not fr:
            return None
        A, B, L, t, n0, gap = fr
        n = n0 * (1 if o.get("side", 1) >= 0 else -1)
        h = max(2.0, float(o.get("height", 12)))
        a = h / 2
        r = min(h, L / 4)

        def P(x, y):
            return A + t * x + n * (gap + y)

        path = QPainterPath(P(0, 0))
        path.quadTo(P(0, a), P(r, a))
        path.lineTo(P(L / 2 - r, a))
        path.quadTo(P(L / 2, a), P(L / 2, h))
        path.quadTo(P(L / 2, a), P(L / 2 + r, a))
        path.lineTo(P(L - r, a))
        path.quadTo(P(L, a), P(L, 0))
        tip = P(L / 2, h)
        text = self.brace_text(o)
        rect = None
        if text:
            w, th = self.tsize(text, o["font"])
            ext = w / 2 * abs(n.x()) + th / 2 * abs(n.y())
            c = tip + n * (ext + 3) + QPointF(o.get("label_dx", 0), o.get("label_dy", 0))
            rect = QRectF(c.x() - w / 2, c.y() - th / 2, w, th)
        return {"path": path, "tip": tip, "rect": rect, "text": text, "n": n}

    # ---- 각 표시
    def angle_text(self, o, span):
        mode = o.get("label_mode", "value")
        if mode == "none":
            return ""
        if mode == "custom":
            return o.get("text", "")
        return M.fmt_angle(self.doc, M.angle_value(self.doc, o))

    def angle(self, o):
        V = self.P(o["v"])
        start, span = M.angle_span(self.doc, o)
        if span < 0.05 or span > 359.95:
            return None
        r = float(o.get("radius", 22))
        arcs = max(1, min(3, int(o.get("arcs", 1))))
        ua, ub = dir_deg(start), dir_deg(start + span)
        u = dir_deg(start + span / 2)
        v = perp(u)
        right = o.get("right_auto", True) and abs(M.angle_value(self.doc, o) - 90) < 0.5
        stroke, fill = QPainterPath(), QPainterPath()
        if right:
            s = r * 0.7
            p1, p2, p3 = V + ua * s, V + (ua + ub) * s, V + ub * s
            stroke.moveTo(p1)
            stroke.lineTo(p2)
            stroke.lineTo(p3)
            fill.addPolygon(QPolygonF([V, p1, p2, p3]))
            fill.closeSubpath()
            target = V + (ua + ub) * (s * 0.5)
            outer = s * 1.414
        else:
            for i in range(arcs):
                rr = r + i * 4
                rc = QRectF(V.x() - rr, V.y() - rr, 2 * rr, 2 * rr)
                stroke.arcMoveTo(rc, start)
                stroke.arcTo(rc, start, span)
            rc = QRectF(V.x() - r, V.y() - r, 2 * r, 2 * r)
            fill.moveTo(V)
            fill.arcTo(rc, start, span)
            fill.closeSubpath()
            outer = r + (arcs - 1) * 4
            target = V + u * outer
        text = self.angle_text(o, span)
        if right and o.get("label_mode", "value") == "value":
            text = ""   # 직각은 ┐ 표시만 (값을 보려면 '직접 입력' 사용)
        rect, leader = None, None
        mode = o.get("place", "auto")
        if mode == "auto":
            mode = "leader" if span < 35 else "inside"
        if text:
            w, th = self.tsize(text, o["font"])
            ext_u = w / 2 * abs(u.x()) + th / 2 * abs(u.y())
            ext_v = w / 2 * abs(v.x()) + th / 2 * abs(v.y())
            lu, lv = o.get("lu"), o.get("lv")
            if lu is None or lv is None:
                if mode == "inside":
                    lu, lv = outer + 4 + ext_u, 0.0
                else:
                    lu, lv = outer + 16 + ext_u, outer * 0.5 + 22 + ext_v
            c = V + u * lu + v * lv
            rect = QRectF(c.x() - w / 2, c.y() - th / 2, w, th)
            if mode == "leader":
                d = target - c
                sx = (w / 2 + 3) / abs(d.x()) if abs(d.x()) > 1e-6 else 1e9
                sy = (th / 2 + 3) / abs(d.y()) if abs(d.y()) > 1e-6 else 1e9
                s = min(sx, sy)
                if s < 0.95:
                    leader = (c + d * s, target)
        return {"V": V, "start": start, "span": span, "u": u, "v": v, "stroke": stroke,
                "fill": fill, "rect": rect, "text": text, "leader": leader, "right": right,
                "outer": outer}

    # ---- 호·부채꼴
    def arcs(self, o):
        C = self.P(o["c"])
        if o.get("r") is not None:
            R = float(o["r"]) * M.GRID
        else:
            R = length(self.P(o["p"]) - C)
        if R < 0.5:
            return None
        start, span = M.arc_angles(self.doc, o)
        rc = QRectF(C.x() - R, C.y() - R, 2 * R, 2 * R)
        path = QPainterPath()
        if o.get("sector"):
            path.moveTo(C)
            path.lineTo(C + dir_deg(start) * R)
            path.arcTo(rc, start, span)
            path.closeSubpath()
        else:
            path.arcMoveTo(rc, start)
            path.arcTo(rc, start, span)
        fill = QPainterPath()
        fill.moveTo(C)
        fill.arcTo(rc, start, span)
        fill.closeSubpath()
        return {"path": path, "fill": fill, "C": C, "R": R, "start": start, "span": span}

    # ---- 입체도형
    def solid(self, o):
        c = self._solids.get(o["id"])
        if c is not None:
            return c
        att = {}
        for q in self.doc.items("point"):
            if q.get("solid") == o["id"] or (q.get("solid") is None and M.mid_solid(self.doc, q) == o["id"]):
                xyz = M.attached_xyz(self.doc, q)
                if xyz is not None:
                    att[q["id"]] = xyz
        a = S.analyze(o, self.doc.objects, att)
        G = M.GRID
        fr = S.frame_of(o, self.doc.objects)
        ox, oy = fr["x"], fr["y"]

        def toQ(xy):
            return QPointF(ox + xy[0] * G, oy + xy[1] * G)
        whole = a["whole"]
        Pts = [toQ(p) for p in whole["pts"]]
        if a.get("vshift"):     # 벌린 조각의 꼭짓점 이름·붙은 점도 함께 이동
            Pts = [P + QPointF(dv[0] * G, dv[1] * G) for P, dv in zip(Pts, a["vshift"])]
        info = {"a": a, "P": Pts, "outline": None, "circle": None, "faces": []}
        vis, hid = QPainterPath(), QPainterPath()
        allpts = []
        colors = o.get("face_colors", {})
        cut = o.get("cut") or {}
        sec_col = (cut.get("color", "#f5a623"), cut.get("alpha", 45))
        backs, fronts = [], []
        pdraw = []
        es = o.get("edge_styles") or {}
        curved = S.is_curved(o)
        inner = o.get("inner_line", "solid") if o.get("host") is not None else "solid"
        info["edge_hits"] = []
        info["custom"] = []
        keycache = {}

        def ekey(part_mesh, i, j, v):
            base_m = getattr(part_mesh, "parent", part_mesh)
            if id(base_m) not in keycache:
                keycache[id(base_m)] = S.edge_keys(base_m, curved)
            kmap, rings = keycache[id(base_m)]
            e = S.part_edge(part_mesh, i, j)
            if e is None:
                return "sec:" + ("v" if v else "h")
            k = kmap.get(e)
            if k is None:
                return "sec:" + ("v" if v else "h")
            if k in rings:
                k += ":v" if v else ":h"
            return k
        cls_cache = {}

        def cls(key, v):
            """선의 그리기 방법: 'V'(보이는 선) / 'H'(숨은 선) / None(안 그림) / ('C', 모양) 직접 정한 선"""
            ck = (key, v)
            if ck in cls_cache:
                return cls_cache[ck]
            st = es.get(key)
            mode = (st or {}).get("mode", "auto")
            if mode == "auto":
                if inner == "dash":
                    mode = "dash"
                elif inner == "allsolid":
                    mode = "solid"
                elif inner == "hide":
                    mode = "hide"
            if mode == "auto" and not (st and (st.get("width") or st.get("color"))):
                r = "V" if v else "H"
            elif mode == "hide":
                r = None
            else:
                if mode == "auto":
                    mode = "solid" if v else "dash"
                base = o["style"] if mode == "solid" else o.get("hid_style", o["style"])
                d = dict(base)
                d["dash"] = "solid" if mode == "solid" else (base.get("dash") if base.get("dash", "solid") != "solid" else "dash")
                if st and st.get("width"):
                    d["width"] = float(st["width"])
                if st and st.get("color"):
                    d["color"] = st["color"]
                r = ("C", d["dash"], float(d.get("width", 2)), d.get("color", "#000000"))
            cls_cache[ck] = r
            return r
        for part in a["parts"]:
            PP = [toQ(p) for p in part["pts"]]
            pm = part["mesh"]
            groups_ = {}       # 분류 → [(i, j)]
            loose = {}         # 분류 → [(A, B)] 화면 좌표 조각
            for flag, segs in ((True, part.get("seg_vis", [])), (False, part.get("seg_hid", []))):
                for i, j in segs:
                    k = ekey(pm, i, j, flag)
                    info["edge_hits"].append((k, PP[i], PP[j], flag))
                    c = cls(k, flag)
                    if c is not None:
                        groups_.setdefault(c, []).append((i, j))
            for it in part["extra"]:
                sa, sb, v = it[0], it[1], it[2]
                A, B = toQ(sa), toQ(sb)
                if len(it) > 3:
                    k = ekey(pm, it[3][0], it[3][1], v)
                    info["edge_hits"].append((k, A, B, v))
                    c = cls(k, v)
                else:
                    c = "V" if v else "H"
                if c is not None:
                    loose.setdefault(c, []).append((A, B))
            paths = {}
            for c in set(groups_) | set(loose):
                path = QPainterPath()
                for ch in S.chains(groups_.get(c, [])):
                    path.moveTo(PP[ch[0]])
                    for v in ch[1:]:
                        path.lineTo(PP[v])
                for A, B in loose.get(c, []):
                    path.moveTo(A)
                    path.lineTo(B)
                paths[c] = path
            pv = paths.pop("V", QPainterPath())
            ph = paths.pop("H", QPainterPath())
            custom = [(path, {"dash": c[1], "width": c[2], "color": c[3]}) for c, path in paths.items()]
            info["custom"] += custom
            vis.addPath(pv)
            hid.addPath(ph)
            mesh = part["mesh"]
            used = set(v for f in mesh.faces for v in f)
            allpts += [PP[i] for i in used]
            hh = S.hull([(PP[i].x(), PP[i].y()) for i in used])
            pdraw.append({"vis": pv, "hid": ph, "hull": QPolygonF([QPointF(x, y) for x, y in hh]),
                          "depth": part.get("depth", 0), "fills": [], "custom": custom})
            backs, fronts = [], []
            groups = {}
            for fi, f in enumerate(mesh.faces):
                g = mesh.groups[fi]
                poly = QPolygonF([PP[i] for i in f])
                info["faces"].append((g, part["fronts"][fi], poly))
                info.setdefault("face_fi", []).append(fi if pm is a["mesh"] else None)
                col = colors.get(g)
                if col is None and g == "단면":
                    col = sec_col
                if col is None:
                    continue
                key = (g, part["fronts"][fi])
                if key not in groups:
                    groups[key] = [QPainterPath(), col]
                groups[key][0].addPolygon(poly)
            for (g, front), (path, col) in groups.items():
                path.setFillRule(Qt.WindingFill)
                (fronts if front else backs).append((path, col[0], col[1]))
            pdraw[-1]["fills"] = backs + fronts
            pdraw[-1]["fills_front"] = fronts
        pdraw.sort(key=lambda d_: -d_["depth"])     # 먼 조각부터
        info["pdraw"] = pdraw
        info["fills"] = [f_ for d_ in pdraw for f_ in d_["fills"]]
        sp = a["sphere"]
        if sp:
            R = sp["r"] * G
            ring = [toQ(q) for q in sp["ring"]]
            N = len(ring)
            for flag in (True, False):
                c = cls("eq:" + ("v" if flag else "h"), flag)
                path = QPainterPath()
                k0 = next((k for k in range(N) if sp["front"][k] != flag and sp["front"][(k + 1) % N] == flag), None)
                if k0 is None:
                    if all(f == flag for f in sp["front"]):
                        path.addPolygon(QPolygonF(ring + [ring[0]]))
                else:
                    k = (k0 + 1) % N
                    path.moveTo(ring[k])
                    while sp["front"][k] == flag:
                        k = (k + 1) % N
                        path.lineTo(ring[k])
                        if k == (k0 + 1) % N:
                            break
                pl = path.toSubpathPolygons()
                for poly_ in pl:
                    for q_ in range(poly_.size() - 1):
                        info["edge_hits"].append(("eq:" + ("v" if flag else "h"), poly_[q_], poly_[q_ + 1], flag))
                if c == "V":
                    vis.addPath(path)
                elif c == "H":
                    hid.addPath(path)
                elif c is not None:
                    info["custom"].append((path, {"dash": c[1], "width": c[2], "color": c[3]}))
            C = toQ(a["proj"].screen(0, a["shift"], 0))
            outline = QPainterPath()
            outline.addEllipse(C, R, R)
            info["outline"] = outline
            info["circle"] = (C, R)
            info["hull"] = QPolygonF(outline.toFillPolygon())
            info["center"] = C
            allpts = []
        sec = a["section"]
        info["section"] = sec
        info["sec_poly"] = None
        if sec and sec.get("poly") and len(sec["poly"]) >= 3:
            info["sec_poly"] = QPolygonF([toQ(p) for p in sec["poly"]])
            if sec.get("overlay") is not None:
                path = QPainterPath()
                path.addPolygon(info["sec_poly"])
                path.closeSubpath()
                info["fills"].append((path, sec_col[0], sec_col[1]))
                for sa, sb, v in sec["overlay"]:
                    k = "sec:" + ("v" if v else "h")
                    A, B = toQ(sa), toQ(sb)
                    info["edge_hits"].append((k, A, B, v))
                    c = cls(k, v)
                    if c is None:
                        continue
                    if c in ("V", "H"):
                        pth = vis if c == "V" else hid
                    else:
                        pth = QPainterPath()
                        info["custom"].append((pth, {"dash": c[1], "width": c[2], "color": c[3]}))
                    pth.moveTo(A)
                    pth.lineTo(B)
        info["vis"], info["hid"] = vis, hid
        if allpts:
            h = S.hull([(p.x(), p.y()) for p in allpts])
            info["hull"] = QPolygonF([QPointF(x, y) for x, y in h])
            info["center"] = QPointF(sum(x for x, _ in h) / len(h), sum(y for _, y in h) / len(h)) if h else QPointF(ox, oy)
        elif "hull" not in info:
            info["hull"] = QPolygonF()
            info["center"] = QPointF(ox, oy)
        # 꼭짓점 이름
        mesh = a["mesh"]
        labs = []
        names = o.get("labels", [])
        nb = {}
        for f in (whole["mesh"].faces if whole else []):
            for q in range(len(f)):
                e = frozenset((f[q], f[(q + 1) % len(f)]))
                if e in mesh.smooth:
                    continue
                a1, b1 = f[q], f[(q + 1) % len(f)]
                nb.setdefault(a1, set()).add(b1)
                nb.setdefault(b1, set()).add(a1)

        def gap_dir(vi):
            """꼭짓점에서 만나는 모서리들 사이의 가장 넓은 빈틈 방향"""
            P0 = Pts[vi]
            angs = sorted(math.atan2(Pts[q].y() - P0.y(), Pts[q].x() - P0.x())
                          for q in nb.get(vi, ()) if length(Pts[q] - P0) > 1)
            if len(nb.get(vi, ())) > 8 or len(angs) < 2:
                return None
            best, bdir = -1, None
            for q in range(len(angs)):
                a1 = angs[q]
                a2 = angs[(q + 1) % len(angs)] + (2 * math.pi if q == len(angs) - 1 else 0)
                if a2 - a1 > best:
                    best, bdir = a2 - a1, (a1 + a2) / 2
            return QPointF(math.cos(bdir), math.sin(bdir))

        show_c = o.get("show_center", False)
        info["center_pts"] = []
        for k, vi in enumerate(mesh.named):
            is_c = k in mesh.centers
            if is_c:
                if not show_c:
                    continue
                info["center_pts"].append(Pts[vi])
            elif not o.get("show_labels", True):
                continue
            if k >= len(names) or not names[k]:
                continue
            w, th = self.tsize(names[k], o["font"])
            P = Pts[vi]
            off = o.get("lab_off", {}).get(str(k))
            if off:
                c = P + QPointF(off[0], off[1])
            else:
                d = None if is_c else gap_dir(vi)
                if d is None:
                    d = norm(P - info["center"])
                    if length(d) < 0.5 or is_c:
                        d = QPointF(0.7071, -0.7071) if not is_c else QPointF(1, 0.35)
                ext = w / 2 * abs(d.x()) + th / 2 * abs(d.y())
                c = P + norm(d) * (ext + 4)
            labs.append((k, QRectF(c.x() - w / 2, c.y() - th / 2, w, th), names[k]))
        # 단면 이름
        info["sec_label"] = None
        if sec and cut.get("show_name") and info["sec_poly"] is not None and sec.get("name"):
            br = info["sec_poly"].boundingRect()
            w, th = self.tsize(sec["name"], o["font"])
            info["sec_label"] = (QRectF(br.center().x() - w / 2, br.center().y() - th / 2, w, th), sec["name"])
        info["labels"] = labs
        self._solids[o["id"]] = info
        return info

    # ---- 전개도
    def net(self, o):
        c = self._solids.get(("net", o["id"]))
        if c is not None:
            return c
        so = self.doc.objects.get(o.get("solid"))
        if not so or not S.net_supported(so):
            return None
        G = M.GRID
        info = {"fills": [], "solid_path": QPainterPath(), "fold_path": QPainterPath(), "labels": [], "polys": [],
                "net_edges": []}
        fold = float(o.get("fold", 0)) if not S.is_curved(so) else 0.0
        if S.is_curved(so):
            shapes = S.net_curved(so)
            xs, ys = [], []
            for sh in shapes:
                if sh[0] == "poly":
                    xs += [p_[0] for p_ in sh[1]]
                    ys += [p_[1] for p_ in sh[1]]
                elif sh[0] == "circle":
                    (cx, cy), rr = sh[1], sh[2]
                    xs += [cx - rr, cx + rr]
                    ys += [cy - rr, cy + rr]
                else:
                    (cx, cy), r1, r2, st, sp = sh[1], sh[2], sh[3], sh[4], sh[5]
                    for k in range(0, 41):
                        a = math.radians(st + sp * k / 40)
                        for rr in (r1, r2):
                            xs.append(cx + rr * math.cos(a))
                            ys.append(cy - rr * math.sin(a))
            mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            T = lambda x, y: QPointF(o["x"] + (x - mx) * G, o["y"] + (y - my) * G)
            for sh in shapes:
                path = QPainterPath()
                if sh[0] == "poly":
                    PP_ = [T(*p_) for p_ in sh[1]]
                    path.addPolygon(QPolygonF(PP_))
                    path.closeSubpath()
                    info["polys"].append(QPolygonF(PP_))
                    for k_ in range(len(PP_)):
                        info["net_edges"].append((PP_[k_], PP_[(k_ + 1) % len(PP_)]))
                elif sh[0] == "circle":
                    path.addEllipse(T(*sh[1]), sh[2] * G, sh[2] * G)
                else:
                    (cx, cy), r1, r2, st, sp = sh[1], sh[2], sh[3], sh[4], sh[5]
                    C = T(cx, cy)
                    R1, R2 = r1 * G, r2 * G
                    path.moveTo(C + dir_deg(st) * R1)
                    path.lineTo(C + dir_deg(st) * R2)
                    info["net_edges"].append((C + dir_deg(st) * R1, C + dir_deg(st) * R2))
                    info["net_edges"].append((C + dir_deg(st + sp) * R1, C + dir_deg(st + sp) * R2))
                    path.arcTo(QRectF(C.x() - R2, C.y() - R2, 2 * R2, 2 * R2), st, sp)
                    path.lineTo(C + dir_deg(st + sp) * R1)
                    if R1 > 0.5:
                        path.arcTo(QRectF(C.x() - R1, C.y() - R1, 2 * R1, 2 * R1), st + sp, -sp)
                    path.closeSubpath()
                info["solid_path"].addPath(path)
                info["fills"].append(path)
            info["hull"] = QPolygonF(info["solid_path"].boundingRect().adjusted(-4, -4, 4, 4))
        elif fold <= 1e-6:
            nd = S.net_poly(so, o.get("layout", "flower"))
            xs = [p_[0] for fc in nd["faces"] for p_ in fc["pts"]]
            ys = [p_[1] for fc in nd["faces"] for p_ in fc["pts"]]
            mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            T = lambda x, y: QPointF(o["x"] + (x - mx) * G, o["y"] - (y - my) * G)
            seen = set()
            mesh = nd["mesh"]
            names = so.get("labels", [])
            lab_pos = {}
            for fc in nd["faces"]:
                P = [T(*p_) for p_ in fc["pts"]]
                poly = QPolygonF(P)
                info["polys"].append(poly)
                fp = QPainterPath()
                fp.addPolygon(poly)
                fp.closeSubpath()
                info["fills"].append(fp)
                cen = QPointF(sum(q.x() for q in P) / len(P), sum(q.y() for q in P) / len(P))
                for k in range(len(P)):
                    a_, b_ = P[k], P[(k + 1) % len(P)]
                    key = (round(a_.x() + b_.x(), 1), round(a_.y() + b_.y(), 1))
                    if key in seen:
                        continue
                    seen.add(key)
                    info["net_edges"].append((a_, b_))
                    path = info["fold_path"] if k in fc["fold"] else info["solid_path"]
                    path.moveTo(a_)
                    path.lineTo(b_)
                for vi, q in zip(fc["vids"], P):
                    if vi in mesh.named:
                        kk = (round(q.x(), 1), round(q.y(), 1))
                        d0 = lab_pos.get(kk, (q, QPointF(0, 0), vi))
                        lab_pos[kk] = (q, d0[1] + norm(q - cen), vi)
            if o.get("show_labels", True):
                for q, dsum, vi in lab_pos.values():
                    k = mesh.named.index(vi)
                    if k >= len(names) or not names[k]:
                        continue
                    w, th = self.tsize(names[k], o["font"])
                    d = norm(dsum) if length(dsum) > 1e-6 else QPointF(0.7, -0.7)
                    ext = w / 2 * abs(d.x()) + th / 2 * abs(d.y())
                    c_ = q + d * (ext + 3)
                    info["labels"].append((QRectF(c_.x() - w / 2, c_.y() - th / 2, w, th), names[k]))
            hp = S.hull([(q.x(), q.y()) for poly in info["polys"] for q in poly])
            info["hull"] = QPolygonF([QPointF(x, y) for x, y in hp])
        else:
            faces3d, mesh = S.net_fold3d(so, o.get("layout", "flower"), fold)
            fake = {"view": "rot", "yaw": -30.0, "pitch": 30.0, "kind": "cube"}
            pr = S.Projector(fake)
            allp = [p_ for _fi, pts in faces3d for p_ in pts]
            cx = sum(p_[0] for p_ in allp) / len(allp)
            cz = sum(p_[2] for p_ in allp) / len(allp)
            scr = [pr.screen(p_[0] - cx, p_[1], p_[2] - cz) for p_ in allp]
            mx = (min(s[0] for s in scr) + max(s[0] for s in scr)) / 2
            my = (min(s[1] for s in scr) + max(s[1] for s in scr)) / 2
            items = []
            for fi, pts in faces3d:
                sp_ = [pr.screen(p_[0] - cx, p_[1], p_[2] - cz) for p_ in pts]
                dep = sum(pr.depth(p_[0] - cx, p_[1], p_[2] - cz) for p_ in pts) / len(pts)
                poly = QPolygonF([QPointF(o["x"] + (s[0] - mx) * G, o["y"] + (s[1] - my) * G) for s in sp_])
                items.append((dep, poly))
            items.sort(key=lambda t: -t[0])
            info["folded"] = [poly for _d, poly in items]
            hp = S.hull([(q.x(), q.y()) for _d, poly in items for q in poly])
            info["hull"] = QPolygonF([QPointF(x, y) for x, y in hp])
        self._solids[("net", o["id"])] = info
        return info

    def solid_edges(self, o):
        """[(i, j, 보이는지, QLineF)] - 길이 표시·점 잡기를 할 수 있는 모서리 (다면체만)"""
        info = self.solid(o)
        if S.is_curved(o) or info["a"]["whole"] is None:
            return []
        P = info["P"]
        return [(i, j, v, QLineF(P[i], P[j])) for i, j, v in info["a"]["whole"]["edges"]
                if i < len(P) and j < len(P)]

    def solid_face_at(self, o, wp, back=False):
        """화면 위치의 면 이름 (앞쪽 면 우선, back=True 이면 뒤쪽 면)"""
        info = self.solid(o)
        for g, front, poly in info["faces"]:
            if front != (not back):
                continue
            if poly.containsPoint(wp, Qt.OddEvenFill):
                return g
        return None

    # ---- 같은 길이 눈금
    def tick_path(self, o):
        seg = self.doc.objects.get(o["seg"])
        if not seg:
            return None
        A, B = self.P(seg["a"]), self.P(seg["b"])
        t = norm(B - A)
        if length(t) < 0.5:
            return None
        n = perp(t)
        mid = (A + B) * 0.5
        k = max(1, min(3, int(o.get("count", 1))))
        size = float(o.get("size", 9))
        path = QPainterPath()
        if o.get("mark") == "par":          # 평행 표시: >, >>, >>>
            if o.get("flip"):
                t = t * -1
            for i in range(k):
                c = mid + t * ((i - (k - 1) / 2) * max(4.0, size * 0.55))
                tip = c + t * (size * 0.3)
                path.moveTo(c - t * (size * 0.3) + n * (size * 0.5))
                path.lineTo(tip)
                path.lineTo(c - t * (size * 0.3) - n * (size * 0.5))
            return path
        for i in range(k):
            c = mid + t * ((i - (k - 1) / 2) * 4.5)
            path.moveTo(c - n * (size / 2))
            path.lineTo(c + n * (size / 2))
        return path

    # ---- 글상자 / 측정값
    def text_rect(self, o):
        w, h = self.tsize(o.get("text", ""), o["font"])
        return QRectF(o["x"], o["y"], w, h)

    def measure_rect(self, o):
        w, h = self.tsize(M.measure_text(self.doc, o), o["font"])
        return QRectF(o["x"], o["y"], w, h)


# ---------------------------------------------------------------- 그리기
class Renderer:
    def __init__(self, doc, geo, selection=(), export=False, only=None):
        self.doc, self.geo = doc, geo
        self.sel = set(selection)
        self.export = export
        self.only = only          # 내보내기: 이 번호들만 그림
        self.text_bounds = QRectF()

    def draw(self, p):
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        objs = [o for o in self.doc.objects.values() if not o.get("hidden")
                and (self.only is None or o["id"] in self.only) and o["id"] not in self.geo.undef]
        groups = {}
        for o in objs:
            groups.setdefault(o["type"], []).append(o)
        g = lambda t: groups.get(t, [])
        for o in g("axes"):
            self.draw_axes(p, o)
        for o in g("graph"):
            self.draw_graph(p, o)
        for o in g("polygon"):
            self.draw_polygon(p, o)
        for o in g("circle"):
            self.draw_circle(p, o)
        for o in g("arc"):
            self.draw_arc(p, o)
        if self.doc.settings.get("construction_traces", True):
            for o in g("trace"):
                path = self.geo.trace_path(o)
                p.setBrush(Qt.NoBrush)
                if o["id"] in self.sel:
                    p.setPen(qpen(o["style"], 6, HALO))
                    p.drawPath(path)
                p.setPen(qpen(o["style"]))
                p.drawPath(path)
        for o in g("solid"):
            self.draw_solid(p, o)
        for o in g("net"):
            self.draw_net(p, o)
        angle_info = {}
        for o in g("angle"):
            info = self.geo.angle(o)
            angle_info[o["id"]] = info
            if info and o.get("alpha", 0) > 0:
                p.setPen(Qt.NoPen)
                p.setBrush(alpha_color(o.get("fill", "#f5a623"), o["alpha"]))
                p.drawPath(info["fill"])
        for o in g("segment"):
            self.draw_segment(p, o)
        for o in g("tick"):
            path = self.geo.tick_path(o)
            if path is None:
                continue
            p.setBrush(Qt.NoBrush)
            if o["id"] in self.sel:
                p.setPen(qpen(o["style"], 6, HALO))
                p.drawPath(path)
            p.setPen(qpen(o["style"]))
            p.drawPath(path)
        for o in g("brace"):
            self.draw_brace(p, o)
        for o in g("angle"):
            self.draw_angle(p, o, angle_info.get(o["id"]))
        for o in g("point"):
            self.draw_point(p, o)
        for o in g("point"):
            r = self.geo.point_label(o["id"])
            if r:
                self.draw_label(p, r, self.geo.label_text(o), o["font"], o.get("text_color", "#000"),
                                o["id"] in self.sel)
        for o in g("solid"):
            info = self.geo.solid(o)
            for _k, rect, name in info["labels"]:
                self.draw_label(p, rect, name, o["font"], o.get("text_color", "#000"), False)
            if info.get("sec_label"):
                rect, name = info["sec_label"]
                self.draw_label(p, rect, name, o["font"], o.get("text_color", "#000"), False)
        for o in g("text"):
            self.draw_label(p, self.geo.text_rect(o), o.get("text", ""), o["font"],
                            o.get("text_color", "#000"), o["id"] in self.sel, Qt.AlignLeft | Qt.AlignTop)
        for o in g("measure"):
            self.draw_label(p, self.geo.measure_rect(o), M.measure_text(self.doc, o), o["font"],
                            o.get("text_color", "#000"), o["id"] in self.sel, Qt.AlignLeft | Qt.AlignTop)

    # ---- 각 개체
    def draw_axes(self, p, o):
        from graphs import nice
        a = self.geo.axes(o)
        R, O, u = a["rect"], a["O"], a["u"]
        step = max(float(o.get("step", 1)), 1e-6)
        sel = o["id"] in self.sel
        if sel:
            p.setPen(QPen(HALO, 1.5, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRect(R.adjusted(-6, -6, 6, 6))
        ks = lambda lo, hi: [k * step for k in range(int(math.ceil(lo / step - 1e-9)), int(math.floor(hi / step + 1e-9)) + 1)]
        if o.get("grid", True):
            p.setPen(qpen(o.get("grid_style", {"width": 0.6, "color": "#c9d4e2"})))
            for x in ks(a["x0"], a["x1"]):
                p.drawLine(a["to"](x, a["y0"]), a["to"](x, a["y1"]))
            for y in ks(a["y0"], a["y1"]):
                p.drawLine(a["to"](a["x0"], y), a["to"](a["x1"], y))
        st = o["style"]
        p.setPen(qpen(st))
        ext = 0.45 * u if o.get("arrows", True) else 0
        xa = 0 if a["y0"] <= 0 <= a["y1"] else a["y0"]
        ya = 0 if a["x0"] <= 0 <= a["x1"] else a["x0"]
        X0, X1 = a["to"](a["x0"], xa), a["to"](a["x1"], xa) + QPointF(ext, 0)
        Y0, Y1 = a["to"](ya, a["y0"]), a["to"](ya, a["y1"]) + QPointF(0, -ext)
        p.drawLine(X0, X1)
        p.drawLine(Y0, Y1)
        if o.get("arrows", True):
            h = 4 + float(st.get("width", 1.3)) * 2
            p.setBrush(QColor(st.get("color", "#000")))
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF([X1 + QPointF(2, 0), X1 + QPointF(-h, -h * 0.45), X1 + QPointF(-h, h * 0.45)]))
            p.drawPolygon(QPolygonF([Y1 + QPointF(0, -2), Y1 + QPointF(-h * 0.45, h), Y1 + QPointF(h * 0.45, h)]))
            p.setBrush(Qt.NoBrush)
        p.setPen(qpen(st))
        t = 3.0
        for x in ks(a["x0"], a["x1"]):
            if abs(x) > 1e-9:
                P = a["to"](x, xa)
                p.drawLine(P + QPointF(0, -t), P + QPointF(0, t))
        for y in ks(a["y0"], a["y1"]):
            if abs(y) > 1e-9:
                P = a["to"](ya, y)
                p.drawLine(P + QPointF(-t, 0), P + QPointF(t, 0))
        fd, col = o["font"], o.get("text_color", "#000")
        if o.get("numbers", True):
            for x in ks(a["x0"], a["x1"]):
                if abs(x) < 1e-9:
                    continue
                s = nice(x).replace("-", "−")
                w, th = self.geo.tsize(s, fd)
                P = a["to"](x, xa)
                self.draw_label(p, QRectF(P.x() - w / 2, P.y() + 4, w, th), s, fd, col, False)
            for y in ks(a["y0"], a["y1"]):
                if abs(y) < 1e-9:
                    continue
                s = nice(y).replace("-", "−")
                w, th = self.geo.tsize(s, fd)
                P = a["to"](ya, y)
                self.draw_label(p, QRectF(P.x() - w - 5, P.y() - th / 2, w, th), s, fd, col, False)
        if o.get("show_o", True) and xa == 0 and ya == 0:
            w, th = self.geo.tsize("O", fd)
            self.draw_label(p, QRectF(O.x() - w - 4, O.y() + 3, w, th), "O", fd, col, False)
        for s, P, dx, dy in ((o.get("xlabel", "x"), X1, 4, 2), (o.get("ylabel", "y"), Y1, 6, -2)):
            if s:
                w, th = self.geo.tsize(s, fd)
                r = QRectF(P.x() + dx, P.y() + dy, w, th) if s == o.get("xlabel", "x") else QRectF(P.x() + dx, P.y() - th / 2 + dy, w, th)
                self.draw_label(p, r, s, fd, col, False)

    def draw_graph(self, p, o):
        import graphs as GR
        info = self.geo.graph_paths(o)
        if not info:
            return
        p.save()
        p.setClipRect(info["rect"].adjusted(-1, -1, 1, 1))
        p.setBrush(Qt.NoBrush)
        if o["id"] in self.sel:
            p.setPen(qpen(o["style"], 6, HALO))
            p.drawPath(info["path"])
        p.setPen(qpen(o["style"]))
        p.drawPath(info["path"])
        p.restore()
        if o.get("show_eq", True) and info["end"] is not None:
            s = GR.label(o)
            w, th = self.geo.tsize(s, o["font"])
            E = info["end"] + QPointF(o.get("label_dx", 0.0), o.get("label_dy", 0.0))
            R = info["rect"]
            x = min(max(E.x() - w - 4, R.left() + 2), R.right() - w - 2)
            y = min(max(E.y() - th - 2, R.top() + 2), R.bottom() - th - 2)
            self.draw_label(p, QRectF(x, y, w, th), s, o["font"], o.get("text_color", "#000"), o["id"] in self.sel)

    def draw_label(self, p, rect, text, fd, color, selected, align=Qt.AlignCenter):
        if not text:
            return
        self.text_bounds = self.text_bounds.united(rect)
        if selected:
            p.setPen(QPen(SEL_EDGE, 1, Qt.DashLine))
            p.setBrush(QColor(40, 140, 255, 30))
            p.drawRect(rect.adjusted(-2, -1, 2, 1))
        draw_rich(p, rect, text, fd, color, align, bool(self.doc.settings.get("math_style")))

    def draw_polygon(self, p, o):
        ids = [i for i in o["pts"] if i in self.doc.objects]
        if len(ids) < 3:
            return
        poly = QPolygonF([self.geo.P(i) for i in ids])
        if o.get("alpha", 0) > 0:
            p.setPen(Qt.NoPen)
            p.setBrush(alpha_color(o.get("fill", "#4a90e2"), o["alpha"]))
            p.drawPolygon(poly)
        if o["id"] in self.sel:
            p.setBrush(QColor(40, 140, 255, 25))
            pen = QPen(HALO, 8)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.drawPolygon(poly)

    def draw_circle(self, p, o):
        C = self.geo.P(o["c"])
        R = length(self.geo.P(o["p"]) - C)
        if R < 0.5:
            return
        if o.get("alpha", 0) > 0:
            p.setPen(Qt.NoPen)
            p.setBrush(alpha_color(o.get("fill", "#4a90e2"), o["alpha"]))
            p.drawEllipse(C, R, R)
        p.setBrush(Qt.NoBrush)
        if o["id"] in self.sel:
            p.setPen(qpen(o["style"], 7, HALO))
            p.drawEllipse(C, R, R)
        p.setPen(qpen(o["style"]))
        p.drawEllipse(C, R, R)

    def draw_arc(self, p, o):
        info = self.geo.arcs(o)
        if not info:
            return
        if o.get("alpha", 0) > 0:
            p.setPen(Qt.NoPen)
            p.setBrush(alpha_color(o.get("fill", "#4a90e2"), o["alpha"]))
            p.drawPath(info["fill"])
        p.setBrush(Qt.NoBrush)
        if o["id"] in self.sel:
            p.setPen(qpen(o["style"], 7, HALO))
            p.drawPath(info["path"])
        p.setPen(qpen(o["style"]))
        p.drawPath(info["path"])

    def draw_solid(self, p, o):
        info = self.geo.solid(o)
        if len(info.get("pdraw", [])) > 1:
            self.draw_solid_pieces(p, o, info)
            return
        sel = o["id"] in self.sel
        if o.get("alpha", 0) > 0 and info["hull"] is not None:
            p.setPen(Qt.NoPen)
            p.setBrush(alpha_color(o.get("fill", "#4a90e2"), o["alpha"]))
            if info["outline"] is not None:
                p.drawPath(info["outline"])
            else:
                p.drawPolygon(info["hull"])
        for path, col, al in info["fills"]:
            p.setPen(Qt.NoPen)
            p.setBrush(alpha_color(col, al))
            p.drawPath(path)
        p.setBrush(Qt.NoBrush)
        hs = o.get("hid_style", o["style"])
        show_h = o.get("show_hidden", True)
        inner = o.get("host") is not None and o.get("inner_line") in ("dash", "hide")
        if sel:
            p.setPen(qpen(o["style"], 7, HALO))
            p.drawPath(info["vis"])
            for path, st in info.get("custom", []):
                if st["dash"] == "solid":
                    p.drawPath(path)
            if info["outline"] is not None:
                p.drawPath(info["outline"])
        if show_h and not info["hid"].isEmpty():
            p.setPen(qpen(hs))
            p.drawPath(info["hid"])
        for path, st in info.get("custom", []):
            p.setPen(qpen(st))
            p.drawPath(path)
        p.setPen(qpen(o["style"]))
        p.drawPath(info["vis"])
        if info["outline"] is not None:
            if inner:
                p.setPen(qpen(hs))
            if o.get("inner_line") != "hide" or o.get("host") is None:
                p.drawPath(info["outline"])
        dot_c = QColor(o["style"].get("color", "#000"))
        r = max(2.0, float(o["style"].get("width", 2)) * 1.4)
        p.setPen(Qt.NoPen)
        p.setBrush(dot_c)
        if o.get("show_dots"):
            mesh = info["a"]["mesh"]
            for k, vi in enumerate(mesh.named):
                if k not in mesh.centers:
                    p.drawEllipse(info["P"][vi], r, r)
        for c in info["center_pts"]:
            p.drawEllipse(c, r, r)

    def draw_net(self, p, o):
        info = self.geo.net(o)
        if not info:
            return
        sel = o["id"] in self.sel
        st = o["style"]
        if info.get("folded") is not None:
            for poly in info["folded"]:
                p.setPen(qpen(st))
                p.setBrush(alpha_color(o.get("fill", "#4a90e2"), max(25, o.get("alpha", 0))))
                p.drawPolygon(poly)
            return
        if o.get("alpha", 0) > 0:
            p.setPen(Qt.NoPen)
            p.setBrush(alpha_color(o.get("fill", "#4a90e2"), o["alpha"]))
            for path in info["fills"]:
                p.drawPath(path)
        p.setBrush(Qt.NoBrush)
        if sel:
            p.setPen(qpen(st, 6, HALO))
            p.drawPath(info["solid_path"])
            p.drawPath(info["fold_path"])
        p.setPen(qpen(st))
        p.drawPath(info["solid_path"])
        p.setPen(qpen(dict(st, dash=o.get("fold_dash", "dash"))))
        p.drawPath(info["fold_path"])
        for rect, name in info["labels"]:
            self.draw_label(p, rect, name, o["font"], o.get("text_color", "#000"), False)

    def draw_solid_pieces(self, p, o, info):
        """잘라서 벌린 두 조각: 먼 조각부터 그리고, 가까운 조각이 덮도록"""
        sel = o["id"] in self.sel
        hs = o.get("hid_style", o["style"])
        for d_ in info["pdraw"]:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("white"))
            p.drawPolygon(d_["hull"])
            if o.get("alpha", 0) > 0:
                p.setBrush(alpha_color(o.get("fill", "#4a90e2"), o["alpha"]))
                p.drawPolygon(d_["hull"])
            for path, col, al in d_["fills_front"]:     # 조각은 불투명하게: 앞쪽 면 색만
                p.setBrush(alpha_color(col, al))
                p.drawPath(path)
            p.setBrush(Qt.NoBrush)
            if sel:
                p.setPen(qpen(o["style"], 7, HALO))
                p.drawPath(d_["vis"])
            if o.get("show_hidden", True) and not d_["hid"].isEmpty():
                p.setPen(qpen(hs))
                p.drawPath(d_["hid"])
            for path, st in d_.get("custom", []):
                p.setPen(qpen(st))
                p.drawPath(path)
            p.setPen(qpen(o["style"]))
            p.drawPath(d_["vis"])

    def area(self):
        """내보낼 때 직선·반직선을 자를 범위: 보이는 점·도형을 둘러싼 사각형 + 여유"""
        if getattr(self, "_area", None) is None:
            xs, ys = [], []
            for o in self.doc.objects.values():
                if o.get("hidden") or o["id"] in self.geo.undef:
                    continue
                if self.only is not None and o["id"] not in self.only:
                    continue
                if o["type"] == "point" and not o.get("helper"):
                    xs.append(o["x"])
                    ys.append(o["y"])
                elif o["type"] == "axes":
                    br = self.geo.axes(o)["rect"]
                    xs += [br.left(), br.right()]
                    ys += [br.top(), br.bottom()]
                elif o["type"] == "solid":
                    br = self.geo.solid(o)["hull"].boundingRect()
                    xs += [br.left(), br.right()]
                    ys += [br.top(), br.bottom()]
            if not xs:
                self._area = QRectF(-200, -200, 400, 400)
            else:
                m = M.GRID * 1.2
                self._area = QRectF(min(xs) - m, min(ys) - m, max(xs) - min(xs) + 2 * m, max(ys) - min(ys) + 2 * m)
        return self._area

    def clip_to_area(self, A, B, kind):
        R = self.area()
        d = B - A
        lo, hi = (-1e9 if kind == "line" else 0.0), 1e9
        for p_, q_ in ((-d.x(), A.x() - R.left()), (d.x(), R.right() - A.x()),
                       (-d.y(), A.y() - R.top()), (d.y(), R.bottom() - A.y())):
            if abs(p_) < 1e-12:
                if q_ < 0:
                    return None
                continue
            t = q_ / p_
            if p_ < 0:
                lo = max(lo, t)
            else:
                hi = min(hi, t)
        if lo > hi:
            return None
        return QLineF(A + d * lo, A + d * hi)

    def draw_segment(self, p, o):
        if self.export and o.get("kind") in ("line", "ray"):
            A, B = self.geo.P(o["a"]), self.geo.P(o["b"])
            line = self.clip_to_area(A, B, o["kind"])
            if line is None:
                return
        else:
            line = self.geo.seg_line(o)
        st = o["style"]
        if o.get("auto3d", True) and st.get("dash", "solid") == "solid" and self.geo.seg_hidden3d(o):
            st = dict(st, dash="dash")      # 입체 안을 지나거나 뒤쪽 면 위의 선 → 점선
        if o["id"] in self.sel:
            p.setPen(qpen(o["style"], 7, HALO))
            p.drawLine(line)
        p.setPen(qpen(st))
        p.drawLine(line)

    def draw_brace(self, p, o):
        info = self.geo.brace(o)
        if not info:
            return
        p.setBrush(Qt.NoBrush)
        if o["id"] in self.sel:
            p.setPen(qpen(o["style"], 6, HALO))
            p.drawPath(info["path"])
        p.setPen(qpen(o["style"]))
        p.drawPath(info["path"])
        if info["rect"]:
            self.draw_label(p, info["rect"], info["text"], o["font"], o.get("text_color", "#000"),
                            o["id"] in self.sel)

    def draw_angle(self, p, o, info):
        if not info:
            return
        p.setBrush(Qt.NoBrush)
        if o["id"] in self.sel:
            p.setPen(qpen(o["style"], 6, HALO))
            p.drawPath(info["stroke"])
        p.setPen(qpen(o["style"]))
        p.drawPath(info["stroke"])
        if info["leader"]:
            a, b = info["leader"]
            col = QColor(o.get("text_color", "#000"))
            head = float(o.get("arrow_size", 7.0))
            pen = QPen(col, max(0.8, head / 6))
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            if o.get("leader_shape") == "curve":
                d0 = b - a
                n0 = perp(d0)
                ctl = (a + b) * 0.5 + n0 * 0.35
                if length(ctl - info["V"]) < length((a + b) * 0.5 - n0 * 0.35 - info["V"]):
                    ctl = (a + b) * 0.5 - n0 * 0.35
                d = norm(b - ctl)
                end = b - d * (head * 0.8)
                path = QPainterPath(a)
                path.quadTo(ctl, end)
                p.drawPath(path)
            else:
                d = norm(b - a)
                p.drawLine(QLineF(a, b - d * (head * 0.8)))
            n = perp(d)
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawPolygon(QPolygonF([b, b - d * head + n * (head * 0.4), b - d * head - n * (head * 0.4)]))
        if info["rect"]:
            self.draw_label(p, info["rect"], info["text"], o["font"], o.get("text_color", "#000"),
                            o["id"] in self.sel)

    def draw_point(self, p, o):
        P = QPointF(o["x"], o["y"])
        r = float(o.get("size", 3.5))
        if o["id"] in self.sel:
            p.setPen(Qt.NoPen)
            p.setBrush(HALO)
            p.drawEllipse(P, r + 5, r + 5)
        if o.get("helper") and o["id"] not in self.sel:
            return
        if o.get("show_dot", True):
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(o.get("color", "#000")))
            p.drawEllipse(P, r, r)
        elif not self.export:
            # 점을 숨겨도 편집할 수 있도록 화면에는 희미한 표시
            p.setPen(QPen(QColor(150, 150, 150, 120), 1, Qt.DotLine))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(P, 3, 3)
