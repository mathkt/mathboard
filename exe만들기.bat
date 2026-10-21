@echo off
cd /d "%~dp0"
title 도형그리기 exe 만들기
echo ==============================================
echo   도형그리기.exe 를 만듭니다. (처음엔 5~10분)
echo ==============================================
:checkrun
tasklist /FI "IMAGENAME eq 도형그리기.exe" 2>nul | find /i "도형그리기.exe" >nul
if not errorlevel 1 (
  echo.
  echo [안내] 도형그리기 프로그램이 켜져 있습니다.
  echo        프로그램을 모두 닫은 뒤 아무 키나 누르세요.
  pause >nul
  goto checkrun
)
set PY=python
%PY% --version >nul 2>&1
if errorlevel 1 (
  set PY=py
  py --version >nul 2>&1
  if errorlevel 1 (
    echo.
    echo [안내] Python 이 설치되어 있지 않습니다.
    echo  1. https://www.python.org/downloads/ 에서 설치하세요.
    echo  2. 설치 첫 화면의 "Add python.exe to PATH" 를 꼭 체크하세요.
    echo  3. 설치 후 이 파일을 다시 더블클릭하세요.
    pause
    exit /b 1
  )
)
echo [1/3] 필요한 부품 설치 중...
%PY% -m pip install --upgrade pip >nul
%PY% -m pip install --upgrade PySide6 pyinstaller numpy
if errorlevel 1 (
  echo [오류] 부품 설치에 실패했습니다. 인터넷 연결을 확인하세요.
  pause
  exit /b 1
)
echo [2/3] exe 만드는 중... (몇 분 걸립니다)
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --add-data "fonts;fonts" --name 도형그리기 main.py
if errorlevel 1 (
  echo [오류] exe 를 만들지 못했습니다. 위의 메시지를 캡처해서 보내주세요.
  pause
  exit /b 1
)
copy /y "dist\도형그리기.exe" "도형그리기.exe" >nul
if errorlevel 1 (
  echo.
  echo [오류] 새 exe 를 바깥 폴더로 복사하지 못했습니다.
  echo        도형그리기 프로그램이 켜져 있으면 닫고 이 파일을 다시 실행하세요.
  echo        (새 exe 는 dist 폴더 안에 있습니다)
  pause
  exit /b 1
)
echo [3/3] 정리 중...
rmdir /s /q build >nul 2>&1
del /q 도형그리기.spec >nul 2>&1
echo.
echo 완료! 이 폴더의 "도형그리기.exe" 를 실행하세요.
echo 창 제목에 나오는 버전을 확인하세요.
echo (다른 PC 에는 도형그리기.exe 파일 하나만 복사하면 됩니다.)
pause
