import json
import google.generativeai as genai
from app.core.config import settings

# # Gemini API Key Setup
genai.configure(api_key=settings.GEMINI_API_KEY)

def generate_video_plan(article_text: str) -> dict:
    system_prompt = """당신은 유튜브 쇼츠(Shorts) 전문 영상 기획자입니다.
    주어진 기사 본문을 분석하여 시청자가 지루하지 않게 빠르고 역동적인 템포의 영상 기획안을 작성하세요.
    
    [조건 - 매우 중요]
    1. 나레이션 분할: 대본(narration)은 반드시 '1문장' 단위로 짧게 쪼개어 하나의 씬(Scene)에 배정하세요. (절대 한 씬에 두 문장 이상 넣지 마세요!)
    2. 무제한 씬(Scene) 생성: 4개로 제한하지 마세요! 기사 내용의 길이에 맞춰 필요한 만큼 씬을 5개, 8개, 12개 등 자유롭게 무한정 생성하세요.
    3. 각 씬의 'image_prompt'는 이미지 생성 AI가 이해할 수 있도록 해당 씬의 대본 상황을 묘사하는 영어 프롬프트를 작성하세요. (예: "A cinematic hyper-realistic shot of a futuristic city, 8k, highly detailed")
    4. 반드시 지정된 JSON 구조로만 응답하세요.
    
    [출력 JSON 형식]
    {
        "scenes": [
            {
                "scene_number": 1,
                "narration": "안녕하세요, 오늘 가장 화제가 된 기술 소식입니다.",
                "image_prompt": "A modern news studio desk with a glowing hologram, cinematic lighting, 8k"
            },
            {
                "scene_number": 2,
                "narration": "최근 엄청난 발전으로 우리의 일상이 크게 바뀔 것입니다.",
                "image_prompt": "People walking in a futuristic smart city with flying cars, bright sunny day, 8k"
            }
            // ... 대본 길이에 맞춰 3, 4, 5, 6... 필요한 만큼 무한정 추가!
        ]
    }"""

    try:
        # Gemini Model Setup
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest",
            system_instruction=system_prompt,
            generation_config={
                "temperature": 0.7,
                "response_mime_type": "application/json",
            }
        )

        # Model에 Prompt 전달
        user_prompt = f"다음 기사를 분석해서 유동적인 씬 개수를 가진 영상 기획안을 JSON으로 만들어줘:\n\n{article_text}"
        response = model.generate_content(user_prompt)

        # JSON Parsing
        video_plan = json.loads(response.text)

        return video_plan
    
    except json.JSONDecodeError:
        raise ValueError(f"Gemini가 올바른 JSON 형식을 반환하지 않았습니다. 원본 응답:\n{response.text}")
    except Exception as e:
        raise Exception(f"Gemini 영상 기획 중 오류가 발생했습니다: {str(e)}")