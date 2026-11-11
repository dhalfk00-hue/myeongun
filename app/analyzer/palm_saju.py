"""사주 × 손금 6대 선 통합 풀이 (재물운 우선).

손금(전통 수상학): 재운선(=태양선·재물선), 사업선, 운명선, 생명선, 두뇌선, 감정선 + 대박손금(재물 특수선)
사주: 재성·식상 분포, 신강/신약, 용신, 대운·세운의 십신
두 가지를 '나이'로 맞춘다 — 손금 유년법(운명선×두뇌선 ≈ 35~38세, ×감정선 ≈ 55세, 재운선 시작점) ↔ 대운 시작 나이.
외부 API 호출 없음, 순수 규칙 기반.
"""
from __future__ import annotations

from datetime import date

from .. import interpret as I

GROUP_OF = I.GROUP_OF
MONEY = ("재성", "식상")

# 대박손금(재물 특수선) 설명
BIG = {
    "삼지창": ("삼지창", "운명선 끝이 태양구(약지)·수성구(소지)로 갈라져 올라가요. 권력·재물·사업운을 두루 갖춘 최길상으로 봐요."),
    "럭키M": ("럭키M", "생명선·두뇌선·감정선과 운명선이 M자를 이뤄요. 노력이 재물로 바뀌는 행운의 손금이에요."),
    "川자상향선": ("川자 상향선", "운명선·재운선·사업선이 나란히 곧게 올라가요. 반드시 성공하는 손금으로 꼽혀요."),
    "재물3선": ("재물 3선", "운명선·재운선(태양선)·사업선이 모두 보여요. 수상학에서 '최고의 재물 손금'이라 부르는 조합이에요."),
    "긴태양선": ("긴 재운선", "재운선이 손바닥 아래쪽부터 약지까지 길게 올라가요. 재물과 명예가 오래 따르는 선이에요."),
    "금전운": ("재운선 여러 가닥", "약지 아래 재운선이 여러 가닥이에요. 수입원이 여러 개로 늘어나는 금전운 손이에요."),
    "긴사업선": ("긴 사업선", "사업선이 길고 뚜렷해요. 돈 버는 재능·언변·기민함을 갖춘 길상(반드시 성공하는 손금 20)이에요."),
    "귀인선": ("귀인선", "재운선이 손날 쪽(제2화성구)에서 올라와요. 고비마다 돈과 기회를 이어 주는 사람이 나타나요."),
}
BAND_AGE = {"early": (20, 35, "35세 이전부터"), "mid": (35, 55, "35~55세 무렵"), "late": (55, 70, "55세 무렵 이후(만년)")}
EL_KO = {"木": "목", "火": "화", "土": "토", "金": "금", "水": "수"}
EL_BODY = {"木": "간·담, 눈과 근육", "火": "심장·혈액순환", "土": "위장·소화", "金": "폐·호흡기, 피부", "水": "신장·방광, 허리"}
EL_LIFE = {"木": "아침 산책이나 스트레칭", "火": "햇볕 쬐기와 가벼운 유산소 운동", "土": "규칙적인 식사 시간",
           "金": "깊은 호흡과 맑은 공기", "水": "충분한 물과 잠"}
DM_NATURE = {"木": "곧게 뻗어 가는 나무처럼 성장 욕구가 큰", "火": "불처럼 밝고 표현력이 좋은", "土": "흙처럼 묵직하고 믿음직한",
             "金": "쇠처럼 원칙과 결단이 분명한", "水": "물처럼 유연하고 생각이 깊은"}


def _g(tg):
    return GROUP_OF.get(tg, "")


def _line(reading, name):
    for l in reading.get("lines", []):
        if l["name"] == name:
            return l
    return None


def _josa(w, pair="이가"):
    c = w[-1]
    if not ("가" <= c <= "힣"):
        return pair[0]
    return pair[0] if (ord(c) - 0xAC00) % 28 else pair[1]


def _daeun_at(daeun, age):
    cur = None
    for d in daeun:
        if d["시작나이(만)"] <= age:
            cur = d
    return cur


def _daeun_tag(d):
    a, b = _g(d["천간십신"]), _g(d["지지십신"])
    return a, b


def _palm_money(f, raw):
    """손금만으로 본 재물 신호. (점수, 문장들, 대박손금 배지, 재운선 나이대)"""
    sun, bz, fate = f.get("sun", {}), f.get("business", {}), f.get("fate", {})
    sp, bp, fp = sun.get("presence", "모름"), bz.get("presence", "모름"), fate.get("presence", "모름")
    score, out = 0.0, []
    if sp == "강함":
        score += 2; out.append("재운선(태양선)이 약지 쪽으로 뚜렷하게 올라가요. 재물과 명예가 따르는 손이에요.")
    elif sp == "보통":
        score += 1.3; out.append("재운선(태양선)이 보여요. 꾸준히 쌓으면 돈과 인정이 함께 따라오는 손이에요.")
    elif sp == "약함":
        score += 0.6; out.append("재운선이 가늘게 보여요. 돈이 모이는 속도는 느린 편이라 새는 돈부터 막으면 선이 진해진다고 봐요.")
    elif sp == "없음":
        out.append("재운선은 아직 뚜렷하지 않아요. 수상학에서는 재운선이 약하면 운명선·사업선 쪽 노력으로 재물을 채운다고 봐요.")
    st = sun.get("start", "모름")
    start_txt = {"운명선": "운명선에서 갈라져 나와, 하는 일(직장·본업)을 바탕으로 돈이 불어나는 흐름이에요.",
                 "손바닥아래": "손바닥 아래쪽에서 시작해 일찍부터 재물 복이 따르는 흐름이에요.",
                 "월구": "월구에서 올라와 대중의 인기·고객의 지지가 돈이 되는 흐름이에요.",
                 "제2화성구": "제2화성구에서 올라오는 귀인선이라, 도와주는 사람을 통해 돈이 들어와요.",
                 "두뇌선": "두뇌선에서 시작해 재능과 아이디어가 돈이 되는 손이에요.",
                 "화성평원": "손바닥 가운데(화성평원)에서 시작해 30대 이후 노력 끝에 재물이 붙는 흐름이에요.",
                 "감정선위": "감정선 위에서만 보여 50~55세 이후 만년에 복이 커지는 흐름이에요."}.get(st)
    if start_txt and sp not in ("없음", "모름"):
        out.append(start_txt)
    cnt = sun.get("count", "")
    if cnt == "2":
        out.append("재운선이 두 줄이라 본업과 부업 양쪽에서 수익이 날 수 있어요.")
    elif cnt == "여러":
        out.append("재운선이 여러 가닥이라 수입원이 여럿으로 늘어나는 손이에요.")
    if bp in ("강함", "보통"):
        score += 0.9 if bp == "강함" else 0.6
        out.append("사업선이 " + ("길고 뚜렷해 " if bp == "강함" else "보여서 ") + "장사·영업 수완으로 돈을 버는 힘이 있어요.")
        if bz.get("start") == "운명선":
            out.append("사업선이 운명선에서 시작해요. 수상학에서는 이를 '장사로 돈 버는 손'으로 봐요.")
    if fp in ("강함", "보통"):
        score += 0.4
    marks = [m for m in (f.get("money_marks") or []) if m in BIG]
    badges = [{"key": m, "label": BIG[m][0], "desc": BIG[m][1]} for m in dict.fromkeys(marks)]
    score += 0.7 * len(badges)
    band = f.get("sun_band") or ""
    return score, out, badges, band


def money_section(f, reading, r=None, today=None):
    today = today or date.today()
    pscore, palm, badges, band = _palm_money(f, None)
    sec = {"title": "재물운", "palm": palm, "badges": badges, "saju": [], "daeun": [], "seun": [], "peak": "", "advice": "",
           "has_saju": bool(r)}
    if not r:
        stars = max(2, min(5, round(2 + pscore * 0.8)))
        sec.update(stars=stars,
                   headline=(f"{badges[0]['label']}{_josa(badges[0]['label'])} 보이는 손이에요. " if badges else "") +
                   ("재운선이 살아 있어 돈복의 바탕이 있어요." if f.get("sun", {}).get("presence") in ("강함", "보통")
                    else "재운선보다는 일·사업선 쪽에서 돈을 만드는 손이에요."),
                   need_birth="생년월일을 넣으면 사주의 재성·식상과 대운·세운으로 '돈이 들어오는 시기'까지 맞춰 드려요.")
        return sec

    dm = r["day_master"]["element"]
    cnt = {k: 0 for k in I.GROUP_OFFSET}
    for k, v in r["ten_gods_count"].items():
        cnt[GROUP_OF[k]] += v
    strong = r["strength"]["support_ratio"] >= 0.5
    ys = I.yongsin(r)
    jae, sik = cnt["재성"], cnt["식상"]
    sscore = 0.0
    jae_el, sik_el = EL_KO[I.el_of_group(dm, "재성")], EL_KO[I.el_of_group(dm, "식상")]
    if jae >= 1:
        sec["saju"].append(f"사주 여덟 글자에 재성(돈·재물, {jae_el} 기운)이 {jae}개 있어요." +
                           (" 재물 그릇이 큰 사주예요." if jae >= 3 else " 돈을 다루는 감각을 타고났어요."))
        sscore += 1 if jae <= 3 else 0.6
    else:
        sec["saju"].append(f"사주 원국에 재성({jae_el} 기운)이 드러나 있지 않아요. 재물은 운(대운·세운)에서 재성이 들어올 때 크게 움직여요.")
    if sik >= 1:
        sec["saju"].append(f"식상(재능·일솜씨, {sik_el} 기운)이 {sik}개라, 재능을 돈으로 바꾸는 '식상생재' 힘이 있어요.")
        sscore += 0.5
    if strong and jae >= 1:
        sec["saju"].append("일간이 강한 신강 사주라 들어온 재물을 감당하고 지키는 힘이 좋아요.")
        sscore += 0.6
    elif strong:
        sec["saju"].append("일간이 강한 신강 사주라, 재성 운이 올 때 크게 벌 수 있는 체력이 있어요.")
        sscore += 0.3
    elif jae >= 3:
        sec["saju"].append("재성은 많은데 일간이 약한 편(재다신약)이라, 큰돈 욕심보다 꾸준한 저축·협업이 돈을 지켜요.")
    else:
        sec["saju"].append("일간이 약한 편이라 혼자보다 사람(동업·조직)과 함께할 때 재물이 커져요.")
    if ys["용신_십신"] in MONEY or ys["희신_십신"] in MONEY:
        which = ys["용신_십신"] if ys["용신_십신"] in MONEY else ys["희신_십신"]
        sec["saju"].append(f"사주의 균형을 맞춰 주는 기운(용신·희신)이 {which}이라, {which} 운이 오면 돈과 운이 함께 풀려요.")
        sscore += 0.5

    # 대운 타이밍
    by = int(r["solar_date"][:4])
    age = today.year - by - (1 if (today.month, today.day) < (int(r["solar_date"][5:7]), int(r["solar_date"][8:10])) else 0)
    b0, b1, blabel = BAND_AGE.get(band, (None, None, ""))
    rows = []
    for i, d in enumerate(r["daeun"]):
        a0 = d["시작나이(만)"]
        a1 = a0 + 9
        if a1 < age - 10 or a0 > age + 40:
            continue
        g1, g2 = _daeun_tag(d)
        hit = [x for x in (g1, g2) if x in MONEY]
        if not hit:
            continue
        why = []
        if "재성" in (g1, g2):
            why.append(f"{'천간' if g1 == '재성' else '지지'}에 재성({d['천간십신'] if g1 == '재성' else d['지지십신']})이 들어와 돈이 직접 움직이는 10년")
        if "식상" in (g1, g2):
            why.append("식상이 들어와 재능·일거리를 돈으로 바꾸는 10년")
        match = bool(b0 is not None and a0 < b1 and a1 >= b0)
        rows.append({"age": f"{a0}~{a1}세", "years": f"{d['시작연도(대략)']}~{d['시작연도(대략)'] + 9}년", "gz": d["ko"],
                     "tag": " · ".join(dict.fromkeys([t for t in (d["천간십신"], d["지지십신"]) if _g(t) in MONEY])),
                     "why": ", ".join(why), "palm_match": match, "now": a0 <= age <= a1, "past": a1 < age,
                     "level": 2 if "재성" in (g1, g2) else 1})
    sec["daeun"] = rows

    # 세운: 올해부터 10년 중 재성·식상 해
    seun = r.get("_seun10") or r["seun"]
    sy = []
    for s in seun:
        if s["년"] < today.year:
            continue
        g1, g2 = _g(s["천간십신"]), _g(s["지지십신"])
        if g1 not in MONEY and g2 not in MONEY:
            continue
        lv = (2 if g1 == "재성" else 0) + (2 if g2 == "재성" else 0) + (1 if g1 == "식상" else 0) + (1 if g2 == "식상" else 0)
        note = ("돈이 눈에 띄게 들어오는 해" if g1 == "재성" else "실속 있게 재물이 쌓이는 해" if g2 == "재성"
                else "일을 벌여 돈을 만드는 해")
        d = _daeun_at(r["daeun"], s["년"] - by)
        in_money_daeun = bool(d and (_g(d["천간십신"]) in MONEY or _g(d["지지십신"]) in MONEY))
        sy.append({"year": s["년"], "age": s["년"] - by, "gz": s["ko"], "tag": f"{s['천간십신']}·{s['지지십신']}", "note": note,
                   "level": lv + (1 if in_money_daeun else 0), "in_money_daeun": in_money_daeun})
    sec["seun"] = sy

    # 가장 좋은 시기 고르기: 손금 나이대와 겹치는 재성 대운 > 지금/다음 재성 대운
    fut = [x for x in rows if not x["past"]]
    best = next((x for x in fut if x["palm_match"] and x["level"] == 2), None) or \
        next((x for x in fut if x["level"] == 2), None) or (fut[0] if fut else None)
    top_years = sorted(sy, key=lambda s: (-s["level"], s["year"]))[:2]
    peak = []
    if best:
        peak.append(f"{best['age']}({best['years']}) {best['gz']} 대운" + (" — 지금 이 대운 안에 있어요." if best["now"] else "이 가장 기대되는 재물 시기예요."))
        if best["palm_match"]:
            peak.append(f"손금의 재운선 나이대({blabel})와 사주의 재물 대운이 겹쳐요. 이 시기가 돈이 들어오는 핵심 구간이에요.")
    if top_years:
        peak.append("가까운 해로는 " + ", ".join(f"{s['year']}년({s['age']}세, {s['note']})" for s in sorted(top_years, key=lambda s: s["year"])) + "을 눈여겨보세요.")
    sec["peak"] = " ".join(peak) if peak else "앞으로 10년 안에는 재성·식상이 크게 들어오는 해가 드물어요. 이런 시기엔 실력과 인맥을 쌓아 두는 것이 다음 재물운의 씨앗이에요."
    if blabel and not (best and best["palm_match"]):
        sec["palm_age"] = f"손금(재운선 시작점)이 가리키는 재물 나이대는 {blabel}예요."
    elif blabel:
        sec["palm_age"] = f"재운선 시작점 기준 재물 나이대: {blabel}"

    total = pscore + sscore
    sec["stars"] = max(2, min(5, round(1.6 + total * 0.6)))
    head = []
    if badges:
        head.append(f"{badges[0]['label']}{_josa(badges[0]['label'])} 있는 손")
    if f.get("sun", {}).get("presence") in ("강함", "보통"):
        head.append("재운선이 살아 있고")
    if jae >= 1:
        head.append(f"사주에 재성 {jae}개")
    elif sik >= 1:
        head.append(f"사주에 식상 {sik}개")
    sec["headline"] = (", ".join(head) + "." if head else "재물은 운에서 들어오는 타입이에요.") + \
        (f" 돈이 크게 움직이는 때는 {best['age']} {best['gz']} 대운이에요." if best else "")
    tips = []
    if ys["용신_십신"] == "재성" or ys["희신_십신"] == "재성":
        tips.append("재성 해에는 투자·이직·가격 인상 같은 '돈 결정'을 미루지 마세요.")
    if sik >= 1 or ys["용신_십신"] == "식상":
        tips.append("식상 해에는 새 일·부업·콘텐츠처럼 손으로 만드는 일을 벌이면 돈이 따라와요.")
    if not strong and jae >= 2:
        tips.append("신약이라 큰 베팅보다 분산·저축이 재물을 지켜요.")
    if f.get("sun", {}).get("presence") in ("약함", "없음"):
        tips.append("재운선은 생활 습관에 따라 진해지는 선이라, 고정 지출을 줄이고 꾸준히 모으면 손에도 운이 드러난다고 봐요.")
    sec["advice"] = " ".join(tips[:3])
    return sec


def combined_sections(f, reading, r=None, today=None):
    """재물운 다음에 이어지는 5개 풀이 (사업·운명 / 건강(생명선) / 생각(두뇌선) / 마음(감정선))."""
    today = today or date.today()
    out = []
    by = int(r["solar_date"][:4]) if r else None
    cnt = {k: 0 for k in I.GROUP_OFFSET}
    if r:
        for k, v in r["ten_gods_count"].items():
            cnt[GROUP_OF[k]] += v

    def palm_txt(name):
        l = _line(reading, name)
        return (l["observed"] + " — " + l["meaning"]) if l else ""

    # 1) 일·사업운: 사업선 + 운명선 + 관성/대운
    s = {"key": "work", "title": "일·사업운", "lines": ["사업선", "운명선"], "palm": [], "saju": [], "timing": []}
    for nm in ("사업선", "운명선"):
        t = palm_txt(nm)
        if t:
            s["palm"].append(f"{nm}: {t}")
    if r:
        gw, gb = cnt["관성"], cnt["식상"] + cnt["재성"]
        if gw >= 2 and gw >= gb:
            s["saju"].append(f"관성(직장·명예)이 {gw}개로 강해, 조직 안에서 자리를 높여 가는 '직장형' 사주예요.")
        elif gb >= 3:
            s["saju"].append(f"식상·재성이 합쳐 {gb}개라, 내 이름으로 일을 벌이는 '사업형' 기질이 강해요.")
        elif gw == 0:
            s["saju"].append("원국에 관성이 없어 남 밑보다 프리랜서·전문직처럼 자율이 큰 일이 맞아요.")
        else:
            s["saju"].append(f"관성 {gw}개, 식상·재성 {gb}개로 직장과 사업 어느 쪽도 가능한 균형형이에요.")
        fate = f.get("fate", {})
        if fate.get("presence") in ("강함", "보통") and fate.get("end") in ("토성구", "감정선에서멈춤"):
            d = _daeun_at(r["daeun"], 36)
            if d:
                s["timing"].append(f"운명선이 두뇌선을 지나는 35~38세는 사주로 {d['ko']} 대운({d['천간십신']}·{d['지지십신']})이에요. "
                                   + ("관성이 들어와 승진·직함이 생기는 흐름과 맞아요." if "관성" in _daeun_tag(d)
                                      else "재성·식상이 들어와 일이 돈으로 연결되는 흐름이에요." if set(_daeun_tag(d)) & set(MONEY)
                                      else "인성·비겁 운이라 자격·실력을 쌓는 시기로 봐요."))
        if fate.get("end") == "토성구":
            d = _daeun_at(r["daeun"], 55)
            if d:
                s["timing"].append(f"운명선이 감정선을 넘는 55세 무렵은 {d['ko']} 대운이에요. 운명선이 끝까지 올라가 노년까지 일이 이어지는 손이에요.")
        for d in r["daeun"]:
            a0 = d["시작나이(만)"]
            if a0 + 9 < today.year - by or a0 > today.year - by + 30:
                continue
            if "관성" in _daeun_tag(d):
                s["timing"].append(f"{a0}~{a0 + 9}세 {d['ko']} 대운에 관성이 들어와 직장운·명예운이 커져요.")
                break
    out.append(s)

    # 2) 건강·생활력: 생명선 + 오행
    s = {"key": "health", "title": "건강·생활력", "lines": ["생명선"], "palm": [], "saju": [], "timing": []}
    t = palm_txt("생명선")
    if t:
        s["palm"].append(f"생명선: {t}")
    if r:
        el = r["five_elements_count"]
        lo = min(el, key=lambda k: el[k]); hi = max(el, key=lambda k: el[k])
        s["saju"].append(f"오행은 {EL_KO[hi]}({hi}) {el[hi]}개로 가장 많고 {EL_KO[lo]}({lo}) {el[lo]}개로 가장 적어요. "
                         f"전통 오행론에선 {EL_KO[lo]} 기운이 맡는 {EL_BODY[lo]} 쪽을 평소에 아껴 쓰라고 봐요. {EL_LIFE[lo]}{_josa(EL_LIFE[lo])} 도움이 돼요.")
        lf = f.get("life", {})
        if lf.get("arc") == "큼" or lf.get("clarity") == "강함":
            s["saju"].append("생명선이 힘 있게 크게 돌아 오행의 부족한 부분을 체력으로 받쳐 주는 손이에요.")
        elif lf.get("clarity") in ("약함",) or lf.get("arc") == "작음":
            s["saju"].append("생명선이 차분한 편이라, 사주의 약한 오행을 생활 습관으로 채워 주면 좋아요.")
        d = _daeun_at(r["daeun"], 45)
        if d:
            s["timing"].append(f"생명선 가운데(40대 무렵)는 사주로 {d['ko']} 대운에 해당해요. 이 시기엔 무리한 일정보다 회복 시간을 챙기세요.")
    s["note"] = "건강 풀이는 전통 해석일 뿐 의학적 진단이 아니에요."
    out.append(s)

    # 3) 생각·재능: 두뇌선 + 일간
    s = {"key": "mind", "title": "생각·재능", "lines": ["두뇌선"], "palm": [], "saju": [], "timing": []}
    t = palm_txt("두뇌선")
    if t:
        s["palm"].append(f"두뇌선: {t}")
    hd = f.get("head", {})
    if hd.get("double"):
        s["title"] = "생각·재능 · 이중 두뇌선"
        s["saju"].append("이중 두뇌선(기억력·멀티태스킹·어학)" + (f"에 사주의 식상 {cnt['식상']}개가 더해져, 머릿속 아이디어를 말·글·일로 풀어내는 힘이 커요." if r and cnt["식상"] >= 1
                         else f"에 사주의 인성 {cnt['인성']}개가 더해져, 배운 것을 오래 기억하고 깊이 쓰는 머리예요." if r and cnt["인성"] >= 1 else "이라 두 가지 일을 함께 끌고 가는 힘이 있어요."))
    if r:
        dm = r["day_master"]["element"]
        s["saju"].append(f"일간은 {r['day_master']['ko']}{EL_KO[dm]}({r['day_master']['stem']}), {DM_NATURE[dm]} 기질이에요."
                         + (f" 인성(공부·자격)이 {cnt['인성']}개라 배운 것을 깊이 소화하는 머리예요." if cnt["인성"] >= 2 else "")
                         + (f" 식상이 {cnt['식상']}개라 말·글·기획으로 표현하는 재능이 있어요." if cnt["식상"] >= 2 else ""))
    out.append(s)

    # 4) 감정·관계: 감정선 + 비겁/관성
    s = {"key": "heart", "title": "마음·관계", "lines": ["감정선"], "palm": [], "saju": [], "timing": []}
    t = palm_txt("감정선") or palm_txt("막쥔손금")
    if t:
        s["palm"].append(f"감정선: {t}")
    hand = f.get("hand", "")
    if hand in ("오른손", "왼손"):
        s["note"] = (f"수상학에서는 오른손 감정선을 겉으로 드러나는 감정, 왼손 감정선을 속마음으로 봐요. 지금은 {hand} 기준이라 "
                     + ("겉으로 드러나는 감정" if hand == "오른손" else "속마음") + " 풀이예요. 반대 손도 찍으면 겉과 속을 비교해 드려요.")
    if r:
        if cnt["비겁"] >= 3:
            s["saju"].append(f"비겁(나·동료)이 {cnt['비겁']}개로 많아 자존심과 독립심이 강해요. 감정 표현을 한 박자 부드럽게 하면 관계운이 살아요.")
        elif cnt["인성"] >= 2:
            s["saju"].append("인성이 넉넉해 마음이 따뜻하고 배려가 깊어요.")
        else:
            s["saju"].append("사주가 한쪽으로 크게 치우치지 않아 사람을 두루 사귀는 편이에요.")
        # 배우자궁(일지) + 배우자 별(남: 재성, 여: 관성)
        dp = next((p for p in r.get("pillars", []) if p.get("name") == "일"), None)
        if dp:
            g = GROUP_OF.get(dp.get("branch_tengod"), "")
            SP = {"비겁": "친구처럼 편하고 대등한 동반자", "식상": "표현이 많고 다정하게 챙겨 주는 인연", "재성": "현실적이고 살림을 함께 꾸리는 인연",
                  "관성": "책임감 있고 반듯한 인연", "인성": "나를 이해하고 돌봐 주는 인연"}
            if g:
                s["saju"].append(f"배우자 자리(일지) {dp['gz'][1]}에 {dp['branch_tengod']}이 앉아 있어 {SP[g]}과 잘 맞아요.")
        fem = str((r.get("input") or {}).get("gender", "")) in ("여", "F")
        star = "관성" if fem else "재성"; n = cnt[star]
        s["saju"].append(f"{'여성은 관성' if fem else '남성은 재성'}을 배우자 별로 보는데, 원국에 {n}개라 "
                         + ("인연을 스스로 고르고 늦게 확신하는 편이에요. 서두르지 않는 게 좋아요." if n == 0
                            else "인연이 또렷하게 들어오는 편이에요." if n <= 2 else "인연이 많은 편이라 고르는 눈이 중요해요."))
        if r.get("seun"):
            for sy in r["seun"][:3]:
                tg = {GROUP_OF.get(sy.get("천간십신")), GROUP_OF.get(sy.get("지지십신"))}
                if star in tg:
                    s["timing"].append(f"{sy['년']}년 {sy['ko']}년은 배우자 별({star})이 들어오는 해라 인연·관계에 변화가 생기기 쉬워요.")
                    break
    out.append(s)
    return out


def advice(f, r, years, money=None):
    """올해·내년 조언: 사주 세운(해의 기운) + 손금 특징을 규칙으로 합침. years = saju_summary의 years 카드 2개."""
    f = f or {}
    pres = lambda k: (f.get(k) or {}).get("presence")
    sun_ok = pres("sun") in ("강함", "보통"); biz_ok = pres("business") in ("강함", "보통"); fate_ok = pres("fate") in ("강함", "보통")
    heart = f.get("heart") or {}; life = f.get("life") or {}
    seun = {s["년"]: s for s in (r or {}).get("seun", [])}
    TIP = {
        "재성": ("사주로 재물의 기운이 들어오는 해예요. " + ("재운선도 보이니 들어온 돈을 저축·자산으로 묶어 두면 오래 남아요." if sun_ok
                 else "재운선이 아직 옅으니 큰 투자보다 고정 수입을 늘리는 쪽이 맞아요."),
                "재물 기운이 이어지는 해라 지난해 모은 돈의 굴릴 곳을 정하기 좋아요. 다만 한 곳에 몰지 말고 나눠 두세요."),
        "식상": ("표현·기획의 기운이 강한 해라 " + ("사업선이 뚜렷한 손과 맞물려 부업·내 일을 시작하기 좋아요." if biz_ok
                 else "아이디어를 글·말·콘텐츠로 꺼내 두면 기회로 이어져요."),
                 "재주가 밖으로 드러나는 해예요. 만들어 둔 것을 알리고 값을 매기는 데 힘을 쓰세요."),
        "관성": ("직장·명예의 기운이 들어와 " + ("운명선이 받쳐 주니 승진·이직 제안을 적극적으로 검토해 보세요." if fate_ok
                 else "책임 있는 자리를 맡되 무리한 약속은 줄이세요."),
                 "자리와 책임이 무거워지는 해예요. 맡은 일의 마감과 규칙을 지키는 것이 곧 평판이 돼요."),
        "인성": ("공부·자격의 기운이 있는 해라 자격증·배움에 쓴 시간이 다음 해의 돈이 돼요.",
                 "도와주는 사람·문서 운이 이어지는 해예요. 계약서·서류는 꼼꼼히 읽고, 윗사람 조언을 흘려듣지 마세요."),
        "비겁": ("사람·경쟁의 기운이 강한 해라 동업·보증·돈 거래는 조심하고, 내 몫을 분명히 하세요.",
                 "경쟁이 이어지는 해예요. 남과 비교하기보다 내 속도로 실력을 쌓는 쪽이 이기는 길이에요."),
    }
    used = set(); out = []
    for i, y in enumerate(years or []):
        yr = y.get("year"); sy = seun.get(yr) or {}
        gs = [g for g in (GROUP_OF.get(sy.get("천간십신")), GROUP_OF.get(sy.get("지지십신"))) if g]
        tips = []
        for g in dict.fromkeys(gs):
            tips.append(TIP[g][1] if g in used else TIP[g][0]); used.add(g)
        if not tips:
            tips.append("큰 기운의 변화가 적은 해라 지금 하는 일을 꾸준히 다지는 것이 가장 좋아요.")
        if i == 0 and life.get("clarity") == "약함":
            tips.append("생명선이 차분한 편이니 바쁜 달일수록 휴식부터 챙기세요.")
        elif i == 0 and life.get("clarity") in ("강함", "보통"):
            tips.append("생명선이 뚜렷해 체력이 받쳐 주니, 미뤄 둔 일을 올해 시작해도 좋아요.")
        if i == 1 and heart.get("clarity") in ("강함", "보통"):
            tips.append("감정선이 뚜렷해 관계 운이 받쳐 줘요. 중요한 사람과의 약속을 미루지 마세요.")
        out.append({"year": yr, "gz": y.get("gz"), "title": y.get("title"), "star": y.get("star"), "saju": y.get("line"), "months": y.get("months"),
                    "tips": tips[:3], "label": "올해" if i == 0 else "내년"})
    return out


def pairs(r, today=None):
    """6대 선마다 함께 보는 사주 요소(무료 요약 칩). 규칙 기반·짧은 글자만."""
    if not r:
        return {}
    today = today or date.today()
    cnt = {k: 0 for k in I.GROUP_OFFSET}
    for k, v in r["ten_gods_count"].items():
        cnt[GROUP_OF[k]] += v
    age = today.year - int(r["solar_date"][:4])
    d = _daeun_at(r["daeun"], age)
    dz = f"지금 {d['ko']} 대운({'·'.join(x for x in _daeun_tag(d) if x)})" if d else "대운"
    el = r["five_elements_count"]; lo = min(el, key=lambda k: el[k]); hi = max(el, key=lambda k: el[k])
    dm = r["day_master"]
    dp = next((p for p in r.get("pillars", []) if p.get("name") == "일"), None)
    fem = str((r.get("input") or {}).get("gender", "")) in ("여", "F")
    return {
        "sun": [f"재성(재물) {cnt['재성']}개", f"식상(돈 버는 재주) {cnt['식상']}개", dz],
        "business": [f"관성(직장·명예) {cnt['관성']}개", f"식상(내 일·표현) {cnt['식상']}개", dz],
        "fate": [dz, f"관성 {cnt['관성']}개"],
        "life": [f"오행 많음 {EL_KO[hi]}({hi}) {el[hi]}", f"오행 적음 {EL_KO[lo]}({lo}) {el[lo]}"],
        "head": [f"일간 {dm['ko']}{EL_KO[dm['element']]}({dm['stem']})", f"인성(공부) {cnt['인성']}개", f"식상(표현) {cnt['식상']}개"],
        "heart": ([f"배우자 자리 {dp['gz'][1]} · {dp['branch_tengod']}"] if dp else []) + [f"배우자 별 {'관성' if fem else '재성'} {cnt['관성' if fem else '재성']}개", f"비겁(자존심) {cnt['비겁']}개"],
    }


def build(f, reading, r=None, today=None):
    return {"money": money_section(f, reading, r, today), "sections": combined_sections(f, reading, r, today)}


# ---------------------------------------------------------------- 양손 비교 (전통 방식, 남좌여우·성별 구분 없음)
# 전통 수상학 근거: 감정선 = 오른손은 겉으로 드러나는 감정, 왼손은 속마음. 양손이 많이 다르면 이중적인 면 [221743707852]
#                      태양선(재운선) = 오른손잡이 기준(주로 쓰는 손)으로 본다.
# 그 밖의 선은 양손 해석 규칙이 자료에 없으므로 '차이 관찰'만 보여 준다 (규칙을 지어내지 않음).
HEART_KEYS = ("shape", "end", "start_height", "clarity", "form")
CMP_LINES = (("생명선", "life", ("clarity", "length", "arc", "head_join")),
             ("두뇌선", "head", ("clarity", "length", "direction", "start")),
             ("운명선", "fate", ("presence", "start", "end")),
             ("사업선", "business", ("presence", "start")))


def _known(v):
    return v not in (None, "", "모름") and v != []


def compare_hands(main_f, main_reading, other_f, other_reading, main_hand, other_hand):
    """main = 주로 쓰는 손(재물운·현재 풀이에 쓰는 손), other = 반대 손."""
    by_hand = {main_hand: (main_f, main_reading), other_hand: (other_f, other_reading)}
    out = {"title": "양손 비교", "badge": "양손 비교", "heart": {}, "sun": "", "others": [], "notes": []}
    # 1) 감정선: 오른손 = 겉, 왼손 = 속
    rf, rr = by_hand.get("오른손", (None, None))
    lf, lr = by_hand.get("왼손", (None, None))
    if rf is not None and lf is not None:
        def heart_txt(rd):
            l = _line(rd, "감정선") or _line(rd, "막쥔손금")
            return (l["observed"] + " — " + l["meaning"]) if l else "감정선을 또렷하게 찾지 못했어요."
        diff = [k for k in HEART_KEYS if _known(rf["heart"].get(k)) and _known(lf["heart"].get(k)) and rf["heart"][k] != lf["heart"][k]]
        simian_diff = rf.get("simian", "없음") != lf.get("simian", "없음")
        big = len(diff) >= 2 or simian_diff
        out["heart"] = {
            "outer": "오른손 감정선 · 겉으로 드러나는 감정: " + heart_txt(rr),
            "inner": "왼손 감정선 · 속마음: " + heart_txt(lr),
            "diff_keys": diff, "dual": big,
            "verdict": ("양손 감정선이 많이 달라요. 수상학에서는 이럴 때 이중적인 면이 있다고 봐요. 겉으로 보이는 모습과 속마음이 다를 수 있어서, "
                        "가까운 사람에게 속마음을 말로 꺼내 주면 오해가 줄어요." if big else
                        "양손 감정선이 비슷해요. 겉으로 보이는 감정과 속마음이 크게 다르지 않은, 솔직한 편이에요." if diff or any(_known(rf["heart"].get(k)) for k in HEART_KEYS)
                        else "감정선 특징이 충분히 잡히지 않아 겉과 속을 비교하기 어려워요."),
        }
    # 2) 재운선: 주로 쓰는 손 기준
    ms, os_ = main_f["sun"].get("presence", "모름"), other_f["sun"].get("presence", "모름")
    out["sun"] = (f"재물운(재운선)은 전통 수상학 기준으로 주로 쓰는 손({main_hand}) 기준으로 풀었어요. "
                  f"반대 손({other_hand}) 재운선은 '{os_ if _known(os_) else '확인 어려움'}'으로 참고만 해요.")
    # 3) 나머지 선: 차이만 관찰
    for nm, key, keys in CMP_LINES:
        a, b = main_f.get(key, {}), other_f.get(key, {})
        la, lb_ = _line(main_reading, nm), _line(other_reading, nm)
        diff = [k for k in keys if _known(a.get(k)) and _known(b.get(k)) and a[k] != b[k]]
        same = [k for k in keys if _known(a.get(k)) and _known(b.get(k)) and a[k] == b[k]]
        out["others"].append({"name": nm, "main": la["observed"] if la else "확인 어려움", "other": lb_["observed"] if lb_ else "확인 어려움",
                              "status": "다름" if diff else "비슷" if same else "비교 어려움"})
    out["notes"].append("전통 수상학에서 양손을 나눠 보는 규칙은 감정선(오른손=겉, 왼손=속)과 재운선(주로 쓰는 손 기준) 두 가지예요. "
                        "다른 선은 양손 해석 규칙이 없어서, 뜻을 덧붙이지 않고 두 손의 차이만 보여 드려요.")
    out["notes"].append("남좌여우(남자 왼손·여자 오른손)처럼 성별로 손을 나누지 않아요.")
    return out
