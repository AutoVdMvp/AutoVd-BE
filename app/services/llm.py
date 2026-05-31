"""
Google Gemini AI 영상 기획 서비스 모듈

뉴스 기사 본문을 입력받아 유튜브 쇼츠 형식의 영상 기획안을
JSON으로 생성하는 함수를 제공합니다.

출력 JSON 구조:
    {
        "scenes": [
            {
                "scene_number": 1,
                "narration": "한 문장 나레이션",
                "image_prompt": "이미지 생성 AI용 영어 프롬프트"
            },
            ...
        ]
    }
"""

import json
import google.generativeai as genai
from app.core.config import settings

# Gemini API 인증 설정 (모듈 로드 시 1회 실행)
genai.configure(api_key=settings.GEMINI_API_KEY)


def generate_video_plan(article_text: str) -> dict:
    """
    뉴스 기사 본문을 분석하여 유튜브 쇼츠용 영상 기획안을 생성합니다.

    Gemini 모델에 기사 본문을 전달하고, 씬 목록(scenes)이 담긴 JSON을 반환합니다.
    각 씬은 1문장 나레이션과 이미지 생성 프롬프트로 구성됩니다.

    Args:
        article_text (str): 크롤링으로 추출된 정제된 기사 본문

    Returns:
        dict: 씬 목록이 담긴 영상 기획안
              {"scenes": [{"scene_number": 1, "narration": "...", "image_prompt": "..."}, ...]}

    Raises:
        ValueError: Gemini가 유효한 JSON 형식을 반환하지 않은 경우
        Exception: Gemini API 호출 중 기타 오류 발생 시
    """
    # Gemini에게 전달할 시스템 프롬프트 (역할 정의 + 출력 형식 지정)
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
        # Gemini 모델 인스턴스 생성
        # - response_mime_type="application/json": JSON 형식으로만 응답하도록 강제
        # - temperature=0.7: 창의성과 일관성의 균형 (0=결정적, 1=창의적)
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest",
            system_instruction=system_prompt,
            generation_config={
                "temperature": 0.7,
                "response_mime_type": "application/json",
            },
        )

        # 사용자 메시지(기사 본문)를 모델에 전달하여 응답 생성
        user_prompt = f"다음 기사를 분석해서 유동적인 씬 개수를 가진 영상 기획안을 JSON으로 만들어줘:\n\n{article_text}"
        response = model.generate_content(user_prompt)

        # 응답 텍스트를 Python dict로 파싱
        video_plan = json.loads(response.text)

        return video_plan

    except json.JSONDecodeError:
        # Gemini가 JSON 형식이 아닌 텍스트를 반환한 경우
        raise ValueError(
            f"Gemini가 올바른 JSON 형식을 반환하지 않았습니다. 원본 응답:\n{response.text}"
        )
    except Exception as e:
        raise Exception(f"Gemini 영상 기획 중 오류가 발생했습니다: {str(e)}")
