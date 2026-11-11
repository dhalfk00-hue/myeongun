# -*- coding: utf-8 -*-
"""Chart → 감정서 HTML 페이지 (규칙 기반 문장 조립)."""
import html
from datetime import datetime
import engine as E
import saju as S
from engine import STEM_ELK, BR_ELK
from texts import *

def esc(s): return html.escape(str(s))
def elsp(ch): 
    e = STEM_ELK.get(ch) or BR_ELK.get(ch)
    return f'<span class="el-{e}">{ch}</span>'
def stars(n): return "★" * n
def ko(gz): return S.gz_ko(gz)
def josa(word, a, b):
    ch = word[-1]
    if "가" <= ch <= "힣":
        return word + (a if (ord(ch) - 0xAC00) % 28 else b)
    return word + a
def el_full(e): return f"{e}({EL_HAN[e]})"
def tgj(c, gz):  # '식신/상관'
    return f"{c.tg(gz[0])}/{c.tg(gz[1], True)}"


class Report:
    def __init__(self, c, name=None, inp=None, now=None):
        self.c = c; self.name = name; self.inp = inp or {}
        self.now = now or datetime.now()
        self.Y = self.now.year
        self.who = (name + "님") if name else "고객님"
        self.years = list(range(self.Y, self.Y + 10))
        self.ysc = {y: c.score(E.year_gz(y))[0] for y in self.years}
        srt = sorted(self.ysc.values(), reverse=True)
        # 10년 분포로 별점 기준을 정함 (상위 2 = ★5 후보, 다음 3 = ★4, 다음 3 = ★3, 하위 2 = ★2)
        self.cut5 = max((srt[1] + srt[2]) / 2, 0.8)
        self.cut4 = (srt[4] + srt[5]) / 2
        self.cut3 = (srt[7] + srt[8]) / 2
        self.ystar = {y: self.star(s) for y, s in self.ysc.items()}
        self.love = {y: c.love_score(E.year_gz(y)) + 0.15 * self.ysc[y] for y in self.years}
        self.mp = E.month_pillars(self.Y, self.Y + 1)
        self.pg = 0
        self.no = 0

    def star(self, s):
        if s >= self.cut5: return 5
        if s >= self.cut4: return 4
        if s >= self.cut3: return 3
        return 2

    def nxt(self):
        self.no += 1
        return f"{self.no:02d}"

    # ------------------------------------------------------------ 공통 분석 문장
    def year_events(self, gz, short=False):
        """세운/월운 간지 → [(제목, 설명)]"""
        c = self.c; s, b = gz; out = []
        rels = c.relations_to_chart(s, b)
        seen = set(); wj_done = set()
        for kind, pos, det, el in rels:
            key = (kind, pos)
            if key in seen: continue
            seen.add(key)
            if kind == "충":
                txt = {"월": "직장 환경·부서·이직, 부모님 댁이나 거처의 변화예요. 미리 준비한 변화라면 좋은 방향으로 풀려요.",
                       "일": "배우자·거처·생활 패턴이 바뀌어요. 이사·독립·관계 정리 같은 일이 생기기 쉬우니 서두르지 말고 조율하세요.",
                       "년": "집안·윗사람 쪽 일로 신경 쓸 일이 생겨요. 집안 행사·부모님 건강을 챙기세요.",
                       "시": "자녀·아랫사람·미래 계획에 변동이 있어요. 계획을 수정하고 다시 세우는 해예요."}[pos]
                out.append((3, f"{det[0]}{det[1]}충 ({POS_NAME[pos]} · {POS[pos]})", txt,
                            f"{det[0]}{det[1]}충: " + {"월": "직장·환경 변화", "일": "거처·관계 변화", "년": "집안 일", "시": "계획 변동"}[pos]))
            elif kind in ("육합", "반합") and pos in ("일", "월", "시"):
                good = c.fav.get(el, 0) >= 0
                txt = {"일": "배우자궁과 합해요. 인연·동거·결혼 이야기, 함께할 사람이 생기기 쉬워요.",
                       "월": "직장 자리와 합해요. 협력자·좋은 제안·소속이 생기기 쉬워요.",
                       "시": "자녀·미래의 자리와 합해요. 새 계획과 아랫사람의 도움이 들어와요."}[pos]
                if not good: txt += f" 다만 합해서 생기는 {el} 기운은 부담이라 욕심은 줄이세요."
                out.append((2, f"{det[0]}{det[1]} {'합' if kind == '육합' else '반합'}({el}) · {POS_NAME[pos]}", txt,
                            f"{det[0]}{det[1]}합: " + {"일": "인연·제안", "월": "협력·좋은 제안", "시": "새 계획"}[pos]))
            elif kind == "천간합" and pos == "일":
                out.append((2, f"{s}{c.dm}합 (일간)", "일간과 합해요. 마음이 묶이는 인연·좋은 제안·계약이 들어오는 기운이에요.", f"{s}{c.dm}합: 좋은 제안·인연"))
            elif kind == "천간충" and pos == "일":
                out.append((2, f"{s}{c.dm}충 (일간)", "일간을 치는 기운이라 생각과 방향이 흔들려요. 큰 결정은 한 번 더 검토하세요.", f"{s}{c.dm}충: 결정은 신중히"))
            elif kind == "형" and pos in ("일", "월"):
                out.append((1, f"{det[0]}{det[1]}형 ({POS_NAME[pos]})", f"조정과 마찰의 기운이에요. {POS[pos]} 쪽 일을 혼자 떠안지 말고 나눠서 지세요.", f"{det[0]}{det[1]}형: 마찰 조정"))
            elif kind in ("원진", "해") and pos in ("일", "월", "년") and det not in wj_done:
                wj_done.add(det)
                if any(x[1].startswith(det) for x in out): continue
                out.append((0.5 if pos != "년" else 0.2, f"{det[0]}{det[1]} {kind} ({POS_NAME[pos]})", f"{POS[pos]} 쪽에 말 못 한 서운함이 쌓이기 쉬워요. 바쁠수록 말 한마디를 더 따뜻하게.", f"{det[0]}{det[1]}{kind}: 말조심"))
        if b in S.CHEONEUL[c.dm]:
            out.append((2, f"천을귀인 {b}", "도와주는 윗사람·귀인이 나타나요. 중요한 일은 추천·소개로 풀어 가세요.", "천을귀인: 귀인 도움"))
        yb, db = c.P["년"]["gz"][1], c.db
        if S.sinsal12(yb, b).startswith("연살") or S.sinsal12(db, b).startswith("연살"):
            out.append((1, f"도화 {b}", "매력이 드러나고 사람이 모여요. 만남·대면 일·홍보에 좋아요.", "도화: 매력·만남"))
        if S.sinsal12(yb, b).startswith("역마") or S.sinsal12(db, b).startswith("역마"):
            out.append((1, f"역마 {b}", "이동·출장·이사·해외 기운이에요. 움직일수록 기회가 와요.", "역마: 이동·출장"))
        be, se = BR_ELK[b], STEM_ELK[s]
        if c.fav[be] >= 1 or c.fav[se] >= 1:
            e = be if c.fav[be] >= c.fav[se] else se
            out.append((2, f"{FAV_WORD[c.fav[e]] or '좋은'} {el_full(e)}", f"나를 살리는 {EL_WORD[e]}의 기운이 들어와 힘이 붙어요.", f"{FAV_WORD[c.fav[e]] or '좋은 기운'} {e}: 힘이 붙음"))
        elif c.fav[be] <= -2:
            out.append((1, f"{FAV_WORD[-2]} {el_full(be)}", f"{EL_WORD[be]}의 기운이 무거워져요. 무리한 확장·과로를 피하고 기본을 지키세요.", f"{be} 과다: 무리 금지"))
        out.sort(key=lambda x: -x[0])
        if short: return [x[3] for x in out]
        return [(x[1], x[2]) for x in out]

    def month_point(self, gz):
        c = self.c; s, b = gz
        st, bt = c.tg(s), c.tg(b, True)
        head = f"{TG_SHORT[st]}·{TG_SHORT[bt]}" if TG_SHORT[st] != TG_SHORT[bt] else TG_SHORT[st]
        ev = self.year_events(gz, short=True)[:3]
        return head + (". " + ", ".join(ev) if ev else "") + "."

    def year_title(self, y):
        c = self.c; gz = E.year_gz(y); st = self.ystar[y]
        rels = c.relations_to_chart(*gz)
        if any(k == "충" and p in ("월", "일") for k, p, _, _ in rels):
            return "판을 다시 짜는 해" if st >= 3 else "흔들림을 다스리는 해"
        g1, g2 = TG_GROUP[c.tg(gz[0])], TG_GROUP[c.tg(gz[1], True)]
        if g1 == g2 and st >= 3:
            return {"식상": "빛나고 바쁜 해", "재성": "돈이 움직이는 해", "관성": "책임과 인정의 해", "인성": "배우고 채우는 해", "비겁": "내 힘으로 서는 해"}[g1] if st < 5 else "크게 도약하는 해"
        return {5: "크게 도약하는 해", 4: "기회가 열리는 해", 3: "다지고 준비하는 해", 2: "지키며 내실을 다지는 해"}[st]

    def year_line(self, y):
        c = self.c; gz = E.year_gz(y)
        st, bt = c.tg(gz[0]), c.tg(gz[1], True)
        a, b = TG_THEME[st][0], TG_THEME[bt][0]
        ev = self.year_events(gz, short=True)[:2]
        s = f"{a}과 {b}의 해" if a != b else f"{a}의 해"
        s = s.replace("과 ", "와 ") if "가" <= a[-1] <= "힣" and (ord(a[-1]) - 0xAC00) % 28 == 0 else s
        return s + (". " + ", ".join(ev) if ev else "")

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
        def cat(y): return "up" if self.ystar[y] >= 4 else "mid"
        for y in ys[1:]:
            if cat(y) == cat(cur[-1]): cur.append(y)
            else: out.append((cat(cur[0]), cur)); cur = [y]
        out.append((cat(cur[0]), cur))
        return out

    def best_daeun_money(self):
        c = self.c; best = None
        for p in c.daeun_periods():
            if p["y1"] <= self.Y or p["a0"] > 65: continue
            g = (TG_GROUP[p["천간십신"]], TG_GROUP[p["지지십신"]])
            sc = 0.5 * c.score(p["gz"])[0] + 2 * g.count("재성") + 0.5 * g.count("식상")
            if best is None or sc > best[0]: best = (sc, p)
        return best[1] if best else None

    # ------------------------------------------------------------ palm hooks
    def palm_cross(self, key, st):
        c = self.c
        if key == "jaeun" and st == "above_heart":
            y50 = c.solar.year + 50
            dp = [p for p in c.daeun_periods() if p["a0"] <= 55 and p["a1"] >= 50]
            dtxt = "·".join(f"{p['gz']} 대운(만 {p['a0']}~{p['a1']}세)" for p in dp)
            return f"50~55세는 {y50}~{y50 + 5}년이에요. 사주로는 {dtxt or '후반 대운'}에 해당해, 이 시기를 재물의 두 번째 정점으로 보세요."
        if key == "jaeun":
            p = self.best_daeun_money()
            ptxt = f"재물이 가장 크게 움직이는 {p['gz']} 대운(만 {p['a0']}~{p['a1']}세)" if p else "후반 대운"
            return f"사주에서는 {ptxt}이 재물의 정점이에요. {'재운선과 시기가 맞물려요.' if st == 'above_heart' else '손금의 재운선과 함께 이 시기를 재물의 기준점으로 삼으세요.'}"
        if key == "saup":
            jj = c.r["ten_gods_count"].get("정재", 0); pj = c.r["ten_gods_count"].get("편재", 0)
            style = "정재 중심(월급·저축·전문성)" if jj >= pj else "편재 중심(활동·거래·사업 감각)"
            return f"사주의 재물 구조는 {style}이에요. " + ("손금과 사주 모두 축적형 재물을 가리켜요." if (st != "clear" and jj >= pj) else "손금과 함께 보면 돈 버는 방식의 균형이 보여요.")
        if key == "fate":
            a0 = c.solar.year + 35; ys = [y for y in range(a0, a0 + 4)]
            return f"정격은 {c.gyeok}이고, 유년법 35~38세는 {ys[0]}~{ys[-1]}년이에요. 이 무렵 세운과 대운이 진로의 분기점을 함께 가리켜요."
        if key == "life":
            return f"사주는 {c.st_label}이에요. " + ("뿌리가 약한 만큼 휴식과 수면이 체력을 지키는 열쇠예요." if not c.strong else "기운이 강한 만큼 과로보다 꾸준한 운동이 체력을 지켜요.")
        if key == "head":
            tal = "식상" if c.gcount["식상"] else max(c.gcount, key=c.gcount.get)
            return f"{c.gyeok}({GYEOK[c.gyeok].split('. ')[0].replace('격이에요', '격')})과 {tal}({GROUP_MEAN[tal]})이 손금의 재능과 함께 읽혀요."
        if key == "heart":
            sp = c.tg(c.db, True)
            return f"배우자궁(일지)은 {sp}이에요. {SPOUSE_PALACE[sp].split('. ')[0].replace('배우자궁에 ' + sp + '이 있어 ', '').replace('배우자궁에 ' + sp + '가 있어 ', '')}."
        return ""

    # ============================================================ PAGES
    def cover(self, palm=None):
        c = self.c; inp = self.inp; P = c.P
        gtxt = "여성" if c.gender == "F" else "남성"
        bdate = inp.get("date_label", "")
        pillars = ""
        for n, lb in (("시", "시주"), ("일", "일주 · 나"), ("월", "월주"), ("년", "년주")):
            if n not in P or (n == "시" and not c.time_known):
                pillars += f'<div class="pl"><div class="lb">{lb}</div><div class="ch"><span>?</span><span>?</span></div><div class="tg">시간 미상</div></div>'
                continue
            p = P[n]; gz = p["gz"]
            tg = "일간 · " + p["branch_tengod"] if n == "일" else f'{p["stem_tengod"]} · {p["branch_tengod"]}'
            pillars += f'<div class="pl{" me" if n == "일" else ""}"><div class="lb">{lb}</div><div class="ch">{elsp(gz[0])}{elsp(gz[1])}</div><div class="tg">{tg}</div></div>'
        k = self.key5(palm)
        ks = "".join(f'<div class="k"><div class="n">{i+1}</div><div class="t"><b>{t}</b>{d.replace("<b>", "<strong>").replace("</b>", "</strong>")}</div></div>' for i, (t, d) in enumerate(k))
        title = "사주 · 손금 종합 감정서" if palm else "사주 종합 감정서"
        return f'''<section class="page cover"><div class="in">
 <div class="brand"><div class="seal">命</div><div class="name">명운</div><div class="en">MYEONGUN · SAJU{' &amp; PALM' if palm else ''}</div></div>
 <div class="ctitle">{title}</div>
 <div class="cmeta">{esc(self.who)} · {gtxt} · {esc(bdate)} · {esc(inp.get("place_label", ""))} 출생</div>
 <div class="pillars">{pillars}</div>
 <div class="serif" style="text-align:center;color:#e9c97c;font-size:12.5pt;letter-spacing:0.18em;margin-bottom:1mm">한눈에 보는 핵심 5가지</div>
 <div class="key5">{ks}</div>
</div><div class="foot">MYEONGUN · __PG__</div></section>'''

    def key5(self, palm):
        c = self.c; out = []
        st = STEM[c.dm]; season = MONTH[c.mb][0]
        out.append((f"{season}에 태어난 {st['title']}의 사주",
                    f"{st['img']}를 닮은 {st['ko']}({c.dm}) 일간이에요. {SEASON_NOTE[c.season]}. 격국은 <b>{c.gyeok}</b>, "
                    f"{c.st_label.split('(')[0]}이라 <span class=\"gold\">용신은 {el_full(c.yong)}, 희신은 {el_full(c.hee)}</span>로 봐요."))
        out.append(self.money_headline(palm))
        # 인연
        ly = self.best_love_years(3)
        age_now = c.age(self.Y)
        if ly:
            y = ly[0]; gz = E.year_gz(y)
            star_word = "남편을 뜻하는 관성" if c.gender == "F" else "아내를 뜻하는 재성"
            why = []
            se = c.gel["관성"] if c.gender == "F" else c.gel["재성"]
            if BR_ELK[gz[1]] == se or STEM_ELK[gz[0]] == se: why.append(f"{star_word}({c.tg(gz[0]) if STEM_ELK[gz[0]]==se else c.tg(gz[1],True)})이 들어오고")
            if frozenset(gz[0] + c.dm) in S.STEM_HAP: why.append(f"{gz[0]}{c.dm}합으로 일간이 묶이고")
            if any(t.startswith("육합") or t.startswith("삼합 반합") for t in S.pair_relations(gz[1], c.db)): why.append("배우자궁과 합하고")
            why_s = " ".join(why).rstrip("고") + ("는 해예요." if why else "")
            if why_s.endswith("하는 해예요.") is False and why: why_s = " ".join(why)[:-1] + "는 해예요."
            lbl = "결혼·인연운" if age_now < 50 else "관계·가정운"
            others = ", ".join(str(x) for x in ly[1:])
            out.append((f"{lbl} 1순위는 {y}년 {ko(gz)}({gz})년",
                        f"{why_s} {('그다음은 ' + others + '년이에요. ') if others else ''}{SPOUSE_PALACE[c.tg(c.db, True)].split('. ')[0]}."))
        else:
            out.append(("인연은 천천히, 깊게", SPOUSE_PALACE[c.tg(c.db, True)]))
        # 올해/내년/최고
        y1 = self.Y + 1; gz1 = E.year_gz(y1)
        top = sorted(self.years, key=lambda y: -self.ysc[y])[:2]
        top.sort()
        tops = "·".join(f"{y} {gzz}" for y, gzz in ((y, E.year_gz(y)) for y in top))
        out.append((f"{y1}년은 {self.year_title(y1).replace('해', '해')}, {'·'.join(map(str, top))}년이 10년의 정점",
                    f"{y1} {gz1}년은 {self.year_line(y1)}. {self.best_months_phrase(y1)} 10년 안에서는 <span class=\"gold\">{tops}년이 일과 재물의 최고 해</span>예요."))
        low = [y for y in self.years if self.ystar[y] == 2][:3]
        cw = self.caution_word()
        out.append((f"지킬 것: {cw}",
                    f"{'·'.join(map(str, low)) + '년은 지키는 해예요. ' if low else ''}개운 포인트는 <span class=\"gold\">{ELEM[c.yong]['colors'].split('·')[0]}·{ELEM[c.hee]['colors'].split('·')[0]} 계열, {ELEM[c.yong]['dir']}, 숫자 {ELEM[c.yong]['nums']}</span>이에요."))
        return out

    def caution_word(self):
        c = self.c
        top = max(c.gw, key=c.gw.get)
        if not c.strong:
            w = {"재성": "혼자 다 떠안기, 보증·무리한 대출", "관성": "과도한 책임·눈치, 번아웃", "식상": "에너지 소모·말실수, 과로",
                 "비겁": "체력 과신", "인성": "생각만 하고 미루기"}[max(c.drain, key=c.drain.get)]
        else:
            w = {"비겁": "고집·독단, 동업·보증", "인성": "생각 많고 실행 늦음", "식상": "말이 앞서는 것", "재성": "욕심·무리한 투자", "관성": "자기 압박"}[top]
        lack = min(c.wt, key=c.wt.get)
        return f"{w}, {HEALTH_LACK[lack].split('.')[0].split('·')[0]} 관리"

    def best_months_phrase(self, y):
        ms = [(a, b, gz) for a, b, gz, n in self.mp if a.year == y and n != "小寒" or (a.year == y + 1 and n == "小寒")]
        if not ms: return ""
        sc = sorted(ms, key=lambda m: -self.c.score(m[2])[0])
        good = sorted(sc[:2], key=lambda m: m[0]); bad = sorted(sc[-2:], key=lambda m: m[0])
        g = "과 ".join(f"{m[0].month}월({m[2]})" for m in good); b = "·".join(f"{m[0].month}월" for m in bad)
        return f"{g}에 움직이고 {b} 큰 결정은 피하세요."

    def money_headline(self, palm):
        c = self.c; n = c.gcount["재성"]
        gos = [p for p in c.P.values() if p["gz"][1] == JAEGO[c.gel["재성"]] or (p["gz"][1] in "辰戌丑未" and any(E.STEM_ELK[h] == c.gel["재성"] for h in S.HIDDEN[p["gz"][1]]))]
        if n == 0:
            t = "재성이 숨어 있어, 운이 올 때 크게 반응하는 재물"
            d = f"재성({el_full(c.gel['재성'])})이 겉에 없어 젊어서는 돈보다 실력을 먼저 쌓는 흐름이에요. 운에서 재성이 들어오는 해에 수입이 확 달라져요."
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
        note = f"겉 글자로는 {EL_WORD[top_c]}({top_c})이 가장 많고" + (f", 지장간까지 넣으면 {EL_WORD[top_w]}({top_w})이 가장 강해요." if top_w != top_c else ", 지장간까지 넣어도 가장 강해요.")
        if zero: note += f" {'·'.join(EL_WORD[e] + '(' + e + ')' for e in zero)}{'는' if True else ''} 겉에 없지만, ‘없는 오행’은 결핍이 아니라 <b>운에서 들어올 때 크게 반응하는 자리</b>예요."
        gm = GROUP_MEAN_F if c.gender == "F" else GROUP_MEAN_M
        grows = "".join(f'<tr><td><b>{g}</b> {c.gcount[g]}</td><td{" class=small" if not c.groups[g] else ""}>{" · ".join(c.groups[g]) or "(지장간 " + " ".join(c.hidden_groups[g][:3]) + ")" if c.hidden_groups[g] else " · ".join(c.groups[g]) or "-"}</td><td class="small">{gm[g].replace("·", " · ")}</td></tr>'
                        for g in sorted(c.gcount, key=lambda g: -c.gcount[g]))
        # 신강
        mbe, dbe = BR_ELK[c.mb], BR_ELK[c.db]
        sup = (c.gel["비겁"], c.gel["인성"])
        s1 = f"태어난 달 {c.mb}({EL_WORD[mbe]})은 {c.dm} 일간을 {'돕고' if c.deukryeong else '돕지 못하고'}(<b>득령 {'O' if c.deukryeong else 'X'}</b>), "
        s1 += f"앉은 자리 {c.db}({EL_WORD[dbe]}){'도 힘이 되어' if c.deukji else '도 힘이 되지 못해' if not c.deukryeong else '는 힘이 되지 못해'}(<b>득지 {'O' if c.deukji else 'X'}</b>). "
        roots = [n for n in c.P if n != "일" and BR_ELK[c.P[n]["gz"][1]] in sup] + [n for n in c.P if n not in ("일",) and STEM_ELK[c.P[n]["gz"][0]] in sup]
        if roots:
            s1 += f"{'·'.join(dict.fromkeys(POS_NAME.get(n, n) if True else n for n in roots))[:20].replace('지', '주')} 쪽에서 {EL_WORD[c.gel['비겁']]}·{EL_WORD[c.gel['인성']]}의 도움이 있어요. "
        conc = {True: "기운이 넘치는 만큼 <b>쓰고 나누고 표현할 때</b> 운이 열리는 사주예요.",
                False: "혼자 모든 것을 짊어지면 지치지만, <b>배움과 내 편이 받쳐 주면</b> 크게 자라는 사주예요."}[c.strong]
        s1 += f"결론은 <span class=\"em\">{c.st_label}</span>(도움 비율 {int(c.ratio * 100)}%)이에요. {conc}"
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
</div><div class="foot">MYEONGUN · __PG__</div></section>'''

    def verify_text(self):
        c = self.c; r = c.r; inp = self.inp; out = []
        if inp.get("lunar"):
            out.append(f"음력 {inp['date']}{'(윤달)' if inp.get('leap') else ''}은 양력 <b>{r['solar_date']}</b>이에요(한국천문연구원 음력 기준).")
        jq = r.get("jieqi", {})
        if jq.get("prev"):
            out.append(f"절입 {jq['prev'][0]}({jq['prev'][1].replace(' KST', '')}) 뒤, {jq['next'][0]}({jq['next'][1].replace(' KST', '')}) 전이라 월주는 <b>{c.P['월']['gz']}</b>, 년주는 <b>{c.P['년']['gz']}</b>예요.")
        if c.time_known:
            tc = r["time_correction"]; lt = tc["local_solar_time"][-5:]
            hh, mm = map(int, lt.split(":")); m = hh * 60 + mm
            bnd = min(abs(m - (h * 60)) for h in range(1, 25, 2)) if True else 0
            bnd = min(bnd, abs(m + 1440 - 23 * 60) if m < 60 else 999)
            hb = c.P["시"]["gz"][1]
            s = f"출생 시각 {inp.get('time')}은 {inp.get('place_label', '')} 경도 보정 시 <b>{lt}</b>({tc['correction_minutes']:+.1f}분)로 {hb}시예요."
            if bnd <= 12: s += f" <b>시(時)의 경계에서 {bnd}분 거리</b>라 출생 시각이 조금만 달라도 시주가 바뀔 수 있어요."
            out.append(s)
        else:
            out.append("출생 시각을 몰라 시주 없이 6글자로 봤어요. 자녀·말년·성향 일부는 참고 정도로 읽어 주세요.")
        di = r["daeun_info"]
        out.append(f"대운은 {di['direction']}, 대운수 {di['대운수']}(정밀 {di.get('exact', '')}, 첫 대운 약 {di.get('exact_start_date', '')[:7].replace('-', '년 ')}월)이고, 나이는 모두 만 나이예요.")
        for w in r.get("warnings", []):
            if "절기" in w or "경계" in w: out.append(esc(w))
        return " ".join(out)

    # ------------------------------------------------------------ P3 용신
    def p_yongsin(self):
        c = self.c; G = c.gel
        steps = []
        season = MONTH[c.mb][0]
        if "조후" in c.method:
            steps.append(f"<b>조후(온도)</b>: {season}생이라 {SEASON_NOTE[c.season]}. 원국에 {EL_WORD[c.yong]}({c.yong})이 가중 {c.wt[c.yong]}로 부족해 <b>{c.yong}을 먼저 씁니다</b>.")
        elif c.season in ("winter", "summer"):
            need = "화" if c.season == "winter" else "수"
            steps.append(f"<b>조후(온도)</b>: {season}생이라 {SEASON_NOTE[c.season]}. 원국에 {EL_WORD[need]}({need})이 가중 {c.wt[need]}로 이미 있어 <b>온도 문제는 크지 않아요</b>.")
        else:
            steps.append(f"<b>조후(온도)</b>: {season}생이라 {SEASON_NOTE[c.season]}. 온도가 크게 치우치지 않아 강약(억부)을 중심으로 봐요.")
        if c.strong:
            big = "비겁" if c.wt[G["비겁"]] >= c.wt[G["인성"]] else "인성"
            steps.append(f"<b>억부(강약)</b>: 일간을 돕는 {big}({EL_WORD[G[big]]})이 강한 {c.st_label}이에요. 넘치는 힘을 <b>{'흘려 쓰는' if big == '비겁' else '현실로 바꾸는'} {c.el_group[c.yong]}({c.yong})</b>이 필요해요.")
        else:
            top = max(c.drain, key=c.drain.get)
            steps.append(f"<b>억부(강약)</b>: 일간의 힘을 빼는 쪽 중 {top}({EL_WORD[G[top]]})이 가장 무거운 {c.st_label}이에요. "
                         f"그래서 <b>{'나를 세워 주는 비겁' if c.el_group[c.yong] == '비겁' else '나를 먹여 주는 인성' if c.el_group[c.yong] == '인성' else c.el_group[c.yong]}({c.yong})</b>이 반가워요.")
        steps.append(f"<b>희신·기신</b>: 용신을 돕는 {el_full(c.hee)}이 희신, 지나치면 부담이 되는 {el_full(c.gi)}{'과 ' + el_full(c.gu) if c.gu else ''}이 조심할 기운이에요.")
        gm = GROUP_MEAN_F if c.gender == "F" else GROUP_MEAN_M
        concl = (f"용신 <b>{el_full(c.yong)}</b> = {gm[c.el_group[c.yong]]} / 희신 <b>{el_full(c.hee)}</b> = {gm[c.el_group[c.hee]]} / "
                 f"기신 <b>{el_full(c.gi)}</b> 과다 = {gm[c.el_group[c.gi]].split('·')[0]}의 부담")
        # 격국
        gy = c.gyeok
        src = c.gyeok_src
        if gy in ("건록격", "양인격"):
            gtxt = f"월지 {c.mb}가 일간 {c.dm}의 {'양인' if gy == '양인격' else '건록'} 자리라 <b>{gy}</b>이에요. {GYEOK[gy]}"
        else:
            tp = getattr(c, "gyeok_transparent", False)
            gtxt = f"월지 {c.mb}의 지장간 {'·'.join(S.HIDDEN[c.mb])} 가운데 {src}{'가 천간에 그대로 떠 있어' if tp else '(정기)를 기준으로'} <b>{gy}</b>이에요. {GYEOK[gy]}"
        # 신살
        rows = ""
        for nm in ["천을귀인", "문창귀인", "건록", "화개", "도화", "홍염살", "역마", "양인", "괴강살", "백호살"]:
            if nm in c.sinsal:
                lst = c.sinsal[nm]
                rows += f'<tr><td><b>{nm}</b>{" ×" + str(len(lst)) if len(lst) > 1 else ""}</td><td>{" · ".join(POS_NAME[p] + " " + gz[1] for p, gz in lst)}</td><td class="small">{SINSAL.get(nm.replace("문창귀인", "문창귀인"), "")}</td></tr>'
        if not rows: rows = '<tr><td colspan="3" class="small">원국에 두드러진 신살이 없어요. 신살은 양념일 뿐, 오행과 십신의 흐름이 본바탕이에요.</td></tr>'
        # 합충
        rel_items = self.chart_rel_items()
        rel_items.sort(key=lambda x: 0 if "완성" in x else 1 if ("충" in x or "형" in x) else 2)
        gmg = c.gongmang
        gm_el = BR_ELK[gmg[0]]
        rel_items.append(f"<b>공망 {gmg[0]}·{gmg[1]}</b>: {c.el_group[gm_el]}({gm[c.el_group[gm_el]].split('·')[0]})의 자리가 비어 있어, 그 일에는 확신이 늦은 편이에요. 운에서 {gmg[0]}·{gmg[1]}이 오는 해에 그 자리가 채워져요.")
        lis = "".join(f"<li>{x}</li>" for x in rel_items[:4] + rel_items[-1:])
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
</div><div class="foot">MYEONGUN · __PG__</div></section>'''

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
                txt = REL_CHART["천간충"]
            elif "천간합" in kind:
                txt = REL_CHART["천간합"]
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
        c = self.c; st = STEM[c.dm]
        top = max(c.gcount, key=lambda g: (c.gcount[g], c.gw[g]))
        absent = [g for g in c.gcount if c.gcount[g] == 0]
        tg_top = "·".join(dict.fromkeys(c.groups[top]))
        p = [f'<p><span class="tag">일간 {c.dm}{EL_HAN[c.dm_el]}</span>{st["img"]}예요. {st["pers"]}</p>',
             f'<p><span class="tag">월지 {c.mb} · {c.gyeok}</span>{MONTH[c.mb][0]}에 태어나 {SEASON_NOTE[c.season].replace("사주예요", "사주라")} {GYEOK[c.gyeok].split(". ")[0]}.</p>',
             f'<p><span class="tag">강한 십신 · {top} {c.gcount[top]}</span>{GROUP_STRONG[top]}</p>']
        if absent:
            p.append(f'<p><span class="tag">{absent[0]} 0</span>{GROUP_ABSENT[absent[0]]}</p>')
        stage = c.P["일"]["12운성"]
        weak = st["weak"]
        if not c.strong:
            dr = max(c.drain, key=c.drain.get)
            adv = {"재성": "책임(재성)이 많아 부탁을 거절하지 못하고 혼자 다 떠안는 경향이 있어요",
                   "관성": "책임과 압박(관성)이 커서 남의 시선과 기대에 스스로를 몰아붙이기 쉬워요",
                   "식상": "표현과 재능(식상)으로 에너지를 많이 써서 쉽게 지치기 쉬워요"}[dr]
            tip = "“이건 제가 못 해요”라고 말하는 연습, 혼자 쉬는 시간을 일정에 넣는 것"
        else:
            adv = {"비겁": "주관이 강해 남의 조언을 흘려듣거나 혼자 결정하는 경향이 있어요",
                   "인성": "생각과 준비가 길어 실행이 늦어지는 경향이 있어요"}.get(max(("비겁", "인성"), key=lambda g: c.gw[g]), "")
            tip = "결정 전에 한 사람에게 의견을 묻는 습관, 생각을 바로 작게 실행해 보는 것"
        box = f'<b class="gold">보완하면 좋은 점</b> · {adv}. 일간의 약점은 {weak}이에요. <b>{tip}</b>만으로 운의 흐름이 가벼워지는 사주예요.'
        # 재물
        m = self.money_paras()
        return f'''<section class="page tight"><div class="in">
 <h2><span class="no">{self.nxt()}</span>성격</h2>
 <div class="sub">일간 → 월지 → 강한 십신 순서로 읽었어요</div>
 {"".join(p)}
 <div class="box small">{box}</div>
 <div class="rule"></div>
 <h2><span class="no">{self.nxt()}</span>재물운</h2>
 <div class="sub">재성의 자리 · 재물 창고 · 식신생재 · 강약과 재물 · 돈 버는 방식</div>
 {m}
</div><div class="foot">MYEONGUN · __PG__</div></section>'''

    def money_paras(self):
        c = self.c; G = c.gel; n = c.gcount["재성"]; out = []
        jpos = [nm for nm, p in c.P.items() if (nm != "일" and TG_GROUP[p["stem_tengod"]] == "재성") or TG_GROUP[p["branch_tengod"]] == "재성"]
        gos = [p["gz"][1] for p in c.P.values() if p["gz"][1] in "辰戌丑未" and any(STEM_ELK[h] == G["재성"] for h in S.HIDDEN[p["gz"][1]])]
        if n:
            s = f"<b>① 재성의 자리</b> · 재성(돈, {el_full(G['재성'])})이 {'·'.join(POS_NAME.get(x, x).replace('지', '주') for x in dict.fromkeys(jpos))}에 {n}개 있어요. "
        else:
            s = f"<b>① 재성의 자리</b> · 재성(돈, {el_full(G['재성'])})이 겉에 없어요. 지장간에 {len(c.hidden_groups['재성'])}개 숨어 있어 <b>운에서 재성이 들어올 때 크게 반응</b>해요. "
        if gos: s += f"{'·'.join(gos)}은 재성을 품은 ‘창고(庫)’ 글자라 <span class=\"em\">버는 것보다 모으고 지키는 재주</span>가 있어요."
        out.append(f"<p>{s}</p>")
        if c.gcount["식상"] and (n or c.hidden_groups["재성"]):
            out.append(f"<p><b>② 재능이 돈이 되는 길(식신생재)</b> · 식상({'·'.join(c.groups['식상'])})이 재성을 낳아요. 감각·말솜씨·전문 기술이 그대로 수입으로 이어지는 구조예요.</p>")
        else:
            out.append(f"<p><b>② 돈이 들어오는 통로</b> · 식상(재능)이 {'적어' if not c.gcount['식상'] else '있지만'} 돈은 {'자격·직급·조직(관성·인성)을 통해' if c.gcount['관성'] + c.gcount['인성'] >= 2 else '내 힘과 인맥(비겁)을 통해'} 들어오는 편이에요. 실력을 먼저 키우면 돈이 따라와요.</p>")
        if not c.strong and n >= 2:
            out.append("<p><b>③ 재다신약: 그릇을 키우면 돈도 커져요</b> · 돈의 기운이 일간보다 커서, 무리하게 큰돈을 다루면 몸과 마음이 먼저 지쳐요. 보증·대출로 크게 벌이는 방식은 맞지 않아요. 대신 <b>자격·전문성과 체력·내 편</b>을 키울 때마다 담을 수 있는 재물이 한 단계씩 커져요.</p>")
        elif c.strong and c.gcount["비겁"] >= 3:
            out.append("<p><b>③ 군겁쟁재: 지키는 힘이 재산</b> · 내 기운이 강하고 경쟁자(비겁)도 많아 번 돈이 사람·지출로 새기 쉬워요. 동업·보증은 서면으로, 통장은 용도별로 나누세요.</p>")
        elif c.strong:
            out.append("<p><b>③ 신강한 사주의 재물</b> · 감당할 힘이 있어 돈을 크게 다뤄도 버티는 구조예요. 재성이 들어오는 해에 과감하게 움직여도 되는 사주예요.</p>")
        else:
            out.append("<p><b>③ 신약한 사주의 재물</b> · 돈을 쫓기보다 실력과 건강을 먼저 챙길 때 돈이 따라오는 구조예요. 큰돈은 나눠서, 천천히.</p>")
        jj = c.r["ten_gods_count"].get("정재", 0); pj = c.r["ten_gods_count"].get("편재", 0)
        bd = self.best_daeun_money()
        way = "<b>안정된 월급 + 꾸준한 저축</b>(정재)" if jj >= pj and (jj or pj) else "<b>활동·거래·사업 감각</b>(편재)" if pj else "<b>실력과 자격으로 받는 보수</b>"
        out.append(f"<p><b>④ 돈 버는 방식</b> · 기본은 {way}이에요. " + (f"재물이 가장 크게 움직이는 시기는 <b>{bd['gz']} 대운(만 {bd['a0']}~{bd['a1']}세, {bd['y0']}~{bd['y1']})</b>이에요." if bd else "") + "</p>")
        kw = []
        if gos: kw.append(f"<b>창고형 재물</b> ({'·'.join(gos)})")
        if c.gcount["식상"]: kw.append(f"<b>재능형 수입</b> (식상 {'·'.join(c.groups['식상'])})")
        if not c.strong and n >= 2: kw.append("<b>그릇을 키우는 돈</b> (재다신약)")
        if "천을귀인" in c.sinsal: kw.append("<b>귀인이 주는 기회</b> (천을귀인)")
        if not kw: kw.append(f"<b>{el_full(c.yong)}의 해에 커지는 돈</b>")
        out.append(f'<div class="box dark" style="margin-top:2.5mm;font-size:10pt"><span class="gold">{esc(self.who)}의 재물 키워드</span><br>{" · ".join(kw)}</div>')
        return "\n".join(out)

    # ------------------------------------------------------------ P5 직업·연애·건강
    def p_job_love_health(self):
        c = self.c; G = c.gel
        picks = []
        gname, greason = CAREER_GYEOK[c.gyeok]; picks.append((gname, greason))
        top = max(c.gcount, key=lambda g: (c.gcount[g], c.gw[g]))
        if CAREER_GROUP[top][0] != gname: picks.append(CAREER_GROUP[top])
        used = set(x.strip() for a, _ in picks for x in a.replace("/", " · ").split("·"))
        yc = [x for x in ELEM[c.yong]["careers"].split("·") if x.strip() not in used]
        picks.append((" · ".join(yc[:5]) or ELEM[c.yong]["careers"], f"용신 {el_full(c.yong)}의 업종이라 일할수록 운이 살아나요."))
        rows = "".join(f'<tr><td><b>{"①②③"[i]} {a}</b></td><td class="small">{b}</td></tr>' for i, (a, b) in enumerate(picks[:3]))
        # 이직 흐름
        move = []
        for y in self.years[:5]:
            gz = E.year_gz(y); rels = c.relations_to_chart(*gz)
            if any(k == "충" and p == "월" for k, p, _, _ in rels): move.append((y, "월지를 충해 직장 환경이 바뀌기 쉬운 해"))
            elif c.tg(gz[1], True) in ("정관", "편관") and self.ystar[y] >= 4: move.append((y, "관성이 들어와 자리·직함이 안정되는 해"))
        mv = " ".join(f"<b>{y}년</b>은 {t}예요." for y, t in move[:3]) or "향후 5년 안에 직장 자리를 크게 흔드는 충은 없어요. 옮긴다면 별점이 높은 해를 고르세요."
        y1 = self.Y + 1
        mv += " " + self.best_months_phrase(y1).replace("움직이고", "움직이는 게 좋고").replace("에 움직이는", "에 움직이는")
        # 연애
        sp = c.tg(c.db, True)
        hidden_sp = [h for h in c.P["일"]["hidden"] if TG_GROUP[h["tengod"]] == ("관성" if c.gender == "F" else "재성")]
        star = "관성(남편)" if c.gender == "F" else "재성(아내)"
        sp_cnt = c.gcount["관성" if c.gender == "F" else "재성"]
        para = SPOUSE_PALACE[sp]
        if hidden_sp: para += f" 배우자궁 속에 {hidden_sp[0]['tengod']} {hidden_sp[0]['stem']}이 숨어 있어 결국 {'바르고 책임감 있는' if '정' in hidden_sp[0]['tengod'] else '능력 있고 추진력 있는'} 사람과 맺어지는 모양이에요."
        para += f" {star}이 " + ("겉에 없어 상대를 오래 지켜본 뒤 마음을 여는 타입이에요." if sp_cnt == 0 else f"{sp_cnt}개라 인연의 기회가 {'많은' if sp_cnt >= 2 else '분명한'} 편이에요.")
        lis = []
        for y in self.best_love_years(3):
            gz = E.year_gz(y); bits = []
            se = G["관성"] if c.gender == "F" else G["재성"]
            if STEM_ELK[gz[0]] == se or BR_ELK[gz[1]] == se: bits.append(f"{star.split('(')[0]}이 들어오는 해")
            if frozenset(gz[0] + c.dm) in S.STEM_HAP: bits.append(f"{gz[0]}{c.dm}합")
            if any(t.startswith("육합") or t.startswith("삼합 반합") for t in S.pair_relations(gz[1], c.db)): bits.append("배우자궁과 합")
            if "충" in S.pair_relations(gz[1], c.db): bits.append("배우자궁 충(변화·결단)")
            lis.append(f"<li><b>{y} {gz}</b> (만 {c.age(y)}세): {', '.join(bits) or '인연의 기운이 강한 해'}.</li>")
        se2 = G["관성"] if c.gender == "F" else G["재성"]
        win = [y for y in self.years if STEM_ELK[E.year_gz(y)[0]] == se2 or BR_ELK[E.year_gz(y)[1]] == se2]
        if win:
            lis.append(f"<li><b>인연의 창</b>: {star.split('(')[0]}이 들어오는 해는 {'·'.join(map(str, win))}년이에요. 이 시기에 만남과 결정이 몰려요.</li>")
        kid_g = "식상" if c.gender == "F" else "관성"
        if c.time_known:
            hp = c.P["시"]; kid = [x for x in (TG_GROUP[hp["stem_tengod"]], TG_GROUP[hp["branch_tengod"]]) if x == kid_g]
            lis.append(f"<li><b>자녀</b>: {'여성' if c.gender == 'F' else '남성'}의 자녀는 {kid_g}이에요. 시주(자녀궁)는 {hp['gz']}({hp['stem_tengod']}·{hp['branch_tengod']}){'로 자녀의 별이 자녀궁에 있어 자녀 인연이 좋아요' if kid else '이고, 자녀의 별이 들어오는 대운·세운에 자녀운이 강해져요'}.</li>")
        # 건강
        hi = max(c.wt, key=c.wt.get); lo = min(c.wt, key=c.wt.get)
        hl = [f"<li><b>{EL_WORD[hi]}({hi}) 강함</b>: {HEALTH_EXCESS[hi]}</li>"]
        hc = max(c.cnt, key=c.cnt.get)
        if hc != hi and c.cnt[hc] >= 3: hl.append(f"<li><b>{EL_WORD[hc]}({hc}) 글자 많음</b>: {HEALTH_EXCESS[hc]}</li>")
        hl.append(f"<li><b>{EL_WORD[lo]}({lo}) 약함</b>: {HEALTH_LACK[lo]}</li>")
        if c.season in ("winter", "summer"):
            hl.append(f"<li><b>{MONTH[c.mb][0]}생</b>: {'몸을 따뜻하게, 겨울철 보온과 혈액순환' if c.season == 'winter' else '열을 식히고 수분 보충, 여름철 과로 주의'}.</li>")
        cy = [y for y in self.years[:4] if any(k == "충" for k, p, _, _ in c.relations_to_chart(*E.year_gz(y)) if p in ("일", "월"))]
        hn = (f"{'·'.join(map(str, cy))}년은 충이 드는 해라 무리하지 말고 정기 검진을 챙기세요." if cy else "가까운 몇 년은 큰 충이 없어 생활 리듬만 지키면 돼요.")
        return f'''<section class="page tight"><div class="in">
 <h2><span class="no">{self.nxt()}</span>직업·적성·이직</h2>
 <div class="sub">격국({c.gyeok}) + 용신({c.yong}) + 강한 십신({top})</div>
 <table><tr><th style="width:33%">추천 계열</th><th>이유</th></tr>{rows}</table>
 <p class="small" style="margin-top:2mm"><b>이직 흐름</b> · {mv}</p>
 <div class="rule"></div>
 <h2><span class="no">{self.nxt()}</span>{'연애·결혼·가정' if c.age(self.Y) < 50 else '부부·가정·관계'}</h2>
 <div class="sub">배우자궁(일지) · {'여성의 관성' if c.gender == 'F' else '남성의 재성'} · 인연 시기</div>
 <p>{para}</p>
 <ul class="small">{"".join(lis)}</ul>
 <p class="small">{'이미 만나는 분이 있다면 위 해에 관계가 깊어지고, 결혼하셨다면 가정이 안정되고 배우자 일이 좋아지는 때예요.' if c.age(self.Y) < 50 else '위 해는 부부 사이가 따뜻해지고 배우자 일이 풀리며, 새로운 인연·모임이 생기기 쉬운 때예요.'}</p>
 <div class="rule"></div>
 <h2><span class="no">{self.nxt()}</span>건강 경향</h2>
 <div class="sub">전통 오행 배속에 따른 ‘관리 포인트’이며 의학적 진단이 아니에요</div>
 <ul class="small">{"".join(hl)}</ul>
 <p class="small">__PALM_HEALTH__{hn}</p>
</div><div class="foot">MYEONGUN · __PG__</div></section>'''

    # ------------------------------------------------------------ P6 대운
    def p_daeun(self):
        c = self.c; ps = c.daeun_periods()
        cur = c.current_daeun(self.Y)
        rows = ""; cur_i = None
        for i, p in enumerate(ps[:8]):
            sc = c.score(p["gz"])[0]; stn = max(2, min(5, self.star(sc)))
            g1, g2 = TG_GROUP[p["천간십신"]], TG_GROUP[p["지지십신"]]
            fs, fb = c.fav[STEM_ELK[p["gz"][0]]], c.fav[BR_ELK[p["gz"][1]]]
            flow = DAEUN_THEME[g2].split(". ")[0]
            if fs >= 1 and fb >= 1: flow = f"용신·희신이 함께 오는 대운. " + flow
            elif fb >= 1: flow = f"지지에 {FAV_WORD[fb]} {p['gz'][1]}. " + flow
            elif fb <= -2: flow += ". 무리한 확장은 조심"
            rr = [r for r in c.relations_to_chart(*p["gz"]) if r[0] in ("충", "육합", "반합") and r[1] in ("일", "월")]
            if rr: flow += f". {rr[0][2]}{'충' if rr[0][0] == '충' else '합'}({POS_NAME[rr[0][1]]})"
            is_cur = cur and p["gz"] == cur["gz"]; is_next = cur and i > 0 and ps[i - 1]["gz"] == cur["gz"]
            if is_cur: cur_i = i
            tag = "<b>현재.</b> " if is_cur else "<b>다음.</b> " if is_next else ""
            hl = ' class="hl"' if is_cur or is_next else ""
            rows += f'<tr{hl}><td>{p["a0"]}~{p["a1"]}</td><td>{p["y0"]}~{p["y1"]}</td><td class="serif">{p["gz"]}</td><td class="small">{p["천간십신"]} / {p["지지십신"]}</td><td class="small">{tag}{flow}.</td><td class="stars">{stars(stn)}</td></tr>'
        paras = ""
        for lab, idx in (("현재 대운", cur_i), ("다음 대운", (cur_i + 1) if cur_i is not None else 0)):
            if idx is None or idx >= len(ps): continue
            p = ps[idx]; g1, g2 = TG_GROUP[p["천간십신"]], TG_GROUP[p["지지십신"]]
            t = f"천간 {p['gz'][0]}는 {p['천간십신']}, 지지 {p['gz'][1]}는 {p['지지십신']}이에요. {DAEUN_THEME[g1]}"
            if g2 != g1: t += f" 지지로는 {DAEUN_THEME[g2].split('. ')[0].replace('10년이에요', '흐름이 함께해요')}."
            fb = c.fav[BR_ELK[p["gz"][1]]]
            t += {2: f" 지지 {p['gz'][1]}가 용신이라 <b>뿌리부터 힘이 붙는 시기</b>예요.", 1: f" 지지 {p['gz'][1]}가 희신이라 무리 없이 성장해요.",
                  0: "", -1: f" {p['gz'][1]}의 기운은 조금 부담이라 속도 조절이 필요해요.", -2: f" {p['gz'][1]}의 기운이 무거워 <b>지키면서 실력을 쌓는</b> 운영이 맞아요."}[fb]
            for k, pos, det, el in c.relations_to_chart(*p["gz"]):
                if k == "충" and pos in ("일", "월"):
                    t += f" 대운 {det[0]}가 {POS_NAME[pos]} {det[1]}를 충해, 이 10년 안에 {POS[pos]}의 큰 변화가 한두 번 있기 쉬워요. 머무르기보다 움직일 때 길이 열려요."
                    break
            paras += f"<h3>{lab} · {p['gz']} (만 {p['a0']}~{p['a1']}세, {p['y0']}~{p['y1']})</h3><p>{t}</p>"
        di = c.r["daeun_info"]
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>대운(大運) 흐름</h2>
 <div class="sub">10년마다 바뀌는 인생의 계절 · {di['direction']} · 대운수 {di['대운수']} · 나이는 만 나이 · 대운은 그해 {ps[0]['month']}월 무렵 바뀌어요</div>
 <table><tr><th style="width:11%">나이</th><th style="width:15%">연도</th><th style="width:10%">대운</th><th style="width:16%">십신</th><th>흐름</th><th style="width:12%">운세</th></tr>{rows}</table>
 {paras}
</div><div class="foot">MYEONGUN · __PG__</div></section>'''

    # ------------------------------------------------------------ P7 올해
    def month_rows(self, ms, hl_cut=4, year_label=False):
        rows = ""
        for a, b, gz, n in ms:
            sc = self.c.score(gz)[0]; stn = self.star(sc)
            end = b - E.timedelta(days=1)
            per = f"{a.month}/{a.day}~{end.month}/{end.day}"
            if year_label and a.year != self.Y: per = f"{a.year} " + per
            pt = self.month_point(gz)
            if stn == 5: pt = "<b>최고의 달.</b> " + pt
            if stn == 2: pt += " 큰 결정·지출은 피하세요."
            rows += f'<tr{" class=hl" if stn >= hl_cut else ""}><td>{per}</td><td class="serif">{gz}</td><td class="small">{self.c.tg(gz[0])}/{self.c.tg(gz[1], True)}</td><td class="small">{pt}</td><td class="stars">{stars(stn)}</td></tr>'
        return rows

    def year_page(self, y, months, cur=False):
        c = self.c; gz = E.year_gz(y)
        st, bt = c.tg(gz[0]), c.tg(gz[1], True)
        ev = self.year_events(gz)
        dae = c.current_daeun(y)
        lc = E.lichun(y)
        summ = f"{TG_THEME[st][1].split('.')[0]}. {TG_THEME[bt][1]}" if st != bt else TG_THEME[st][1]
        lis = "".join(f"<li><b>{t}</b>: {d}</li>" for t, d in ev[:4]) or "<li>원국과 크게 부딪히거나 묶이는 글자가 없어 흐름이 순한 해예요.</li>"
        rows = self.month_rows(months, year_label=cur)
        if cur:
            mtitle = f"남은 {y}년 월별 운"; extra = self.tips_box(y, months) + self.preview_box(y)
        else:
            mtitle = f"{y}년 월별 운"
            extra = '<p class="tiny" style="margin-top:1.6mm">※ 월의 경계는 절기 절입일 기준이에요(입춘·경칩·청명…). 다음 해 1월(소한~입춘 전)은 아직 이 해의 기운이에요.</p>'
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>{y} {ko(gz)}({gz})년: {self.year_title(y)}</h2>
 <div class="sub">만 {c.age(y)}세 · 세운 {st}/{bt} · 대운 {dae['gz'] if dae else '-'} · 입춘 {lc.strftime('%Y-%m-%d %H:%M')} (한국시간) · 운세 {stars(self.ystar[y])}</div>
 <div class="box dark"><span class="gold">한 줄 요약</span> · {summ}</div>
 <ul class="small">{lis}</ul>
 <h3>{mtitle}</h3>
 <table><tr><th style="width:{'22' if cur else '14'}%">{'기간' if cur else '양력'}</th><th style="width:10%">월건</th><th style="width:14%">십신</th><th>포인트</th><th style="width:11%">운세</th></tr>{rows}</table>
 {extra}
</div><div class="foot">MYEONGUN · __PG__</div></section>'''

    def preview_box(self, y):
        rows = ""
        for yy in (y, y + 1, y + 2):
            gz = E.year_gz(yy)
            rows += f'<tr{" class=hl" if self.ystar[yy] >= 4 else ""}><td><b>{yy}</b></td><td class="serif">{gz}</td><td class="small">{tgj(self.c, gz)}</td><td class="small">{self.year_line(yy)}.</td><td class="stars">{stars(self.ystar[yy])}</td></tr>'
        return f'<h3>앞으로 3년 미리 보기</h3><table><tr><th style="width:10%">연도</th><th style="width:9%">간지</th><th style="width:14%">십신</th><th>흐름</th><th style="width:11%">운세</th></tr>{rows}</table>'

    def tips_box(self, y, months):
        if not months: return ""
        sc = sorted(months, key=lambda m: -self.c.score(m[2])[0])
        g = sc[0]; b = sc[-1]
        tips = [f"{g[0].month}월({g[2]})에 들어온 제안·만남·계획은 적극적으로", f"{b[0].month}월({b[2]})에는 큰 지출·충동적 결정을 미루기",
                f"{ELEM[self.c.yong]['colors'].split('·')[0]} 계열 소품 하나로 용신 {self.c.yong}의 기운 더하기"]
        return f'<div class="box small"><b class="gold">{y}년 남은 기간 실천 팁</b> · ' + " ".join(f"{'①②③'[i]} {t}" for i, t in enumerate(tips)) + f". {y + 1}년을 준비하는 가장 좋은 출발점이에요.</div>"

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
            if y in top2: tag = f"<b>10년 중 최고 ({sorted(top2).index(y) + 1}).</b> "
            if y == love1: tag += "<b>인연운 1순위.</b> "
            rows += f'<tr{" class=hl" if s >= 4 else ""}><td>{"<b>%d</b>" % y if tag else y}</td><td>{c.age(y)}</td><td class="serif">{gz}</td><td class="small">{tgj(c, gz)}</td><td class="small">{tag}{line}.</td><td class="stars">{stars(s)}</td></tr>'
        good = self.money_years(); bad = [y for y in self.years if self.ystar[y] == 2]
        jj = c.r["ten_gods_count"].get("정재", 0); pj = c.r["ten_gods_count"].get("편재", 0)
        fit = "적금·청약·연금처럼 쌓이는 자산, 내 실력에 투자(자격·교육), 실거주 부동산" if (not c.strong or jj >= pj) else "사업·거래·투자처럼 움직이는 자산, 단 분산과 원칙 매매"
        avoid = "보증, 지인 권유 투자, 대출 끼고 하는 단타·코인" + (". 재다신약이라 감당 못 할 돈은 새요" if (not c.strong and c.gcount['재성'] >= 2) else ". 동업은 반드시 서면으로" if c.strong else "")
        money = (f"<li><b>맞는 방식</b>: {fit}.</li><li><b>피할 방식</b>: {avoid}.</li>"
                 f"<li><b>좋은 시기</b>: {', '.join(map(str, good)) or ', '.join(map(str, sorted(top2)))}년.</li>"
                 f"<li><b>보수적으로</b>: {', '.join(map(str, bad)) or '특별히 나쁜 해는 없어요'}{'년' if bad else ''}.</li>")
        phase = ""
        nm = {"up": "도약기", "mid": "준비·안정기", "down": "지키는 시기"}
        for cat, ys in self.runs():
            span = f"{ys[0]}~{ys[-1]}" if len(ys) > 1 else f"{ys[0]}"
            lows = [y for y in ys if self.ystar[y] == 2]
            phase += f"<li><b>{nm[cat]} · {span}</b>: {'운이 받쳐 줄 때 크게 펼치기' if cat == 'up' else '실력과 기반을 다지기'}{' (지키는 해: ' + '·'.join(map(str, lows)) + ')' if lows else ''}.</li>"
        bd = self.best_daeun_money()
        if bd: phase += f"<li><b>재물 정점 · 만 {bd['a0']}~{bd['a1']}세</b> ({bd['gz']} 대운).</li>"
        phase += "<li>__PALM_TIMING__</li>"
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>향후 10년: 재물 · 일 · 인연의 시기표</h2>
 <div class="sub">{self.Y}~{self.Y + 9} 세운 × 대운 × 용신({c.yong}·{c.hee}) · 나이는 그해 생일 이후 만 나이</div>
 <table><tr><th style="width:8%">연도</th><th style="width:7%">나이</th><th style="width:8%">간지</th><th style="width:13%">십신</th><th>흐름</th><th style="width:12%">종합</th></tr>{rows}</table>
 <div class="two" style="margin-top:3.4mm">
  <div class="box" style="margin:0"><h3 style="margin-top:0">재물·투자운</h3><ul class="small" style="margin:0">{money}</ul></div>
  <div class="box" style="margin:0"><h3 style="margin-top:0">인생 흐름</h3><ul class="small" style="margin:0">{phase}</ul></div>
 </div>
</div><div class="foot">MYEONGUN · __PG__</div></section>'''

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
        adv.append(f"<li><b>{y1}년</b>: {self.best_months_phrase(y1)}</li>")
        for cat, ys in self.runs():
            if ys[0] <= y1: ys = [y for y in ys if y > y1]
            if not ys: continue
            span = f"{ys[0]}~{ys[-1]}년" if len(ys) > 1 else f"{ys[0]}년"
            lows = [y for y in ys if self.ystar[y] == 2]
            adv.append(f"<li><b>{span}</b>: " + {"up": "운이 받쳐 주는 시기예요. 승진·내 집·독립·결혼 같은 큰 계획을 이때 펼치세요.",
                                                  "mid": "기반을 다지는 시기예요. 자격·저축·관계를 차곡차곡 쌓으세요."}[cat]
                       + (f" 특히 {'·'.join(map(str, lows))}년은 큰 투자·보증·충동적 이직을 피하고 건강을 챙기세요." if lows else "") + "</li>")
        yg = c.el_group[c.yong]
        mind = {"비겁": "혼자 다 짊어지지 말고, 내 편을 곁에 두고, 체력을 지키세요.",
                "인성": "배움을 멈추지 말고, 쉬어 갈 줄 알고, 도와주는 사람을 곁에 두세요.",
                "식상": "가진 재능을 꺼내 표현하고, 생각을 바로 작게 실행해 보세요.",
                "재성": "생각을 현실의 숫자로 바꾸고, 결과를 차곡차곡 쌓으세요.",
                "관성": "책임 있는 자리를 피하지 말고, 원칙을 지키며 올라가세요."}[yg]
        lim = []
        if not c.time_known: lim.append("출생 시각을 몰라 시주 없이 판단했어요.")
        lim.append("결혼 여부와 현재 상황을 알 수 없어 여러 경우를 함께 적었어요.")
        lim.append("대운 교체 시점과 월운 별점은 계산상 근사치이며, 같은 사주라도 환경과 선택에 따라 다르게 펼쳐져요.")
        basis = "전통 명리학(자평명리)" + ("과 전통 수상학" if palm else "")
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>개운법 · 조언</h2>
 <div class="sub">용신 {el_full(c.yong)} · 희신 {el_full(c.hee)}를 생활 속에서 쓰는 방법</div>
 <table><tr><th style="width:18%">항목</th><th>{el_full(c.yong)} · 용신</th><th>{el_full(c.hee)} · 희신</th></tr>{rows}</table>
 <p class="tiny" style="margin-top:1.4mm">줄이면 좋은 것: {ELEM[c.gi]['colors'].split('·')[0]} 일색의 옷차림, {ELEM[c.yong]['reduce'].split(', ')[-1]}. 완전히 피하기보다 용신의 색을 한 가지 더하는 정도면 충분해요.</p>
 <h3>시기별 행동 조언</h3><ul class="small">{"".join(adv[:5])}</ul>
 <h3>마음가짐 한 가지</h3>
 <div class="box dark">{KEY_CLOSING[c.season]}, {esc(self.who)}의 운도 때가 되면 반드시 열려요. <b>{mind}</b> __PALM_CLOSING__</div>
 <div class="rule"></div>
 <div class="tiny"><b>판독 참고와 한계</b> · __PALM_LIMIT__{" ".join(lim)}<br><br>
 <b>안내</b> · 이 감정서는 {basis}에 따른 해석이에요. 과학적으로 검증된 예측이 아니며 오락과 자기 이해를 위한 참고 자료예요. 건강·투자·법률 등 중요한 결정은 반드시 전문가와 상의하세요.</div>
</div><div class="foot">MYEONGUN · __PG__ · 명운 {'사주·손금' if palm else '사주'} 종합 감정서</div></section>'''

    def tips_short(self):
        cur_ms = [m for m in self.mp if m[1] > self.now and m[0].year <= self.Y + 1 and (m[0].year == self.Y or m[3] == "小寒")]
        if not cur_ms: return "다음 해 계획을 세우세요."
        g = max(cur_ms, key=lambda m: self.c.score(m[2])[0])
        return f"{g[0].month}월({g[2]})의 기회를 잡고, 연말연시에는 무리한 지출을 줄이세요."

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
        when = (f"<b>50대({y50}년~)</b>에 재산이 가장 크게 쌓여요" if js == "above_heart" else
                f"젊어서부터 꾸준히, 특히 <b>{'·'.join(map(str, top2))}년</b>" if js == "long" else f"사주의 좋은 해 <b>{'·'.join(map(str, top2))}년</b>이 기준점")
        love1 = (self.best_love_years(1) or [None])[0]
        tal = {"moon": "기획·창작·교육", "curve": "기획·교육·콘텐츠", "straight": "분석·실무·금융", "mercury": "영업·투자·말"}.get(hs, "기획")
        rows = [("돈 버는 방식", f"{'정재 중심(월급·저축·전문성)' if jj >= pj else '편재 중심(활동·거래)'}{' + 재다신약' if (not c.strong and c.gcount['재성'] >= 2) else ''}", f"사업선 {items[1]['tag']}", way),
                ("재물이 커지는 때", f"{bd['gz']} 대운(만 {bd['a0']}~{bd['a1']}세)" if bd else "-", f"재운선 {items[0]['tag']}", when),
                ("수입원", f"정재 {jj} · 편재 {pj}", f"재운선 {jn}가닥", "<b>본업 + 하나 더</b>" if jn >= 2 or pj else "<b>한 우물</b>을 깊게"),
                ("일·도약", f"좋은 해 {'·'.join(map(str, top2))}", f"운명선 {items[2]['tag']}", f"<b>{y35}~{y35 + 3}년</b>이 커리어의 분기점" if fs != "none" else "한 분야를 정할수록 운명선이 선명해져요"),
                ("재능", f"{c.gyeok}", f"두뇌선 {items[4]['tag']}", f"{tal}에서 빛남"),
                ("사랑", f"배우자궁 {c.tg(c.db, True)}" + (f", {love1}년 인연운 1순위" if love1 else ""), f"감정선 {items[5]['tag']}", "천천히 고르고 <b>깊고 오래</b> 가는 인연" if fl.get("heart", {}).get("clarity", "clear") == "clear" else "표현을 늘릴수록 깊어지는 인연"),
                ("체력", c.st_label, f"생명선 {items[3]['tag']}", "회복력은 좋음, <b>과로만 조심</b>" if fl.get("life", {}).get("venus", "wide") == "wide" else "<b>휴식과 수면</b>이 최우선")]
        tr = "".join(f'<tr><td><b>{a}</b></td><td class="small">{b}</td><td class="small">{p}</td><td class="small">{d}</td></tr>' for a, b, p, d in rows)
        mrows = []
        for cat, ys in self.runs():
            a0, a1 = c.age(ys[0]), c.age(ys[-1])
            mrows.append(ys[0]); mrows[-1] = (ys[0], f'<tr{" class=hl" if cat == "up" else ""}><td>{ys[0]}~{ys[-1]}</td><td>{a0}~{a1}세</td><td class="small">{"<b>도약.</b> 운이 받쳐 주는 시기. 승진·내 집·독립을 크게 펼치기." if cat == "up" else "준비와 선택의 시기. 실력·저축·관계를 다지기."}</td></tr>')
        if bd: mrows.append((bd["y0"], f'<tr class="hl"><td>{bd["y0"]}~{bd["y1"]}</td><td>{bd["a0"]}~{bd["a1"]}세</td><td class="small"><b>재물 규모 최대.</b> {bd["gz"]} 대운. 체력과 ‘나눠 맡기기’가 조건.</td></tr>'))
        if js == "above_heart": mrows.append((y50, f'<tr class="hl"><td>{y50}~{y50 + 12}</td><td>50~62세</td><td class="small"><b>만년의 복.</b> 재운선이 말하는 50~55세 이후. 쌓아 둔 재물이 드러나요.</td></tr>'))
        mrows = "".join(x for _, x in sorted(mrows))
        first_up = next((ys for cat, ys in self.runs() if cat == "up"), None)
        concl = (f"{esc(self.who)}은 <b>{'젊어서 크게 벌기보다 실력과 저축으로 차곡차곡 쌓아' if js != 'long' else '일찍부터 재물과 인연이 닿아'}"
                 f"{' ' + str(first_up[0] // 10 * 10) + '년대 ' + ('초반' if first_up[0] % 10 < 5 else '후반') + '에 도약하고' if first_up else ''}"
                 f"{' 50대에 크게 거두는' if js == 'above_heart' else ' 좋은 해마다 한 단계씩 올라서는'}</b> 사주이자 손이에요. 서두르지 않는 것이 가장 큰 재테크예요.")
        lk = ", ".join(lucky) if lucky else "뚜렷한 대박손금은 없어요"
        return f'''<section class="page"><div class="in">
 <h2><span class="no">{self.nxt()}</span>사주 × 손금 종합</h2>
 <div class="sub">두 가지 체계가 같은 말을 하는 곳이 가장 믿을 만한 결론이에요 · 대박손금: {lk}</div>
 <table><tr><th style="width:17%">주제</th><th style="width:28%">사주가 말하는 것</th><th style="width:27%">손금이 말하는 것</th><th>종합</th></tr>{tr}</table>
 <h3>{esc(self.who)} 인생의 재물 지도</h3>
 <table><tr><th style="width:20%">시기</th><th style="width:16%">나이</th><th>흐름</th></tr>{mrows}</table>
 <div class="box dark" style="margin-top:3mm"><span class="gold">한 문장 결론</span> · {concl}</div>
</div><div class="foot">MYEONGUN · __PG__</div></section>'''
