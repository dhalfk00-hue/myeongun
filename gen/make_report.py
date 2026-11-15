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
from josa import josa, particle, fix_josa, settle


def time_label(t):
    if not t: return "시간 미상"
    h, m = map(int, t.split(":"))
    part = "새벽" if h < 6 else "오전" if h < 12 else "낮" if h == 12 else "오후" if h < 18 else "저녁" if h < 21 else "밤"
    hh = h if h <= 12 else h - 12
    return f"{part} {hh}시" + (f" {m}분" if m else "")


def prepare(args, now):
    """tier1115: 입력 → (Chart, Report). 종합 감정서와 등급별 감정서가 같은 계산을 써요."""
    y, m, d = map(int, args.date.split("-"))
    if args.lunar:
        sd = L.lunar_to_solar(y, m, d, args.leap)  # 잘못된 음력 날짜면 여기서 에러
    import jobs as JB
    JB.apply(getattr(args, "job", None) or "미정", age=now.year - y + 1)  # release1116: 세는 나이(60세+ 무직 문구용)
    rule = getattr(args, "time_rule", None) or "경도"
    calc_place = "127.5" if rule == "30분" else args.place  # sync1114: '30분' = 표준시 −30분(동경 127.5°) 관례, 기본은 출생지 경도
    r = E.run_saju(args.date, args.time, args.lunar, args.leap, args.gender, calc_place, now.year, now.year + 11)
    c = E.Chart(r, args.gender, now)
    sd = r["solar_date"]
    if args.lunar:
        dl = f"음력 {y}년 {m}월 {d}일{'(윤달)' if args.leap else ''} {time_label(args.time)} (양력 {int(sd[:4])}년 {int(sd[5:7])}월 {int(sd[8:])}일)"
    else:
        dl = f"양력 {y}년 {m}월 {d}일 {time_label(args.time)}"
    place = getattr(args, "place_label", None) or args.place or "서울"
    try: float(place); place = "출생지"
    except (TypeError, ValueError): pass
    inp = dict(date=args.date, lunar=args.lunar, leap=args.leap, time=args.time, date_label=dl, place_label=place,
               time_rule=rule, place=args.place)
    rep = B.Report(c, args.name, inp, now)
    return c, rep, inp


def finish(html, title="손명리 감정서"):
    """쪽 번호 · 조사 고치기 · 금지어 검사 → 완성 문서"""
    n = 0
    def pg(mm):
        nonlocal n; n += 1; return str(n)
    html = re.sub("__PG__", pg, html)
    html = fix_josa(html)
    import gloss as GL   # gloss1116: 사주 용어 쉬운 풀이 · 한자는 한글 읽기와 함께
    html = settle(fix_josa(GL.apply(html)))   # josa1116: 풀이 괄호를 건너뛰고 앞 한글 낱말 받침에 맞춰 조사를 마지막으로 골라요
    for bad in ("\ubc31\uc6b4", "\ub3c4\uc0ac", "\ucca0\ud559\uc6d0", "\ube14\ub85c\uadf8"):
        assert bad not in html, f"금지어 포함: {bad}"
    return f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=800, initial-scale=1"><style>html{{-webkit-text-size-adjust:100%;text-size-adjust:100%}}</style><title>{title}</title><link rel="stylesheet" href="style.css"></head><body>\n{html}\n</body></html>'


def assemble(args, now):
    if getattr(args, "tier", None):
        import tiers as TR
        return TR.assemble_tier(args, now)
    c, rep, inp = prepare(args, now)
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
        fs = fl.get("fate", {}).get("state", "clear")
        jtag = items[0]["tag"]
        ltag = items[3]["tag"]
        if js == "none":
            hooks["__PALM_KEY2__"] = "손금에서는 약지 아래 뚜렷한 재운선이 확인되지 않았어요."
        else:
            hooks["__PALM_KEY2__"] = f"손금의 재운선은 {josa(jtag, '이에요')}."
        if fl.get("life", {}).get("venus", "wide") == "wide":
            hooks["__PALM_HEALTH__"] = f"손금의 생명선은 {josa(ltag, '이라')} 체력과 활력, 추진력이 좋아요. "
        else:
            hooks["__PALM_HEALTH__"] = f"손금의 생명선은 {josa(ltag, '이라')} 체력 관리가 특히 중요해요. "
        if fs == "none":
            hooks["__PALM_TIMING__"] = "운명선이 뚜렷하지 않은 형 · 자유롭게 자기 길을 만드는 형"
        else:
            hooks["__PALM_TIMING__"] = "손금 유년법 · 운명선 × 두뇌선 = 35~38세, × 감정선 = 55세" + ((", 재운선 = 50~55세 이후" if rep.fifties_ok() else ", 재운선 = 50대는 지키고 관리하는 때") if js == "above_heart" else "")
        hooks["__PALM_CLOSING__"] = "손금도 같은 길을 가리키고 있어요."
        hooks["__PALM_LIMIT__"] = f"손금은 {palm.get('hand', '오른손')} 사진으로 판독했어요" + ("(반대 손 사진이 없어 양손 비교는 하지 않았어요). " if not palm.get("both_hands") else ". ")
    else:
        hooks["__PALM_TIMING__"] = "좋은 해에 큰 계획을, 지키는 해에 준비를"
    pages.append(rep.p_end(bool(palm)))
    html = "\n".join(pages)
    html = html.replace("<li>__PALM_TIMING__</li>", f"<li>{hooks['__PALM_TIMING__']}</li>")
    for k, v in hooks.items(): html = html.replace(k, v)
    return finish(html), assets, rep, c


LIMIT = 1045          # 쪽 안쪽 내용 높이 한도(px)
ZOOM_MIN = 0.85       # 이보다 작게 줄이지 않아요(가독성)
SPLIT_AT = int(LIMIT / ZOOM_MIN)  # 이 높이를 넘으면(0.85로도 못 담으면) 축소 대신 쪽을 나눠요
SPLIT_JS = r"""([idx, LIM]) => {
  const pages = () => [...document.querySelectorAll('.page')];
  const full = (s) => { const r = s.getBoundingClientRect(); let m = 0;
    s.querySelectorAll('.in *').forEach(e => { const q = e.getBoundingClientRect(); if (q.height > 0) m = Math.max(m, q.bottom - r.top); }); return m; };
  // release1116: 빠른 측정 — '.in'의 바로 아래 블록만 먼저 재고(항상 full 이하), 한도 안으로 들어오면 그때만 전체를 재요. 판정은 full과 똑같아요.
  const fast = (s) => { const r = s.getBoundingClientRect(); let m = 0;
    s.querySelectorAll(':scope > .in > *').forEach(e => { const q = e.getBoundingClientRect(); if (q.height > 0) m = Math.max(m, q.bottom - r.top); }); return m; };
  const meas = (s) => { const f = fast(s); return f > LIM ? f : full(s); };
  const targets = idx.map(i => pages()[i]);
  targets.forEach(pg => {
    const inEl = pg.querySelector('.in'); if (!inEl) return;
    // tier1115: 흐름 쪽은 넘친 내용을 다음 흐름 쪽 맨 앞으로 밀어 넣어요(새 쪽을 끼우면 중간에 빈 쪽이 생겨요)
    const nx = pg.nextElementSibling;
    let np, ni, cont;
    if (pg.classList.contains('flow') && nx && nx.classList && nx.classList.contains('flow') && nx.querySelector(':scope > .in')) {
      np = nx; ni = nx.querySelector(':scope > .in');
      cont = ni.querySelector(':scope > .sub.cont');
      if (!cont) { cont = document.createElement('div'); cont.className = 'sub cont'; ni.insertBefore(cont, ni.firstChild); }
    } else {
      np = pg.cloneNode(false); ni = document.createElement('div'); ni.className = 'in'; np.appendChild(ni);
      const ft = pg.querySelector('.foot'); if (ft) np.appendChild(ft.cloneNode(true));
      pg.after(np);
      cont = document.createElement('div'); cont.className = 'sub cont'; ni.appendChild(cont);
    }
    const front = () => cont.nextSibling;
    // tier1115: 통째로 넘기는 표·목록 조각이 다음 쪽 맨 앞의 같은 원본 조각과 만나면 하나로 합쳐요(머리줄 반복 방지)
    const put = (el) => {
      const f = cont.nextElementSibling, sid = el.dataset && el.dataset.sid;
      if (f && sid && f.dataset.sid === sid && f.tagName === el.tagName) {
        if (el.tagName === 'TABLE') { const tb2 = f.querySelector('tbody') || f; const rs = [...el.querySelectorAll('tr')].slice(1); const at = tb2.children[1] || null; rs.forEach(r => tb2.insertBefore(r, at)); el.remove(); return; }
        const u1 = el.tagName === 'UL' ? el : el.querySelector(':scope > ul'), u2 = f.tagName === 'UL' ? f : f.querySelector(':scope > ul');
        if (u1 && u2) { const at = u2.firstChild; [...u1.children].forEach(li => u2.insertBefore(li, at)); if (el.dataset.splitUl === undefined) { ni.insertBefore(el, f); u1.append(...u2.children); f.remove(); } else el.remove(); return; }
      }
      ni.insertBefore(el, front());
    };
    let guard = 0;
    while (meas(pg) > LIM && inEl.children.length > 2 && guard++ < 200) {
      const last = inEl.lastElementChild;
      const rows = last.tagName === 'TABLE' ? [...last.querySelectorAll('tr')] : null;
      const lis = (!rows && last.querySelector) ? (last.tagName === 'UL' ? last : last.querySelector(':scope > ul')) : null;
      if (!last.dataset.sid) last.dataset.sid = 's' + (window.__sid = (window.__sid || 0) + 1);   // tier1115: 나눈 조각은 같은 원본끼리만 이어요
      const sid = last.dataset.sid;
      if (rows && rows.length > 3) {   // 표는 머리줄을 복제해 행 단위로 넘겨요
        let t2 = ni.querySelector(':scope > table[data-sid="' + sid + '"]');
        if (!t2) { t2 = last.cloneNode(false); t2.dataset.split = sid; const hd = rows[0].cloneNode(true); const tb = document.createElement('tbody'); tb.appendChild(hd); t2.appendChild(tb); ni.insertBefore(t2, front()); }
        const tb2 = t2.querySelector('tbody');
        while (meas(pg) > LIM && last.querySelectorAll('tr').length > 2) { const rs = last.querySelectorAll('tr'); tb2.insertBefore(rs[rs.length - 1], tb2.children[1] || null); }
        if (meas(pg) > LIM) { put(last); }   // 그래도 넘치면 표 전체를 넘겨요(앞 조각과 합쳐요)
        continue;
      }
      if (lis && lis.children.length > 2) {   // 조언 목록은 항목 단위로
        let box = ni.querySelector(':scope > [data-sid="' + sid + '"]');
        if (!box) { box = last.cloneNode(true); box.dataset.splitUl = sid; const u = box.tagName === 'UL' ? box : box.querySelector(':scope > ul'); u.innerHTML = ''; [...box.children].forEach(ch => { if (ch !== u) ch.remove(); }); ni.insertBefore(box, front()); }
        const u2 = box.tagName === 'UL' ? box : box.querySelector(':scope > ul');
        while (meas(pg) > LIM && lis.children.length > 1) u2.insertBefore(lis.lastElementChild, u2.firstChild);
        if (meas(pg) > LIM) { put(last); }
        continue;
      }
      put(last);
    }
    // 제목·부제·구분선이 쪽 끝에 홀로 남지 않게 다음 쪽으로 함께 넘겨요
    const lone = (e) => e && (/^H[23]$/.test(e.tagName) || e.classList.contains('sub') || e.classList.contains('rule'));
    while (inEl.children.length > 2 && lone(inEl.lastElementChild)) ni.insertBefore(inEl.lastElementChild, front());
    // tier1115: '(이어서)' 이름은 이 쪽에 남은 마지막 큰 제목(없으면 이 쪽의 이어서 이름)
    const hs = [...inEl.children].filter(e => e.tagName === 'H2');
    const oc = inEl.querySelector(':scope > .sub.cont');
    cont.textContent = (hs.length ? hs[hs.length - 1].textContent.replace(/^\d+/, '').trim() : (oc ? oc.textContent.replace(/ \(이어서\)$/, '') : '')) + ' (이어서)';
    const f1 = cont.nextElementSibling;
    if (f1 && (f1.tagName === 'H2' || (f1.classList.contains('rule') && f1.nextElementSibling && f1.nextElementSibling.tagName === 'H2'))) {
      cont.remove(); if (f1.classList.contains('rule')) f1.remove();
    }
  });
  pages().forEach((s, i) => { const f = s.querySelector('.foot'); if (f) f.innerHTML = f.innerHTML.replace(/SONMYEONGRI · \d+/, 'SONMYEONGRI · ' + (i + 1)); });
}"""


# tier1115: 마지막 쪽에 끝맺음 안내(.tiny)만 조금 넘어간 경우, 앞 쪽을 조금만(0.92 이상) 줄여 함께 담아요(거의 빈 마지막 쪽 방지)
TAIL_JS = r"""([LIM]) => {
  const meas = (s) => { const r = s.getBoundingClientRect(); let m = 0;
    s.querySelectorAll('.in *').forEach(e => { const q = e.getBoundingClientRect(); if (q.height > 0) m = Math.max(m, q.bottom - r.top); }); return m; };
  const ps = [...document.querySelectorAll('.page')]; const L = ps[ps.length - 1], P = ps[ps.length - 2];
  if (!L || !P || !L.classList.contains('flow') || !P.classList.contains('flow') || L.classList.contains('lite')) return 0;
  const li = L.querySelector(':scope > .in'), pi = P.querySelector(':scope > .in'); if (!li || !pi || pi.dataset.z) return 0;
  const kids = [...li.children].filter(e => !(e.classList.contains('sub') && e.classList.contains('cont')));
  if (!kids.length || !kids.every(e => e.classList.contains('tiny') || e.classList.contains('rule') || e.tagName === 'HR')) return 0;
  if (meas(L) > 0.3 * LIM) return 0;
  kids.forEach(e => pi.appendChild(e));
  const h = meas(P), z = Math.min(1, (LIM - 5) / h);
  if (z < 0.92) { kids.forEach(e => li.appendChild(e)); return 0; }
  if (z < 1) { pi.dataset.z = z; pi.style.zoom = z; }
  L.remove();
  [...document.querySelectorAll('.page')].forEach((s, i) => { const f = s.querySelector('.foot'); if (f) f.innerHTML = f.innerHTML.replace(/SONMYEONGRI · \d+/, 'SONMYEONGRI · ' + (i + 1)); });
  return 1;
}"""


# 앱 화면(HTML 보기)에서도 PDF와 같은 쪽 나누기·축소를 브라우저에서 해 주는 스크립트 (report_api가 보기 응답에만 붙여요)
# ui1115: PDF와 같은 고정 좌표계. 페이지 측정 중 바깥 화면 축소를 하지 않아요.
VIEW_FIT_JS = ("<script>(()=>{const LIM=" + str(LIMIT) + ",SPL=" + str(SPLIT_AT) + ",ZMIN=" + str(ZOOM_MIN) + ";"
               "const meas=(s)=>{const r=s.getBoundingClientRect();let m=0;s.querySelectorAll('.in *').forEach(e=>{const q=e.getBoundingClientRect();if(q.height>0)m=Math.max(m,q.bottom-r.top)});return m};"
               "const split=" + SPLIT_JS + ";"
               "const st=document.createElement('style');st.textContent='@media screen{.page{height:auto!important;min-height:297mm;overflow:visible!important}}';document.head.appendChild(st);"   # ui1115: 화면에서는 어떤 경우에도 내용을 자르지 않고 종이가 늘어나요(PDF는 그대로)
               "let busy=false;const go=()=>{if(busy)return;busy=true;"
               "for(let k=0;k<120;k++){const ps=[...document.querySelectorAll('.page')];const big=ps.map((s,i)=>[i,meas(s),s.classList.contains('flow')&&!s.classList.contains('lite')]).filter(x=>x[1]>(x[2]?LIM:SPL)).map(x=>x[0]);if(!big.length)break;split([big,LIM]);}"
               "(" + TAIL_JS + ")([LIM]);"
               "for(let k=0;k<8;k++){document.querySelectorAll('.page').forEach(s=>{const h=meas(s);if(h>LIM){const el=s.querySelector('.in');const z0=parseFloat(el.dataset.z||'1');const z=Math.max(ZMIN,Math.min(z0-0.02,z0*1040/h));el.dataset.z=z;el.style.zoom=z;}});}"
               "document.documentElement.dataset.fitReady='1';busy=false;};"
               "const fonts=document.fonts?document.fonts.ready:Promise.resolve();"
               "const load=document.readyState==='complete'?Promise.resolve():new Promise(r=>window.addEventListener('load',r,{once:true}));"
               "Promise.all([fonts,load]).then(()=>requestAnimationFrame(()=>requestAnimationFrame(go)));"
               "if(document.fonts)document.fonts.addEventListener('loadingdone',go);window.addEventListener('resize',go);})();</script>")


# tier1115: 흐름 쪽(.flow)은 한도에서 바로 나눠요. 기본 등급의 한 쪽짜리(.flow.lite)는 기존처럼 0.85까지 축소를 허용해요
FLOW_JS = "[...document.querySelectorAll('.page')].map(s=>s.classList.contains('flow')&&!s.classList.contains('lite'))"


async def render(src, out, fit=True):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None, args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 794, "height": 1123})
        await pg.goto("file://" + src); await pg.evaluate("document.fonts.ready"); await pg.wait_for_timeout(300)
        js = """[...document.querySelectorAll('.page')].map((s,i)=>{const r=s.getBoundingClientRect();let m=0;s.querySelectorAll('.in *').forEach(e=>{const q=e.getBoundingClientRect();if(q.height>0)m=Math.max(m,q.bottom-r.top)});return Math.round(m)})"""
        ov = await pg.evaluate(js)
        if fit:  # sync1114: 크게 넘친 쪽(축소하면 0.9 아래)은 블록·표 행 단위로 다음 쪽에 이어 붙여요
            # tier1115: 흐름 쪽(.flow)은 한도(LIMIT)에서 바로 나눠 축소 없이 꽉 채워요
            flow = await pg.evaluate(FLOW_JS)
            for _ in range(60):
                big = [i for i, h in enumerate(ov) if h > (LIMIT if flow[i] else SPLIT_AT)]
                if not big: break
                await pg.evaluate(SPLIT_JS, [big, LIMIT])
                ov = await pg.evaluate(js)
                flow = await pg.evaluate(FLOW_JS)
            if await pg.evaluate(TAIL_JS, [LIMIT]): ov = await pg.evaluate(js)
        for it in range(8):   # 남은 넘침은 비율만큼 축소(하한 ZOOM_MIN)
            bad = [(i, h) for i, h in enumerate(ov) if h > LIMIT]
            if not bad or not fit: break
            await pg.evaluate("""([bad,zmin])=>{const ps=[...document.querySelectorAll('.page')];bad.forEach(([i,h])=>{const el=ps[i].querySelector('.in');const z0=parseFloat(el.dataset.z||'1');const z=Math.max(zmin,Math.min(z0-0.02,z0*1040/h));el.dataset.z=z;el.style.zoom=z;});}""", [bad, ZOOM_MIN])
            ov = await pg.evaluate(js)
        render.zooms = await pg.evaluate("""[...document.querySelectorAll('.page')].map(s=>{const e=s.querySelector('.in');return e?parseFloat(e.dataset.z||'1'):1})""")
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
    ap.add_argument("--job", default="미정", choices=["직장인", "사업자", "사업가", "프리랜서", "주부", "학생", "무직", "미정"],
                    help="직업 상황 (기본 미정 = 직장·사업 모두 읽히는 중립 문장)")
    ap.add_argument("--time-rule", default="경도", choices=["경도", "30분"],
                    help="시주 시각 보정: 경도(기본, 출생지 경도로 지방평균태양시) / 30분(흔한 만세력 관례, 표준시 −30분)")
    ap.add_argument("--tier", choices=["free", "focus", "premium"], help="tier1115: 등급별 감정서 (free 기본 · focus 2,900원 주제 2개 · premium 9,900원 전체). 빼면 기존 종합 감정서")
    ap.add_argument("--topics", help="focus 주제 2개: 돈,직업,사업,결혼,이사,궁합,건강,자녀 (영문 money,job,biz,love,move,gunghap,health,kids도 돼요)")
    for k in ("name", "gender", "date", "time", "place"):
        ap.add_argument(f"--partner-{k}", help="궁합 상대 " + k)
    ap.add_argument("--partner-lunar", action="store_true"); ap.add_argument("--partner-leap", action="store_true")
    a = ap.parse_args()
    a.gender = {"f": "F", "m": "M", "여": "F", "남": "M"}.get(a.gender, a.gender)
    if a.job == "사업가": a.job = "사업자"
    if a.partner_gender: a.partner_gender = {"f": "F", "m": "M", "여": "F", "남": "M"}.get(a.partner_gender, a.partner_gender)
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
    print(json.dumps({"pdf": out, "pages": len(ov), "page_heights": ov, "tier": a.tier, "topics": getattr(rep, "tier_topics", None), "용신": c.yong, "희신": c.hee, "격국": c.gyeok,
                      "강약": c.st_label, "job": a.job, "years": {y: rep.ystar[y] for y in rep.years},
                      "sec_analysis": round(t1 - t0, 2), "sec_render": round(t2 - t1, 2), "sec_total": round(time.time() - t0, 2)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
