# Python Version
FROM python:3.14.5-slim

# OS Package Install
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    && rm -rf /var/lib/lists/*

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