"""도형그리기 - 수학 수업용 도형 그리기 프로그램 (1단계: 평면도형)

실행:  python main.py
"""
import copy
import json
import math
import os
import sys
import time

from PySide6.QtCore import (Qt, QPointF, QRectF, QSize, QSettings, QTranslator, QLibraryInfo, QBuffer,
                            QIODevice, QMimeData)
from PySide6.QtGui import (QAction, QActionGroup, QColor, QFont, QFontDatabase, QIcon, QImage, QKeySequence,
                           QPainter, QPainterPath, QPen, QPicture, QPixmap, QPolygonF)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QDockWidget, QDoubleSpinBox, QFileDialog, QFontComboBox, QFormLayout,
                               QFrame, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog,
                               QKeySequenceEdit, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
                               QSpinBox, QStyle, QListWidget, QTabBar, QMenu, QSizePolicy, QStyleOptionToolButton, QStylePainter, QTabWidget,
                               QTableWidget, QTableWidgetItem, QTextBrowser, QToolBar, QToolButton,
                               QVBoxLayout, QWidget)

import model as M
import solid as S
from canvas import Canvas
from panel import PropertyPanel
from render import Geo, Renderer, length, norm, perp, dot

APP_NAME = "도형그리기"
APP_VERSION = "1.6"

TOOLS = [
    ("select", "선택", "V"),
    ("point", "점", "P"),
    ("segment", "선분", "S"),
    ("line", "직선", "L"),
    ("ray", "반직선", "R"),
    ("polygon", "다각형", "G"),
    ("regpoly", "정다각형", "N"),
    ("circle", "원", "C"),
    ("arc", "호·부채꼴", "Q"),
    ("solid", "입체도형", "K"),
    None,
    ("mid", "중점", "D"),
    ("pbis", "수직이등분", "H"),
    ("abis", "각이등분", "J"),
    ("perp", "수선", "U"),
    ("par", "평행선", "Y"),
    ("inter", "교점", "I"),
    ("tan", "접선", "W"),
    ("copyseg", "선분 옮기기", "E"),
    ("copyang", "각 옮기기", "F"),
    ("compass", "컴퍼스", "O"),
    None,
    ("brace", "길이 표시", "B"),
    ("angle", "각 표시", "A"),
    ("tick", "같은 길이", "T"),
    ("measure", "측정값", "M"),
    ("text", "글상자", "X"),
]


# ---------------------------------------------------------------- 아이콘
def make_icon(name):
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    ink = QColor("#253858")
    acc = QColor("#2f80ed")
    pen = QPen(ink, 4)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)

    def dotp(x, y, c=acc, r=5):
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawEllipse(QPointF(x, y), r, r)
        p.restore()

    if name == "select":
        p.setBrush(ink)
        p.drawPolygon(QPolygonF([QPointF(18, 8), QPointF(18, 50), QPointF(29, 40), QPointF(37, 56),
                                 QPointF(44, 53), QPointF(36, 37), QPointF(50, 36)]))
    elif name == "point":
        dotp(26, 38, ink, 7)
        p.setFont(QFont("Arial", 20, QFont.Bold))
        p.drawText(QRectF(32, 6, 30, 30), Qt.AlignCenter, "A")
    elif name == "segment":
        p.drawLine(12, 50, 52, 14)
        dotp(12, 50)
        dotp(52, 14)
    elif name == "line":
        p.drawLine(2, 58, 62, 6)
        dotp(20, 42)
        dotp(44, 21)
    elif name == "ray":
        p.drawLine(10, 52, 58, 10)
        p.drawLine(58, 10, 46, 12)
        p.drawLine(58, 10, 55, 22)
        dotp(10, 52)
        dotp(34, 31)
    elif name == "polygon":
        pts = [QPointF(10, 46), QPointF(22, 12), QPointF(52, 18), QPointF(56, 50), QPointF(30, 56)]
        p.setBrush(QColor(47, 128, 237, 50))
        p.drawPolygon(QPolygonF(pts))
        for q in pts:
            dotp(q.x(), q.y(), acc, 4)
    elif name == "regpoly":
        pts = [QPointF(32 + 24 * math.cos(math.radians(90 + 60 * k)), 33 - 24 * math.sin(math.radians(90 + 60 * k)))
               for k in range(6)]
        p.setBrush(QColor(47, 128, 237, 50))
        p.drawPolygon(QPolygonF(pts))
    elif name == "circle":
        p.drawEllipse(QPointF(32, 32), 24, 24)
        dotp(32, 32)
    elif name == "brace":
        p.drawLine(8, 52, 56, 52)
        pen.setWidth(3)
        p.setPen(pen)
        path = QPainterPath(QPointF(8, 44))
        path.quadTo(8, 36, 14, 36)
        path.lineTo(28, 36)
        path.quadTo(32, 36, 32, 28)
        path.quadTo(32, 36, 36, 36)
        path.lineTo(50, 36)
        path.quadTo(56, 36, 56, 44)
        p.drawPath(path)
        p.setFont(QFont("Arial", 13, QFont.Bold))
        p.drawText(QRectF(14, 4, 36, 22), Qt.AlignCenter, "5")
    elif name == "angle":
        p.drawLine(10, 52, 58, 52)
        p.drawLine(10, 52, 44, 12)
        pen.setColor(acc)
        p.setPen(pen)
        p.drawArc(QRectF(-10, 32, 40, 40), 0, 50 * 16)
    elif name == "tick":
        p.drawLine(6, 40, 58, 40)
        pen.setWidth(3)
        p.setPen(pen)
        p.drawLine(28, 30, 28, 50)
        p.drawLine(36, 30, 36, 50)
    elif name == "measure":
        p.setFont(QFont("Arial", 15, QFont.Bold))
        p.drawText(QRectF(0, 4, 64, 30), Qt.AlignCenter, "cm")
        p.drawRect(QRectF(6, 38, 52, 16))
        pen.setWidth(2)
        p.setPen(pen)
        for x in range(12, 56, 8):
            p.drawLine(x, 38, x, 46)
    elif name == "arc":
        path = QPainterPath(QPointF(14, 52))
        path.lineTo(QPointF(14, 14))
        p.drawLine(QPointF(14, 52), QPointF(52, 52))
        p.drawArc(QRectF(-24, 14, 76, 76), 0, 90 * 16)
        dotp(14, 52)
    elif name == "mid":
        p.drawLine(8, 44, 56, 44)
        dotp(8, 44, ink, 4)
        dotp(56, 44, ink, 4)
        dotp(32, 44, acc, 6)
        p.setFont(QFont("Arial", 13, QFont.Bold))
        p.drawText(QRectF(18, 8, 28, 26), Qt.AlignCenter, "M")
    elif name == "pbis":
        p.drawLine(6, 40, 58, 40)
        pen.setColor(acc)
        p.setPen(pen)
        p.drawLine(32, 6, 32, 60)
        pen.setWidth(2)
        p.setPen(pen)
        p.drawRect(32, 32, 8, 8)
    elif name == "abis":
        p.drawLine(8, 54, 58, 54)
        p.drawLine(8, 54, 46, 10)
        pen.setColor(acc)
        p.setPen(pen)
        p.drawLine(8, 54, 60, 30)
    elif name == "perp":
        p.drawLine(4, 52, 60, 52)
        pen.setColor(acc)
        p.setPen(pen)
        p.drawLine(30, 8, 30, 52)
        pen.setWidth(2)
        p.setPen(pen)
        p.drawPolyline(QPolygonF([QPointF(30, 44), QPointF(38, 44), QPointF(38, 52)]))
        dotp(30, 8, ink, 4)
    elif name == "par":
        p.drawLine(4, 48, 60, 36)
        pen.setColor(acc)
        p.setPen(pen)
        p.drawLine(4, 28, 60, 16)
        dotp(30, 22, ink, 4)
    elif name == "inter":
        p.drawLine(6, 54, 58, 10)
        p.drawEllipse(QPointF(30, 34), 20, 20)
        dotp(14, 47, acc, 5)
        dotp(44, 21, acc, 5)
    elif name == "tan":
        p.drawEllipse(QPointF(26, 38), 16, 16)
        pen.setColor(acc)
        p.setPen(pen)
        p.drawLine(4, 22, 60, 6)
        p.drawLine(4, 22, 54, 60)
        dotp(4, 22, ink, 4)
    elif name == "copyseg":
        p.drawLine(6, 18, 40, 18)
        pen.setColor(acc)
        p.setPen(pen)
        p.drawLine(22, 46, 56, 46)
        pen.setWidth(2)
        p.setPen(pen)
        p.drawArc(QRectF(-12, 12, 68, 68), 0, 30 * 16)
    elif name == "copyang":
        p.drawLine(4, 30, 30, 30)
        p.drawLine(4, 30, 24, 12)
        pen.setColor(acc)
        p.setPen(pen)
        p.drawLine(32, 58, 60, 58)
        p.drawLine(32, 58, 52, 40)
    elif name == "compass":
        p.drawLine(32, 8, 16, 56)
        p.drawLine(32, 8, 48, 56)
        pen.setColor(QColor("#e0a020"))
        pen.setWidth(5)
        p.setPen(pen)
        p.drawLine(44, 44, 48, 56)
        dotp(32, 8, ink, 5)
    elif name == "solid":
        p.setBrush(QColor(47, 128, 237, 40))
        p.drawPolygon(QPolygonF([QPointF(10, 22), QPointF(40, 22), QPointF(40, 54), QPointF(10, 54)]))
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(QPolygonF([QPointF(10, 22), QPointF(24, 10), QPointF(54, 10), QPointF(54, 42), QPointF(40, 54)]))
        p.drawLine(QPointF(40, 22), QPointF(54, 10))
        pen.setStyle(Qt.DashLine)
        pen.setWidth(2)
        p.setPen(pen)
        p.drawPolyline(QPolygonF([QPointF(10, 54), QPointF(24, 42), QPointF(54, 42)]))
        p.drawLine(QPointF(24, 42), QPointF(24, 10))
    elif name == "text":
        p.setFont(QFont("Malgun Gothic", 28, QFont.Bold))
        p.drawText(QRectF(0, 0, 64, 64), Qt.AlignCenter, "가")
    p.end()
    return QIcon(pm)


# ---------------------------------------------------------------- 단축키 저장
FIXED_KEYS = {"Esc", "Return", "Enter", "Left", "Right", "Up", "Down", "Space"}


def qsettings():
    return QSettings("Dohyeong", "도형그리기")


def load_shortcuts():
    try:
        return dict(json.loads(qsettings().value("shortcuts", "{}") or "{}"))
    except Exception:
        return {}


def save_shortcuts(d):
    qsettings().setValue("shortcuts", json.dumps(d, ensure_ascii=False))


def shortcut_text(a):
    return a.shortcut().toString(QKeySequence.NativeText)


# ---------------------------------------------------------------- 도구 버튼 (이름 + 작은 단축키)
class ToolButton(QToolButton):
    def __init__(self, action):
        super().__init__()
        self.setDefaultAction(action)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.setIconSize(QSize(24, 24))
        self.setFixedSize(60, 52)
        self.setAutoRaise(True)

    def paintEvent(self, e):
        p = QStylePainter(self)
        opt = QStyleOptionToolButton()
        self.initStyleOption(opt)
        opt.icon = QIcon()
        opt.text = ""
        p.drawComplexControl(QStyle.CC_ToolButton, opt)
        a = self.defaultAction()
        if a.isChecked():
            p.setPen(QPen(QColor("#2f80ed"), 1.2))
            p.setBrush(QColor("#d6e6fb"))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 5, 5)
        pm = a.icon().pixmap(24, 24)
        p.drawPixmap((self.width() - 24) // 2, 3, pm)
        f = QFont(self.font())
        f.setPointSizeF(9)
        p.setFont(f)
        p.setPen(QColor("#1f2d3d"))
        f.setPointSizeF(8.5)
        p.setFont(f)
        p.drawText(QRectF(0, 26, self.width(), 14), Qt.AlignCenter, a.text())
        k = shortcut_text(a)
        if k:
            f.setPointSizeF(7)
            p.setFont(f)
            p.setPen(QColor("#8a94a3"))
            p.drawText(QRectF(0, 39, self.width(), 11), Qt.AlignCenter, k)


# ---------------------------------------------------------------- 입체도형 만들기 창
class SolidDialog(QDialog):
    last_kind = "cuboid"

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("입체도형 만들기")
        lay = QHBoxLayout(self)
        self.list = QListWidget()
        for k, name in S.KINDS:
            self.list.addItem(name)
        self.list.setFixedWidth(140)
        lay.addWidget(self.list)
        right = QVBoxLayout()
        self.form_box = QWidget()
        self.form = QFormLayout(self.form_box)
        right.addWidget(QLabel("크기 (cm)"))
        right.addWidget(self.form_box)
        right.addStretch()
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        lay.addLayout(right)
        self.spins = {}
        self.list.currentRowChanged.connect(self.fill)
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        keys = [k for k, _ in S.KINDS]
        self.list.setCurrentRow(keys.index(SolidDialog.last_kind))
        self.resize(380, 300)

    def kind(self):
        return S.KINDS[self.list.currentRow()][0]

    def fill(self, _row):
        while self.form.rowCount():
            self.form.removeRow(0)
        self.spins = {}
        if self.kind() == "stack":
            self.preset = QComboBox()
            for k in S.STACK_PRESETS:
                self.preset.addItem(k)
            self.form.addRow("모양", self.preset)
            self.base = QComboBox()
            self.base.addItem("원 (회전체)", 0)
            for k in range(3, 13):
                self.base.addItem(f"정{k}각형", k)
            self.form.addRow("밑면", self.base)
            tip = QLabel("층의 종류·크기는 놓은 뒤 속성 창에서 바꿉니다.")
            tip.setWordWrap(True)
            tip.setStyleSheet("color:#666")
            self.form.addRow(tip)
            return
        for key, name, d, lo, hi, is_int in S.PARAMS[self.kind()]:
            s = QSpinBox() if is_int else QDoubleSpinBox()
            if not is_int:
                s.setDecimals(1)
                s.setSingleStep(0.5)
            s.setRange(lo, hi)
            s.setValue(d)
            self.form.addRow(name, s)
            self.spins[key] = (s, is_int)

    def values(self):
        SolidDialog.last_kind = self.kind()
        if self.kind() == "stack":
            layers = [dict(l) for l in S.STACK_PRESETS[self.preset.currentText()]]
            n = self.base.currentData()
            if n:
                for L in layers:
                    if L["shape"] != "line":
                        L.update(shape="line", r1=L.get("r1") or L.get("r2"), r2=L.get("r1") or L.get("r2"))
            return "stack", {"layers": layers, "n": n}
        return self.kind(), {k: (int(s.value()) if i else float(s.value())) for k, (s, i) in self.spins.items()}


# ---------------------------------------------------------------- 설정 창
class SettingsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("환경 설정")
        st = win.doc.settings
        outer = QVBoxLayout(self)
        tabs = QTabWidget()
        outer.addWidget(tabs)

        # ---- 일반
        page = QWidget()
        form = QFormLayout(page)
        self.unit = QComboBox()
        self.unit.setEditable(True)
        self.unit.addItems(["cm", "mm", "m", ""])
        self.unit.setCurrentText(st.get("unit", "cm"))
        form.addRow("길이 단위 (비우면 숫자만)", self.unit)
        self.dec = QSpinBox()
        self.dec.setRange(0, 3)
        self.dec.setValue(st.get("decimals", 1))
        form.addRow("길이 소수점 자리", self.dec)
        self.adec = QSpinBox()
        self.adec.setRange(0, 2)
        self.adec.setValue(st.get("angle_decimals", 0))
        form.addRow("각도 소수점 자리", self.adec)
        self.shape = QComboBox()
        self.shape.addItem("중괄호  ⏞", "brace")
        self.shape.addItem("호  ⌒", "arc")
        self.shape.setCurrentIndex(max(0, self.shape.findData(st.get("length_shape", "brace"))))
        form.addRow("새 길이 표시 기본 모양", self.shape)
        self.font = QFontComboBox()
        self.font.setCurrentFont(QFont(st["font"].get("family", "맑은 고딕")))
        form.addRow("새 글자 기본 글꼴", self.font)
        self.fsize = QSpinBox()
        self.fsize.setRange(6, 120)
        self.fsize.setValue(int(st["font"].get("size", 14)))
        form.addRow("새 글자 기본 크기(pt)", self.fsize)
        self.apply_all = QCheckBox("지금 있는 모든 글자에도 이 글꼴·크기 적용")
        form.addRow(self.apply_all)
        self.lw = QDoubleSpinBox()
        self.lw.setRange(0.25, 12)
        self.lw.setSingleStep(0.25)
        self.lw.setValue(st.get("line_width", 2.0))
        form.addRow("새 선 기본 굵기", self.lw)
        self.scale = QSpinBox()
        self.scale.setRange(1, 6)
        self.scale.setValue(st.get("export_scale", 3))
        form.addRow("그림 내보내기 선명도(배율)", self.scale)
        self.transp = QCheckBox("PNG 저장 시 배경 투명")
        self.transp.setChecked(st.get("png_transparent", True))
        form.addRow(self.transp)
        self.traces = QCheckBox("작도할 때 컴퍼스 흔적(호) 보이기")
        self.traces.setChecked(bool(st.get("construction_traces", True)))
        form.addRow(self.traces)
        self.math = QCheckBox("수식처럼 쓰기 (x, a, θ 기울임 · ° 작은 동그라미)")
        self.math.setChecked(bool(st.get("math_style")))
        form.addRow(self.math)
        self.textbook = False
        tb = QPushButton("교과서 스타일로 맞추기")
        tb.setToolTip("CMU Serif 글꼴(LaTeX 글씨체), 수식처럼 쓰기, 가는 선, 작은 각 표시로 바꿉니다.")
        tb.clicked.connect(self.set_textbook)
        form.addRow(tb)
        tabs.addTab(page, "일반")

        # ---- 단축키
        page = QWidget()
        lay = QVBoxLayout(page)
        info = QLabel("칸을 클릭하고 원하는 키를 누르세요. (지우기: 칸 오른쪽 ✕)\n"
                      "바꿀 수 없는 고정 키: Esc 취소 · Enter 다각형 완성 · 방향키 이동 · "
                      "Space+끌기 화면 이동 · Alt 모눈 무시")
        info.setWordWrap(True)
        lay.addWidget(info)
        defs = win.shortcut_defs
        self.table = QTableWidget(len(defs), 3)
        self.table.setHorizontalHeaderLabels(["분류", "기능", "단축키"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(2, 170)
        self.edits = []
        for r, (sid, group, a, default) in enumerate(defs):
            self.table.setItem(r, 0, QTableWidgetItem(group))
            self.table.setItem(r, 1, QTableWidgetItem(a.text().replace("...", "")))
            for c in (0, 1):
                self.table.item(r, c).setFlags(Qt.ItemIsEnabled)
            ed = QKeySequenceEdit(QKeySequence(win.custom_shortcuts.get(sid, default)))
            if hasattr(ed, "setMaximumSequenceLength"):
                ed.setMaximumSequenceLength(1)
            if hasattr(ed, "setClearButtonEnabled"):
                ed.setClearButtonEnabled(True)
            le = ed.findChild(QLineEdit)
            if le:
                le.setPlaceholderText("키를 누르세요")
            ed.keySequenceChanged.connect(self.check_dupes)
            self.table.setCellWidget(r, 2, ed)
            self.edits.append((sid, default, ed))
        lay.addWidget(self.table)
        row = QHBoxLayout()
        self.dupe_label = QLabel()
        self.dupe_label.setStyleSheet("color:#c0392b")
        self.dupe_label.setWordWrap(True)
        row.addWidget(self.dupe_label, 1)
        reset = QPushButton("기본값으로 되돌리기")
        reset.clicked.connect(self.reset_keys)
        row.addWidget(reset)
        lay.addLayout(row)
        tabs.addTab(page, "단축키")

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        outer.addWidget(bb)
        self.resize(560, 620)
        self.check_dupes()

    def set_textbook(self):
        self.textbook = True
        self.font.setCurrentFont(QFont("CMU Serif"))
        self.fsize.setValue(13)
        self.lw.setValue(1.5)
        self.math.setChecked(True)
        self.apply_all.setChecked(True)
        QMessageBox.information(self, "교과서 스타일",
                                "글꼴 CMU Serif 13pt, 선 굵기 1.5, 수식처럼 쓰기를 골랐습니다.\n"
                                "'확인'을 누르면 적용됩니다. (지금 있는 그림에도 적용하려면 위 체크를 켜 두세요)")

    def key_of(self, ed):
        return ed.keySequence().toString(QKeySequence.PortableText)

    def reset_keys(self):
        for _sid, default, ed in self.edits:
            ed.setKeySequence(QKeySequence(default))
        self.check_dupes()

    def problems(self):
        seen, msgs = {}, []
        names = {sid: self.table.item(r, 1).text() for r, (sid, _d, _e) in enumerate(self.edits)}
        for sid, _d, ed in self.edits:
            k = self.key_of(ed)
            bad = False
            if k in FIXED_KEYS:
                msgs.append(f"'{k}' 는 고정 키라 쓸 수 없습니다 ({names[sid]}).")
                bad = True
            elif k and k in seen:
                msgs.append(f"'{k}' 가 겹칩니다: {names[seen[k]]} / {names[sid]}")
                bad = True
            elif k:
                seen[k] = sid
            ed.setStyleSheet("background:#fde2e1;" if bad else "")
        return msgs

    def check_dupes(self, *_):
        self.dupe_label.setText("\n".join(self.problems()))

    def accept(self):
        msgs = self.problems()
        if msgs:
            QMessageBox.warning(self, "단축키 확인", "\n".join(msgs) + "\n\n고친 뒤 다시 확인을 눌러 주세요.")
            return
        super().accept()

    def shortcut_values(self):
        out = {}
        for sid, default, ed in self.edits:
            k = self.key_of(ed)
            if k != QKeySequence(default).toString(QKeySequence.PortableText):
                out[sid] = k
        return out

    def values(self):
        return {
            "unit": self.unit.currentText().strip(),
            "decimals": self.dec.value(),
            "angle_decimals": self.adec.value(),
            "length_shape": self.shape.currentData(),
            "font_family": self.font.currentFont().family(),
            "font_size": self.fsize.value(),
            "line_width": self.lw.value(),
            "export_scale": self.scale.value(),
            "png_transparent": self.transp.isChecked(),
            "apply_all": self.apply_all.isChecked(),
            "math_style": self.math.isChecked(),
            "construction_traces": self.traces.isChecked(),
            "textbook": self.textbook,
        }


HELP_HTML = """
<h2>도형그리기 사용법</h2>
<h3>도형 그리기</h3>
<ul>
<li><b>점/선분/직선/반직선</b>: 도구를 고른 뒤 클릭. 이미 있는 점을 클릭하면 그 점을 씁니다.</li>
<li><b>다각형</b>: 꼭짓점을 차례로 클릭 → 첫 점 다시 클릭(또는 더블클릭, Enter)으로 완성</li>
<li><b>정다각형</b>: 왼쪽에서 변의 수를 정하고 한 변의 두 끝점을 클릭</li>
<li><b>원</b>: 중심 → 원 위의 점</li>
<li><b>호·부채꼴(Q)</b>: 중심 → 시작점 → 끝점 (시계 반대 방향). 속성 창에서 부채꼴로 바꾸고 반대쪽 호로 뒤집을 수 있습니다.</li>
<li>그린 뒤에는 자동으로 <b>선택</b> 도구로 돌아갑니다. 같은 도형을 여러 개 그릴 때는 <b>Shift</b>를 누른 채 그리세요.</li>
<li>점을 찍을 때 <b>Alt</b>를 누르고 있으면 모눈에 맞추지 않습니다.</li>
</ul>
<h3>작도</h3>
<ul>
<li><b>중점(D)</b>: 두 점 또는 선분 · <b>수직이등분선(H)</b>: 두 점 또는 선분 · <b>각의 이등분선(J)</b>: 끝 점→꼭짓점→끝 점(또는 각 표시)</li>
<li><b>수선(U)</b>: 점 → 직선·선분. 수선의 발, 수선, 직각 표시가 함께 생깁니다. 입체 위의 점이면 모서리나 면을 클릭 (예: 각뿔의 꼭짓점 → 밑면 = 높이). 길이는 실제 3D 값.</li>
<li><b>평행선(Y)</b>: 점 → 직선·선분 · <b>교점(I)</b>: 두 선·원을 차례로(또는 교점 근처를 바로) 클릭</li>
<li><b>점 도구</b>로 선·원 위를 클릭하면 그 위를 움직이는 점, 두 선이 만나는 곳을 클릭하면 교점이 생깁니다.</li>
<li>작도로 생긴 것은 원래 점을 움직이면 함께 움직입니다. 컴퍼스 흔적(호)은 설정에서 켜고 끕니다.</li>
<li><b>컴퍼스(O)</b>: 왼쪽에서 너비를 넣거나 '두 점으로 재기' → 고정점 클릭 → 끌어서 돌리면 돌린 만큼 호. Shift+클릭: 고정점 바꾸기, Esc: 풀기. 컴퍼스는 Esc를 누를 때까지 도구가 유지됩니다.</li>
</ul>
<ul>
<li><b>접선(W)</b>: 원 밖의 점 → 원 (두 접선과 접점). 원 위의 점이면 그 점에서의 접선.</li>
<li><b>선분 옮기기(E)</b>: 선분 → 새 시작점 → 방향 · <b>각 옮기기(F)</b>: 각 → 새 꼭짓점 → 한 변의 방향 (컴퍼스 흔적 포함)</li>
<li><b>작도 메뉴 → 삼각형 작도</b>: SSS·SAS·ASA 조건을 넣으면 흔적과 함께 삼각형을 그립니다.</li>
<li><b>삼각형의 중심</b>: 삼각형을 선택하면 속성 창에 외심·내심·무게중심·수심 단추 (외접원·내접원·중선·수선 포함).</li>
<li><b>전개도</b>: 입체도형을 선택하고 속성 창 '전개도' → 옆에 전개도가 생깁니다. 펼치는 모양(밑면 둘레/옆면 한 줄), 접기 슬라이더로 접어 볼 수 있습니다.</li>
</ul>
<h3>표시하기</h3>
<ul>
<li><b>길이 표시</b>: 선분을 클릭하면 중괄호(또는 호)와 길이가 생깁니다. 모양은 속성 창에서 중괄호/호 중 고릅니다. 호는 가운데를 비우고 글자를 쓰며, 글자를 ‘없음’으로 하면 그냥 호가 됩니다. 중괄호를 끌면 높이·방향, 글자를 끌면 위치가 바뀝니다. 글자를 더블클릭하면 원하는 글자(예: x cm)로 바꿉니다.</li>
<li><b>각 표시</b>: 끝 점 → 꼭짓점 → 끝 점. 각이 좁으면 자동으로 화살표로 바깥에 표시합니다. 호를 끌면 크기, 글자를 끌면 위치가 바뀝니다. 90°이면 직각 표시(┐)가 됩니다.</li>
<li><b>같은 길이</b>: 선분 클릭 → |, 다시 클릭 → ||, |||</li>
<li><b>측정값</b>: 도형을 클릭하면 길이·각도·넓이가 화면에 표시되고, 점을 움직이면 함께 바뀝니다.</li>
</ul>
<h3>입체도형</h3>
<ul>
<li><b>입체도형(K)</b> 도구로 클릭 → 종류(정육면체·직육면체·각기둥·각뿔·각뿔대·원기둥·원뿔·원뿔대·구)와 크기(cm)를 고릅니다.</li>
<li>보이지 않는 모서리는 자동으로 점선이 됩니다. 처음엔 교과서식 <b>겨냥도</b>로 그립니다.</li>
<li><b>더블클릭 → 회전 모드</b>: 끌어서 돌립니다. Esc 또는 빈 곳 클릭으로 끝. 속성 창의 버튼(겨냥도·비스듬히·앞·위·옆·아래)과 슬라이더로도 돌립니다.</li>
<li>평소에 끌면 위치가 옮겨집니다. 꼭짓점 이름은 더블클릭해서 바꾸고 끌어서 옮깁니다.</li>
<li><b>길이 표시</b> 도구로 모서리를 클릭하면 실제 길이(cm)가 표시되고, 돌려도 따라갑니다.</li>
<li>속성 창에서 겉넓이·부피를 볼 수 있습니다. 원기둥·원뿔·구는 π를 써서 보여 줍니다.</li>
</ul>
<h3>입체도형 더 쓰기</h3>
<ul>
<li><b>점 잡기</b>: 선분·길이·각·점 도구로 입체의 꼭짓점이나 모서리 위를 클릭하면 그 점을 씁니다. 돌리거나 옮겨도 따라가고, 길이와 각은 실제(3D) 값으로 나옵니다. 모서리 위 점은 끌어서 모서리를 따라 옮깁니다(가운데에 자동으로 맞춤).</li>
<li><b>원의 중심점</b>: 원기둥·원뿔·구 등은 속성 창 '원의 중심점 보이기'.</li>
<li><b>면 색칠</b>: Alt+클릭 (앞쪽 면), Alt+Shift+클릭 (뒤쪽 면). 색과 진하기는 속성 창에서.</li>
<li><b>자르기</b>: 속성 창 → '점 3개로 자르기'(꼭짓점·모서리 위 3곳 클릭) 또는 '방향으로 자르기'(기울기·방향·위치 슬라이더). 단면 모양 이름과 넓이가 나오고, 벌리기·한쪽 조각만 보기·단면 색을 바꿀 수 있습니다.</li>
<li><b>겹치기(안에 넣기)</b>: 안에 넣을 입체를 고르고 속성 창 '바깥 입체'를 고르면 밑면을 맞춰 겹칩니다. 안쪽 선은 실선/점선. 함께 움직이고 함께 돕니다.</li>
<li><b>쌓기(회전체)</b>: 입체도형 종류에서 '쌓기' → 연필·팽이·캡슐 등. 속성 창에서 층을 더하고 크기를 바꿉니다. 밑면을 정n각형으로 하면 각기둥+각뿔 같은 모양도 됩니다.</li>
</ul>
<h3>교과서 스타일</h3>
<ul><li>설정 → 환경 설정 → <b>교과서 스타일로 맞추기</b>: LaTeX 글씨체(CMU Serif), x·θ 기울임, ° 작은 동그라미, 가는 선, 작은 각 표시.</li></ul>
<h3>고치기</h3>
<ul>
<li><b>선택</b> 도구로 클릭하면 오른쪽 속성 창에서 굵기, 점선, 색, 글꼴, 크기를 바꿉니다.</li>
<li>여러 개 선택: Shift+클릭, 빈 곳 드래그 · 전부 선택: Ctrl+A</li>
<li>점 이름 바꾸기: 점이나 이름을 더블클릭 · 이름은 끌어서 옮길 수 있습니다.</li>
<li>오른쪽 클릭: 바로가기 메뉴 · 방향키: 조금씩 이동 (Shift: 크게)</li>
</ul>
<h3>화면</h3>
<ul><li>마우스 휠: 확대/축소 · 오른쪽 버튼(또는 가운데 버튼, Space+드래그)으로 끌기: 화면 이동</li></ul>
<h3>한글(HWP)·PPT에 넣기</h3>
<ul>
<li><b>Ctrl+Shift+C</b>(그림 복사) 후 한글/PPT에서 Ctrl+V</li>
<li>파일 → PNG 그림으로 저장 (배경 투명 가능), SVG로 저장</li>
<li>1칸 모눈 = 1cm 이므로, 붙여넣은 그림 크기가 실제 길이와 거의 같습니다.</li>
</ul>
<h3>단축키 (기본값 · 설정 → 환경 설정 → 단축키 에서 바꿀 수 있음)</h3>
<p>V 선택 · P 점 · S 선분 · L 직선 · R 반직선 · G 다각형 · N 정다각형 · C 원 · K 입체도형 · B 길이 · A 각 · T 같은 길이 · M 측정값 · X 글상자<br>
Ctrl+Z 되돌리기 · Ctrl+Y 다시하기 · Ctrl+C/V 복사/붙여넣기 · Delete 삭제 · Ctrl+S 저장 · Esc 취소</p>
"""


# ---------------------------------------------------------------- 탭 하나
class Page:
    def __init__(self, name, doc):
        self.name = name
        self.doc = doc
        self.undo, self.redo = [], []
        self.view = None      # (확대, 화면 위치)


# ---------------------------------------------------------------- 메인 창
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = M.default_settings()
        self.pages = [Page("1번", M.Document(self.settings))]
        self.cur = 0
        self.path = None
        self.modified = False
        self._ck_key, self._ck_time = None, 0.0
        self.clip = None
        self.paste_count = 0
        self.face_color, self.face_alpha = "#f5a623", 40

        self.canvas = Canvas(self)
        central = QWidget()
        cv = QVBoxLayout(central)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        row = QHBoxLayout()
        row.setContentsMargins(4, 2, 4, 0)
        self.tabbar = QTabBar()
        self.tabbar.setMovable(True)
        self.tabbar.setExpanding(False)
        self.tabbar.setUsesScrollButtons(False)
        self.tabbar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.tabbar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabbar.addTab("1번")
        self.tabbar.currentChanged.connect(self.switch_tab)
        self.tabbar.tabMoved.connect(self.tab_moved)
        self.tabbar.tabBarDoubleClicked.connect(self.rename_tab)
        self.tabbar.customContextMenuRequested.connect(self.tab_menu)
        row.addWidget(self.tabbar)
        plus = QToolButton()
        plus.setText("＋")
        plus.setToolTip("새 탭 (Ctrl+T)")
        plus.clicked.connect(self.add_tab)
        row.addWidget(plus)
        row.addStretch()
        cv.addLayout(row)
        cv.addWidget(self.canvas, 1)
        self.setCentralWidget(central)
        self.panel = PropertyPanel(self)
        dock = QDockWidget("속성", self)
        dock.setWidget(self.panel)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.build_actions()
        self.build_menus()
        self.build_toolbars()
        self.canvas.selectionChanged.connect(self.panel.rebuild)
        self.canvas.changed.connect(self.panel.refresh_info)
        self.canvas.status.connect(lambda s: self.statusBar().showMessage(s))
        self.choose_tool("select")
        self.update_title()
        self.resize(1360, 860)

    # ------------------------------------------------------------ 탭
    @property
    def doc(self):
        return self.pages[self.cur].doc

    @property
    def undo_stack(self):
        return self.pages[self.cur].undo

    @property
    def redo_stack(self):
        return self.pages[self.cur].redo

    def save_view(self):
        if 0 <= self.cur < len(self.pages):
            self.pages[self.cur].view = (self.canvas.scale, QPointF(self.canvas.offset))

    def switch_tab(self, i):
        if i < 0 or i >= len(self.pages) or i == self.cur and self.canvas.doc is self.pages[i].doc:
            return
        self.canvas.cancel_temp()
        self.save_view()
        self.cur = i
        self.canvas.rotating = None
        self.canvas.selection = []
        pg = self.pages[i]
        if pg.view:
            self.canvas.scale, self.canvas.offset = pg.view[0], QPointF(pg.view[1])
        self._ck_key = None
        self.panel.rebuild()
        self.canvas.update()

    def add_tab(self, name=None, doc=None, select=True):
        n = len(self.pages) + 1
        names = {p.name for p in self.pages}
        while f"{n}번" in names:
            n += 1
        pg = Page(name or f"{n}번", doc or M.Document(self.settings))
        self.pages.append(pg)
        self.tabbar.blockSignals(True)
        self.tabbar.addTab(pg.name)
        self.tabbar.blockSignals(False)
        self.set_modified(True)
        if select:
            self.tabbar.setCurrentIndex(len(self.pages) - 1)
            self.switch_tab(len(self.pages) - 1)

    def dup_tab(self, i=None):
        i = self.cur if i is None else i
        src = self.pages[i]
        doc = M.Document(self.settings)
        doc.objects = json.loads(json.dumps(src.doc.objects, ensure_ascii=False))
        doc.objects = {int(k): v for k, v in doc.objects.items()}
        doc.next_id = src.doc.next_id
        self.add_tab(src.name + " 복사", doc)

    def rename_tab(self, i=None):
        i = self.cur if (i is None or i < 0) else i
        if i < 0:
            return
        text, ok = QInputDialog.getText(self, "탭 이름", "이름:", text=self.pages[i].name)
        if ok and text.strip():
            self.pages[i].name = text.strip()
            self.tabbar.setTabText(i, text.strip())
            self.set_modified(True)

    def del_tab(self, i=None):
        i = self.cur if i is None else i
        if len(self.pages) <= 1:
            QMessageBox.information(self, APP_NAME, "탭이 하나뿐이라 지울 수 없습니다.")
            return
        if self.pages[i].doc.objects and QMessageBox.question(
                self, APP_NAME, f"'{self.pages[i].name}' 탭을 지울까요? (되돌릴 수 없습니다)") != QMessageBox.Yes:
            return
        self.save_view()
        del self.pages[i]
        self.tabbar.blockSignals(True)
        self.tabbar.removeTab(i)
        self.tabbar.blockSignals(False)
        self.cur = -1
        new = min(i, len(self.pages) - 1)
        self.tabbar.setCurrentIndex(new)
        self.cur = new
        self.canvas.selection = []
        pg = self.pages[new]
        if pg.view:
            self.canvas.scale, self.canvas.offset = pg.view[0], QPointF(pg.view[1])
        self.panel.rebuild()
        self.canvas.update()
        self.set_modified(True)

    def tab_moved(self, frm, to):
        pg = self.pages.pop(frm)
        self.pages.insert(to, pg)
        self.cur = self.tabbar.currentIndex()
        self.set_modified(True)

    def tab_menu(self, pos):
        i = self.tabbar.tabAt(pos)
        if i < 0:
            return
        menu = QMenu(self)
        menu.addAction("이름 바꾸기", lambda: self.rename_tab(i))
        menu.addAction("복제", lambda: self.dup_tab(i))
        menu.addAction("지우기", lambda: self.del_tab(i))
        menu.exec(self.tabbar.mapToGlobal(pos))

    def reset_pages(self, settings, pages):
        """pages: [(이름, Document)]"""
        self.settings.clear()
        self.settings.update(settings)
        for _n, d in pages:
            d.settings = self.settings
        self.pages = [Page(n, d) for n, d in pages] or [Page("1번", M.Document(self.settings))]
        self.cur = 0
        self.tabbar.blockSignals(True)
        while self.tabbar.count():
            self.tabbar.removeTab(0)
        for pg in self.pages:
            self.tabbar.addTab(pg.name)
        self.tabbar.setCurrentIndex(0)
        self.tabbar.blockSignals(False)
        self.canvas.selection = []
        self.canvas.temp, self.canvas.temp_created = [], []
        self.canvas.rotating = None
        self._ck_key = None

    # ------------------------------------------------------------ 동작 만들기
    def act(self, sid, group, text, fn, shortcut="", checkable=False, checked=False):
        a = QAction(text, self)
        a.setCheckable(checkable)
        if checkable:
            a.setChecked(checked)
            a.toggled.connect(fn)
        else:
            a.triggered.connect(lambda _=False: fn())
        self.shortcut_defs.append((sid, group, a, shortcut))
        return a

    def build_actions(self):
        self.shortcut_defs = []
        A = self.act
        F, E, V, H = "파일", "편집", "보기", "도움말"
        self.a_new = A("new", F, "새로 만들기", self.file_new, "Ctrl+N")
        self.a_open = A("open", F, "열기...", self.file_open, "Ctrl+O")
        self.a_save = A("save", F, "저장", self.file_save, "Ctrl+S")
        self.a_saveas = A("saveas", F, "다른 이름으로 저장...", self.file_save_as, "Ctrl+Shift+S")
        self.a_copyimg = A("copyimg", F, "그림 복사 (한글·PPT에 붙여넣기)", self.copy_image, "Ctrl+Shift+C")
        self.a_png = A("png", F, "PNG 그림으로 저장...", self.export_png, "Ctrl+E")
        self.a_svg = A("svg", F, "SVG 그림으로 저장...", self.export_svg, "")
        self.a_quit = A("quit", F, "끝내기", self.close, "Ctrl+Q")
        self.a_newtab = A("newtab", F, "새 탭", self.add_tab, "Ctrl+T")
        self.a_duptab = A("duptab", F, "탭 복제", self.dup_tab, "")
        self.a_deltab = A("deltab", F, "탭 지우기", self.del_tab, "")
        self.a_undo = A("undo", E, "되돌리기", self.do_undo, "Ctrl+Z")
        self.a_redo = A("redo", E, "다시하기", self.do_redo, "Ctrl+Y")
        self.a_copy = A("copy", E, "복사", self.copy_selection, "Ctrl+C")
        self.a_paste = A("paste", E, "붙여넣기", self.paste, "Ctrl+V")
        self.a_dup = A("dup", E, "복제", self.duplicate, "Ctrl+D")
        self.a_del = A("delete", E, "삭제", self.delete_selection, "Delete")
        self.a_all = A("all", E, "모두 선택", self.select_all, "Ctrl+A")
        self.a_hide = A("hide", E, "숨기기", self.hide_selection, "Ctrl+H")
        self.a_showall = A("showall", E, "숨긴 개체 모두 보이기", self.show_all_hidden, "Ctrl+Shift+H")
        st = self.doc.settings
        self.a_grid = A("grid", V, "모눈 보이기", self.toggle_grid, "Ctrl+G", True, st["show_grid"])
        self.a_snap = A("snap", V, "모눈에 맞추기", self.toggle_snap, "Ctrl+Shift+G", True, st["snap"])
        self.a_zin = A("zin", V, "확대", lambda: self.zoom(1.25), "Ctrl+=")
        self.a_zout = A("zout", V, "축소", lambda: self.zoom(0.8), "Ctrl+-")
        self.a_z100 = A("z100", V, "원래 크기 (100%)", self.zoom_reset, "Ctrl+0")
        self.a_zfit = A("zfit", V, "전체 보기", self.zoom_fit, "Ctrl+9")
        self.a_settings = A("settings", H, "환경 설정...", self.open_settings, "")
        self.a_help = A("help", H, "사용법", self.show_help, "F1")
        self.a_about = A("about", H, "프로그램 정보", self.show_about, "")
        for _sid, _g, a, _d in self.shortcut_defs:
            self.addAction(a)

        # 도구
        self.tool_group = QActionGroup(self)
        self.tool_actions = {}
        for t in TOOLS:
            if t is None:
                continue
            key, name, sc = t
            a = QAction(make_icon(key), name, self)
            a.setCheckable(True)
            a.triggered.connect(lambda _=False, key=key: self.choose_tool(key))
            self.tool_group.addAction(a)
            self.addAction(a)
            self.tool_actions[key] = a
            self.shortcut_defs.append(("tool_" + key, "도구", a, sc))
        self.apply_shortcuts(load_shortcuts())

    def apply_shortcuts(self, custom):
        self.custom_shortcuts = dict(custom)
        for sid, _g, a, default in self.shortcut_defs:
            key = custom.get(sid, default)
            if sid == "delete" and key == "Delete":
                a.setShortcuts([QKeySequence(Qt.Key_Delete), QKeySequence(Qt.Key_Backspace)])
            else:
                a.setShortcut(QKeySequence(key))
            if sid.startswith("tool_"):
                k = shortcut_text(a)
                a.setToolTip(f"{a.text()} ({k})" if k else a.text())
        for b in getattr(self, "tool_buttons", []):
            b.update()
        for a, name in getattr(self, "top_names", {}).items():
            k = shortcut_text(a)
            a.setIconText(name)
            a.setToolTip(f"{a.text()} ({k})" if k else a.text())
        if hasattr(self, "a_copyimg"):
            self.a_copyimg.setToolTip("선택한 것이 있으면 그것만, 없으면 전체를 PNG 그림으로 복사")

    def build_menus(self):
        mb = self.menuBar()
        m = mb.addMenu("파일(&F)")
        for a in [self.a_new, self.a_open, None, self.a_newtab, self.a_duptab, self.a_deltab, None,
                  self.a_save, self.a_saveas, None,
                  self.a_copyimg, self.a_png, self.a_svg, None, self.a_quit]:
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("편집(&E)")
        for a in [self.a_undo, self.a_redo, None, self.a_copy, self.a_paste, self.a_dup, self.a_del,
                  None, self.a_all, self.a_hide, self.a_showall]:
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("보기(&V)")
        for a in [self.a_grid, self.a_snap, None, self.a_zin, self.a_zout, self.a_z100, self.a_zfit]:
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("작도(&C)")
        m.addAction("삼각형 작도 (SSS·SAS·ASA)…", self.triangle_dialog)
        for key, name in (("mid", "중점"), ("pbis", "수직이등분선"), ("abis", "각의 이등분선"), ("perp", "수선"),
                          ("par", "평행선"), ("inter", "교점"), ("tan", "접선"), ("copyseg", "길이가 같은 선분 옮기기"),
                          ("copyang", "크기가 같은 각 옮기기"), ("compass", "컴퍼스")):
            m.addAction(name, lambda key=key: self.choose_tool(key))
        m.addSeparator()
        tr = QAction("작도 흔적(컴퍼스 호) 보이기", self)
        tr.setCheckable(True)
        tr.setChecked(bool(self.doc.settings.get("construction_traces", True)))
        tr.toggled.connect(lambda v: (self.doc.settings.__setitem__("construction_traces", v), self.canvas.update()))
        m.addAction(tr)
        self.a_traces = tr
        m = mb.addMenu("설정(&S)")
        m.addAction(self.a_settings)
        m = mb.addMenu("도움말(&H)")
        m.addAction(self.a_help)
        m.addAction(self.a_about)

    def build_toolbars(self):
        top = QToolBar("기본")
        top.setIconSize(QSize(20, 20))
        top.setToolButtonStyle(Qt.ToolButtonTextOnly)
        top.setMovable(False)
        self.top_names = {self.a_new: "새로 만들기", self.a_open: "열기", self.a_save: "저장",
                          self.a_newtab: "새 탭", self.a_undo: "되돌리기", self.a_redo: "다시하기",
                          self.a_copyimg: "그림 복사", self.a_png: "PNG 저장", self.a_zfit: "전체 보기",
                          self.a_grid: "모눈", self.a_snap: "모눈 맞추기"}
        for a in [self.a_new, self.a_open, self.a_save, self.a_newtab, None, self.a_undo, self.a_redo, None,
                  self.a_copyimg, self.a_png, None, self.a_zfit, self.a_grid, self.a_snap]:
            top.addSeparator() if a is None else top.addAction(a)
        top.setStyleSheet("QToolButton{padding:1px 6px;}")
        self.addToolBar(Qt.TopToolBarArea, top)
        self.apply_shortcuts(self.custom_shortcuts)

        left = QToolBar("도구")
        left.setMovable(False)
        box = QWidget()
        grid = QGridLayout(box)
        grid.setContentsMargins(3, 3, 3, 3)
        grid.setSpacing(3)
        self.tool_buttons = []
        row, col = 0, 0
        for t in TOOLS:
            if t is None:
                if col:
                    row, col = row + 1, 0
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setStyleSheet("color:#ccc")
                grid.addWidget(line, row, 0, 1, 3)
                row += 1
                continue
            key = t[0]
            b = ToolButton(self.tool_actions[key])
            grid.addWidget(b, row, col)
            self.tool_buttons.append(b)
            col += 1
            if col == 3:
                row, col = row + 1, 0
            if key == "compass":
                if col:
                    row, col = row + 1, 0
                cw = QDoubleSpinBox()
                cw.setRange(0.1, 50)
                cw.setDecimals(1)
                cw.setSingleStep(0.5)
                cw.setValue(self.canvas.compass_r)
                cw.setPrefix("너비 ")
                cw.setSuffix(" cm")
                cw.setToolTip("컴퍼스 너비")
                cw.valueChanged.connect(lambda v: (setattr(self.canvas, "compass_r", v), self.canvas.update()))
                self.canvas.on_compass_width = lambda v: (cw.blockSignals(True), cw.setValue(v), cw.blockSignals(False))
                mb = QPushButton("두 점으로 재기")
                mb.setToolTip("컴퍼스 너비를 두 점 사이 길이로 맞춥니다")

                def measure():
                    self.choose_tool("compass")
                    self.canvas.compass_measure = []
                    self.statusBar().showMessage("너비를 잴 두 점을 차례로 클릭하세요.")
                mb.clicked.connect(measure)
                grid.addWidget(cw, row, 0, 1, 2)
                grid.addWidget(mb, row, 2)
                row += 1
            if key == "regpoly":
                if col:
                    row, col = row + 1, 0
                spin = QSpinBox()
                spin.setRange(3, 20)
                spin.setValue(5)
                spin.setPrefix("정다각형 변 ")
                spin.setToolTip("정다각형 변의 수")
                spin.valueChanged.connect(lambda v: setattr(self.canvas, "reg_n", v))
                grid.addWidget(spin, row, 0, 1, 3)
                row += 1
        grid.setRowStretch(row + 1, 1)
        left.addWidget(box)
        self.addToolBar(Qt.LeftToolBarArea, left)

    def choose_tool(self, key):
        self.tool_actions[key].setChecked(True)
        self.canvas.set_tool(key)
        self.canvas.setFocus()

    # ------------------------------------------------------------ 되돌리기
    def checkpoint(self, key=None):
        now = time.monotonic()
        if key is not None and key == self._ck_key and now - self._ck_time < 1.5:
            self._ck_time = now
            self.set_modified(True)
            return
        self.push_undo_state(self.doc.dump())
        self._ck_key, self._ck_time = key, now

    def push_undo_state(self, s):
        self.undo_stack.append(s)
        if len(self.undo_stack) > 300:
            del self.undo_stack[0]
        self.redo_stack.clear()
        self._ck_key = None
        self.set_modified(True)

    def do_undo(self):
        if not self.undo_stack:
            return
        self.canvas.cancel_temp()
        self.redo_stack.append(self.doc.dump())
        self.restore(self.undo_stack.pop())

    def do_redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self.doc.dump())
        self.restore(self.redo_stack.pop())

    def restore(self, s):
        self.doc.load(s)
        self._ck_key = None
        self.canvas.temp, self.canvas.temp_created = [], []
        self.canvas.selection = [i for i in self.canvas.selection if i in self.doc.objects]
        self.sync_view_actions()
        self.panel.rebuild()
        self.canvas.update()
        self.set_modified(True)

    def set_modified(self, v=True):
        if self.modified != v:
            self.modified = v
            self.update_title()

    def update_title(self):
        name = os.path.basename(self.path) if self.path else "제목 없음"
        self.setWindowTitle(f"{'*' if self.modified else ''}{name} - {APP_NAME} {APP_VERSION}")

    def changed(self):
        self.canvas.update()
        self.panel.refresh_info()
        self.set_modified(True)

    # ------------------------------------------------------------ 명령
    def selected(self):
        return [i for i in self.canvas.selection if i in self.doc.objects]

    def add_brace(self, a, b):
        geo = Geo(self.doc)
        A, B = geo.P(a), geo.P(b)
        n0 = perp(norm(B - A))
        side = 1
        c = geo.edge_cent.get(frozenset((a, b)))
        if c is not None:
            side = 1 if dot((A + B) * 0.5 - c, n0) >= 0 else -1
        self.checkpoint()
        bid = M.make_brace(self.doc, a, b, side)
        self.canvas.set_selection([bid])
        self.changed()
        return bid

    def add_tick(self, seg):
        self.checkpoint()
        for o in self.doc.items("tick"):
            if o["seg"] == seg:
                o["count"] = o.get("count", 1) % 3 + 1
                self.canvas.set_selection([o["id"]])
                break
        else:
            self.canvas.set_selection([M.make_tick(self.doc, seg)])
        self.changed()

    def add_measure(self, oid, kind, pos=None):
        o = self.doc.objects.get(oid)
        if not o:
            return
        geo = Geo(self.doc)
        if pos is None:
            ids = sorted(self.doc.point_ids_of([oid]))
            pts = [geo.P(i) for i in ids] or [QPointF(0, 0)]
            if o["type"] == "solid":
                br = geo.solid(o)["hull"].boundingRect()
                left, bottom = br.left(), br.bottom()
            elif o["type"] == "circle":
                C, R = geo.P(o["c"]), length(geo.P(o["p"]) - geo.P(o["c"]))
                left, bottom = C.x() - R, C.y() + R
            else:
                left, bottom = min(p.x() for p in pts), max(p.y() for p in pts)
            # 도형 아래쪽에 차례로 쌓기
            n = sum(1 for m in self.doc.items("measure") if m["target"] == oid)
            pos = (left, bottom + 50 + 28 * n)
        self.checkpoint()
        mid = M.make_measure(self.doc, oid, kind, pos[0], pos[1])
        self.canvas.set_selection([mid])
        self.changed()

    # ------------------------------------------------------------ 삼각형의 중심·삼각형 작도·전개도
    CENTER_NAMES = {"circum": ("외심", "O"), "in": ("내심", "I"), "centroid": ("무게중심", "G"), "ortho": ("수심", "H")}

    def tri_center(self, poly_id, kind):
        doc = self.doc
        a, b, c = doc.objects[poly_id]["pts"][:3]
        self.checkpoint()
        name, lab = self.CENTER_NAMES[kind]
        used = {o.get("label") for o in doc.items("point")}
        X = M.make_dep_point(doc, {"t": "center", "kind": kind, "a": a, "b": b, "v": c},
                             label=lab if lab not in used else None)

        def dash(seg):
            doc.objects[seg]["style"].update(dash="dash", width=max(1.0, doc.settings.get("line_width", 2) * 0.6))
            return seg
        if kind == "circum":
            M.make_circle(doc, X, a)
            for v in (a, b, c):
                dash(M.make_segment(doc, X, v))
        elif kind == "in":
            f = M.make_dep_point(doc, {"t": "foot", "p": X, "a": a, "b": b}, show=False)
            M.make_circle(doc, X, f)
            for v in (a, b, c):
                dash(M.make_segment(doc, v, X))
        elif kind == "centroid":
            for v, (p_, q_) in ((a, (b, c)), (b, (c, a)), (c, (a, b))):
                mid = M.make_dep_point(doc, {"t": "mid", "a": p_, "b": q_}, label="")
                doc.objects[mid]["show_label"] = False
                dash(M.make_segment(doc, v, mid))
        else:
            for v, (p_, q_) in ((a, (b, c)), (b, (c, a)), (c, (a, b))):
                f = M.make_dep_point(doc, {"t": "foot", "p": v, "a": p_, "b": q_}, show=False)
                dash(M.make_segment(doc, v, f))
        self.canvas.set_selection([X])
        self.changed()
        self.statusBar().showMessage(f"{name}을(를) 만들었습니다. 꼭짓점을 움직이면 함께 움직입니다.")

    def triangle_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("삼각형 작도")
        form = QFormLayout(dlg)
        kind = QComboBox()
        kind.addItem("세 변의 길이 (SSS)", "SSS")
        kind.addItem("두 변의 길이와 그 끼인각 (SAS)", "SAS")
        kind.addItem("한 변의 길이와 그 양 끝 각 (ASA)", "ASA")
        form.addRow("조건", kind)
        spins, labs = [], []
        for _ in range(3):
            s = QDoubleSpinBox()
            s.setDecimals(1)
            s.setRange(0.1, 179.0)
            lab = QLabel()
            form.addRow(lab, s)
            spins.append(s)
            labs.append(lab)

        def setup():
            k = kind.currentData()
            spec = {"SSS": [("변 BC (cm)", 5), ("변 CA (cm)", 4), ("변 AB (cm)", 6)],
                    "SAS": [("변 AB (cm)", 6), ("∠A (°)", 50), ("변 AC (cm)", 4)],
                    "ASA": [("변 AB (cm)", 6), ("∠A (°)", 50), ("∠B (°)", 60)]}[k]
            for (t, v), s, l in zip(spec, spins, labs):
                l.setText(t)
                s.setRange(0.1, 179.0 if "°" in t else 40.0)
                s.setValue(v)
        kind.currentIndexChanged.connect(lambda _i: setup())
        setup()
        tip = QLabel("작도 흔적(컴퍼스 호)과 길이·각 표시가 함께 그려집니다.")
        tip.setStyleSheet("color:#666")
        form.addRow(tip)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        self.make_triangle(kind.currentData(), [s.value() for s in spins])

    def make_triangle(self, k, v):
        doc = self.doc
        G = M.GRID
        if k == "SSS":
            a, b, c = v
            if not (a + b > c and b + c > a and c + a > b):
                QMessageBox.warning(self, "삼각형 작도", "가장 긴 변이 나머지 두 변의 합보다 짧아야 삼각형이 됩니다.")
                return
            AB = c
            xC = (b * b - a * a + c * c) / (2 * c)
            yC = math.sqrt(max(0.0, b * b - xC * xC))
        elif k == "SAS":
            AB, angA, AC = v
            xC, yC = AC * math.cos(math.radians(angA)), AC * math.sin(math.radians(angA))
        else:
            AB, angA, angB = v
            if angA + angB >= 180:
                QMessageBox.warning(self, "삼각형 작도", "두 각의 합이 180°보다 작아야 합니다.")
                return
            angC = 180 - angA - angB
            AC = AB * math.sin(math.radians(angB)) / math.sin(math.radians(angC))
            xC, yC = AC * math.cos(math.radians(angA)), AC * math.sin(math.radians(angA))
        ctr = self.canvas.to_world(QPointF(self.canvas.width() / 2, self.canvas.height() / 2))
        ox, oy = ctr.x() - AB * G / 2, ctr.y() + yC * G / 2
        self.checkpoint()
        used = {o.get("label") for o in doc.items("point")}
        labs = ["A", "B", "C"] if not used & {"A", "B", "C"} else [None, None, None]
        A = M.make_point(doc, ox, oy, labs[0])
        B = M.make_point(doc, ox + AB * G, oy, labs[1])
        C = M.make_point(doc, ox + xC * G, oy - yC * G, labs[2])
        poly = M.make_polygon(doc, [A, B, C])
        tr = doc.settings.get("construction_traces", True)
        if k == "SSS":
            if tr:
                M.make_trace(doc, "mark", c=A, p=C, deg=16)
                M.make_trace(doc, "mark", c=B, p=C, deg=16)
            for p_, q_ in ((A, B), (B, C), (C, A)):
                self.add_brace(p_, q_)
        elif k == "SAS":
            if tr:
                M.make_trace(doc, "mark", c=A, p=C, deg=16)
            self.add_brace(A, B)
            self.add_brace(C, A)
            M.make_angle(doc, B, A, C)
        else:
            self.add_brace(A, B)
            M.make_angle(doc, B, A, C)
            M.make_angle(doc, C, B, A)
        self.canvas.set_selection([poly])
        self.choose_tool("select")
        self.changed()

    def add_net(self, sid):
        so = self.doc.objects[sid]
        if not S.net_supported(so):
            QMessageBox.information(self, APP_NAME, "구와 쌓기(회전체)는 전개도를 만들 수 없습니다.")
            return
        hull = Geo(self.doc).solid(so)["hull"].boundingRect()
        self.checkpoint()
        nid = M.make_net(self.doc, sid, hull.right() + 40, hull.center().y())
        br = Geo(self.doc).net(self.doc.objects[nid])["hull"].boundingRect()
        self.doc.objects[nid]["x"] += br.width() / 2
        self.canvas.set_selection([nid])
        self.changed()

    def add_solid(self, wp):
        dlg = SolidDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return False
        kind, params = dlg.values()
        self.checkpoint()
        sid = M.make_solid(self.doc, kind, wp.x(), wp.y(), params)
        self.canvas.set_selection([sid])
        self.changed()
        self.statusBar().showMessage("입체도형을 놓았습니다. 더블클릭하면 회전 모드, 속성 창에서 크기·보는 방향을 바꿉니다.")
        return True

    def add_solid_brace(self, sid, i, j):
        self.checkpoint()
        for b in self.doc.items("brace"):
            if b.get("solid") == sid and set(b["sv"]) == {i, j}:
                self.canvas.set_selection([b["id"]])
                return
        bid = M.make_solid_brace(self.doc, sid, i, j)
        self.canvas.set_selection([bid])
        self.changed()

    def rename_solid_label(self, sid, k):
        o = self.doc.objects[sid]
        labs = o.get("labels", [])
        if k >= len(labs):
            return
        text, ok = QInputDialog.getText(self, "꼭짓점 이름", "새 이름:", text=labs[k])
        if ok:
            self.checkpoint()
            labs[k] = text
            self.panel.rebuild()
            self.changed()

    VIEWS = {"iso": (-35.0, 25.0), "front": (0.0, 0.0), "top": (0.0, 90.0),
             "side": (-90.0, 0.0), "bottom": (0.0, -90.0)}

    def solid_view(self, ids, view):
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        self.checkpoint()
        for i in ids:
            o = self.doc.objects.get(i)
            if not o:
                continue
            if view == "oblique":
                o["view"] = "oblique"
                o["yaw"], o["pitch"] = (0.0, 20.0) if o["kind"] in S.CURVED else (-30.0, 20.0)
            else:
                o["view"] = "rot"
                o["yaw"], o["pitch"] = self.VIEWS[view]
        self.changed()

    def polygon_braces(self, pid):
        poly = self.doc.objects[pid]
        ids = poly["pts"]
        geo = Geo(self.doc)
        self.checkpoint()
        new = []
        for k in range(len(ids)):
            a, b = ids[k], ids[(k + 1) % len(ids)]
            A, B = geo.P(a), geo.P(b)
            n0 = perp(norm(B - A))
            c = geo.edge_cent.get(frozenset((a, b)))
            side = 1 if c is None or dot((A + B) * 0.5 - c, n0) >= 0 else -1
            new.append(M.make_brace(self.doc, a, b, side))
        self.canvas.set_selection(new)
        self.changed()

    def polygon_angles(self, pid):
        poly = self.doc.objects[pid]
        ids = [i for i in poly["pts"] if i in self.doc.objects]
        orient = M.poly_orientation(self.doc, poly)
        self.checkpoint()
        new = []
        for k in range(len(ids)):
            P, V, N = ids[k - 1], ids[k], ids[(k + 1) % len(ids)]
            a, b = (P, N) if orient > 0 else (N, P)
            new.append(M.make_angle(self.doc, a, V, b, auto_swap=False))
        self.canvas.set_selection(new)
        self.changed()

    def rename_point(self, pid):
        o = self.doc.objects[pid]
        text, ok = QInputDialog.getText(self, "점 이름", "새 이름 (예: A, P₁, O):", text=o.get("label", ""))
        if ok:
            self.checkpoint()
            o["label"] = text
            self.panel.rebuild()
            self.changed()

    def edit_text(self, tid):
        o = self.doc.objects[tid]
        text, ok = QInputDialog.getMultiLineText(self, "글상자", "내용:", o.get("text", ""))
        if ok:
            self.checkpoint()
            o["text"] = text
            self.panel.rebuild()
            self.changed()

    def delete_selection(self):
        ids = self.selected()
        if not ids:
            return
        self.checkpoint()
        self.doc.delete(ids)
        self.canvas.set_selection([])
        self.changed()

    def hide_selection(self):
        ids = self.selected()
        if not ids:
            return
        self.checkpoint()
        for i in ids:
            self.doc.objects[i]["hidden"] = True
        self.canvas.set_selection([])
        self.changed()
        self.statusBar().showMessage("숨겼습니다. 다시 보려면 편집 → 숨긴 개체 모두 보이기 (Ctrl+Shift+H)")

    def show_all_hidden(self):
        hid = [o for o in self.doc.objects.values() if o.get("hidden")]
        if not hid:
            return
        self.checkpoint()
        for o in hid:
            o["hidden"] = False
        self.canvas.set_selection([o["id"] for o in hid])
        self.changed()

    def select_all(self):
        self.canvas.set_selection([o["id"] for o in self.doc.objects.values() if not o.get("hidden")])

    def copy_selection(self):
        ids = self.selected()
        if not ids:
            return
        need = self.doc.requirements(ids)
        objs = [copy.deepcopy(o) for o in self.doc.objects.values() if o["id"] in need]
        self.clip = objs
        self.paste_count = 0
        self.statusBar().showMessage(f"{len(ids)}개 복사했습니다. Ctrl+V 로 붙여넣기")

    def paste(self):
        if not self.clip:
            return
        self.paste_count += 1
        off = 20 * self.paste_count
        self.checkpoint()
        mapping, new_ids = {}, []
        for o in self.clip:
            n = copy.deepcopy(o)
            old = n.pop("id")
            M.remap_refs(n, mapping)
            if n["type"] in ("point", "text", "measure", "solid"):
                n["x"] += off
                n["y"] += off
            if n["type"] == "point":
                n["label"] = self.doc.next_label()
            nid = self.doc.add(n)
            mapping[old] = nid
            new_ids.append(nid)
        self.canvas.set_selection(new_ids)
        self.changed()

    def duplicate(self):
        self.copy_selection()
        self.paste()

    # ------------------------------------------------------------ 보기
    def toggle_grid(self, v):
        self.doc.settings["show_grid"] = v
        self.canvas.update()

    def toggle_snap(self, v):
        self.doc.settings["snap"] = v

    def sync_view_actions(self):
        for a, k in ((self.a_grid, "show_grid"), (self.a_snap, "snap")):
            a.blockSignals(True)
            a.setChecked(bool(self.doc.settings.get(k)))
            a.blockSignals(False)

    def zoom(self, f):
        c = QPointF(self.canvas.width() / 2, self.canvas.height() / 2)
        wp = self.canvas.to_world(c)
        self.canvas.scale = max(0.1, min(10.0, self.canvas.scale * f))
        self.canvas.offset = QPointF(c.x() - wp.x() * self.canvas.scale, c.y() - wp.y() * self.canvas.scale)
        self.canvas.update()

    def zoom_reset(self):
        self.zoom(1.0 / self.canvas.scale)

    def zoom_fit(self):
        br = self.content_bounds(export=False)
        if br is None:
            self.canvas.scale = 1.0
            self.canvas.offset = QPointF(40, 40)
            self.canvas.update()
            return
        br = br.adjusted(-40, -40, 40, 40)
        s = min(self.canvas.width() / br.width(), self.canvas.height() / br.height())
        s = max(0.1, min(4.0, s))
        self.canvas.scale = s
        self.canvas.offset = QPointF(self.canvas.width() / 2 - br.center().x() * s,
                                     self.canvas.height() / 2 - br.center().y() * s)
        self.canvas.update()

    # ------------------------------------------------------------ 내보내기
    def export_ids(self):
        """선택한 것이 있으면 그것과 딸린 것(꼭짓점, 변, 붙은 길이·각 표시)만, 없으면 None(전체)"""
        sel = [i for i in self.canvas.selection if i in self.doc.objects]
        if not sel:
            return None
        doc = self.doc
        S_ = set(doc.requirements(sel))
        for i in list(S_):
            o = doc.objects[i]
            if o["type"] == "polygon":
                ids = o["pts"]
                for k in range(len(ids)):
                    sid = doc.find_segment(ids[k], ids[(k + 1) % len(ids)])
                    if sid:
                        S_.add(sid)
        changed = True
        while changed:
            changed = False
            for o in doc.objects.values():
                if o["id"] in S_ or o["type"] not in ("brace", "angle", "tick", "measure", "segment", "polygon", "arc"):
                    continue
                req = doc.requirements([o["id"]]) - {o["id"]}
                if req and req <= S_:
                    S_.add(o["id"])
                    changed = True
        # 선택하지 않은 점은 그리지 않음 (단, 선분·다각형 등을 고르면 그 꼭짓점은 함께)
        return S_

    def content_bounds(self, export=True, only=None):
        if not any(not o.get("hidden") for o in self.doc.objects.values()):
            return None
        pic = QPicture()
        pp = QPainter(pic)
        rd = Renderer(self.doc, Geo(self.doc), (), export=True, only=only)
        rd.draw(pp)
        pp.end()
        br = QRectF(pic.boundingRect())
        if not rd.text_bounds.isEmpty():
            br = br.united(rd.text_bounds) if not br.isEmpty() else rd.text_bounds
        if br.isEmpty():
            return None
        return br

    def render_image(self, transparent):
        only = self.export_ids()
        br = self.content_bounds(only=only)
        if br is None:
            QMessageBox.information(self, APP_NAME, "그림이 비어 있습니다.")
            return None
        br = br.adjusted(-8, -8, 8, 8)
        s = int(self.doc.settings.get("export_scale", 3))
        img = QImage(int(math.ceil(br.width() * s)), int(math.ceil(br.height() * s)),
                     QImage.Format_ARGB32_Premultiplied)
        img.fill(QColor(0, 0, 0, 0) if transparent else QColor("white"))
        dpm = int(round(96 * s / 0.0254))
        img.setDotsPerMeterX(dpm)
        img.setDotsPerMeterY(dpm)
        p = QPainter(img)
        p.scale(s, s)
        p.translate(-br.topLeft())
        Renderer(self.doc, Geo(self.doc), (), export=True, only=only).draw(p)
        p.end()
        return img

    def default_export_name(self, ext):
        base = os.path.splitext(self.path)[0] if self.path else os.path.join(os.path.expanduser("~"), "도형")
        return f"{base}.{ext}"

    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "PNG 그림으로 저장", self.default_export_name("png"),
                                              "PNG 그림 (*.png)")
        if not path:
            return
        img = self.render_image(self.doc.settings.get("png_transparent", True))
        if img is not None:
            if not img.save(path, "PNG"):
                QMessageBox.warning(self, APP_NAME, "저장하지 못했습니다.")
            else:
                self.statusBar().showMessage(f"저장했습니다: {path}")

    def export_svg(self):
        try:
            from PySide6.QtSvg import QSvgGenerator
        except ImportError:
            QMessageBox.warning(self, APP_NAME, "SVG 저장 기능을 불러오지 못했습니다.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "SVG 그림으로 저장", self.default_export_name("svg"),
                                              "SVG 그림 (*.svg)")
        if not path:
            return
        br = self.content_bounds()
        if br is None:
            return
        br = br.adjusted(-8, -8, 8, 8)
        gen = QSvgGenerator()
        gen.setFileName(path)
        gen.setSize(br.size().toSize())
        gen.setViewBox(br)
        gen.setResolution(96)
        gen.setTitle(APP_NAME)
        p = QPainter(gen)
        Renderer(self.doc, Geo(self.doc), (), export=True).draw(p)
        p.end()
        self.statusBar().showMessage(f"저장했습니다: {path}")

    def copy_image(self):
        img = self.render_image(transparent=self.doc.settings.get("png_transparent", True))
        if img is None:
            return
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        img.save(buf, "PNG")
        data = QMimeData()
        data.setData("image/png", buf.data())
        data.setData("PNG", buf.data())
        flat = QImage(img.size(), QImage.Format_RGB32)
        flat.fill(QColor("white"))
        pp = QPainter(flat)
        pp.drawImage(0, 0, img)
        pp.end()
        data.setImageData(flat)
        QApplication.clipboard().setMimeData(data)
        what = "선택한 것만" if self.export_ids() is not None else "전체를"
        self.statusBar().showMessage(f"{what} PNG 그림으로 복사했습니다. 한글이나 PPT에서 Ctrl+V 로 붙여넣으세요.")

    # ------------------------------------------------------------ 파일
    def maybe_save(self):
        if not self.modified or not any(p.doc.objects for p in self.pages):
            return True
        r = QMessageBox.question(self, APP_NAME, "바뀐 내용을 저장할까요?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.file_save()
        return r == QMessageBox.Discard

    def file_new(self):
        if not self.maybe_save():
            return
        self.reset_pages(dict(self.settings), [("1번", M.Document())])
        self.path = None
        self.panel.rebuild()
        self.canvas.update()
        self.modified = False
        self.update_title()

    def file_open(self, path=None):
        if not path:
            if not self.maybe_save():
                return
            path, _ = QFileDialog.getOpenFileName(self, "열기", os.path.dirname(self.path or ""),
                                                  f"도형 파일 (*.{M.FILE_EXT});;모든 파일 (*)")
            if not path:
                return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
            settings, pages = M.load_pages(data)
        except Exception as ex:
            QMessageBox.warning(self, APP_NAME, f"파일을 열지 못했습니다.\n{ex}")
            return
        self.reset_pages(settings, pages)
        self.path = path
        self.sync_view_actions()
        self.panel.rebuild()
        self.modified = False
        self.update_title()
        self.zoom_fit()

    def file_save(self):
        if not self.path:
            return self.file_save_as()
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(M.dump_pages([(p.name, p.doc) for p in self.pages], self.settings))
        except Exception as ex:
            QMessageBox.warning(self, APP_NAME, f"저장하지 못했습니다.\n{ex}")
            return False
        self.modified = False
        self.update_title()
        self.statusBar().showMessage(f"저장했습니다: {self.path}")
        return True

    def file_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "다른 이름으로 저장", self.default_export_name(M.FILE_EXT),
                                              f"도형 파일 (*.{M.FILE_EXT})")
        if not path:
            return False
        if not path.lower().endswith("." + M.FILE_EXT):
            path += "." + M.FILE_EXT
        self.path = path
        return self.file_save()

    def closeEvent(self, e):
        if self.maybe_save():
            e.accept()
        else:
            e.ignore()

    # ------------------------------------------------------------ 설정/도움말
    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        v = dlg.values()
        self.checkpoint()
        st = self.doc.settings
        st["unit"] = v["unit"]
        st["decimals"] = v["decimals"]
        st["angle_decimals"] = v["angle_decimals"]
        st["font"] = dict(st["font"], family=v["font_family"], size=v["font_size"])
        st["line_width"] = v["line_width"]
        st["export_scale"] = v["export_scale"]
        st["png_transparent"] = v["png_transparent"]
        st["length_shape"] = v["length_shape"]
        st["math_style"] = v["math_style"]
        st["construction_traces"] = v["construction_traces"]
        if v["textbook"]:
            st["angle_radius"] = 16.0
            st["mark_width"] = 1.0
        sc = dlg.shortcut_values()
        save_shortcuts(sc)
        self.apply_shortcuts(sc)
        if v["apply_all"]:
            for o in self.doc.objects.values():
                if "font" in o:
                    o["font"]["family"] = v["font_family"]
                    o["font"]["size"] = v["font_size"]
                    if v["textbook"]:
                        o["font"]["bold"] = o["font"]["italic"] = False
                if v["textbook"]:
                    t = o["type"]
                    if t in ("segment", "circle", "solid"):
                        o["style"]["width"] = v["line_width"]
                        if "hid_style" in o:
                            o["hid_style"]["width"] = v["line_width"]
                    elif t in ("brace", "angle", "tick"):
                        o["style"]["width"] = st["mark_width"]
                    if t == "angle":
                        o["radius"] = st["angle_radius"]
                        o["lu"] = o["lv"] = None
        self.panel.rebuild()
        self.changed()

    def show_help(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("사용법")
        lay = QVBoxLayout(dlg)
        tb = QTextBrowser()
        tb.setHtml(HELP_HTML)
        lay.addWidget(tb)
        dlg.resize(640, 640)
        dlg.exec()

    def show_about(self):
        QMessageBox.about(self, APP_NAME, f"<b>{APP_NAME}</b> {APP_VERSION}<br><br>"
                                          "수학 수업과 학습지용 도형 그리기 프로그램입니다.")


def register_fonts():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    folder = os.path.join(base, "fonts")
    if os.path.isdir(folder):
        for f in os.listdir(folder):
            if f.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(folder, f))


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    register_fonts()
    tr = QTranslator(app)
    if tr.load("qtbase_ko", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(tr)
    f = app.font()
    f.setFamily("맑은 고딕")
    f.setPointSize(10)
    app.setFont(f)
    w = MainWindow()
    w.show()
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        w.file_open(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
