import re

from app.services.crawling.selenium import SeleniumArticleSource
from app.schemas.video import CrawledSource, VideoGenerateRequest

_NOISE_KEYWORDS = [
    "무단 전재",
    "재배포 금지",
    "Copyright",
    "ⓒ",
    "저작권자",
    "기자 =",
    "제공처",
    "구독하고",
    "메인에서 바로",
]

_MIN_CONTENT_LENGTH = 100

class Crawler:
    """Fetch URL content or pass direct text through as a CrawledSource."""

    def fetch(self, request: VideoGenerateRequest) -> CrawledSource:
        if request.text and request.text.strip():
            return CrawledSource(content=request.text.strip())

        if request.url is None:
            raise ValueError("url 또는 text 중 하나는 필요합니다.")

        source_url = str(request.url)
        # 같은 폴더 내의 selenium 모듈을 사용하여 데이터를 가져옴
        source = SeleniumArticleSource().fetch(source_url)
        content = _clean(source.content)
        if len(content) < _MIN_CONTENT_LENGTH:
            raise ValueError("본문 내용을 충분히 추출하지 못했습니다.")

        return CrawledSource(
            url=source.url or source_url,
            title=source.title,
            content=content,
        )

def _clean(text: str) -> str:
    text = re.sub(r"[a-zA-Z0-9_.+-]@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "", text)
    text = re.sub(r"\[.*?\]\(.*?\)", "", text)

    cleaned_lines = []
    for line in text.split("\n"):
        line = line.strip()
        if any(keyword in line for keyword in _NOISE_KEYWORDS):
            continue
        if len(line) > 10:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)