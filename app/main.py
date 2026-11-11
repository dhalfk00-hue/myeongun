# -*- coding: utf-8 -*-
"""손명리 웹앱 백엔드 (FastAPI). 화면은 /static, API는 /api/v2 (report_api). 사진 업로드 API 없음."""
import mimetypes
from pathlib import Path

mimetypes.add_type("image/webp", ".webp")  # slim 이미지에는 mime.types가 없어 webp가 octet-stream으로 나감

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import report_api

DISCLAIMER = "전통 명리·수상·관상 해석에 기반한 오락·자기이해용 콘텐츠예요. 미래를 예측하지 않으며, 건강·투자·법률 등 중요한 결정은 전문가와 상의하세요."
STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="손명리", version="0.2.0", docs_url=None, redoc_url=None)
app.include_router(report_api.router)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/favicon.ico")
def favicon():
    return FileResponse(STATIC / "icons" / "icon-48.png", media_type="image/png")


@app.get("/privacy")
def privacy():
    return FileResponse(STATIC / "privacy.html", headers={"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():   # 범위(scope)를 / 전체로 두려고 루트에서 제공
    return FileResponse(STATIC / "sw.js", media_type="application/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/.well-known/assetlinks.json")
def assetlinks():   # TWA(안드로이드 앱) 도메인 인증. 앱 서명 SHA-256 을 static/assetlinks.json 에 넣으세요
    return FileResponse(STATIC / "assetlinks.json", media_type="application/json")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
