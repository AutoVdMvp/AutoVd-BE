import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from app.schemas.video import CrawledSource

_TITLE_SELECTORS = [
    "h2#title_area",
    "h2.media_end_head_headline",
    ".news_title",
    "h1",
    "h2",
]

_CONTENT_SELECTORS = [
    "#newsct_article",
    "#dic_area",
    "#articleBodyContents",
    "#articleBody",
    ".article_view",
    "article",
]

class SeleniumArticleSource:
    """Fetch raw title/content from a URL."""

    def fetch(self, source: str) -> CrawledSource:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # 컨테이너 환경에서 크롬 크래시를 방지하기 위한 추가 옵션
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        driver = None
        try:
            # Docker 내부 환경이므로 webdriver_manager가 적절한 드라이버를 찾아줍니다.
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get(source)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "p"))
            )
            time.sleep(2)

            return CrawledSource(
                title=self._extract_title(driver),
                content=self._extract_content(driver),
                url=source,
            )
        except Exception as exc:
            raise RuntimeError(f"기사 크롤링 실패 ({source}): {exc}") from exc
        finally:
            if driver:
                driver.quit()

    @staticmethod
    def _extract_title(driver) -> str:
        title = ""
        for selector in _TITLE_SELECTORS:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                title = elements[0].text.strip()
                break
        if not title:
            title = driver.title
        return title

    @staticmethod
    def _extract_content(driver) -> str:
        article_text = ""
        main_content_found = False
        for selector in _CONTENT_SELECTORS:
            content_area = driver.find_elements(By.CSS_SELECTOR, selector)
            if content_area:
                article_text = content_area[0].text.strip()
                main_content_found = True
                break

        if not main_content_found or len(article_text) < 100:
            paragraphs = driver.find_elements(By.TAG_NAME, "p")
            content_lines = [
                p.text.strip() for p in paragraphs if len(p.text.strip()) > 30
            ]
            article_text = "\n".join(content_lines)

        return article_text