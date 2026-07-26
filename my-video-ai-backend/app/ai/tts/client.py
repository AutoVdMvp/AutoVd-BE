import asyncio
import os
from pathlib import Path

import edge_tts
import yaml
from mutagen.mp3 import MP3

_CONFIG_PATH = Path(__file__).resolve().with_name("config.yaml")

_DEFAULTS = {
    "voice": "ko-KR-SunHiNeural",
    "rate": "+0%",
    "pitch": "+0Hz",
    "volume": "+0%",
}


def _load_config() -> dict:
    # config.yaml 파일이 같은 폴더에 있는지 확인
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
