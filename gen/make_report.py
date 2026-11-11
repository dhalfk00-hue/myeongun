#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""손명리 사주(+손금) 감정서 고속 생성기 — LLM 호출 없음, 전부 로컬.

예) python3 make_report.py --gender F --date 1992-03-14 --time 09:30 --place 서울 --out /tmp/report.pdf
    python3 make_report.py --name 홍길동 --gender M --date 1990-05-03 --time 14:20 --place 서울 \
        --palm-json palm.json --out out.pdf
"""
import argparse, asyncio, json, os, re, shutil, subprocess, sys, time
from datetime import datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E
import build as B
import lunar as L


def time_label(t):
    if not t: return "시간 미상"
    h, m = map(int, t.split(":"))
    part = "새벽" if h < 6 else "오전" if h < 12 else "낮" if h == 12 else "오후" if h < 18 else "저녁" if h < 21 else "밤"
    hh = h if h <= 12 else h - 12
    return f"{part} {hh}시" + (f" {m}분" if m else "")


def assemble(args, now):
    y, m, d = map(int, args.date.split("-"))
    if args.lunar:
        sd = L.lunar_to_solar(y, m, d, args.leap)  # 잘못된 음력 날짜면 여기서 에러
    r = E.run_saju(args.date, args.time, args.lunar, args.leap, args.gender, args.place, now.year, now.year + 11)
    c = E.Chart(r, args.gender, now)
    sd = r["solar_date"]
    if args.lunar:
        dl = f"음력 {y}년 {m}월 {d}일{'(윤달)' if args.leap else ''} {time_label(args.time)} (양력 {int(sd[:4])}년 {int(sd[5:7])}월 {int(sd[8:])}일)"
    else:
        dl = f"양력 {y}년 {m}월 {d}일 {time_label(args.time)}"
    place = getattr(args, "place_label", None) or args.place or "서울"
    inp = dict(date=args.date, lunar=args.lunar, leap=args.leap, time=args.time, date_label=dl, place_label=place)
    rep = B.Report(c, args.name, inp, now)
    palm = None
    if args.palm_json:
        import palm as PM
        palm = args.palm_json if isinstance(args.palm_json, dict) else json.load(open(args.palm_json))
        if args.palm_photo: palm["photo"] = args.palm_photo
    # 사주+손금 함께 볼 때는 손금(재운선·대박손금 → 6대 선 × 사주) → 사주×손금 종합 → 나머지 사주 순서
    pages = [rep.cover(palm)]
    hooks = {"__PALM_KEY2__": "", "__PALM_HEALTH__": "", "__PALM_TIMING__": "", "__PALM_CLOSING__": "", "__PALM_LIMIT__": ""}
    assets = {}
    if palm:
        ov_name = "palm_overlay.jpg"
        assets[ov_name] = palm
        ppages, items, lucky = PM.palm_html(palm, rep, ov_name, rep.no + 1)
        rep.no += 1
        pages += ppages
        pages.append(rep.p_synth(items, lucky, palm))
    pages += [rep.p_chart(), rep.p_yongsin(), rep.p_persona_money(), rep.p_job_love_health(), rep.p_daeun()]
    pages += rep.p_years()
    pages.append(rep.p_decade())
    if palm:
        fl = palm.get("flags", {})
        js = fl.get("jaeun", {}).get("state", "none")
        hooks["__PALM_KEY2__"] = f"손금의 재운선은 {items[0]['tag']}이에요."
        hooks["__PALM_HEALTH__"] = f"손금의 생명선은 {items[3]['tag']}이라 " + ("회복력이 좋은 편이에요. " if fl.get("life", {}).get("venus", "wide") == "wide" else "체력 관리가 특히 중요해요. ")
        hooks["__PALM_TIMING__"] = "손금 유년법 · 운명선 × 두뇌선 = 35~38세, × 감정선 = 55세" + (", 재운선 = 50~55세 이후" if js == "above_heart" else "")
        hooks["__PALM_CLOSING__"] = "손금도 같은 길을 가리키고 있어요."
        hooks["__PALM_LIMIT__"] = f"손금은 {palm.get('hand', '오른손')} 사진으로 판독했어요" + ("(반대 손 사진이 없어 양손 비교는 하지 않았어요). " if not palm.get("both_hands") else ". ")
    else:
        hooks["__PALM_TIMING__"] = "좋은 해에 큰 계획을, 지키는 해에 준비를"
    pages.append(rep.p_end(bool(palm)))
    html = "\n".join(pages)
    html = html.replace("<li>__PALM_TIMING__</li>", f"<li>{hooks['__PALM_TIMING__']}</li>")
    for k, v in hooks.items(): html = html.replace(k, v)
    n = 0
    def pg(mm):
        nonlocal n; n += 1; return str(n)
    html = re.sub("__PG__", pg, html)
    for bad in ("\ubc31\uc6b4", "\ub3c4\uc0ac", "\ucca0\ud559\uc6d0", "\ube14\ub85c\uadf8"):
        assert bad not in html, f"금지어 포함: {bad}"
    doc = f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>손명리 감정서</title><link rel="stylesheet" href="style.css"></head><body>\n{html}\n</body></html>'
    return doc, assets, rep, c


# 메모리 적은 서버(512MB)용: 프로세스 수·공유메모리 줄이기
CHROME_ARGS = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--no-zygote", "--disable-extensions",
               "--disable-background-networking", "--disable-sync", "--mute-audio", "--no-first-run",
               "--renderer-process-limit=1", "--js-flags=--max-old-space-size=192"]
if os.environ.get("MYEONGUN_CHROME_SINGLE") == "1":
    CHROME_ARGS.append("--single-process")


async def render(src, out, fit=True):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None, args=CHROME_ARGS)
        pg = await b.new_page(viewport={"width": 794, "height": 1123})
        await pg.goto("file://" + src); await pg.wait_for_timeout(300)
        js = """[...document.querySelectorAll('.page')].map((s,i)=>{const r=s.getBoundingClientRect();let m=0;s.querySelectorAll('.in *').forEach(e=>{const q=e.getBoundingClientRect();if(q.height>0)m=Math.max(m,q.bottom-r.top)});return Math.round(m)})"""
        ov = await pg.evaluate(js)
        for it in range(4):
            bad = [i for i, h in enumerate(ov) if h > 1045]
            if not bad or not fit: break
            await pg.evaluate("""(bad)=>{const ps=[...document.querySelectorAll('.page')];bad.forEach(i=>{const el=ps[i].querySelector('.in');const z=parseFloat(el.dataset.z||'1')-0.05;el.dataset.z=z;el.style.zoom=z;});}""", bad)
            ov = await pg.evaluate(js)
        await pg.pdf(path=out, format="A4", print_background=True, prefer_css_page_size=True)
        await b.close()
        return ov


def main():
    ap = argparse.ArgumentParser(description="손명리 사주(+손금) 감정서 생성기")
    ap.add_argument("--name"); ap.add_argument("--gender", required=True, choices=["F", "M", "f", "m", "여", "남"])
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (기본 양력, --lunar 면 음력)")
    ap.add_argument("--lunar", action="store_true"); ap.add_argument("--leap", action="store_true", help="음력 윤달")
    ap.add_argument("--time", help="HH:MM (모르면 생략)"); ap.add_argument("--place", default="서울", help="출생지(서울·광주…) 또는 경도")
    ap.add_argument("--palm-json", help="손금 선 좌표·특징 JSON (README 참고)"); ap.add_argument("--palm-photo", help="손 사진 경로(JSON의 photo 대신)")
    ap.add_argument("--out", required=True); ap.add_argument("--now", help="기준일 YYYY-MM-DD (기본 오늘)")
    ap.add_argument("--previews", action="store_true", help="페이지별 PNG 미리보기도 저장")
    ap.add_argument("--keep-html", action="store_true")
    a = ap.parse_args()
    a.gender = {"f": "F", "m": "M", "여": "F", "남": "M"}.get(a.gender, a.gender)
    t0 = time.time()
    now = datetime.fromisoformat(a.now) if a.now else datetime.now()
    doc, assets, rep, c = assemble(a, now)
    out = os.path.abspath(a.out)
    work = out[:-4] + "_build"
    os.makedirs(work, exist_ok=True)
    shutil.copy(os.path.join(HERE, "assets", "style.css"), work)
    for nm, spec in assets.items():
        import palm as PM
        PM.render_overlay(spec, os.path.join(work, nm))
        shutil.copy(os.path.join(work, nm), out[:-4] + "_palm_overlay.jpg")
    src = os.path.join(work, "report.html")
    open(src, "w").write(doc)
    t1 = time.time()
    ov = asyncio.run(render(src, out))
    t2 = time.time()
    if a.previews:
        subprocess.run(["pdftoppm", "-r", "96", "-png", out, out[:-4] + "_p"], check=True)
    if not a.keep_html:
        pass
    print(json.dumps({"pdf": out, "pages": len(ov), "page_heights": ov, "용신": c.yong, "희신": c.hee, "격국": c.gyeok,
                      "강약": c.st_label, "years": {y: rep.ystar[y] for y in rep.years},
                      "sec_analysis": round(t1 - t0, 2), "sec_render": round(t2 - t1, 2), "sec_total": round(time.time() - t0, 2)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
