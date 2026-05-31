# Python Version
FROM python:3.14.5-slim

# 영상/자막 생성 task: MoviePy 렌더링, 오디오/영상 인코딩, TextClip 이미지 생성에 사용합니다.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# 한글 자막 렌더링 task: Docker/Linux 환경에서 사용할 한국어 폰트와 폰트 캐시 도구입니다.
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-nanum \
    fontconfig \
    && fc-cache -f -v \
    && rm -rf /var/lib/apt/lists/*

# Chrome 설치 task: Google Chrome 저장소 등록과 설치 과정에 필요한 도구입니다.
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Selenium/Chrome 실행 task: Headless Chrome 실행에 필요한 런타임 라이브러리입니다.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxinerama1 \
    libxrandr2 \
    libxrender1 \
    libxshmfence1 \
    libxtst6 \
    && rm -rf /var/lib/apt/lists/*


# Google Chrome 브라우저 설치 (최신 gpg 키링 방식 적용)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*


# MoviePy TextClip(caption)이 임시 텍스트 파일(@/tmp/...)을 읽을 수 있도록 ImageMagick path 정책을 조정합니다.
RUN sed -i '/pattern="@\*"/d' /etc/ImageMagick-6/policy.xml || true

# Docker 컨테이너에서 사용할 한국어 자막 폰트 경로입니다. 필요 시 compose 환경변수로 덮어쓸 수 있습니다.
ENV VIDEO_FONT_PATH=/usr/share/fonts/truetype/nanum/NanumGothic.ttf

# 작업 폴더 설정
WORKDIR /app

# Python Package Install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source Code Copy
COPY . .

# 기본 실행 명령어(FastAPI)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
