# -*- coding: utf-8 -*-
"""tier1115: 등급별 감정서 조립.

  free    (기본 · 무료)   표지(핵심 3) · 명식 · 성격 · 용신 한눈에 · 올해(또는 내년) 운세 · 더 보기 안내      ≈ 3쪽
  focus   (2,900원)      기본 전부 + 고른 주제 2개 심층 + 개운법                                     ≈ 8~10쪽
  premium (9,900원)      표지(핵심 5) · 명식 · 용신·격국 · 성격 · 대운 · 주제 7개 심층(+상대 정보가 있으면 궁합)
                          · 올해·내년 월별 · 개운법                                                     ≈ 20쪽
- 표지·명식 쪽은 고정 쪽, 나머지는 하나의 '흐름'(.flow)으로 이어 붙여 렌더 때 한도에서 나눠요(빈 쪽 없음, 축소 없음).
- 세 등급 모두 같은 Chart·같은 별점을 써요. 등급이 올라가면 깊이만 늘어나요.
"""
import re
from datetime import datetime
import engine as E
import build as B
import jobs as JB
import advice as AV
import topics as TP
from texts import *
from josa import josa, particle

PRICE = {"free": 0, "focus": 2900, "premium": 9900, "newyear": 4900}
PRODUCT = {"free": None, "focus": "focus_2900", "premium": "premium_9900", "newyear": "newyear_4900"}
PREMIUM_ORDER = ("money", "job", "biz", "love", "move", "health", "kids")
_HEAD = re.compile(r'^\s*<section class="page[^"]*"><div class="in">\s*', re.S)
_TAIL = re.compile(r'\s*</div><div class="foot">[^<]*</div></section>\s*$', re.S)
RULE = '<div class="rule"></div>'


def inner(page):
    return _TAIL.sub("", _HEAD.sub("", page))


def flow(parts, cls="flow"):
    body = ("\n" + RULE + "\n").join(p.strip() for p in parts if p and p.strip())
    body = re.sub(r'(<div class="rule"></div>\s*)+(?=<!--T:)', "", body)           # 주제 섹션은 스스로 구분선을 가져요
    body = re.sub(r'^\s*(<!--T:\w+-->)?\s*<div class="rule"></div>', r"\1", body)  # 맨 앞 구분선은 빼요
    return f'<section class="page {cls} tight"><div class="in">\n{body}\n</div><div class="foot">SONMYEONGRI · __PG__</div></section>'


def focus_year(rep):
    """10~12월에는 다음 해를 '올해 운세'로 봐요(앱 화면의 연도 규칙과 같아요)."""
    return rep.Y + 1 if rep.now.month >= 10 else rep.Y


def free_core(rep, tier):
    c = rep.c; y = focus_year(rep); gz = E.year_gz(y)
    st, bt = c.tg(gz[0]), c.tg(gz[1], True)
    import persona as PS, natal as NT
    fs_, fb_ = c.fav[E.STEM_ELK[gz[0]]], c.fav[E.BR_ELK[gz[1]]]
    stY = rep.ystar[y]; dom = fb_ if abs(fb_) >= abs(fs_) else fs_
    # verdict1116: 별이 판정을 정해요 — ★2 이하·안 맞는 기운이면 좋은 말 테마 문장은 빼고, 관계 문구도 별 방향에 맞춰 2개까지
    summ = (f"천간 {josa(PS.ST_KO[gz[0]], '은')} {st}({TG_THEME[st][0]})로 이 사주엔 {NT.ROLE[fs_]}, 지지 {josa(PS.BR_KO[gz[1]], '은')} {bt}({TG_THEME[bt][0]})로 {josa(NT.ROLE[fb_], '이에요')}."
            + (" " + TG_THEME[bt if abs(fb_) >= abs(fs_) else st][1].split(". ")[0].rstrip(".") + "." if dom >= 0 and stY >= 3 else ""))
    free = tier == "free"
    ev = rep._ev_pick(rep.year_events(gz), stY)
    if stY >= 4: ev = [(t_, B._no_but(d_)) for t_, d_ in ev]   # release1116
    lis = "".join(f"<li><b>{t}</b>: {d}</li>" for t, d in ev[:2]) or "<li>원국과 크게 부딪히거나 묶이는 글자가 없어 흐름이 순한 해예요.</li>"
    advs = rep.yadv(y, "gen", 2)
    if stY >= 4: advs = [x for x in advs if x[0] != "조심"] or advs[:1]   # release1116: 좋은 해의 조심은 결론줄 한 번만
    steps, concl = rep.yongsin_parts()
    Y_, H_ = ELEM[c.yong], ELEM[c.hee]
    gaeun = f"{Y_['colors'].split('·')[0]}·{H_['colors'].split('·')[0]} 계열, {Y_['dir']}, 숫자 {Y_['nums']}"
    left = f'<p class="small"><b>남은 {rep.Y}년</b> · {rep.tips_short()}</p>' if (y != rep.Y and not free) else ""
    parts = []
    if free:   # 기본: 한 쪽 안에 성격·용신·올해를 담아요
        ps = re.findall(r"<p>.*?</p>", rep.persona_html(), flags=re.S)[:3]
        parts.append(f'''<h2><span class="no">{rep.nxt()}</span>타고난 성격 · 용신</h2>
 <div class="sub">일간 → 월지 → 강한 십신 · {c.st_label} · 격국 {c.gyeok}</div>
 {"".join(ps)}
 <div class="box dark small"><span class="gold">용신</span> · {concl}<br><span class="gold">생활 속 개운</span> · {gaeun}</div>''')
    else:
        parts.append(f'''<h2><span class="no">{rep.nxt()}</span>타고난 성격</h2>
 <div class="sub">일간 → 월지 → 강한 십신 순서로 읽었어요</div>
 {rep.persona_html()}''')
        parts.append(f'''<h2><span class="no">{rep.nxt()}</span>용신 한눈에 · 나를 살리는 기운</h2>
 <div class="sub">{c.st_label} · 격국 {c.gyeok}</div>
 <ol class="small" style="padding-left:5mm;margin-top:0">{"".join(f"<li>{s_}</li>" for s_ in steps)}</ol>
 <div class="box dark"><span class="gold">결론</span> · {concl}<br><span class="gold">생활 속 개운</span> · {gaeun}</div>''')
    parts.append(f'''<h2><span class="no">{rep.nxt()}</span>{y} {B.ko(gz)}({gz})년: {rep.year_title(y)}</h2>
 <div class="sub">만 {c.age(y)}세 · 세운 {st}/{bt} · 운세 {B.stars(rep.ystar[y])}</div>
 {rep.verdict_line(y)}
 <div class="box dark"><span class="gold">한 줄 요약</span> · {summ}</div>
 <ul class="small">{lis}</ul>
 <div class="advbox small"><b class="gold">{y}년 {"할 일" if stY >= 4 else "할 일 · 조심 · 보완"}</b><ul>{AV.fmt(advs)}</ul></div>
 <p class="small"><b>{y}년 안의 달별 차이</b> · {rep.best_months_phrase(y, 1)}</p>
 {left}''')
    if free: parts.append(more_box())
    return parts


def more_box():
    return ('<div class="box small"><b class="gold">더 깊게 보고 싶다면</b> · <b>주제 심층 2,900원</b>: 돈·직업·사업·결혼·이사·궁합·건강·자녀 중 2개를 골라 '
            '타고난 바탕, 10년 단위 흐름, 해마다 조심·보완, 좋은 해와 조심할 해까지(약 8~10쪽). <b>프리미엄 9,900원</b>: 모든 주제 심층과 대운 전체, 올해·내년 월별 운세(약 20쪽). '
            '주제 심층을 산 같은 사주는 차액 7,000원만 내요. 세 등급 모두 같은 계산·같은 별점이라 결론이 엇갈리지 않아요.</div>')


def gunghap_section(rep, args, now):
    """상대 정보로 궁합 심층 (남녀 두 사람 기준)"""
    import make_gunghap as MG
    c = rep.c
    pg_ = args.partner_gender
    if pg_ not in ("F", "M"): raise ValueError("궁합은 상대의 성별이 필요해요")
    if pg_ == c.gender: raise ValueError("궁합은 지금은 남녀 두 사람 기준의 전통 이론으로만 볼 수 있어요. 상대의 성별을 확인해 주세요")
    if not args.partner_date: raise ValueError("궁합은 상대의 생년월일이 필요해요")
    rule = getattr(args, "time_rule", None) or "경도"
    me_place = "127.5" if rule == "30분" else args.place
    me = MG.Person("고객님", args.name, c.gender, args.date, args.lunar, args.leap, args.time, me_place, rep.inp.get("place_label"), now)
    pp = getattr(args, "partner_place", None) or "서울"
    try:
        import places_kr as PK  # 앱과 같은 지명 해석이 있으면 써요
        pp = str(PK.resolve(pp)[0]) if hasattr(PK, "resolve") else pp
    except Exception:
        pass
    other = MG.Person("상대방", getattr(args, "partner_name", None), pg_, args.partner_date, bool(getattr(args, "partner_lunar", False)),
                      bool(getattr(args, "partner_leap", False)), getattr(args, "partner_time", None), pp, getattr(args, "partner_place_label", None) or getattr(args, "partner_place", None) or "서울", now)
    F, M = (me, other) if c.gender == "F" else (other, me)
    G = MG.Gunghap(F, M, now, "")
    G.time_note_short = ""
    no = lambda h: re.sub(r'<span class="no">\d+</span>', lambda m_: f'<span class="no">{rep.nxt()}</span>', h)
    sc = inner(G.p_score())
    sc = re.sub(r'<p class="tiny" style="margin-top:1.4mm">채점 방법:.*?</p>', "", sc, flags=re.S)
    parts = [no(sc), no(inner(G.p_palace())), no(inner(G.p_life())), no(inner(G.p_timing()))]
    caut = "".join(x[2] for x in G.cautions())
    parts.append(f'<h3>두 사람이 함께 지킬 해</h3><ul class="small">{caut or "<li>향후 10년 안에 두 사람이 함께 크게 흔들리는 해는 없어요.</li>"}</ul>')
    body = ("\n" + RULE + "\n").join(parts)
    return f"<!--T:gunghap--><div class=\"rule\"></div>\n{body}<!--/T-->", G


def assemble_tier(args, now):
    import make_report as MR
    tier = args.tier
    if tier == "newyear":   # newyear1116: 2027 신년운세는 따로 조립해요
        import newyear as NY
        return NY.assemble(args, now)
    if tier not in PRICE: raise ValueError("등급은 free·focus·premium 중 하나예요")
    topics = TP.parse_topics(getattr(args, "topics", None) or "")
    if tier == "focus":
        if len(topics) != 2: raise ValueError("주제 심층(2,900원)은 주제를 정확히 2개 골라요")
    elif tier == "premium":
        topics = list(PREMIUM_ORDER) + (["gunghap"] if getattr(args, "partner_date", None) else [])
    else:
        topics = []
    if "gunghap" in topics and not getattr(args, "partner_date", None):
        raise ValueError("궁합을 고르면 상대의 생년월일·성별이 필요해요")
    c, rep, inp = MR.prepare(args, now)
    T = TP.Topics(rep)
    pages = []
    if tier == "premium":
        cover = rep.cover(None).replace("사주 종합 감정서", "사주 프리미엄 감정서")
    else:
        cover = rep.cover(None)
        keep = [0, 3, 4] if tier == "free" else [0, 1, 2, 3, 4]
        ks = re.findall(r'<div class="k"><div class="n">\d+</div>.*?</div></div>', cover, flags=re.S)
        if tier == "free" and len(ks) == 5:
            new = "".join(re.sub(r'<div class="n">\d+</div>', f'<div class="n">{i + 1}</div>', ks[k]) for i, k in enumerate(keep))
            cover = cover.replace("".join(ks), new).replace("한눈에 보는 핵심 5가지", "한눈에 보는 핵심 3가지")
        cover = cover.replace("사주 종합 감정서", "사주 기본 감정서" if tier == "free" else "사주 주제 심층 감정서 · " + "·".join(TP.KO[t] for t in topics))
    pages.append(cover)
    pages.append(rep.p_chart())
    css_extra = ""
    G = None
    if tier in ("free", "focus"):
        fl = free_core(rep, tier)
        for t in topics:
            if t == "gunghap":
                sec, G = gunghap_section(rep, args, now)
                fl.append(sec)
            else:
                fl.append(T.section(t))
        if tier == "focus":
            fl.append(inner(rep.p_end(False)))
        pages.append(flow(fl, "flow lite" if tier == "free" else "flow"))
    else:
        import gloss as GL   # gloss1116: 명식 다음 '사주 용어 쉽게 보기'(흐름 맨 앞 약 1쪽)
        fl = [inner(rep.p_yongsin()), GL.guide_block(c, GL.guide_extra(c, rep.Y)), inner(rep.p_persona()), inner(rep.p_daeun()) + "\n" + T.daeun_matrix(topics)]
        for t in topics:
            if t == "gunghap":
                sec, G = gunghap_section(rep, args, now)
                fl.append(sec)
            else:
                fl.append(T.section(t, compact=True))
        fl += [inner(p) for p in rep.p_years()]
        fl.append(inner(rep.p_end(False)))
        pages.append(flow(fl))
    if G is not None:
        import make_gunghap as MG
        css_extra = MG.CSS_EXTRA
    html = "\n".join(pages)
    for k in ("__PALM_KEY2__", "__PALM_HEALTH__", "__PALM_CLOSING__", "__PALM_LIMIT__"):
        html = html.replace(k, "")
    html = html.replace("<li>__PALM_TIMING__</li>", "<li>좋은 해에 큰 계획을, 지키는 해에 준비를</li>").replace("__PALM_TIMING__", "")
    title = {"free": "손명리 사주 기본 감정서", "focus": "손명리 사주 주제 심층 감정서", "premium": "손명리 사주 프리미엄 감정서"}[tier]
    doc = MR.finish(html, title)
    if css_extra:
        doc = doc.replace('<link rel="stylesheet" href="style.css">', '<link rel="stylesheet" href="style.css"><style>' + css_extra + "</style>")
    rep.tier = tier; rep.tier_topics = topics
    return doc, {}, rep, c
