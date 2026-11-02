"""도형그리기 - 오른쪽 속성 패널"""
import math

from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QMenu, QWidgetAction, QToolButton, QSizePolicy
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QGroupBox, QLabel, QPushButton, QDoubleSpinBox, QSpinBox,
                               QComboBox, QCheckBox, QLineEdit, QColorDialog, QFontComboBox,
                               QSlider, QPlainTextEdit, QGridLayout)

import model as M
import solid as S
from render import Geo


QUICK_COLORS = ["#000000", "#d0021b", "#1a4fa0", "#2e8b57", "#f5a623", "#9b59b6", "#888888",
                "#4a90e2", "#7ed321", "#ffffff"]


class ColorButton(QPushButton):
    """작은 색 단추: 누르면 자주 쓰는 색 목록 + '다른 색…'"""

    def __init__(self, color, on_change):
        super().__init__()
        self.color = color
        self.on_change = on_change
        self.setFixedSize(34, 20)
        self.setCursor(Qt.PointingHandCursor)
        self.refresh()
        self.clicked.connect(self.popup)

    def refresh(self):
        self.setStyleSheet(f"QPushButton{{background:{self.color}; border:1px solid #888; border-radius:3px;}}")

    def set_color(self, c):
        self.color = c
        self.refresh()
        self.on_change(c)

    def popup(self):
        menu = QMenu(self)
        box = QWidget()
        g = QGridLayout(box)
        g.setContentsMargins(6, 6, 6, 6)
        g.setSpacing(4)
        for k, qc in enumerate(QUICK_COLORS):
            b = QPushButton()
            b.setFixedSize(20, 20)
            b.setStyleSheet(f"background:{qc}; border:1px solid #999; border-radius:10px;")
            b.clicked.connect(lambda _=False, qc=qc: (menu.close(), self.set_color(qc)))
            g.addWidget(b, k // 5, k % 5)
        more = QPushButton("다른 색…")
        more.clicked.connect(lambda _=False: (menu.close(), self.pick()))
        g.addWidget(more, 2, 0, 1, 5)
        act = QWidgetAction(menu)
        act.setDefaultWidget(box)
        menu.addAction(act)
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def pick(self):
        c = QColorDialog.getColor(QColor(self.color), self, "색 선택")
        if c.isValid():
            self.set_color(c.name())


PANEL_CSS = """
QWidget { font-size: 9pt; }
QPushButton { padding: 2px 6px; min-height: 18px; }
QComboBox, QAbstractSpinBox, QLineEdit { min-height: 19px; max-height: 22px; }
QToolButton#grouphead { border: none; font-weight: bold; text-align: left; padding: 3px 2px;
                        background: #eef2f7; border-radius: 3px; }
QToolButton#grouphead:hover { background: #e2e9f3; }
"""


class PropertyPanel(QScrollArea):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setWidgetResizable(True)
        self.setMinimumWidth(130)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._cols = None
        self._rt = QTimer(self)
        self._rt.setSingleShot(True)
        self._rt.setInterval(120)
        self._rt.timeout.connect(self.rebuild)
        self.setStyleSheet(PANEL_CSS)
        self.updaters = []
        self.rebuild()

    # ------------------------------------------------------------ 도우미
    @property
    def doc(self):
        return self.win.doc

    def objs(self):
        return [self.doc.objects[i] for i in self.win.canvas.selection if i in self.doc.objects]

    def apply(self, targets, key, fn):
        if not targets:
            return
        ids = ",".join(str(o["id"]) for o in targets)
        self.win.checkpoint(f"{key}:{ids}")
        for o in targets:
            fn(o)
        self.win.canvas.update()
        self.win.set_modified(True)
        self.refresh_info()

    # 처음에 접혀 있는 그룹 (제목 앞부분) - 사용자가 펼치거나 접으면 기억
    collapsed = {"숨은 선", "면 색칠", "자르기", "겹치기", "꼭짓점", "선의 종류", "보는 방향"}

    def group(self, title):
        key = title.split(" (")[0]
        head = QToolButton()
        head.setObjectName("grouphead")
        head.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        head.setArrowType(Qt.RightArrow if key in PropertyPanel.collapsed else Qt.DownArrow)
        head.setText(title)
        head.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        body = QWidget()
        form = QFormLayout(body)
        form.setContentsMargins(4, 2, 2, 4)
        form.setVerticalSpacing(3)
        form.setHorizontalSpacing(6)
        form.setLabelAlignment(Qt.AlignRight)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        body.setVisible(key not in PropertyPanel.collapsed)

        def toggle():
            vis = not body.isVisible()
            body.setVisible(vis)
            head.setArrowType(Qt.DownArrow if vis else Qt.RightArrow)
            (PropertyPanel.collapsed.discard if vis else PropertyPanel.collapsed.add)(key)
        head.clicked.connect(toggle)
        self.lay.addWidget(head)
        self.lay.addWidget(body)
        return form

    def hrow(self, *items):
        """한 줄에 여러 칸: hrow("굵기", 칸, "종류", 칸, ...)"""
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        for it in items:
            if isinstance(it, str):
                lab = QLabel(it)
                lab.setStyleSheet("color:#444")
                h.addWidget(lab)
            else:
                h.addWidget(it)
        h.addStretch()
        return row

    def color_row(self, targets, key, getter, setter):
        return ColorButton(getter(targets[0]), lambda c: self.apply(targets, key, lambda o: setter(o, c)))

    def spin(self, value, lo, hi, step, on_change, decimals=1, suffix=""):
        s = QDoubleSpinBox() if decimals else QSpinBox()
        if decimals:
            s.setDecimals(decimals)
        s.setRange(lo, hi)
        s.setSingleStep(step)
        s.setValue(value)
        if suffix:
            s.setSuffix(suffix)
        s.setMaximumWidth(96)
        s.valueChanged.connect(on_change)
        return s

    def combo(self, items, current, on_change):
        c = QComboBox()
        for key, name in items:
            c.addItem(name, key)
        idx = max(0, c.findData(current))
        c.setCurrentIndex(idx)
        c.setMaximumWidth(130)
        c.currentIndexChanged.connect(lambda _i: on_change(c.currentData()))
        return c

    def check(self, text, value, on_change):
        c = QCheckBox(text)
        c.setChecked(bool(value))
        c.toggled.connect(on_change)
        return c

    def button(self, text, fn):
        b = QPushButton(text)
        b.clicked.connect(fn)
        return b

    def ncols(self):
        # 스크롤 막대 유무와 상관없는 폭 (막대가 생겼다 없어졌다 하며 다시 그리기를 되풀이하지 않게)
        w = self.width() - 2 * self.frameWidth() - self.verticalScrollBar().sizeHint().width()
        return 3 if w >= 250 else (2 if w >= 165 else 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._cols is not None and self.ncols() != self._cols:
            self._rt.start()

    # ------------------------------------------------------------ 다시 만들기
    def refresh_info(self):
        for f in self.updaters:
            try:
                f()
            except Exception:
                pass

    # 휠로 창을 내릴 때 칸 값이 바뀌지 않게: 칸을 클릭(포커스)한 경우에만 휠로 값 변경
    def eventFilter(self, obj, e):
        if (e.type() == QEvent.Wheel and isinstance(obj, (QAbstractSpinBox, QComboBox, QSlider))
                and not obj.hasFocus()):
            QApplication.sendEvent(self.verticalScrollBar(), e)
            return True
        return super().eventFilter(obj, e)

    def guard_wheel(self, root):
        for wdg in root.findChildren(QWidget):
            if isinstance(wdg, (QAbstractSpinBox, QComboBox, QSlider)):
                wdg.setFocusPolicy(Qt.StrongFocus)
                wdg.installEventFilter(self)

    def setWidget(self, w):
        self.guard_wheel(w)
        for form in w.findChildren(QFormLayout):
            form.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        super().setWidget(w)

    def rebuild(self):
        # 같은 것을 다시 그릴 때는 스크롤 위치를 그대로 두고, 다 만든 뒤 한 번에 바꿔 깜빡이지 않게
        sel_key = tuple(self.win.canvas.selection)
        keep_scroll = sel_key == getattr(self, "_last_sel", None)
        self._last_sel = sel_key
        self._scroll_to = self.verticalScrollBar().value() if keep_scroll else 0
        self.setUpdatesEnabled(False)
        try:
            self._rebuild()
        finally:
            QTimer.singleShot(0, lambda v=self._scroll_to: self.verticalScrollBar().setValue(v))
            self.setUpdatesEnabled(True)

    def _rebuild(self):
        self.updaters = []
        self._cols = self.ncols()
        w = QWidget()
        self.lay = QVBoxLayout(w)
        self.lay.setContentsMargins(4, 4, 4, 4)
        self.lay.setSpacing(2)
        objs = self.objs()
        if not objs:
            lab = QLabel(
                "<b>선택된 개체가 없습니다.</b><br><br>"
                "왼쪽 <b>선택</b> 도구로 도형을 클릭하면<br>여기에서 선 두께, 점선, 색, 글꼴, "
                "이름 등을 바꿀 수 있습니다.<br><br>"
                "· 여러 개: Shift+클릭 또는 빈 곳 드래그<br>"
                "· 전부: Ctrl+A (글꼴을 한꺼번에 바꿀 때)<br>"
                "· 오른쪽 클릭: 바로가기 메뉴<br>"
                "· 이름/글자 수정: 더블클릭<br>"
                "· 글자·중괄호·각 표시는 끌어서 위치 조절")
            lab.setWordWrap(True)
            lab.setTextFormat(Qt.RichText)
            self.lay.addWidget(lab)
            self.lay.addStretch()
            self.setWidget(w)
            return
        types = {o["type"] for o in objs}
        if len(objs) == 1:
            title = M.TYPE_NAMES.get(objs[0]["type"], "")
            if objs[0]["type"] == "point":
                title += f" {objs[0].get('label', '')}"
        else:
            gs = {o.get("group") for o in objs}
            title = (f"그룹 ({len(objs)}개)" if len(gs) == 1 and None not in gs else f"{len(objs)}개 선택됨")
        head = QLabel(f"<span style='font-size:11pt'><b>{title}</b></span>")
        self.lay.addWidget(head)

        if len(objs) == 1:
            self.build_info(objs[0])
        self.build_solid(objs)
        self.build_net(objs)
        self.build_arc(objs)
        self.build_point(objs)
        self.build_line(objs)
        self.build_segment_kind(objs)
        self.build_fill(objs)
        self.build_text_content(objs)
        self.build_brace(objs)
        self.build_angle(objs)
        self.build_tick(objs)
        self.build_font(objs)
        self.build_actions(objs)
        self.lay.addStretch()
        self.setWidget(w)

    # ------------------------------------------------------------ 정보
    def build_info(self, o):
        t = o["type"]
        if t not in ("segment", "polygon", "circle", "angle", "brace", "point", "solid", "arc"):
            return
        form = self.group("측정")
        lab = QLabel()
        lab.setStyleSheet("color:#234")
        lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lab.setWordWrap(True)
        form.addRow(lab)
        doc = self.doc

        def upd():
            if o["id"] not in doc.objects:
                return
            lines = []
            if t == "point":
                lines.append(f"좌표: ({o['x'] / M.GRID:.2f}, {-o['y'] / M.GRID:.2f})")
            elif t in ("segment", "brace"):
                lines.append(M.measure_value_text(doc, o, "length"))
            elif t == "angle":
                lines.append(M.measure_value_text(doc, o, "angle"))
            elif t == "arc":
                for k, _n in M.MEASURE_KINDS["arc"]:
                    lines.append(M.measure_value_text(doc, o, k))
            elif t == "solid":
                lines.append(M.measure_value_text(doc, o, "surface"))
                lines.append(M.measure_value_text(doc, o, "volume"))
            elif t == "circle":
                for k, _ in M.MEASURE_KINDS["circle"]:
                    lines.append(M.measure_value_text(doc, o, k))
            elif t == "polygon":
                lines.append(M.measure_value_text(doc, o, "perimeter"))
                lines.append(M.measure_value_text(doc, o, "area"))
                angs = M.poly_interior_angles(doc, o)
                s = sum(a for _, a in angs)
                lines.append("내각: " + ", ".join(f"∠{doc.label(i)}={M.fmt_angle(doc, a)}" for i, a in angs))
                lines.append(f"내각의 합 = {M.fmt_angle(doc, s)}")
            lab.setText("\n".join(lines))
        upd()
        self.updaters.append(upd)

    # ------------------------------------------------------------ 입체도형
    def build_solid(self, objs):
        tg = [o for o in objs if o["type"] == "solid"]
        if not tg:
            return
        w = self.win
        if len(tg) == 1:
            o = tg[0]
            form = self.group("입체도형 크기 (cm)")

            def set_kind(k):
                def f(ob):
                    ob["kind"] = k
                    ob["params"] = S.default_params(k)
                    ob["labels"] = list(S.build(k, ob["params"]).names)
                    ob["lab_off"] = {}
                    ob["show_labels"] = not S.is_curved(ob)
                    ob.pop("cut", None)
                    ob["face_colors"] = {}
                    ob.pop("edge_styles", None)
                    if S.is_curved(ob):
                        ob["yaw"] = 0.0
                self.apply(tg, "skind", f)
                self.drop_solid_braces(tg)
                QTimer.singleShot(0, self.rebuild)
            form.addRow("종류", self.combo(S.KINDS, o["kind"], set_kind))
            for key, name, _d, lo, hi, is_int in S.PARAMS[o["kind"]]:
                def ch(v, key=key, is_int=is_int):
                    def f(ob):
                        ob["params"][key] = int(v) if is_int else float(v)
                        if is_int:
                            ob["params"].pop("vmove", None)
                            ob["labels"] = list(S.build(ob["kind"], ob["params"]).names)
                            ob["lab_off"] = {}
                            ob.pop("edge_styles", None)
                    self.apply(tg, "sp" + key, f)
                    if is_int:
                        self.drop_solid_braces(tg)
                form.addRow(name, self.spin(o["params"][key], lo, hi, 1 if is_int else 0.5, ch,
                                            decimals=0 if is_int else 1))
            if o["kind"] == "stack":
                self.build_stack_layers(form, tg, o)
            names = QLineEdit(" ".join(o.get("labels", [])))
            names.setToolTip("꼭짓점 이름을 띄어쓰기로 구분해 차례로 적습니다. (밑면 → 윗면 → 꼭대기)")

            def set_names():
                parts = names.text().split()
                def f(ob):
                    labs = list(ob.get("labels", []))
                    for k in range(min(len(labs), len(parts))):
                        labs[k] = parts[k]
                    ob["labels"] = labs
                self.apply(tg, "snames", f)
            names.editingFinished.connect(set_names)
            form.addRow("꼭짓점 이름", names)

        form = self.group("보는 방향 (회전)")
        row = QWidget()
        g = QGridLayout(row)
        g.setContentsMargins(0, 0, 0, 0)
        views = [("겨냥도", "oblique"), ("비스듬히", "iso"), ("앞에서", "front"),
                 ("위에서", "top"), ("옆에서", "side"), ("아래에서", "bottom")]
        frames = []
        for ob in tg:
            fo = S.frame_of(ob, self.doc.objects)
            if fo not in frames:
                frames.append(fo)
        for k, (name, v) in enumerate(views):
            b = QPushButton(name)
            b.clicked.connect(lambda _=False, v=v: (w.solid_view([fo["id"] for fo in frames], v),
                                                   QTimer.singleShot(0, self.rebuild)))
            g.addWidget(b, k // 3, k % 3)
        form.addRow(row)
        o = frames[0]
        for key, name, lo, hi in (("yaw", "좌우 회전", -180, 180), ("pitch", "위아래 기울기", -90, 90)):
            r = QWidget()
            h = QHBoxLayout(r)
            h.setContentsMargins(0, 0, 0, 0)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(lo, hi)
            sl.setValue(int(round(float(o.get(key, 0)))))
            lab = QLabel(f"{sl.value()}°")
            lab.setFixedWidth(40)

            def ch(v, key=key, lab=lab):
                lab.setText(f"{v}°")
                def f(ob):
                    ob[key] = float(v)
                    ob["view"] = "rot"
                self.apply(frames, "s" + key, f)
            sl.valueChanged.connect(ch)
            h.addWidget(sl)
            h.addWidget(lab)
            form.addRow(name, r)
        tip = QLabel("※ 입체도형을 더블클릭하면 회전 모드: 끌어서 돌립니다.")
        tip.setStyleSheet("color:#666")
        tip.setWordWrap(True)
        form.addRow(tip)

        # ---- 놓는 방향 (옆으로 눕히기)
        form = self.group("놓는 방향 (눕히기)")
        orow = QWidget()
        og = QGridLayout(orow)
        og.setContentsMargins(0, 0, 0, 0)
        og.setSpacing(3)
        short_o = {"down": "세우기", "up": "거꾸로", "right": "밑면 →", "left": "← 밑면", "front": "밑면 앞", "back": "밑면 뒤"}
        nc = 3 if (self._cols or 3) >= 2 else 2

        def set_orient(tz, tx):
            def f(ob):
                ob["tz"], ob["tx"] = float(tz), float(tx)
            self.apply(frames, "orient", f)
            QTimer.singleShot(0, self.rebuild)
        for k_, (key, name, tz, tx) in enumerate(S.ORIENTS):
            b = QPushButton(short_o[key])
            b.setToolTip(name)
            b.setMinimumWidth(10)
            b.clicked.connect(lambda _=False, tz=tz, tx=tx: set_orient(tz, tx))
            og.addWidget(b, k_ // nc, k_ % nc)
        form.addRow(orow)
        for key, name, lo, hi in (("tz", "옆으로", -180, 180), ("tx", "앞뒤로", -90, 90)):
            r = QWidget()
            h = QHBoxLayout(r)
            h.setContentsMargins(0, 0, 0, 0)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(lo, hi)
            sl.setValue(int(round(float(o.get(key, 0)))))
            lab = QLabel(f"{sl.value()}°")
            lab.setFixedWidth(36)

            def ch(v, key=key, lab=lab):
                lab.setText(f"{v}°")
                self.apply(frames, "s" + key, lambda ob: ob.__setitem__(key, float(v)))
            sl.valueChanged.connect(ch)
            h.addWidget(sl)
            h.addWidget(lab)
            form.addRow(name, r)
        if any(fo.get("host") is not None for fo in tg):
            tip = QLabel("※ 안에 넣은 입체는 바깥 입체의 방향을 따릅니다.")
            tip.setStyleSheet("color:#666")
            tip.setWordWrap(True)
            form.addRow(tip)

        o = tg[0]
        if len(tg) == 1 and o["kind"] in S.VMOVE_KINDS:
            self.build_vedit(tg, o)
        if len(tg) == 1:
            self.build_edge_pick(tg, o)
        form = self.group("숨은 선 (보이지 않는 모서리)")
        form.addRow(self.check("숨은 선 보이기", o.get("show_hidden", True),
                               lambda v: self.apply(tg, "shid", lambda ob: ob.__setitem__("show_hidden", v))))
        hs = o.get("hid_style", o["style"])
        for ob in tg:
            ob.setdefault("hid_style", dict(ob["style"], dash="dash"))
        form.addRow("굵기", self.spin(hs["width"], 0.25, 12, 0.25,
                                    lambda v: self.apply(tg, "hw", lambda ob: ob["hid_style"].__setitem__("width", v)),
                                    decimals=2))
        form.addRow("종류", self.combo(M.DASH_NAMES, hs.get("dash", "dash"),
                                     lambda v: self.apply(tg, "hd", lambda ob: ob["hid_style"].__setitem__("dash", v))))
        form.addRow("색", self.color_row(tg, "hc", lambda ob: ob["hid_style"]["color"],
                                        lambda ob, c: ob["hid_style"].__setitem__("color", c)))

        form = self.group("꼭짓점")
        form.addRow(self.check("이름 보이기", o.get("show_labels", True),
                               lambda v: self.apply(tg, "slab", lambda ob: ob.__setitem__("show_labels", v))))
        form.addRow(self.check("점 찍기", o.get("show_dots", False),
                               lambda v: self.apply(tg, "sdot", lambda ob: ob.__setitem__("show_dots", v))))
        form.addRow(self.button("이름 위치 자동으로",
                                lambda _=False: self.apply(tg, "sloff", lambda ob: ob.__setitem__("lab_off", {}))))
        if S.build(o["kind"], o["params"]).centers:
            form.addRow(self.check("원의 중심점 보이기", o.get("show_center", False),
                                   lambda v: self.apply(tg, "scen", lambda ob: ob.__setitem__("show_center", v))))
        tip = QLabel("※ 꼭짓점·모서리를 점처럼 클릭해 선분·길이·각 표시를 할 수 있습니다.")
        tip.setStyleSheet("color:#666")
        tip.setWordWrap(True)
        form.addRow(tip)

        # ---- 면 색칠
        form = self.group("면 색칠 (Alt+클릭)")
        crow = QWidget()
        ch_ = QHBoxLayout(crow)
        ch_.setContentsMargins(0, 0, 0, 0)
        cbtn = ColorButton(w.face_color, lambda c: setattr(w, "face_color", c))
        ch_.addWidget(cbtn)
        for qc in ["#f5a623", "#4a90e2", "#7ed321", "#d0021b", "#9b59b6", "#bbbbbb"]:
            b = QPushButton()
            b.setFixedSize(16, 16)
            b.setStyleSheet(f"background:{qc}; border:1px solid #aaa; border-radius:8px;")
            b.clicked.connect(lambda _=False, qc=qc: (setattr(w, "face_color", qc), setattr(cbtn, "color", qc), cbtn.refresh()))
            ch_.addWidget(b)
        ch_.addStretch()
        form.addRow("칠할 색", crow)
        r = QWidget()
        h = QHBoxLayout(r)
        h.setContentsMargins(0, 0, 0, 0)
        sl = QSlider(Qt.Horizontal)
        sl.setRange(5, 100)
        sl.setValue(int(w.face_alpha))
        lab = QLabel(f"{sl.value()}%")
        lab.setFixedWidth(36)
        sl.valueChanged.connect(lambda v: (setattr(w, "face_alpha", v), lab.setText(f"{v}%")))
        h.addWidget(sl)
        h.addWidget(lab)
        form.addRow("진하기", r)
        tip = QLabel("Alt+클릭: 앞쪽 면 칠하기/지우기\nAlt+Shift+클릭: 뒤쪽(가려진) 면")
        tip.setStyleSheet("color:#666")
        form.addRow(tip)
        form.addRow(self.button("면 색 모두 지우기",
                                lambda _=False: self.apply(tg, "fclear", lambda ob: ob.__setitem__("face_colors", {}))))

        if len(tg) == 1:
            self.build_cut(tg, o)
            self.build_nest(tg, o)

    # ------------------------------------------------------------ 자르기
    def build_cut(self, tg, o):
        w = self.win
        form = self.group("자르기")
        row = QWidget()
        g = QHBoxLayout(row)
        g.setContentsMargins(0, 0, 0, 0)
        b1 = self.button("점 3개로 자르기", lambda _=False: w.canvas.start_cut_pick(o["id"]))
        b2 = self.button("방향으로 자르기", lambda _=False: (self.apply(tg, "cutp", lambda ob: ob.__setitem__("cut", M.default_cut("plane"))),
                                                         QTimer.singleShot(0, self.rebuild)))
        g.addWidget(b1)
        g.addWidget(b2)
        form.addRow(row)
        cut = o.get("cut")
        if not cut:
            tip = QLabel("점 3개: 꼭짓점이나 모서리 위를 차례로 클릭\n방향: 기울기·방향·위치를 슬라이더로")
            tip.setStyleSheet("color:#666")
            form.addRow(tip)
            return
        from render import Geo as _G
        info = _G(self.doc).solid(o)
        s = info.get("section")
        lab = QLabel()
        lab.setWordWrap(True)
        if s and s.get("name"):
            lab.setText(f"<b>단면: {s['name']}</b><br>넓이 = {M.fmt_area(self.doc, s['area'])}")
        else:
            lab.setText("<span style='color:#c0392b'>평면이 입체를 지나지 않습니다.</span>")
        form.addRow(lab)

        def upd():
            if o["id"] not in self.doc.objects:
                return
            s2 = _G(self.doc).solid(o).get("section")
            if s2 and s2.get("name"):
                lab.setText(f"<b>단면: {s2['name']}</b><br>넓이 = {M.fmt_area(self.doc, s2['area'])}")
        self.updaters.append(upd)

        def setc(key, val):
            self.apply(tg, "cut" + key, lambda ob: ob["cut"].__setitem__(key, val))
            upd()
        if cut.get("mode") == "plane":
            pre = QWidget()
            pg = QHBoxLayout(pre)
            pg.setContentsMargins(0, 0, 0, 0)
            for name, tilt in (("수평", 0.0), ("수직", 90.0), ("비스듬히", 40.0)):
                pg.addWidget(self.button(name, lambda _=False, t=tilt: (setc("tilt", t), QTimer.singleShot(0, self.rebuild))))
            form.addRow(pre)
            for key, name, lo, hi, mul in (("tilt", "기울기", 0, 90, 1), ("turn", "방향", -180, 180, 1),
                                           ("pos", "위치", -100, 100, 100)):
                r = QWidget()
                h = QHBoxLayout(r)
                h.setContentsMargins(0, 0, 0, 0)
                sl = QSlider(Qt.Horizontal)
                sl.setRange(lo, hi)
                sl.setValue(int(round(float(cut.get(key, 0)) * mul)))
                vl = QLabel(str(sl.value()) + ("°" if mul == 1 else "%"))
                vl.setFixedWidth(40)

                def ch(v, key=key, mul=mul, vl=vl):
                    vl.setText(str(v) + ("°" if mul == 1 else "%"))
                    setc(key, v / mul)
                sl.valueChanged.connect(ch)
                h.addWidget(sl)
                h.addWidget(vl)
                form.addRow(name, r)
        else:
            tip = QLabel("자른 점을 모서리를 따라 끌면 단면이 바뀝니다.")
            tip.setStyleSheet("color:#666")
            tip.setWordWrap(True)
            form.addRow(tip)
        form.addRow("보기", self.combo([("both", "두 조각 모두"), ("low", "아래(앞) 조각만"), ("up", "위(뒤) 조각만")],
                                     cut.get("show", "both"), lambda v: setc("show", v)))
        form.addRow("벌리기", self.spin(float(cut.get("gap", 0)), 0, 20, 0.5, lambda v: setc("gap", v), suffix=" cm"))
        form.addRow("단면 색", self.color_row(tg, "cutcol", lambda ob: ob["cut"].get("color", "#f5a623"),
                                           lambda ob, c: ob["cut"].__setitem__("color", c)))
        form.addRow("단면 진하기", self.spin(int(cut.get("alpha", 45)), 0, 100, 5, lambda v: setc("alpha", int(v)),
                                         decimals=0, suffix=" %"))
        form.addRow(self.check("단면 이름을 그림에 쓰기", cut.get("show_name", False), lambda v: setc("show_name", v)))
        form.addRow(self.button("자르기 없애기", lambda _=False: (self.apply(tg, "cutx", lambda ob: ob.pop("cut", None)),
                                                            QTimer.singleShot(0, self.rebuild))))

    # ------------------------------------------------------------ 겹치기(안에 넣기)
    def build_nest(self, tg, o):
        others = [s for s in self.doc.items("solid") if s["id"] != o["id"] and s.get("host") != o["id"]]
        if not others and o.get("host") is None:
            return
        form = self.group("겹치기 (다른 입체 안에 넣기)")
        items = [(None, "넣지 않음")] + [(s["id"], f"{M.solid_name(s)} ({s['id']})") for s in others]

        def set_host(v):
            def f(ob):
                if v is None:
                    hst = self.doc.objects.get(ob.get("host"))
                    ob.pop("host", None)
                    if hst:
                        ob["x"], ob["y"] = hst["x"] + 30, hst["y"]
                else:
                    ob["host"] = v
                    ob.setdefault("align", "bottom")
                    ob.setdefault("inner_line", "solid")
            self.apply(tg, "host", f)
            QTimer.singleShot(0, self.rebuild)
        form.addRow("바깥 입체", self.combo(items, o.get("host"), set_host))
        if o.get("host") is not None:
            form.addRow("맞추기", self.combo([("bottom", "밑면 맞춤"), ("center", "가운데 맞춤")], o.get("align", "bottom"),
                                          lambda v: self.apply(tg, "align", lambda ob: ob.__setitem__("align", v))))
            form.addRow("안쪽 선", self.combo([("solid", "자동 (숨은 선만 점선)"), ("allsolid", "모두 실선"),
                                            ("dash", "모두 점선"), ("hide", "숨김 (색칠만)")],
                                           o.get("inner_line", "solid"),
                                           lambda v: self.apply(tg, "inl", lambda ob: ob.__setitem__("inner_line", v))))
            tip = QLabel("※ 바깥 입체와 함께 움직이고 함께 돕니다.")
            tip.setStyleSheet("color:#666")
            form.addRow(tip)

    # ------------------------------------------------------------ 꼭짓점 옮기기
    def build_vedit(self, tg, o):
        cv = self.win.canvas
        on = cv.vedit == o["id"]
        form = self.group("꼭짓점 옮기기")
        b = self.button("옮기기 끝내기" if on else "꼭짓점 옮기기", lambda _=False: cv.start_vedit(o["id"]))
        if on:
            b.setStyleSheet("background:#d6e6fb; border:1px solid #2f80ed; border-radius:3px;")
        moved = bool(o["params"].get("vmove"))
        rs = self.button("처음 모양으로", lambda _=False: (
            self.apply(tg, "vreset", lambda ob: ob["params"].pop("vmove", None)), QTimer.singleShot(0, self.rebuild)))
        rs.setEnabled(moved)
        form.addRow(self.hrow(b, rs))
        if S.vertex_pair(o["kind"], o["params"], 0) is not None:
            c = self.combo([(True, "기둥 유지 (윗면도 함께)"), (False, "점 하나만")], cv.vkeep,
                           lambda v: setattr(cv, "vkeep", bool(v)))
            form.addRow("방식", c)
        tip = QLabel("네모 손잡이를 끌면 밑면과 나란하게 움직입니다.\nCtrl+끌기: 반대 방식 · 높이는 위 '크기'에서"
                     if on else ("밑면 모양을 바꿨습니다. 겉넓이·부피는 소수로 나옵니다." if moved else
                                 "꼭짓점을 끌어 밑면이 정다각형이 아닌 기둥·뿔을 만듭니다."))
        tip.setStyleSheet("color:#2f80ed" if on else "color:#666")
        tip.setWordWrap(True)
        form.addRow(tip)

    # ------------------------------------------------------------ 선 고르기
    def build_edge_pick(self, tg, o):
        w = self.win
        cv = w.canvas
        ep = cv.edge_pick if cv.edge_pick and cv.edge_pick["sid"] == o["id"] else None
        form = self.group("선마다 실선·점선")
        on = ep is not None
        b = self.button("선 고르기 끝내기" if on else "선 고르기", lambda _=False: cv.start_edge_pick(o["id"]))
        if on:
            b.setStyleSheet("background:#d6e6fb; border:1px solid #2f80ed; border-radius:3px;")
        es = o.get("edge_styles") or {}
        clr = self.button("모두 자동으로", lambda _=False: (self.apply(tg, "esclear", lambda ob: ob.pop("edge_styles", None)),
                                                       QTimer.singleShot(0, self.rebuild)))
        clr.setEnabled(bool(es))
        form.addRow(self.hrow(b, clr))
        if not ep:
            tip = QLabel(f"바꾼 선 {len(es)}개" if es else "보이는 선은 실선, 가려진 선은 점선 (자동)")
            tip.setStyleSheet("color:#666")
            tip.setWordWrap(True)
            form.addRow(tip)
            return
        keys = list(ep["keys"])
        if not keys:
            tip = QLabel("입체도형의 선을 클릭하세요.\nShift+클릭: 여러 개 고르기\n원은 앞쪽 반·뒤쪽 반을 따로 고릅니다.")
            tip.setStyleSheet("color:#2f80ed")
            form.addRow(tip)
            return
        cur = es.get(keys[0]) or {}
        lab = QLabel(f"고른 선 {len(keys)}개")
        lab.setStyleSheet("color:#2f80ed; font-weight:bold")
        form.addRow(lab)

        def setk(field, val):
            def f(ob):
                d = ob.setdefault("edge_styles", {})
                for k in keys:
                    st = dict(d.get(k) or {"mode": "auto"})
                    if val is None:
                        st.pop(field, None)
                    else:
                        st[field] = val
                    if st.get("mode", "auto") == "auto" and not st.get("width") and not st.get("color"):
                        d.pop(k, None)
                    else:
                        d[k] = st
            self.apply(tg, "es" + field, f)
        form.addRow("선", self.combo([("auto", "자동"), ("solid", "실선"), ("dash", "점선"), ("hide", "숨김")],
                                    cur.get("mode", "auto"), lambda v: setk("mode", v)))
        base_w = float(cur.get("width") or o["style"].get("width", 2))
        wrow = self.spin(base_w, 0.25, 12, 0.25, lambda v: setk("width", float(v)), decimals=2)
        col = ColorButton(cur.get("color") or o["style"].get("color", "#000000"), lambda c: setk("color", c))
        form.addRow(self.hrow("굵기", wrow, "색", col))
        form.addRow(self.button("고른 선 자동으로", lambda _=False: (
            self.apply(tg, "esk", lambda ob: [(ob.get("edge_styles") or {}).pop(k, None) for k in keys]),
            QTimer.singleShot(0, self.rebuild))))

    # ------------------------------------------------------------ 쌓기 층
    LAYER_KINDS_C = [("cyl", "원기둥"), ("cone", "원뿔"), ("rcone", "거꾸로 원뿔"), ("frus", "원뿔대"),
                     ("dome", "반구 (위로 볼록)"), ("bowl", "반구 (아래로 볼록)")]
    LAYER_KINDS_P = [("cyl", "각기둥"), ("cone", "각뿔"), ("rcone", "거꾸로 각뿔"), ("frus", "각뿔대"),
                     ("dome", "반구 모양 (위)"), ("bowl", "반구 모양 (아래)")]

    @staticmethod
    def layer_kind(L):
        sh = L.get("shape", "line")
        if sh in ("dome", "bowl"):
            return sh
        r1, r2 = float(L.get("r1", 1)), float(L.get("r2", 1))
        if abs(r1 - r2) < 1e-9:
            return "cyl"
        if r2 <= 1e-9:
            return "cone"
        if r1 <= 1e-9:
            return "rcone"
        return "frus"

    def build_stack_layers(self, form, tg, o):
        def setp(fn, key="stk"):
            def f(ob):
                fn(ob["params"])
                ob["labels"] = list(S.build(ob["kind"], ob["params"]).names)
                ob["lab_off"] = {}
                ob.pop("cut", None)
                ob.pop("edge_styles", None)
            self.apply(tg, key, f)
            self.drop_solid_braces(tg)

        def later():
            QTimer.singleShot(0, self.rebuild)
        poly = int(o["params"].get("n", 0)) > 0
        form.addRow("밑면", self.combo([(0, "원 (회전체)")] + [(k, f"정{k}각형") for k in range(3, 13)],
                                     int(o["params"].get("n", 0)),
                                     lambda v: (setp(lambda pp: pp.__setitem__("n", int(v))), later())))
        presets = [("", "모양 고르기…")] + [(k, k) for k in S.STACK_PRESETS]

        def use_preset(k):
            if k:
                setp(lambda pp: pp.__setitem__("layers", [dict(l) for l in S.STACK_PRESETS[k]]))
                later()
        form.addRow("예시", self.combo(presets, "", use_preset))
        layers = o["params"].get("layers", [])
        kinds = self.LAYER_KINDS_P if poly else self.LAYER_KINDS_C
        rname = "반지름"

        def top_r(idx):
            """idx 층 바로 아래 층의 윗면 반지름 (모양을 바꿀 때 크기를 이어 맞춤)"""
            if idx <= 0:
                return None
            P = layers[idx - 1]
            sh = P.get("shape", "line")
            if sh == "dome":
                return float(P.get("r1", 1.5))
            v = float(P.get("r2", 0))
            return v if v > 1e-9 else (float(P.get("r1", 1.5)) or 1.5)

        def set_kind(idx, kd):
            def fn(pp):
                L = pp["layers"][idx]
                base = top_r(idx) or max(float(L.get("r1", 0)), float(L.get("r2", 0)), 1.5)
                h = float(L.get("h", 2.0))
                if kd == "cyl":
                    L.update(shape="line", r1=base, r2=base, h=h)
                elif kd == "cone":
                    L.update(shape="line", r1=base, r2=0.0, h=h)
                elif kd == "rcone":
                    L.update(shape="line", r1=0.0, r2=base, h=h)
                elif kd == "frus":
                    L.update(shape="line", r1=base, r2=round(base * 0.5, 1), h=h)
                elif kd == "dome":
                    L.update(shape="dome", r1=base, r2=0.0, h=base)
                else:
                    L.update(shape="bowl", r1=0.0, r2=base, h=base)
            setp(fn, key=f"stk{idx}kind")
            later()

        def sp(val, lo, cb):
            b = self.spin(float(val), lo, 30, 0.5, cb, suffix=" cm")
            b.setMinimumWidth(110)
            b.setMaximumWidth(16777215)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setMinimumHeight(24)
            b.setKeyboardTracking(False)     # 숫자를 다 쓰고 Enter·다른 칸으로 옮길 때 반영
            return b
        for idx in range(len(layers) - 1, -1, -1):
            L = layers[idx]
            kd = self.layer_kind(L)

            def setl(key, val, idx=idx):
                setp(lambda pp: pp["layers"][idx].__setitem__(key, val), key=f"stk{idx}{key}")

            def setboth(val, idx=idx):
                def fn(pp):
                    pp["layers"][idx]["r1"] = val
                    pp["layers"][idx]["r2"] = val
                setp(fn, key=f"stk{idx}r")
            box = QWidget()
            vb = QVBoxLayout(box)
            vb.setContentsMargins(0, 2, 0, 2)
            vb.setSpacing(2)
            head = QWidget()
            hh = QHBoxLayout(head)
            hh.setContentsMargins(0, 0, 0, 0)
            hh.setSpacing(3)
            t = QLabel(f"<b>{idx + 1}층</b>")
            t.setFixedWidth(30)
            hh.addWidget(t)
            cb_ = self.combo(kinds, kd, lambda v, idx=idx: set_kind(idx, v))
            cb_.setMinimumWidth(60)
            hh.addWidget(cb_, 1)

            def move(idx, d):
                def fn(pp):
                    j = idx + d
                    pp["layers"][idx], pp["layers"][j] = pp["layers"][j], pp["layers"][idx]
                setp(fn, key="stkmove")
                later()
            for txt, d, ok in (("▲", 1, idx < len(layers) - 1), ("▼", -1, idx > 0)):
                mb = QToolButton()
                mb.setText(txt)
                mb.setToolTip("위층과 바꾸기" if d > 0 else "아래층과 바꾸기")
                mb.setEnabled(ok)
                mb.clicked.connect(lambda _=False, idx=idx, d=d: move(idx, d))
                hh.addWidget(mb)
            xb = QToolButton()
            xb.setText("✕")
            xb.setToolTip("이 층 지우기")
            xb.setEnabled(len(layers) > 1)
            xb.clicked.connect(lambda _=False, idx=idx: (setp(lambda pp: pp["layers"].pop(idx)), later()))
            hh.addWidget(xb)
            vb.addWidget(head)
            H = lambda v, idx=idx: setl("h", v, idx)
            R = lambda key, idx=idx: (lambda v: setl(key, v, idx))
            if kd == "cyl":
                fields = [("반지름", L.get("r1", 1), setboth), ("높이", L.get("h", 1), H)]
            elif kd == "cone":
                fields = [("반지름", L.get("r1", 1), R("r1")), ("높이", L.get("h", 1), H)]
            elif kd == "rcone":
                fields = [("반지름", L.get("r2", 1), R("r2")), ("높이", L.get("h", 1), H)]
            elif kd == "frus":
                fields = [("아랫면 반지름", L.get("r1", 1), R("r1")), ("윗면 반지름", L.get("r2", 1), R("r2")),
                          ("높이", L.get("h", 1), H)]
            else:
                key = "r1" if kd == "dome" else "r2"
                fields = [("반지름", L.get(key, 1), R(key))]
            row = QWidget()
            fl = QFormLayout(row)
            fl.setContentsMargins(8, 0, 0, 0)
            fl.setHorizontalSpacing(6)
            fl.setVerticalSpacing(3)
            fl.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
            fl.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            for nm, val, cb in fields:
                lb = QLabel(nm)
                lb.setStyleSheet("color:#444")
                lb.setMinimumWidth(80)
                lb.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                fl.addRow(lb, sp(val, 0.1, cb))
            vb.addWidget(row)
            if idx:
                line = QWidget()
                line.setFixedHeight(1)
                line.setStyleSheet("background:#dde3ea")
                vb.addWidget(line)
            form.addRow(box)
        form.addRow(self.button("＋ 층 추가 (맨 위)", lambda _=False: (
            setp(lambda pp: pp["layers"].append({"shape": "line", "r1": top_r(len(layers)) or 1.5,
                                                 "r2": top_r(len(layers)) or 1.5, "h": 2.0})),
            later())))

    def drop_solid_braces(self, tg):
        """모양이 바뀌어 꼭짓점 번호가 달라지면 그 입체에 붙인 길이 표시는 지웁니다."""
        ids = {o["id"] for o in tg}
        gone = [b["id"] for b in self.doc.items("brace") if b.get("solid") in ids]
        if gone:
            self.doc.delete(gone)
            self.win.canvas.update()

    # ------------------------------------------------------------ 전개도
    def build_net(self, objs):
        tg = [o for o in objs if o["type"] == "net"]
        if not tg:
            return
        o = tg[0]
        so = self.doc.objects.get(o.get("solid"))
        if not so:
            return
        form = self.group("전개도")
        surf = S.metrics(so["kind"], so["params"])
        lab = QLabel(f"전개도의 넓이 = 겉넓이 = {M.measure_value_text(self.doc, so, 'surface').split('= ', 1)[-1]}")
        lab.setWordWrap(True)
        lab.setStyleSheet("color:#234")
        form.addRow(lab)
        if not S.is_curved(so):
            if so["kind"] in ("cube", "cuboid", "prism", "frustum"):
                form.addRow(self.hrow("펼치기", self.combo(S.NET_LAYOUTS, o.get("layout", "flower"),
                                                       lambda v: self.apply(tg, "nlay", lambda ob: ob.__setitem__("layout", v)))))
            sl = QSlider(Qt.Horizontal)
            sl.setRange(0, 100)
            sl.setValue(int(round(float(o.get("fold", 0)) * 100)))
            sl.setMaximumWidth(130)
            vl = QLabel(f"{sl.value()}%")
            vl.setFixedWidth(34)

            def ch(v):
                vl.setText(f"{v}%")
                self.apply(tg, "nfold", lambda ob: ob.__setitem__("fold", v / 100))
            sl.valueChanged.connect(ch)
            form.addRow(self.hrow("접기", sl, vl))
        form.addRow(self.hrow(
            self.check("꼭짓점 이름", o.get("show_labels", True),
                       lambda v: self.apply(tg, "nlab", lambda ob: ob.__setitem__("show_labels", v))),
            "접는 선", self.combo(M.DASH_NAMES, o.get("fold_dash", "dash"),
                                lambda v: self.apply(tg, "nfd", lambda ob: ob.__setitem__("fold_dash", v)))))

    # ------------------------------------------------------------ 호·부채꼴
    def build_arc(self, objs):
        tg = [o for o in objs if o["type"] == "arc"]
        if not tg:
            return
        form = self.group("호·부채꼴")
        form.addRow("모양", self.combo([(False, "호"), (True, "부채꼴")], bool(tg[0].get("sector")),
                                     lambda v: self.apply(tg, "sector", lambda o: o.__setitem__("sector", bool(v)))))
        form.addRow(self.button("반대쪽 호로 바꾸기",
                                lambda _=False: self.apply(tg, "rev", lambda o: o.__setitem__("reverse", not o.get("reverse")))))

    # ------------------------------------------------------------ 점
    def build_point(self, objs):
        pts = [o for o in objs if o["type"] == "point"]
        if not pts:
            return
        form = self.group("점")
        if len(pts) == 1:
            p = pts[0]
            ed = QLineEdit(p.get("label", ""))
            ed.setPlaceholderText("A, P₁ …")
            ed.setMaximumWidth(80)
            ed.textEdited.connect(lambda s: self.apply(pts, "label", lambda o: o.__setitem__("label", s)))
            syms = []
            for ch in ["₁", "₂", "′", "″"]:
                b = QPushButton(ch)
                b.setFixedWidth(22)
                b.clicked.connect(lambda _=False, ch=ch: (ed.insert(ch), ed.textEdited.emit(ed.text())))
                syms.append(b)
            form.addRow("이름", self.hrow(ed, *syms))
        form.addRow(self.hrow(
            self.check("이름", pts[0].get("show_label", True),
                       lambda v: self.apply(pts, "showlab", lambda o: o.__setitem__("show_label", v))),
            self.check("점", pts[0].get("show_dot", True),
                       lambda v: self.apply(pts, "showdot", lambda o: o.__setitem__("show_dot", v))),
            "크기", self.spin(pts[0].get("size", 3.5), 1, 12, 0.5,
                            lambda v: self.apply(pts, "psize", lambda o: o.__setitem__("size", v))),
            self.color_row(pts, "pcolor", lambda o: o.get("color", "#000000"),
                           lambda o, c: o.__setitem__("color", c))))

        def reset(_=False):
            self.apply(pts, "labreset", lambda o: o.__setitem__("label_auto", True))
        form.addRow(self.hrow(self.button("이름 위치 자동", reset)))

    # ------------------------------------------------------------ 선
    def line_targets(self, objs):
        out, seen = [], set()
        for o in objs:
            cands = []
            if o["type"] in ("segment", "circle", "brace", "angle", "tick", "solid", "arc", "trace", "net"):
                cands = [o]
            elif o["type"] == "polygon":
                ids = o["pts"]
                for k in range(len(ids)):
                    sid = self.doc.find_segment(ids[k], ids[(k + 1) % len(ids)])
                    if sid:
                        cands.append(self.doc.objects[sid])
            for c in cands:
                if c["id"] not in seen:
                    seen.add(c["id"])
                    out.append(c)
        return out

    def build_line(self, objs):
        tg = self.line_targets(objs)
        if not tg:
            return
        title = "선 모양"
        if any(o["type"] == "solid" for o in objs):
            title = "선 모양 (보이는 선)"
        if any(o["type"] == "polygon" for o in objs):
            title += " (변 전체)"
        form = self.group(title)
        st = tg[0]["style"]
        form.addRow(self.hrow(
            "굵기", self.spin(st["width"], 0.25, 12, 0.25,
                            lambda v: self.apply(tg, "width", lambda o: o["style"].__setitem__("width", v)), decimals=2),
            self.combo(M.DASH_NAMES, st.get("dash", "solid"),
                       lambda v: self.apply(tg, "dash", lambda o: o["style"].__setitem__("dash", v))),
            self.color_row(tg, "lcolor", lambda o: o["style"]["color"],
                           lambda o, c: o["style"].__setitem__("color", c))))

    def build_segment_kind(self, objs):
        segs = [o for o in objs if o["type"] == "segment"]
        if not segs:
            return
        form = self.group("선의 종류")
        form.addRow("종류", self.combo([("segment", "선분"), ("line", "직선"), ("ray", "반직선")],
                                     segs[0].get("kind", "segment"),
                                     lambda v: self.apply(segs, "kind", lambda o: o.__setitem__("kind", v))))
        if len(segs) == 1:
            def swap(_=False):
                def f(o):
                    o["a"], o["b"] = o["b"], o["a"]
                self.apply(segs, "swap", f)
            form.addRow(self.button("반직선 방향 바꾸기", swap))

    # ------------------------------------------------------------ 채우기
    def build_fill(self, objs):
        tg = [o for o in objs if o["type"] in ("polygon", "circle", "angle", "solid", "arc", "net")]
        if not tg:
            return
        form = self.group("안쪽 색 채우기")
        sl = QSlider(Qt.Horizontal)
        sl.setRange(0, 100)
        sl.setValue(int(tg[0].get("alpha", 0)))
        sl.setMaximumWidth(110)
        lab = QLabel(f"{sl.value()}%")
        lab.setFixedWidth(32)

        def ch(v):
            lab.setText(f"{v}%")
            self.apply(tg, "alpha", lambda o: o.__setitem__("alpha", v))
        sl.valueChanged.connect(ch)

        def setcol(o, c):
            o["fill"] = c
            if not o.get("alpha"):
                o["alpha"] = 25
                sl.blockSignals(True)
                sl.setValue(25)
                lab.setText("25%")
                sl.blockSignals(False)
        form.addRow(self.hrow(self.color_row(tg, "fill", lambda o: o.get("fill", "#4a90e2"), setcol),
                              "진하기", sl, lab))

    # ------------------------------------------------------------ 글상자
    def build_text_content(self, objs):
        texts = [o for o in objs if o["type"] == "text"]
        if len(texts) != 1:
            return
        form = self.group("글상자 내용")
        ed = QPlainTextEdit(texts[0].get("text", ""))
        ed.setFixedHeight(70)
        ed.textChanged.connect(lambda: self.apply(texts, "text", lambda o: o.__setitem__("text", ed.toPlainText())))
        form.addRow(ed)

    # ------------------------------------------------------------ 중괄호
    def build_brace(self, objs):
        tg = [o for o in objs if o["type"] == "brace"]
        if not tg:
            return
        form = self.group("길이 표시")
        shape = tg[0].get("shape", "arc")

        def set_shape(v):
            self.apply(tg, "bshape", lambda o: o.__setitem__("shape", v))
            QTimer.singleShot(0, self.rebuild)
        ed = QLineEdit(tg[0].get("text", ""))
        ed.setPlaceholderText("직접 입력: 5cm, x …")
        ed.setMaximumWidth(120)
        cb = self.combo([("auto", "실제 길이"), ("custom", "직접 입력"),
                         ("none", "글자 없음")],
                        tg[0].get("text_mode", "auto"),
                        lambda v: self.apply(tg, "bmode", lambda o: o.__setitem__("text_mode", v)))

        def edited(s):
            def f(o):
                o["text"] = s
                o["text_mode"] = "custom" if s else "auto"
            self.apply(tg, "btext", f)
            cb.blockSignals(True)
            cb.setCurrentIndex(cb.findData("custom" if s else "auto"))
            cb.blockSignals(False)
        ed.textEdited.connect(edited)
        form.addRow(self.hrow(self.combo([("brace", "중괄호 ⏞"), ("arc", "호 ⌒")], shape, set_shape), cb))
        form.addRow(self.hrow(ed))
        if shape == "arc":
            geo = Geo(self.doc)
            o0 = tg[0]
            fr = geo.brace_frame(o0)
            h0 = geo.arc_height(o0, fr[2] if fr else 40.0)
            hsp = self.spin(round(h0, 1), 4, 400, 1,
                            lambda v: self.apply(tg, "bah", lambda o: o.__setitem__("arc_height", v)))
            hname = "휘기"
        else:
            hsp = self.spin(tg[0].get("height", 12), 4, 200, 1,
                            lambda v: self.apply(tg, "bh", lambda o: o.__setitem__("height", v)))
            hname = "높이"

        def flip(_=False):
            self.apply(tg, "bflip", lambda o: o.__setitem__("side", -o.get("side", 1)))

        def reset(_=False):
            def f(o):
                o["label_dx"] = o["label_dy"] = 0.0
            self.apply(tg, "breset", f)
        form.addRow(self.hrow(hname, hsp, self.button("뒤집기", flip), self.button("글자 제자리", reset)))

    # ------------------------------------------------------------ 각 표시
    def build_angle(self, objs):
        tg = [o for o in objs if o["type"] == "angle"]
        if not tg:
            return
        form = self.group("각 표시")
        ed = QLineEdit(tg[0].get("text", ""))
        ed.setPlaceholderText("직접 입력: ∠x, 30° …")
        ed.setMaximumWidth(110)
        acb = self.combo([("value", "각의 크기"), ("custom", "직접 입력"), ("none", "글자 없음")],
                         tg[0].get("label_mode", "value"),
                         lambda v: self.apply(tg, "amode", lambda o: o.__setitem__("label_mode", v)))

        def edited(s):
            def f(o):
                o["text"] = s
                o["label_mode"] = "custom" if s else "value"
            self.apply(tg, "atext", f)
            acb.blockSignals(True)
            acb.setCurrentIndex(acb.findData("custom" if s else "value"))
            acb.blockSignals(False)
        ed.textEdited.connect(edited)
        form.addRow(self.hrow(acb, ed))
        syms = []
        for ch in ["∠", "°", "x", "α", "β", "θ", "●"]:
            b = QPushButton(ch)
            b.setFixedWidth(22)
            b.clicked.connect(lambda _=False, ch=ch: (ed.insert(ch), edited(ed.text())))
            syms.append(b)
        form.addRow(self.hrow(*syms))
        place = self.combo([("auto", "위치 자동"), ("inside", "각 안쪽"), ("leader", "화살표로 밖에")],
                           tg[0].get("place", "auto"),
                           lambda v: self.apply(tg, "aplace", lambda o: (o.__setitem__("place", v),
                                                                       o.__setitem__("lu", None),
                                                                       o.__setitem__("lv", None))))
        lsh = self.combo([("line", "직선 화살표"), ("curve", "곡선 화살표")], tg[0].get("leader_shape", "line"),
                         lambda v: self.apply(tg, "lshape", lambda o: o.__setitem__("leader_shape", v)))
        form.addRow(self.hrow(place, lsh))
        form.addRow(self.hrow(
            "화살표", self.spin(tg[0].get("arrow_size", 7.0), 3, 30, 1,
                             lambda v: self.apply(tg, "asize", lambda o: o.__setitem__("arrow_size", v)), decimals=0),
            "호", self.spin(tg[0].get("arcs", 1), 1, 3, 1,
                           lambda v: self.apply(tg, "arcs", lambda o: o.__setitem__("arcs", int(v))), decimals=0),
            "크기", self.spin(tg[0].get("radius", 22), 6, 300, 1,
                            lambda v: self.apply(tg, "rad", lambda o: o.__setitem__("radius", v)), decimals=0)))

        def reset(_=False):
            def f(o):
                o["lu"] = o["lv"] = None
            self.apply(tg, "areset", f)
        form.addRow(self.hrow(
            self.check("직각 ┐", tg[0].get("right_auto", True),
                       lambda v: self.apply(tg, "right", lambda o: o.__setitem__("right_auto", v))),
            self.check("큰 각", tg[0].get("reflex", False),
                       lambda v: self.apply(tg, "reflex", lambda o: (o.__setitem__("reflex", v),
                                                                   o.__setitem__("lu", None),
                                                                   o.__setitem__("lv", None)))),
            self.button("글자 제자리", reset)))

    # ------------------------------------------------------------ 눈금
    def build_tick(self, objs):
        tg = [o for o in objs if o["type"] == "tick"]
        if not tg:
            return
        form = self.group("같은 길이 눈금")
        form.addRow("개수", self.spin(tg[0].get("count", 1), 1, 3, 1,
                                    lambda v: self.apply(tg, "tcount", lambda o: o.__setitem__("count", int(v))),
                                    decimals=0))
        form.addRow("길이", self.spin(tg[0].get("size", 9), 3, 40, 1,
                                    lambda v: self.apply(tg, "tsize", lambda o: o.__setitem__("size", v))))

    # ------------------------------------------------------------ 글꼴
    def build_font(self, objs):
        tg = [o for o in objs if "font" in o]
        if not tg:
            return
        names = {"point": "점 이름", "brace": "길이", "angle": "각", "text": "글상자", "measure": "측정값",
                 "solid": "꼭짓점 이름", "net": "꼭짓점 이름"}
        kinds = sorted({names[o["type"]] for o in tg if o["type"] in names})
        form = self.group("글자 (" + ", ".join(kinds) + ")")
        fd = tg[0]["font"]
        fc = QFontComboBox()
        fc.setMaximumWidth(150)
        fc.setCurrentFont(QFont(fd.get("family", "CMU Serif")))
        fc.currentFontChanged.connect(
            lambda f: self.apply(tg, "family", lambda o: o["font"].__setitem__("family", f.family())))
        sz = self.spin(fd.get("size", 14), 6, 120, 1,
                       lambda v: self.apply(tg, "fsize", lambda o: o["font"].__setitem__("size", v)), decimals=0)
        form.addRow(self.hrow(fc, sz))
        form.addRow(self.hrow(
            self.check("굵게", fd.get("bold"),
                       lambda v: self.apply(tg, "bold", lambda o: o["font"].__setitem__("bold", v))),
            self.check("기울임", fd.get("italic"),
                       lambda v: self.apply(tg, "italic", lambda o: o["font"].__setitem__("italic", v))),
            "색", self.color_row(tg, "tcolor", lambda o: o.get("text_color", "#000000"),
                                lambda o, c: o.__setitem__("text_color", c))))

    # ------------------------------------------------------------ 바로가기 버튼
    def build_actions(self, objs):
        w = self.win
        box = QWidget()
        grid = QGridLayout(box)
        grid.setContentsMargins(0, 4, 0, 0)
        grid.setSpacing(3)
        btns = []
        if len(objs) == 1:
            o = objs[0]
            t = o["type"]
            if t == "segment":
                btns += [("길이 표시", lambda: w.add_brace(o["a"], o["b"])),
                         ("같은 길이 눈금", lambda: w.add_tick(o["id"])),
                         ("길이 측정값 표시", lambda: w.add_measure(o["id"], "length"))]
            elif t == "polygon":
                if len(o["pts"]) == 3:
                    btns += [("외심", lambda: w.tri_center(o["id"], "circum")),
                             ("내심", lambda: w.tri_center(o["id"], "in")),
                             ("무게중심", lambda: w.tri_center(o["id"], "centroid")),
                             ("수심", lambda: w.tri_center(o["id"], "ortho"))]
                btns += [("모든 변에 길이 표시", lambda: w.polygon_braces(o["id"])),
                         ("모든 내각 표시", lambda: w.polygon_angles(o["id"])),
                         ("넓이 표시", lambda: w.add_measure(o["id"], "area")),
                         ("둘레 표시", lambda: w.add_measure(o["id"], "perimeter"))]
            elif t == "circle":
                btns += [("반지름 표시", lambda: w.add_measure(o["id"], "radius")),
                         ("넓이 표시", lambda: w.add_measure(o["id"], "area")),
                         ("원주 표시", lambda: w.add_measure(o["id"], "circumference"))]
            elif t == "angle":
                btns += [("각도 측정값 표시", lambda: w.add_measure(o["id"], "angle"))]
            elif t == "arc":
                btns += [("호의 길이 표시", lambda: w.add_measure(o["id"], "arclen")),
                         ("넓이 표시", lambda: w.add_measure(o["id"], "area"))]
            elif t == "solid":
                btns += [("전개도", lambda: w.add_net(o["id"])),
                         ("부피 표시", lambda: w.add_measure(o["id"], "volume")),
                         ("겉넓이 표시", lambda: w.add_measure(o["id"], "surface"))]
        segs = [o for o in objs if o["type"] == "segment"]
        if len(segs) > 1:
            btns += [("선분마다 같은 눈금", lambda: [w.add_tick(s["id"]) for s in segs])]
        if len(objs) > 1:
            btns += [("그룹으로 묶기", w.group_selection)]
        if any(o.get("group") is not None for o in objs):
            btns += [("그룹 풀기", w.ungroup_selection)]
        btns += [("숨기기", w.hide_selection), ("삭제", w.delete_selection)]
        short = {"길이 측정값 표시": "길이값", "같은 길이 눈금": "같은 길이", "모든 변에 길이 표시": "변 길이 모두",
                 "모든 내각 표시": "내각 모두", "각도 측정값 표시": "각도값", "호의 길이 표시": "호의 길이",
                 "선분마다 같은 눈금": "같은 눈금", "그룹으로 묶기": "그룹"}
        nc = self._cols or 3
        for k, (text, fn) in enumerate(btns):
            b = self.button(short.get(text, text), lambda _=False, fn=fn: fn())
            b.setToolTip(text)
            b.setMinimumWidth(10)
            grid.addWidget(b, k // nc, k % nc)
        self.lay.addWidget(box)
