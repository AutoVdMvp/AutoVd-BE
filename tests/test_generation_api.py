import json

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_generate_image_prompt_uses_stub_provider() -> None:
    response = client.post(
        "/api/v1/generation/image-prompt",
        json={
            "scene_description": "노인이 복지관에서 상담을 받는 장면",
            "character": {
                "name": "김영수",
                "appearance_prompt": "70대 남성, 회색 머리, 따뜻한 인상",
                "personality_prompt": "차분하고 신중함",
            },
            "style": {
                "name": "따뜻한 동화풍",
                "style_prompt": "soft children book illustration, warm pastel colors",
                "negative_prompt": "horror, violent, sexual, distorted face",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["prompt_id"] == "image.prompt.generate"
    assert data["provider"] == "gemini"
    assert data["model"] == "gemini-2.5-flash"

    raw_result = json.loads(data["raw_result"])
    assert raw_result["provider"] == "gemini"
    assert raw_result["camera_angle"] == "medium shot"

