@echo off
chcp 65001 >nul
echo ===================================================
echo   AWS 자동 배포 스크립트 (VC Deal Sourcing)
echo ===================================================
echo.
echo [1/4] 변경된 파일을 Git에 추가하는 중...
git add .

echo [2/4] 변경 사항을 Commit 하는 중...
set /p commit_msg="업데이트 내용을 간단히 입력하세요 (엔터 치면 '자동 업데이트'로 저장됩니다): "
if "%commit_msg%"=="" set commit_msg=자동 업데이트
git commit -m "%commit_msg%"

echo.
echo [3/4] GitHub로 Push 하는 중...
git push origin main

echo.
echo [4/4] AWS 서버에 접속하여 코드를 갱신하고 서비스를 재시작합니다...
ssh -o StrictHostKeyChecking=no -i "C:\Users\llll\Downloads\aws-key.pem" ubuntu@13.209.3.151 "cd /home/ubuntu/dealsourcing-agent && git fetch origin && git reset --hard origin/main && sudo systemctl restart vc-dealsourcing"

echo.
echo ===================================================
echo   배포가 성공적으로 완료되었습니다!
echo   사이트에서 확인하세요 (캐시 새로고침: Ctrl + Shift + R)
echo ===================================================
pause
