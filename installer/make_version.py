"""PyInstaller 용 버전 정보 파일 만들기 (Windows 탐색기·'연결 프로그램' 목록에 '도형그리기'로 보이게)"""
import re
import sys

ver = re.search(r'APP_VERSION = "(.+?)"', open("main.py", encoding="utf-8").read()).group(1)
nums = [int(x) for x in re.findall(r"\d+", ver)][:4]
nums += [0] * (4 - len(nums))
exe = sys.argv[1] if len(sys.argv) > 1 else "도형그리기.exe"
t = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tuple(nums)}, prodvers={tuple(nums)}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041204B0', [
      StringStruct('CompanyName', 'mathkt'),
      StringStruct('FileDescription', '도형그리기'),
      StringStruct('FileVersion', '{ver}'),
      StringStruct('InternalName', '도형그리기'),
      StringStruct('OriginalFilename', '{exe}'),
      StringStruct('ProductName', '도형그리기'),
      StringStruct('ProductVersion', '{ver}')])]),
    VarFileInfo([VarStruct('Translation', [0x0412, 1200])])
  ]
)
"""
open("version_info.txt", "w", encoding="utf-8").write(t)
print("version", ver)
