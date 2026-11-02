@echo off
chcp 65001 > nul
title VC 딜소싱 & 인텔리전스 Pro 실행
echo ===================================================
echo   VC 딜소싱 & 벤처 인텔리전스 백엔드 서버를 구동합니다.
echo   이 검은색 창을 닫으면 프로그램이 멈춥니다!
echo ===================================================
cd /d "%~dp0"

echo FastAPI 백엔드 서버를 백그라운드로 실행합니다...
venv\Scripts\python.exe --version >nul 2>&1
if %errorlevel%==0 (
    start /b venv\Scripts\python.exe backend\main.py
) else (
    start /b python backend\main.py
)

timeout /t 4 /nobreak > nul
echo 웹 화면을 띄웁니다...
start "" "http://localhost:8002/"
cmd /k
