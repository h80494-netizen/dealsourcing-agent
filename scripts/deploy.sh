#!/bin/bash
# AWS Ubuntu 환경 배포 스크립트

echo "1. 시스템 업데이트 및 필요 패키지 설치"
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx sqlite3

echo "2. 파이썬 가상환경 생성 및 패키지 설치"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "3. Nginx 리버스 프록시 설정"
sudo cp scripts/nginx.conf /etc/nginx/sites-available/vc-dealsourcing
sudo ln -sf /etc/nginx/sites-available/vc-dealsourcing /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

echo "4. FastAPI 백그라운드 서비스(systemd) 등록"
sudo cp scripts/vc-dealsourcing.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vc-dealsourcing
sudo systemctl start vc-dealsourcing

echo "5. SSL(HTTPS) 인증서 발급 (Certbot)"
echo "주의: DNS A 레코드가 이미 연결되어 있어야 성공합니다."
sudo certbot --nginx -d vc.ai-auction-experts.cloud --non-interactive --agree-tos -m admin@ai-auction-experts.cloud

echo "배포가 완료되었습니다! https://vc.ai-auction-experts.cloud 로 접속해보세요."
