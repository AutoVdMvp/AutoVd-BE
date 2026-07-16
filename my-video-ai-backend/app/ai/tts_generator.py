import os
import asyncio
import edge_tts
import yaml
from pathlib import Path
from mutagen.mp3 import MP3

from app.services.artifacts.local_store import LocalStore
from app.schemas.video import GeneratedAudio, Scene

_CONFIG_PATH = Path(__file__).resolve().with_name("tts_config.yaml")

_DEFAULTS = {
    "voice": "ko-KR-SunHiNeural",
    "rate": "+0%",
    "pitch": "+0Hz",
    "volume": "+0%",
}

def _load_config() -> dict:
    # tts_config.yaml 파일이 같은 폴더(app/services/ai/)에 있는지 확인
    data = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return {**_DEFAULTS, **data}

class EdgeTTSClient:
    """Concrete edge-tts client used by TTSGenerator."""

    def __init__(self) -> None:
        config = _load_config()
        self.voice = config["voice"]
        self.rate = config["rate"]
        self.pitch = config["pitch"]
        self.volume = config["volume"]

    def speak(self, text: str, dest: str) -> float:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            pitch=self.pitch,
            volume=self.volume,
        )
        # asyncio.run은 메인 스레드 호출 시에만 사용 권장 (Celery Task 내에서는 루프 주의)
        # 하지만 여기서는 개별 태스크 단위로 호출되므로 안정적입니다.
        asyncio.run(communicate.save(dest))
        return float(MP3(dest).info.length)

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