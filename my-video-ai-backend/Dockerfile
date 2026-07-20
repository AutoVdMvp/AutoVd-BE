# Python Version
FROM python:3.11-slim

# 영상/자막 생성 및 시스템 기본 도구 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    imagemagick \
    fonts-nanum \
    fontconfig \
    wget \
    gnupg \
    unzip \
    && fc-cache -f -v \
    && rm -rf /var/lib/apt/lists/*

# Selenium 실행을 위한 필수 OS 라이브러리 설치
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

# Google Chrome 설치
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ImageMagick 보안 정책 우회 (오류 수정 완료)
RUN find /etc -name "policy.xml" -exec sed -i 's/"none"/"read|write"/g' {} +
RUN find /etc -path '*/ImageMagick-*/policy.xml' -exec sed -i '/pattern="@\*"/d' {} \; || true

# 컨테이너 내부 한국어 자막 폰트 환경 변수
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