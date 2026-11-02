"""도형그리기 - 데이터 모델과 계산

모든 개체는 dict 로 저장합니다. (저장/되돌리기가 쉬움)
좌표 단위는 화면 픽셀(96dpi 기준)이며, GRID 픽셀 = 1 cm 입니다.
"""
import copy
import json
import math

import solid as S

GRID = 96 / 2.54          # 1 cm = 37.8 px (96 dpi 기준이라 그림을 붙여넣으면 실제 크기와 같음)
FILE_APP = "dohyeong"
FILE_VERSION = 1
FILE_EXT = "dhg"

DASH_NAMES = [("solid", "실선"), ("dash", "파선"), ("dot", "점선"), ("dashdot", "일점쇄선")]
REF_KEYS = ("a", "b", "v", "c", "p", "q", "seg", "target", "solid")

TYPE_NAMES = {
    "point": "점", "segment": "선", "polygon": "다각형", "circle": "원",
    "brace": "길이 표시", "angle": "각 표시", "tick": "같은 길이 눈금",
    "text": "글상자", "measure": "측정값", "solid": "입체도형", "arc": "호·부채꼴", "trace": "작도 흔적", "net": "전개도",
}


# ---------------------------------------------------------------- 기본값
def default_font():
    return {"family": "CMU Serif", "size": 14, "bold": False, "italic": False}


def default_settings():
    return {
        "unit": "cm",
        "decimals": 1,
        "angle_decimals": 0,
        "show_grid": True,
        "snap": True,
        "font": default_font(),
        "line_width": 2.0,
        "export_scale": 3,
        "png_transparent": True,
        "length_shape": "arc",
        "length_dash": "dash",
        "math_style": True,
        "construction_traces": True,   # 작도할 때 컴퍼스 흔적(호) 함께 그리기      # 교과서 스타일: x·α 기울임, ° 위첨자 동그라미
        "angle_radius": 22.0,
        "mark_width": 1.5,        # 중괄호·각 표시·눈금 선 굵기
    }


def new_style(doc=None, width=None, dash="solid", color="#000000"):
    if width is None:
        width = doc.settings.get("line_width", 2.0) if doc else 2.0
    return {"width": float(width), "dash": dash, "color": color}


# ---------------------------------------------------------------- 참조
def _is_id(v):
    return isinstance(v, int) and not isinstance(v, bool)


DEP_KEYS = ("a", "b", "v", "p", "q", "c", "base", "o1", "o2", "obj")


def obj_refs(o):
    if o["type"] == "polygon":
        return list(o["pts"])
    out = [o[k] for k in REF_KEYS if k in o and _is_id(o[k])]
    for dk in ("dep", "dep3"):        # 작도로 생긴 점이 기대는 개체
        dd = o.get(dk)
        if dd:
            out += [dd[k] for k in DEP_KEYS if k in dd and _is_id(dd[k])]
    return out


def remap_refs(o, m):
    if o["type"] == "polygon":
        o["pts"] = [m.get(i, i) for i in o["pts"]]
    for k in REF_KEYS:
        if k in o and _is_id(o[k]):
            o[k] = m.get(o[k], o[k])
    for dk in ("dep", "dep3"):
        dd = o.get(dk)
        if dd:
            for k in DEP_KEYS:
                if k in dd and _is_id(dd[k]):
                    dd[k] = m.get(dd[k], dd[k])


# ---------------------------------------------------------------- 문서
class Document:
    def __init__(self, settings=None):
        self.objects = {}
        self.next_id = 1
        # 탭들이 같은 설정을 함께 씁니다 (같은 dict 를 공유)
        self.settings = settings if settings is not None else default_settings()

    # 기본 조작
    def add(self, o):
        o["id"] = self.next_id
        self.next_id += 1
        o.setdefault("hidden", False)
        self.objects[o["id"]] = o
        return o["id"]

    def get(self, i):
        return self.objects.get(i)

    def items(self, *types):
        return [o for o in self.objects.values() if not types or o["type"] in types]

    def xy(self, pid):
        o = self.objects[pid]
        return o["x"], o["y"]

    def dependents(self, ids):
        """ids 와 그것에 기대는 모든 개체"""
        result = set(i for i in ids if i in self.objects)
        changed = True
        while changed:
            changed = False
            for o in self.objects.values():
                if o["id"] not in result and any(r in result for r in obj_refs(o)):
                    result.add(o["id"])
                    changed = True
        return result

    def requirements(self, ids):
        """ids 와 그것이 필요로 하는 모든 개체"""
        result, stack = set(), list(ids)
        while stack:
            i = stack.pop()
            if i in result or i not in self.objects:
                continue
            result.add(i)
            stack.extend(obj_refs(self.objects[i]))
        return result

    def point_ids_of(self, ids):
        return {i for i in self.requirements(ids) if self.objects[i]["type"] == "point"}

    def delete(self, ids):
        for i in self.dependents(ids):
            self.objects.pop(i, None)

    def next_label(self):
        used = {o.get("label") for o in self.items("point")}
        for so in self.items("solid"):
            used |= set(so.get("labels", []))
        for n in range(0, 1000):
            for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                lab = ch if n == 0 else f"{ch}{n}"
                if lab not in used:
                    return lab
        return "?"

    def find_segment(self, a, b):
        for o in self.items("segment"):
            if {o["a"], o["b"]} == {a, b}:
                return o["id"]
        return None

    def label(self, pid):
        o = self.objects.get(pid)
        if not o:
            return ""
        if o.get("label") or o.get("solid") is None or o.get("sv") is None:
            return o.get("label", "")
        so = self.objects.get(o["solid"])     # 입체 꼭짓점에 붙은 점은 입체의 꼭짓점 이름
        if not so:
            return ""
        mesh = S.build(so["kind"], so["params"])
        if o["sv"] in mesh.named:
            k = mesh.named.index(o["sv"])
            labs = so.get("labels", [])
            return labs[k] if k < len(labs) else ""
        return ""

    # 저장/불러오기
    def dump(self):
        return json.dumps({
            "app": FILE_APP, "version": FILE_VERSION, "next_id": self.next_id,
            "settings": self.settings, "objects": list(self.objects.values()),
        }, ensure_ascii=False)

    def load(self, s):
        d = json.loads(s)
        if d.get("app") != FILE_APP:
            raise ValueError("도형그리기 파일이 아닙니다.")
        st = default_settings()
        st.update(d.get("settings", {}))
        self.settings.clear()
        self.settings.update(st)
        self.objects = {}
        for o in d.get("objects", []):
            self.objects[int(o["id"])] = o
        self.next_id = max([d.get("next_id", 1)] + [i + 1 for i in self.objects])


# ---------------------------------------------------------------- 여러 탭 파일
def dump_pages(pages, settings):
    """pages: [(이름, Document)]"""
    return json.dumps({
        "app": FILE_APP, "version": 2, "settings": settings,
        "pages": [{"name": n, "next_id": d.next_id, "objects": list(d.objects.values())} for n, d in pages],
    }, ensure_ascii=False)


def load_pages(s):
    """→ (설정, [(이름, Document)])  (탭 없던 예전 파일도 열림)"""
    d = json.loads(s)
    if d.get("app") != FILE_APP:
        raise ValueError("도형그리기 파일이 아닙니다.")
    st = default_settings()
    st.update(d.get("settings", {}))
    raw = d.get("pages") or [{"name": "1번", "next_id": d.get("next_id", 1), "objects": d.get("objects", [])}]
    pages = []
    for k, pg in enumerate(raw):
        doc = Document(st)
        for o in pg.get("objects", []):
            doc.objects[int(o["id"])] = o
        doc.next_id = max([pg.get("next_id", 1)] + [i + 1 for i in doc.objects])
        pages.append((pg.get("name") or f"{k + 1}번", doc))
    return st, pages


# ---------------------------------------------------------------- 만들기
def make_point(doc, x, y, label=None):
    return doc.add({
        "type": "point", "x": float(x), "y": float(y),
        "label": doc.next_label() if label is None else label,
        "show_label": True, "label_auto": True, "label_dx": 0.0, "label_dy": 0.0,
        "font": copy.deepcopy(doc.settings["font"]), "text_color": "#000000",
        "size": 3.5, "color": "#000000", "show_dot": True,
    })


def make_segment(doc, a, b, kind="segment"):
    if kind == "segment":
        found = doc.find_segment(a, b)
        if found and doc.objects[found].get("kind") == "segment":
            return found
    return doc.add({"type": "segment", "kind": kind, "a": a, "b": b, "style": new_style(doc)})


def make_polygon(doc, pts):
    pid = doc.add({"type": "polygon", "pts": list(pts), "fill": "#4a90e2", "alpha": 0})
    for k in range(len(pts)):
        make_segment(doc, pts[k], pts[(k + 1) % len(pts)])
    return pid


def make_circle(doc, c, p):
    return doc.add({"type": "circle", "c": c, "p": p, "style": new_style(doc),
                    "fill": "#4a90e2", "alpha": 0})


def make_arc(doc, c, p, q):
    """중심 c, 시작점 p, 끝 방향 q 인 호 (시계 반대 방향)"""
    return doc.add({"type": "arc", "c": c, "p": p, "q": q, "sector": False, "reverse": False,
                    "style": new_style(doc), "fill": "#4a90e2", "alpha": 0})


def arc_radius(doc, o):
    """호의 반지름(cm)"""
    if o.get("r") is not None:
        return float(o["r"])
    return dist_units(doc, o["c"], o["p"])


def arc_angles(doc, o):
    """(시작각, 크기) 도 단위 - 수학 방향"""
    if o.get("r") is not None:        # 컴퍼스로 그린 호: 시작각·크기를 그대로 저장
        s, span = float(o.get("a0", 0)), float(o.get("span", 90))
        if o.get("reverse") and span < 360:
            s, span = s + span, 360.0 - span
        return s, span
    cx, cy = doc.xy(o["c"])
    px, py = doc.xy(o["p"])
    qx, qy = doc.xy(o["q"])
    s = math.degrees(math.atan2(-(py - cy), px - cx))
    e = math.degrees(math.atan2(-(qy - cy), qx - cx))
    span = (e - s) % 360.0
    if o.get("reverse"):
        s, span = e, 360.0 - span
    return s, span


def make_brace(doc, a, b, side=1):
    f = copy.deepcopy(doc.settings["font"])
    return doc.add({
        "type": "brace", "a": a, "b": b, "side": side, "height": 12.0,
        "shape": doc.settings.get("length_shape", "arc"), "arc_height": None,
        "style": new_style(doc, width=doc.settings.get("mark_width", 1.5),
                           dash=doc.settings.get("length_dash", "dash")),
        "text_mode": "auto", "text": "", "font": f, "text_color": "#000000",
        "label_dx": 0.0, "label_dy": 0.0,
    })


def make_solid_brace(doc, sid, i, j):
    """입체도형 모서리(꼭짓점 번호 i, j)의 길이 표시"""
    o = {
        "type": "brace", "solid": sid, "sv": [int(i), int(j)], "side": 1, "height": 12.0,
        "shape": doc.settings.get("length_shape", "arc"), "arc_height": None,
        "style": new_style(doc, width=doc.settings.get("mark_width", 1.5),
                           dash=doc.settings.get("length_dash", "dash")),
        "text_mode": "auto", "text": "", "font": copy.deepcopy(doc.settings["font"]),
        "text_color": "#000000", "label_dx": 0.0, "label_dy": 0.0,
    }
    return doc.add(o)


def make_solid(doc, kind, x, y, params=None, tz=0.0, tx=0.0):
    return doc.add(solid_dict(doc, kind, x, y, params, tz, tx))


def solid_dict(doc, kind, x, y, params=None, tz=0.0, tx=0.0):
    p = S.default_params(kind)
    if params:
        p.update(params)
    mesh = S.build(kind, p)
    curved = S.is_curved({"kind": kind, "params": p})
    lw = doc.settings.get("line_width", 2.0)
    return ({
        "type": "solid", "kind": kind, "params": p, "x": float(x), "y": float(y),
        "view": "oblique", "yaw": 0.0 if curved else -30.0, "pitch": 20.0,
        "style": new_style(doc), "hid_style": new_style(doc, width=lw, dash="dash"),
        "show_hidden": True, "fill": "#4a90e2", "alpha": 0,
        "labels": list(mesh.names), "show_labels": not curved, "show_dots": False,
        "lab_off": {}, "font": copy.deepcopy(doc.settings["font"]), "text_color": "#000000",
        "tz": float(tz), "tx": float(tx),
    })


def solid_name(o):
    if o["kind"] == "stack":
        return "회전체" if int(o["params"].get("n", 0)) == 0 else "입체도형"
    return S.KIND_NAMES.get(o["kind"], "입체도형")


def brace_len(doc, o):
    if "solid" in o:
        so = doc.objects.get(o["solid"])
        return S.edge_length(so, *o["sv"]) if so else 0.0
    return dist_units(doc, o["a"], o["b"])


def brace_name(doc, o):
    if "solid" in o:
        so = doc.objects.get(o["solid"])
        if not so:
            return ""
        mesh = S.build(so["kind"], so["params"])
        labs = so.get("labels", [])
        out = ""
        for v in o["sv"]:
            if v in mesh.named and mesh.named.index(v) < len(labs):
                out += labs[mesh.named.index(v)]
        return out
    return doc.label(o["a"]) + doc.label(o["b"])


def make_angle(doc, a, v, b, auto_swap=True):
    o = {
        "type": "angle", "a": a, "v": v, "b": b, "radius": float(doc.settings.get("angle_radius", 22.0)),
        "arcs": 1, "reflex": False, "right_auto": True,
        "style": new_style(doc, width=doc.settings.get("mark_width", 1.5)), "fill": "#f5a623", "alpha": 0,
        "label_mode": "value", "text": "", "place": "auto",
        "leader_shape": "line", "arrow_size": 7.0,
        "font": copy.deepcopy(doc.settings["font"]), "text_color": "#000000",
        "lu": None, "lv": None,
    }
    if auto_swap:
        _, span = angle_span(doc, o)
        if span > 180:
            o["a"], o["b"] = b, a
    return doc.add(o)


def make_tick(doc, seg, count=1):
    return doc.add({"type": "tick", "seg": seg, "count": count, "size": 9.0,
                    "style": new_style(doc, width=doc.settings.get("mark_width", 1.5))})


def make_text(doc, x, y, text):
    return doc.add({"type": "text", "x": float(x), "y": float(y), "text": text,
                    "font": copy.deepcopy(doc.settings["font"]), "text_color": "#000000"})


def make_measure(doc, target, kind, x, y):
    return doc.add({"type": "measure", "target": target, "kind": kind,
                    "x": float(x), "y": float(y),
                    "font": copy.deepcopy(doc.settings["font"]), "text_color": "#1a4fa0"})


# ---------------------------------------------------------------- 계산
def mid_solid(doc, q):
    """같은 입체 위 두 점의 중점이면 그 입체 번호"""
    dep = q.get("dep") or {}
    if dep.get("t") != "mid":
        return None
    a, b = doc.objects.get(dep.get("a")), doc.objects.get(dep.get("b"))
    if a and b and a.get("solid") is not None and a.get("solid") == b.get("solid"):
        return a["solid"]
    return None


def attached_xyz(doc, q):
    """입체에 붙은 점의 3D 좌표(cm, 모델 좌표)"""
    if q.get("solid") is None and mid_solid(doc, q) is not None:
        A = attached_xyz(doc, doc.objects[q["dep"]["a"]])
        B = attached_xyz(doc, doc.objects[q["dep"]["b"]])
        if A is None or B is None:
            return None
        return tuple((A[k] + B[k]) / 2 for k in range(3))
    so = doc.objects.get(q.get("solid"))
    if not so:
        return None
    if q.get("sv") is not None:
        return S.point3d(so, sv=q["sv"])
    if q.get("edge"):
        return S.point3d(so, edge=q["edge"], t=float(q.get("t", 0.5)))
    if q.get("face") is not None:
        return S.face_point(S.build(so["kind"], so["params"]), int(q["face"]), float(q.get("fa", 0)), float(q.get("fb", 0)))
    if q.get("ring") is not None:
        return S.ring_point(S.build(so["kind"], so["params"]), int(q["ring"]), float(q.get("ang", 0)))
    d3 = q.get("dep3")
    if d3:
        P = attached_xyz(doc, doc.objects.get(d3.get("p"), {}))
        if P is None:
            return None
        if d3.get("t") == "foot_line":
            A = attached_xyz(doc, doc.objects.get(d3.get("a"), {}))
            B = attached_xyz(doc, doc.objects.get(d3.get("b"), {}))
            if A is None or B is None:
                return None
            d = [B[k] - A[k] for k in range(3)]
            dd = sum(c * c for c in d)
            if dd < 1e-12:
                return A
            t = sum((P[k] - A[k]) * d[k] for k in range(3)) / dd
            return tuple(A[k] + d[k] * t for k in range(3))
        if d3.get("t") == "foot_face":
            mesh = S.build(so["kind"], so["params"])
            f = next((f for f, g in zip(mesh.faces, mesh.groups) if g == d3.get("face")), None)
            if not f:
                return None
            n = S.newell(mesh, f)
            L = math.sqrt(sum(c * c for c in n)) or 1
            n = [c / L for c in n]
            p0 = mesh.v[f[0]]
            dist = sum((P[k] - p0[k]) * n[k] for k in range(3))
            return tuple(P[k] - dist * n[k] for k in range(3))
    return None


def same_solid_xyz(doc, ids):
    """점들이 모두 같은 입체에 붙어 있으면 3D 좌표 목록, 아니면 None"""
    pts = [doc.objects.get(i) for i in ids]
    if not all(pts) or any(p.get("solid") is None for p in pts):
        return None
    if len({p["solid"] for p in pts}) != 1:
        return None
    xyz = [attached_xyz(doc, p) for p in pts]
    return None if any(v is None for v in xyz) else xyz


def dist_units(doc, a, b):
    """두 점 사이 길이(cm). 같은 입체 위의 점이면 화면이 아니라 실제 3D 길이"""
    xyz = same_solid_xyz(doc, [a, b])
    if xyz:
        return math.dist(xyz[0], xyz[1])
    (x1, y1), (x2, y2) = doc.xy(a), doc.xy(b)
    return math.hypot(x2 - x1, y2 - y1) / GRID


def angle_value(doc, o):
    """각의 크기. 같은 입체 위의 세 점이면 실제 3D 각"""
    xyz = same_solid_xyz(doc, [o["a"], o["v"], o["b"]])
    if xyz:
        A, V, B = xyz
        u = [A[k] - V[k] for k in range(3)]
        w = [B[k] - V[k] for k in range(3)]
        lu = math.sqrt(sum(c * c for c in u))
        lw = math.sqrt(sum(c * c for c in w))
        if lu > 1e-9 and lw > 1e-9:
            c = sum(u[k] * w[k] for k in range(3)) / (lu * lw)
            ang = math.degrees(math.acos(max(-1, min(1, c))))
            return 360 - ang if o.get("reflex") else ang
    return angle_span(doc, o)[1]


def make_attached_point(doc, sid, sv=None, edge=None, t=0.5, face=None, fa=0.0, fb=0.0, ring=None, ang=0.0):
    """입체의 꼭짓점(sv), 모서리(edge) 위, 면(face) 위, 원 둘레(ring) 위 점"""
    for q in doc.items("point"):
        if q.get("solid") == sid:
            if sv is not None and q.get("sv") == sv:
                return q["id"]
    pid = make_point(doc, 0, 0, label="" if sv is not None else None)
    o = doc.objects[pid]
    o["solid"] = sid
    if sv is not None:
        o["sv"] = int(sv)
        o["show_dot"] = False
        o["show_label"] = False
    elif face is not None:
        o["face"], o["fa"], o["fb"] = int(face), float(fa), float(fb)
    elif ring is not None:
        o["ring"], o["ang"] = int(ring), float(ang)
    else:
        o["edge"] = [int(edge[0]), int(edge[1])]
        o["t"] = float(t)
    return pid


def make_dep_point(doc, dep, label=None, show=True):
    """작도로 생기는 점 (원래 점을 움직이면 따라 움직임)"""
    pid = make_point(doc, 0, 0, label=label if label is not None else (doc.next_label() if show else ""))
    o = doc.objects[pid]
    o["dep"] = dep
    if not show:
        o["show_dot"] = False
        o["show_label"] = False
        o["helper"] = True
    return pid


def make_trace(doc, kind, **refs):
    d = {"type": "trace", "kind": kind, "style": new_style(doc, width=1.0, color="#555555")}
    d.update(refs)
    return doc.add(d)


def make_net(doc, sid, x, y):
    kind = doc.objects[sid]["kind"]
    return doc.add({"type": "net", "solid": sid, "x": float(x), "y": float(y),
                    "layout": "strip" if kind == "prism" else "flower",
                    "fold": 0.0, "show_labels": True, "fold_dash": "dash",
                    "style": new_style(doc), "fill": "#4a90e2", "alpha": 0,
                    "font": copy.deepcopy(doc.settings["font"]), "text_color": "#000000"})


def default_cut(mode):
    return {"mode": mode, "pts": [], "tilt": 0.0, "turn": 0.0, "pos": 0.0, "gap": 0.0,
            "show": "both", "color": "#f5a623", "alpha": 45, "show_name": False}


def angle_span(doc, o):
    """(시작각, 크기)  - 도 단위, 수학 방향(시계 반대) 기준. Qt 의 arcTo 와 같은 기준."""
    vx, vy = doc.xy(o["v"])
    ax, ay = doc.xy(o["a"])
    bx, by = doc.xy(o["b"])
    sa = math.degrees(math.atan2(-(ay - vy), ax - vx))
    sb = math.degrees(math.atan2(-(by - vy), bx - vx))
    span = (sb - sa) % 360.0
    start = sa
    if o.get("reflex"):
        start, span = sb, 360.0 - span
    return start, span


def polygon_xy(doc, poly):
    return [doc.xy(i) for i in poly["pts"] if i in doc.objects]


def signed_area(xy):
    s = 0.0
    for k in range(len(xy)):
        x1, y1 = xy[k]
        x2, y2 = xy[(k + 1) % len(xy)]
        s += x1 * y2 - x2 * y1
    return s / 2


def poly_area(doc, poly):
    return abs(signed_area(polygon_xy(doc, poly))) / GRID ** 2


def poly_perimeter(doc, poly):
    ids = [i for i in poly["pts"] if i in doc.objects]
    return sum(dist_units(doc, ids[k], ids[(k + 1) % len(ids)]) for k in range(len(ids)))


def poly_interior_angles(doc, poly):
    """[(꼭짓점 id, 내각)]"""
    ids = [i for i in poly["pts"] if i in doc.objects]
    xy = [doc.xy(i) for i in ids]
    n = len(ids)
    if n < 3:
        return []
    orient = 1 if signed_area(xy) > 0 else -1
    out = []
    for k in range(n):
        px, py = xy[k - 1]
        vx, vy = xy[k]
        nx, ny = xy[(k + 1) % n]
        e1 = (px - vx, py - vy)
        e2 = (nx - vx, ny - vy)
        l1, l2 = math.hypot(*e1), math.hypot(*e2)
        if l1 < 1e-9 or l2 < 1e-9:
            out.append((ids[k], 0.0))
            continue
        c = max(-1, min(1, (e1[0] * e2[0] + e1[1] * e2[1]) / (l1 * l2)))
        ang = math.degrees(math.acos(c))
        cross = (vx - px) * (ny - vy) - (vy - py) * (nx - vx)
        if cross * orient < 0:
            ang = 360 - ang
        out.append((ids[k], ang))
    return out


def poly_orientation(doc, poly):
    return 1 if signed_area(polygon_xy(doc, poly)) > 0 else -1


def circle_radius(doc, c):
    return dist_units(doc, c["c"], c["p"])


def fmt_num(v, d):
    return f"{v:.{int(d)}f}"


def fmt_len(doc, v):
    s = fmt_num(v, doc.settings["decimals"])
    u = doc.settings.get("unit", "")
    return f"{s} {u}" if u else s


def fmt_area(doc, v):
    s = fmt_num(v, doc.settings["decimals"])
    u = doc.settings.get("unit", "")
    return f"{s} {u}²" if u else s


def fmt_angle(doc, v):
    return fmt_num(v, doc.settings["angle_decimals"]) + "°"


def poly_name(doc, poly):
    labs = "".join(doc.label(i) for i in poly["pts"])
    n = len(poly["pts"])
    if n == 3:
        return "△" + labs
    if n == 4:
        return "□" + labs
    return "다각형 " + labs


MEASURE_KINDS = {
    "segment": [("length", "길이")],
    "polygon": [("area", "넓이"), ("perimeter", "둘레")],
    "circle": [("radius", "반지름"), ("circumference", "원주"), ("area", "넓이")],
    "angle": [("angle", "각도")],
    "brace": [("length", "길이")],
    "solid": [("volume", "부피"), ("surface", "겉넓이")],
    "arc": [("arclen", "호의 길이"), ("area", "부채꼴 넓이"), ("angle", "중심각")],
}


def nice(v, d):
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return fmt_num(v, d)


def measure_value_text(doc, o, kind):
    """측정 대상 o 의 값을 '이름 = 값' 형태로"""
    t = o["type"]
    if t == "brace":
        return f"{brace_name(doc, o)} = {fmt_len(doc, brace_len(doc, o))}"
    if t == "segment":
        return f"{doc.label(o['a'])}{doc.label(o['b'])} = {fmt_len(doc, dist_units(doc, o['a'], o['b']))}"
    if t == "arc":
        r = arc_radius(doc, o)
        _s, span = arc_angles(doc, o)
        name = f"{doc.label(o['p'])}{doc.label(o['q'])}" if o.get("p") is not None else ""
        if kind == "area":
            return f"부채꼴의 넓이 = {fmt_area(doc, 0.5 * r * r * math.radians(span))}"
        if kind == "angle":
            return f"중심각 = {fmt_angle(doc, span)}"
        return f"호 {name}의 길이 = {fmt_len(doc, r * math.radians(span))}"
    if t == "solid":
        surf, vol, sk, vk = S.metrics(o["kind"], o["params"])
        u = doc.settings.get("unit", "")
        d = doc.settings["decimals"]
        name = solid_name(o)
        if kind == "surface":
            val, k, uu, word = surf, sk, f" {u}²" if u else "", "겉넓이"
        else:
            val, k, uu, word = vol, vk, f" {u}³" if u else "", "부피"
        if k is not None:
            return f"{name}의 {word} = {nice(k, d)}π{uu} (≈ {fmt_num(val, d)}{uu})"
        return f"{name}의 {word} = {nice(val, d)}{uu}"
    if t == "angle":
        span = angle_value(doc, o)
        name = doc.label(o["a"]) + doc.label(o["v"]) + doc.label(o["b"])
        return f"∠{name} = {fmt_angle(doc, span)}"
    if t == "polygon":
        if kind == "perimeter":
            return f"{poly_name(doc, o)}의 둘레 = {fmt_len(doc, poly_perimeter(doc, o))}"
        return f"{poly_name(doc, o)}의 넓이 = {fmt_area(doc, poly_area(doc, o))}"
    if t == "circle":
        r = circle_radius(doc, o)
        name = f"원 {doc.label(o['c'])}"
        if kind == "circumference":
            return f"{name}의 둘레 = {fmt_len(doc, 2 * math.pi * r)}"
        if kind == "area":
            return f"{name}의 넓이 = {fmt_area(doc, math.pi * r * r)}"
        return f"{name}의 반지름 = {fmt_len(doc, r)}"
    return ""


def measure_text(doc, m):
    o = doc.objects.get(m["target"])
    if not o:
        return "?"
    return measure_value_text(doc, o, m["kind"])
