# -*- coding: utf-8 -*-
"""newyear1116: 2027 신년운세 감정서(4,900원 · 12~14쪽).
표지 → 2027 총운(사주 결론 + 토정 총운 · 전통 참고) → 열두 달 달력(주제별 별점 + 한 줄) → 8개 주제의 2027년 → 마무리.
- 판정은 사주 별점이 정해요. 토정비결은 '전통 참고'로만 쓰고, 별과 어긋나면 별 쪽을 따른다고 밝혀요.
- 10년 흐름·대운은 한 줄 요약만."""
import re
import engine as E
import build as B
import advice as AV
import topics as TP
import tojeong as TJ
from texts import *
from josa import josa, particle

YEAR = 2027
ORDER = ("money", "job", "biz", "love", "move", "gunghap", "health", "kids")
NAME = {"money": "돈·재물", "job": "직업·일", "biz": "사업·장사", "love": "결혼·애정", "move": "이사·이동", "gunghap": "궁합", "health": "건강", "kids": "자녀"}
MONTH_T = ("money", "job", "biz", "love", "move", "health", "kids")
TONE = {"g": ("좋음", "#dfe9dc"), "n": ("보통", "#efe9dc"), "b": ("조심", "#f3dcd6")}


def tojeong_of(args, y=YEAR):
    return TJ.reading(args.date, bool(args.lunar), bool(getattr(args, "leap", False)), y)


def months_of(y):
    """정미년 열두 달: 입춘(寅月)~다음 해 소한 달(丑月). i번째 달 ≈ 음력 i월(전통 대응)"""
    ms = [m for m in E.month_pillars(y, y + 1) if (m[0].year == y and m[3] != "小寒") or (m[0].year == y + 1 and m[3] == "小寒")]
    return ms[:12]


def topic_year(T, t, y):
    sc, st = T.ystars(t)
    return sc[y], st[y]


def cover(rep, tj, y, best, low):
    c = rep.c; gz = E.year_gz(y); st = rep.ystar[y]
    tj_t = f'괘 {tj["sang"]}·{tj["jung"]}·{tj["ha"]} 「{tj["title"]}」' if tj["ready"] else f'괘 {tj["sang"]}·{tj["jung"]}·{tj["ha"]}'
    ks = [(f"{y}년 사주 운세 {B.stars(st)}", f"{rep.VY[st]}예요. 할 일·조심할 일·이사·계약 판정은 다음 쪽 첫 줄에 모았어요."),
          ("힘을 실을 주제", "·".join(NAME[t] for t in best) + " 쪽이 이 해에 상대적으로 나아요."),
          ("먼저 챙길 주제", "·".join(NAME[t] for t in low) + " 쪽은 서두르지 말고 지키는 쪽으로 가세요."),
          ("토정비결 · 전통 참고", f"{tj_t}. 판단은 사주 별점이 정하고, 토정 풀이는 옛 풍속으로 곁들여 읽어요.")]
    kh = "".join(f'<div class="k"><div class="n">{i + 1}</div><div class="t"><b>{a}</b>{b}</div></div>' for i, (a, b) in enumerate(ks))
    base = rep.cover(None)
    base = re.sub(r'<div class="key5">.*?</div>\n</div><div class="foot">', f'<div class="key5">{kh}</div>\n</div><div class="foot">', base, flags=re.S)
    base = base.replace("한눈에 보는 핵심 5가지", f"{y}년 한눈에 보기").replace("사주 종합 감정서", f"{y} {B.ko(gz)}년 신년운세").replace("SONMYEONGRI · SAJU", f"SONMYEONGRI · NEW YEAR {y}")
    return base


def chongun(rep, tj, y):
    import tiers as TR
    c = rep.c; gz = E.year_gz(y); st = rep.ystar[y]
    s_, b_ = c.tg(gz[0]), c.tg(gz[1], True)
    import persona as PS, natal as NT
    fs_, fb_ = c.fav[E.STEM_ELK[gz[0]]], c.fav[E.BR_ELK[gz[1]]]
    dom = fb_ if abs(fb_) >= abs(fs_) else fs_
    summ = (f"천간 {josa(PS.ST_KO[gz[0]], '은')} {s_}({TG_THEME[s_][0]})로 이 사주엔 {NT.ROLE[fs_]}, 지지 {josa(PS.BR_KO[gz[1]], '은')} {b_}({TG_THEME[b_][0]})로 {josa(NT.ROLE[fb_], '이에요')}."
            + (" " + TG_THEME[b_ if abs(fb_) >= abs(fs_) else s_][1].split(". ")[0].rstrip(".") + "." if dom >= 0 and st >= 3 else ""))
    ev = rep._ev_pick(rep.year_events(gz), st)
    if st >= 4: ev = [(t_, B._no_but(d_)) for t_, d_ in ev]
    lis = "".join(f"<li><b>{t}</b>: {d}</li>" for t, d in ev[:2]) or "<li>원국과 크게 부딪히거나 묶이는 글자가 없어 흐름이 순한 해예요.</li>"
    advs = rep.yadv(y, "gen", 2)
    if st >= 4: advs = [x for x in advs if x[0] != "조심"] or advs[:1]
    rep.__dict__.setdefault("_ny_txt", set()).update(z for x in advs for z in (re.sub(r"\s+", "", q) for q in re.split(r"(?<=[.!?])\s+", re.sub(r"<[^>]+>", " ", str(x[1])))) if len(z) > 15)
    dae = c.current_daeun(y)
    dline = (f"<b>10년 흐름 한 줄</b> · 지금은 {dae['gz']} 대운 안에 있고, " + rep.year_line(y).rstrip(".") + "." ) if dae else ""
    parts = [f'''<h2><span class="no">{rep.nxt()}</span>{y} {B.ko(gz)}({gz})년 총운: {rep.year_title(y)}</h2>
 <div class="sub">만 {c.age(y)}세 · 세운 {s_}/{b_} · 운세 {B.stars(st)}</div>
 {rep.verdict_line(y)}
 <div class="box dark"><span class="gold">사주로 본 한 해</span> · {summ}</div>
 <ul class="small">{lis}</ul>
 <div class="advbox small"><b class="gold">{y}년 {"할 일" if st >= 4 else "할 일 · 조심 · 보완"}</b><ul>{AV.fmt(advs)}</ul></div>
 <p class="small">{dline}</p>''']
    parts.append(tojeong_block(tj, y, st))
    return parts


def tojeong_block(tj, y, st):
    if not tj["ready"]:
        body = '<p class="small">이 괘의 현대어 풀이는 준비 중이에요.</p>'
        grid = ""
    else:
        fl = tj["flow"]
        conflict = (fl == "좋음" and st <= 2) or (fl == "조심" and st >= 4)
        cn = f' <b>사주 별점({B.stars(st)})과 결이 달라요 — 판단은 별점을 따르고, 토정 풀이는 전통 참고로만 읽어 주세요.</b>' if conflict else ""
        body = f'<p class="small"><b>「{tj["title"]}」</b> · 토정 총흐름 {fl} · {tj["chongun"]}{cn}</p>'
        cells = "".join(f'<td style="background:{TONE[m["tone"]][1]};text-align:center" class="tiny">{m["m"]}월<br>{TONE[m["tone"]][0]}</td>' for m in tj["months"])
        grid = f'<table class="tiny"><tr>{cells}</tr></table><p class="tiny">음력 달 기준 · 달별 한 줄은 다음 달력에 같이 적었어요.</p>'
    return f'''<h3>토정비결 · 전통 참고 · 괘 {tj["sang"]}·{tj["jung"]}·{tj["ha"]}</h3>
 <div class="sub">음력 생일 {tj["lunar_birth"][:4]}년 {int(tj["lunar_birth"][5:7])}월 {int(tj["lunar_birth"][8:])}일{"(윤달은 평달로)" if tj["leap_birth"] else ""} · {tj["basis"]}{" · 작은달이라 29일로 셈" if tj["clamped"] else ""}</div>
 {body}{grid}
 <p class="tiny">{TJ.NOTE} {TJ.SOURCE}</p>'''


def calendar(rep, T, tj, y):
    c = rep.c; rows = ""
    for i, (a, b, gz, n) in enumerate(months_of(y)):
        sc = c.score(gz)[0]; stn = rep.star(sc)
        tsc = {t: T.tscore(t, gz) for t in MONTH_T}
        tst = {t: max(1, min(5, c.stars(v))) for t, v in tsc.items()}
        best = max(MONTH_T, key=lambda t: tsc[t]); worst = min(MONTH_T, key=lambda t: tsc[t])
        ak, at = AV.short_advice(c, gz, sc, "month")
        line = rep.month_point(gz)
        if stn == 5: line = "<b>좋은 달.</b> " + line
        line += AV.fmt_inline(ak, at)
        mo = f"{a.month}월에는"
        if stn >= 4: line += f" {mo} {NAME[best]} 쪽에 힘을 쓰세요."
        elif stn <= 2: line += f" {mo} {NAME[worst]} 쪽에서 특히 무리하지 마세요."
        else: line += f" {mo} {NAME[best]} 쪽을 챙기고, {NAME[worst]} 쪽은 서두르지 마세요."
        tline = "·".join(f"{TP.KO[t]}{tst[t]}" for t in MONTH_T)
        tjc = ""
        if tj["ready"]:
            m = tj["months"][i]
            off = (m["tone"] == "g" and stn <= 2) or (m["tone"] == "b" and stn >= 4)
            tjc = f'<span class="tiny"><b>음력 {m["m"]}월</b> {m["text"]}{" (별점과 달라요 · 별점 기준)" if off else ""}</span>'
        end = b - E.timedelta(days=1)
        per = f"{a.month}/{a.day}~{end.month}/{end.day}<br>({a.year}년)" if a.year != y else f"{a.month}/{a.day}~{end.month}/{end.day}"
        rows += (f'<tr{" class=hl" if stn >= 4 else ""}><td class="small"><b>{per}</b><br><span class="serif">{gz}</span></td>'
                 f'<td class="small">{line}<br><span class="tiny">주제별 ★ {tline}</span></td><td>{tjc}</td><td class="stars">{B.stars(stn)}</td></tr>')
    return f'''<h2><span class="no">{rep.nxt()}</span>열두 달 달력 · {y}년</h2>
 <div class="sub">절기(입춘·경칩…)로 나눈 달 · 별점은 사주 기준, 오른쪽 토정 한 줄은 전통 참고(음력 달)</div>
 <div class="box small cal-guide"><b>달력 읽는 법</b> · <b>기간</b> 절기로 나눈 한 달(양력 날짜)과 그 달의 간지 · <b>사주 · 이달 한 줄</b> 그 달에 할 일(추천)과 조심할 일, 아래 작은 줄은 주제별 별점 · <b>토정</b> 음력 그 달의 전통 풀이(참고만, 별점과 다르면 별점을 따르세요) · <b>운세</b> 그 달 종합 별점, 별이 많을수록 좋은 달이고 ★4 이상인 달은 칸을 색칠했어요.</div>
 <table><tr><th style="width:13%">기간</th><th>사주 · 이달 한 줄</th><th style="width:27%">토정 · 전통 참고</th><th style="width:11%">운세</th></tr>{rows}</table>
 <p class="tiny">※ 주제별 별: 돈·직업·사업·결혼(애정)·이사·건강·자녀를 ★1~★5로 적었어요. 모든 주제가 높을수록 좋아요(건강도 높을수록 탈이 적어요). 다음 해 1월(소한~입춘 전)까지가 {y}년의 기운이에요.</p>'''


SUB = {"money": "재성·식상·비겁의 구조로 보는 돈 그릇 · 돈만 따로 본 별점이라 종합 별점과 다를 수 있어요",
       "job": "격국·관성·인성·식상 · 일하는 방식과 자리", "biz": "재성·식상·비겁·강약으로 보는 장사 체질",
       "love": "배우자궁(일지)·배우자 별 · 결혼 시기는 점치지 않아요", "move": "충·역마로 보는 이동수 · 용신 방향 · 그해 피할 방향",
       "health": "오행의 강약과 충 · 전통 배속에 따른 관리 포인트이며 의학적 진단이 아니에요",
       "kids": "자녀의 별과 자녀궁(시주) · 자녀가 있는지 모르는 채로 썼어요. 자녀가 없다면 아끼는 아랫사람과의 인연으로 읽으세요"}


def quarters(rep, T, y):
    """계절(석 달)마다: 별 흐름 · 힘 쓸 달 · 아낄 달 · 할 일 한 가지 — 별이 판정을 정해요"""
    c = rep.c; ms = months_of(y); rows = ""
    for qi, (nm, sl) in enumerate((("봄", ms[0:3]), ("여름", ms[3:6]), ("가을", ms[6:9]), ("겨울", ms[9:12]))):
        sts = [(m, rep.star(c.score(m[2])[0])) for m in sl]
        hi = max(sts, key=lambda x: (x[1], -sts.index(x))); lo = min(sts, key=lambda x: (x[1], sts.index(x)))
        avg = sum(x[1] for x in sts) / 3
        ml = lambda m: f"{m[0].month}월({m[2]})"
        bt = {t: sum(T.tscore(t, m[2]) for m in sl) for t in MONTH_T}
        bt_ = max(MONTH_T, key=lambda t: bt[t]); wt_ = min(MONTH_T, key=lambda t: bt[t])
        if avg >= 3.5:
            act = f"<b class=\"adv-g\">할 일</b> {ml(hi[0])}에 {NAME[bt_]} 쪽 계획을 실행하세요. <b class=\"adv-c\">조심</b> {ml(lo[0])}에는 속도를 한 번 늦추세요."
        elif avg <= 2.5:
            act = f"<b class=\"adv-s\">보완</b> 이 석 달은 새로 벌이기보다 {NAME[wt_]} 쪽을 먼저 지키세요. 그나마 나은 {ml(hi[0])}에 밀린 일을 정리하세요."
        else:
            act = f"<b class=\"adv-g\">할 일</b> {ml(hi[0])}에 {NAME[bt_]} 쪽을 챙기세요. <b class=\"adv-c\">조심</b> {ml(lo[0])}에는 {NAME[wt_]} 쪽을 서두르지 마세요."
        stl = " · ".join(f"{m[0].month}월 ★{v} {'좋음' if v >= 4 else '조심' if v <= 2 else '보통'}" for m, v in sts)   # qa1116: 별 개수 대신 ★숫자 + 말
        rows += f'<tr><td><b>{nm}</b><br><span class="tiny">{sl[0][0].month}~{(sl[-1][1] - E.timedelta(days=1)).month}월</span></td><td class="small">{stl}</td><td class="small">{act}</td></tr>'
    return f'''<h3>{y}년 석 달씩 정리</h3>
 <table><tr><th style="width:12%">계절</th><th style="width:30%">달별 별</th><th>할 일 · 조심 · 보완</th></tr>{rows}</table>'''


def topic_months(T, t, y):
    c = T.c; cells = ""
    for i, (a, b, gz, n) in enumerate(months_of(y)):
        v = max(1, min(5, c.stars(T.tscore(t, gz))))
        bg = "#dfe9dc" if v >= 4 else "#f3dcd6" if v <= 2 else "#efe9dc"
        cells += f'<td class="tiny" style="background:{bg};text-align:center;white-space:nowrap">{a.month}월<br>★{v} {"좋음" if v >= 4 else "조심" if v <= 2 else "보통"}</td>'
    return f'<table class="tiny"><tr>{cells}</tr></table>'


def topic_block(rep, T, t, y, args):
    c = rep.c; gz = E.year_gz(y)
    if t == "gunghap":
        lsc, lst = topic_year(T, "love", y)
        if getattr(args, "partner_date", None):
            return f'<h3>{NAME[t]}</h3><p class="small">상대 정보로 본 두 사람의 궁합은 별도 궁합 풀이에서 자세히 다뤄요. {y}년 내 쪽 애정 흐름은 {B.stars(lst)}이에요.</p>'
        return (f'<h3>{NAME[t]} · 상대 입력 필요</h3><p class="small">궁합은 상대의 생년월일을 넣어야 두 사람을 함께 볼 수 있어요. '
                f'지금은 내 쪽 {y}년 애정 흐름({B.stars(lst)})만 결혼·애정 쪽에 적었어요. 앱에서 상대 정보를 넣으면 따로 볼 수 있어요.</p>')
    orig = None
    if t == "biz":
        import jobs as JB
        orig = JB.CUR["job"]; JB.apply("사업자")
    try:
        sc, st = topic_year(T, t, y)
        used = rep.__dict__.setdefault("_ny_txt", set())
        sp_ = lambda h_: {z for z in (re.sub(r"\s+", "", q) for q in re.split(r"(?<=[.!?])\s+", re.sub(r"<[^>]+>", " ", h_))) if len(z) > 15}
        for i_ in range(6):   # 직업·사업은 같은 갈래 조언을 쓰니 앞 주제와 겹치는 문장이면 다른 문장을 골라요
            k, x = T.adv(t, gz, sc, f"ny{y}" + (f"r{i_}" if i_ else ""), year=y, star=st, age=c.age(y))
            if not (sp_(x) & used): break
        used.update(sp_(x))
        hint = T.month_hint(t, y, 0, st)
        hint = re.sub(r"이 해 안에서도 (\S+?)(?:은|는) 특히 무리하지 마세요\.", lambda m_: f"{TP.KO[t]} 일은 {m_.group(1)}에 특히 무리하지 마세요.", hint)
        sig = T.signal(t, gz)
        natal, one = T.natal(t)
        chk = T.checklist(t, [y] if st >= 4 else [], [y] if st <= 2 else [])
    finally:
        if orig is not None: JB.apply(orig)
    chk = (chk.replace("★4 이상인 해가 없으니 ", f"{y}년은 {B.stars(st)}라 ").replace("'해도 됨'인 해가 없으니 ", f"{y}년은 '해도 됨'이 아니니 ")
           .replace("년처럼 관계 온도가 높은 해에는", "년에는").replace("년처럼 흐름이 좋은 해에", "년 안에"))
    natal = re.sub(r"<h3>.*?</h3>", "", natal, flags=re.S)
    seen = rep.__dict__.setdefault("_ny_seen", set())
    def _dd(m_):
        k_ = re.sub(r"\s+", "", m_.group(0))
        if k_ in seen: return ""
        seen.add(k_); return m_.group(0)
    natal = re.sub(r"[^.<>]{20,}?\.(?=\s|<)", _dd, natal)
    natal = re.sub(r"\s*(?<=[.>])[^.<>]*10년 안[^.<>]*\.", "", natal)   # 10년 흐름은 총운 쪽 한 줄로만
    note = ""
    if t == "kids": note = '<p class="tiny">아래 관계 풀이는 자녀가 있다면 해당해요. 자녀 유무·나이·계획은 사주로 단정하지 않아요.</p>'
    if t == "love": note = '<p class="tiny">배우자가 있다면 부부 관계로, 없다면 가까운 관계의 성향으로 읽으세요. 결혼 여부나 시기를 단정하지 않아요.</p>'
    title = "배우자 · 가족 관계" if t == "love" and c.age(y) >= 60 else NAME[t]
    one = re.sub(r"([가-힣])\.\.(?!\.)", r"\1.", one)   # 이어 붙인 문장 끝의 마침표 겹침 정리(주제 섹션과 같은 규칙)
    return f"""<!--T:{t}--><div class="rule"></div>
 <h2><span class="no">{rep.nxt()}</span>{y}년 {title} <span class="stars">{B.stars(st)}</span></h2>
 <div class="sub">{SUB[t]}</div>
 <div class="box dark small"><span class="gold">{y}년 판정</span> · {k} {x}</div>
 <p class="small"><b>달별로 보면</b> · {hint}</p>
 {topic_months(T, t, y)}
 <p class="tiny">{y}년 {TP.KO[t]} 신호 · {sig}</p>
 <p class="small"><b>타고난 바탕 한 줄</b> · {one}</p>{note}
 <h3>타고난 바탕 · 자세히</h3>{natal}
 <h3>{y}년 실천 체크</h3><ul class="small">{chk}</ul><!--/T-->"""


def assemble(args, now):
    import make_report as MR, tiers as TR
    c, rep, inp = MR.prepare(args, now)
    y = YEAR
    if y not in rep.ystar: raise ValueError("신년운세는 2027년만 볼 수 있어요")
    tj = tojeong_of(args, y)
    if not tj["ready"] and not getattr(args, "allow_missing_gwae", False):
        raise ValueError(f"토정 괘 {tj['code']} 풀이가 아직 준비되지 않았어요")
    import gloss as GL   # qa1116: 프리미엄과 같은 '사주 용어 쉽게 보기'를 신년운세에도
    T = TP.Topics(rep)
    tys = {t: topic_year(T, t, y) for t in MONTH_T}
    order = sorted(MONTH_T, key=lambda t: -tys[t][0])
    best = [t for t in order[:2] if tys[t][1] >= 3] or order[:1]
    low = [t for t in order[::-1][:2] if t not in best]
    pages = [cover(rep, tj, y, best, low), rep.p_chart(), GL.guide_page(rep.c, GL.guide_extra(rep.c, y))]   # qa1116: 명식 다음 '사주 용어 쉽게 보기' 한 쪽
    fl = chongun(rep, tj, y)
    fl.append(calendar(rep, T, tj, y) + "\n" + quarters(rep, T, y))
    fl.append(f'<h3>{y}년 주제별 운세 · 8가지</h3><p class="small">별점이 판정을 정해요 · ★4~5 할 일 중심 · ★3 균형 · ★1~2 보완 중심. 주제 별점은 그 주제만 따로 본 값이라 종합 별점과 다를 수 있어요.</p>')
    fl += [topic_block(rep, T, t, y, args) for t in ORDER]
    end = TR.inner(rep.p_end(False))
    end = re.sub(r'<h3>시기별 행동 조언</h3><ul class="small">.*?</ul>', "", end, flags=re.S)
    fl.append(end)
    pages.append(TR.flow(fl))
    html = "\n".join(pages)
    for k_ in ("__PALM_KEY2__", "__PALM_HEALTH__", "__PALM_CLOSING__", "__PALM_LIMIT__", "__PALM_TIMING__"):
        html = html.replace(k_, "")
    doc = MR.finish(html, f"손명리 {y} 신년운세 감정서")
    rep.tier = "newyear"; rep.tier_topics = list(ORDER); rep.tojeong = tj
    return doc, {}, rep, c


# ------------------------------------------------------------------ 앱 무료 화면(토정 + 사주 요약 + 8칸 맛보기)
def _plain(h): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h or "")).strip()


def free_data(args, now):
    """앱 무료 화면용 값(글은 html 조각 · 앱에서 풀이·조사 맞춤). 판정은 사주 별점, 토정은 전통 참고."""
    import make_report as MR
    c, rep, inp = MR.prepare(args, now)
    y = YEAR; gz = E.year_gz(y); st = rep.ystar[y]
    tj = tojeong_of(args, y)
    T = TP.Topics(rep)
    mst = T.ystars("move")[1][y]; cst = T.ystars("money")[1][y]
    vv = lambda s_: "해도 됨" if s_ >= 4 else "신중" if s_ == 3 else "미룸"
    cells = []; seen_tz = set()
    for t in ORDER:
        if t == "gunghap":
            cells.append({"key": t, "ko": NAME[t], "star": None, "partner": True, "teaser": "상대의 생년월일을 넣으면 두 사람의 2027년을 함께 봐요."}); continue
        sc, s_ = topic_year(T, t, y)
        k, x = T.adv(t, gz, sc, f"ny{y}", year=y, star=s_, age=c.age(y))
        first = re.split(r"(?<=[.!?])\s", _plain(x))[0]
        first = re.sub(r"^(추천|조심|보완)\s+", "", first)
        m_ = re.match(r"^(.*?해)라,\s*(.*)$", first)
        head, act = (m_.group(1) + "예요.", m_.group(2)) if m_ else (first, "")
        head = re.sub(r"^[^,.]*?(?:와서|들어와|겹쳐서|겹쳐)\s+", "", head)   # 이유(십신) 앞부분은 감정서에서 · 맛보기는 결과만
        tz = head if head not in seen_tz or not act else act
        seen_tz.add(tz)
        tz = tz if len(tz) <= 46 else tz[:44].rstrip(" ,·") + "…"
        cells.append({"key": t, "ko": NAME[t], "star": s_, "verdict": AV.VERD[s_], "teaser": tz})
    tjo = {"code": tj["code"], "sang": tj["sang"], "jung": tj["jung"], "ha": tj["ha"], "ready": tj["ready"], "basis": tj["basis"],
           "lunar_birth": tj["lunar_birth"], "leap_birth": tj["leap_birth"], "note": TJ.NOTE, "source": TJ.SOURCE,
           "upper": TJ.UPPER[tj["sang"]]}
    if tj["ready"]:
        fl = tj["flow"]
        tjo.update(title=tj["title"], flow=fl, line=re.split(r"(?<=요\.)\s", tj["chongun"])[0],
                   months=[{"m": m["m"], "tone": m["tone"]} for m in tj["months"]],
                   conflict=(fl == "좋음" and st <= 2) or (fl == "조심" and st >= 4))
    dae = c.current_daeun(y)
    return {"year": y, "gz": gz, "ko": B.ko(gz), "age": c.age(y), "star": st, "verdict": rep.VY[st], "title": rep.year_title(y),
            "line": rep.year_line(y), "move": vv(mst), "contract": vv(cst), "daeun": (dae["gz"] if dae else None),
            "yong": c.yong, "hee": c.hee, "dm": c.dm, "strength": c.st_label, "tojeong": tjo, "topics": cells, "report_ready": bool(tj["ready"])}
