import os

from app.ai.tts.client import EdgeTTSClient
from app.services.artifacts.local_store import LocalStore
from app.schemas.video import GeneratedAudio, Scene

class TTSGenerator:
    """Scene.narration[] -> GeneratedAudio[]."""

    def __init__(
        self,
        client: EdgeTTSClient | None = None,
        store: LocalStore | None = None,
    ) -> None:
        self.client = client or EdgeTTSClient()
        self.store = store or LocalStore()

    def generate(self, project_id: str, scenes: list[Scene]) -> list[GeneratedAudio]:
        if not scenes:
            raise ValueError("Scene이 없어서 TTS를 생성할 수 없습니다.")

        audios = []
        for scene in scenes:
            dest = self.store.audio_path(project_id, scene.index)
            try:
                # 개별 TTS 생성
                duration = self.client.speak(scene.narration, dest)
            except Exception as exc:
                raise RuntimeError(f"[Scene {scene.index}] TTS 생성 실패: {exc}") from exc

            if duration <= 0:
                raise RuntimeError(f"[Scene {scene.index}] TTS 음성 길이를 확인할 수 없습니다.")
            if not os.path.exists(dest):
                raise FileNotFoundError(f"[Scene {scene.index}] audio 파일 누락: {dest}")

            audios.append(
                GeneratedAudio(scene_index=scene.index, path=dest, duration_sec=duration)
            )

        return audios
