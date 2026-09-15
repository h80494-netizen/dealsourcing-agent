import tarfile
import os

def create_patch():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    patch_file = os.path.join(base_dir, 'update_analyzer.tar.gz')
    
    # 묶을 파일 경로
    files_to_pack = [
        'processor/analyzer.py',
        'backend/main.py',
        'frontend/index.html',
        'frontend/script.js'
    ]
    
    with tarfile.open(patch_file, "w:gz") as tar:
        for file in files_to_pack:
            file_path = os.path.join(base_dir, file)
            if os.path.exists(file_path):
                tar.add(file_path, arcname=file)
                print(f"추가됨: {file}")
            else:
                print(f"파일을 찾을 수 없음: {file}")
                
    print(f"\n패치 아카이브 생성 완료: {patch_file}")
    print("이 파일을 AWS 서버에 업로드한 후 압축을 풀고 백엔드를 재시작(sudo systemctl restart vc-dealsourcing) 해주세요.")

if __name__ == "__main__":
    create_patch()
