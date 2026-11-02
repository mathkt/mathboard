"""도형그리기 - 그림판(마우스 조작)"""
import math

from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPathStroker, QPolygonF, QCursor, QPainterPath
from PySide6.QtWidgets import QWidget, QInputDialog, QMenu

import model as M
import solid as S
from render import Geo, Renderer, length, norm, perp, dot, qpen, dir_deg

TOOL_HINTS = {
    "select": "클릭: 선택 · 드래그: 이동 · Shift+클릭: 여러 개 선택 · 빈 곳 드래그: 영역 선택 · 더블클릭: 이름/글자 수정 · 휠: 확대/축소 · 오른쪽 드래그: 화면 이동",
    "point": "클릭해서 점을 찍습니다. 입체의 꼭짓점·모서리·원 둘레·면을 클릭하면 그 위의 점 (Alt: 모눈·입체 무시)",
    "segment": "두 점을 차례로 클릭하면 선분이 생깁니다. Shift: 수평·수직·30°·45°·60° 방향으로",
    "line": "두 점을 차례로 클릭하면 직선이 생깁니다. Shift: 수평·수직·30°·45°·60° 방향으로",
    "ray": "시작점, 지나는 점 순서로 클릭하면 반직선이 생깁니다. Shift: 수평·수직·30°·45°·60° 방향으로",
    "polygon": "꼭짓점을 차례로 클릭하고, 첫 점을 다시 클릭하거나 더블클릭/Enter 로 완성합니다. Esc: 취소",
    "regpoly": "한 변의 두 끝점을 클릭하면 정다각형이 생깁니다. (변의 수는 왼쪽 도구모음에서)",
    "circle": "중심, 원 위의 한 점 순서로 클릭합니다.",
    "arc": "호: 중심 → 시작점 → 끝점 순서로 클릭 (시계 반대 방향). 부채꼴은 속성 창에서.",
    "brace": "선분을 클릭하거나, 두 점을 차례로 클릭하면 길이를 표시합니다. (중괄호/호 모양은 속성 창에서)",
    "angle": "각의 한쪽 끝 점 → 꼭짓점 → 다른 쪽 끝 점 순서로 클릭합니다.",
    "tick": "선분을 클릭하면 같은 길이 눈금(|)이 붙습니다. 다시 클릭하면 ||, ||| 로 바뀝니다.",
    "text": "글상자를 놓을 곳을 클릭합니다.",
    "mid": "중점: 두 점 또는 선분을 클릭합니다.",
    "pbis": "수직이등분선: 두 점 또는 선분을 클릭합니다. (작도 흔적은 설정에서 켜고 끔)",
    "abis": "각의 이등분선: 끝 점 → 꼭짓점 → 끝 점 (또는 각 표시를 클릭)",
    "perp": "수선: 점을 클릭한 뒤 직선·선분(입체는 모서리나 면)을 클릭합니다. 수선의 발과 직각 표시가 생깁니다.",
    "par": "평행선: 점을 클릭한 뒤 직선·선분을 클릭합니다.",
    "inter": "교점: 두 선·원을 차례로 클릭하거나, 교점 근처를 바로 클릭합니다.",
    "tan": "접선: 원 밖(또는 원 위)의 점을 클릭한 뒤 원을 클릭합니다.",
    "copyseg": "선분 옮기기: 옮길 선분(또는 두 점) → 새 시작점 → 방향을 차례로 클릭합니다.",
    "copyang": "각 옮기기: 옮길 각(각 표시 또는 끝 점→꼭짓점→끝 점) → 새 꼭짓점 → 한 변의 방향을 클릭합니다.",
    "compass": "컴퍼스: 고정점(바늘)을 클릭한 뒤, 끌어서 돌리면 돌린 만큼 호가 그려집니다. 너비는 왼쪽에서. Esc: 고정점 풀기",
    "solid": "놓을 곳을 클릭합니다. (Shift+클릭: 계속 놓기 · 놓은 뒤 더블클릭: 회전 모드)",
    "measure": "길이·각·넓이를 잴 도형을 클릭하면 측정값이 화면에 표시됩니다.",
}


def clamp_vec(v, maxlen):
    """이름을 끌 때 점에서 너무 멀어지지 않게"""
    L = length(v)
    return v * (maxlen / L) if L > maxlen else v


LABEL_MAX = 70.0   # 이름·길이 글자를 끌어 옮길 수 있는 최대 거리(px)


def dist_to_seg(P, A, B, kind="segment"):
    d = B - A
    L2 = dot(d, d)
    if L2 < 1e-9:
        return length(P - A)
    t = dot(P - A, d) / L2
    if kind == "segment":
        t = max(0.0, min(1.0, t))
    elif kind == "ray":
        t = max(0.0, t)
    return length(P - (A + d * t))


class Canvas(QWidget):
    selectionChanged = Signal()
    changed = Signal()
    status = Signal(str)

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.scale = 1.0
        self.offset = QPointF(40, 40)
        self.tool = "select"
        self.temp = []
        self.temp_created = []
        self.selection = []
        self.drag = None
        self.mouse = QPointF()
        self.reg_n = 5
        self.space_down = False
        self.rotating = None
        self.cut_pick = None     # 점 3개로 자르기: {"sid": 입체, "pts": []}
        self.compass_r = 3.0     # 컴퍼스 너비(cm)
        self.compass_pivot = None
        self.compass_measure = None   # 두 점으로 너비 재기: [점, ...]
        self.compass_draw = None      # 끌고 있는 동안: {"start": 각, "sweep": 누적각, "last": 각}
        self.on_compass_width = None
        self.solid_pending = None     # 입체도형 도구: (종류, 크기, tz, tx) — 마우스를 따라 겨냥도 미리보기
        self.edge_pick = None         # 선 고르기: {"sid": 입체, "keys": [선 이름]}
        self.group_edit = None        # 더블클릭으로 들어간 그룹 (그 안에서는 하나씩 선택)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(400, 300)
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    # ------------------------------------------------------------ 기본
    @property
    def doc(self):
        return self.win.doc

    def to_world(self, sp):
        return QPointF((sp.x() - self.offset.x()) / self.scale, (sp.y() - self.offset.y()) / self.scale)

    def to_screen(self, wp):
        return QPointF(wp.x() * self.scale + self.offset.x(), wp.y() * self.scale + self.offset.y())

    def tol(self):
        return 7 / self.scale

    def set_selection(self, ids):
        self.selection = [i for i in ids if i in self.doc.objects]
        if self.edge_pick and self.selection != [self.edge_pick["sid"]]:
            self.edge_pick = None
        self.selectionChanged.emit()
        self.update()

    def group_members(self, oid):
        """그룹에 든 개체를 누르면 그룹 전체 (더블클릭으로 들어간 그룹은 하나씩)"""
        o = self.doc.objects.get(oid)
        g = o.get("group") if o else None
        if g is None or g == self.group_edit:
            return [oid]
        return [i for i, q in self.doc.objects.items() if q.get("group") == g and not q.get("hidden")]

    def expand_groups(self, ids):
        out = []
        for i in ids:
            for j in self.group_members(i):
                if j not in out:
                    out.append(j)
        return out

    # ------------------------------------------------------------ 선 고르기 (입체도형 모서리마다 실선·점선)
    def start_edge_pick(self, sid):
        if self.edge_pick and self.edge_pick["sid"] == sid:
            self.edge_pick = None
            self.status.emit("선 고르기를 끝냈습니다.")
        else:
            self.win.choose_tool("select")
            self.selection = [sid]
            self.edge_pick = {"sid": sid, "keys": []}
            self.status.emit("선 고르기: 바꿀 선을 클릭하세요. Shift+클릭으로 여러 개, 빈 곳 클릭이나 Esc로 끝")
        self.selectionChanged.emit()
        self.update()

    def edge_at(self, sid, wp):
        o = self.doc.objects.get(sid)
        if not o:
            return None
        best, bk = self.tol() * 1.6, None
        for k, A, B, _v in Geo(self.doc).solid(o).get("edge_hits", []):
            d = dist_to_seg(wp, A, B)
            if d < best:
                best, bk = d, k
        return bk

    def draw_edge_pick(self, p, geo):
        o = self.doc.objects.get(self.edge_pick["sid"]) if self.edge_pick else None
        if not o:
            self.edge_pick = None
            return
        hits = geo.solid(o).get("edge_hits", [])
        keys = set(self.edge_pick["keys"])
        hov = self.edge_at(o["id"], self.mouse)
        for k, A, B, _v in hits:
            if k in keys:
                p.setPen(QPen(QColor(40, 140, 255, 150), 7 / self.scale, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(A, B)
            elif k == hov:
                p.setPen(QPen(QColor(240, 140, 30, 140), 6 / self.scale, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(A, B)
            else:
                p.setPen(QPen(QColor(40, 140, 255, 45), 3 / self.scale, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(A, B)

    def press_edge_pick(self, wp, mods):
        ep = self.edge_pick
        k = self.edge_at(ep["sid"], wp)
        if k is None:
            h = self.hit(wp)
            if h and h[0] == ep["sid"]:
                return True
            self.edge_pick = None
            self.status.emit("선 고르기를 끝냈습니다.")
            self.selectionChanged.emit()
            return False
        if mods & (Qt.ShiftModifier | Qt.ControlModifier):
            if k in ep["keys"]:
                ep["keys"].remove(k)
            else:
                ep["keys"].append(k)
        else:
            ep["keys"] = [k]
        self.selectionChanged.emit()
        return True

    def set_tool(self, tool):
        self.cancel_temp()
        if tool != "compass":
            self.compass_draw = None
            self.compass_measure = None
        self.tool = tool
        self.setCursor(Qt.ArrowCursor if tool == "select" else Qt.CrossCursor)
        self.status.emit(TOOL_HINTS.get(tool, ""))
        self.update()

    def cancel_temp(self):
        if self.temp_created:
            alive = [i for i in self.temp_created if i in self.doc.objects]
            if alive:
                self.doc.delete(alive)
                self.changed.emit()
        self.temp, self.temp_created = [], []
        self.update()

    def snap(self, wp, alt=False):
        if self.doc.settings.get("snap") and not alt:
            G = M.GRID
            return QPointF(round(wp.x() / G) * G, round(wp.y() / G) * G)
        return wp

    def notify(self):
        self.win.set_modified(True)
        self.changed.emit()
        self.update()

    # ------------------------------------------------------------ 찾기
    def visible(self):
        return [o for o in reversed(list(self.doc.objects.values())) if not o.get("hidden")]

    def pick_point(self, wp, exclude=()):
        best, bd = None, None
        for o in self.visible():
            if o["type"] != "point" or o["id"] in exclude or o.get("helper") or o.get("undef"):
                continue
            d = math.hypot(o["x"] - wp.x(), o["y"] - wp.y())
            if d < self.tol() + o.get("size", 3.5) and (bd is None or d < bd):
                best, bd = o["id"], d
        return best

    def hit(self, wp, kinds=None):
        geo = Geo(self.doc)
        tol = self.tol()
        objs = self.visible()
        ok = (lambda o: True) if kinds is None else (lambda o: o["type"] in kinds)
        if kinds is None:
            for o in objs:
                t = o["type"]
                if t == "point":
                    r = geo.point_label(o["id"])
                    if r and r.adjusted(-2, -2, 2, 2).contains(wp):
                        return o["id"], "label"
                elif t == "text":
                    if geo.text_rect(o).adjusted(-2, -2, 2, 2).contains(wp):
                        return o["id"], "body"
                elif t == "measure":
                    if geo.measure_rect(o).adjusted(-2, -2, 2, 2).contains(wp):
                        return o["id"], "body"
                elif t == "brace":
                    b = geo.brace(o)
                    if b and b["rect"] and b["rect"].adjusted(-2, -2, 2, 2).contains(wp):
                        return o["id"], "label"
                elif t == "angle":
                    a = geo.angle(o)
                    if a and a["rect"] and a["rect"].adjusted(-2, -2, 2, 2).contains(wp):
                        return o["id"], "label"
                elif t == "solid":
                    for k, rect, _n in geo.solid(o)["labels"]:
                        if rect.adjusted(-2, -2, 2, 2).contains(wp):
                            return o["id"], f"slabel{k}"
        pid = self.pick_point(wp)
        if pid and ok(self.doc.objects[pid]):
            return pid, "body"
        st = QPainterPathStroker()
        st.setWidth(tol * 2)
        for o in objs:
            if not ok(o):
                continue
            t = o["type"]
            if t == "angle":
                a = geo.angle(o)
                if a and st.createStroke(a["stroke"]).contains(wp):
                    return o["id"], "radius"
            elif t == "brace":
                b = geo.brace(o)
                if b and st.createStroke(b["path"]).contains(wp):
                    return o["id"], "height"
            elif t == "trace":
                path = geo.trace_path(o)
                if not path.isEmpty() and st.createStroke(path).contains(wp):
                    return o["id"], "body"
            elif t == "tick":
                path = geo.tick_path(o)
                if path is not None and st.createStroke(path).contains(wp):
                    return o["id"], "body"
        for o in objs:
            if o["type"] == "segment" and ok(o):
                d = dist_to_seg(wp, geo.P(o["a"]), geo.P(o["b"]), o.get("kind", "segment"))
                if d < tol + o["style"]["width"] / 2:
                    return o["id"], "body"
        for o in objs:
            if o["type"] == "circle" and ok(o):
                C = geo.P(o["c"])
                R = length(geo.P(o["p"]) - C)
                d = length(wp - C)
                if abs(d - R) < tol + o["style"]["width"] / 2 or (o.get("alpha", 0) > 0 and d < R):
                    return o["id"], "body"
        for o in objs:
            if o["type"] == "arc" and ok(o):
                a = geo.arcs(o)
                if a and (st.createStroke(a["path"]).contains(wp) or
                          (o.get("alpha", 0) > 0 and a["fill"].contains(wp))):
                    return o["id"], "body"
        for o in objs:
            if o["type"] == "net" and ok(o):
                ni = geo.net(o)
                if ni and ni["hull"].containsPoint(wp, Qt.OddEvenFill):
                    return o["id"], "body"
        for o in objs:
            if o["type"] == "solid" and ok(o):
                if st.createStroke(geo.solid(o)["vis"]).contains(wp):
                    return o["id"], "body"
        # 입체 위에 그린 다각형이 입체보다 먼저 잡히도록 (작은 것부터)
        polys = []
        for o in objs:
            if o["type"] == "polygon" and ok(o):
                ids = [i for i in o["pts"] if i in self.doc.objects]
                if len(ids) >= 3:
                    pg = QPolygonF([geo.P(i) for i in ids])
                    if pg.containsPoint(wp, Qt.OddEvenFill):
                        br = pg.boundingRect()
                        polys.append((br.width() * br.height(), o["id"]))
        if polys:
            return min(polys)[1], "body"
        for o in objs:
            if o["type"] == "solid" and ok(o):
                info = geo.solid(o)
                if info["hull"] is not None and info["hull"].containsPoint(wp, Qt.OddEvenFill):
                    return o["id"], "body"
        return None

    # ------------------------------------------------------------ 그리기
    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("white"))
        if self.doc.settings.get("show_grid"):
            self.draw_grid(p)
        p.save()
        p.translate(self.offset)
        p.scale(self.scale, self.scale)
        geo = Geo(self.doc)
        sel = [i for i in self.selection if not (self.edge_pick and i == self.edge_pick["sid"])]
        Renderer(self.doc, geo, sel).draw(p)
        self.draw_preview(p, geo)
        if self.edge_pick:
            self.draw_edge_pick(p, geo)
        if self.cut_pick:
            p.setPen(QPen(QColor(230, 90, 20), 2 / self.scale))
            p.setBrush(QColor(230, 90, 20, 60))
            for pid in self.cut_pick["pts"]:
                if pid in self.doc.objects:
                    q = self.doc.objects[pid]
                    p.drawEllipse(QPointF(q["x"], q["y"]), 7 / self.scale, 7 / self.scale)
        ro = self.doc.objects.get(self.rotating) if self.rotating else None
        if ro:
            br = geo.solid(ro)["hull"].boundingRect().adjusted(-14, -14, 14, 14)
            pen = QPen(QColor(240, 140, 30), 2 / self.scale, Qt.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(br, 8, 8)
            p.setPen(QColor(240, 140, 30))
            f = p.font()
            f.setPixelSize(max(1, int(12 / self.scale)))
            p.setFont(f)
            p.drawText(QPointF(br.left(), br.top() - 4 / self.scale), "회전 모드 – 끌어서 돌리기 · Esc 끝")
        else:
            self.rotating = None
        p.restore()
        if self.drag and self.drag["mode"] == "rubber":
            r = QRectF(self.to_screen(self.drag["start"]), self.to_screen(self.drag["cur"])).normalized()
            p.setPen(QPen(QColor(40, 140, 255), 1, Qt.DashLine))
            p.setBrush(QColor(40, 140, 255, 30))
            p.drawRect(r)
        p.end()

    def draw_grid(self, p):
        G = M.GRID * self.scale
        if G < 6:
            return
        w0 = self.to_world(QPointF(0, 0))
        w1 = self.to_world(QPointF(self.width(), self.height()))
        i0, i1 = math.floor(w0.x() / M.GRID), math.ceil(w1.x() / M.GRID)
        j0, j1 = math.floor(w0.y() / M.GRID), math.ceil(w1.y() / M.GRID)
        light, dark = QPen(QColor(232, 238, 245), 1), QPen(QColor(208, 218, 230), 1)
        for i in range(i0, i1 + 1):
            x = self.to_screen(QPointF(i * M.GRID, 0)).x()
            p.setPen(dark if i % 5 == 0 else light)
            p.drawLine(QPointF(x, 0), QPointF(x, self.height()))
        for j in range(j0, j1 + 1):
            y = self.to_screen(QPointF(0, j * M.GRID)).y()
            p.setPen(dark if j % 5 == 0 else light)
            p.drawLine(QPointF(0, y), QPointF(self.width(), y))

    def draw_preview(self, p, geo):
        if self.tool == "select":
            return
        if self.tool == "solid" and self.solid_pending and self.underMouse():
            kind, params, tz, tx = self.solid_pending
            c = self.snap(self.mouse, self.alt_now())
            ghost = M.solid_dict(self.doc, kind, c.x(), c.y(), params, tz, tx)
            ghost["id"] = -1
            g2 = Geo(self.doc)
            p.save()
            p.setOpacity(0.45)
            Renderer(self.doc, g2, []).draw_solid(p, ghost)
            p.restore()
            return
        if self.tool == "compass":
            self.draw_compass(p, geo)
            return
        if self.tool in ("mid", "pbis", "abis", "perp", "par", "inter", "tan", "copyseg", "copyang"):
            p.setPen(QPen(QColor(230, 90, 20), 2 / self.scale))
            p.setBrush(QColor(230, 90, 20, 50))
            for i in self.temp:
                o = self.doc.objects.get(i)
                if o and o["type"] == "point":
                    p.drawEllipse(QPointF(o["x"], o["y"]), 7 / self.scale, 7 / self.scale)
                elif o and o["type"] == "segment":
                    A, B = geo.P(o["a"]), geo.P(o["b"])
                    p.drawLine(A, B)
        m = self.mouse
        hp = self.pick_point(m)
        cur = geo.P(hp) if hp else self.snap(m, self.alt_now())
        qa = self.angle_snap(m)
        if qa is not None:
            cur = qa
            hp = None
        p.setBrush(Qt.NoBrush)
        pen = QPen(QColor(40, 140, 255), 1.5 / self.scale, Qt.DashLine)
        p.setPen(pen)
        pts = [geo.P(i) for i in self.temp if i in self.doc.objects]
        t = self.tool
        if t in ("segment", "line", "ray", "brace") and pts:
            p.drawLine(pts[0], cur)
        elif t == "angle" and pts:
            for k in range(len(pts) - 1):
                p.drawLine(pts[k], pts[k + 1])
            p.drawLine(pts[-1], cur)
        elif t == "polygon" and pts:
            p.drawPolyline(QPolygonF(pts + [cur]))
        elif t == "circle" and pts:
            R = length(cur - pts[0])
            p.drawEllipse(pts[0], R, R)
        elif t == "arc" and pts:
            if len(pts) == 1:
                R = length(cur - pts[0])
                p.drawLine(pts[0], cur)
                p.setPen(QPen(QColor(40, 140, 255, 90), 1 / self.scale, Qt.DotLine))
                p.drawEllipse(pts[0], R, R)
            else:
                C, A = pts[0], pts[1]
                R = length(A - C)
                s = math.degrees(math.atan2(-(A.y() - C.y()), A.x() - C.x()))
                e = math.degrees(math.atan2(-(cur.y() - C.y()), cur.x() - C.x()))
                rc = QRectF(C.x() - R, C.y() - R, 2 * R, 2 * R)
                path = QPainterPath()
                path.arcMoveTo(rc, s)
                path.arcTo(rc, s, (e - s) % 360)
                p.drawPath(path)
                p.drawLine(C, A)
        elif t == "regpoly" and pts:
            poly = self.regpoly_points(pts[0], cur, self.reg_n)
            p.drawPolygon(QPolygonF(poly))
        # 마우스 위치 표시
        if t not in ("tick", "measure", "text"):
            p.setPen(QPen(QColor(40, 140, 255), 1.5 / self.scale))
            p.setBrush(QColor(40, 140, 255, 60) if hp else Qt.NoBrush)
            p.drawEllipse(cur, 6 / self.scale, 6 / self.scale)

    def alt_now(self):
        from PySide6.QtWidgets import QApplication
        return bool(QApplication.keyboardModifiers() & Qt.AltModifier)

    @staticmethod
    def regpoly_points(A, B, n):
        pts = [A, B]
        d = B - A
        phi = -2 * math.pi / n
        cur = B
        for _ in range(n - 2):
            d = QPointF(d.x() * math.cos(phi) - d.y() * math.sin(phi),
                        d.x() * math.sin(phi) + d.y() * math.cos(phi))
            cur = cur + d
            pts.append(cur)
        return pts

    # ------------------------------------------------------------ 마우스
    def mousePressEvent(self, e):
        sp = e.position()
        wp = self.to_world(sp)
        self.setFocus()
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and self.space_down):
            self.drag = {"mode": "pan", "last": sp}
            self.setCursor(Qt.ClosedHandCursor)
            return
        if e.button() == Qt.RightButton:
            self.drag = {"mode": "rpan", "last": sp, "start": sp, "moved": False}
            return
        if e.button() != Qt.LeftButton:
            return
        alt = bool(e.modifiers() & Qt.AltModifier)
        if self.tool == "select":
            self.press_select(wp, e.modifiers())
        else:
            self.press_tool(wp, alt)
        self.update()

    def press_select(self, wp, mods):
        if self.cut_pick:
            self.press_cut_pick(wp)
            return
        if self.edge_pick and self.press_edge_pick(wp, mods):
            self.update()
            return
        if mods & Qt.AltModifier:
            hp = self.hit(wp, kinds=("polygon",))
            if hp and self.doc.objects[hp[0]]["type"] == "polygon":
                o = self.doc.objects[hp[0]]
                self.win.checkpoint()
                same = o.get("alpha", 0) > 0 and o.get("fill") == self.win.face_color and int(o.get("alpha", 0)) == int(self.win.face_alpha)
                if same:
                    o["alpha"] = 0
                else:
                    o["fill"], o["alpha"] = self.win.face_color, int(self.win.face_alpha)
                self.set_selection([o["id"]])
                self.notify()
                self.status.emit("다각형 색칠 (같은 색으로 다시 Alt+클릭하면 지워집니다)")
                return
            h = self.hit(wp, kinds=("solid",))
            if h:
                o = self.doc.objects[h[0]]
                g = Geo(self.doc).solid_face_at(o, wp, back=bool(mods & Qt.ShiftModifier))
                if g:
                    self.win.checkpoint()
                    fc = o.setdefault("face_colors", {})
                    col = [self.win.face_color, self.win.face_alpha]
                    if fc.get(g) == col:
                        del fc[g]
                    else:
                        fc[g] = col
                    self.set_selection([o["id"]])
                    self.notify()
                    self.status.emit(f"면 색칠: {g}  (같은 색으로 다시 Alt+클릭하면 지워집니다. Alt+Shift+클릭: 뒤쪽 면)")
                return
        h = self.hit(wp)
        multi = bool(mods & (Qt.ShiftModifier | Qt.ControlModifier))
        if self.rotating:
            hf = None
            if h and h[1] == "body" and self.doc.objects[h[0]]["type"] == "solid":
                hf = S.frame_of(self.doc.objects[h[0]], self.doc.objects)["id"]
            if h and hf == self.rotating:
                o = self.doc.objects[self.rotating]
                self.drag = {"mode": "rotate", "oid": o["id"], "start": wp, "state": self.doc.dump(),
                             "moved": False, "yaw": float(o.get("yaw", -30)), "pitch": float(o.get("pitch", 20)),
                             "sp": self.to_screen(wp)}
                return
            self.rotating = None
        if h:
            oid, part = h
            g = self.doc.objects[oid].get("group")
            if self.group_edit is not None and g != self.group_edit:
                self.group_edit = None
            mem = self.group_members(oid)
            if multi:
                if oid in self.selection:
                    for i in mem:
                        if i in self.selection:
                            self.selection.remove(i)
                    self.selectionChanged.emit()
                    return
                self.selection += [i for i in mem if i not in self.selection]
                self.selectionChanged.emit()
            elif oid not in self.selection:
                self.selection = mem
                self.selectionChanged.emit()
            self.start_drag(oid, part, wp)
        else:
            self.group_edit = None
            if not multi and self.selection:
                self.selection = []
                self.selectionChanged.emit()
            self.drag = {"mode": "rubber", "start": wp, "cur": wp, "add": multi}

    def start_drag(self, oid, part, wp):
        doc = self.doc
        o = doc.objects[oid]
        d = {"mode": part, "oid": oid, "start": wp, "state": doc.dump(), "moved": False}
        if part == "body":
            sel = self.selection if oid in self.selection else [oid]
            pts, pos = set(), set()
            for i in sel:
                ob = doc.objects.get(i)
                if not ob:
                    continue
                t = ob["type"]
                if t == "solid":
                    pos.add(ob.get("host") if ob.get("host") in doc.objects else i)
                elif t in ("text", "measure", "net"):
                    pos.add(i)
                elif t == "tick":
                    seg = doc.objects.get(ob["seg"])
                    if seg:
                        pts |= {seg["a"], seg["b"]}
                elif t in ("brace", "angle"):
                    continue
                else:
                    pts |= doc.point_ids_of([i])
            pts = {i for i in pts if doc.objects[i].get("solid") is None
                   and not doc.objects[i].get("dep")}   # 입체에 붙은 점·작도로 생긴 점은 스스로 움직이지 않음
            if o["type"] == "point" and (o.get("dep") or {}).get("t") == "on" and len(sel) == 1:
                d["mode"] = "slide2d"
            d["orig"] = {i: (doc.objects[i]["x"], doc.objects[i]["y"]) for i in pts | pos}
            d["single_point"] = (o["type"] == "point" and len(pts) == 1 and not pos)
            if o["type"] == "point" and o.get("edge") and len(sel) == 1:
                d["mode"] = "slide"
            if o["type"] == "point" and o.get("solid") is not None and len(sel) == 1:
                if o.get("face") is not None:
                    d["mode"] = "slideface"
                elif o.get("ring") is not None:
                    d["mode"] = "slidering"
        elif part.startswith("slabel"):
            k = int(part[6:])
            geo = Geo(doc)
            for kk, rect, _n in geo.solid(o)["labels"]:
                if kk == k:
                    d["grab"] = rect.center() - wp
            d["k"] = k
        elif part == "label":
            geo = Geo(doc)
            if o["type"] == "point":
                r = geo.point_label(oid)
                d["grab"] = r.center() - wp
            elif o["type"] == "brace":
                d["orig_lab"] = (o.get("label_dx", 0), o.get("label_dy", 0))
            elif o["type"] == "angle":
                a = geo.angle(o)
                d["grab"] = a["rect"].center() - wp
        self.drag = d

    def mouseMoveEvent(self, e):
        sp = e.position()
        wp = self.to_world(sp)
        self.mouse = wp
        if self.compass_draw is not None:
            self.compass_sweep(wp)
            self.update()
            return
        d = self.drag
        if not d:
            self.update()
            return
        mode = d["mode"]
        if mode == "pan":
            self.offset += sp - d["last"]
            d["last"] = sp
            self.update()
            return
        if mode == "rpan":
            if not d["moved"] and length(sp - d["start"]) > 4:
                d["moved"] = True
                self.setCursor(Qt.ClosedHandCursor)
            if d["moved"]:
                self.offset += sp - d["last"]
            d["last"] = sp
            self.update()
            return
        if mode == "rubber":
            d["cur"] = wp
            self.update()
            return
        if not d["moved"]:
            if length(self.to_screen(wp) - self.to_screen(d["start"])) < 3:
                return
            d["moved"] = True
            self.win.push_undo_state(d["state"])
        alt = bool(e.modifiers() & Qt.AltModifier)
        self.apply_drag(d, wp, alt)
        self.changed.emit()
        self.update()

    def apply_drag(self, d, wp, alt):
        doc = self.doc
        o = doc.objects.get(d["oid"])
        if not o:
            return
        mode = d["mode"]
        geo = Geo(doc)
        if mode == "slide2d":
            u = geo.on_param(o["dep"]["obj"], wp)
            if u is not None:
                o["dep"]["u"] = u
            return
        if mode == "slidering":
            so = doc.objects.get(o.get("solid"))
            if so:
                o["ang"] = round(self.ring_angle_at(so, int(o["ring"]), wp), 5)
            return
        if mode == "slideface":
            so = doc.objects.get(o.get("solid"))
            if not so:
                return
            info = geo.solid(so)
            m = info["a"]["mesh"]
            cur = int(o["face"])
            g0 = m.groups[cur] if cur < len(m.groups) else None
            fis = info.get("face_fi") or []
            cur_front = next((fr_ for k, (_g, fr_, _p) in enumerate(info["faces"]) if k < len(fis) and fis[k] == cur), True)
            target = None
            for k, (g, front, poly) in enumerate(info["faces"]):
                if k >= len(fis) or fis[k] is None or g != g0 or front != cur_front:
                    continue
                if poly.containsPoint(wp, Qt.OddEvenFill):
                    target = fis[k]
                    break
            if target is None:
                return
            X = self.unproject_face(so, target, wp, info)
            if X is not None:
                a, b = S.face_coords(m, target, X)
                o["face"], o["fa"], o["fb"] = target, round(a, 5), round(b, 5)
            return
        if mode == "slide":
            so = doc.objects.get(o.get("solid"))
            if so:
                P = geo.solid(so)["P"]
                A, B = P[o["edge"][0]], P[o["edge"][1]]
                dd = B - A
                t = max(0.0, min(1.0, dot(wp - A, dd) / max(dot(dd, dd), 1e-9)))
                if abs(t - 0.5) < 0.04:
                    t = 0.5
                o["t"] = round(t, 4)
            return
        if mode == "rotate":
            ds = self.to_screen(wp) - d["sp"]
            if o.get("view") != "rot":
                o["view"] = "rot"
            o["yaw"] = round((d["yaw"] + ds.x() * 0.5 + 180) % 360 - 180, 1)
            o["pitch"] = round(max(-90.0, min(90.0, d["pitch"] + ds.y() * 0.5)), 1)
            return
        if mode.startswith("slabel"):
            info = geo.solid(o)
            vi = info["a"]["mesh"].named[d["k"]]
            c = wp + d.get("grab", QPointF())
            P = info["P"][vi]
            v = clamp_vec(c - P, LABEL_MAX * 0.7)
            o.setdefault("lab_off", {})[str(d["k"])] = [v.x(), v.y()]
            return
        if mode == "body":
            delta = wp - d["start"]
            snap = doc.settings.get("snap") and not alt
            if snap and d.get("single_point"):
                (ox, oy), = d["orig"].values()
                q = self.snap(QPointF(ox, oy) + delta)
                delta = q - QPointF(ox, oy)
            elif snap:
                G = M.GRID
                delta = QPointF(round(delta.x() / G) * G, round(delta.y() / G) * G)
            for i, (x, y) in d["orig"].items():
                if i in doc.objects:
                    doc.objects[i]["x"] = x + delta.x()
                    doc.objects[i]["y"] = y + delta.y()
        elif mode == "label":
            if o["type"] == "point":
                c = wp + d["grab"]
                o["label_auto"] = False
                v = clamp_vec(c - QPointF(o["x"], o["y"]), LABEL_MAX * 0.7)
                o["label_dx"], o["label_dy"] = v.x(), v.y()
            elif o["type"] == "brace":
                delta = wp - d["start"]
                v = clamp_vec(QPointF(d["orig_lab"][0] + delta.x(), d["orig_lab"][1] + delta.y()), LABEL_MAX)
                o["label_dx"], o["label_dy"] = v.x(), v.y()
            elif o["type"] == "angle":
                a = geo.angle(o)
                if a:
                    rel = clamp_vec(wp + d["grab"] - a["V"], a["outer"] + LABEL_MAX * 1.5)
                    o["lu"], o["lv"] = dot(rel, a["u"]), dot(rel, a["v"])
        elif mode == "height":
            fr = geo.brace_frame(o)
            if fr:
                A, B, L, t, n0, gap = fr
                s = dot(wp - (A + B) * 0.5, n0)
                o["side"] = 1 if s >= 0 else -1
                if o.get("shape") == "arc":
                    o["arc_height"] = round(max(4.0, abs(s)), 1)
                else:
                    o["height"] = round(max(4.0, abs(s) - gap), 1)
        elif mode == "radius":
            V = geo.P(o["v"])
            o["radius"] = round(max(6.0, length(wp - V)), 1)

    def mouseReleaseEvent(self, e):
        if self.compass_draw is not None and e.button() == Qt.LeftButton:
            self.compass_finish()
            return
        d = self.drag
        self.drag = None
        if self.tool == "select":
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.CrossCursor)
        if not d:
            return
        if d["mode"] == "rubber":
            r = QRectF(d["start"], d["cur"]).normalized()
            if r.width() * self.scale > 3 or r.height() * self.scale > 3:
                ids = self.expand_groups(self.objects_in_rect(r))
                if d["add"]:
                    ids = list(dict.fromkeys(self.selection + ids))
                self.set_selection(ids)
        elif d["mode"] == "rpan" and not d["moved"]:
            self.context_menu(e.position())
        elif d.get("moved"):
            self.notify()
        self.update()

    def objects_in_rect(self, r):
        doc = self.doc
        geo = Geo(doc)
        out = []
        for o in doc.objects.values():
            if o.get("hidden"):
                continue
            t = o["type"]
            if t == "point":
                if r.contains(QPointF(o["x"], o["y"])):
                    out.append(o["id"])
            elif t == "text":
                if r.contains(geo.text_rect(o).center()):
                    out.append(o["id"])
            elif t == "measure":
                if r.contains(geo.measure_rect(o).center()):
                    out.append(o["id"])
            elif t == "solid":
                if r.contains(geo.solid(o)["hull"].boundingRect()):
                    out.append(o["id"])
            elif t == "net":
                ni = geo.net(o)
                if ni and r.contains(ni["hull"].boundingRect()):
                    out.append(o["id"])
            else:
                pts = doc.point_ids_of([o["id"]]) if t != "tick" else doc.point_ids_of([o["seg"]])
                if pts and all(r.contains(geo.P(i)) for i in pts):
                    out.append(o["id"])
        return out

    def mouseDoubleClickEvent(self, e):
        wp = self.to_world(e.position())
        if self.tool == "polygon":
            self.finish_polygon()
            return
        if self.tool != "select":
            return
        h = self.hit(wp)
        if not h:
            return
        oid, part = h
        o = self.doc.objects[oid]
        self.drag = None
        g = o.get("group")
        if g is not None and g != self.group_edit and len(self.selection) > 1:
            self.group_edit = g
            self.set_selection([oid])
            self.status.emit("그룹 안에서 하나씩 고릅니다. 그룹 밖을 클릭하면 다시 묶여서 선택됩니다.")
            return
        t = o["type"]
        if t == "solid":
            if part.startswith("slabel"):
                self.win.rename_solid_label(oid, int(part[6:]))
            else:
                fid = S.frame_of(o, self.doc.objects)["id"]
                self.rotating = None if self.rotating == fid else fid
                self.set_selection([oid])
                self.status.emit("회전 모드: 입체도형을 끌어서 돌리세요. 끝내려면 Esc 또는 빈 곳 클릭"
                                 if self.rotating else "회전 모드를 끝냈습니다.")
                self.update()
            return
        if t == "point":
            self.win.rename_point(oid)
        elif t == "text":
            self.win.edit_text(oid)
        elif t == "brace" and part == "label":
            self.edit_custom(o, "text_mode", "중괄호 글자", Geo(self.doc).brace_text(o))
        elif t == "angle" and part == "label":
            _, span = M.angle_span(self.doc, o)
            self.edit_custom(o, "label_mode", "각 표시 글자", Geo(self.doc).angle_text(o, span))

    def edit_custom(self, o, mode_key, title, current):
        text, ok = QInputDialog.getText(self, title, "표시할 글자 (예: x, 5cm, 30°, ∠a):", text=current)
        if ok:
            self.win.checkpoint()
            o[mode_key] = "custom"
            o["text"] = text
            self.notify()
            self.selectionChanged.emit()

    def wheelEvent(self, e):
        dy = e.angleDelta().y()
        if dy == 0:
            return
        f = 1.15 ** (dy / 120)
        new = max(0.1, min(10.0, self.scale * f))
        sp = e.position()
        wp = self.to_world(sp)
        self.scale = new
        self.offset = QPointF(sp.x() - wp.x() * new, sp.y() - wp.y() * new)
        self.status.emit(f"확대 {int(round(self.scale * 100))}%")
        self.update()

    # ------------------------------------------------------------ 도구
    def snap_point(self, wp, edges=True, only_sid=None):
        """점 고르기: 있는 점 → 입체의 꼭짓점 → (edges) 입체 모서리 위. 없으면 None"""
        pid = self.pick_point(wp)
        if pid and (only_sid is None or self.doc.objects[pid].get("solid") == only_sid):
            return pid
        geo = Geo(self.doc)
        tol = self.tol() + 3
        best = None
        for o in self.visible():
            if o["type"] != "solid" or (only_sid is not None and o["id"] != only_sid):
                continue
            info = geo.solid(o)
            mesh = info["a"]["mesh"]
            cand = set(mesh.named)
            if not S.is_curved(o) and info["a"]["whole"]:
                cand |= {v for f in mesh.faces for v in f}
            for vi in cand:
                if vi >= len(info["P"]):
                    continue
                dd = length(info["P"][vi] - wp)
                if dd < tol and (best is None or dd < best[0]):
                    best = (dd, o["id"], vi)
        if best:
            self.win.checkpoint()
            return M.make_attached_point(self.doc, best[1], sv=best[2])
        if not edges:
            return None
        rg = self.ring_at(wp, only_sid)
        if rg:
            o, r0 = rg
            self.win.checkpoint()
            return M.make_attached_point(self.doc, o["id"], ring=r0, ang=self.ring_angle_at(o, r0, wp))
        se = self.solid_edge_at(wp, only_sid)
        if se:
            sid, i, j = se
            o = self.doc.objects[sid]
            P = geo.solid(o)["P"]
            A, B = P[i], P[j]
            d = B - A
            t = max(0.0, min(1.0, dot(wp - A, d) / max(dot(d, d), 1e-9)))
            if abs(t - 0.5) < 0.06:
                t = 0.5
            self.win.checkpoint()
            return M.make_attached_point(self.doc, sid, edge=(i, j), t=t)
        return None

    def angle_snap(self, wp):
        """Shift: 첫 점에서 수평·수직·30°·45°·60° 방향으로 맞춘 위치 (선분·직선·반직선)"""
        if self.tool not in ("segment", "line", "ray") or not self.temp:
            return None
        from PySide6.QtWidgets import QApplication
        if not (QApplication.keyboardModifiers() & Qt.ShiftModifier):
            return None
        a = self.doc.objects.get(self.temp[0])
        if not a:
            return None
        A = QPointF(a["x"], a["y"])
        v = wp - A
        L = length(v)
        if L < 1e-6:
            return None
        ang = math.degrees(math.atan2(-v.y(), v.x()))
        cands = [k * 15 for k in range(-12, 13) if (k * 15) % 30 == 0 or (k * 15) % 45 == 0]
        best = min(cands, key=lambda c: abs((ang - c + 180) % 360 - 180))
        t = math.radians(best)
        u = QPointF(math.cos(t), -math.sin(t))
        Lp = dot(v, u)
        if self.doc.settings.get("snap") and not self.alt_now():
            # 모눈에 맞출 때는 길이를 0.5cm 단위로
            h = M.GRID / 2
            Lp = round(Lp / h) * h
        return A + u * Lp

    def face_at(self, wp):
        """화면 위치의 입체 앞쪽 면 → (입체, 면 번호, 3D 점)"""
        geo = Geo(self.doc)
        for o in reversed(self.visible()):
            if o["type"] != "solid" or o.get("cut"):
                continue
            info = geo.solid(o)
            fis = info.get("face_fi") or []
            for k, (g, front, poly) in enumerate(info["faces"]):
                if not front or k >= len(fis) or fis[k] is None:
                    continue
                if poly.containsPoint(wp, Qt.OddEvenFill):
                    X = self.unproject_face(o, fis[k], wp, info)
                    if X is not None:
                        return o, fis[k], X
        return None

    def unproject_face(self, o, fi, wp, info=None):
        info = info or Geo(self.doc).solid(o)
        a = info["a"]
        m = a["mesh"]
        f = m.faces[fi]
        n = S.newell(m, f)
        L = math.sqrt(sum(c * c for c in n)) or 1.0
        n = tuple(c / L for c in n)
        v0 = m.v[f[0]]
        d = sum(n[k] * v0[k] for k in range(3))
        fr = S.frame_of(o, self.doc.objects)
        return S.unproject(a["proj"], (wp.x() - fr["x"]) / M.GRID, (wp.y() - fr["y"]) / M.GRID, n, d, a["shift"])

    def ring_at(self, wp, only_sid=None):
        """곡면 입체(원기둥·원뿔 등)의 원 둘레 근처 → (입체, 원 번호)"""
        geo = Geo(self.doc)
        best = None
        for o in self.visible():
            if o["type"] != "solid" or (only_sid is not None and o["id"] != only_sid):
                continue
            if not S.is_curved(o) or o.get("cut") or S.build(o["kind"], o["params"]).sphere_r is not None:
                continue
            info = geo.solid(o)
            for k, A, B, v in info.get("edge_hits", []):
                if not k.startswith("r"):
                    continue
                if not v and not o.get("show_hidden", True):
                    continue
                dd = dist_to_seg(wp, A, B)
                if dd < self.tol() + 2 and (best is None or dd < best[0]):
                    best = (dd, o, int(k[1:].split(":")[0]))
        if not best:
            return None
        m = geo.solid(best[1])["a"]["mesh"]
        x0, _y0, z0 = m.v[best[2]]
        if abs(z0) > 1e-6 or x0 <= 1e-6:
            return None
        return best[1], best[2]

    def ring_angle_at(self, so, r0, wp):
        geo = Geo(self.doc)
        m = geo.solid(so)["a"]["mesh"]
        best, ba = None, 0.0
        for k in range(360):
            t = math.radians(k)
            X = S.ring_point(m, r0, t)
            if X is None:
                return 0.0
            dd = length(geo.solid_screen(so, X) - wp)
            if best is None or dd < best:
                best, ba = dd, t
        return ba

    def make_face_point(self, wp):
        fa_ = self.face_at(wp)
        if not fa_:
            return None
        o, fi, X = fa_
        m = Geo(self.doc).solid(o)["a"]["mesh"]
        a, b = S.face_coords(m, fi, X)
        self.win.checkpoint()
        return M.make_attached_point(self.doc, o["id"], face=fi, fa=a, fb=b)

    def get_or_make(self, wp, alt):
        q = self.angle_snap(wp)
        if q is not None:
            self.win.checkpoint()
            return M.make_point(self.doc, q.x(), q.y()), True
        pid = self.snap_point(wp)
        if pid:
            return pid, False
        pid = self.make_face_point(wp) if not alt else None
        if pid:
            return pid, True
        self.win.checkpoint()
        q = self.snap(wp, alt)
        return M.make_point(self.doc, q.x(), q.y()), True

    def press_tool(self, wp, alt):
        doc = self.doc
        t = self.tool
        if t == "point":
            pid = self.pick_point(wp)
            if pid:
                self.set_selection([pid])
                return
            pid = self.snap_point(wp)
            if not pid:
                pid = self.point_on_objects(wp)
            if not pid and not alt:
                pid = self.make_face_point(wp)
            if pid:
                self.set_selection([pid])
                self.notify()
                self.done_shape()
                return
            self.win.checkpoint()
            q = self.snap(wp, alt)
            pid = M.make_point(doc, q.x(), q.y())
            self.selection = [pid]
            self.selectionChanged.emit()
            self.notify()
            self.done_shape()
        elif t in ("segment", "line", "ray"):
            pid, _ = self.get_or_make(wp, alt)
            if not self.temp:
                self.temp = [pid]
            elif pid != self.temp[0]:
                self.win.checkpoint()
                sid = M.make_segment(doc, self.temp[0], pid, kind=t)
                self.temp = []
                self.set_selection([sid])
                self.done_shape()
            self.notify()
        elif t == "polygon":
            existing = self.pick_point(wp)
            if self.temp and len(self.temp) >= 3 and existing == self.temp[0]:
                self.finish_polygon()
                return
            pid, created = self.get_or_make(wp, alt)
            if pid not in self.temp:
                self.temp.append(pid)
                if created:
                    self.temp_created.append(pid)
            self.notify()
        elif t == "regpoly":
            pid, created = self.get_or_make(wp, alt)
            if not self.temp:
                self.temp = [pid]
                self.temp_created = [pid] if created else []
            elif pid != self.temp[0]:
                self.win.checkpoint()
                A, B = QPointF(*doc.xy(self.temp[0])), QPointF(*doc.xy(pid))
                ids = [self.temp[0], pid]
                for q in self.regpoly_points(A, B, self.reg_n)[2:]:
                    ids.append(M.make_point(doc, q.x(), q.y()))
                poly = M.make_polygon(doc, ids)
                self.temp, self.temp_created = [], []
                self.set_selection([poly])
                self.done_shape()
            self.notify()
        elif t == "arc":
            pid = self.pick_point(wp)
            created = False
            if not pid:
                self.win.checkpoint()
                if len(self.temp) == 2:
                    # 끝점은 원 위에 놓이게
                    C, A = QPointF(*doc.xy(self.temp[0])), QPointF(*doc.xy(self.temp[1]))
                    q = C + norm(wp - C) * length(A - C)
                else:
                    q = self.snap(wp, alt)
                pid = M.make_point(doc, q.x(), q.y())
                created = True
            if pid in self.temp:
                return
            self.temp.append(pid)
            if created:
                self.temp_created.append(pid)
            if len(self.temp) == 3:
                self.win.checkpoint()
                c0, p0, q0 = self.temp
                aid = M.make_arc(doc, c0, p0, q0)
                self.temp, self.temp_created = [], []
                self.set_selection([aid])
                self.done_shape()
            self.notify()
        elif t == "circle":
            pid, created = self.get_or_make(wp, alt)
            if not self.temp:
                self.temp = [pid]
            elif pid != self.temp[0]:
                self.win.checkpoint()
                cid = M.make_circle(doc, self.temp[0], pid)
                self.temp = []
                self.set_selection([cid])
                self.done_shape()
            self.notify()
        elif t == "solid":
            if self.win.add_solid(self.snap(wp, alt)):
                self.done_shape()
        elif t == "brace":
            vpid = self.snap_point(wp, edges=False)
            if not self.temp and not vpid:
                se = self.solid_edge_at(wp)
                if se:
                    self.win.add_solid_brace(*se)
                    self.done_shape()
                    return
                h = self.hit(wp, kinds=("segment",))
                if h:
                    seg = doc.objects[h[0]]
                    self.win.add_brace(seg["a"], seg["b"])
                    self.done_shape()
                    return
            pid = vpid or self.snap_point(wp)
            if not pid:
                self.status.emit("길이 표시는 점(입체의 꼭짓점 포함)이나 선분을 클릭해 주세요.")
                return
            if not self.temp:
                self.temp = [pid]
            elif pid != self.temp[0]:
                self.win.add_brace(self.temp[0], pid)
                self.temp = []
                self.done_shape()
            self.update()
        elif t == "angle":
            pid = self.snap_point(wp)
            if not pid:
                self.status.emit("각 표시는 이미 있는 점 3개를 차례로 클릭합니다. (끝 점 → 꼭짓점 → 끝 점)")
                return
            if pid in self.temp:
                return
            self.temp.append(pid)
            if len(self.temp) == 3:
                self.win.checkpoint()
                a, v, b = self.temp
                aid = M.make_angle(doc, a, v, b)
                self.temp = []
                self.set_selection([aid])
                self.notify()
                self.done_shape()
            self.update()
        elif t in ("mid", "pbis", "abis", "perp", "par", "inter", "tan", "copyseg", "copyang"):
            self.press_construct(t, wp)
        elif t == "compass":
            self.press_compass(wp)
        elif t == "tick":
            h = self.hit(wp, kinds=("segment",))
            if not h:
                return
            self.win.checkpoint()
            for o in doc.items("tick"):
                if o["seg"] == h[0]:
                    o["count"] = o.get("count", 1) % 3 + 1
                    self.set_selection([o["id"]])
                    break
            else:
                self.set_selection([M.make_tick(doc, h[0])])
            self.notify()
            self.done_shape()
        elif t == "text":
            text, ok = QInputDialog.getMultiLineText(self, "글상자", "내용:")
            if ok and text:
                self.win.checkpoint()
                q = self.snap(wp, alt) if False else wp
                self.set_selection([M.make_text(doc, q.x(), q.y(), text)])
                self.notify()
                self.done_shape()
        elif t == "measure":
            h = self.hit(wp, kinds=tuple(M.MEASURE_KINDS.keys()))
            if not h:
                return
            o = doc.objects[h[0]]
            kinds = M.MEASURE_KINDS.get(o["type"], [])
            if not kinds:
                return
            kind = kinds[0][0]
            if len(kinds) > 1:
                menu = QMenu(self)
                acts = {menu.addAction(name): k for k, name in kinds}
                chosen = menu.exec(QCursor.pos())
                if not chosen:
                    return
                kind = acts[chosen]
            self.win.add_measure(o["id"], kind, (wp.x() + 12, wp.y() + 12))
            self.done_shape()

    def solid_edge_at(self, wp, only_sid=None, visible_only=False, skip_v=()):
        geo = Geo(self.doc)
        best, bd = None, None
        for o in self.visible():
            if o["type"] != "solid" or (only_sid is not None and o["id"] != only_sid):
                continue
            for i, j, vis, line in geo.solid_edges(o):
                if not vis and (visible_only or not o.get("show_hidden", True)):
                    continue
                if i in skip_v or j in skip_v:
                    continue
                dd = dist_to_seg(wp, line.p1(), line.p2())
                if dd < self.tol() + 2 and (bd is None or dd < bd):
                    best, bd = (o["id"], i, j), dd
        return best

    # ------------------------------------------------------------ 작도
    def near_prims(self, wp):
        """클릭 근처의 선·원 [(거리, 번호)]"""
        geo = Geo(self.doc)
        tol = self.tol() + 2
        out = []
        for o in self.visible():
            if o["type"] not in ("segment", "circle", "arc") or o["id"] in geo.undef:
                continue
            pr = geo.prim(o["id"])
            if not pr:
                continue
            if pr[0] == "line":
                dd = dist_to_seg(wp, pr[1], pr[2], pr[3])
            else:
                dd = abs(length(wp - pr[1]) - pr[2])
                if o["type"] == "arc":
                    a_ = geo.arcs(o)
                    st = QPainterPathStroker()
                    st.setWidth(tol * 2)
                    if a_ and not st.createStroke(a_["path"]).contains(wp):
                        continue
            if dd < tol:
                out.append((dd, o["id"]))
        return sorted(out)

    def make_intersection(self, o1, o2, wp):
        geo = Geo(self.doc)
        p1, p2 = geo.prim(o1), geo.prim(o2)
        if not p1 or not p2:
            return None
        pts = geo.intersections(p1, p2)
        if not pts:
            self.status.emit("두 도형이 만나지 않습니다.")
            return None
        k = min(range(len(pts)), key=lambda i: length(pts[i] - wp))
        for q in self.doc.items("point"):     # 이미 있는 교점이면 그것을 씀
            dd = q.get("dep") or {}
            if dd.get("t") == "inter" and {dd.get("o1"), dd.get("o2")} == {o1, o2} and dd.get("k") == k:
                return q["id"]
        self.win.checkpoint()
        return M.make_dep_point(self.doc, {"t": "inter", "o1": o1, "o2": o2, "k": k})

    def point_on_objects(self, wp):
        """점 도구로 선·원 위를 클릭: 교점 근처면 교점, 아니면 그 위를 움직이는 점"""
        near = self.near_prims(wp)
        if len(near) >= 2:
            geo = Geo(self.doc)
            p1, p2 = geo.prim(near[0][1]), geo.prim(near[1][1])
            pts = geo.intersections(p1, p2) if p1 and p2 else []
            if pts and min(length(q - wp) for q in pts) < self.tol() * 2 + 3:
                return self.make_intersection(near[0][1], near[1][1], wp)
        if near:
            oid = near[0][1]
            u = Geo(self.doc).on_param(oid, wp)
            if u is None:
                return None
            self.win.checkpoint()
            return M.make_dep_point(self.doc, {"t": "on", "obj": oid, "u": u})
        return None

    def press_construct(self, t, wp):
        doc = self.doc
        traces = doc.settings.get("construction_traces", True)
        if t in ("mid", "pbis"):
            if not self.temp:
                pid = self.snap_point(wp)
                if not pid:
                    h = self.hit(wp, kinds=("segment",))
                    if h:
                        seg = doc.objects[h[0]]
                        self.finish_two(t, seg["a"], seg["b"])
                    return
                self.temp = [pid]
                self.update()
                return
            pid = self.snap_point(wp)
            if pid and pid != self.temp[0]:
                self.finish_two(t, self.temp[0], pid)
            return
        if t == "abis":
            if not self.temp:
                h = self.hit(wp, kinds=("angle",))
                if h and not self.pick_point(wp):
                    an = doc.objects[h[0]]
                    a, b = (an["b"], an["a"]) if an.get("reflex") else (an["a"], an["b"])
                    self.finish_abis(a, an["v"], b)
                    return
            pid = self.snap_point(wp)
            if not pid or pid in self.temp:
                return
            self.temp.append(pid)
            if len(self.temp) == 3:
                self.finish_abis(*self.temp)
            self.update()
            return
        if t in ("perp", "par"):
            if not self.temp:
                pid = self.snap_point(wp)
                if pid:
                    self.temp = [pid]
                    self.status.emit("이제 직선·선분" + ("(입체는 모서리나 면)" if t == "perp" else "") + "을 클릭하세요.")
                    self.update()
                return
            P = self.temp[0]
            po = doc.objects[P]
            if t == "perp" and po.get("solid") is not None:
                if self.perp_3d(P, wp):
                    return
            h = self.hit(wp, kinds=("segment",))
            if not h:
                se = self.solid_edge_at(wp)
                if se:
                    sid, i, j = se
                    self.win.checkpoint()
                    a = M.make_attached_point(doc, sid, sv=i)
                    b = M.make_attached_point(doc, sid, sv=j)
                    self.finish_line_rel(t, P, a, b)
                    return
                self.status.emit("직선이나 선분을 클릭하세요.")
                return
            seg = doc.objects[h[0]]
            self.finish_line_rel(t, P, seg["a"], seg["b"])
            return
        if t == "tan":
            if not self.temp:
                pid = self.snap_point(wp)
                if pid:
                    self.temp = [pid]
                    self.status.emit("이제 원을 클릭하세요.")
                    self.update()
                return
            near = [oid for _d, oid in self.near_prims(wp) if doc.objects[oid]["type"] in ("circle", "arc")]
            if not near:
                self.status.emit("원을 클릭하세요.")
                return
            P, cir = self.temp[0], near[0]
            geo = Geo(doc)
            pr = geo.prim(cir)
            dist = length(geo.P(P) - pr[1])
            if dist < pr[2] - 2:
                self.status.emit("점이 원 안에 있어 접선을 그을 수 없습니다.")
                self.temp = []
                return
            self.win.checkpoint()
            sel = []
            if dist <= pr[2] + 2:       # 원 위의 점: 반지름에 수직인 직선
                cen = doc.objects[cir]["c"]
                q = M.make_dep_point(doc, {"t": "dir", "base": P, "a": cen, "b": P, "mode": "perp"}, show=False)
                sel.append(M.make_segment(doc, P, q, kind="line"))
            else:
                for k in (0, 1):
                    tp = M.make_dep_point(doc, {"t": "tan", "p": P, "obj": cir, "k": k})
                    sel += [tp, M.make_segment(doc, P, tp, kind="line")]
            self.after_construct(sel)
            return
        if t == "copyseg":
            # temp: [A, B] (원래 선분) → [A, B, P] → 방향 D
            if len(self.temp) < 2:
                if not self.temp:
                    pid = self.pick_point(wp)
                    if not pid:
                        h = self.hit(wp, kinds=("segment",))
                        if h:
                            seg = doc.objects[h[0]]
                            self.temp = [seg["a"], seg["b"]]
                            self.status.emit("옮길 선분을 골랐습니다. 새 시작점을 클릭하세요.")
                            self.update()
                        return
                    self.temp = [pid]
                    self.update()
                    return
                pid = self.snap_point(wp)
                if pid and pid != self.temp[0]:
                    self.temp.append(pid)
                    self.status.emit("새 시작점을 클릭하세요.")
                    self.update()
                return
            pid, _c = self.get_or_make(wp, self.alt_now())
            if len(self.temp) == 2:
                self.temp.append(pid)
                self.status.emit("선분을 놓을 방향을 클릭하세요.")
                self.notify()
                return
            A, B, P = self.temp
            if pid == P:
                return
            ray = M.make_segment(doc, P, pid, kind="ray")
            q = M.make_dep_point(doc, {"t": "copylen", "p": P, "q": pid, "a": A, "b": B})
            if doc.settings.get("construction_traces", True):
                M.make_trace(doc, "mark", c=P, p=q)
            seg = M.make_segment(doc, P, q)
            self.after_construct([q, seg])
            return
        if t == "copyang":
            # temp: [A, V, B] (원래 각) → [.., P] → 방향 D
            if len(self.temp) < 3:
                if not self.temp:
                    h = self.hit(wp, kinds=("angle",))
                    if h and not self.pick_point(wp):
                        an = doc.objects[h[0]]
                        self.temp = [an["a"], an["v"], an["b"]]
                        self.status.emit("옮길 각을 골랐습니다. 새 꼭짓점을 클릭하세요.")
                        self.update()
                        return
                pid = self.snap_point(wp)
                if pid and pid not in self.temp:
                    self.temp.append(pid)
                    if len(self.temp) == 3:
                        self.status.emit("새 꼭짓점을 클릭하세요.")
                    self.update()
                return
            pid, _c = self.get_or_make(wp, self.alt_now())
            if len(self.temp) == 3:
                self.temp.append(pid)
                self.status.emit("한 변의 방향을 클릭하세요.")
                self.notify()
                return
            A, V, B, P = self.temp
            if pid == P:
                return
            M.make_segment(doc, P, pid, kind="ray")
            q = M.make_dep_point(doc, {"t": "copyang", "a": A, "v": V, "b": B, "p": P, "q": pid}, show=False)
            ray2 = M.make_segment(doc, P, q, kind="ray")
            if doc.settings.get("construction_traces", True):
                M.make_trace(doc, "copyang", a=A, v=V, b=B, p=P, q=pid)
            self.after_construct([ray2])
            return
        if t == "inter":
            near = self.near_prims(wp)
            if not self.temp:
                if len(near) >= 2:
                    pid = self.make_intersection(near[0][1], near[1][1], wp)
                    if pid:
                        self.after_construct([pid])
                    return
                if near:
                    self.temp = [near[0][1]]
                    self.status.emit("두 번째 선·원을 클릭하세요.")
                    self.update()
                return
            cand = [oid for _d, oid in near if oid != self.temp[0]]
            if cand:
                pid = self.make_intersection(self.temp[0], cand[0], wp)
                self.temp = []
                if pid:
                    self.after_construct([pid])

    def after_construct(self, sel):
        self.temp, self.temp_created = [], []
        self.set_selection([i for i in sel if i in self.doc.objects])
        self.notify()
        self.done_shape()

    def finish_two(self, t, a, b):
        doc = self.doc
        self.win.checkpoint()
        if t == "mid":
            m_ = M.make_dep_point(doc, {"t": "mid", "a": a, "b": b})
            self.after_construct([m_])
            return
        m_ = M.make_dep_point(doc, {"t": "mid", "a": a, "b": b}, show=False)
        q = M.make_dep_point(doc, {"t": "dir", "base": m_, "a": a, "b": b, "mode": "perp"}, show=False)
        line = M.make_segment(doc, m_, q, kind="line")
        sel = [line]
        if doc.settings.get("construction_traces", True):
            sel.append(M.make_trace(doc, "pbis", a=a, b=b))
        self.after_construct([line])

    def finish_abis(self, a, v, b):
        doc = self.doc
        self.win.checkpoint()
        q = M.make_dep_point(doc, {"t": "bis", "a": a, "v": v, "b": b}, show=False)
        ray = M.make_segment(doc, v, q, kind="ray")
        if doc.settings.get("construction_traces", True):
            M.make_trace(doc, "abis", a=a, v=v, b=b)
        self.after_construct([ray])

    def finish_line_rel(self, t, P, a, b):
        doc = self.doc
        self.win.checkpoint()
        if t == "par":
            q = M.make_dep_point(doc, {"t": "dir", "base": P, "a": a, "b": b, "mode": "par"}, show=False)
            self.after_construct([M.make_segment(doc, P, q, kind="line")])
            return
        geo = Geo(doc)
        Pp, A, B = geo.P(P), geo.P(a), geo.P(b)
        d = norm(B - A)
        F = A + d * dot(Pp - A, d)
        if length(Pp - F) < 2:      # 점이 직선 위에 있으면: 그 점을 지나는 수선
            q = M.make_dep_point(doc, {"t": "dir", "base": P, "a": a, "b": b, "mode": "perp"}, show=False)
            sel = [M.make_segment(doc, P, q, kind="line")]
        else:
            f = M.make_dep_point(doc, {"t": "foot", "p": P, "a": a, "b": b})
            seg = M.make_segment(doc, P, f)
            other = a if length(A - F) >= length(B - F) else b
            M.make_angle(doc, P, f, other, auto_swap=True)
            sel = [f, seg]
        if doc.settings.get("construction_traces", True):
            M.make_trace(doc, "perp", p=P, a=a, b=b)
        self.after_construct(sel)

    def perp_3d(self, P, wp):
        """입체 위의 점에서 모서리나 면에 내린 수선"""
        doc = self.doc
        po = doc.objects[P]
        sid = po["solid"]
        so = doc.objects.get(sid)
        if not so:
            return False
        skip = ()
        if po.get("sv") is not None:
            skip = (po["sv"],)
        elif po.get("edge"):
            skip = tuple(po["edge"])
        se = self.solid_edge_at(wp, only_sid=sid, visible_only=True, skip_v=skip)
        self.win.checkpoint()
        if se:
            _s, i, j = se
            a = M.make_attached_point(doc, sid, sv=i)
            b = M.make_attached_point(doc, sid, sv=j)
            f = M.make_point(doc, 0, 0)
            fo = doc.objects[f]
            fo["solid"] = sid
            fo["dep3"] = {"t": "foot_line", "p": P, "a": a, "b": b}
            Geo(doc)
            other = a if M.dist_units(doc, a, f) >= M.dist_units(doc, b, f) else b
        else:
            mesh = S.build(so["kind"], so["params"])
            Pxyz = M.attached_xyz(doc, po)
            g = None
            info = Geo(doc).solid(so)
            # 클릭한 곳의 면들 중 (앞쪽 먼저) 시작점이 들어 있지 않은 면 → 예: 겨냥도에서 꼭짓점 → 밑면(높이)
            for front_first in (True, False):
                for gname, front, poly in info["faces"]:
                    if front != front_first or not poly.containsPoint(wp, Qt.OddEvenFill):
                        continue
                    f_ = next((ff for ff, gg in zip(mesh.faces, mesh.groups) if gg == gname), None)
                    if not f_ or Pxyz is None:
                        continue
                    n_ = S.newell(mesh, f_)
                    L_ = math.sqrt(sum(q * q for q in n_)) or 1
                    p0 = mesh.v[f_[0]]
                    if abs(sum((Pxyz[k] - p0[k]) * n_[k] for k in range(3)) / L_) > 1e-6:
                        g = gname
                        break
                if g:
                    break
            if not g:
                return False
            face = next((f_ for f_, gg in zip(mesh.faces, mesh.groups) if gg == g), None)
            f = M.make_point(doc, 0, 0)
            fo = doc.objects[f]
            fo["solid"] = sid
            fo["dep3"] = {"t": "foot_face", "p": P, "face": g}
            other = None
            if face:
                Geo(doc)
                cands = [vi for vi in face if vi < len(mesh.v)]
                vi = max(cands, key=lambda v_: math.dist(mesh.v[v_], M.attached_xyz(doc, fo) or (0, 0, 0)))
                other = M.make_attached_point(doc, sid, sv=vi)
        Geo(doc)
        seg = M.make_segment(doc, P, f)
        # 입체 안을 지나는 수선은 점선 (교과서처럼). 같은 면 위에 있으면 실선
        inside = True
        if se and po.get("sv") is not None:
            mesh_ = S.build(so["kind"], so["params"])
            inside = not any(po["sv"] in ff and se[1] in ff and se[2] in ff for ff in mesh_.faces)
        if inside:
            doc.objects[seg]["style"]["dash"] = "dash"
        if other is not None and M.dist_units(doc, other, f) > 1e-6:
            M.make_angle(doc, P, f, other, auto_swap=True)
        self.after_construct([f, seg])
        self.status.emit(f"수선의 발을 만들었습니다. 길이 = {M.fmt_len(doc, M.dist_units(doc, P, f))}")
        return True

    # ------------------------------------------------------------ 컴퍼스
    def press_compass(self, wp):
        if self.compass_measure is not None:
            pid = self.snap_point(wp)
            if not pid:
                return
            self.compass_measure.append(pid)
            if len(self.compass_measure) == 2:
                a, b = self.compass_measure
                self.compass_measure = None
                r = M.dist_units(self.doc, a, b)
                if r > 0.01:
                    self.compass_r = round(r, 3)
                    if self.on_compass_width:
                        self.on_compass_width(self.compass_r)
                    self.status.emit(f"컴퍼스 너비를 {self.compass_r:.2f} cm 로 맞췄습니다. 이제 고정점을 클릭하세요.")
            self.update()
            return
        from PySide6.QtWidgets import QApplication
        shift = bool(QApplication.keyboardModifiers() & Qt.ShiftModifier)
        if self.compass_pivot is None or shift or self.compass_pivot not in self.doc.objects:
            pid = self.snap_point(wp)
            if not pid:
                self.win.checkpoint()
                q = self.snap(wp, self.alt_now())
                pid = M.make_point(self.doc, q.x(), q.y())
            self.compass_pivot = pid
            self.status.emit("고정점을 잡았습니다. 끌어서 돌리면 호가 그려집니다. (Shift+클릭: 고정점 바꾸기, Esc: 풀기)")
            self.notify()
            return
        C = QPointF(*self.doc.xy(self.compass_pivot))
        a = math.degrees(math.atan2(-(wp.y() - C.y()), wp.x() - C.x()))
        self.compass_draw = {"start": a, "sweep": 0.0, "last": a}

    def compass_sweep(self, wp):
        C = QPointF(*self.doc.xy(self.compass_pivot))
        a = math.degrees(math.atan2(-(wp.y() - C.y()), wp.x() - C.x()))
        d = (a - self.compass_draw["last"] + 180) % 360 - 180
        self.compass_draw["sweep"] = max(-360.0, min(360.0, self.compass_draw["sweep"] + d))
        self.compass_draw["last"] = a

    def compass_finish(self):
        cd = self.compass_draw
        self.compass_draw = None
        sw = cd["sweep"]
        if abs(sw) < 2:
            self.update()
            return
        self.win.checkpoint()
        a0 = cd["start"] if sw > 0 else cd["start"] + sw
        aid = self.doc.add({"type": "arc", "c": self.compass_pivot, "r": float(self.compass_r),
                            "a0": a0, "span": min(360.0, abs(sw)), "sector": False, "reverse": False,
                            "style": M.new_style(self.doc), "fill": "#4a90e2", "alpha": 0})
        self.selection = [aid]
        self.selectionChanged.emit()
        self.notify()

    def draw_compass(self, p, geo):
        """화면에만 보이는 컴퍼스 그림 (그림 저장에는 들어가지 않음)"""
        R = float(self.compass_r) * M.GRID
        if self.compass_pivot in self.doc.objects:
            C = geo.P(self.compass_pivot)
            if self.compass_draw is not None:
                ang = self.compass_draw["last"]
                cd = self.compass_draw
                sw = cd["sweep"]
                rc = QRectF(C.x() - R, C.y() - R, 2 * R, 2 * R)
                path = QPainterPath()
                path.arcMoveTo(rc, cd["start"])
                path.arcTo(rc, cd["start"], sw)
                p.setPen(QPen(QColor(0, 0, 0), 2))
                p.setBrush(Qt.NoBrush)
                p.drawPath(path)
            else:
                v = self.mouse - C
                ang = math.degrees(math.atan2(-v.y(), v.x())) if length(v) > 1 else 0.0
            alpha = 220
        else:
            C = self.mouse
            ang = 0.0
            alpha = 110
        if self.compass_measure is not None:
            p.setPen(QPen(QColor(230, 90, 20), 2 / self.scale))
            p.setBrush(QColor(230, 90, 20, 50))
            for i in self.compass_measure:
                if i in self.doc.objects:
                    p.drawEllipse(geo.P(i), 7 / self.scale, 7 / self.scale)
        T = C + dir_deg(ang) * R              # 연필 끝
        mid = (C + T) * 0.5
        u = norm(T - C) if R > 1 else QPointF(1, 0)
        n = perp(u)
        if n.y() > 0:
            n = n * -1
        Lg = max(R / 2 + 25, R * 0.72)
        h = math.sqrt(max(Lg * Lg - (R / 2) ** 2, 100))
        H = mid + n * h                      # 손잡이 쪽 경첩
        # 다리
        pen = QPen(QColor(90, 100, 115, alpha), 4)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(H, C + norm(H - C) * 10)
        p.drawLine(H, T + norm(H - T) * 16)
        # 바늘
        p.setPen(QPen(QColor(40, 40, 40, alpha), 1.6))
        p.drawLine(C + norm(H - C) * 10, C)
        # 연필
        p.setPen(QPen(QColor(230, 170, 30, alpha), 5))
        p.drawLine(T + norm(H - T) * 16, T + norm(H - T) * 5)
        p.setPen(QPen(QColor(60, 60, 60, alpha), 2))
        p.drawLine(T + norm(H - T) * 5, T)
        # 경첩과 손잡이
        p.setPen(QPen(QColor(60, 70, 85, alpha), 1.5))
        p.setBrush(QColor(200, 205, 215, alpha))
        p.drawEllipse(H, 6, 6)
        p.drawLine(H, H + n * 16)
        # 너비 글자
        p.setPen(QColor(230, 90, 20, alpha))
        f = p.font()
        f.setPixelSize(12)
        p.setFont(f)
        p.drawText(mid + n * -14 + QPointF(-20, 0), f"{self.compass_r:.1f} cm")

    def start_cut_pick(self, sid):
        self.win.choose_tool("select")
        self.cut_pick = {"sid": sid, "pts": []}
        self.setCursor(Qt.CrossCursor)
        self.status.emit("자를 평면이 지나는 점 3개를 클릭하세요 (꼭짓점 또는 모서리 위). Esc: 취소")
        self.update()

    def press_cut_pick(self, wp):
        cp = self.cut_pick
        pid = self.snap_point(wp, only_sid=cp["sid"])
        if not pid:
            self.status.emit("입체도형의 꼭짓점이나 모서리 위를 클릭하세요. (Esc: 취소)")
            return
        if pid in cp["pts"]:
            return
        cp["pts"].append(pid)
        self.status.emit(f"자르기 점 {len(cp['pts'])}/3")
        if len(cp["pts"]) == 3:
            o = self.doc.objects.get(cp["sid"])
            self.cut_pick = None
            self.setCursor(Qt.ArrowCursor)
            if o:
                self.win.checkpoint()
                cut = M.default_cut("points")
                cut["pts"] = list(cp["pts"])
                o["cut"] = cut
                self.set_selection([o["id"]])
                sec = Geo(self.doc).solid(o)["section"]
                if sec and sec.get("name"):
                    self.status.emit(f"잘랐습니다. 단면: {sec['name']}  (점을 모서리를 따라 끌면 단면이 바뀝니다)")
                else:
                    self.status.emit("세 점이 한 직선 위에 있거나 입체를 지나지 않아 자를 수 없습니다.")
        self.notify()

    def done_shape(self):
        """도형 하나를 다 그리면 선택 도구로 (Shift 를 누르고 있으면 도구 유지)"""
        from PySide6.QtWidgets import QApplication
        if self.tool == "compass" or (QApplication.keyboardModifiers() & Qt.ShiftModifier
                                       and self.tool not in ("segment", "line", "ray")):
            return
        QTimer.singleShot(0, lambda: self.win.choose_tool("select"))

    def finish_polygon(self):
        if self.tool != "polygon":
            return
        ids = [i for i in self.temp if i in self.doc.objects]
        if len(ids) < 3:
            self.status.emit("다각형은 꼭짓점이 3개 이상 필요합니다.")
            return
        self.win.checkpoint()
        poly = M.make_polygon(self.doc, ids)
        self.temp, self.temp_created = [], []
        self.set_selection([poly])
        self.notify()
        self.done_shape()

    # ------------------------------------------------------------ 키보드
    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Shift:
            self.update()
        if k == Qt.Key_Space and not e.isAutoRepeat():
            self.space_down = True
            self.setCursor(Qt.OpenHandCursor)
            return
        if k == Qt.Key_Escape:
            if self.edge_pick:
                self.edge_pick = None
                self.status.emit("선 고르기를 끝냈습니다.")
                self.selectionChanged.emit()
                self.update()
                return
            if self.tool == "compass" and (self.compass_pivot or self.compass_measure is not None):
                self.compass_pivot = None
                self.compass_measure = None
                self.status.emit("고정점을 풀었습니다. 새 고정점을 클릭하세요.")
                self.update()
                return
            if self.cut_pick:
                self.cut_pick = None
                self.setCursor(Qt.ArrowCursor)
                self.status.emit("자르기를 취소했습니다.")
                self.update()
                return
            if self.rotating:
                self.rotating = None
                self.status.emit("회전 모드를 끝냈습니다.")
                self.update()
                return
            if self.temp:
                self.cancel_temp()
            elif self.tool != "select":
                self.win.choose_tool("select")
            elif self.selection:
                self.set_selection([])
            return
        if k in (Qt.Key_Return, Qt.Key_Enter):
            self.finish_polygon()
            return
        if k in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down) and self.selection:
            step = 10.0 if e.modifiers() & Qt.ShiftModifier else 1.0
            dx = {Qt.Key_Left: -step, Qt.Key_Right: step}.get(k, 0.0)
            dy = {Qt.Key_Up: -step, Qt.Key_Down: step}.get(k, 0.0)
            self.win.checkpoint("nudge")
            self.nudge(dx, dy)
            return
        super().keyPressEvent(e)

    def leaveEvent(self, e):
        if self.tool == "solid":
            self.update()
        super().leaveEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self.space_down = False
            self.setCursor(Qt.ArrowCursor if self.tool == "select" else Qt.CrossCursor)
            return
        super().keyReleaseEvent(e)

    def nudge(self, dx, dy):
        doc = self.doc
        movers = set()
        for i in self.selection:
            o = doc.objects.get(i)
            if not o:
                continue
            if o["type"] in ("text", "measure", "solid", "net"):
                movers.add(i)
            elif o["type"] not in ("brace", "angle", "tick"):
                movers |= doc.point_ids_of([i])
        for i in movers:
            doc.objects[i]["x"] += dx
            doc.objects[i]["y"] += dy
        self.notify()

    # ------------------------------------------------------------ 오른쪽 클릭
    def context_menu(self, sp):
        wp = self.to_world(sp)
        h = self.hit(wp)
        menu = QMenu(self)
        w = self.win
        if h:
            oid = h[0]
            if oid not in self.selection:
                self.set_selection([oid])
            o = self.doc.objects[oid]
            t = o["type"]
            if t == "point":
                menu.addAction("이름 바꾸기", lambda: w.rename_point(oid))
            if t == "segment":
                menu.addAction("길이 표시 (중괄호/호)", lambda: w.add_brace(o["a"], o["b"]))
                menu.addAction("같은 길이 눈금 추가", lambda: w.add_tick(oid))
                menu.addAction("길이 측정값 표시", lambda: w.add_measure(oid, "length"))
            if t == "polygon":
                menu.addAction("모든 변에 길이 표시", lambda: w.polygon_braces(oid))
                menu.addAction("모든 내각 표시", lambda: w.polygon_angles(oid))
                menu.addAction("넓이 측정값 표시", lambda: w.add_measure(oid, "area"))
            if t == "angle":
                menu.addAction("각도 측정값 표시", lambda: w.add_measure(oid, "angle"))
            if t == "text":
                menu.addAction("글자 고치기", lambda: w.edit_text(oid))
            if t == "solid":
                menu.addAction("회전 모드 (더블클릭)", lambda: (setattr(self, "rotating", oid), self.update()))
                menu.addAction("겨냥도로 보기", lambda: w.solid_view(oid, "oblique"))
                menu.addAction("부피 표시", lambda: w.add_measure(oid, "volume"))
                menu.addAction("겉넓이 표시", lambda: w.add_measure(oid, "surface"))
            menu.addSeparator()
            menu.addAction("복사", w.copy_selection)
            menu.addAction("숨기기", w.hide_selection)
            menu.addAction("삭제", w.delete_selection)
        else:
            menu.addAction("붙여넣기", w.paste)
            menu.addAction("모두 선택", w.select_all)
            menu.addAction("전체 보기", w.zoom_fit)
            menu.addAction("숨긴 개체 모두 보이기", w.show_all_hidden)
        menu.exec(self.mapToGlobal(sp.toPoint()))
