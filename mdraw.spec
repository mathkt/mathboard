# -*- mode: python ; coding: utf-8 -*-
# 도형그리기 PyInstaller 설정 — 쓰지 않는 부품을 빼서 크기를 줄임
#   MDRAW_MODE=onefile (exe 하나) / onedir (설치용 폴더),  MDRAW_NAME=만들 exe 이름
import os

MODE = os.environ.get("MDRAW_MODE", "onefile")
NAME = os.environ.get("MDRAW_NAME", "mdraw")
ICON = os.path.join("icon", "mdraw.ico")
VERSION = "version_info.txt" if os.path.exists("version_info.txt") else None

# 쓰지 않는 파이썬 부품 (계산은 numpy 없이, 인터넷 기능 없음)
EXCLUDES = ["numpy", "tkinter", "_tkinter", "unittest", "pydoc", "pydoc_data", "_ssl", "ssl", "_hashlib",
            "sqlite3", "_sqlite3", "xmlrpc", "lib2to3", "distutils", "setuptools", "pip", "PySide6.QtNetwork"]
# 쓰지 않는 Qt·시스템 부품
DROP_FILES = {"opengl32sw.dll", "libcrypto-3-x64.dll", "libssl-3-x64.dll", "libcrypto-3.dll", "libssl-3.dll",
              "d3dcompiler_47.dll", "qt6network.dll", "qdirect2d.dll", "qtiff.dll", "qjpeg.dll", "qwebp.dll"}
DROP_DIRS = ("plugins/tls", "plugins/networkinformation", "plugins/generic")


def keep(entry):
    dest = entry[0].replace("\\", "/")
    base = dest.rsplit("/", 1)[-1].lower()
    if base in DROP_FILES:
        return False
    if any(("/" + d + "/") in ("/" + dest.lower()) for d in DROP_DIRS):
        return False
    if "/translations/" in ("/" + dest.lower()) and base.endswith(".qm") and not base.endswith("_ko.qm"):
        return False      # 번역은 한국어만
    return True


a = Analysis(["main.py"], pathex=[], binaries=[], datas=[("fonts", "fonts"), ("icon", "icon")],
             hiddenimports=[], excludes=EXCLUDES, noarchive=False)
a.binaries = [e for e in a.binaries if keep(e)]
a.datas = [e for e in a.datas if keep(e)]
pyz = PYZ(a.pure)

if MODE == "onefile":
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name=NAME, console=False, icon=ICON, version=VERSION,
              upx=False, debug=False, strip=False)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=NAME, console=False, icon=ICON, version=VERSION,
              upx=False, debug=False, strip=False)
    coll = COLLECT(exe, a.binaries, a.datas, name=NAME, upx=False, strip=False)
