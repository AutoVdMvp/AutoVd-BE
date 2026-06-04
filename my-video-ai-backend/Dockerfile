# Python Version
FROM python:3.11-slim

# OS Package Install
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    fonts-nanum \
    wget \
    gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && sh -c 'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ImageMagick 보안 정책 우회
RUN sed -i 's/<policy domain="path" rights="none" pattern="@\*"//g' /etc/ImageMagick-6/policy.xml || true

# 작업 폴더 설정
WORKDIR /app

# Python Package Install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source Code Copy
COPY . .

# 기본 실행 명령어(FastAPI)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]