import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 키가 제대로 들어왔는지 확인 (보안상 앞 10자리만 출력)
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ 에러: .env 파일에서 GEMINI_API_KEY를 찾지 못했습니다!")
else:
    print(f"✅ 키 로드 성공: {api_key[:10]}...")

    genai.configure(api_key=api_key)
    print("🔍 사용 가능한 Gemini 모델 목록 조회 중...")
    
    models = genai.list_models()
    count = 0
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            count += 1
            
    if count == 0:
        print("❌ 사용 가능한 모델이 없습니다. (API 키 권한 또는 구글 클라우드 설정 확인 필요)")