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
    # Chrome Browser Option Setup
    chrome_options = Options()

    # Background Mode
    chrome_options.add_argument("--headless")

    # Linux/Docker 충돌 방지
    chrome_options.add_argument("--no-sandbox")

    # Memory Issue 방지
    chrome_options.add_argument("--disable-dev-shm-usage")

    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = None
    try:
        # Chrome Driver Setup and Browser Launch
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Target URL 접속
        driver.get(url)

        # Page Load Wait
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "p"))
        )

        # Wait for additional content to Load
        time.sleep(2)

        # Title 추출
        title = ""
        title_selectors = [
            "h2#title_area",
            "h2.media_end_head_headline",
            ".news_title",
            "h1",
            "h2",
        ]

        for selector in title_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                title = elements[0].text.strip()
                break
            if not title:
                title = driver.title

        # Content 추출
        article_text = ""
        content_selectors = [
            "#newsct_article",
            "#dic_area",
            "#articleBodyContents",
            "#articleBody",
            ".article_view",
            "article",
        ]

        main_content_found = False
        for selector in content_selectors:
            content_area = driver.find_elements(By.CSS_SELECTOR, selector)
            if content_area:
                article_text = content_area[0].text.strip()
                main_content_found = True
                break

        # 만약 Content Area를 못 찾았다면, p 태그로 수집
        if not main_content_found or len(article_text) < 100:
            paragraphs = driver.find_elements(By.TAG_NAME, "p")
            content_lines = []

            for p in paragraphs:
                text = p.text.strip()

                if len(text) > 30:
                    content_lines.append(text)

            article_text = "\n".join(content_lines)

        # 불필요한 내용 제거(예: 광고, 저작권 정보 등)
        # 이메일 주소 패턴 삭제
        article_text = re.sub(
            r"[a-zA-Z0-9_.+-]@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "", article_text
        )

        # 사진 설명, 언론사명 삭제
        article_text = re.sub(r"\[.*?\]\(.*?\)", "", article_text)

        # 꼬리말이 포함된 줄 삭제
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

            # Noise Keyword가 포함된 줄 삭제
            if any(keyword in line for keyword in noise_keywords):
                continue

            # 너무 짧은 줄 삭제
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
        # Browser end
        if driver:
            driver.quit()
