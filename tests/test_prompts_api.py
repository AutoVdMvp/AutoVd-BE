from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_list_prompts() -> None:
    response = client.get("/api/v1/prompts")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "image.prompt.generate"


def test_render_prompt() -> None:
    response = client.post(
        "/api/v1/prompts/render",
        json={
            "prompt_id": "image.prompt.generate",
            "variables": {
                "scene_description": "노인이 복지관에서 상담을 받는 장면",
                "character_name": "김영수",
                "character_appearance": "70대 남성, 회색 머리, 따뜻한 인상",
                "character_personality": "차분하고 신중함",
                "style_name": "따뜻한 동화풍",
                "style_prompt": "soft children book illustration, warm pastel colors",
                "negative_prompt": "horror, violent, sexual, distorted face",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "image.prompt.generate"
    assert data["provider"] == "gemini"
    assert "노인이 복지관에서 상담을 받는 장면" in data["user_prompt"]
    assert "김영수" in data["user_prompt"]


def test_render_prompt_missing_variable_returns_400() -> None:
    response = client.post(
        "/api/v1/prompts/render",
        json={
            "prompt_id": "image.prompt.generate",
            "variables": {
                "scene_description": "장면",
            },
        },
    )

    assert response.status_code == 400
    assert "Missing prompt variables" in response.json()["detail"]

