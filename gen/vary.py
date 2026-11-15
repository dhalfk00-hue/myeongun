# -*- coding: utf-8 -*-
"""q1113: 감정서의 '모두에게 똑같던 틀 문장'을 이 사주의 특징으로 고르는 문구 모음.

무작위가 아니라 사주 특징(용신·기신 그룹, 재물 구조, 배우자궁 십신, 달마다의 용신/충 여부 …)으로 골라요.
같은 입력이면 늘 같은 문장이 나와요.
"""
from texts import EL_WORD, TG_GROUP, POS_NAME
from engine import STEM_ELK, BR_ELK
from josa import josa, particle
import persona as PS

ROLE_SHORT = {2: "용신", 1: "희신", 0: "", -1: "구신", -2: "기신"}


def elw(e):
    return f"{EL_WORD[e]}({e})"


# ------------------------------------------------------------------ 달의 이유
def month_reason(c, gz, good=True):
    """그 달이 좋은/나쁜 이유를 명사구로: '용신 불(화)의 달', '일지와 충하는 달' …"""
    s, b = gz
    fs, fb = c.fav[STEM_ELK[s]], c.fav[BR_ELK[b]]
    rels = c.relations_to_chart(s, b)
    if good:
        if max(fs, fb) >= 1:
            e = BR_ELK[b] if fb >= fs else STEM_ELK[s]
            return f"{ROLE_SHORT[max(fs, fb)]} {elw(e)}의 달"
        for k, pos, det, el in rels:
            if k in ("육합", "반합") and pos in ("일", "월"):
                return f"{POS_NAME[pos]}와 합하는 달"
        return "부딪히는 글자가 없는 달"
    for k, pos, det, el in rels:
        if k == "충" and pos in ("일", "월"):
            return f"{POS_NAME[pos]}와 충하는 달"
    if min(fs, fb) <= -1:
        e = BR_ELK[b] if fb <= fs else STEM_ELK[s]
        return f"{ROLE_SHORT[min(fs, fb)]} {elw(e)}의 달"
    for k, pos, det, el in rels:
        if k in ("형", "원진", "해", "파") and pos in ("일", "월"):
            return f"{POS_NAME[pos]}와 {k}이 걸리는 달"
    return "기운이 약한 달"


def _join_months(items):
    """[('5월(午)', '용신 불(화)의 달'), …] → '5월(午)은 용신 불(화)의 달, 9월(酉)은 …'  (이유가 같으면 합쳐요)"""
    if len(items) == 2 and items[0][1] == items[1][1]:
        return f"{items[0][0]}과 {josa(items[1][0], '은')} {items[0][1]}"
    return ", ".join(f"{josa(m, '은')} {r}" for m, r in items)


def months_phrase(c, good, bad, style=0, y=None, star=3):
    # tier1115: 그해 운의 마지막 달(소한~입춘 전)은 다음 해 1월이라 '이듬해 1월'로 적어요
    # release1116: 별이 판정을 정해요. ★1-2 해는 좋은 달 문구를 빼고 조심할 달만, ★4-5 해는 힘 쓸 달만 적어요(조심은 할 일 상자 하나로)
    ml = lambda m: ("이듬해 " if y is not None and m[0].year > y else "") + f"{m[0].month}월"
    G = [(f"{ml(m)}({m[2]})", month_reason(c, m[2], True)) for m in good]
    B = [(ml(m), month_reason(c, m[2], False)) for m in bad]
    g, b = _join_months(G), _join_months(B)
    if star <= 2:
        bm = "·".join(m for m, _ in B)
        return [f"{b}이라 이 해 안에서도 특히 큰 결정은 미루는 게 좋아요. 다른 달도 넓히기보다 지키는 쪽으로 보세요.",
                f"{b}이라 계약·지출을 특히 줄일 달이에요. 나머지 달도 크게 벌이기보다 정리하는 쪽이 맞아요.",
                f"{bm}에는 특히 큰 결정을 피하세요({'·'.join(dict.fromkeys(r for _, r in B))}). 다른 달도 지키는 쪽으로 보세요."][style % 3]
    if star >= 4:
        gm = "·".join(m for m, _ in G)
        return [f"{g}이라 이 해 안에서도 특히 힘을 실어 볼 만해요.",
                f"{g}이라 중요한 일정을 이 달에 맞추면 좋아요.",
                f"중요한 일은 {gm}에 잡으세요({'·'.join(dict.fromkeys(r for _, r in G))})."][style % 3]
    if style == 1:
        return f"{g}이라 움직이는 게 좋고, {b}이라 큰 결정은 미루는 게 좋아요."
    if style == 2:
        gs = "·".join(m for m, _ in G); bs = "·".join(m for m, _ in B)
        gr = "·".join(dict.fromkeys(r.replace("의 달", "").replace("하는 달", "").replace(" 달", "") for _, r in G))
        br = "·".join(dict.fromkeys(r.replace("의 달", "").replace("하는 달", "").replace(" 달", "") for _, r in B))
        return f"중요한 일은 {gs}에 잡고({gr}), {bs}에는 큰 결정을 피하세요({br})."
    return f"{g}이라 움직이기 좋고, {b}이라 큰 결정은 피하세요."


# ------------------------------------------------------------------ 기신 그룹별 '조심할 것'
GI_CARE = {"비겁": "모임·경조사 지출과 돈 거래", "식상": "말실수와 과로", "재성": "무리한 지출과 욕심",
           "관성": "과로와 책임 떠안기", "인성": "미루는 습관과 결정 지연"}
GI_CARE2 = {"비겁": "지출과 사람 문제", "식상": "건강과 말", "재성": "지출과 건강", "관성": "건강과 일의 양", "인성": "실행과 건강"}


def gi_care(c, short=False):
    g = c.el_group[c.gi]
    return (GI_CARE2 if short else GI_CARE)[g]


# ------------------------------------------------------------------ 기간 묶음(도약기·안정기·지키는 시기)의 주제 십신
def run_group(rep, ys):
    from collections import Counter
    c = rep.c
    cnt = Counter()
    import engine as E
    for y in ys:
        p = PS.P(c, E.year_gz(y), rep.ysc[y], "year", y)
        cnt[p.g] += 2; cnt[p.og] += 1
    return cnt.most_common(1)[0][0]


PHASE_DECADE = {
 "up": {"비겁": "내 편과 추진력이 붙는 때라 계획을 실행하되 독단·과로는 금물",
        "식상": "재능과 결과물을 내보일 때라 실행하되 말과 과로를 조심",
        "재성": "돈과 기회가 보이는 때라 실행하되 한 번에 크게 거는 과욕은 금물",
        "관성": "자리와 인정이 따라오는 때라 맡을 일은 맡되 책임을 무리하게 늘리지 않기",
        "인성": "배움·문서·도움이 받쳐 주는 때라 자격과 계약을 밀되 준비만 길어지지 않게"},
 "mid": {"비겁": "내 힘으로 기반을 다지며 함께할 사람을 고르기", "식상": "실력과 결과물을 다듬어 쌓아 두기",
         "재성": "수입 구조를 정리하고 저축 비율을 정해 두기", "관성": "맡은 역할에서 신뢰를 쌓아 두기",
         "인성": "자격·공부로 다음 운의 기반을 다지기"},
 "down": {"비겁": "경쟁과 지출이 늘기 쉬우니 보증·돈 거래를 막고 내 몫 지키기",
          "식상": "기운이 새기 쉬우니 일을 줄이고 건강부터 점검하기",
          "재성": "돈이 힘보다 커지기 쉬우니 큰 계약을 미루고 현금 지키기",
          "관성": "압박이 커지기 쉬우니 책임을 나누고 몸부터 지키기",
          "인성": "생각만 많아지기 쉬우니 작게 실행하며 문서를 점검하기"},
}
PHASE_END = {
 "up": {"비겁": "운이 받쳐 주고 내 편이 붙는 시기예요. 준비해 둔 계획은 이때 실행하되, 공동 명의·돈 거래는 서면으로 정리하세요.",
        "식상": "운이 받쳐 주고 재능이 드러나는 시기예요. 결과물을 세상에 내놓되, 일이 몰려도 쉬는 날은 지키세요.",
        "재성": "운이 받쳐 주고 돈의 흐름이 커지는 시기예요. 계획한 투자는 나눠서 실행하고, 큰 계약은 서면으로 확인하세요.",
        "관성": "운이 받쳐 주고 자리와 인정이 따라오는 시기예요. 맡는 역할이 커질수록 기록과 근거를 남기세요.",
        "인성": "운이 받쳐 주고 도움과 문서 운이 좋은 시기예요. 자격·계약·승인 일을 이때 마무리하세요."},
 "mid": {"비겁": "함께할 사람을 고르고 혼자 다 하려는 습관을 덜어 내며 기반을 다지는 시기예요.",
         "식상": "크게 알리기보다 실력과 결과물을 하나씩 모아 두며 기반을 다지는 시기예요.",
         "재성": "새는 돈을 막고 저축 비율을 정해 두며 기반을 다지는 시기예요. 이때 모은 힘이 다음 운의 밑천이 돼요.",
         "관성": "맡은 일에서 신뢰를 쌓되 책임을 혼자 떠안지 않으며 기반을 다지는 시기예요.",
         "인성": "배울 것 하나를 정해 꾸준히 이어 가며 기반을 다지는 시기예요."},
 "down": {"비겁": "보증·돈 거래·공동 투자는 미루고 비상금과 건강 검진으로 대비하며 지키는 시기예요.",
          "식상": "벌이는 일을 줄이고 쉬는 시간을 일정에 넣어 몸과 관계를 지키는 시기예요.",
          "재성": "큰 투자·대출은 미루고 생활비 몇 달 치 비상금부터 채우며 지키는 시기예요.",
          "관성": "무리한 책임은 나누고 과로가 쌓이면 일부터 줄이며 지키는 시기예요.",
          "인성": "생각만 길어지지 않게 작게 실행하고 서류·계약을 다시 점검하며 지키는 시기예요."},
}


# ------------------------------------------------------------------ 재물 구조
def money_struct(c):
    n = PS.gcount
    if c.strong and n(c, "비겁") >= 3 and n(c, "재성") >= 1: return "gun"
    if not c.strong and not c.neutral and n(c, "재성") >= 2: return "jaeda"
    if n(c, "재성") == 0: return "nojae"
    if n(c, "식상") >= 2: return "sik"
    if n(c, "인성") >= 3: return "in"
    if n(c, "관성") >= 3: return "gwan"
    return "base"


AVOID = {"gun": "보증·돈 빌려주기·공동 투자, 남 따라 하는 투자", "jaeda": "감당 못 할 대출, 한 번에 큰돈이 드는 계약",
         "nojae": "잘 모르는 분야의 투자, 빚을 낸 투자", "sik": "충동적인 장비·취미 지출, 검증 안 된 부업 투자",
         "in": "문서 확인 없는 계약, 남의 말만 믿는 투자", "gwan": "체면을 위한 지출, 명의 빌려주기",
         "base": "보증, 지인 권유 투자, 대출 끼고 하는 단타·코인"}
CAREFUL = {"gun": "좋은 해에도 들어온 돈은 내 통장부터 채우고", "jaeda": "좋은 해에도 다루는 돈의 크기를 체력에 맞추고",
           "nojae": "재성이 들어오는 해에 생긴 돈은 바로 묶어 두고", "sik": "좋은 해에 번 돈은 절반을 바로 저축으로 돌리고",
           "in": "좋은 해에도 계약서는 두 번 읽고", "gwan": "좋은 해에도 보여 주기 위한 지출을 줄이고",
           "base": "좋은 해에도 목돈은 한 번에 넣지 말고"}
CONSERV = {"비겁": "보수적인 해에는 지출 상한을 정하고 믿을 사람과 함께 점검하세요.",
           "인성": "보수적인 해에는 지출 상한을 정하고 서류부터 다시 확인하세요.",
           "식상": "보수적인 해에는 지출 상한을 정하고 내 실력에 쓰는 돈만 남기세요.",
           "재성": "보수적인 해에는 지출 상한을 숫자로 정해 가계부로 지키세요.",
           "관성": "보수적인 해에는 지출 상한과 원칙을 미리 정해 두세요."}
NO_PEAK2 = {"gun": "번 돈을 지키는 힘이 곧 재산이 되는 형이에요", "jaeda": "그릇을 키운 만큼 담기는 형이에요",
            "nojae": "재성이 들어오는 해마다 한 단계씩 커지는 형이에요", "sik": "실력이 쌓인 만큼 수입이 따라오는 형이에요",
            "in": "자격과 신용이 쌓인 만큼 돈이 붙는 형이에요", "gwan": "자리와 신용이 올라간 만큼 돈이 따라오는 형이에요",
            "base": "좋은 해마다 조금씩 쌓는 형이에요"}


# ------------------------------------------------------------------ 연애·가정
IDEAL = {"비견": "친구처럼 편하고 대등하게 의견을 나누는 사람", "겁재": "추진력이 있으면서도 내 몫을 존중해 주는 사람",
         "식신": "함께 먹고 웃는 일상이 편안한 사람", "상관": "재치 있고 대화가 잘 통하되 내 말을 끝까지 들어 주는 사람",
         "정재": "성실하고 생활력 있는 사람", "편재": "활동적이고 시야가 넓은 사람",
         "정관": "약속을 잘 지키고 반듯한 사람", "편관": "결단력 있고 나를 지켜 주는 듬직한 사람",
         "정인": "따뜻하게 품어 주고 배울 점이 있는 사람", "편인": "생각이 깊고 내 개성을 이해해 주는 사람"}


def ideal_line(c, sp):
    from persona import BR_KO
    return f"배우자궁(일지 {BR_KO[c.db]})에 {josa(sp, '이')} 있어 {IDEAL.get(sp, '대화가 편하게 통하는 사람')}과 잘 맞아요."


def palace_line(c):
    f = c.fav[BR_ELK[c.db]]
    if f >= 1: return f"배우자 자리({c.db})가 이 사주에 힘이 되는 {ROLE_SHORT[f]}이라, 서로 기댈수록 단단해지는 관계예요. "
    if f <= -1: return f"배우자 자리({c.db})가 이 사주에 부담인 {ROLE_SHORT[f]} 쪽이라, 서로의 영역을 존중할수록 편해지는 관계예요. "
    return ""


CNT_WORD = {1: "하나", 2: "둘"}


NT_ROLE = {2: "용신", 1: "희신", 0: "중립", -1: "구신", -2: "기신"}


def spouse_star_line(c, star_word, cnt, tail_kind="편이에요"):
    if tail_kind == "짧게":   # 표지(핵심 5가지)용: 본문과 같은 문장을 되풀이하지 않게 짧게
        sg = "관성" if c.gender == "F" else "재성"; f = c.fav[c.gel[sg]]
        if cnt == 0: return f"{star_word}은 겉에 없고, 운에서 {elw(c.gel[sg])} 기운이 올 때 인연이 드러나요."
        return f"{star_word}은 {CNT_WORD.get(cnt, '여럿')}" + (f", 이 사주에 힘이 되는 {elw(c.gel[sg])} 기운이에요." if f >= 1 else f", 이 사주엔 부담인 {elw(c.gel[sg])} 기운이라 관계에서 내 몫을 챙기세요." if f <= -1 else f"이고 {elw(c.gel[sg])} 기운이에요.")
    sg = "관성" if c.gender == "F" else "재성"
    f = c.fav[c.gel[sg]]
    if cnt == 0:
        return f"{elw(c.gel[sg])} 기운인 {josa(star_word, '이')} 겉에 없어 상대를 오래 지켜본 뒤 마음을 여는 " + ("타입이에요." if tail_kind == "타입이에요" else "편이에요.")
    w = CNT_WORD.get(cnt, "여럿")
    if cnt >= 3:
        base = f"{elw(c.gel[sg])} 기운인 {josa(star_word, '이')} {w}이라 관계에 마음 쓸 일이 많은 편이에요."
    else:
        base = f"{elw(c.gel[sg])} 기운인 {josa(star_word, '이')} {w} 있어 책임감 있게 관계를 지키는 편이에요."
    if f >= 1: base = base[:-len("편이에요.")] + f"편이고, 이 기운이 사주에 힘이 되는 {NT_ROLE[f]} 쪽이라 좋은 인연이 버팀목이 돼요."
    elif f <= -1: base = base[:-len("편이에요.")] + f"편인데, 이 기운이 사주엔 부담인 {NT_ROLE[f]} 쪽이라 맞춰 주느라 지치지 않게 내 몫을 챙기세요."
    return base
