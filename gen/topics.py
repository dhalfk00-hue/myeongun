# -*- coding: utf-8 -*-
"""tier1115: 주제 심층(돈·직업·사업·결혼·이사·궁합·건강·자녀).

주제마다 같은 틀로 써요.
  한눈에(요약) → 타고난 바탕(원국 근거) → 10년 단위 흐름(대운) → 2026~2035 해마다(주제 별점 + 조심/보완)
  → 좋은 해·조심할 해 → 실천 체크.
- 주제 점수 = 0.6 × 종합 점수 + 그 주제에 걸린 십신·합충·신살 가감(±2.5 안). 별점은 종합과 같은 방식(절대 60% + 10년 안 순위 40%).
  같은 엔진·같은 용신을 쓰므로 주제끼리, 등급끼리 결론이 엇갈리지 않아요.
- 좋은 해에는 '조심', 나쁜 해에는 '보완'을 꼭 붙여요(advice.period_advice 규칙 그대로).
- 결혼은 시기를 말하지 않아요. 관계의 온도와 부딪히기 쉬운 해, 다지기 좋은 해만 말해요.
"""
import re
import engine as E
import saju as S
from engine import STEM_ELK, BR_ELK
from texts import *
from josa import josa, particle
import advice as AV
import jobs as JB
import vary as V
import persona as PS
import natal as NT

TOPICS = ("money", "job", "biz", "love", "move", "gunghap", "health", "kids")
KO = {"money": "돈", "job": "직업", "biz": "사업", "love": "결혼", "move": "이사", "gunghap": "궁합", "health": "건강", "kids": "자녀"}
FROM_KO = {v: k for k, v in KO.items()}
FROM_KO.update({"재물": "money", "애정": "love", "배우자": "love", "연애": "love"})
TITLE = {"money": "돈 · 재물의 흐름", "job": "직업 · 일과 자리", "biz": "사업 · 장사와 확장", "love": "결혼 · 애정 · 배우자",
         "move": "이사 · 이동과 방향", "gunghap": "궁합 · 두 사람", "health": "건강 · 몸의 리듬", "kids": "자녀 · 자녀와의 인연"}
AREA = {"money": "money", "job": "job", "biz": "job", "love": "rel", "health": "health"}
DIR = {"목": "동쪽", "화": "남쪽", "토": "남서쪽", "금": "서쪽", "수": "북쪽"}
# 해마다 피하는 방향(전통 이사 방위): 삼살(三殺) · 대장군(大將軍)
SAMSAL = {**{b: "남쪽" for b in "申子辰"}, **{b: "북쪽" for b in "寅午戌"}, **{b: "동쪽" for b in "巳酉丑"}, **{b: "서쪽" for b in "亥卯未"}}
DAEJANG = {**{b: "서쪽" for b in "亥子丑"}, **{b: "북쪽" for b in "寅卯辰"}, **{b: "동쪽" for b in "巳午未"}, **{b: "남쪽" for b in "申酉戌"}}


def parse_topics(s):
    out = []
    for x in re.split(r"[,\s·/]+", s or ""):
        if not x: continue
        k = FROM_KO.get(x, x)
        if k not in TOPICS: raise ValueError(f"주제는 {'·'.join(KO.values())} 중에서 골라요: {x}")
        if k not in out: out.append(k)
    return out


def stars(n): return "★" * n + "☆" * (5 - n)
def el_full(e): return f"{e}({EL_HAN[e]})"


_SS = "비견|겁재|식신|상관|편재|정재|편관|정관|편인|정인|재성|관성|인성|식상|비겁"
def _norm(x):
    x = re.sub(r"(?:%s)(?:이|가|은|는|을|를|과|와)?" % _SS, "X", re.sub(r"<[^>]+>", " ", x))
    return re.sub(r"\s+", " ", x).strip()


def _trip():
    return "이동·여행·출장" if JB.CUR["job"] in ("직장인", "사업자", "프리랜서", "미정") else "이동·여행·바깥 일정"


def _why_split(x):
    """'…해라, 행동' / '…해예요. 행동' → (이유, 행동)"""
    for sep in ("해라, ", "해예요. ", "해라 ", "해예요, "):
        if sep in x:
            i = x.index(sep) + len(sep); w, r = x[:i].strip(), x[i:].strip()
            if r and r[0] != r[0].upper(): pass
            return w, (r[0].upper() + r[1:]) if r else ""
    return "", ""


class Topics:
    def __init__(self, rep):
        self.rep = rep; self.c = rep.c; self.years = rep.years; self.Y = rep.Y
        self._ts = {}

    # ------------------------------------------------------------ 점수
    def arrivals(self, gz):
        c = self.c; s, b = gz
        return [(TG_GROUP[c.tg(s)], c.fav[STEM_ELK[s]], 1.0, c.tg(s), s), (TG_GROUP[c.tg(b, True)], c.fav[BR_ELK[b]], 1.3, c.tg(b, True), b)]

    def yeokma(self, b):
        c = self.c; yb = c.P["년"]["gz"][1]
        return S.sinsal12(yb, b).startswith("역마") or S.sinsal12(c.db, b).startswith("역마")

    def move_power(self, gz):
        """이동수 세기: 일지 충 2 · 월지 충 1.5 · 역마 1 · 년지 충 0.5 · 일간 천간충 0.5"""
        c = self.c; rels = c.relations_to_chart(*gz); v = 0; why = []
        for k, pos, det, el in rels:
            if k == "충" and pos == "일" and "일" not in why: v += 2; why.append("일")
            elif k == "충" and pos == "월" and "월" not in why: v += 1.5; why.append("월")
            elif k == "충" and pos == "년" and "년" not in why: v += 0.5; why.append("년")
            elif k == "천간충" and pos == "일" and "간" not in why: v += 0.5; why.append("간")
        if self.yeokma(gz[1]): v += 1; why.append("역마")
        return v, why

    def tscore(self, t, gz):
        key = (t, gz)
        if key in self._ts: return self._ts[key]
        c = self.c; base, rels = c.score(gz); m = 0.0
        arr = self.arrivals(gz)
        chung = {p for k, p, _, _ in rels if k == "충"}
        hap = {p: el for k, p, _, el in rels if k in ("육합", "반합")}
        hy = {p for k, p, _, _ in rels if k in ("형", "원진")}
        has_j = c.gcount["재성"] or c.hidden_groups["재성"]
        if t == "money":
            for g, f, w, *_ in arr:
                if g == "재성": m += w * (0.9 if f >= 0 else (0.1 if c.strong else -0.7))
                elif g == "식상": m += w * (0.5 if f >= 0 else -0.2) * (1 if has_j else 0.5)
                elif g == "비겁": m += w * (-0.7 if (c.gcount["재성"] and (c.strong or f < 0)) else 0.3)
                elif g == "관성": m += w * (-0.3 if f <= 0 else 0.1)
                elif g == "인성": m += w * (-0.3 if f < 0 else 0.1)
            if "월" in chung: m -= 0.3
        elif t == "job":
            for g, f, w, *_ in arr:
                m += w * {"관성": (0.8, -0.5), "인성": (0.5, -0.2), "식상": (0.4, -0.4), "재성": (0.3, -0.2), "비겁": (0.2, -0.5)}[g][0 if f >= 0 else 1]
            if "월" in chung: m -= 0.4
            if "월" in hap and c.fav.get(hap["월"], 0) >= 0: m += 0.4
        elif t == "biz":
            for g, f, w, *_ in arr:
                if g == "비겁": m += w * (-0.8 if (c.strong or f < 0) else 0.3)
                else: m += w * {"재성": (0.9, -0.6), "식상": (0.7, -0.2), "관성": (0.3, -0.6), "인성": (0.1, -0.4)}[g][0 if f >= 0 else 1]
            if "월" in chung: m -= 0.4
            if "월" in hap and c.fav.get(hap["월"], 0) >= 0: m += 0.4
            if self.yeokma(gz[1]): m += 0.2
        elif t == "love":
            m += 0.8 * (c.love_score(gz) - 1.0)
            if "일" in chung: m -= 0.8
            if "일" in hy: m -= 0.4
        elif t == "move":
            f2 = c.fav[BR_ELK[gz[1]]]
            m += 0.6 if f2 >= 1 else -0.4 if f2 <= -1 else 0
            mp, _ = self.move_power(gz)
            if mp >= 2 and base < 0: m -= 0.4
        elif t == "health":
            hi = max(c.wt, key=c.wt.get); lo = min(c.wt, key=c.wt.get)
            if "일" in chung: m -= 0.8
            if "월" in chung: m -= 0.6
            if hy & {"일", "월"}: m -= 0.4
            for el, w in ((STEM_ELK[gz[0]], 1.0), (BR_ELK[gz[1]], 1.3)):
                if el == hi and c.fav[el] < 0: m -= 0.5 * w
                if el == lo and c.fav[el] >= 0: m += 0.4 * w
                if CTRL[el] == lo and c.fav[el] < 0: m -= 0.3 * w
            if not c.strong and any(g == "관성" for g, *_ in arr): m -= 0.3
        elif t == "kids":
            kg = "식상" if c.gender == "F" else "관성"
            for g, f, w, tg, ch in arr:
                if g == kg: m += w * (0.7 if f >= 0 else 0.3)
                if c.gender == "F" and tg == "편인" and c.gcount["식상"]: m -= 0.3 * w
            if c.time_known:
                if "시" in hap: m += 0.5
                if "시" in chung: m -= 0.6
        v = 0.6 * base + max(-2.5, min(2.5, m))
        self._ts[key] = round(v, 2)
        return self._ts[key]

    def ystars(self, t):
        """종합 별점과 같은 규칙: 절대 별점 60% + 10년 안 순위 40%"""
        c = self.c; ys = self.years
        sc = {y: self.tscore(t, E.year_gz(y)) for y in ys}
        ab = {y: c.stars(v) for y, v in sc.items()}
        order = sorted(ys, key=lambda y: -sc[y]); n = len(order)
        rk = {y: 5 - 4 * i / (n - 1) for i, y in enumerate(order)}
        out = {}
        for y in ys:
            a = ab[y]; v = int(0.6 * a + 0.4 * rk[y] + 0.5)
            v = max(a - 1, min(a + 1, v))
            if a <= 3: v = min(v, 4)
            if a <= 1: v = min(v, 2)
            out[y] = max(1, min(5, v))
        return sc, out

    # ------------------------------------------------------------ 신호(표 칸)
    def signal(self, t, gz):
        c = self.c; rels = c.relations_to_chart(*gz); toks = []
        want = {"money": ("재성", "식상", "비겁"), "job": ("관성", "인성", "식상"), "biz": ("재성", "식상", "비겁", "관성"),
                "love": (), "move": (), "health": (), "kids": ("식상",) if c.gender == "F" else ("관성",)}[t]
        for g, f, w, tg, ch in self.arrivals(gz):
            if g in want and tg not in " ".join(toks):
                toks.append(f"{tg}" + (f"({NT.ROLE[f][:2]})" if f else ""))
        if t == "love":
            se = c.gel["관성"] if c.gender == "F" else c.gel["재성"]
            if STEM_ELK[gz[0]] == se or BR_ELK[gz[1]] == se: toks.append("배우자 별")
            if frozenset(gz[0] + c.dm) in S.STEM_HAP: toks.append("일간 합")
        if t in ("health",):
            for el in dict.fromkeys((STEM_ELK[gz[0]], BR_ELK[gz[1]])):
                if c.fav[el] <= -1: toks.append(f"{EL_WORD[el]} 부담")
        pos_want = {"money": ("월", "일"), "job": ("월",), "biz": ("월",), "love": ("일",), "move": ("일", "월", "년"),
                    "health": ("일", "월"), "kids": ("시",)}[t]
        seen = set()
        for k, pos, det, el in rels:
            if pos not in pos_want: continue
            kk = {"육합": "합", "반합": "합"}.get(k, k)
            if kk not in ("충", "합", "형", "원진") or (kk, pos) in seen: continue
            seen.add((kk, pos)); toks.append(f"{POS_NAME[pos]} {kk}")
        if t in ("move", "biz") and self.yeokma(gz[1]): toks.append("역마")
        if t == "money":
            gb = JAEGO[c.gel["재성"]]
            if gb in [p["gz"][1] for p in c.P.values()] and "충" in S.pair_relations(gz[1], gb): toks.append("재고 충")
        return " · ".join(toks[:3]) or "큰 신호 없음"

    # ------------------------------------------------------------ 조언 한 줄
    def adv(self, t, gz, sc, key, kind="year", year=None, star=None, age=None):
        """verdict1116: (판정 꼬리표 html, 글). 별점이 판정을 정해요.
        ★4~5 추천 + 조심 1 / ★3 조심 + 보완 / ★1~2 보완. 이사는 해도 됨·신중·미룸."""
        c = self.c; st = star if star is not None else c.stars(sc)
        if t in AREA:
            it = AV.period_advice(c, gz, sc, AREA[t], key=key + t, max_items=2, scope="이 해는" if kind == "year" else "이 10년은",
                                  lead=True, label="", kind=kind, year=year, star=st)
            if st <= 2: it = it[:1]   # 표 칸은 보완 1개로 짧게
            return AV.vd(st), self._compose(it, st)
        if t == "move": return self.move_adv(gz, sc, key, kind, st, year)
        if t == "kids": return self.kids_adv(gz, sc, key, kind, year, st, age)
        return AV.vd(st), ""

    @staticmethod
    def _compose(items, st):
        out = []
        for i, (k, x) in enumerate(items):
            x = AV.fuse(x)
            if i == 0 and (k == "추천" and st >= 4 or k == "보완" and st <= 2): out.append(x)
            else: out.append(f'<b class="{AV.cls(k)}">{k}</b> {x}')
        return " ".join(out)

    def move_adv(self, gz, sc, key, kind="year", st=None, year=None):
        """verdict1116: 이사·매매 판정은 별점이 정해요 — ★4~5 해도 됨 / ★3 신중 / ★1~2 미룸. 이동수(충·역마)는 이유로만 써요."""
        c = self.c; mp, why = self.move_power(gz); st = st if st is not None else c.stars(sc)
        span = "해" if kind == "year" else "10년"
        yd = DIR[c.yong]; hd = DIR[c.hee]
        avoid = SAMSAL[gz[1]] if kind == "year" else None
        d = yd if avoid != yd else hd
        src = (f"{'일지(생활 터전)' if '일' in why else '월지(사회 환경)' if '월' in why else '년지(집안)' if '년' in why else ''}"
               f"{'를 치는 충' if any(x in why for x in ('일', '월', '년')) else ''}{'과 ' if any(x in why for x in ('일', '월', '년')) and '역마' in why else ''}{'역마' if '역마' in why else ''}")
        if mp >= 1.5 and src: rs = f"{src}{particle(src, '로')} 움직일 일이 생기기 쉬운 {josa(span, '이에요')}."
        elif mp >= 1: rs = f"역마가 들어 {_trip()}이 잦아지는 {josa(span, '이에요')}."
        else:   # release1116: 이동수가 약한 해도 그해 글자 갈래로 사람마다 다른 이유를 붙여요
            g_ = TG_GROUP[c.tg(gz[1], True)]
            why_ = {"비겁": "사람·형제 일로 집 문제가 얽히기 쉬운", "식상": "집을 꾸미고 바꾸고 싶은 마음이 커지는", "재성": "집값·대출 같은 돈 계산이 앞서는",
                    "관성": "계약·규칙 쪽 책임이 커지는", "인성": "서류·문서 일이 늘어나는"}[g_]
            rs = PS.pick([f"이동수는 약하고, {why_} {josa(span, '이에요')}.", f"크게 움직일 신호는 없지만 {why_} {josa(span, '이에요')}."], c, key + "rs")
        # release1116: 조심·보완은 그해 글자(십신 갈래·원국과의 관계)와 나이에 맞춰 골라요 — 사람마다 다른 이유가 붙어요
        grp = TG_GROUP[c.tg(gz[1], True)]
        rel = [k for k, p, _, _ in c.relations_to_chart(*gz) if p in ("일", "월")] if kind == "year" else []
        age = c.age(year) if year else None
        gi_d = DIR.get(c.gi)
        CAU = {"비겁": ["공동명의나 지인이 소개한 매물은 조건을 따로 확인하세요.", "가족·지인과 돈을 섞어 집을 구하지 마세요."],
               "식상": ["인테리어·옵션 욕심으로 예산이 불기 쉬우니 상한을 먼저 정하세요.", "말로 한 약속은 특약으로 계약서에 적어 두세요."],
               "재성": ["매매가·대출 한도를 숫자로 적어 두고 그 안에서만 고르세요.", "계약금 비율과 잔금 날짜를 먼저 정하고 들어가세요."],
               "관성": ["등기부 권리관계와 계약서 특약을 꼭 직접 확인하세요.", "관리 규약·허가 사항처럼 규칙에 걸리는 부분을 먼저 보세요."],
               "인성": ["서류·입주 일정이 늦어지기 쉬우니 잔금 날짜에 여유를 두세요.", "계약 전에 서류를 한 번 더 받아 읽고 서명하세요."]}[grp]
        if "형" in rel: CAU = ["층간소음·관리 문제처럼 이웃과 부딪힐 부분을 미리 확인하세요."] + CAU
        if "원진" in rel: CAU = ["함께 사는 사람과 의견이 갈리기 쉬우니 집은 같이 보고 정하세요."] + CAU
        if "충" in rel and st >= 3: CAU = ["이사 날짜를 몰아서 잡지 말고 짐·계약을 단계별로 나누세요."] + CAU
        if age is not None and age >= 65: REM = ["옮기기보다 지금 집의 난방·문턱·조명을 손보는 쪽이 이 해엔 더 맞아요.",
                                               "꼭 옮겨야 하면 병원·가족과 가까운 곳을 먼저 보세요."]
        elif age is not None and age < 35: REM = ["전월세 만기가 오면 연장 조건부터 알아보세요.", "보증금은 올리지 말고 이사 비용을 따로 모아 두세요."]
        else: REM = ["만기가 오면 연장 조건부터 알아보세요.", "수리·정리처럼 작은 변화로 대신하고, 이사 비용은 따로 모아 두세요."]
        REM = REM + [f"만기 등으로 꼭 옮겨야 하면 비용 상한부터 정하고 {d}의 작은 집부터 보세요."]
        avoid_t = f" {gi_d}은 피하는 쪽이 좋아요." if gi_d and gi_d != d and kind == "year" and PS.pick([0, 1], c, key + "gd") else ""
        if st >= 4:
            body = PS.pick([f"이사·매매를 해도 되는 {span}라, 옮긴다면 {d}을 먼저 보세요.",
                            f"집을 옮기거나 계약해도 좋은 {josa(span, '이에요')}. {d}과 밝은 집을 우선하세요."], c, key + "m1")
            if mp < 1: body = PS.pick([f"꼭 옮길 이유가 있다면 해도 돼요. 옮긴다면 {d}을 먼저 보세요.", f"옮길 계획이 있었다면 진행해도 괜찮아요. {d} 매물부터 보세요."], c, key + "m5")
            # release1116: ★4+ 행은 '늦어지기 쉬우니'처럼 나쁜 예고 없이 확인 습관 한 가지만 남겨요
            hi = [x for x in CAU if not re.search(r"늦어지|부딪|갈리|불기 쉬", x)] or ["계약서 특약과 잔금 날짜를 한 번 더 확인하세요."]
            if grp == "인성": hi = ["잔금 날짜는 여유 있게 잡고, 서류는 미리 챙겨 두세요."] + hi
            cau = PS.pick(hi[:2], c, key + "m2")
            return AV.vd(st, "해도 됨"), f'{rs} {body} <b class="adv-c">조심</b> {cau}'
        if st == 3:
            body = f"필요하면 하되, 두세 곳을 글로 비교한 뒤 {d}을 우선하세요." + avoid_t
            cau = PS.pick(CAU[:3], c, key + "m3")
            return AV.vd(st, "신중"), f'{rs} {body} <b class="adv-c">조심</b> {cau}'
        body = "큰 이사·매매는 미루세요."
        rem = PS.pick(REM, c, key + "m4")
        return AV.vd(st, "미룸"), f'{rs} {body} <b class="adv-s">보완</b> {rem}'

    @staticmethod
    def stage(age):
        """verdict1116: 자녀 문구의 나이 단계(그 해의 내 나이 기준). 자녀가 있는지는 모르므로 늘 조건문으로 써요."""
        return "young" if age < 35 else "school" if age < 45 else "adult" if age < 60 else "senior"

    KID_EV = {
        "chung": {"young": "생활 리듬·돌봄 계획이 바뀌기 쉬운", "school": "자녀의 학교·진로·거처에 변동이 생기기 쉬운",
                  "adult": "자녀의 독립·취업·거처 같은 큰 변화가 생기기 쉬운", "senior": "자녀와의 왕래·거처에 변화가 생기기 쉬운"},
        "doshik": {"young": "걱정이 앞서 마음이 바빠지기 쉬운", "school": "걱정과 간섭이 자녀와의 거리를 만들기 쉬운",
                   "adult": "성인 자녀 일에 간섭이 거리를 만들기 쉬운", "senior": "걱정이 서운함으로 바뀌기 쉬운"},
        "in_good": {"young": "자녀 일에 마음과 시간이 많이 가는", "school": "자녀의 학업·진로에 마음과 시간이 많이 가는",
                    "adult": "자녀의 독립·거처 같은 일에 마음과 돈이 가는", "senior": "자녀·손주와 오가는 일이 늘어나는"},
        "in_bad": {"young": "돌봄 부담과 지출이 늘기 쉬운", "school": "자녀 관련 지출과 걱정이 늘기 쉬운",
                   "adult": "경제적 도움 요청이 늘기 쉬운", "senior": "자녀 일로 걱정이 늘기 쉬운"},
        "hap": {"young": "자녀와 함께하는 계획이 생기기 쉬운", "school": "자녀와 함께 정할 계획(진학·활동)이 생기기 쉬운",
                "adult": "자녀의 독립·거처를 함께 의논할 일이 생기기 쉬운", "senior": "자녀와 함께 모이거나 도움을 주고받을 일이 생기기 쉬운"},
    }
    KID_GO = {"young": "함께하는 시간을 달력에 먼저 정해 두세요.", "school": "진로 이야기는 먼저 들어 주고 함께 정하세요.",
              "adult": "독립·취업 준비는 응원하되 결정은 자녀에게 맡기세요.", "senior": "먼저 연락하고 함께 식사하는 날을 정하세요."}
    KID_CAU = {"young": ["돌봄 계획은 무리 없는 만큼만 잡으세요.", "아이 용품·돌봄 지출 한도를 정해 두세요."],
               "school": ["자녀 관련 지출은 상한을 미리 정하세요.", "진로를 부모 뜻대로 정하지 마세요."],
               "adult": ["경제적 도움은 한도를 정해 두세요.", "결혼·집 문제에 먼저 결론을 내리지 마세요.", "보증·대출 명의는 빌려주지 마세요."],
               "senior": ["상속·증여 이야기는 문서로 분명히 하세요.", "돈 도움은 노후 자금을 먼저 떼고 하세요."]}
    KID_REM = {"young": ["배우자·가족과 돌봄 역할을 나누세요.", "내 쉬는 시간을 먼저 정해 두세요."],
               "school": ["잔소리 대신 들어 주는 시간을 늘리세요.", "주 1회 함께하는 시간을 고정하세요."],
               "adult": ["의견은 한 번만 말하고 결정은 존중하세요.", "자주 연락하되 간섭은 줄이세요."],
               "senior": ["서운한 일은 쌓지 말고 짧게 말로 푸세요.", "먼저 안부를 묻는 날을 정해 두세요."]}

    def kids_adv(self, gz, sc, key, kind="year", year=None, st=None, age=None):
        c = self.c; kg = "식상" if c.gender == "F" else "관성"; st = st if st is not None else c.stars(sc)
        span = "해" if kind == "year" else "10년"
        age = age if age is not None else (c.age(year) if year else c.age(self.Y))
        sg = self.stage(age)
        arr = self.arrivals(gz); rels = c.relations_to_chart(*gz)
        kid_in = [(tg, f) for g, f, w, tg, ch in arr if g == kg]
        si_chung = c.time_known and any(k == "충" and p == "시" for k, p, _, _ in rels)
        si_hap = c.time_known and any(k in ("육합", "반합") and p == "시" for k, p, _, _ in rels)
        doshik = c.gender == "F" and any(tg == "편인" for g, f, w, tg, ch in arr) and c.gcount["식상"]
        br = ("chung" if si_chung else "doshik" if doshik else ("in_good" if kid_in[0][1] >= 0 else "in_bad") if kid_in else "hap" if si_hap else None)
        cond = PS.pick(["자녀가 있다면 ", "자녀가 있는 경우 "], c, key + "kc")
        if br: rs = f"{cond}{self.KID_EV[br][sg]} {josa(span, '이에요')}."
        elif st <= 2: rs = f"이 {josa(span, '는')} 내 기운이 먼저 지치기 쉬워 가까운 사람에게 날카로워지기 쉬워요."
        else: rs = f"자녀 쪽으로 큰 신호는 없는 {josa(span, '이에요')}."
        ca = PS.pick(self.KID_CAU[sg], c, key + "kca"); re_ = PS.pick(self.KID_REM[sg], c, key + "kre")
        if st >= 4: return AV.vd(st), f'{cond}{self.KID_GO[sg]} <b class="adv-c">조심</b> {ca}'
        if st == 3: return AV.vd(st), f'{rs if br else cond} <b class="adv-c">조심</b> {ca} <b class="adv-s">보완</b> {re_}'
        return AV.vd(st), f'{rs} {cond if not br else ""}<b class="adv-s">보완</b> {re_}'

    # ------------------------------------------------------------ 표
    def daeun_rows(self, t, n=4):
        c = self.c; out = ""
        ps = [p for p in c.daeun_periods() if p["y1"] > self.Y and p["a0"] <= 85][:n]
        cur = c.current_daeun(self.Y)
        sc_all = [self.tscore(t, p["gz"]) for p in ps]
        for p, sc in zip(ps, sc_all):
            k, x = self.adv(t, p["gz"], sc, "d" + p["gz"], kind="daeun", age=max(p["a0"], c.age(self.Y)))
            if t == "move":
                mp, _ = self.move_power(p["gz"]); x = f"<b>이동수 {'강' if mp >= 2 else '중' if mp >= 1 else '약'}.</b> " + x
            tag = "<b>현재.</b> " if cur and p["gz"] == cur["gz"] else ""
            out += (f'<tr{" class=hl" if tag else ""}><td>{p["a0"]}~{p["a1"]}</td><td>{p["y0"]}~{p["y1"]}</td><td class="serif">{p["gz"]}</td>'
                    f'<td class="small">{p["천간십신"]}/{p["지지십신"]}</td><td class="small">{tag}{k} {x}</td><td class="stars">{stars(c.stars(sc))}</td></tr>')
        return f'<table><tr><th style="width:10%">나이</th><th style="width:13%">연도</th><th style="width:8%">대운</th><th style="width:13%">십신</th><th>{KO[t]} 판정 · 할 일 · 조심/보완</th><th style="width:11%">{KO[t]}</th></tr>{out}</table>'

    def daeun_matrix(self, topics):
        """프리미엄: 대운 × 주제 별점 한 표 (주제마다 대운 표를 따로 두지 않아요)"""
        c = self.c; cur = c.current_daeun(self.Y)
        LB = dict(KO, love="애정")   # '결혼에 힘이 실리는 10년'처럼 시기로 읽히지 않게 애정으로 적어요
        ps = [p for p in c.daeun_periods() if p["y1"] > self.Y and p["a0"] <= 85][:4]
        ts = [t for t in topics if t in AREA or t in ("move", "kids")]
        head = "".join(f'<th style="width:8%">{LB[t]}</th>' for t in ts)
        rows = ""
        for p in ps:
            v = {t: self.tscore(t, p["gz"]) for t in ts}
            sv = {t: c.stars(v[t]) for t in ts}
            hi = max(ts, key=lambda t: (sv[t], v[t])); lo = min(ts, key=lambda t: (sv[t], v[t]))
            cells = "".join(f'<td class="stars" style="text-align:center">{sv[t]}</td>' for t in ts)
            tag = "<b>현재.</b> " if cur and p["gz"] == cur["gz"] else ""
            if sv[hi] == sv[lo]:   # verdict1116: 별이 모두 같으면 '힘이 실리고/조심'을 지어내지 않아요
                g0 = c.score(p["gz"])[0]; g0s = c.stars(g0)
                it = AV.period_advice(c, p["gz"], g0, "gen", key="mx" + p["gz"], max_items=2, scope="이 10년은", kind="daeun", star=g0s)
                txt = f"주제별 차이가 작은 10년이에요(모두 ★{sv[hi]}). {AV.vd(g0s)} {self._compose(it, g0s)}"
            else:
                k2, x2 = self.adv(lo, p["gz"], v[lo], "mn" + p["gz"], kind="daeun", age=max(p["a0"], c.age(self.Y)))
                low = "은 보완" if sv[lo] <= 2 else "은 상대적으로 낮아요"
                txt = f"<b>{LB[hi]}</b>(★{sv[hi]})에 힘이 실리고 <b>{LB[lo]}</b>(★{sv[lo]}){particle(LB[lo], '은')}{low[1:]} · {k2} {x2}"
            rows += (f'<tr{" class=hl" if tag else ""}><td>{p["gz"]}<br><span class="tiny">만 {p["a0"]}~{p["a1"]}세<br>{p["y0"]}~{p["y1"]}</span></td>{cells}'
                     f'<td class="small">{tag}{txt}</td></tr>')
        return (f'<h3>대운 × 주제 · 10년마다 어느 쪽에 힘이 실리나</h3><p class="small">숫자는 그 대운에서 주제별로 따로 본 별점(1~5)이에요. 별이 가장 높은 주제와 낮은 주제를 적고, 모두 같으면 차이가 작다고만 적었어요.</p>'
                f'<table><tr><th style="width:13%">대운</th>{head}<th>읽는 법</th></tr>{rows}</table>')

    def month_hint(self, t, y, sh=0, star=3):
        ms = [(a, gz) for a, b, gz, n in E.month_pillars(y, y + 1) if (a.year == y and n != "小寒") or (a.year == y + 1 and n == "小寒")]
        if len(ms) < 6: return ""
        yb = E.year_gz(y)[1]
        def ms_sc(gz):   # 그해 지지와 충이면 깎고 합이면 더해요(5년마다 같은 월 간지가 돌아와도 해마다 달라져요)
            v = self.tscore(t, gz)
            if frozenset((yb, gz[1])) in S.CHUNG: v -= 1.0
            if frozenset((yb, gz[1])) in S.YUKHAP: v += 0.5
            return v
        r = sorted(ms, key=lambda m: -ms_sc(m[1]))
        g = sorted(r[sh:sh + 2], key=lambda m: m[0]); b = r[-1 - sh]
        ml = lambda m: ("이듬해 " if m[0].year > y else "") + f"{m[0].month}월({m[1]})"
        if star >= 4:   # release1116: ★4-5 해는 조심을 한 번만(할 일 칸) 말하고 여기선 힘 쓸 달만
            return f"이 해 안에서는 {ml(g[0])}·{ml(g[1])}이 {KO[t]} 쪽으로 특히 나아요."
        if star <= 2:   # ★1-2 해는 좋은 달 문구를 빼요
            return f"이 해 안에서도 {ml(b)}{particle(ml(b), '은')} 특히 무리하지 마세요."
        return f"이 해 안에서는 {ml(g[0])}·{ml(g[1])}이 {KO[t]} 쪽으로 낫고, {ml(b)}{particle(ml(b), '은')} 무리하지 마세요."

    def year_rows(self, t):
        c = self.c; sc, st = self.ystars(t); out = ""
        best, worst = self.bw(t)
        used, whys, nrep = set(), {}, -1
        for y in self.years:
            gz = E.year_gz(y)
            for i in range(4):   # 같은 표 안에서 같은 조언(십신 이름만 다른 것 포함)이 되풀이되지 않게 다른 문장을 골라요
                k, x = self.adv(t, gz, sc[y], str(y) + ("" if not i else "r%d" % i), year=y, star=st[y])
                if _norm(x) not in used: break
            w, rest = _why_split(x)
            if t not in ("kids", "move") and (_norm(x) in used or (w and _norm(w) in whys)):
                # 이유가 앞 해와 같으면 같다고 밝히고, 그해 안의 좋은 달·조심할 달로 그해만의 내용을 붙여요
                py = whys.get(_norm(w)) if w else None
                if py and st[py] != st[y]: py = None   # verdict1116: 별이 다른 해를 '같은 해'로 잇지 않아요
                nrep += 1
                bt = c.tg(gz[1], True); brole = NT.ROLE[c.fav[BR_ELK[gz[1]]]]
                br = f"지지 {gz[1]}{particle(gz[1], '는')} {bt}({TG_THEME[bt][0]})로 이 사주엔 {josa(brole, '이에요')}. "
                same = [f"{py}년과 같은 이유가 이어지는 해예요. 다만 ", f"{py}년과 같은 갈래의 해예요. 다만 ", f"{py}년의 흐름이 한 번 더 와요. 다만 "][nrep % 3]
                base = ((same + br) if py else "") + (rest or x)
                for sh in range(3):
                    x = base + " " + self.month_hint(t, y, sh, st[y])
                    if _norm(x) not in used: break
            if w and _norm(w) not in whys: whys[_norm(w)] = y
            used.add(_norm(x))
            sig = self.signal(t, gz)
            if t == "move":
                mp, _ = self.move_power(gz)
                sig = f"이동수 {'강' if mp >= 2 else '중' if mp >= 1 else '약'} · " + sig + f"<br><span class=\"tiny\">피할 방향 {SAMSAL[gz[1]]}(삼살)·{DAEJANG[gz[1]]}(대장군)</span>"
            tag = "<b class=\"adv-s\">▲ 힘이 실리는 해</b><br>" if y in best else "<b class=\"adv-c\">▼ 조심할 해</b><br>" if y in worst else ""
            out += (f'<tr{" class=hl" if st[y] >= 4 else ""}><td><b>{y}</b><br><span class="serif">{gz}</span><br><span class="tiny">만 {c.age(y)}세</span></td><td class="small">{tag}{sig}</td>'
                    f'<td class="small">{k} {x}</td><td class="stars">{stars(st[y])}</td></tr>')
        return f'<table><tr><th style="width:11%">연도</th><th style="width:19%">{KO[t]} 신호</th><th>판정 · 할 일 · 조심/보완</th><th style="width:11%">{KO[t]}</th></tr>{out}</table>'

    def bw(self, t):
        """verdict1116: 힘이 실리는 해 = ★4 이상 중 상위 2, 조심할 해 = ★2 이하 중 하위 2 (별과 어긋나지 않게)"""
        sc, st = self.ystars(t); order = sorted(self.years, key=lambda y: -sc[y])
        return sorted([y for y in order[:2] if st[y] >= 4]), sorted([y for y in order[-2:] if st[y] <= 2])

    def best_worst(self, t):
        c = self.c; sc, st = self.ystars(t)
        best, worst = self.bw(t)
        def why(y):
            gz = E.year_gz(y); k, x = self.adv(t, gz, sc[y], "bw" + str(y), year=y, star=st[y])
            return f"{k} {x}"
        b = "".join(f"<li><b>{y} {E.year_gz(y)} {stars(st[y])}</b>: {why(y)}</li>" for y in best) or "<li>★4 이상인 해가 없어요.</li>"
        w = "".join(f"<li><b>{y} {E.year_gz(y)} {stars(st[y])}</b>: {why(y)}</li>" for y in worst) or "<li>★2 이하인 해가 없어요.</li>"
        return (f'<div class="two" style="margin-top:2.6mm"><div class="box" style="margin:0"><h3 style="margin-top:0">{KO[t]} · 힘이 실리는 해</h3><ul class="small" style="margin:0">{b}</ul></div>'
                f'<div class="box" style="margin:0"><h3 style="margin-top:0">{KO[t]} · 조심할 해</h3><ul class="small" style="margin:0">{w}</ul></div></div>'), best, worst

    # ------------------------------------------------------------ 원국 근거
    def natal(self, t):
        c = self.c; rep = self.rep; G = c.gel
        if t == "money":   # 지금 대운·내년 조언 상자는 아래 표와 겹쳐서 빼요
            return re.sub(r'<div class="advbox small"><b class="gold">재물 · 지금 조심할 점과 보완할 점</b><ul>.*?</ul></div>', "", rep.money_paras(), flags=re.S), self.money_one()
        if t == "job":
            J = rep.jlh_parts()
            gs = []
            for g in ("관성", "인성", "식상", "비겁", "재성"):
                n = c.gcount[g]
                txt = (GROUP_STRONG[g].split(". ")[0].rstrip(".") if n >= 2 else GROUP_ABSENT[g].split(". ")[0].rstrip(".") if n == 0 else
                       f"{GROUP_MEAN[g]}의 기운이 알맞게 있어요")
                gs.append(f'<tr><td><b>{g}</b> {n}</td><td class="small">{NT.ROLE[c.fav[G[g]]]} {el_full(G[g])}</td><td class="small">{txt}.</td></tr>')
            html = (f'<table><tr><th style="width:33%">{JB.t("p5_th")}</th><th>이유</th></tr>{J["rows"]}</table>'
                    f'<h3>일하는 방식 · 십신 구조</h3><table><tr><th style="width:13%">십신</th><th style="width:22%">이 사주에서</th><th>뜻</th></tr>{"".join(gs)}</table>'
                    f'<p class="small" style="margin-top:2mm"><b>{JB.t("move_label")}</b> · {J["mv"]}</p>')
            one = f"{c.gyeok}에 강한 십신은 {J['top']}이라 {J['picks'][0][0].split(' · ')[0]} 같은 길이 맞고, 용신 {el_full(c.yong)}의 분야에서 운이 살아나요."
            return html, one
        if t == "biz":
            return self.biz_natal()
        if t == "love":
            J = rep.jlh_parts()
            sp = c.tg(c.db, True)
            se = "관성" if c.gender == "F" else "재성"
            html = (f'<p>{J["para"]}</p><ul class="small">{"".join(J["lis"][:2])}</ul>'
                    f'<p class="small">배우자 별({se}, {el_full(G[se])})은 이 사주에서 <b>{NT.ROLE[c.fav[G[se]]]}</b>이에요. '
                    + ({2: "배우자 별이 나를 살리는 기운이라, 좋은 관계가 운 전체를 받쳐 줘요.", 1: "배우자 별이 나를 돕는 쪽이라, 관계가 편할수록 일과 돈도 함께 풀려요.",
                        0: "배우자 별이 중립이라, 관계는 운보다 두 사람의 습관과 대화가 좌우해요.", -1: "배우자 별이 조금 부담이 되는 기운이라, 관계에 기대를 너무 많이 걸기보다 각자의 영역을 지키는 편이 편해요.",
                        -2: "배우자 별이 무거운 기운이라, 관계가 나를 지치게 하지 않도록 거리와 속도를 스스로 조절하는 것이 중요해요."}[c.fav[G[se]]])
                    + ' 이 장은 결혼 시기를 점치지 않아요. 해마다 관계의 온도가 어떤지, 언제 부딪히기 쉽고 언제 다지기 좋은지를 봐요.</p>')
            one = f"배우자궁(일지)은 {sp}, {SPOUSE_PALACE[sp].split('. ')[0].split('있어 ')[-1]}."
            return html, one
        if t == "move":
            return self.move_natal()
        if t == "health":
            J = rep.jlh_parts()
            rows = ""
            for e in ("목", "화", "토", "금", "수"):
                rows += (f'<tr{" class=hl" if e in (J["hi"], J["lo"]) else ""}><td class="el-{e}"><b>{EL_WORD[e]}({e})</b></td><td>{c.cnt[e]}개 · {c.wt[e]}</td>'
                         f'<td class="small">{NT.ROLE[c.fav[e]]}</td><td class="small">{ELEM[e]["organs"]}</td></tr>')
            html = (f'<table><tr><th style="width:14%">오행</th><th style="width:15%">글자·가중</th><th style="width:15%">역할</th><th>전통 배속(관리 포인트)</th></tr>{rows}</table>'
                    f'<ul class="small" style="margin-top:2mm">{"".join(J["hl"])}</ul><p class="small">{J["hn"].replace("__PALM_HEALTH__", "")}</p>')
            one = f"가장 강한 {EL_WORD[J['hi']]}({J['hi']}), 가장 약한 {EL_WORD[J['lo']]}({J['lo']}) 쪽이 관리 포인트예요({HEALTH_LACK[J['lo']].split('.')[0].split('·')[0]} 쪽)."
            return html, one
        if t == "kids":
            return self.kids_natal()
        return "", ""

    def money_one(self):
        c = self.c; n = c.gcount["재성"]
        return (f"재성 {n}개 · {c.st_label.split('(')[0]} · 재성은 이 사주에서 {NT.ROLE[c.fav[c.gel['재성']]]}이에요.")

    def biz_natal(self):
        c = self.c; G = c.gel; rows = []
        nj, ns, nb, nk = c.gcount["재성"], c.gcount["식상"], c.gcount["비겁"], c.gcount["관성"]
        tc = c.r["ten_gods_count"]; pj, jj = tc.get("편재", 0), tc.get("정재", 0)
        def row(lab, ok, val, txt): rows.append(f'<tr><td><b>{lab}</b></td><td style="text-align:center">{ok}</td><td class="small">{val}</td><td class="small">{txt}</td></tr>')
        row("돈을 보는 눈(재성)", "○" if nj >= 1 and c.fav[G["재성"]] >= 0 else "△" if nj or c.hidden_groups["재성"] else "✕", f"{nj}개 · 편재 {pj}·정재 {jj}",
            "편재가 있어 판을 키우고 거래를 넓히는 감각이 있어요." if pj else "정재 중심이라 큰 판보다 고정 매출을 차곡차곡 쌓는 장사가 맞아요." if jj else "재성이 겉에 없어 돈 계산은 숫자로 관리하는 습관부터 만드세요.")
        row("팔 거리(식상)", "○" if ns >= 1 and c.fav[G["식상"]] >= 0 else "△" if ns else "✕", f"{ns}개 · {NT.ROLE[c.fav[G['식상']]]}",
            "상품·기술·말솜씨가 매출로 이어지는 식신생재의 바탕이 있어요." if ns and nj else "재능은 있지만 돈으로 바꾸는 통로(재성)를 따로 만들어야 해요." if ns else "팔 거리를 내 재능보다 좋은 상품·사람에게서 찾는 쪽이 맞아요.")
        row("버티는 힘(강약)", "○" if c.strong else "△" if c.neutral else "✕", c.st_label.split("(")[0],
            "돈과 일을 감당할 힘이 있어 확장도 버틸 수 있어요. 대신 한 번에 크게 거는 것이 가장 큰 위험이에요." if c.strong else "감당력이 알맞아 단계적으로 키우면 돼요." if c.neutral else "감당력보다 일이 커지기 쉬워, 작게 시작해 검증한 뒤 키우는 방식이 맞아요.")
        row("동업·경쟁(비겁)", "△" if nb >= 3 else "○", f"{nb}개 · {NT.ROLE[c.fav[G['비겁']]]}",
            "비겁이 많아 동업·지분 문제로 몫이 새기 쉬워요. 수익 배분은 처음부터 계약서로." if nb >= 3 else "경쟁 기운이 지나치지 않아 협업이 무난해요." if nb else "내 편이 적어 혼자 다 떠안기 쉬우니, 믿을 실무 파트너 한 명이 중요해요.")
        row("신용·규정(관성)", "○" if nk and c.fav[G["관성"]] >= 0 else "△", f"{nk}개 · {NT.ROLE[c.fav[G['관성']]]}",
            "신용과 절차를 지키는 힘이 있어 기관·큰 거래처와 일하기 좋아요." if nk and c.fav[G["관성"]] >= 0 else "세무·인허가·계약 같은 관리 일이 부담이 되기 쉬워 전문가에게 맡기는 편이 나아요." if nk else "규칙에 얽매이지 않는 대신 세무·계약 관리는 처음부터 체계를 만들어 두세요.")
        if "역마" in c.sinsal: row("움직임(역마)", "○", "원국에 역마", "움직일수록 기회가 오는 형이라 영업·유통·온라인처럼 넓게 뛰는 일이 맞아요.")
        cg = JB._CAREER_GYEOK.get("사업자", {}).get(c.gyeok)
        top = max(c.gcount, key=lambda g: (c.gcount[g], c.gw[g]))
        cr = JB._CAREER_GROUP.get("사업자", {}).get(top)
        fields = []
        if cg: fields.append(f"<li><b>{cg[0]}</b>: {cg[1]}</li>")
        if cr and (not cg or cr[0] != cg[0]): fields.append(f"<li><b>{cr[0]}</b>: {cr[1]}</li>")
        fields.append(f"<li><b>{ELEM[c.yong]['careers'].replace('·', ' · ')}</b>: 용신 {el_full(c.yong)}의 업종이라 할수록 운이 살아나요.</li>")
        lead = ("지금 하는 사업을 이 사주의 구조와 맞춰 봤어요." if JB.CUR["job"] == "사업자" else "창업이나 부업을 생각한다면, 이 사주가 장사·사업에 어떤 체질인지부터 봐요.")
        ok = sum(r.count("○") for r in rows)
        html = (f'<p class="small">{lead}</p><table><tr><th style="width:22%">항목</th><th style="width:7%">체질</th><th style="width:17%">원국</th><th>풀이</th></tr>{"".join(rows)}</table>'
                f'<h3>맞는 사업 분야</h3><ul class="small">{"".join(fields[:3])}</ul>')
        one = f"사업 체질 점검 {len(rows)}항목 중 ○ {ok}개 · " + ("편재형(판을 키우는 장사)" if pj > jj else "정재형(고정 매출을 쌓는 장사)" if jj else "재성 숨은 형(운에서 재성이 올 때 커지는 장사)")
        return html, one

    def move_natal(self):
        c = self.c; G = c.gel; li = []
        ym = c.sinsal.get("역마")
        li.append(f"<li><b>원국의 이동성</b>: " + (f"역마가 {'·'.join(POS_NAME[p] for p, _ in ym)}에 있어 움직이며 기회를 만드는 형이에요. 한곳에 오래 묶이면 답답함을 느끼기 쉬워요." if ym else
                                             "원국에 역마가 없어 자주 옮기기보다 한곳에 뿌리를 내릴수록 안정되는 형이에요. 이사는 운에서 충·역마가 들 때 몰려 와요.") + "</li>")
        ch = [x for x in c.r["relations"] if "충" in x and "천간" not in x]
        dpos = [x for x in ch if "일" in x.split(" ")[0]]
        li.append("<li><b>생활 터전(일지)</b>: " + (f"원국 안에서 일지가 충을 받고 있어(" + esc_(dpos[0].split(' ')[1]) + ") 생활 터전이 자주 바뀌기 쉬운 구조예요. 이사할 때마다 조건을 글로 비교해 두면 손해가 줄어요." if dpos else
                                                 f"일지 {c.db}가 원국 안에서 충을 받지 않아 생활 터전이 안정된 편이에요.") + "</li>")
        yd, hd, gd = DIR[c.yong], DIR[c.hee], DIR[c.gi]
        li.append(f"<li><b>좋은 방향</b>: 용신 {el_full(c.yong)}의 <b>{yd}</b>, 희신 {el_full(c.hee)}의 <b>{hd}</b>이에요. 지금 집에서 이 방향으로 옮기거나, 같은 동네라도 집의 큰 창·현관이 이쪽을 향하면 좋아요.</li>")
        li.append(f"<li><b>줄일 방향</b>: 기신 {el_full(c.gi)}의 {gd}{particle(gd, '은')} 꼭 피할 필요는 없지만, 같은 조건이면 {yd}·{hd}{particle(hd, '을')} 고르세요.</li>")
        house = {"목": "나무가 보이는 집, 공원·숲길이 가까운 동네", "화": "해가 잘 드는 남향, 밝고 활기찬 동네", "토": "지대가 안정된 평지, 생활 편의가 모인 동네",
                 "금": "깔끔하게 정돈된 신축·단지형, 서쪽 전망", "수": "물(강·호수·하천)이 가까운 동네, 조용한 주거지"}
        li.append(f"<li><b>맞는 집</b>: {house[c.yong]}. 희신 {c.hee} 기운으로는 {house[c.hee].split(', ')[0]}도 좋아요.</li>")
        li.append(f"<li><b>해마다 피하는 방향</b>: 전통 이사 방위로는 그해의 삼살·대장군 방향을 피해요. 아래 표의 해마다 피할 방향과 내 좋은 방향({yd}·{hd})이 겹치는 해에는 방향보다 실제 계약 조건을 먼저 따져 보세요. 방위는 전통 참고이며 실행 판정은 아래 별점 기준이에요.</li>")
        html = f'<ul class="small">{"".join(li)}</ul>'
        one = f"좋은 방향은 {yd}·{hd}" + (", 원국에 역마가 있어 움직이며 기회를 만드는 형" if ym else ", 한곳에 뿌리를 내릴수록 안정되는 형") + "이에요."
        return html, one

    def kids_natal(self):
        c = self.c; G = c.gel; kg = "식상" if c.gender == "F" else "관성"
        n = c.gcount[kg]; hid = c.hidden_groups[kg]
        li = [f"<li><b>자녀의 별</b>: {'여성' if c.gender == 'F' else '남성'}에게 자녀는 {kg}, 곧 {V.elw(G[kg])} 기운이에요. 원국에 {n}개{', 지장간에 ' + '·'.join(hid) + ' 숨어 있어요' if hid else ''}. "
              + ("자녀의 별이 넉넉해 자녀와 마음을 주고받는 일이 삶의 큰 부분이에요." if n >= 2 else "자녀의 별이 알맞게 있어요." if n == 1 else "자녀의 별이 겉에 없어, 운에서 자녀의 별이 들어올 때 자녀 일이 크게 드러나요.")
              + f" 이 사주에서 {kg}{particle(kg, '은')} <b>{NT.ROLE[c.fav[G[kg]]]}</b>이라 " + ({2: "자녀가 나를 살리는 기운이에요. 자녀와 함께할수록 힘이 나요.", 1: "자녀가 나를 돕는 쪽이에요.", 0: "자녀와의 관계는 습관과 대화가 좌우해요.",
                                                                             -1: "자녀 일에 마음을 너무 쏟으면 내가 먼저 지치기 쉬워요.", -2: "자녀 걱정이 쌓이기 쉬우니, 믿고 맡기는 연습이 중요해요."}[c.fav[G[kg]]]) + "</li>"]
        if c.time_known:
            hp = c.P["시"]; kid = [x for x in (TG_GROUP[hp["stem_tengod"]], TG_GROUP[hp["branch_tengod"]]) if x == kg]
            r = S.pair_relations(hp["gz"][1], c.db)
            rel = ("일지와 합해 자녀와 정이 깊은 배치예요." if any(x.startswith("육합") or x.startswith("삼합 반합") for x in r) else
                   "일지와 충해 생활 방식이 달라 각자의 공간을 존중할수록 사이가 좋아요." if "충" in r else
                   "일지와 원진이라 사소한 서운함이 쌓이기 쉬워, 그날 일은 그날 푸는 습관이 좋아요." if "원진" in r else "일지와 부딪히지 않아 무난한 배치예요.")
            li.append(f"<li><b>자녀궁(시주) {hp['gz']}</b>: 십신으로 {hp['stem_tengod']}·{hp['branch_tengod']}이에요. " + ("자녀의 별이 자녀궁에 앉아 자녀 인연이 뚜렷해요. " if kid else "자녀궁에 자녀의 별이 직접 앉지는 않아, 자녀의 별이 들어오는 해에 자녀 일이 드러나요. ") + f"시지 {hp['gz'][1]}{particle(hp['gz'][1], '는')} {rel}</li>")
        else:
            li.append("<li><b>자녀궁(시주)</b>: 출생 시각을 몰라 자녀궁은 보지 않았어요. 자녀의 별(십신)과 운의 흐름으로만 봤어요.</li>")
        style = {"식상": "표현을 받아 주고 재능을 키워 주는", "관성": "규칙과 책임을 가르쳐 주는", "인성": "품어 주고 기다려 주는", "비겁": "친구처럼 대등하게 대하는", "재성": "현실 감각을 길러 주는"}
        yg = c.el_group[c.yong]
        if c.age(self.Y) < 50:
            li.append(f"<li><b>나에게 맞는 양육·관계 방식</b>: 자녀가 있다면 용신이 {yg}이라 {style[yg]} 부모일 때 서로 편해요. {STEM[c.dm]['ko']} 일간의 약점인 {STEM[c.dm]['weak']}{particle(STEM[c.dm]['weak'], '이')} 자녀 앞에서 드러나지 않게 조심하세요.</li>")
        else:   # verdict1116: 50대 이후는 성인 자녀와의 관계로 써요(자녀 유무는 조건문)
            st2 = {"식상": "이야기를 들어 주고 표현을 받아 주는", "관성": "원칙은 지키되 결정은 맡기는", "인성": "믿고 기다려 주는", "비겁": "친구처럼 대등하게 대하는", "재성": "도움의 선을 분명히 하는"}
            li.append(f"<li><b>자녀와 맞는 관계 방식</b>: 자녀가 있다면 용신이 {yg}이라 {st2[yg]} 쪽일 때 서로 편해요. {STEM[c.dm]['ko']} 일간의 약점인 {STEM[c.dm]['weak']}{particle(STEM[c.dm]['weak'], '이')} 가족 앞에서 드러나지 않게 조심하세요.</li>")
        html = f'<ul class="small">{"".join(li)}</ul>'
        one = f"자녀의 별 {kg} {n}개, 이 사주에서 {NT.ROLE[c.fav[G[kg]]]}" + (f" · 자녀궁 {c.P['시']['gz']}" if c.time_known else " · 시각 미상") + "."
        return html, one

    # ------------------------------------------------------------ 실천 체크
    def checklist(self, t, best, worst):
        """verdict1116: 표의 판정과 같은 기준(★4 이상 = 힘이 실리는 해, ★2 이하 = 조심할 해)"""
        c = self.c; Y = ELEM[c.yong]; out = []
        b = "·".join(map(str, best)); w = "·".join(map(str, worst))
        if t == "money":
            out += [(f"큰돈(계약·투자·대출)은 {b}년에 맞추고" if b else "★4 이상인 해가 없으니 큰돈(계약·투자·대출)은 꼭 필요한 것만 하고") + (f", {w}년에는 현금 비중을 늘리기" if w else ", 해마다 현금 비중을 지키기"),
                    {"직장인": "월급날", "사업자": "매출이 들어오는 날", "프리랜서": "작업 대금이 들어오는 날", "주부": "생활비가 들어오는 날", "학생": "용돈·아르바이트비가 들어오는 날",
                     "무직": "돈이 들어오는 날"}.get(JB.CUR["job"], "수입이 들어오는 날") + " 자동이체로 저축부터 떼기",
                    f"돈 결정 전 하루 묵히기" + (f": 특히 {w}년에는 꼭" if w else "")]
        elif t == "job":
            out += [(f"지원·이동·승부는 {b}년에" if b else "★4 이상인 해가 없으니 지원·이동은 조건이 확실할 때만") + (f", {w}년에는 자격·실력 쌓기" if w else ""), f"맡은 일의 범위와 기한을 문서로 남기기", f"용신 {c.yong}의 분야({Y['careers'].split('·')[0]}) 공부 하나 이어 가기"]
        elif t == "biz":
            out += [(f"확장·신규 투자는 {b}년에 맞추고" if b else "★4 이상인 해가 없으니 확장은 작게 나눠 하고") + (f", {w}년에는 운영자금 6개월치 확보" if w else ", 운영자금 6개월치는 늘 확보"), "거래별 마진·미수금을 매달 표로 점검", "동업·지분은 시작 전에 계약서로"]
        elif t == "love":
            out += [(f"{b}년처럼 관계 온도가 높은 해에는 함께하는 계획(여행·집·저축)을 같이 세우기" if b else "함께하는 계획(여행·집·저축)은 서두르지 말고 같이 세우기"), (f"{w}년에는 중요한 대화를 피곤한 밤에 하지 않기" if w else "중요한 대화는 피곤한 밤에 하지 않기"), "서운한 건 그날 말로 풀기"]
        elif t == "move":
            out += [(f"이사·매매는 '해도 됨'인 {b}년에" if b else "'해도 됨'인 해가 없으니 이사·매매는 꼭 필요할 때만, 비교 후") + (f", '미룸'인 {w}년에는 연장·수리로" if w else ""), f"계약 전 그해 피할 방향(삼살·대장군)과 내 좋은 방향({DIR[c.yong]}·{DIR[c.hee]}) 확인", "전세·대출 만기를 달력에 적어 두기"]
        elif t == "health":
            out += [(f"{w}년에는 정기 검진 날짜를 먼저 잡기" if w else "해마다 정기 검진 날짜를 먼저 잡기"), f"약한 {EL_WORD[min(c.wt, key=c.wt.get)]} 기운 채우기: {ELEM[min(c.wt, key=c.wt.get)]['life'].split(', ')[0]}", "잠자는 시간 고정하기"]
        elif t == "kids":
            sg = self.stage(c.age(self.Y)); bb = f"{b}년처럼 흐름이 좋은 해에" if b else "서두르지 말고"
            out += {"young": [f"자녀 계획이 있거나 어린 자녀가 있다면 큰 결정은 {bb} 정하기", "배우자·가족과 돌봄 역할을 미리 나누기", "내 쉬는 시간을 먼저 달력에 적기"],
                    "school": [f"자녀가 있다면 그해 나이 단계에 맞는 큰 결정은 {bb} 함께 의논하기", (f"{w}년에는 " if w else "") + "잔소리보다 들어 주는 시간 늘리기", "자녀 관련 지출 상한을 미리 정하기"],
                    "adult": [f"성인 자녀가 있다면 독립·결혼 같은 큰일은 {bb} 함께 의논하기", (f"{w}년에는 " if w else "") + "경제적 도움 요청에 바로 답하지 말고 하루 묵히기", "도움은 한도를 정해 두기"],
                    "senior": [f"자녀가 있다면 가족 모임·큰 의논은 {bb} 잡기", (f"{w}년에는 " if w else "") + "서운한 일을 쌓지 말고 짧게 말로 풀기", "상속·증여는 문서로 미리 정리하기"]}[sg]
        return "".join(f"<li>{x}</li>" for x in out[:3])

    # ------------------------------------------------------------ 섹션 조립
    def section(self, t, compact=False):
        c = self.c; rep = self.rep
        if t == "biz":
            orig = JB.CUR["job"]; JB.apply("사업자")
            try: return self._section(t, compact)
            finally: JB.apply(orig)
        return self._section(t, compact)

    def _section(self, t, compact=False):
        c = self.c; rep = self.rep
        natal, one = self.natal(t)
        sc, st = self.ystars(t)
        best, worst = self.bw(t)
        cur = c.current_daeun(self.Y)
        cur_t = ""
        if cur:
            csc = self.tscore(t, cur["gz"]); k, x = self.adv(t, cur["gz"], csc, "cur" + cur["gz"], kind="daeun", age=c.age(self.Y))
            cur_t = f"지금 {cur['gz']} 대운은 {KO[t]} 쪽으로 {stars(c.stars(csc))}예요. {k} {x}"
        sub = {"money": "재성·식상·비겁의 구조와 재물 창고 · 주제 별점은 돈만 따로 본 값이라 종합 별점과 다를 수 있어요",
               "job": "격국·관성·인성·식상 · 일하는 방식과 자리의 흐름", "biz": "재성·식상·비겁·강약으로 보는 사업 체질과 확장의 때",
               "love": "배우자궁(일지)·배우자 별 · 결혼 시기는 점치지 않아요", "move": "충·역마로 보는 이동수 · 용신 방향 · 해마다 피할 방향",
               "health": "오행의 강약과 충 · 전통 배속에 따른 관리 포인트이며 의학적 진단이 아니에요", "kids": "자녀의 별(여성 식상·남성 관성)과 자녀궁(시주) · 자녀가 있는지 모르는 채로 썼어요. 자녀가 없다면 아끼는 아랫사람과의 인연으로 읽으세요"}[t]
        keys = [f"<b>타고난 바탕</b> · {one}",
                f"<b>2026~2035</b> · " + (f"힘이 실리는 해(★4 이상)는 {'·'.join(map(str, best))}년" if best else "★4 이상인 해는 없어요") + ", "
                + (f"조심할 해(★2 이하)는 {'·'.join(map(str, worst))}년이에요." if worst else "★2 이하인 해도 없어요."),
                f"<b>지금</b> · {cur_t}" if cur_t else ""]
        h = f"""<!--T:{t}--><div class="rule"></div>
 <h2><span class="no">{rep.nxt()}</span>{"배우자 · 가족 관계" if t == "love" and c.age(self.Y) >= 60 else TITLE[t]}</h2>
 <div class="sub">{sub}</div>
 <div class="box dark small"><span class="gold">한눈에</span><br>{'<br>'.join(k for k in keys if k)}</div>
 <h3>타고난 바탕</h3>
 {natal}
 {"" if compact else "<h3>10년 단위 흐름 · 대운</h3>" + self.daeun_rows(t)}
 <h3>2026~2035 해마다 · {KO[t]}</h3>
 {self.year_rows(t)}
 <h3>실천 체크</h3><ul class="small">{self.checklist(t, best, worst)}</ul><!--/T-->"""
        h = re.sub(r"([가-힣])\.\.(?!\.)", r"\1.", h)   # 이어 붙인 문장 끝의 마침표 겹침 정리
        if t == "kids":
            h = h.replace('<h3>타고난 바탕</h3>', '<h3>타고난 바탕</h3><p class="tiny">아래 관계 풀이는 자녀가 있다면 해당해요. 자녀 유무·나이·계획은 사주로 단정하지 않아요.</p>')
        if t == "love":
            h = h.replace('<h3>타고난 바탕</h3>', '<h3>타고난 바탕</h3><p class="tiny">배우자가 있다면 부부 관계로, 없다면 가까운 관계의 성향으로 읽으세요. 결혼 여부나 시기를 단정하지 않아요.</p>')
        return h.replace("2026~2035", f"{self.years[0]}~{self.years[-1]}")


def esc_(s):
    import html
    return html.escape(str(s))
