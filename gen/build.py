# -*- coding: utf-8 -*-
"""Chart → 감정서 HTML 페이지 (규칙 기반 문장 조립)."""
import html
from datetime import datetime
import engine as E
import saju as S
from engine import STEM_ELK, BR_ELK
from texts import *
from josa import josa, particle, fix_josa
import advice as AV
import jobs as JB
import vary as V
import persona as PS
import natal as NT

def esc(s): return html.escape(str(s))
def elsp(ch): 
    e = STEM_ELK.get(ch) or BR_ELK.get(ch)
    return f'<span class="el-{e}">{ch}</span>'
def cov_cell(ch):   # cover1116: 표지 기둥 칸 — 큰 한글 한 줄 + (한자·뜻) 작은 한 줄
    e = STEM_ELK.get(ch) or BR_ELK.get(ch)
    return f'<div class="cc el-{e}"><b>{_COV_KO.get(ch, ch)}</b><i>({ch}·{_COV_EL.get(e, "")})</i></div>'
_COV_KO = dict(zip("甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥", "갑을병정무기경신임계자축인묘진사오미신유술해"))
_COV_EL = {"목": "나무", "화": "불", "토": "흙", "금": "쇠", "수": "물"}
def stars(n): return "★" * n + "☆" * (5 - n)
def ko(gz): return S.gz_ko(gz)
def el_full(e): return f"{e}({EL_HAN[e]})"
def tgj(c, gz):  # '식신/상관'
    return f"{c.tg(gz[0])}/{c.tg(gz[1], True)}"




TG_SHORT_HI = {"겁재": "경쟁·추진", "상관": "표현·말솜씨"}   # release1116: ★4-5 달의 주제어


def _no_but(d):
    """'… 좋아요. 다만 …하세요.' → 앞 문장만 (좋은 해의 주의 말은 결론줄 '조심' 한 번으로 모아요)"""
    i = d.find(" 다만 ")
    if i < 0: i = d.find(". 다만")
    return d[:i].rstrip(" .,") + "." if i > 20 else d

def _hm_ko(t):
    """josa1116: '12:15' → '12시 15분' (읽히는 대로 써야 조사도 맞아요)"""
    try:
        h, m = (int(x) for x in str(t).split(":")[:2])
    except (TypeError, ValueError):
        return t
    return f"{h}시 {m}분" if m else f"{h}시"

class Report:
    def __init__(self, c, name=None, inp=None, now=None):
        self.c = c; self.name = name; self.inp = inp or {}
        self.now = now or datetime.now()
        self.Y = self.now.year
        self.who = (name + "님") if name else "고객님"
        self.years = list(range(self.Y, self.Y + 10))
        self.ysc = {y: c.score(E.year_gz(y))[0] for y in self.years}
        # fix1113: 세운 별점 = 절대 점수 별점(60%) + 10년 안 순위(40%) 혼합.
        #  - 순위는 1위=5 … 10위=1 로 고르게 펼침
        #  - 절대 별점이 3 이하인 해는 ★5가 될 수 없고(나쁜 10년이면 ★5가 0개), 절대 ★1인 해는 ★2를 넘지 않아요
        self.yabs = {y: c.stars(v) for y, v in self.ysc.items()}
        order = sorted(self.years, key=lambda y: -self.ysc[y])
        n = len(order)
        self.yrank = {y: 5 - 4 * i / (n - 1) for i, y in enumerate(order)}
        self.ystar = {}
        for y in self.years:
            a = self.yabs[y]
            v = int(0.6 * a + 0.4 * self.yrank[y] + 0.5)
            v = max(a - 1, min(a + 1, v))
            if a <= 3: v = min(v, 4)
            if a <= 1: v = min(v, 2)
            self.ystar[y] = max(1, min(5, v))
        self.love = {y: c.love_score(E.year_gz(y)) + 0.15 * self.ysc[y] for y in self.years}
        self.mp = E.month_pillars(self.Y, self.Y + 1)
        self.pg = 0
        self.no = 0

    def star(self, s):
        """대운·월운 등 단일 점수 → 절대 기준 별점(★1~★5)."""
        return self.c.stars(s)

    def nxt(self):
        self.no += 1
        return f"{self.no:02d}"

    # ------------------------------------------------------------ 공통 분석 문장
    def year_events(self, gz, short=False):
        """세운/월운 간지 → [(제목, 설명)]"""
        c = self.c; s, b = gz; out = []
        tn = c.tone(c.score(gz)[0])
        rels = c.relations_to_chart(s, b)
        seen = set(); wj_done = set()
        for kind, pos, det, el in rels:
            key = (kind, pos)
            if key in seen: continue
            seen.add(key)
            tgb = c.tg(b, True); fb_ = c.fav[BR_ELK[b]]
            who = (f"{NT.ROLE[fb_]} " if fb_ else "") + f"{tgb}({b})"
            if kind == "충":
                txt = {"월": f"{who}가 월지를 치는 때라 " + JB.t("ev_chung_wol") + ("미리 준비한 변화라면 좋은 방향으로 풀려요." if tn == "good" else "갑작스러운 결정보다 준비해 둔 계획대로 움직이면 흔들림이 적어요." if tn == "mid" else f"원치 않는 변화가 올 수 있으니 {JB.t('move')}·이사는 서두르지 말고, 조건을 꼼꼼히 비교한 뒤 정하세요."),
                       "일": f"{who}가 배우자궁을 쳐서 배우자·거처·생활 패턴이 바뀌기 쉬우니, 이사·독립·관계 정리 같은 일은 서두르지 말고 조율하세요.",
                       "년": f"{who}가 년지를 쳐서 집안·윗사람 쪽 일로 신경 쓸 일이 생기니, 집안 행사·부모님 건강을 챙기세요.",
                       "시": f"{who}가 시지를 쳐서 자녀·아랫사람·미래 계획에 변동이 있으니, 계획을 수정하고 다시 세우세요."}[pos]
                out.append((3, f"{det[0]}{det[1]}충 ({POS_NAME[pos]} · {POS[pos]})", txt,
                            f"{det[0]}{det[1]}충: " + {"월": JB.t("ev_chung_wol_short"), "일": "거처·관계 변화", "년": "집안 일", "시": "계획 변동"}[pos]))
            elif kind in ("육합", "반합") and pos in ("일", "월", "시"):
                good = c.fav.get(el, 0) >= 0
                txt = {"일": f"{tgb}({b})가 배우자궁과 합해, 가까운 사람과의 관계가 깊어지고 함께하는 계획이 생기기 쉬워요.",
                       "월": f"{tgb}({b})가 " + JB.t("ev_hap_wol").replace("합해요. ", "합해, ", 1),
                       "시": f"{tgb}({b})가 자녀·미래의 자리와 합해, 새 계획과 아랫사람의 도움이 들어와요."}[pos]
                if c.fav.get(el, 0) >= 1: txt += f" 합으로 생기는 {el} 기운이 {NT.ROLE[c.fav[el]]}이라 그 인연이 실제 도움으로 이어져요."
                if not good: txt += " " + {"일": f"다만 합으로 생기는 {el} 기운이 이 사주엔 {NT.ROLE[c.fav[el]]}이라, 관계에 기대를 너무 많이 걸지 마세요.",
                                           "월": f"다만 합으로 생기는 {el} 기운이 {NT.ROLE[c.fav[el]]}이라, 좋은 제안이라도 조건부터 확인하세요.",
                                           "시": f"다만 합으로 생기는 {el} 기운이 {NT.ROLE[c.fav[el]]}이라, 새 계획은 작게 시작하세요."}[pos]
                out.append((2, f"{det[0]}{det[1]} {'합' if kind == '육합' else '반합'}({el}) · {POS_NAME[pos]}", txt,
                            f"{det[0]}{det[1]}합: " + {"일": "가까운 관계", "월": "협력·좋은 제안", "시": "새 계획"}[pos]))
            elif kind == "천간합" and pos == "일":
                out.append((2, f"{s}{c.dm}합 (일간)", f"{c.tg(s)} {s}가 일간과 합해, 마음이 묶이는 좋은 제안·계약이 들어오는 기운이에요.", f"{s}{c.dm}합: 좋은 제안"))
            elif kind == "천간충" and pos == "일":
                out.append((2, f"{s}{c.dm}충 (일간)", f"{c.tg(s)} {s}가 일간을 치는 기운이라 생각과 방향이 흔들리니, 큰 결정은 한 번 더 검토하세요.", f"{s}{c.dm}충: 결정은 신중히"))
            elif kind == "형" and pos in ("일", "월"):
                out.append((1, f"{det[0]}{det[1]}형 ({POS_NAME[pos]})", f"{det[0]}{det[1]}형이 {POS_NAME[pos]}에 걸려 조정과 마찰이 생기기 쉬우니, {POS[pos]} 쪽 일을 혼자 떠안지 말고 나눠서 지세요.", f"{det[0]}{det[1]}형: 마찰 조정"))
            elif kind in ("원진", "해") and pos in ("일", "월", "년") and det not in wj_done:
                wj_done.add(det)
                if any(x[1].startswith(det) for x in out): continue
                out.append((0.5 if pos != "년" else 0.2, f"{det[0]}{det[1]} {kind} ({POS_NAME[pos]})", f"{POS_NAME[pos]}와 {josa(kind, '이')} 걸려 {POS[pos]} 쪽에 말 못 한 서운함이 쌓이기 쉬우니, 바쁠수록 말 한마디를 더 따뜻하게 건네세요.", f"{det[0]}{det[1]}{kind}: 말조심"))
        if b in S.CHEONEUL[c.dm]:
            hg = {"비겁": "친구·동료", "식상": "후배·아랫사람", "재성": "돈과 일로 얽힌 사람", "관성": "윗사람·기관", "인성": "스승·어른"}[TG_GROUP[c.tg(b, True)]]
            out.append((2, f"천을귀인 {b}", f"{c.tg(b, True)}({b}) 자리로 귀인이 들어와 {hg} 가운데 도와주는 사람이 나타나니, 중요한 일은 추천·소개로 풀어 가세요.", "천을귀인: 귀인 도움"))
        yb, db = c.P["년"]["gz"][1], c.db
        if S.sinsal12(yb, b).startswith("연살") or S.sinsal12(db, b).startswith("연살"):
            out.append((1, f"도화 {b}", f"{c.tg(b, True)}({b})로 도화가 들어와 매력이 드러나고 사람이 모이니, 대면 일·홍보에 좋아요.", "도화: 매력·인기"))
        if S.sinsal12(yb, b).startswith("역마") or S.sinsal12(db, b).startswith("역마"):
            out.append((1, f"역마 {b}", JB.r("이동·출장·이사·해외 기운이에요. 움직일수록 기회가 와요."), JB.r("역마: 이동·출장")))
        be, se = BR_ELK[b], STEM_ELK[s]
        if c.fav[be] >= 1 or c.fav[se] >= 1:
            e = be if c.fav[be] >= c.fav[se] else se
            out.append((2, f"{FAV_WORD[c.fav[e]] or '좋은'} {el_full(e)}", f"나를 살리는 {EL_WORD[e]}({c.el_group[e]})의 기운이 들어와 {PS.GMEAN[c.el_group[e]]} 쪽에 힘이 붙어요.", f"{FAV_WORD[c.fav[e]] or '좋은 기운'} {e}: 힘이 붙음"))
        elif c.fav[be] <= -2:
            out.append((1, f"{FAV_WORD[-2]} {el_full(be)}", f"{EL_WORD[be]}({c.el_group[be]})의 기운이 무거워지는 때라 " + {"비겁": "사람·지출 문제를 줄이고 기본을 지키세요.", "식상": "벌이는 일과 말을 줄이고 기본을 지키세요.", "재성": "돈 욕심과 무리한 확장을 줄이고 기본을 지키세요.", "관성": "과로와 무리한 책임을 피하고 기본을 지키세요.", "인성": "생각만 길어지지 않게 몸을 움직이며 기본을 지키세요."}[c.el_group[be]], f"{be} 과다: 무리 금지"))
        out.sort(key=lambda x: -x[0])
        if short: return [x[3] for x in out]
        return [(x[1], x[2]) for x in out]

    POSW = ("좋은 제안", "귀인", "매력", "힘이 붙음", "가까운 관계", "새 계획", "협력")

    def ev_star(self, ev, stn):
        """verdict1116: 짧은 꼬리표도 별 방향에 맞춰요 — ★1~2엔 좋은 말 꼬리표를 빼고, ★4~5엔 나쁜 말 꼬리표를 1개까지만."""
        if stn <= 2: return [e for e in ev if not any(w in e for w in self.POSW)]
        if stn >= 4:
            neg = [e for e in ev if not any(w in e for w in self.POSW)]
            return [e for e in ev if any(w in e for w in self.POSW)] + neg[:1]
        return ev

    def month_point(self, gz):
        c = self.c; s, b = gz
        st, bt = c.tg(s), c.tg(b, True)
        head = f"{TG_SHORT[st]}·{TG_SHORT[bt]}" if TG_SHORT[st] != TG_SHORT[bt] else TG_SHORT[st]
        ev = self.year_events(gz, short=True)[:3]
        stn = self.star(c.score(gz)[0])
        ev = self.ev_star(ev, stn)
        if stn >= 4:   # release1116: ★4-5 달은 조심을 줄 끝 '조심' 한 번만 — 주제어·꼬리표의 주의 말은 빼요
            head = "·".join(dict.fromkeys(TG_SHORT_HI.get(x, TG_SHORT[x]) for x in (st, bt)))
            ev = [e for e in ev if any(w in e for w in self.POSW)]
        return head + (" · " + ", ".join(ev) if ev else "") + "."

    def year_title(self, y):
        c = self.c; gz = E.year_gz(y); st = self.ystar[y]
        rels = c.relations_to_chart(*gz)
        if any(k == "충" and p in ("월", "일") for k, p, _, _ in rels):
            return "판을 다시 짜는 해" if st >= 4 else "흔들림을 다스리는 해"
        g1, g2 = TG_GROUP[c.tg(gz[0])], TG_GROUP[c.tg(gz[1], True)]
        if g1 == g2 and st >= 3:
            return {"식상": "빛나고 바쁜 해", "재성": "돈이 움직이는 해", "관성": "책임과 인정의 해", "인성": "배우고 채우는 해", "비겁": "내 힘으로 서는 해"}[g1] if st < 5 else "기회가 큰 해"
        return {5: "기회가 큰 해", 4: "기회가 열리는 해", 3: "다지고 준비하는 해", 2: "지키며 내실을 다지는 해", 1: "몸과 살림을 먼저 지키는 해"}[st]

    # ------------------------------------------------------------ fix1113b 조언
    def yadv(self, y, area="gen", n=2, lab=None):
        gz = E.year_gz(y); return AV.period_advice(self.c, gz, self.ysc[y], area, key=str(y), max_items=n, scope="이 해는", lead=(area == "gen" or lab is not None), label=lab, kind="year", year=y, star=self.ystar.get(y))

    def yshort(self, y):
        k, t = AV.short_advice(self.c, E.year_gz(y), self.ysc[y], "year", y, star=self.ystar.get(y)); return k, t

    def cur_daeun_adv(self, area, n=1):
        c = self.c; p = c.current_daeun(self.Y)
        if not p: return []
        return AV.period_advice(c, p["gz"], c.score(p["gz"])[0], area, key="cd" + area, max_items=n, scope=f"지금 {p['gz']} 대운은", label=f"지금 대운({p['gz']})")

    def year_line(self, y):
        c = self.c; gz = E.year_gz(y)
        st, bt = c.tg(gz[0]), c.tg(gz[1], True)
        a, b = TG_THEME[st][0], TG_THEME[bt][0]
        ev = self.ev_star(self.year_events(gz, short=True)[:3], self.ystar.get(y, 3))[:2]
        s = f"{josa(a, '과')} {b}의 해" if a != b else f"{a}의 해"
        return s + (" · " + ", ".join(ev) if ev else "")

    # ------------------------------------------------------------ 시기 고르기
    def best_love_years(self, n=3):
        ys = sorted(self.years, key=lambda y: -self.love[y])
        return [y for y in ys if self.love[y] >= 1.4][:n]

    def money_years(self):
        c = self.c; out = []
        for y in self.years:
            gz = E.year_gz(y)
            if (c.tg(gz[0]) in ("정재", "편재") or c.tg(gz[1], True) in ("정재", "편재") or c.fav[BR_ELK[gz[1]]] >= 1) and self.ystar[y] >= 4:
                out.append(y)
        return out[:3]

    def runs(self):
        ys = self.years; out = []; cur = [ys[0]]
        def cat(y): return "up" if self.ystar[y] >= 4 else "down" if self.ystar[y] <= 2 else "mid"
        for y in ys[1:]:
            if cat(y) == cat(cur[-1]): cur.append(y)
            else: out.append((cat(cur[0]), cur)); cur = [y]
        out.append((cat(cur[0]), cur))
        return out

    def best_daeun_money(self):
        """fix1113: 재물 정점 대운. 대운 점수 < 0 이거나, 재성이 기신인데 재성 글자가 오는 대운은 후보에서 빼요.
        후보가 없으면 None → '뚜렷한 재물 정점은 없어요' 문구."""
        c = self.c; best = None
        jel = c.gel["재성"]; sel = c.gel["식상"]
        for p in c.daeun_periods():
            if p["y1"] <= self.Y or p["a0"] > 65: continue
            sc0 = c.score(p["gz"])[0]
            # verdict1116: 정점은 ★4 이상(good) 대운만, 그리고 천간·지지 어느 쪽도 기신이 아닐 때만
            if c.tone(sc0) != "good" or c.fav[STEM_ELK[p["gz"][0]]] <= -2 or c.fav[BR_ELK[p["gz"][1]]] <= -2: continue
            # job1113: 0 언저리(★3 하단) 대운을 '정점'이라 부르지 않도록 문턱 0 → 0.5
            if sc0 < 0.5: continue
            # job1113: 세운 별점과 어긋나지 않게 — 이 대운 안에 드는 10년표 해 중 ★2 이하가 3해 이상이거나 평균이 ★3 미만이면 제외
            ov = [self.ystar[y] for y in self.years if p["y0"] <= y < p["y1"]]
            if ov and (sum(v <= 2 for v in ov) >= 3 or sum(ov) / len(ov) < 3): continue
            g = (TG_GROUP[p["천간십신"]], TG_GROUP[p["지지십신"]])
            if "재성" in g and c.fav[jel] <= -2: continue
            nj = g.count("재성"); ns = g.count("식상")
            if nj + ns == 0 and c.tone(sc0) != "good": continue
            sc = sc0 + 1.0 * nj + (0.4 * ns if c.fav[sel] >= 0 else 0)
            if best is None or sc > best[0]: best = (sc, p)
        return best[1] if best else None

    def peak_phrase(self, p):
        """job1113: 정점 대운 문구. 대운 자체가 ★4(good)가 아니면 '정점'보다 '상대적으로 나은 시기'로 낮춰 말해요."""
        if self.c.tone(self.c.score(p["gz"])[0]) == "good":
            return "재물이 가장 크게 움직이는 시기는"
        return "재물 흐름이 상대적으로 가장 나은 시기는"

    def money_window(self):
        """job1113: 정점 대운이 없을 때 10년표에서 돈을 움직이기 좋은 해(★4 이상)를 이름으로 말해요."""
        ms = self.tpx().ystars("money")[1]   # verdict1116: 돈 표의 별과 같은 기준
        up = [y for y in self.years if ms[y] >= 4][:3]
        return (f" 10년 안에서는 {'·'.join(map(str, up))}년(돈 ★4 이상, {V.run_group(self, up)} 운)이 돈을 움직이기 가장 좋은 해예요" if up else "")

    def no_peak(self):
        """NO_PEAK의 사람별 버전: 재물 구조와 용신 그룹을 한 문장에 묶어요."""
        c = self.c
        return (f"사주로 보면 앞으로 재물이 한꺼번에 크게 불어나는 정점 대운은 뚜렷하지 않아, {c.el_group[c.yong]}({V.elw(c.yong)}) 운이 드는 좋은 해마다 조금씩 쌓아 가는 쪽이 맞아요")

    SEASON_CL = {"winter": "차가운 계절을 데워 줄 따뜻한 불(火)의 기운이 반가운 사주예요",
                 "summer": "뜨거운 계절을 식혀 줄 시원한 물(水)의 기운이 반가운 사주예요",
                 "spring": "만물이 자라는 계절의 성장과 시작 기운을 품었어요",
                 "autumn": "거두고 정리하는 계절의 결단과 결실 기운을 품었어요"}
    NO_PEAK = "사주로 보면 앞으로 재물이 한꺼번에 크게 불어나는 정점 대운은 뚜렷하지 않아요. 한 번에 크게 버는 쪽보다 좋은 해마다 조금씩 쌓아 가는 쪽이 맞아요"

    def fifties_ok(self):
        return self.c.fifties_ok()

    # ------------------------------------------------------------ palm hooks
    def palm_cross(self, key, st):
        c = self.c
        if key == "jaeun" and st == "above_heart":
            y50 = c.solar.year + 50
            dp = [p for p in c.daeun_periods() if p["a0"] <= 55 and p["a1"] >= 50]
            dtxt = "·".join(f"{p['gz']} 대운(만 {p['a0']}~{p['a1']}세)" for p in dp)
            if self.fifties_ok():
                return f"50~55세는 {y50}~{y50 + 5}년이에요. 사주로는 {dtxt or '50대 대운'}에 해당하고 이 대운이 받쳐 줘, 이 시기를 재물의 두 번째 정점으로 보세요."
            return f"50~55세는 {y50}~{y50 + 5}년이에요. 사주로는 {dtxt or '50대 대운'}에 해당하는데 이 대운의 힘이 약한 편이라, 이때는 크게 늘리기보다 모아 둔 것을 지키고 관리하는 데 쓰는 게 맞아요."
        if key == "jaeun":
            p = self.best_daeun_money()
            if not p:
                return self.NO_PEAK + ". 손금의 재운선도 이 흐름과 함께 읽으세요."
            good = c.tone(c.score(p["gz"])[0]) == "good"
            ptxt = f"{'재물이 가장 크게 움직이는' if good else '재물 흐름이 상대적으로 나은'} {p['gz']} 대운(만 {p['a0']}~{p['a1']}세)"
            return f"사주에서는 {josa(ptxt, '이')} {'재물의 정점' if good else '재물의 기준 시기'}이에요. {'재운선과 시기가 맞물려요.' if st == 'above_heart' and self.fifties_ok() else '손금의 재운선과 함께 이 시기를 재물의 기준점으로 삼으세요.'}"
        if key == "saup":
            jj = c.r["ten_gods_count"].get("정재", 0); pj = c.r["ten_gods_count"].get("편재", 0)
            style = f"정재 중심({JB.t('salary_short')})" if jj >= pj else "편재 중심(활동·거래·사업 감각)"
            return f"사주의 재물 구조는 {josa(style, '이에요')}. " + ("손금과 사주 모두 축적형 재물을 가리켜요." if (st != "clear" and jj >= pj) else "손금과 함께 보면 돈 버는 방식의 균형이 보여요.")
        if key == "fate":
            a0 = c.solar.year + 35; ys = [y for y in range(a0, a0 + 4)]
            if st == "none":
                return f"사주는 {josa(c.gyeok, '이고')} {josa(c.st_label.split('(')[0], '이라')} 시기를 따라 자기 길을 쌓는 형이에요. 손금의 운명선이 뚜렷하지 않은 것과 맞물려, 정해진 길보다 자유롭게 진로를 만들어 가요."
            return f"정격은 {josa(c.gyeok, '이고')}, 유년법 35~38세는 {ys[0]}~{ys[-1]}년이에요. 이 무렵 세운과 대운이 진로의 분기점을 함께 가리켜요."
        if key == "life":
            return f"사주는 {josa(c.st_label, '이에요')}. " + ("뿌리가 약한 만큼 휴식과 수면이 체력을 지키는 열쇠예요." if not c.strong else "기운이 강한 만큼 과로보다 꾸준한 운동이 체력을 지켜요.")
        if key == "head":
            tal = "식상" if c.gcount["식상"] else max(c.gcount, key=c.gcount.get)
            return f"{c.gyeok}({GYEOK[c.gyeok].split('. ')[0].replace('격이에요', '격')})과 {tal}({GROUP_MEAN[tal]})이 손금의 재능과 함께 읽혀요."
        if key == "heart":
            sp = c.tg(c.db, True)
            return f"배우자궁(일지)은 {josa(sp, '이에요')}. {SPOUSE_PALACE[sp].split('. ')[0].replace('배우자궁에 ' + sp + '이 있어 ', '').replace('배우자궁에 ' + sp + '가 있어 ', '')}."
        return ""

    # ============================================================ PAGES
    def cover(self, palm=None):
        c = self.c; inp = self.inp; P = c.P
        gtxt = "여성" if c.gender == "F" else "남성"
        bdate = inp.get("date_label", "")
        pillars = ""
        for n, lb in (("시", "시주"), ("일", "일주 · 나"), ("월", "월주"), ("년", "년주")):
            if n not in P or (n == "시" and not c.time_known):
                pillars += f'<div class="pl"><div class="lb">{lb}</div><div class="ch"><div class="cc"><b>?</b><i>&#160;</i></div><div class="cc"><b>?</b><i>&#160;</i></div></div><div class="tg">시간 미상</div></div>'
                continue
            p = P[n]; gz = p["gz"]
            tg = "일간 · " + p["branch_tengod"] if n == "일" else f'{p["stem_tengod"]} · {p["branch_tengod"]}'
            pillars += f'<div class="pl{" me" if n == "일" else ""}"><div class="lb">{lb}</div><div class="ch">{cov_cell(gz[0])}{cov_cell(gz[1])}</div><div class="tg">{tg}</div></div>'
        k = self.key5(palm)
        ks = "".join(f'<div class="k"><div class="n">{i+1}</div><div class="t"><b>{t}</b>{d.replace("<b>", "<strong>").replace("</b>", "</strong>")}</div></div>' for i, (t, d) in enumerate(k))
        title = "사주 × 손금 교차 감정서" if palm else "사주 종합 감정서"
        return f'''<section class="page cover"><div class="in">
 <div class="brand"><div class="seal">命</div><div class="name">손명리</div><div class="en">SONMYEONGRI · SAJU{' &amp; PALM' if palm else ''}</div></div>
 <div class="ctitle">{title}</div>
 <div class="cmeta">{esc(self.who)} · {gtxt}{(' · ' + JB.label()) if JB.label() else ''} · {esc(bdate)} · {esc(inp.get("place_label", ""))} 출생</div>
 <div class="pillars no-gloss">{pillars}</div>
 <div class="serif" style="text-align:center;color:#e9c97c;font-size:12.5pt;letter-spacing:0.18em;margin-bottom:1mm">한눈에 보는 핵심 5가지</div>
 <div class="key5">{ks}</div>
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def key5(self, palm):
        c = self.c; out = []
        st = STEM[c.dm]; season = MONTH[c.mb][0]
        out.append((f"{season}에 태어난 {st['title']}의 사주",
                    f"{josa(st['img'], '를')} 닮은 {st['ko']}({c.dm}) 일간으로 {season}에 태어나, {self.SEASON_CL[c.season]}. 격국은 <b>{c.gyeok}</b>, "
                    f"{josa(c.st_label.split('(')[0], '이라')} <span class=\"gold\">용신은 {el_full(c.yong)}, 희신은 {el_full(c.hee)}</span>{particle(el_full(c.hee), '로')} 봐요."))
        mt, md = self.money_headline(palm)
        ma = self.cur_daeun_adv("money", 1)
        if ma: md += f" <b>{ma[0][0]}</b>: {ma[0][1]}"
        out.append((mt, md))
        # 관계 (fix1113: 결혼·인연 '시기'는 말하지 않아요)
        sp = c.tg(c.db, True)
        cnt = c.gcount["관성" if c.gender == "F" else "재성"]
        star_word = "관성(남편)" if c.gender == "F" else "재성(아내)"
        extra = " " + V.spouse_star_line(c, star_word, cnt, "짧게")
        out.append((SPOUSE_TITLE[sp], SPOUSE_PALACE[sp] + extra))
        # 올해/내년/최고
        y1 = self.Y + 1; gz1 = E.year_gz(y1)
        top = sorted(self.years, key=lambda y: -self.ysc[y])[:2]
        top.sort()
        tops = "·".join(f"{y} {gzz}" for y, gzz in ((y, E.year_gz(y)) for y in top))
        out.append((f"{y1}년은 {self.year_title(y1).replace('해', '해')}, {'·'.join(map(str, top))}년이 10년의 정점",
                    f"{y1} {gz1}년은 {self.year_line(y1)}. {self.best_months_phrase(y1)} 10년 안에서는 <span class=\"gold\">{tops}년이 {self.top_reason(top)} 상대적으로 가장 좋은 해</span>예요. "
                    f"<b>{self.yshort(y1)[0]}</b>({y1}년): {self.yshort(y1)[1]}." + (f" <b>{self.yshort(top[0])[0]}</b>({top[0]}년): {self.yshort(top[0])[1]}." if top[0] != y1 else "")))
        low = [y for y in self.years if self.ystar[y] <= 2][:3]
        cw = self.caution_word()
        out.append((f"지킬 것: {cw}",
                    f"{'·'.join(map(str, low)) + '년은 지키는 해예요. ' if low else ''}개운 포인트는 <span class=\"gold\">{ELEM[c.yong]['colors'].split('·')[0]}·{ELEM[c.hee]['colors'].split('·')[0]} 계열, {ELEM[c.yong]['dir']}, 숫자 {ELEM[c.yong]['nums']}</span>이에요."))
        return out

    def first_group_year(self, g):
        for y in self.years:
            gz = E.year_gz(y)
            if g in (TG_GROUP[self.c.tg(gz[0])], TG_GROUP[self.c.tg(gz[1], True)]): return y
        return None

    def top_reason(self, top):
        """q1113: 10년 중 좋은 두 해가 왜 좋은지(그해 주제 십신)"""
        gs = [(y, PS.P(self.c, E.year_gz(y), self.ysc[y], "year", y).g) for y in top]
        gl = list(dict.fromkeys(g for _, g in gs))
        return "·".join(f"{g}({PS.GMEAN[g]})" for g in gl) + " 기운을 받아"

    def caution_word(self):
        c = self.c
        top = max(c.gw, key=c.gw.get)
        if not c.strong:
            w = {"재성": "혼자 다 떠안기, 보증·무리한 대출", "관성": "과도한 책임·눈치, 번아웃", "식상": "에너지 소모·말실수, 과로",
                 "비겁": "체력 과신", "인성": "생각만 하고 미루기"}[max(c.drain, key=c.drain.get)]
        else:
            w = {"비겁": "고집·독단, 동업·보증", "인성": "생각 많고 실행 늦음", "식상": "말이 앞서는 것", "재성": "욕심·무리한 투자", "관성": "자기 압박"}[top]
        lack = min(c.wt, key=c.wt.get)
        return JB.r(f"{w}, {HEALTH_LACK[lack].split('.')[0].split('·')[0]} 관리")

    def best_months_phrase(self, y, style=0):
        ms = [(a, b, gz) for a, b, gz, n in self.mp if a.year == y and n != "小寒" or (a.year == y + 1 and n == "小寒")]
        if not ms: return ""
        sc = sorted(ms, key=lambda m: -self.c.score(m[2])[0])
        good = sorted(sc[:2], key=lambda m: m[0]); bad = sorted(sc[-2:], key=lambda m: m[0])
        # q1113: 달마다 '왜 좋은지/왜 피하는지'(용신·기신 오행, 일지·월지 충)를 붙여요
        return V.months_phrase(self.c, good, bad, style, y, self.ystar.get(y, 3))

    def money_headline(self, palm):
        c = self.c; n = c.gcount["재성"]
        gos = [p for p in c.P.values() if p["gz"][1] == JAEGO[c.gel["재성"]] or (p["gz"][1] in "辰戌丑未" and any(E.STEM_ELK[h] == c.gel["재성"] for h in S.HIDDEN[p["gz"][1]]))]
        if n == 0:
            t = "재성이 숨어 있어, 운이 올 때 크게 반응하는 재물"
            d = f"재성({el_full(c.gel['재성'])})이 겉에 없어 젊어서는 돈보다 실력을 먼저 쌓는 흐름이에요. 운에서 재성({EL_WORD[c.gel['재성']]})이 들어오는 해" + (f", 가깝게는 {self.first_group_year('재성')}년" if self.first_group_year('재성') else "") + "에 수입이 확 달라져요."
        elif not c.strong and c.gw["재성"] >= max(c.gw["식상"], c.gw["관성"]) and n >= 2:
            t = "돈의 기운이 크고, 그릇을 키울수록 담는 돈도 커져요"
            d = f"재성이 {n}개{', 그중 재물 창고(' + '·'.join(p['gz'][1] for p in gos) + ')도 있어 모으는 힘이 강해요' if gos else '로 돈과 인연이 깊어요'}. 다만 일간보다 돈의 기운이 커서 <b>전문성과 체력을 키울수록 담을 수 있는 돈도 커지는</b> 구조예요."
        elif c.strong and c.gcount["비겁"] >= 3 and n >= 1:
            t = "버는 힘은 강하고, 지키는 힘이 관건"
            d = "비겁이 강해 돈을 벌어도 사람·지출로 새기 쉬운 군겁쟁재의 모양이에요. <b>통장 분리·자동 저축</b>만 해도 재산의 크기가 달라져요."
        else:
            t = "재능이 돈이 되는 사주" if c.gcount["식상"] and n else "꾸준히 쌓아 가는 재물"
            d = f"재성이 {n}개{', 식상이 재성을 낳는 식신생재 구조라 실력과 감각이 그대로 수입이 돼요' if c.gcount['식상'] else '로 현실 감각이 좋아요'}{'. 재물 창고(' + '·'.join(p['gz'][1] for p in gos) + ')도 있어 모으는 재주가 있어요' if gos else ''}."
        if palm: d += " __PALM_KEY2__"
        return (t, d)

    # ------------------------------------------------------------ P2 명식
    def p_chart(self):
        c = self.c; P = c.P
        cols = [n for n in ("시", "일", "월", "년") if n in P and (n != "시" or c.time_known)]
        hdr = {"시": "시주", "일": "일주 (나)", "월": "월주", "년": "년주"}
        def row(lab, f, cls=""):
            return f'<tr><td class="small">{lab}</td>' + "".join(f'<td class="{cls(n) if callable(cls) else cls}">{f(n)}</td>' for n in cols) + "</tr>"
        ss = {}
        for nm, lst in c.sinsal.items():
            for pil, gz in lst: ss.setdefault(pil, []).append(nm.replace("살", "") if nm in ("백호살", "괴강살", "홍염살") else nm)
        tbl = (f'<table class="mchart"><tr><th style="width:18%"></th>' + "".join(f"<th>{hdr[n]}</th>" for n in cols) + "</tr>"
               + row("천간 십신", lambda n: "<b>일간</b>" if n == "일" else P[n]["stem_tengod"])
               + row("천간", lambda n: P[n]["gz"][0], lambda n: f"big el-{STEM_ELK[P[n]['gz'][0]]}")
               + row("지지", lambda n: P[n]["gz"][1], lambda n: f"big el-{BR_ELK[P[n]['gz'][1]]}")
               + row("지지 십신", lambda n: P[n]["branch_tengod"])
               + row("지장간", lambda n: " ".join(h["stem"] for h in P[n]["hidden"]), "small")
               + row("12운성", lambda n: P[n]["12운성"])
               + row("신살", lambda n: " · ".join(ss.get(n, [])) or "-", "small") + "</table>")
        mx = max(c.wt.values())
        colr = {"목": "#2f7a4c", "화": "#c0392b", "토": "#a0762a", "금": "#7d8590", "수": "#1f4e8c"}
        bars = "".join(f'<div class="row"><span class="lab el-{e}">{e}({EL_HAN[e]})</span><div class="track"><div class="fill" style="width:{max(4, int(c.wt[e] / mx * 100))}%;background:{colr[e]}"></div></div><span class="v">{c.cnt[e]}개 · 가중 {c.wt[e]}</span></div>'
                       for e in sorted(c.wt, key=lambda e: -c.wt[e]))
        top_c = max(c.cnt, key=c.cnt.get); top_w = max(c.wt, key=c.wt.get)
        zero = [e for e in c.cnt if c.cnt[e] == 0]
        note = f"겉 글자로는 {josa(EL_WORD[top_c] + '(' + top_c + ')', '이')} 가장 많고" + (f", 지장간까지 넣으면 {josa(EL_WORD[top_w] + '(' + top_w + ')', '이')} 가장 강해요." if top_w != top_c else ", 지장간까지 넣어도 가장 강해요.")
        if zero:
            zw = '·'.join(EL_WORD[e] + '(' + e + ')' for e in zero)
            note += f" {josa(zw, '는')} 겉에 없지만, ‘없는 오행’은 결핍이 아니라 <b>운에서 들어올 때 크게 반응하는 자리</b>예요."
        gm = GROUP_MEAN_F if c.gender == "F" else GROUP_MEAN_M
        grows = "".join(f'<tr><td><b>{g}</b> {c.gcount[g]}</td><td{" class=small" if not c.groups[g] else ""}>{" · ".join(c.groups[g]) or "(지장간 " + " ".join(c.hidden_groups[g][:3]) + ")" if c.hidden_groups[g] else " · ".join(c.groups[g]) or "-"}</td><td class="small">{gm[g].replace("·", " · ")}</td></tr>'
                        for g in sorted(c.gcount, key=lambda g: -c.gcount[g]))
        # 신강
        mbe, dbe = BR_ELK[c.mb], BR_ELK[c.db]
        sup = (c.gel["비겁"], c.gel["인성"])
        s1 = f"태어난 달 {josa(c.mb + '(' + EL_WORD[mbe] + ')', '은')} {c.dm} 일간을 {'돕고' if c.deukryeong else '돕지 못하고'}(<b>득령 {'O' if c.deukryeong else 'X'}</b>), "
        s1 += f"앉은 자리 {c.db}({EL_WORD[dbe]}){('도 힘이 돼요' if c.deukryeong else '는 힘이 돼요') if c.deukji else ('도 힘이 되지 못해요' if not c.deukryeong else '는 힘이 되지 못해요')}(<b>득지 {'O' if c.deukji else 'X'}</b>). "
        roots = [n for n in c.P if n != "일" and BR_ELK[c.P[n]["gz"][1]] in sup] + [n for n in c.P if n not in ("일",) and STEM_ELK[c.P[n]["gz"][0]] in sup]
        if roots:
            s1 += f"{'·'.join(dict.fromkeys(POS_NAME.get(n, n) if True else n for n in roots))[:20].replace('지', '주')} 쪽에서 {EL_WORD[c.gel['비겁']]}·{EL_WORD[c.gel['인성']]}의 도움이 있어요. "
        if c.neutral:
            conc = ("돕는 힘과 빼는 힘이 비슷한 중화 사주라, <b>운에서 오는 기운에 따라 흐름이 잘 바뀌는</b> 편이에요. 좋은 해에 움직이고 약한 해에 쉬어 가면 균형이 잘 맞아요.")
        else:
            yg_ = c.el_group[c.yong]
            conc = (f"기운이 넘치는 만큼 <b>{ {'식상': '재능으로 쓰고 표현할 때', '재성': '현실의 성과로 바꿀 때', '관성': '책임 있는 자리에서 쓸 때'}.get(yg_, '쓰고 나누고 표현할 때') }</b> 운이 열리는 사주라, 용신 {V.elw(c.yong)}의 해가 특히 반가워요." if c.strong else
                    f"혼자 모든 것을 짊어지면 지치지만, <b>{ {'비겁': '내 편과 동료가 받쳐 주면', '인성': '배움과 어른의 도움이 받쳐 주면'}.get(yg_, '배움과 내 편이 받쳐 주면') }</b> 크게 자라는 사주라, 용신 {V.elw(c.yong)}의 해가 특히 반가워요.")
        how = f"천간에 뜬 기운이 지지에 뿌리를 두었는지(통근·투간)와 태어난 달의 힘(월령 {c.month_state})까지 넣어 계산했어요. "
        s1 += f"{how}결론은 {STEM[c.dm]['ko']} 일간 기준 <span class=\"em\">{c.st_label}</span>{particle(c.st_label, '이에요')}. 나를 돕는 기운의 비율이 {int(c.ratio * 100)}%예요(40~50%면 중화로 봐요). {conc}"
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>명식(命式)과 오행</h2>
 <div class="sub">원국: 타고난 기운의 지도 · 만세력 계산(KASI 기준 음력·절기, 지방시 보정)</div>
 {tbl}
 <div class="two" style="margin-top:4mm">
  <div><h3 style="margin-top:0">오행 분포</h3><div class="bars">{bars}</div><p class="small" style="margin-top:2mm">{note}</p></div>
  <div><h3 style="margin-top:0">십신 분포</h3><table><tr><th>그룹</th><th>글자</th><th>뜻</th></tr>{grows}</table></div>
 </div>
 <h3>신강·신약 판단</h3><p>{s1}</p>
 <div class="box small"><b class="gold">출생 정보 검증</b> · {self.verify_text()}</div>
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def _alt_hour(self, lon):
        """다른 경도 관례로 본 시주와 그 관례에서 시 경계까지 거리(분). 실패하면 None."""
        inp = self.inp
        if not self.c.time_known or not inp.get("time"): return None
        try:
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):
                r2 = E.run_saju(inp["date"], inp["time"], inp.get("lunar"), inp.get("leap"), self.c.gender, str(lon), self.c.now.year, self.c.now.year + 1)
            p2 = {p["name"]: p for p in r2["pillars"]}
            lt = r2["time_correction"]["local_solar_time"][-5:]; hh, mm = map(int, lt.split(":")); m = hh * 60 + mm
            d = min(min(abs(m - h * 60), 1440 - abs(m - h * 60)) for h in range(1, 25, 2))
            return p2["시"]["gz"], d
        except Exception:
            return None

    def verify_text(self):
        c = self.c; r = c.r; inp = self.inp; out = []
        if inp.get("lunar"):
            out.append(f"{josa('음력 ' + inp['date'] + ('(윤달)' if inp.get('leap') else ''), '은')} 양력 <b>{r['solar_date']}</b>{particle(r['solar_date'], '이에요')}(한국천문연구원 음력 기준).")
        jq = r.get("jieqi", {})
        if jq.get("prev"):
            out.append(f"절입 {jq['prev'][0]}({jq['prev'][1].replace(' KST', '')}) 뒤, {jq['next'][0]}({jq['next'][1].replace(' KST', '')}) 전이라 월주는 <b>{c.P['월']['gz']}</b>, 년주는 <b>{c.P['년']['gz']}</b>" + ("이고, " if c.time_known else "예요."))
        if c.time_known:
            tc = r["time_correction"]; lt = tc["local_solar_time"][-5:]
            hh, mm = map(int, lt.split(":")); m = hh * 60 + mm
            bnd = min(abs(m - (h * 60)) for h in range(1, 25, 2)) if True else 0
            bnd = min(bnd, abs(m + 1440 - 23 * 60) if m < 60 else 999)
            hb = c.P["시"]["gz"][1]
            s = f"{'' if jq.get('prev') else ''}출생 시각 {josa(_hm_ko(inp.get('time')), '은')} {inp.get('place_label', '')} 경도 보정{' (그해 서머타임 1시간 포함)' if str(tc.get('utc_offset_at_birth', '')).startswith('10') else ''} 시 <b>{lt}</b>{josa('(' + f"{tc['correction_minutes']:+.1f}분)", '로')} {hb}시예요."
            if bnd <= 12: s = s[:-len("예요.")] + f"인데, <b>시(時)의 경계에서 {bnd}분 거리</b>라 출생 시각이 조금만 달라도 시주가 바뀔 수 있어요."
            rule = inp.get("time_rule", "경도")
            if rule == "30분":
                s = f"출생 시각 {josa(_hm_ko(inp.get('time')), '은')} 흔한 만세력 방식(표준시에서 30분 보정)으로 <b>{lt}</b>, {hb}시예요."
                if bnd <= 12: s = s[:-len("예요.")] + ("인데, <b>시(時)의 경계에 딱 걸린 시각</b>이에요." if bnd == 0 else f"인데, <b>시(時)의 경계에서 {bnd}분 거리</b>예요.")
                pl = inp.get("place"); lon = S.PLACES.get(pl) if pl in S.PLACES else None
                if lon is None:
                    try: lon = float(pl)
                    except (TypeError, ValueError): lon = None
                alt = self._alt_hour(lon) if lon is not None else None
                if alt and alt[0] != c.P["시"]["gz"]:
                    s += f" 출생지 {inp.get('place_label', '')} 경도로 정밀하게 보정하면 <b>{alt[0]}시</b>가 되는 경계 사주라, 이 감정서는 의뢰하신 {hb}시 기준으로 풀었어요."
            else:
                alt = self._alt_hour(127.5)  # sync1114: 흔한 만세력 관례(표준시 −30분, 동경 127.5°)와 비교
                if alt:
                    agz, amin = alt
                    if agz != c.P["시"]["gz"]:
                        s += f" 참고로 시계 시각에서 30분만 빼는 흔한 만세력 방식으로는 <b>{agz}시</b>로 볼 수 있어, 시주가 달라지는 경계 사주예요."
                    elif bnd > 12 and amin <= 10:
                        s += f" 시계 시각에서 30분만 빼는 흔한 만세력 방식으로도 {agz}시지만, 그 방식으로는 {'시(時)의 경계에 딱 걸려요' if amin == 0 else f'시(時)의 경계에서 {amin}분 거리예요'}."
            if jq.get("prev") and out: out[-1] += s; s = None
            if s: out.append(s)
        else:
            out.append("출생 시각을 몰라 시주 없이 6글자로 봤어요. 자녀·말년·성향 일부는 참고 정도로 읽어 주세요.")
        di = r["daeun_info"]
        ys_ = c.P['년']['gz'][0]
        out.append(f"{'남성' if c.gender == 'M' else '여성'}이고 년간이 {'양' if ys_ in '甲丙戊庚壬' else '음'}의 {josa(PS.ST_KO[ys_], '이라')} 대운은 {di['direction']}, 대운수 {di['대운수']}(정밀 {di.get('exact', '')}, 첫 대운 약 {di.get('exact_start_date', '')[:7].replace('-', '년 ')}월)이고, 나이는 모두 만 나이예요.")
        for w in r.get("warnings", []):
            if "절기" in w or "경계" in w: out.append(esc(w))
        return " ".join(out)

    # ------------------------------------------------------------ P3 용신
    def p_yongsin(self):
        c = self.c; G = c.gel
        steps, concl = self.yongsin_parts()
        gm = GROUP_MEAN_F if c.gender == "F" else GROUP_MEAN_M
        # 격국
        gy = c.gyeok
        src = c.gyeok_src
        if gy in ("건록격", "양인격"):
            gtxt = f"월지 {josa(c.mb, '가')} 일간 {c.dm}의 {'양인' if gy == '양인격' else '건록'} 자리라 <b>{gy}</b>{particle(gy, '이에요')}. {GYEOK[gy]} {NT.gyeok_strength_line(c)}"
        else:
            tp = getattr(c, "gyeok_transparent", False)
            gtxt = f"월지 {c.mb}의 지장간 {'·'.join(S.HIDDEN[c.mb])} 가운데 {src}{'가 천간에 그대로 떠 있어' if tp else '(정기)를 기준으로'} <b>{gy}</b>{particle(gy, '이에요')}. {GYEOK[gy]} {NT.gyeok_strength_line(c)}"
        # 신살
        rows = ""
        for nm in ["천을귀인", "문창귀인", "건록", "화개", "도화", "홍염살", "역마", "양인", "괴강살", "백호살"]:
            if nm in c.sinsal:
                lst = c.sinsal[nm]
                rows += f'<tr><td><b>{nm}</b>{" ×" + str(len(lst)) if len(lst) > 1 else ""}</td><td>{" · ".join(POS_NAME[p] + " " + gz[1] for p, gz in lst)}</td><td class="small">{NT.sinsal_text(nm, lst, SINSAL.get(nm, ""))}</td></tr>'
        if not rows: rows = '<tr><td colspan="3" class="small">원국에 두드러진 신살이 없어요. 신살은 양념일 뿐, 오행과 십신의 흐름이 본바탕이에요.</td></tr>'
        # 합충
        rel_items = self.chart_rel_items()
        rel_items.sort(key=lambda x: 0 if "완성" in x else 1 if ("충" in x or "형" in x) else 2)
        gmg = c.gongmang
        gm_el = BR_ELK[gmg[0]]
        rel_items.append(f"<b>공망 {gmg[0]}·{gmg[1]}</b>: {c.el_group[gm_el]}({gm[c.el_group[gm_el]].split('·')[0]})의 자리가 비어 그 일에는 확신이 늦은 편이지만, 운에서 {josa(gmg[0] + '·' + gmg[1], '이')} 오는 해에 그 자리가 채워져요.")
        lis = "".join(f"<li>{x}</li>" for x in (rel_items[:4] + rel_items[-1:] if len(rel_items) > 4 else rel_items))
        return f'''<section class="page tight"><div class="in">
 <h2><span class="no">{self.nxt()}</span>용신·격국·신살·합충</h2>
 <div class="sub">사주를 살리는 기운과, 원국에 새겨진 특별한 표식</div>
 <h3 style="margin-top:0">용신(用神) {c.yong} · 희신(喜神) {c.hee}: 이렇게 정했어요</h3>
 <ol class="small" style="padding-left:5mm;margin-top:0">{"".join(f"<li>{s}</li>" for s in steps)}</ol>
 <div class="box dark"><span class="gold">결론</span> · {concl}</div>
 <h3>격국: {gy}</h3><p>{gtxt}</p>
 <h3>신살(神殺): 양념처럼 읽는 특별한 표식</h3>
 <table><tr><th style="width:21%">신살</th><th style="width:17%">자리</th><th>의미 (전통 해석)</th></tr>{rows}</table>
 <h3>합·충·형 · 공망</h3><ul class="small">{lis}</ul>
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def yongsin_parts(self):
        """tier1115: 용신을 정한 단계와 결론 (기본 등급의 짧은 용신 설명에도 써요)"""
        c = self.c; G = c.gel
        steps = []
        season = MONTH[c.mb][0]
        if "조후" in c.method:
            steps.append(f"<b>조후(온도)</b>: {season}생, {SEASON_NOTE[c.season].replace('사주예요', '사주인데')}, 원국에 {josa(EL_WORD[c.yong] + '(' + c.yong + ')', '이')} 가중 {josa(c.wt[c.yong], '로')} 부족해 <b>{josa(c.yong, '을')} 먼저 씁니다</b>.")
        elif c.season in ("winter", "summer"):
            need = "화" if c.season == "winter" else "수"
            steps.append(f"<b>조후(온도)</b>: {season}생, {SEASON_NOTE[c.season].replace('사주예요', '사주지만')}, 원국에 {josa(EL_WORD[need] + '(' + need + ')', '이')} 가중 {josa(c.wt[need], '로')} 이미 있어 <b>온도 문제는 크지 않아요</b>.")
        else:
            steps.append(f"<b>조후(온도)</b>: {season}생, {SEASON_NOTE[c.season].replace('강해요', '강하고')}, {MONTH[c.mb][0]}생은 온도가 크게 치우치지 않아 강약(억부)을 중심으로 봐요.")
        if not c.weak_path:
            big = "비겁" if c.wt[G["비겁"]] >= c.wt[G["인성"]] else "인성"
            steps.append(f"<b>억부(강약)</b>: 일간을 돕는 {josa(big + '(' + EL_WORD[G[big]] + ')', '이')} 강한 {josa(c.st_label, '이에요')}. 넘치는 힘을 <b>{'흘려 쓰는' if big == '비겁' else '현실로 바꾸는'} {c.el_group[c.yong]}({c.yong})</b>{particle(c.el_group[c.yong] + '(' + c.yong + ')', '이')} 필요해요.")
        else:
            top = max(c.drain, key=c.drain.get)
            steps.append(f"<b>억부(강약)</b>: 일간의 힘을 빼는 쪽 중 {josa(top + '(' + EL_WORD[G[top]] + ')', '이')} 가장 무거운 {josa(c.st_label, '이에요')}. "
                         + ("중화이지만 관성(살)이 가장 무거워, 인성으로 살의 압박을 풀어 일간을 돕는 <b>살인상생(殺印相生)</b>으로 봐요. " if c.salin else ""))
            ylabel = ("나를 세워 주는 비겁" if c.el_group[c.yong] == "비겁" else "나를 먹여 주는 인성" if c.el_group[c.yong] == "인성" else c.el_group[c.yong]) + f"({c.yong})"
            steps[-1] += f"그래서 <b>{ylabel}</b>{particle(ylabel, '이')} 반가워요."
        if c.gu:
            steps.append(f"<b>희신·기신</b>: 용신을 돕는 {josa(el_full(c.hee), '이')} 희신, 지나치면 부담이 되는 {josa(el_full(c.gi), '과')} {josa(el_full(c.gu), '이')} 조심할 기운이에요.")
        else:
            steps.append(f"<b>희신·기신</b>: 용신을 돕는 {josa(el_full(c.hee), '이')} 희신, 지나치면 부담이 되는 {josa(el_full(c.gi), '이')} 조심할 기운이에요.")
        gm = GROUP_MEAN_F if c.gender == "F" else GROUP_MEAN_M
        concl = (f"용신 <b>{el_full(c.yong)}</b> = {gm[c.el_group[c.yong]]} / 희신 <b>{el_full(c.hee)}</b> = {gm[c.el_group[c.hee]]} / "
                 f"기신 <b>{el_full(c.gi)}</b> 과다 = {gm[c.el_group[c.gi]].split('·')[0]}의 부담")
        return steps, concl

    def chart_rel_items(self):
        c = self.c; out = []; seen = set()
        nm2pos = {"년": "년", "월": "월", "일": "일", "시": "시"}
        for s in c.r["relations"]:
            parts = s.split(" ")
            if len(parts) < 3 or "-" not in parts[0]: 
                if s.startswith("삼합 완성") or s.startswith("방합 완성"):
                    out.append(f"<b>{esc(s)}</b>: 한 오행이 국(局)을 이뤄 그 기운이 아주 강해요.")
                continue
            a, b = parts[0].split("-"); chars = parts[1]; kind = " ".join(parts[2:])
            pa, pb = a[0], b[0]
            if "천간충" in kind:
                key = ("천간충", chars)
                txt = REL_CHART["천간충"].format(pos=f"{POS_NAME[pa].replace('지', '간')}·{POS_NAME[pb].replace('지', '간')}")
            elif "천간합" in kind:
                txt = REL_CHART["천간합"].format(pos=f"{POS_NAME[pa].replace('지', '간')}·{POS_NAME[pb].replace('지', '간')}")
            elif kind == "충":
                txt = REL_CHART["충"].format(pos=f"{POS[pa]}·{POS[pb]}")
            elif "형" in kind:
                txt = REL_CHART["형"].format(pos=f"{POS[pa]}·{POS[pb]}")
            elif kind.startswith("육합"):
                txt = REL_CHART["육합"].format(pos=f"{POS[pa]}·{POS[pb]}")
            elif kind.startswith("삼합 반합") or kind.startswith("삼합 가합"):
                txt = REL_CHART["반합"].format(pos=f"{POS[pa]}·{POS[pb]}")
            elif kind in ("원진",):
                txt = REL_CHART["원진"].format(pos=f"{POS[pa]}·{POS[pb]}")
            else:
                continue
            k = (chars, kind.split("(")[0])
            if k in seen: continue
            seen.add(k)
            out.append(f"<b>{chars} {kind.split('(')[0].replace('삼합 ', '')}</b> ({a}↔{b}): {txt}")
        if not out:
            out.append("<b>큰 충·형이 없는 원국</b>: 타고난 구조가 안정적이라 운의 흐름을 그대로 타기 좋아요.")
        return out

    # ------------------------------------------------------------ P4 성격·재물
    def p_persona_money(self):
        m = self.money_paras()
        return f'''<section class="page tight"><div class="in">
 <h2><span class="no">{self.nxt()}</span>성격</h2>
 <div class="sub">일간 → 월지 → 강한 십신 순서로 읽었어요</div>
 {self.persona_html()}
 <div class="rule"></div>
 <h2><span class="no">{self.nxt()}</span>재물운</h2>
 <div class="sub">재성의 자리 · 재물 창고 · 식신생재 · 강약과 재물 · 돈 버는 방식</div>
 {m}
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def p_persona(self):
        """tier1115: 성격만 (재물은 주제 심층에서)"""
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>성격</h2>
 <div class="sub">일간 → 월지 → 강한 십신 순서로 읽었어요</div>
 {self.persona_html()}
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def persona_html(self):
        c = self.c; st = STEM[c.dm]
        top = max(c.gcount, key=lambda g: (c.gcount[g], c.gw[g]))
        absent = [g for g in c.gcount if c.gcount[g] == 0]
        tg_top = "·".join(dict.fromkeys(c.groups[top]))
        p = [f'<p><span class="tag">일간 {c.dm}{EL_HAN[c.dm_el]}</span>{josa(st["img"], "예요")}. {st["pers"]} {NT.dm_strength_line(c)} {NT.day_pillar_line(c)}</p>',
             f'<p><span class="tag">월지 {c.mb} · {c.gyeok}</span>{MONTH[c.mb][0]}에 태어나 {SEASON_NOTE[c.season].replace("사주예요", "사주라") if "사주예요" in SEASON_NOTE[c.season] else SEASON_NOTE[c.season] + "."} {GYEOK[c.gyeok].split(". ")[0]}.</p>',
             f'<p><span class="tag">강한 십신 · {top} {c.gcount[top]}</span>{josa(top + "(" + V.elw(c.gel[top]) + ")", "이")} {c.gcount[top]}개로 가장 많아, {GROUP_STRONG[top].split(". ")[0].rstrip(".")}. {NT.strong_role_line(c, top)}</p>']
        if absent:
            p.append(f'<p><span class="tag">{absent[0]} 0</span>{AV.fuse(st["ko"] + " 일간에게 " + absent[0] + particle(absent[0], "는") + " " + EL_WORD[c.gel[absent[0]]] + "의 기운인데, " + GROUP_ABSENT[absent[0]])} {NT.absent_line(c, absent[0])}</p>')
        stage = c.P["일"]["12운성"]
        weak = st["weak"]
        if not c.strong:
            dr = max(c.drain, key=c.drain.get)
            adv = {"재성": "책임(재성)이 많아 부탁을 거절하지 못하고 혼자 다 떠안는 경향이 있어요",
                   "관성": "책임과 압박(관성)이 커서 남의 시선과 기대에 스스로를 몰아붙이기 쉬워요",
                   "식상": "표현과 재능(식상)으로 에너지를 많이 써서 쉽게 지치기 쉬워요"}[dr]
            tip = "“이건 제가 못 해요”라고 말하는 연습부터 해 보세요"
        else:
            adv = {"비겁": "주관이 강해 남의 조언을 흘려듣거나 혼자 결정하는 경향이 있어요",
                   "인성": "생각과 준비가 길어 실행이 늦어지는 경향이 있어요"}.get(max(("비겁", "인성"), key=lambda g: c.gw[g]), "")
            tip = "말을 꺼내기 전에 한 번 더 듣는 습관이 관계를 지켜 줘요"
        lab_ = c.st_label.split("(")[0].split(",")[0]
        box = f'<b class="gold">보완하면 좋은 점</b> · {st["ko"]} 일간이 {lab_}하면 {adv}. 일간의 약점은 {josa(weak, "이라")}, {tip}. {NT.tip_line(c)}'
        return "".join(p) + f'\n <div class="box small">{box}</div>'

    def money_paras(self):
        c = self.c; G = c.gel; n = c.gcount["재성"]; out = []
        jpos = [nm for nm, p in c.P.items() if (nm != "일" and TG_GROUP[p["stem_tengod"]] == "재성") or TG_GROUP[p["branch_tengod"]] == "재성"]
        gos = [p["gz"][1] for p in c.P.values() if p["gz"][1] in "辰戌丑未" and any(STEM_ELK[h] == G["재성"] for h in S.HIDDEN[p["gz"][1]])]
        if n:
            s = f"<b>① 재성의 자리</b> · {josa('재성(돈, ' + el_full(G['재성']) + ')', '이')} {'·'.join(POS_NAME.get(x, x).replace('지', '주') for x in dict.fromkeys(jpos))}에 {n}개 있어요. " + NT.money_palace_line(c, jpos) + " "
        else:
            s = f"<b>① 재성의 자리</b> · {josa('재성(돈, ' + el_full(G['재성']) + ')', '이')} 겉에 없어요. 지장간에 {len(c.hidden_groups['재성'])}개 숨어 있어 <b>운에서 재성({EL_WORD[G['재성']]})이 들어올 때 크게 반응</b>해요. "
        if gos: s += f"{'·'.join(gos)}은 재성 {EL_WORD[G['재성']]}을 품은 ‘창고(庫)’ 글자라 <span class=\"em\">버는 것보다 모으고 지키는 재주</span>가 있어요."
        out.append(f"<p>{s}</p>")
        if c.gcount["식상"] and (n or c.hidden_groups["재성"]):
            out.append(f"<p><b>② 재능이 돈이 되는 길(식신생재)</b> · {NT.sikjae_line(c)}</p>")
        else:
            out.append(f"<p><b>② 돈이 들어오는 통로</b> · 식상(재능)이 {'적어' if not c.gcount['식상'] else '있지만'} 돈은 {JB.t('money_channel') + '(관성·인성)을 통해' if c.gcount['관성'] + c.gcount['인성'] >= 2 else '내 힘과 인맥(비겁)을 통해'} 들어오는 편이라, {STEM[c.dm]['ko']} 일간은 실력을 먼저 키우면 돈이 따라와요.</p>")
        if (not c.strong and not c.neutral) and n >= 2:
            out.append("<p><b>③ 재다신약: 그릇을 키우면 돈도 커져요</b> · 돈의 기운이 일간보다 커서, 무리하게 큰돈을 다루면 몸과 마음이 먼저 지쳐요. 보증·대출로 크게 벌이는 방식은 맞지 않아요. 대신 <b>자격·전문성과 체력·내 편</b>을 키울 때마다 담을 수 있는 재물이 한 단계씩 커져요. " + NT.money_yong_line(c) + "</p>")
        elif c.strong and c.gcount["비겁"] >= 3:
            out.append("<p><b>③ 군겁쟁재: 지키는 힘이 재산</b> · 내 기운이 강하고 경쟁자(비겁)도 많아 번 돈이 사람·지출로 새기 쉬워요. " + JB.r("동업·보증은 서면으로") + ", 통장은 용도별로 나누세요. " + NT.money_yong_line(c) + "</p>")
        elif c.strong:
            out.append(f"<p><b>③ 신강한 사주의 재물</b> · {STEM[c.dm]['ko']} 일간이 신강해 돈을 다뤄도 버티는 힘이 있지만, 자신감이 앞서 한 번에 크게 거는 투자가 이 사주의 가장 큰 위험이에요. 재성({EL_WORD[G['재성']]})이 들어오는 해에도 나눠서 들어가세요. " + NT.money_yong_line(c) + "</p>")
        else:
            out.append(f"<p><b>③ 신약한 사주의 재물</b> · {STEM[c.dm]['ko']} 일간이 신약해 돈을 쫓기보다 실력과 건강을 먼저 챙길 때 돈이 따라오는 구조라, 큰돈은 나눠서 천천히 다루세요. " + NT.money_yong_line(c) + "</p>")
        jj = c.r["ten_gods_count"].get("정재", 0); pj = c.r["ten_gods_count"].get("편재", 0)
        bd = self.best_daeun_money()
        way = f"<b>{JB.t('salary')}</b>(정재)" if jj >= pj and (jj or pj) else "<b>활동·거래·사업 감각</b>(편재)" if pj else "<b>실력과 자격으로 받는 보수</b>"
        out.append(f"<p><b>④ 돈 버는 방식</b> · 기본은 {way}이고, " + (f"{self.peak_phrase(bd)} {TG_GROUP[bd['지지십신']]} 운이 들어오는 <b>{bd['gz']} 대운(만 {bd['a0']}~{bd['a1']}세, {bd['y0']}~{bd['y1']})</b>{particle(str(bd['y1']), '이에요')}." + ("" if c.tone(c.score(bd['gz'])[0]) == "good" else " 다만 크게 불어나는 정점이라기보다 고르게 가는 대운이라, 나눠서 쌓는 쪽이 맞아요.") if bd else self.no_peak() + "." + (self.money_window() + "." if self.money_window() else "")) + "</p>")
        ma = self.cur_daeun_adv("money", 2)
        y1 = self.Y + 1
        ma += self.yadv(y1, "money", 1, lab=f"{y1}년")[:1]
        out.append(f'<div class="advbox small"><b class="gold">재물 · 지금 조심할 점과 보완할 점</b><ul>{AV.fmt(ma)}</ul></div>')
        kw = []
        if gos: kw.append(f"<b>창고형 재물</b> ({'·'.join(gos)})")
        if c.gcount["식상"]: kw.append(f"<b>재능형 수입</b> (식상 {'·'.join(c.groups['식상'])})")
        if (not c.strong and not c.neutral) and n >= 2: kw.append("<b>그릇을 키우는 돈</b> (재다신약)")
        if "천을귀인" in c.sinsal: kw.append("<b>귀인이 주는 기회</b> (천을귀인)")
        if not kw: kw.append(f"<b>{el_full(c.yong)}의 해에 커지는 돈</b>")
        out.append(f'<div class="box dark" style="margin-top:2.5mm;font-size:10pt"><span class="gold">{esc(self.who)}의 재물 키워드</span><br>{" · ".join(kw)}</div>')
        return "\n".join(out)

    # ------------------------------------------------------------ P5 직업·연애·건강
    def p_job_love_health(self):
        c = self.c; J = self.jlh_parts()
        rows, mv, para, lis, hl, hn, top = J["rows"], J["mv"], J["para"], J["lis"], J["hl"], J["hn"], J["top"]
        return f'''<section class="page tight"><div class="in">
 <h2><span class="no">{self.nxt()}</span>{JB.t("p5_title")}</h2>
 <div class="sub">격국({c.gyeok}) + 용신({c.yong}) + 강한 십신({top})</div>
 <table><tr><th style="width:33%">{JB.t("p5_th")}</th><th>이유</th></tr>{rows}</table>
 <p class="small" style="margin-top:2mm"><b>{JB.t("move_label")}</b> · {mv}</p>
 <div class="advbox small"><ul>{AV.fmt(self.cur_daeun_adv("job", 1) + self.yadv(self.Y + 1, "job", 1, lab=f"{self.Y + 1}년")[:1])}</ul></div>
 <div class="rule"></div>
 <h2><span class="no">{self.nxt()}</span>{'연애·부부·가정' if c.age(self.Y) < 50 else '부부·가정·관계'}</h2>
 <div class="sub">배우자궁(일지) · {'여성의 관성' if c.gender == 'F' else '남성의 재성'} · 관계의 결</div>
 <p>{para}</p>
 <ul class="small">{"".join(lis)}{AV.fmt(self.cur_daeun_adv("rel", 1)[:1] + self.yadv(self.Y + 1, "rel", 1, lab=f"{self.Y + 1}년")[:1])}</ul>
 <div class="rule"></div>
 <h2><span class="no">{self.nxt()}</span>건강 경향</h2>
 <div class="sub">전통 오행 배속에 따른 ‘관리 포인트’이며 의학적 진단이 아니에요</div>
 <ul class="small">{"".join(hl)}</ul>
 <p class="small">__PALM_HEALTH__{hn}</p>
 <div class="advbox small"><ul>{AV.fmt(self.cur_daeun_adv("health", 1)[:1] + self.yadv(self.Y + 1, "health", 1, lab=f"{self.Y + 1}년")[:1])}</ul></div>
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def jlh_parts(self):
        """tier1115: 직업·연애·건강 페이지의 부품 (주제 심층에서도 같은 근거를 써요)"""
        c = self.c; G = c.gel
        picks = []
        gname, greason = CAREER_GYEOK[c.gyeok]; picks.append((gname, greason))
        top = max(c.gcount, key=lambda g: (c.gcount[g], c.gw[g]))
        if CAREER_GROUP[top][0] != gname: picks.append(CAREER_GROUP[top])
        used = set(x.strip() for a, _ in picks for x in a.replace("/", " · ").split("·"))
        yc = [x for x in ELEM[c.yong]["careers"].split("·") if x.strip() not in used]
        picks.append((" · ".join(yc[:5]) or ELEM[c.yong]["careers"], f"용신 {el_full(c.yong)}의 업종이라 일할수록 운이 살아나요."))
        rows = "".join(f'<tr><td><b>{"①②③"[i]} {a}</b></td><td class="small">{b}</td></tr>' for i, (a, b) in enumerate(picks[:3]))
        # 이직 흐름 (job1113: 직업 상황별)
        move = []
        for y in self.years[:5]:
            gz = E.year_gz(y); rels = c.relations_to_chart(*gz)
            if any(k == "충" and p == "월" for k, p, _, _ in rels): move.append((y, f"{c.tg(gz[1], True)} {josa(PS.BR_KO[gz[1]], '이')} " + JB.t("move_wol")))
            elif c.tg(gz[1], True) in ("정관", "편관") and self.ystar[y] >= 4: move.append((y, JB.t("move_gwan")))
        mv = " ".join(f"<b>{y}년</b>은 {t}예요." for y, t in move[:3]) or JB.t("move_none").replace("충은 없어요. ", f"충이 없어 {c.gyeok}의 바탕이 그대로 이어지니, ").replace("충은 없어요.", f"충이 없어 {c.gyeok}의 바탕이 그대로 이어져요.")
        if JB.CUR["job"] == "사업자":
            up = [y for y in self.years if self.ystar[y] >= 4][:3]; dn = [y for y in self.years[:5] if self.ystar[y] <= 2]
            def yr(ys): return f"{ys[0]}~{ys[-1]}" if len(ys) > 2 and ys[-1] - ys[0] == len(ys) - 1 else "·".join(map(str, ys))
            mv += (" 확장·신규 투자는 별이 높은 " + yr(up) + "년에 맞추고" if up else " 10년 안에 확장에 크게 유리한 해가 뚜렷하지 않아 확장은 작게 나눠 하고") + \
                  (", " + yr(dn) + "년에는 운영자금과 기존 거래처 관리에 집중하세요." if dn else ", 별이 낮은 해에는 운영자금부터 채우세요.")
        y1 = self.Y + 1
        mv += f" {y1}년에는 " + self.best_months_phrase(y1, 1)
        # 연애
        sp = c.tg(c.db, True)
        hidden_sp = [h for h in c.P["일"]["hidden"] if TG_GROUP[h["tengod"]] == ("관성" if c.gender == "F" else "재성")]
        star = "관성(남편)" if c.gender == "F" else "재성(아내)"
        sp_cnt = c.gcount["관성" if c.gender == "F" else "재성"]
        para = SPOUSE_PALACE[sp] + (" " + NT.palace_rel_line(c) if NT.palace_rel_line(c) else "")
        if hidden_sp: para += f" 배우자궁 속에 {hidden_sp[0]['tengod']} {hidden_sp[0]['stem']}이 숨어 있어 결국 {'바르고 책임감 있는' if '정' in hidden_sp[0]['tengod'] else '능력 있고 추진력 있는'} 사람과 맺어지는 모양이에요."
        para += " " + V.spouse_star_line(c, star, sp_cnt, "타입이에요")
        lis = []
        top2 = sorted(sorted(self.years, key=lambda y: -self.ysc[y])[:2])
        good2 = [y for y in top2 if self.ystar[y] >= 4]
        lis.append(f"<li><b>함께하는 사람이 있다면</b>: " + V.palace_line(c) + (f"가정의 큰 계획(내 집·저축·교육)은 별이 높은 해({'·'.join(map(str, good2))}년, {V.run_group(self, good2)} 운)에 함께 세우면 힘을 받아요." if good2 else "향후 10년은 크게 벌이기보다 함께 지키는 흐름이라, 큰 계획은 작게 나눠 차근차근 세우세요.") + "</li>")
        helper = (f" 천을귀인이 {'·'.join(dict.fromkeys(POS_NAME[p_] for p_, _ in c.sinsal['천을귀인'] if p_ in POS_NAME))}에 있어, {'·'.join(dict.fromkeys(NT.SIN_POS[p_] for p_, _ in c.sinsal['천을귀인'] if p_ in NT.SIN_POS)) or '가까운'} 쪽에서 만나는 사람의 소개와 도움을 가까이하세요.") if "천을귀인" in c.sinsal else ""
        lis.append(f"<li><b>혼자이시라면</b>: {V.ideal_line(c, sp)}{helper}</li>")
        kid_g = "식상" if c.gender == "F" else "관성"
        if c.time_known:
            hp = c.P["시"]; kid = [x for x in (TG_GROUP[hp["stem_tengod"]], TG_GROUP[hp["branch_tengod"]]) if x == kid_g]
            lis.append(f"<li><b>자녀</b>: {'여성' if c.gender == 'F' else '남성'}의 자녀는 {kid_g}, 곧 {V.elw(c.gel[kid_g])} 기운이에요. 시주(자녀궁)는 {hp['gz']}, 십신으로 {hp['stem_tengod']}·{josa(hp['branch_tengod'], '이라') if kid else hp['branch_tengod'] + '이고'}{' 자녀의 별이 자녀궁에 있어 자녀 인연이 좋아요' if kid else ', 자녀의 별이 들어오는 대운·세운에 자녀운이 강해져요'}.</li>")
        # 건강
        hi = max(c.wt, key=c.wt.get); lo = min(c.wt, key=c.wt.get)
        def _hl(e, txt, over):
            org, _, adv_ = txt.partition(". ")
            role = NT.ROLE[c.fav[e]] + "인 " if c.fav[e] else ""
            if not adv_: return txt
            f_ = c.fav[e]
            if over and f_ > 0:  # 강한 용신·희신: '넘쳐(해)'라고 하면 모순 → 많이 쓰는 만큼 지치는 쪽으로
                return f"{role}{V.elw(e)} 기운은 많아도 나를 돕는 쪽이라 해가 되기보다 힘이 되지만, 많이 쓰는 만큼 {org} 쪽이 먼저 지치기 쉬우니, {adv_}"
            if not over and f_ < 0:  # 약한 기신·구신: 사주엔 나쁘지 않지만 몸의 회복력은 챙겨야
                return f"{role}{V.elw(e)} 기운은 약한 편이 사주에는 오히려 낫지만, 몸에서는 {org} 쪽 회복이 더딜 수 있으니, {adv_}"
            return f"{role}{V.elw(e)} 기운이 {'넘쳐' if over else '약해'} {org} 쪽을 살펴야 하니, {adv_}"
        hl = [f"<li><b>{EL_WORD[hi]}({hi}) 강함</b>: {_hl(hi, HEALTH_EXCESS[hi], True)}</li>"]
        hc = max(c.cnt, key=c.cnt.get)
        if hc != hi and c.cnt[hc] >= 3: hl.append(f"<li><b>{EL_WORD[hc]}({hc}) 글자 많음</b>: {_hl(hc, HEALTH_EXCESS[hc], True)}</li>")
        hl.append(f"<li><b>{EL_WORD[lo]}({lo}) 약함</b>: {_hl(lo, HEALTH_LACK[lo], False)}</li>")
        hp_ = NT.health_pair_line(c, hi, lo)
        if hp_: hl.append(f"<li><b>{EL_WORD[hi]}↔{EL_WORD[lo]}</b>: {hp_}</li>")
        if c.season in ("winter", "summer"):
            hl.append(f"<li><b>{MONTH[c.mb][0]}생</b>: {'몸을 따뜻하게, 겨울철 보온과 혈액순환' if c.season == 'winter' else '열을 식히고 수분 보충, 여름철 과로 주의'}.</li>")
        cy = [y for y in self.years[:4] if any(k == "충" for k, p, _, _ in c.relations_to_chart(*E.year_gz(y)) if p in ("일", "월"))]
        hn = (f"{'·'.join(map(str, cy))}년은 충이 드는 해라 약한 {V.elw(lo)} 쪽({HEALTH_LACK[lo].split('.')[0].split('·')[0]})부터 무리하지 말고 정기 검진을 챙기세요." if cy else f"가까운 몇 년은 큰 충이 없어, 약한 {V.elw(lo)} 쪽({HEALTH_LACK[lo].split('.')[0].split('·')[0]})만 꾸준히 챙기면 돼요.")
        return dict(rows=rows, picks=picks, mv=mv, move=move, para=para, lis=lis, hl=hl, hn=hn, top=top, hi=hi, lo=lo, cy=cy)

    # ------------------------------------------------------------ P6 대운
    def p_daeun(self):
        c = self.c; ps = c.daeun_periods()
        cur = c.current_daeun(self.Y)
        rows = ""; cur_i = None
        for i, p in enumerate(ps[:8]):
            sc = c.score(p["gz"])[0]; stn = c.stars(sc); tn = c.tone(sc)
            g1, g2 = TG_GROUP[p["천간십신"]], TG_GROUP[p["지지십신"]]
            fs, fb = c.fav[STEM_ELK[p["gz"][0]]], c.fav[BR_ELK[p["gz"][1]]]
            flow = NT.daeun_flow(g1, g2, DAEUN_THEME3[g2][tn].split(". ")[0])
            if fs >= 1 and fb >= 1: flow = f"{FAV_WORD[fs]} {p['gz'][0]}·{FAV_WORD[fb]} {p['gz'][1]}가 함께 오는 대운이라 " + flow
            elif fb >= 1: flow = f"지지에 {FAV_WORD[fb]} {p['gz'][1]}가 받쳐 " + flow
            elif fb <= -2 and tn != "bad": flow += ". 무리한 확장은 조심"
            rr = [r for r in c.relations_to_chart(*p["gz"]) if r[0] in ("충", "육합", "반합") and r[1] in ("일", "월")]
            if rr: flow += f". {rr[0][2]}{'충' if rr[0][0] == '충' else '합'}({POS_NAME[rr[0][1]]})"
            is_cur = cur and p["gz"] == cur["gz"]; is_next = cur and i > 0 and ps[i - 1]["gz"] == cur["gz"]
            if is_cur: cur_i = i
            tag = "<b>현재.</b> " if is_cur else "<b>다음.</b> " if is_next else ""
            hl = ' class="hl"' if is_cur or is_next else ""
            ak, at = AV.short_advice(c, p["gz"], sc, "daeun")
            rows += f'<tr{hl}><td>{p["a0"]}~{p["a1"]}</td><td>{p["y0"]}~{p["y1"]}</td><td class="serif">{p["gz"]}</td><td class="small">{p["천간십신"]} / {p["지지십신"]}</td><td class="small">{tag}{flow}.{AV.fmt_inline(ak, at)}</td><td class="stars">{stars(stn)}</td></tr>'
        paras = ""
        for lab, idx in (("현재 대운", cur_i), ("다음 대운", (cur_i + 1) if cur_i is not None else 0)):
            if idx is None or idx >= len(ps): continue
            p = ps[idx]; g1, g2 = TG_GROUP[p["천간십신"]], TG_GROUP[p["지지십신"]]
            psc = c.score(p["gz"])[0]; tn = c.tone(psc)
            t = f"천간 {josa(p['gz'][0], '는')} {p['천간십신']}, 지지 {josa(p['gz'][1], '는')} {josa(p['지지십신'], '이에요')}. {DAEUN_THEME3[g1][tn]}"
            if g2 != g1: t += f" 지지로는 {DAEUN_THEME3[g2][tn].split('. ')[0].replace('10년이에요', '흐름이 함께해요')}."
            fb = c.fav[BR_ELK[p["gz"][1]]]
            if tn == "bad" and fb >= 1:
                t += f" 그래도 지지 {josa(p['gz'][1], '가')} {'용신' if fb == 2 else '희신'}이라 바탕의 힘은 남아 있어, 무리하지 않으면 충분히 버틸 수 있어요."
            else:
              t += {2: f" 지지 {p['gz'][1]}({p['지지십신']})가 용신이라 <b>{PS.GMEAN[TG_GROUP[p['지지십신']]]} 쪽에서 뿌리부터 힘이 붙는 시기</b>예요.", 1: f" 지지 {p['gz'][1]}({p['지지십신']})가 희신이라 {PS.GMEAN[TG_GROUP[p['지지십신']]]} 쪽으로 무리 없이 성장해요.",
                  0: "", -1: f" {p['gz'][1]}({p['지지십신']})의 기운은 조금 부담이라 속도 조절이 필요해요.", -2: f" {p['gz'][1]}({p['지지십신']})의 기운이 무거워 <b>지키면서 실력을 쌓는</b> 쪽이 맞아요."}[fb]
            for k, pos, det, el in c.relations_to_chart(*p["gz"]):
                if k == "충" and pos in ("일", "월"):
                    t += f" 대운 {det[0]}({c.tg(det[0], True)})가 {POS_NAME[pos]} {josa(det[1], '를')} 충해, 이 10년 안에 {POS[pos]}의 큰 변화가 한두 번 있기 쉬워요. " + (
                        "머무르기보다 움직일 때 길이 열려요." if tn == "good" else
                        f"변화가 오면 서두르지 말고, {JB.t('daeun_prep') if pos == '월' else '옮길 곳을'} 미리 알아봐 두면 흔들림이 줄어요." if tn == "mid" else
                        f"이 시기의 변화는 스스로 고르기 어려운 경우가 많으니, 계약·이사·{josa(JB.t('move'), '은')} 한 번 더 확인하고, 비상금을 넉넉히 두면 무난히 넘길 수 있어요.")
                    break
            items = AV.period_advice(c, p["gz"], psc, "gen", key=lab, max_items=2, scope="이 10년은", kind="daeun") + AV.period_advice(c, p["gz"], psc, "money" if idx == cur_i else "job", key=lab, max_items=1, lead=False, kind="daeun")[:1]
            paras += f"<h3>{lab} · {p['gz']} (만 {p['a0']}~{p['a1']}세, {p['y0']}~{p['y1']})</h3><p>{t}</p><div class=\"advbox small\"><ul>{AV.fmt(items)}</ul></div>"
        di = c.r["daeun_info"]
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>대운(大運) 흐름</h2>
 <div class="sub">10년마다 바뀌는 인생의 계절 · {di['direction']} · 대운수 {di['대운수']} · 나이는 만 나이 · 대운은 그해 {ps[0]['month']}월 무렵 바뀌어요</div>
 <table><tr><th style="width:11%">나이</th><th style="width:15%">연도</th><th style="width:10%">대운</th><th style="width:16%">십신</th><th>흐름</th><th style="width:12%">운세</th></tr>{rows}</table>
 {paras}
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    # ------------------------------------------------------------ P7 올해
    def month_rows(self, ms, hl_cut=4, year_label=False):
        rows = ""
        for a, b, gz, n in ms:
            sc = self.c.score(gz)[0]; stn = self.star(sc)
            end = b - E.timedelta(days=1)
            per = f"{a.month}/{a.day}~{end.month}/{end.day}"
            if year_label and a.year != self.Y: per = f"{a.year} " + per
            pt = self.month_point(gz)
            if stn == 5: pt = "<b>좋은 달.</b> " + pt
            ak, at = AV.short_advice(self.c, gz, sc, "month")
            pt += AV.fmt_inline(ak, at)
            rows += f'<tr{" class=hl" if stn >= hl_cut else ""}><td>{per}</td><td class="serif">{gz}</td><td class="small">{self.c.tg(gz[0])}/{self.c.tg(gz[1], True)}</td><td class="small">{pt}</td><td class="stars">{stars(stn)}</td></tr>'
        return rows

    POSK = ("합", "귀인", "도화", "좋은", "반가운", "희신", "용신")
    NEGK = ("충", "형", "원진", " 해 ", "파 ", "과다", "무거", "기신", "구신")

    def _ev_pick(self, ev, st):
        """verdict1116: 해 페이지 관계 문구를 별 방향에 맞춰 골라요(★1~2에 좋은 말만, ★4~5에 나쁜 말만 남지 않게), 최대 2개."""
        out = []; neg_n = 0
        for t, d in ev:
            pos = any(k in t for k in self.POSK) and not any(k in t for k in ("충", "형", "원진"))
            if st <= 2 and pos:
                if "귀인" in t:   # 귀인은 보완 수단으로만
                    d = d.split(" 가운데")[0].replace("자리로 귀인이 들어와", "자리에 귀인이 있어") + " 가운데 도움을 청할 사람이 있으니, 어려운 일은 혼자 버티지 말고 추천·소개로 풀어 가세요."
                    out.append((t, d))
                continue
            if st >= 4 and not pos:
                neg_n += 1
                if neg_n > 0: continue   # 좋은 해의 주의점은 조언 칸 1개로 모아요
            out.append((t, d))
        return out[:2]

    def tpx(self):
        if not hasattr(self, "_tpx"):
            import topics as TP
            self._tpx = TP.Topics(self)
        return self._tpx

    VY = {5: "적극 움직이는 해", 4: "움직여도 좋은 해", 3: "균형을 잡는 해", 2: "보완하며 지키는 해", 1: "몸과 살림을 지키는 해"}

    def verdict_line(self, y):
        """verdict1116: 해마다 맨 위 한 줄 결론 — 별점이 정해요. 할 일 1 · 조심/안 할 일 1 · 이사·계약 판정."""
        c = self.c; gz = E.year_gz(y); st = self.ystar[y]; tone = AV.star_tone(st)
        p = PS.P(c, gz, self.ysc[y], "year", y, tone=tone); W = PS.words()
        fc = "unf" if p.f <= -1 else "fav"; cau, rem = AV.SHORT2[p.g][fc]
        do = AV.go_short(c, p, str(y)) if tone == "good" else PS.fill(PS.pick(rem, c, "vr" + str(y)), **W)
        dont = PS.fill(PS.pick(cau, c, "vc" + str(y)), **W)
        mst = self.tpx().ystars("move")[1][y]
        mv = "해도 됨" if mst >= 4 else "신중" if mst == 3 else "미룸"
        cst = self.tpx().ystars("money")[1][y]
        cv = "해도 됨" if cst >= 4 else "신중" if cst == 3 else "미룸"
        return (f'<div class="box small" style="margin:1.6mm 0"><b class="vd vd{st}">결론</b> <b>{self.VY[st]}</b> · <b class="adv-g">할 일</b> {do} · '
                f'<b class="adv-c">조심</b> {dont} · <b>이사</b> {mv} · <b>계약</b> {cv}</div>')

    def year_page(self, y, months, cur=False):
        c = self.c; gz = E.year_gz(y)
        st, bt = c.tg(gz[0]), c.tg(gz[1], True)
        stY = self.ystar[y]
        ev = self._ev_pick(self.year_events(gz), stY)
        if stY >= 4: ev = [(t, _no_but(d)) for t, d in ev]   # release1116: 좋은 해의 조심은 맨 위 결론줄 한 번만
        dae = c.current_daeun(y)
        lc = E.lichun(y)
        fs_, fb_ = c.fav[STEM_ELK[gz[0]]], c.fav[BR_ELK[gz[1]]]
        dom = fb_ if abs(fb_) >= abs(fs_) else fs_
        theme = TG_THEME[bt if abs(fb_) >= abs(fs_) else st][1].split(". ")[0].rstrip(".") + "."
        # verdict1116: 주된 기운이 이 사주에 맞지 않거나 ★2 이하면 좋은 말 한 줄(테마 문장)은 빼요
        summ = (f"천간 {josa(PS.ST_KO[gz[0]], '은')} {st}({TG_THEME[st][0]})로 이 사주엔 {NT.ROLE[fs_]}, 지지 {josa(PS.BR_KO[gz[1]], '은')} {bt}({TG_THEME[bt][0]})로 {josa(NT.ROLE[fb_], '이에요')}."
                + (" " + theme if dom >= 0 and stY >= 3 else ""))
        lis = "".join(f"<li><b>{t}</b>: {d}</li>" for t, d in ev) or "<li>원국과 크게 부딪히거나 묶이는 글자가 없어 흐름이 순한 해예요.</li>"
        rows = self.month_rows(months, year_label=cur)
        advs = self.yadv(y, "gen", 2)
        if stY >= 4: advs = [x for x in advs if x[0] != "조심"] or advs[:1]   # release1116: 좋은 해의 조심은 결론줄 한 번만
        advh = f'<div class="advbox small"><b class="gold">{y}년 {"할 일" if stY >= 4 else "할 일 · 조심 · 보완"}</b><ul>{AV.fmt(advs)}</ul></div>'
        if cur:
            mtitle = f"남은 {y}년 월별 운"; extra = self.tips_box(y, months) + self.preview_box(y)
        else:
            mtitle = f"{y}년 월별 운"
            extra = '<p class="tiny" style="margin-top:1.6mm">※ 월의 경계는 절기 절입일 기준이에요(입춘·경칩·청명…). 다음 해 1월(소한~입춘 전)은 아직 이 해의 기운이에요.</p>'
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>{y} {ko(gz)}({gz})년: {self.year_title(y)}</h2>
 <div class="sub">만 {c.age(y)}세 · 세운 {st}/{bt} · 대운 {dae['gz'] if dae else '-'} · 입춘 {lc.strftime('%Y-%m-%d %H:%M')} (한국시간) · 운세 {stars(self.ystar[y])}</div>
 {self.verdict_line(y)}
 <div class="box dark"><span class="gold">한 줄 요약</span> · {summ}</div>
 <ul class="small">{lis}</ul>
 {advh}
 <h3>{mtitle}</h3>
 <table><tr><th style="width:{'22' if cur else '14'}%">{'기간' if cur else '양력'}</th><th style="width:10%">월건</th><th style="width:14%">십신</th><th>포인트</th><th style="width:11%">운세</th></tr>{rows}</table>
 {extra}
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def preview_box(self, y):
        rows = ""
        for yy in (y, y + 1, y + 2):
            gz = E.year_gz(yy)
            ak, at = self.yshort(yy)
            rows += f'<tr{" class=hl" if self.ystar[yy] >= 4 else ""}><td><b>{yy}</b></td><td class="serif">{gz}</td><td class="small">{tgj(self.c, gz)}</td><td class="small">{self.year_line(yy)}.</td><td class="small">{AV.vd(self.ystar[yy])} <b class="{AV.cls(ak)}">{ak}</b> {at}</td><td class="stars">{stars(self.ystar[yy])}</td></tr>'
        return f'<h3>앞으로 3년 미리 보기</h3><table><tr><th style="width:8%">연도</th><th style="width:8%">간지</th><th style="width:12%">십신</th><th>흐름</th><th style="width:22%">할 일 · 조심/보완</th><th style="width:11%">운세</th></tr>{rows}</table>'

    def tips_box(self, y, months):
        if not months: return ""
        sc = sorted(months, key=lambda m: -self.c.score(m[2])[0])
        g = sc[0]; b = sc[-1]
        tips = [f"{g[0].month}월({g[2]}, {V.month_reason(self.c, g[2], True).replace('의 달', '').replace(' 달', '')})에 들어온 제안·만남·계획은 적극적으로",
                f"{b[0].month}월({b[2]}, {V.month_reason(self.c, b[2], False).replace('의 달', '').replace(' 달', '')})에는 큰 지출·충동적 결정을 미루기",
                f"{ELEM[self.c.yong]['colors'].split('·')[0]} 계열 소품 하나로 용신 {self.c.yong}의 기운 더하기"]
        return f'<div class="box small"><b class="gold">{y}년 남은 기간 실천 팁</b> · ' + " ".join(f"{'①②③'[i]} {t}" for i, t in enumerate(tips)) + f". {STEM[self.c.dm]['ko']} 일간에게는 용신 {V.elw(self.c.yong)}의 기운을 미리 채워 두는 것이 {y + 1}년을 준비하는 가장 좋은 출발점이에요.</div>"

    def p_years(self):
        now = self.now
        cur_ms = [m for m in self.mp if m[1] > now and (m[0].year == self.Y or (m[0].year == self.Y + 1 and m[3] == "小寒"))]
        nxt_ms = [m for m in self.mp if m[0].year == self.Y + 1 and m[3] != "小寒"]
        return [self.year_page(self.Y, cur_ms, cur=True), self.year_page(self.Y + 1, nxt_ms)]

    # ------------------------------------------------------------ P9 10년
    def p_decade(self):
        c = self.c
        top2 = sorted(self.years, key=lambda y: -self.ysc[y])[:2]
        love1 = (self.best_love_years(1) or [None])[0]
        rows = ""
        for y in self.years:
            gz = E.year_gz(y); s = self.ystar[y]
            line = self.year_line(y)
            tag = ""
            if y in top2: tag = f"<b>10년 중 상위 {sorted(top2).index(y) + 1}.</b> "
            ak, at = self.yshort(y)
            rows += f'<tr{" class=hl" if s >= 4 else ""}><td>{"<b>%d</b>" % y if tag else y}</td><td>{c.age(y)}</td><td class="serif">{gz}</td><td class="small">{tgj(c, gz)}</td><td class="small">{tag}{line}.</td><td class="small">{AV.vd(s)} <b class="{AV.cls(ak)}">{ak}</b> {at}</td><td class="stars">{stars(s)}</td></tr>'
        good = self.money_years(); bad = [y for y in self.years if self.ystar[y] <= 2]
        jj = c.r["ten_gods_count"].get("정재", 0); pj = c.r["ten_gods_count"].get("편재", 0)
        fit = "적금·청약·연금처럼 쌓이는 자산, 내 실력에 투자(자격·교육), 실거주 부동산" if (not c.strong or jj >= pj) else "사업·거래·투자처럼 움직이는 자산, 단 분산과 원칙 매매"
        ms_ = V.money_struct(c)
        avoid = JB.r(V.AVOID[ms_]) + (". 재다신약이라 감당 못 할 돈은 새요" if ((not c.strong and not c.neutral) and c.gcount['재성'] >= 2) else ". " + JB.r("동업은 반드시 서면으로") if c.strong else "")
        money = (f"<li><b>맞는 방식</b>: {fit}.</li><li><b>피할 방식</b>: {josa(avoid, '은')} 기신 {EL_WORD[c.gi]}의 해에 특히 멀리하세요.</li>"
                 + (f"<li><b>좋은 시기</b>: {', '.join(map(str, good))}년({'·'.join(dict.fromkeys(V.run_group(self, [y]) for y in good))} 운).</li>" if good else "<li><b>좋은 시기</b>: 돈 쪽으로 ★4 이상인 해는 없어요. 큰돈은 꼭 필요한 것만 움직이세요.</li>")
                 + f"<li><b>보수적으로</b>: {', '.join(map(str, bad)) or '특별히 나쁜 해는 없어요'}{'년(' + '·'.join(dict.fromkeys(V.run_group(self, [y]) for y in bad)) + ' 운)' if bad else ''}.</li>"
                 + f"<li><b class=\"adv-c\">조심</b>: {V.CAREFUL[ms_]}" + (", " + V.CONSERV[c.el_group[c.yong]] if bad else ", 목돈은 나눠서 들어가세요.") + "</li>")
        phase = ""
        nm = {"up": "도약기", "mid": "준비·안정기", "down": "지키는 시기"}
        for cat, ys in self.runs():
            span = f"{ys[0]}~{ys[-1]}" if len(ys) > 1 else f"{ys[0]}"
            lows = [y for y in ys if self.ystar[y] <= 2]
            rg = V.run_group(self, ys)
            phase += f"<li><b>{nm[cat]} · {span}</b>: {rg}({V.elw(c.gel[rg]) if rg in c.gel else PS.GMEAN.get(rg, '')}) 운이 중심 · " + V.PHASE_DECADE[cat][rg] + ".</li>"
        bd = self.best_daeun_money()
        if bd: phase += f"<li><b>{'재물 정점' if c.tone(c.score(bd['gz'])[0]) == 'good' else '재물 흐름이 나은 대운'} · 만 {bd['a0']}~{bd['a1']}세</b> ({bd['gz']} 대운, {bd['천간십신']}·{bd['지지십신']} 운).</li>"
        else: phase += f"<li><b>재물 정점</b>: {STEM[c.dm]['ko']} 일간에게 재성은 {EL_WORD[c.gel['재성']]}인데, 이 기운이 크게 받쳐 주는 정점 대운은 뚜렷하지 않아요. {V.NO_PEAK2[ms_]}." + (self.money_window() + "." if self.money_window() else "") + "</li>"
        phase += "<li>__PALM_TIMING__</li>"
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>향후 10년: 재물 · 일 · 가정의 시기표</h2>
 <div class="sub">{self.Y}~{self.Y + 9} 세운 × 대운 × 용신({c.yong}·{c.hee}) · 나이는 그해 생일 이후 만 나이</div>
 <table><tr><th style="width:7%">연도</th><th style="width:6%">나이</th><th style="width:7%">간지</th><th style="width:11%">십신</th><th>흐름</th><th style="width:23%">조심 · 보완</th><th style="width:11%">종합</th></tr>{rows}</table>
 <div class="two" style="margin-top:3.4mm">
  <div class="box" style="margin:0"><h3 style="margin-top:0">재물·투자운</h3><ul class="small" style="margin:0">{money}</ul></div>
  <div class="box" style="margin:0"><h3 style="margin-top:0">인생 흐름</h3><ul class="small" style="margin:0">{phase}</ul></div>
 </div>
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    # ------------------------------------------------------------ 개운법·한계
    def p_end(self, palm=False):
        c = self.c; Y, H = ELEM[c.yong], ELEM[c.hee]
        rows = "".join(f'<tr><td><b>{lab}</b></td><td class="small">{a}</td><td class="small">{b}</td></tr>' for lab, a, b in [
            ("색", f"{Y['colors']}. {Y['where']}", f"{H['colors']}. {H['where']}"),
            ("방향", f"{Y['dir']}. {Y['dir_use']}", f"{H['dir']}. {H['dir_use']}"),
            ("숫자", Y["nums"], H["nums"]), ("시간·계절", Y["time"], H["time"]), ("생활", Y["life"], H["life"])])
        adv = []
        y1 = self.Y + 1
        adv.append(f"<li><b>지금~{y1}년 1월</b>: {self.tips_short()}</li>")
        adv.append(f"<li><b>{y1}년</b>: {self.best_months_phrase(y1, 2)}</li>")
        for cat, ys in self.runs():
            if ys[0] <= y1: ys = [y for y in ys if y > y1]
            if not ys: continue
            span = f"{ys[0]}~{ys[-1]}년" if len(ys) > 1 else f"{ys[0]}년"
            lows = [y for y in ys if self.ystar[y] <= 2]
            rg = V.run_group(self, ys)
            adv.append(f"<li><b>{span}" + (f" · {rg} {V.elw(c.gel[rg])} 운" if rg in c.gel else "") + "</b>: " + AV.fuse(JB.r(V.PHASE_END[cat][rg])) + "</li>")
        yg = c.el_group[c.yong]
        mind = {"비겁": "혼자 다 짊어지지 말고, 내 편을 곁에 두고, 체력을 지키세요.",
                "인성": "배움을 멈추지 말고, 쉬어 갈 줄 알고, 도와주는 사람을 곁에 두세요.",
                "식상": "가진 재능을 꺼내 표현하고, 생각을 바로 작게 실행해 보세요.",
                "재성": "생각을 현실의 숫자로 바꾸고, 결과를 차곡차곡 쌓으세요.",
                "관성": "책임 있는 자리를 피하지 말고, 원칙을 지키며 올라가세요."}[yg]
        mind = f"{STEM[c.dm]['ko']} 일간이 {c.st_label.split('(')[0].split(',')[0]}한 사주라 " + mind
        lim = []
        if not c.time_known: lim.append("출생 시각을 몰라 시주 없이 판단했어요.")
        lim.append("결혼 여부와 현재 상황을 알 수 없어 여러 경우를 함께 적었어요.")
        lim.append("대운 교체 시점과 월운 별점은 계산상 근사치이며, 같은 사주라도 환경과 선택에 따라 다르게 펼쳐져요.")
        basis = "전통 명리학(자평명리)" + ("과 전통 수상학" if palm else "")
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>개운법 · 조언</h2>
 <div class="sub">용신 {el_full(c.yong)} · 희신 {josa(el_full(c.hee), "를")} 생활 속에서 쓰는 방법</div>
 <table><tr><th style="width:18%">항목</th><th>{el_full(c.yong)} · 용신</th><th>{el_full(c.hee)} · 희신</th></tr>{rows}</table>
 <p class="tiny" style="margin-top:1.4mm">줄이면 좋은 것: {ELEM[c.gi]['colors'].split('·')[0]} 일색의 옷차림, {ELEM[c.yong]['reduce'].split(', ')[-1]} 정도예요. 완전히 피하기보다 {ELEM[c.yong]['colors'].split('·')[0]}처럼 용신 {EL_WORD[c.yong]}의 색을 한 가지 더하면 기신 {EL_WORD[c.gi]}의 기운이 누그러져요.</p>
 <h3>시기별 행동 조언</h3><ul class="small">{"".join(adv[:5])}</ul>
 <h3>마음가짐 한 가지</h3>
 <div class="box dark">{self.closing(mind)} __PALM_CLOSING__</div>
 <div class="rule"></div>
 <div class="tiny"><b>판독 참고와 한계</b> · __PALM_LIMIT__{" ".join(lim)}<br><br>
 <b>안내</b> · 이 감정서는 {basis}에 따른 해석이에요. 과학적으로 검증된 예측이 아니며 오락과 자기 이해를 위한 참고 자료예요. 건강·투자·법률 등 중요한 결정은 반드시 전문가와 상의하세요.</div>
</div><div class="foot">SONMYEONGRI · __PG__ · 손명리 {'사주 × 손금 교차' if palm else '사주 종합'} 감정서</div></section>'''

    def outlook(self):
        """앞으로의 흐름: good(10년 안 ★5가 있거나 다음/현재 대운이 좋음) / mid / bad"""
        c = self.c
        cur = c.current_daeun(self.Y); ps = c.daeun_periods()
        nxt = next((p for p in ps if cur and p["y0"] > cur["y0"]), None)
        dtn = [c.tone(c.score(p["gz"])[0]) for p in (cur, nxt) if p]
        n5 = sum(1 for y in self.years if self.ystar[y] == 5)
        n_low = sum(1 for y in self.years if self.ystar[y] <= 2)
        if n5 or "good" in dtn: return "good"
        if n_low >= 4 and "bad" in dtn: return "bad"
        return "mid"

    def closing(self, mind):
        """fix1113: 마무리 문장. 일간 이미지 × 계절 × 앞으로의 흐름 × 용신 그룹으로 조합해 사람마다 달라지게."""
        c = self.c; who = esc(self.who)
        img = STEM_CLOSING[c.dm].format(season=SEASON_WORD[c.season])
        ol = self.outlook()
        ups = [ys for cat, ys in self.runs() if cat == "up"]
        first_up = next((ys for ys in ups if ys[-1] > self.Y), None)
        if ol == "good":
            when = (f"지금이 {V.run_group(self, first_up)} 운이 받쳐 주는 때예요" if first_up and first_up[0] <= self.Y else
                    f"{first_up[0]}년 무렵부터 {V.run_group(self, first_up)} 운이 받쳐 주니, 그때를 위해 지금 힘을 모아 두세요" if first_up else "좋은 해를 골라 움직이면 돼요")
            bad_y = [y for y in self.years if self.ystar[y] <= 2]
            warn = f" 다만 {'·'.join(map(str, bad_y[:3]))}년처럼 {V.run_group(self, bad_y[:3])} 운이 부담인 해에는 {josa(V.gi_care(c, True), '을')} 먼저 챙기세요." if bad_y else " 다만 좋은 해일수록 욕심과 과로가 같이 커지니 속도를 조절하세요."
            body = f"{img}, {who}에게도 흐름이 바뀌는 때가 와요. {when}.{warn}"
        elif ol == "mid":
            when = (f" {first_up[0]}년 무렵이 다음 기회의 문이에요." if first_up else "")
            body = f"{img}, {who}의 운은 크게 오르내리기보다 고르게 흘러가는 편이에요. 서두르지 않고 쌓은 만큼 돌아와요.{when}"
        else:
            body = (f"{img}, 지금 {who}에게 필요한 건 크게 벌이는 힘보다 버티고 지키는 힘이에요. "
                    f"향후 몇 년은 지출과 건강을 먼저 챙기고, 모아 둔 힘을 다음 운에 쓰세요.")
        gx = GYEOK_CLOSING.get(c.gyeok, "")
        return f"{body} {gx} <b>{mind}</b>"

    def tips_short(self):
        cur_ms = [m for m in self.mp if m[1] > self.now and m[0].year <= self.Y + 1 and (m[0].year == self.Y or m[3] == "小寒")]
        if not cur_ms: return "다음 해 계획을 세우세요."
        g = max(cur_ms, key=lambda m: self.c.score(m[2])[0])
        st = self.ystar.get(self.Y, 3)   # release1116: 올해 별에 맞춰 한쪽만 말해요
        if st <= 2:
            return f"남은 달은 새로 벌이기보다 정리하는 쪽으로 쓰고, 연말연시에는 {josa(V.gi_care(self.c), '을')} 줄이세요."
        if st >= 4:
            return f"{'내년 ' if g[0].year > self.Y else ''}{g[0].month}월({g[2]})은 {V.month_reason(self.c, g[2], True)}이라 남은 기회를 잡기 좋아요."
        return f"{'내년 ' if g[0].year > self.Y else ''}{g[0].month}월({g[2]})은 {V.month_reason(self.c, g[2], True)}이라 기회를 잡기 좋고, 연말연시에는 {josa(V.gi_care(self.c), '을')} 줄이세요."

    # ------------------------------------------------------------ 종합(손금)
    def p_synth(self, items, lucky, spec):
        c = self.c; fl = spec.get("flags", {})
        js = fl.get("jaeun", {}).get("state", "none"); jn = fl.get("jaeun", {}).get("count", 1)
        sp = fl.get("saup", {}).get("state", "none"); fs = fl.get("fate", {}).get("state", "clear")
        hs = fl.get("head", {}).get("shape", "curve")
        bd = self.best_daeun_money()
        jj = c.r["ten_gods_count"].get("정재", 0); pj = c.r["ten_gods_count"].get("편재", 0)
        top2 = sorted(sorted(self.years, key=lambda y: -self.ysc[y])[:2])
        y35 = c.solar.year + 35; y50 = c.solar.year + 50
        if sp != "clear" and jj >= pj: way = "<b>전문가형·축적형</b>. 투기보다 실력과 저축"
        elif sp == "clear" and pj > jj: way = "<b>사업·거래형</b>. 판을 키울수록 커지는 돈"
        else: way = "<b>본업 + 감각</b>. 안정 수입 위에 기회를 얹기"
        f_ok = self.fifties_ok()
        when = (f"<b>50대({y50}년~)</b>에 재산이 가장 크게 쌓여요" if js == "above_heart" and f_ok else
                f"재운선은 50대를 가리키지만 사주의 50대 대운은 힘이 약해, <b>50대에는 지키고 관리하는 쪽</b>이 맞아요" if js == "above_heart" else
                f"젊어서부터 꾸준히, 특히 <b>{'·'.join(map(str, top2))}년</b>" if js == "long" else f"사주의 좋은 해 <b>{'·'.join(map(str, top2))}년</b>이 기준점")
        love1 = (self.best_love_years(1) or [None])[0]
        tal = {"moon": "기획·창작·교육", "curve": "기획·교육·콘텐츠", "straight": "분석·실무·금융", "mercury": "영업·투자·말"}.get(hs, "기획")
        rows = [("돈 버는 방식", f"{'정재 중심(' + JB.t('salary_short') + ')' if jj >= pj else '편재 중심(활동·거래)'}{' + 재다신약' if ((not c.strong and not c.neutral) and c.gcount['재성'] >= 2) else ''}", f"사업선 {items[1]['tag']}", way),
                ("재물이 커지는 때", f"{bd['gz']} 대운(만 {bd['a0']}~{bd['a1']}세)" if bd else "뚜렷한 정점 대운 없음", f"재운선 {items[0]['tag']}", when),
                ("수입원", f"정재 {jj} · 편재 {pj}", f"재운선 {'뚜렷하지 않음' if js == 'none' or not jn else str(jn) + '가닥'}", "<b>본업 + 하나 더</b>" if jn >= 2 or pj else "<b>한 우물</b>을 깊게"),
                ("일·도약", f"좋은 해 {'·'.join(map(str, top2))}", f"운명선 {items[2]['tag']}", f"<b>{y35}~{y35 + 3}년</b>이 커리어의 분기점" if fs != "none" else "운명선이 뚜렷하지 않은 형 · 자유롭게 자기 길을 만드는 형"),
                ("재능", f"{c.gyeok}", f"두뇌선 {items[4]['tag']}", f"{tal}에서 빛남"),
                ("사랑", f"배우자궁 {c.tg(c.db, True)}", f"감정선 {items[5]['tag']}", "천천히 고르고 <b>깊고 오래</b> 가는 인연" if fl.get("heart", {}).get("clarity", "clear") == "clear" else "표현을 늘릴수록 깊어지는 인연"),
                ("체력", c.st_label, f"생명선 {items[3]['tag']}", "체력·활력·추진력이 좋음, <b>과로만 조심</b>" if fl.get("life", {}).get("venus", "wide") == "wide" else "<b>휴식과 수면</b>이 최우선")]
        tr = "".join(f'<tr><td><b>{a}</b></td><td class="small">{b}</td><td class="small">{p}</td><td class="small">{d}</td></tr>' for a, b, p, d in rows)
        mrows = []
        for cat, ys in self.runs():
            a0, a1 = c.age(ys[0]), c.age(ys[-1])
            mtxt = {"up": "<b>기회.</b> 운이 받쳐 주는 시기. 계획을 실행하되 과욕은 금물.", "mid": "준비와 선택의 시기. 실력·저축·관계를 다지기.",
                    "down": "<b>지키는 시기.</b> 새로 벌이기보다 지출과 건강을 점검하며 대비하기."}[cat]
            mrows.append((ys[0], f'<tr{" class=hl" if cat == "up" else ""}><td>{ys[0]}~{ys[-1]}</td><td>{a0}~{a1}세</td><td class="small">{mtxt}</td></tr>'))
        if bd: mrows.append((bd["y0"], f'<tr class="hl"><td>{bd["y0"]}~{bd["y1"]}</td><td>{bd["a0"]}~{bd["a1"]}세</td><td class="small"><b>재물 규모 최대.</b> {bd["gz"]} 대운. 체력과 ‘나눠 맡기기’가 조건.</td></tr>'))
        if js == "above_heart" and f_ok: mrows.append((y50, f'<tr class="hl"><td>{y50}~{y50 + 12}</td><td>50~62세</td><td class="small"><b>만년의 복.</b> 재운선이 말하는 50~55세 이후. 쌓아 둔 재물이 드러나요.</td></tr>'))
        elif js == "above_heart": mrows.append((y50, f'<tr><td>{y50}~{y50 + 12}</td><td>50~62세</td><td class="small"><b>지키는 50대.</b> 재운선은 이 시기를 가리키지만 사주 대운의 힘이 약해, 늘리기보다 지키고 관리할 때 복이 남아요.</td></tr>'))
        mrows = "".join(x for _, x in sorted(mrows))
        first_up = next((ys for cat, ys in self.runs() if cat == "up"), None)
        concl = (f"{josa(self.who, '은')} <b>{'젊어서 크게 벌기보다 실력과 저축으로 차곡차곡 쌓아' if js != 'long' else '일찍부터 재물과 인연이 닿아'}"
                 f"{' ' + str(first_up[0] // 10 * 10) + '년대 ' + ('초반' if first_up[0] % 10 < 5 else '후반') + '에 도약하고' if first_up else ''}"
                 f"{' 50대에 크게 거두는' if js == 'above_heart' and f_ok else ' 좋은 해마다 한 단계씩 올라서는'}</b> 사주이자 손이에요. 서두르지 않는 것이 가장 큰 재테크예요.")
        lk = ", ".join(lucky) if lucky else "뚜렷한 대박손금은 없어요"
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>사주 × 손금 종합</h2>
 <div class="sub">두 가지 체계가 같은 말을 하는 곳이 가장 믿을 만한 결론이에요 · 대박손금: {lk}</div>
 <table><tr><th style="width:17%">주제</th><th style="width:28%">사주가 말하는 것</th><th style="width:27%">손금이 말하는 것</th><th>종합</th></tr>{tr}</table>
 <h3>{esc(self.who)} 인생의 재물 지도</h3>
 <table><tr><th style="width:20%">시기</th><th style="width:16%">나이</th><th>흐름</th></tr>{mrows}</table>
 <div class="box dark" style="margin-top:3mm"><span class="gold">한 문장 결론</span> · {concl}</div>
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''
