# 명운 (Render 무료 웹 서비스, Docker). Render가 $PORT 를 정해 줌(기본 10000)
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    MYEONGUN_CACHE=/tmp/myeongun-cache \
    MYEONGUN_DEV_UNLOCK=1 \
    TZ=Asia/Seoul \
    PORT=10000

# 한글 폰트 (감정서 PDF · 손금 그림)
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk fontconfig tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/user/app
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && playwright install --with-deps --only-shell chromium \
    && chmod -R a+rx /ms-playwright \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
COPY --chown=user:user . .
USER user
ENV HOME=/home/user

EXPOSE 10000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --proxy-headers --forwarded-allow-ips '*'"]
