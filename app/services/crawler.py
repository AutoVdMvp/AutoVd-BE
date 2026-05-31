"""
뉴스 기사 크롤링 서비스 모듈

Selenium WebDriver를 사용하여 뉴스 기사 URL에서
제목(title)과 본문(content)을 추출하고 정제합니다.

주요 기능:
    - JavaScript 렌더링이 필요한 동적 페이지 지원 (Headless Chrome)
    - 네이버 뉴스 등 주요 언론사 CSS 선택자 우선 처리
    - 광고, 저작권 문구, 이메일 주소 등 노이즈 제거
"""

import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def extract_article(url: str) -> dict:
    """
    주어진 URL의 뉴스 기사에서 제목과 본문을 추출하여 반환합니다.

    Args:
        url (str): 크롤링할 뉴스 기사의 전체 URL

    Returns:
        dict: {"title": str, "content": str}
              - title: 기사 제목
              - content: 광고·저작권 문구 등을 제거한 정제된 본문

    Raises:
        Exception: 크롤링 실패 또는 본문이 100자 미만인 경우
    """
    # Chrome 브라우저 옵션 설정
    chrome_options = Options()

    # Headless 모드: 화면 없이 백그라운드에서 실행 (서버 환경 필수)
    chrome_options.add_argument("--headless")

    # Linux/Docker 환경에서 권한 관련 충돌 방지
    chrome_options.add_argument("--no-sandbox")

    # /dev/shm 공유 메모리 이슈 방지 (Docker 환경)
    chrome_options.add_argument("--disable-dev-shm-usage")

    # 일반 사용자처럼 보이도록 User-Agent 설정 (봇 차단 우회)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = None
    try:
        # Chrome Driver 자동 설치 및 브라우저 실행
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # 대상 URL 접속
        driver.get(url)

        # 페이지 내 <p> 태그가 나타날 때까지 최대 10초 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "p"))
        )

        # 동적 콘텐츠(광고, 댓글 등) 추가 로딩 대기
        time.sleep(2)

        # ── 제목 추출 ──────────────────────────────────────────────────────
        # 네이버 뉴스 전용 선택자부터 시도하고, 없으면 범용 선택자 사용
        title = ""
        title_selectors = [
            "h2#title_area",              # 네이버 뉴스 (신형)
            "h2.media_end_head_headline", # 네이버 뉴스 (구형)
            ".news_title",                # 기타 언론사
            "h1",                         # 범용
            "h2",                         # 범용 fallback
        ]

        for selector in title_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                title = elements[0].text.strip()
                break
            if not title:
                title = driver.title  # 위 선택자 모두 실패 시 브라우저 탭 제목 사용

        # ── 본문 추출 ──────────────────────────────────────────────────────
        # 언론사별 주요 본문 영역 선택자를 순서대로 시도
        article_text = ""
        content_selectors = [
            "#newsct_article",      # 네이버 뉴스 (최신)
            "#dic_area",            # 네이버 뉴스 (구형)
            "#articleBodyContents", # 다음 뉴스
            "#articleBody",         # 기타 언론사
            ".article_view",        # 기타 언론사
            "article",              # HTML5 시맨틱 태그
        ]

        main_content_found = False
        for selector in content_selectors:
            content_area = driver.find_elements(By.CSS_SELECTOR, selector)
            if content_area:
                article_text = content_area[0].text.strip()
                main_content_found = True
                break

        # 본문 영역을 못 찾았거나 내용이 너무 짧으면 모든 <p> 태그에서 수집
        if not main_content_found or len(article_text) < 100:
            paragraphs = driver.find_elements(By.TAG_NAME, "p")
            content_lines = []

            for p in paragraphs:
                text = p.text.strip()

                # 너무 짧은 단편 텍스트(버튼 레이블 등)는 제외
                if len(text) > 30:
                    content_lines.append(text)

            article_text = "\n".join(content_lines)

        # ── 노이즈 제거 ────────────────────────────────────────────────────

        # 이메일 주소 패턴 삭제 (예: reporter@news.com)
        article_text = re.sub(
            r"[a-zA-Z0-9_.+-]@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "", article_text
        )

        # 마크다운 링크 형식([텍스트](URL)) 삭제
        article_text = re.sub(r"\[.*?\]\(.*?\)", "", article_text)

        # 저작권·출처 관련 노이즈 키워드가 포함된 줄 전체 삭제
        cleaned_lines = []
        noise_keywords = [
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

        for line in article_text.split("\n"):
            line = line.strip()

            # 노이즈 키워드가 포함된 줄 건너뜀
            if any(keyword in line for keyword in noise_keywords):
                continue

            # 10자 이하의 너무 짧은 줄 제거
            if len(line) > 10:
                cleaned_lines.append(line)

        # 최종 정제된 본문
        article_text = "\n".join(cleaned_lines)

        if len(article_text) < 100:
            raise ValueError("본문 내용을 충분히 추출하지 못했습니다.")

        return {"title": title, "content": article_text}

    except Exception as e:
        raise Exception(f"기사 크롤링 실패 ({url}): {str(e)}")

    finally:
        # 작업 완료(성공/실패 무관) 후 반드시 브라우저 종료
        if driver:
            driver.quit()
