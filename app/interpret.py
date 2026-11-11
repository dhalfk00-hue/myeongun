# -*- coding: utf-8 -*-
"""규칙 기반 사주 해석 엔진 (유료 LLM 없음).
전통 명리 해석을 정리한 오락·자기이해용 텍스트를 생성한다."""
import argparse
from datetime import date, datetime, timedelta
from functools import lru_cache

from lunar_python import Solar

from . import saju_engine as S

EL = S.ELEMENTS  # 木火土金水
EK = S.EL_KO
GROUP_OF = {"비견": "비겁", "겁재": "비겁", "식신": "식상", "상관": "식상", "편재": "재성", "정재": "재성",
            "편관": "관성", "정관": "관성", "편인": "인성", "정인": "인성"}
GROUP_OFFSET = {"비겁": 0, "식상": 1, "재성": 2, "관성": 3, "인성": 4}
PALACE = {"년": "집안·윗사람", "월": "직장·사회 환경", "일": "배우자·건강·생활 기반", "시": "자녀·아랫사람·일의 결과"}

DM = {
    "甲": ("큰 나무", "곧고 리더십이 있으며 한번 정하면 밀고 나가는 추진력이 있어요", "고집이 세 보일 수 있으니 굽힐 때를 아는 게 좋아요"),
    "乙": ("화초·덩굴", "유연하고 적응력이 뛰어나며 생활력이 강하고 섬세해요", "남 눈치를 많이 보다 지칠 수 있어요"),
    "丙": ("태양", "밝고 솔직하며 공명정대하고 표현력이 뛰어나요", "성급하게 결론을 내리는 버릇을 조심하세요"),
    "丁": ("촛불·등불", "따뜻하고 집중력이 좋으며 한 사람·한 일에 헌신하는 타입이에요", "예민함이 쌓이면 속으로 끓는 편이에요"),
    "戊": ("큰 산", "듬직하고 포용력이 있으며 신용을 중시해요", "변화에 무겁게 반응해 기회를 놓칠 수 있어요"),
    "己": ("논밭·정원", "실속 있고 배려심이 깊으며 관리 능력이 좋아요", "걱정과 의심이 많아질 때가 있어요"),
    "庚": ("원석·바위", "결단력과 의리가 있고 강직해요", "말과 행동이 거칠게 비칠 수 있어요"),
    "辛": ("보석·칼날", "섬세하고 깔끔하며 자존심과 자기 기준이 분명해요", "완벽주의 때문에 스스로를 피곤하게 만들 수 있어요"),
    "壬": ("바다·큰 강", "포부가 크고 지혜로우며 자유로운 사고를 해요", "한곳에 머무르지 못하고 흩어질 수 있어요"),
    "癸": ("비·이슬", "총명하고 감수성이 풍부하며 인내심이 있어요", "속마음을 감춰 오해를 사기 쉬워요"),
}
GROUP_TRAIT = {
    "비겁": "자존심·독립심·승부욕이 강해 내 방식대로 해야 직성이 풀리는 타입",
    "식상": "재치와 표현력이 좋고 아이디어가 많아 말·글·기술로 존재감을 드러내는 타입",
    "재성": "현실 감각과 활동력이 좋아 돈과 사람을 굴리는 데 능한 타입",
    "관성": "책임감과 원칙이 강해 조직과 명예를 중시하는 타입",
    "인성": "생각이 깊고 배움을 좋아하며 문서·자격·후원 운이 있는 타입",
}
STAGE_TXT = {"장생": "새로 시작하는 힘이 좋고 사람들에게 귀여움을 받아요", "목욕": "감성적이고 멋을 알지만 마음이 자주 흔들려요",
             "관대": "자신감과 혈기가 넘쳐요", "건록": "자립심과 실무 능력이 탄탄해요", "제왕": "주도권을 쥐려는 힘이 강해요",
             "쇠": "노련하고 안정적이에요", "병": "배려심과 감성이 깊어요", "사": "정신적·연구적인 집중력이 있어요",
             "묘": "모으고 지키는 힘과 고집이 있어요", "절": "끊고 새로 시작하는 결단이 빠르고 변화가 많아요",
             "태": "계획과 구상이 많아요", "양": "보호받고 키워지는 복이 있어요"}
TG_KEY = {"비견": "독립·동료·경쟁", "겁재": "승부·경쟁·지출", "식신": "표현·생산·여유", "상관": "아이디어·말·변화",
          "편재": "큰돈·사업 기회·활동", "정재": "안정 수입·실속", "편관": "압박·책임·도전", "정관": "명예·직책·계약",
          "편인": "직관·공부·기술", "정인": "문서·후원·자격"}
EL_INFO = {
    "木": {"color": "초록·청색", "dir": "동쪽", "num": "3·8", "act": "새 기획 세우기, 공부·독서, 산책과 숲, 사람 키우기",
           "job": "교육·출판·기획·디자인·인테리어·유아/환경 분야", "organ": "간·담, 근육·관절, 눈"},
    "火": {"color": "빨강·주황", "dir": "남쪽", "num": "2·7", "act": "햇빛 보는 운동, 발표·홍보, 사람 만나기",
           "job": "방송·미디어·마케팅·IT·조명/에너지·예술 분야", "organ": "심장·소장, 혈압·혈액순환"},
    "土": {"color": "노랑·베이지", "dir": "중앙(사는 곳 근처)", "num": "5·10", "act": "규칙적인 생활, 신용 쌓기, 부동산·자산 정리",
           "job": "부동산·건설·중개·컨설팅·농식품·유통 관리 분야", "organ": "위장·소화기, 피부"},
    "金": {"color": "흰색·금색·은색", "dir": "서쪽", "num": "4·9", "act": "정리정돈, 원칙 세우기, 근력 운동",
           "job": "기계·금속·설비·금융·법무·군경·의료기기 분야", "organ": "폐·대장, 호흡기·피부, 뼈"},
    "水": {"color": "검정·남색", "dir": "북쪽", "num": "1·6", "act": "말·글로 표현하기, 콘텐츠 만들기, 물가 산책, 충분한 수면",
           "job": "무역·물류·유통·콘텐츠·연구·여행·서비스 분야", "organ": "신장·방광, 생식·비뇨기"},
}
STAR = lambda n: "★" * n + "☆" * (5 - n)


def _last_hangul(w):
    import re
    w = re.sub(r"\([^)]*\)", "", w)
    for ch in reversed(w):
        if "가" <= ch <= "힣":
            return ch
    return None


def J(w, kind):
    """한국어 조사: J('목(木)','으로') -> '목(木)으로'"""
    ch = _last_hangul(w)
    jong = (ord(ch) - 0xAC00) % 28 if ch else 0
    pairs = {"이": ("이", "가"), "은": ("은", "는"), "을": ("을", "를"), "과": ("과", "와"), "이라": ("이라", "라"), "이에요": ("이에요", "예요")}
    if kind == "으로":
        return w + ("로" if jong in (0, 8) else "으로")
    a, b = pairs[kind]
    return w + (a if jong else b)


def el_of_group(dm_el, group):
    return EL[(EL.index(dm_el) + GROUP_OFFSET[group]) % 5]


def group_of_el(dm_el, el):
    k = (EL.index(el) - EL.index(dm_el)) % 5
    return [g for g, o in GROUP_OFFSET.items() if o == k][0]


def calc(date_str, lunar=False, leap=False, time=None, gender="M", place="서울", seun_from=None, seun_to=None):
    y = date.today().year
    a = argparse.Namespace(date=date_str, time=time, lunar=lunar, leap=leap, gender=gender, place=place,
                           tz=None, utc_offset=None, zi="unified", eot=False, _nosc=False,
                           seun_from=seun_from or y - 1, seun_to=seun_to or y + 1)
    return S.compute_wrap(a)


# ------------------------------------------------------------ 용신
def yongsin(r):
    dm_el = r["day_master"]["element"]
    w = r["five_elements_weighted_with_hidden"]
    ratio = r["strength"]["support_ratio"]
    g = {grp: w[el_of_group(dm_el, grp)] for grp in GROUP_OFFSET}
    score = {grp: 0.0 for grp in GROUP_OFFSET}
    strong = ratio >= 0.5
    if strong:
        if g["인성"] > g["비겁"]:
            yong, hee, reason = "재성", "식상", "인성(나를 돕는 기운)이 지나쳐 재성으로 눌러 주는 게 균형"
            score.update({"재성": 2, "식상": 1, "관성": 0.3, "비겁": -1, "인성": -2})
        else:
            yong, hee, reason = "식상", "재성", "비겁(나와 같은 기운)이 강해 식상으로 힘을 흘려보내는 게 균형"
            score.update({"식상": 2, "재성": 1, "관성": 0.5, "인성": -1.5, "비겁": -1})
    else:
        drain = max(("식상", "재성", "관성"), key=lambda k: g[k])
        if drain == "재성":
            yong, hee, reason = "비겁", "인성", "재성이 많아 몸이 약하니 비겁으로 버티는 게 균형"
            score.update({"비겁": 2, "인성": 1, "재성": -1.5, "관성": -1, "식상": -0.5})
        else:
            yong, hee = "인성", "비겁"
            reason = ("관성의 압박을 인성이 풀어 주는(살인상생) 구조" if drain == "관성"
                      else "식상으로 기운이 많이 새어 인성으로 채워 주는 게 균형")
            score.update({"인성": 2, "비겁": 1, drain: -1.5})
            for k in ("식상", "재성", "관성"):
                if k != drain: score[k] = -0.7
    el_score = {el_of_group(dm_el, k): v for k, v in score.items()}
    johu = None
    mb = S.pillars_by(r["pillars"], "월")["gz"][1]
    if mb in "亥子丑" and w["火"] < 1.0:
        johu = "火"; el_score["火"] = max(el_score["火"], 0) + 0.7
    elif mb in "巳午未" and w["水"] < 1.0:
        johu = "水"; el_score["水"] = max(el_score["水"], 0) + 0.7
    order = sorted(EL, key=lambda e: -el_score[e])
    labels = {}
    for e in EL:
        labels[e] = "한신"
    labels[order[0]] = "용신"; labels[order[1]] = "희신"; labels[order[-1]] = "기신"; labels[order[-2]] = "구신"
    return {"용신": el_of_group(dm_el, yong), "희신": el_of_group(dm_el, hee), "용신_십신": yong, "희신_십신": hee,
            "이유": reason, "조후": johu, "el_score": el_score, "labels": labels, "strong": strong}


def gz_score(gz, ys, r, extra_branches=None):
    """간지 하나가 이 사주에 주는 영향 점수 (-3 ~ +3 근사) 와 관계 설명 목록"""
    s, b = gz
    es = ys["el_score"]
    sc = es[S.STEM_EL[S.STEMS.index(s)]] * 0.8 + es[S.BRANCH_EL[S.BRANCHES.index(b)]] * 1.0
    notes = []
    for p in r["pillars"] + (extra_branches or []):
        name = p["name"]
        for rel in S.pair_relations(b, p["gz"][1]):
            pal = PALACE.get(name, name)
            if rel == "충":
                sc -= 1.0 if name in ("일", "월") else 0.5
                notes.append(f"{J(S.BRANCHES_KO[S.BRANCHES.index(p['gz'][1])] + '(' + p['gz'][1] + ')', '과')} 충돌({pal} 쪽 변동)")
            elif "형" in rel:
                sc -= 0.6
                notes.append(f"{J(S.BRANCHES_KO[S.BRANCHES.index(p['gz'][1])] + '(' + p['gz'][1] + ')', '과')} 형({pal} 쪽 마찰·서류 점검)")
            elif rel.startswith("육합") or rel.startswith("삼합 반합"):
                hel = rel.split("(")[1].rstrip(")").split(",")[0][:1]
                hel_h = {v: k for k, v in EK.items()}.get(hel)
                good = hel_h and es.get(hel_h, 0) > 0
                sc += 0.5 if good else 0.1
                notes.append(f"{J(S.BRANCHES_KO[S.BRANCHES.index(p['gz'][1])] + '(' + p['gz'][1] + ')', '과')} 합({pal} 쪽 인연·협력{'' if good else ', 다만 발이 묶일 수도'})")
            elif rel in ("파", "해", "원진"):
                sc -= 0.3
                notes.append(f"{J(S.BRANCHES_KO[S.BRANCHES.index(p['gz'][1])] + '(' + p['gz'][1] + ')', '과')} {rel}({pal} 쪽 작은 서운함)")
        for rel in S.pair_relations(s, p["gz"][0], stems=True):
            if rel == "천간충": sc -= 0.3
            elif p["name"] == "일" and rel.startswith("천간합"):
                sc += 0.3; notes.append(f"일간과 천간합({p['gz'][0]}{s}: 끌리는 인연·일에 묶임)")
    if b in S.CHEONEUL[r["day_master"]["stem"]]:
        sc += 0.7; notes.append("천을귀인(도와주는 사람)")
    # 중복 제거 + 중요도 순 정렬 (귀인 > 충 > 형 > 합 > 기타)
    seen, uniq = set(), []
    for n in notes:
        if n not in seen: seen.add(n); uniq.append(n)
    pri = lambda n: 0 if "귀인" in n else 1 if "충돌" in n else 2 if " 형(" in n else 3 if "합" in n else 4
    return sc, sorted(uniq, key=pri)


def stars(sc):
    return max(1, min(5, int(round(3 + sc * 0.8))))


# ------------------------------------------------------------ 월건 목록
@lru_cache(maxsize=4096)
def _day_gz(d):
    # 정오 KST(=11시 CST) 기준 년/월 간지
    lun = Solar.fromYmdHms(d.year, d.month, d.day, 11, 0, 0).getLunar()
    ec = lun.getEightChar()
    return ec.getYear(), ec.getMonth(), ec.getDay()


def month_segments(start, days=460):
    segs = []
    d = start
    for i in range(days):
        yg, mg, _ = _day_gz(d)
        if not segs or segs[-1]["gz"] != mg:
            segs.append({"gz": mg, "year_gz": yg, "start": d, "end": d})
        else:
            segs[-1]["end"] = d
        d += timedelta(days=1)
    return segs


def day_gz(d):
    # 일진: saju_engine과 같은 방식 (2000-01-01 = 戊午)
    return S.gz_from_index(54 + d.toordinal() - date(2000, 1, 1).toordinal())


# ------------------------------------------------------------ 섹션 생성
def build(r, today=None):
    today = today or date.today()
    dm = r["day_master"]; ds = dm["stem"]; dm_el = dm["element"]
    ps = r["pillars"]; P = {p["name"]: p for p in ps}
    w = r["five_elements_weighted_with_hidden"]; cnt = r["five_elements_count"]
    ys = yongsin(r)
    male = r["input"]["gender"] == "남"
    tg = r["ten_gods_count"]
    grp = {k: 0 for k in GROUP_OFFSET}
    for k, v in tg.items(): grp[GROUP_OF[k]] += v
    top = max(grp, key=lambda k: grp[k])
    img, good, caution = DM[ds]
    yong, hee = ys["용신"], ys["희신"]
    sin_all = [s for x in r["sinsal"] for s in x["sinsal"]]
    rels = r["relations"]
    strong_txt = r["strength"]["판단(참고용)"].split("(")[0]
    missing = [e for e in EL if cnt[e] == 0]
    excess = [e for e in EL if cnt[e] >= 4 or w[e] >= 3.5]

    sec = []
    # 요약
    summary = (f"{img}({ds}{dm['ko']}, {EK[dm_el]}) 같은 사람이에요. "
               + ("기운이 강한(" + strong_txt + ") 편" if ys["strong"] else "기운이 여린(" + strong_txt + ") 편")
               + (f"이고 {', '.join(EK[e]+'('+e+')' for e in excess)} 기운이 많아요. " if excess else "이에요. ")
               + f"균형을 잡아 주는 기운(용신)은 {EK[yong]}({yong}), 돕는 기운(희신)은 {J(EK[hee] + '(' + hee + ')', '으로')} 봐요.")
    # 성격
    t = [f"일간이 {ds}({dm['ko']}){EK[dm_el]}, 즉 {J(img, '이라')}서 {good}.",
         f"사주에 {J(top, '이')} {grp[top]}개로 가장 많아 {GROUP_TRAIT[top]}이에요."]
    mtg = P["월"]["branch_tengod"]
    t.append(f"사회 환경을 뜻하는 월지가 {J(mtg + '(' + P['월']['gz'][1] + ')', '이라')} 밖에서는 '{TG_KEY[mtg]}'의 모습이 두드러져요.")
    t.append(f"일지 12운성이 {J(P['일']['12운성'], '이라')} {STAGE_TXT[P['일']['12운성']]}.")
    t.append(f"다만 {caution}.")
    sec.append({"key": "personality", "title": "성격", "icon": "🪞", "body": " ".join(t)})

    # 재물
    jae_vis = grp["재성"]; sik_vis = grp["식상"]; bi = grp["비겁"]
    jae_el = el_of_group(dm_el, "재성"); jae_w = w[jae_el]
    t = []
    if jae_vis == 0 and jae_w < 0.5:
        t.append("겉으로 드러난 재성(돈 기운)이 거의 없어 돈을 직접 쫓기보다 실력·명예를 쌓으면 돈이 따라오는 구조예요.")
    else:
        pos = [p["name"] for p in ps if GROUP_OF.get(p["branch_tengod"]) == "재성" or (p["name"] != "일" and GROUP_OF.get(p["stem_tengod"]) == "재성")]
        posm = {"년": "집안·초년", "월": "사회 활동", "일": "배우자·생활", "시": "사업 결과·말년"}
        kind = "편재" if tg.get("편재", 0) >= tg.get("정재", 0) else "정재"
        t.append(f"재성이 {'·'.join(posm[x] for x in pos) or '지장간'} 자리에 있고 {kind} 위주라 "
                 + ("큰돈이 들고 나는 사업형이에요." if kind == "편재" else "꾸준히 모으는 월급·저축형이에요."))
    if sik_vis >= 1 and (jae_vis >= 1 or jae_w >= 1):
        t.append("식상과 재성이 이어져 재능·아이디어가 돈으로 바뀌는 식신생재 흐름이 있어요.")
    if bi >= 3 and jae_vis >= 1:
        t.append(f"비겁이 {bi}개로 많아 동업·돈거래·보증으로 돈이 새기 쉬운 '군겁쟁재' 경향이 있어요. 돈 관리는 직접 하세요.")
    if any(p["gz"][1] in "辰戌丑未" for p in ps):
        t.append("창고 글자(辰戌丑未)가 있어 모아 두는 힘은 있어요.")
    if ys["용신_십신"] in ("재성", "식상"):
        t.append(f"용신이 {ys['용신_십신']} 쪽이라 돈을 버는 활동 자체가 운을 살려 줘요.")
    sec.append({"key": "wealth", "title": "재물", "icon": "💰", "body": " ".join(t)})

    # 직업
    car = {"비겁": "독립 사업·자영업·스포츠·영업", "식상": "기술·강의·방송·콘텐츠·기획", "재성": "사업·유통·무역·금융·투자",
           "관성": "공직·대기업·관리직·법무", "인성": "교육·연구·상담·자격 전문직"}
    t = [f"가장 강한 {top} 기운으로 보면 {car[top]} 쪽 성향이 있어요.",
         f"용신 {EK[yong]}({yong}) 기운을 쓰는 {EL_INFO[yong]['job']}도 잘 맞아요.",
         f"본업의 오행이 내게 많은 기운이라도 괜찮아요. 부족한 {EK[yong]} 기운({TG_KEY.get({'식상':'식신','재성':'편재','관성':'정관','인성':'정인','비겁':'비견'}[ys['용신_십신']])})을 일하는 방식에 더하면 시너지가 나요."]
    if grp["관성"] >= 1 and grp["인성"] >= 1:
        t.append("관성과 인성이 함께 있어 조직에서 신뢰를 얻고 직함을 얻는 '관인상생' 기운도 있어요.")
    sec.append({"key": "career", "title": "직업·적성", "icon": "🧭", "body": " ".join(t)})

    # 연애
    spouse_grp = "재성" if male else "관성"
    sp_cnt = grp[spouse_grp]
    db = P["일"]["gz"][1]; dtg = P["일"]["branch_tengod"]
    t = [f"배우자 자리(일지)가 {J(dtg + '(' + db + ')', '이라')} 배우자에게 '{TG_KEY[dtg]}'의 모습을 기대하거나 그런 인연을 만나기 쉬워요."]
    if sp_cnt == 0:
        t.append(f"{'남자는 재성' if male else '여자는 관성'}이 배우자 별인데 겉으로 드러나지 않아 인연이 늦거나 직접 찾아 나서야 하는 편이에요.")
    elif sp_cnt >= 3:
        t.append("배우자 별이 많아 이성 인연은 많지만 정리가 필요할 수 있어요.")
    else:
        t.append("배우자 별이 적당히 있어 인연 운은 무난해요.")
    for x in rels:
        if "일지" in x and ("충" in x.split()[-1] or "형" in x):
            t.append(f"일지가 다른 글자와 부딪혀({x.split(' ',1)[1]}) 생활 리듬이나 의견 차이로 다툼이 생길 수 있으니 대화로 풀어 가세요.")
            break
    for x in rels:
        if "일지" in x and "육합" in x:
            t.append("일지가 합을 이뤄 정이 깊은 관계를 만들어요."); break
    if any("홍염" in s for s in sin_all) or any("도화" in s for s in sin_all):
        t.append("도화·홍염 기운이 있어 이성에게 매력이 있어요.")
    sec.append({"key": "love", "title": "연애·결혼", "icon": "💞", "body": " ".join(t)})

    # 건강
    t = []
    for e in excess:
        t.append(f"{EK[e]}({e}) 기운이 넘쳐 {EL_INFO[e]['organ']} 쪽을 챙기세요.")
        ctrl = EL[(EL.index(e) + 2) % 5]
        t.append(f"넘치는 {EK[e]}에 눌리는 {EK[ctrl]}({ctrl})의 {EL_INFO[ctrl]['organ']}도 신경 쓰면 좋아요.")
    for e in missing:
        if e not in [EL[(EL.index(x) + 2) % 5] for x in excess]:
            t.append(f"{EK[e]}({e}) 기운이 비어 있어 {EL_INFO[e]['organ']} 관리에 관심을 두세요.")
    if not t:
        t.append("오행이 비교적 고르게 있어 큰 치우침은 없어요. 규칙적인 생활이 최고의 관리예요.")
    t.append("(전통적 관점일 뿐 의학적 진단이 아니에요.)")
    sec.append({"key": "health", "title": "건강", "icon": "🌿", "body": " ".join(t)})

    # 대운
    by = date.fromisoformat(r["solar_date"]).year
    age_now = today.year - by
    daeun = []
    for d in r["daeun"]:
        sc, notes = gz_score(d["gz"], ys, r)
        cur = d["시작나이(만)"] <= age_now < d["시작나이(만)"] + 10
        daeun.append({"gz": d["gz"], "ko": d["ko"], "age": d["시작나이(만)"], "year": d["시작연도(대략)"],
                      "tg": f"{d['천간십신']}/{d['지지십신']}", "stars": stars(sc), "current": cur})
    cur_d = next((d for d in daeun if d["current"]), None)

    # 세운 (올해·내년) — 입춘 기준 사주 연도
    segs = month_segments(today)
    cur_year_gz = segs[0]["year_gz"]
    years = []
    for yg in dict.fromkeys(s["year_gz"] for s in segs):
        years.append(yg)
    cur_daeun_branch = [{"name": "대운", "gz": cur_d["gz"]}] if cur_d else []
    year_txt = []
    for i, yg in enumerate(years[:2]):
        sc, notes = gz_score(yg, ys, r, cur_daeun_branch)
        st, bt = S.ten_god(ds, yg[0]), S.branch_ten_god(ds, yg[1])
        n = stars(sc)
        mood = {5: "아주 좋은 해", 4: "좋은 해", 3: "무난한 해", 2: "조심이 필요한 해", 1: "몸을 낮추고 지키는 해"}[n]
        segs_y = [s for s in segs if s["year_gz"] == yg]
        gy = segs_y[0]["start"].year if i == 0 else segs_y[0]["start"].year
        body = (f"{yg}({S.gz_ko(yg)})년은 {mood}예요. 천간 {st}({TG_KEY[st]}), 지지 {bt}({TG_KEY[bt]})의 기운이 들어와요. "
                + (f"이 해의 기운이 용신·희신 쪽이라 힘을 받기 좋아요. " if sc > 0.8 else
                   "도움 기운과 부담 기운이 섞여 있어 선택과 집중이 중요해요. " if sc > -0.5 else
                   "부담 기운이 강해 무리한 확장보다 내실을 다지는 게 좋아요. ")
                + (("눈여겨볼 점: " + ", ".join(notes) + ".") if notes else ""))
        year_txt.append({"title": f"{'올해' if i == 0 else '내년'} {yg}({S.gz_ko(yg)})년", "stars": n, "body": body,
                         "label": "올해" if i == 0 else "내년"})

    # 월운
    months = []
    for s in segs:
        if s["year_gz"] not in years[:2]:
            continue
        sc, notes = gz_score(s["gz"], ys, r)
        st, bt = S.ten_god(ds, s["gz"][0]), S.branch_ten_god(ds, s["gz"][1])
        n = stars(sc)
        tip = {5: "적극적으로 밀어붙이기 좋은 달", 4: "기회를 잡기 좋은 달", 3: "꾸준히 이어 가는 달",
               2: "지출·말·계약을 한 번 더 점검할 달", 1: "무리하지 말고 지키는 달"}[n]
        months.append({"gz": s["gz"], "ko": S.gz_ko(s["gz"]), "start": s["start"].isoformat(), "end": s["end"].isoformat(),
                       "year": "올해" if s["year_gz"] == years[0] else "내년", "stars": n,
                       "tg": f"{st}·{bt}",
                       "body": f"{J(chr(39) + TG_KEY[st] + chr(39), '과')} '{TG_KEY[bt]}' 기운이 들어오는, {tip}이에요." + (" 포인트: " + ", ".join(notes[:2]) + "." if notes else "")})

    # 조언
    info = EL_INFO[yong]
    t = [f"용신 {EK[yong]}({yong}) 기운을 생활에 더하세요: {info['act']}.",
         f"행운 색은 {info['color']}, 방향은 {info['dir']}, 숫자는 {info['num']}이에요.",
         f"희신 {EK[hee]}({hee}) 쪽({EL_INFO[hee]['act'].split(',')[0]})도 함께 챙기면 좋아요."]
    if bi >= 3: t.append("돈과 결정권은 직접 쥐고, 고집은 조금만 내려놓으세요.")
    if grp["관성"] >= 3: t.append("책임을 혼자 다 지려 하지 말고 스트레스를 풀 통로를 만드세요.")
    if grp["식상"] >= 3: t.append("말이 앞서면 구설이 생기니 한 번 더 생각하고 말하세요.")
    if grp["인성"] >= 3: t.append("생각만 하다 타이밍을 놓치지 않게 실행 날짜를 정해 두세요.")
    good_m = [m for m in months if m["stars"] >= 4][:3]
    if good_m:
        t.append("다가오는 좋은 달: " + ", ".join(f"{m['start'][:7].replace('-', '년 ')}월({m['gz']})" for m in good_m) + ".")
    sec_adv = {"key": "advice", "title": "조언", "icon": "🧧", "body": " ".join(t)}

    return {"summary": summary, "yongsin": {k: ys[k] for k in ("용신", "희신", "용신_십신", "희신_십신", "이유", "조후", "labels")},
            "sections": sec, "years": year_txt, "months": months, "daeun": daeun, "advice": sec_adv,
            "groups": grp}


# ------------------------------------------------------------ 궁합
def gunghap(r1, r2):
    a, b = r1["day_master"], r2["day_master"]
    ea, eb = a["element"], b["element"]
    k = (EL.index(eb) - EL.index(ea)) % 5
    score = 60
    pts = []
    rel_txt = {0: ("같은 오행", "생각과 기질이 비슷해 편하지만 주도권 경쟁이 생길 수 있어요.", 4),
               1: ("A가 B를 생함", "A가 B를 챙기고 밀어 주는 관계예요.", 8),
               4: ("B가 A를 생함", "B가 A를 챙기고 밀어 주는 관계예요.", 8),
               2: ("A가 B를 극함", "A가 B를 이끌거나 통제하려는 구도가 생기기 쉬워요. 존중이 열쇠예요.", -4),
               3: ("B가 A를 극함", "B가 A를 이끌거나 통제하려는 구도가 생기기 쉬워요. 존중이 열쇠예요.", -4)}
    nm, txt, d = rel_txt[k]
    score += d
    pts.append({"title": "일간 관계", "body": f"{a['stem']}{EK[ea]} × {b['stem']}{EK[eb]} → {nm}. {txt}"})
    hap = S.pair_relations(a["stem"], b["stem"], stems=True)
    if any(h.startswith("천간합") for h in hap):
        score += 12; pts.append({"title": "천간합", "body": f"두 일간이 합({a['stem']}{b['stem']})을 이뤄 서로 끌리는 인연이에요."})
    if "천간충" in hap:
        score -= 6; pts.append({"title": "천간충", "body": "생각의 방향이 부딪히기 쉬워 대화 방식 조율이 필요해요."})
    da = S.pillars_by(r1["pillars"], "일")["gz"][1]; db = S.pillars_by(r2["pillars"], "일")["gz"][1]
    br = S.pair_relations(da, db)
    good = [x for x in br if x.startswith("육합") or x.startswith("삼합") or x.startswith("방합")]
    bad = [x for x in br if x == "충" or "형" in x or x in ("파", "해", "원진")]
    if good: score += 10
    if bad: score -= 6 * len(bad)
    pts.append({"title": "일지(배우자 자리)", "body": f"{da} × {db}: " + (", ".join(br) if br else "특별한 합충 없음")
                + (". 생활 리듬과 정서가 잘 맞아요." if good and not bad else ". 생활 속 사소한 부딪힘을 조심하세요." if bad else ". 무난해요.")})
    # 오행 보완
    wa, wb = r1["five_elements_weighted_with_hidden"], r2["five_elements_weighted_with_hidden"]
    ya, yb = yongsin(r1)["용신"], yongsin(r2)["용신"]
    comp = []
    if wb[ya] >= 1.5: comp.append(f"B가 A에게 필요한 {EK[ya]}({ya}) 기운을 채워 줘요"); score += 8
    if wa[yb] >= 1.5: comp.append(f"A가 B에게 필요한 {EK[yb]}({yb}) 기운을 채워 줘요"); score += 8
    pts.append({"title": "오행 보완", "body": (". ".join(comp) + ".") if comp else "서로의 부족한 기운을 직접 채워 주진 않지만, 함께 다른 활동으로 보완할 수 있어요."})
    # 띠
    ya_b = S.pillars_by(r1["pillars"], "년")["gz"][1]; yb_b = S.pillars_by(r2["pillars"], "년")["gz"][1]
    tb = S.pair_relations(ya_b, yb_b)
    if tb:
        pts.append({"title": "띠 궁합", "body": f"{S.ANIMALS[S.BRANCHES.index(ya_b)]}띠 × {S.ANIMALS[S.BRANCHES.index(yb_b)]}띠: {', '.join(tb)}"})
        if any(x.startswith("육합") or x.startswith("삼합") for x in tb): score += 4
        if "충" in tb or "원진" in tb: score -= 4
    score = max(20, min(98, score))
    grade = "천생연분" if score >= 85 else "잘 맞는 편" if score >= 70 else "노력하면 좋은 사이" if score >= 55 else "서로 맞춰 가야 하는 사이"
    return {"score": score, "grade": grade, "points": pts}


# ------------------------------------------------------------ 택일
PURPOSE = {"계약": ("정관", "정재", "정인"), "개업": ("식신", "편재", "정재"), "이사": ("정인", "정재", "식신")}


def taekil(r, start, end, purpose="계약", topn=7):
    ys = yongsin(r)
    ds = r["day_master"]["stem"]
    db = S.pillars_by(r["pillars"], "일")["gz"][1]
    yb = S.pillars_by(r["pillars"], "년")["gz"][1]
    fav = PURPOSE.get(purpose, PURPOSE["계약"])
    out = []
    d = start
    while d <= end and len(out) < 400:
        g = day_gz(d)
        sc, notes = gz_score(g, ys, r)
        st, bt = S.ten_god(ds, g[0]), S.branch_ten_god(ds, g[1])
        if st in fav: sc += 0.6
        if bt in fav: sc += 0.6
        if purpose == "이사" and g[1] in S.CHEONEUL[ds]: sc += 0.3
        bad = "충" in S.pair_relations(g[1], db) or "충" in S.pair_relations(g[1], yb)
        if bad: sc -= 1.0
        out.append({"date": d.isoformat(), "weekday": "월화수목금토일"[d.weekday()], "gz": g, "ko": S.gz_ko(g),
                    "score": round(sc, 2), "stars": stars(sc), "tg": f"{st}/{bt}",
                    "why": f"{st}·{bt}({TG_KEY[st]} / {TG_KEY[bt]})" + (". " + ", ".join(notes[:2]) if notes else ""),
                    "avoid": bad})
        d += timedelta(days=1)
    best = sorted([x for x in out if not x["avoid"]], key=lambda x: -x["score"])[:topn]
    avoid = [x for x in out if x["avoid"]][:10]
    return {"purpose": purpose, "best": sorted(best, key=lambda x: x["date"]), "avoid": avoid, "days": len(out)}
