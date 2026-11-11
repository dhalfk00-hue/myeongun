#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""손명리 결혼 궁합 감정서 생성기 (규칙 기반, LLM 없음).
예) python3 make_gunghap.py --f-date 1992-03-14 --f-time 09:30 --f-place 서울 \
      --m-name 홍길동 --m-date 1990-07-02 --m-time 18:00 --m-place 부산 --out /tmp/gunghap.pdf"""
import argparse, asyncio, json, os, re, shutil, subprocess, sys, time
from datetime import datetime
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import engine as E
import saju as S
import build as B
from build import esc, elsp, stars, ko, el_full
from engine import STEM_ELK, BR_ELK
from texts import *
from make_report import render, time_label
import lunar as L

GM = {"F": GROUP_MEAN_F, "M": GROUP_MEAN_M}


class Person:
    def __init__(self, label, name, gender, date, lunar, leap, t, place, place_label, now):
        self.r = E.run_saju(date, t, lunar, leap, gender, place, now.year, now.year + 11)
        self.c = E.Chart(self.r, gender, now)
        self.rep = B.Report(self.c, name, {}, now)
        self.label = label; self.name = name; self.gender = gender
        self.date, self.lunar, self.leap, self.time, self.place_label = date, lunar, leap, t, place_label or place
        self.who = (name + "님") if name else label

    def chars(self):
        out = []
        for n, p in self.c.P.items():
            if n == "시" and not self.c.time_known: continue
            out.append((n, "s", p["gz"][0])); out.append((n, "b", p["gz"][1]))
        return out

    def dlabel(self):
        sd = self.r["solar_date"]
        if self.lunar:
            return f"음력 {self.date.replace('-', '.')} (양력 {sd.replace('-', '.')}) {time_label(self.time)}"
        return f"양력 {self.date.replace('-', '.')} {time_label(self.time)}"


def rels(a, b, stems=False):
    return S.pair_relations(a, b, stems)


class Gunghap:
    def __init__(self, F, M, now, time_note=""):
        self.F, self.M, self.now = F, M, now
        self.Y = now.year; self.years = list(range(self.Y, self.Y + 10))
        self.time_note = time_note
        self.score_items = []
        self._score()

    # ------------------------------------------------------------ 점수
    def _score(self):
        F, M = self.F.c, self.M.c
        items = []
        # A 일간 관계 15
        a, b = F.dm, M.dm
        tg_f = S.ten_god(a, b)  # 여자 입장에서 남자 일간
        ia = TG_GROUP[tg_f]
        if rels(a, b, True) and "합" in rels(a, b, True)[0]: sA, why = 15, f"{a}{b} 천간합: 서로 끌리고 묶이는 일간"
        elif "천간충" in rels(a, b, True): sA, why = 6, f"{a}{b} 충: 생각의 방향이 정반대"
        elif ia == "비겁":
            sA = 11; why = f"같은 {F.dm_el}({EL_HAN[F.dm_el]}) 일간: 친구 같은 동지형"
            if {a, b} == {"甲", "乙"}: why += " · 큰 나무와 덩굴이 함께 뻗는 등라계갑(藤蘿繫甲)"
        elif ia in ("인성", "식상"): sA, why = 12, "한쪽이 다른 쪽을 낳아 주는 상생 관계"
        elif ia == "관성": sA, why = (13 if tg_f == "정관" else 10), f"남자가 여자의 {tg_f}: 전통적으로 안정된 부부 배치"
        else: sA, why = 9, "여자가 남자를 이끄는 관계"
        items.append(("일간 관계", 15, sA, why))
        # B 용신 보완 20
        def avgfav(p, q):  # p 입장에서 q의 글자
            vals = [p.c.fav[STEM_ELK[ch]] if k == "s" else p.c.branch_fav(ch) for _, k, ch in q.chars()]
            return sum(vals) / len(vals)
        fF, fM = avgfav(self.F, self.M), avgfav(self.M, self.F)
        sB = sum(max(0, min(10, 10 * (v + 1.5) / 2.5)) for v in (fF, fM))
        self.fav_avgs = (fF, fM)
        miss_f = [e for e in F.cnt if F.cnt[e] == 0 and M.cnt[e] > 0]
        miss_m = [e for e in M.cnt if M.cnt[e] == 0 and F.cnt[e] > 0]
        why = f"서로의 글자가 상대에게 주는 평균 호감도 {self.F.who} {fF:+.2f} · {self.M.who} {fM:+.2f}"
        if miss_f: why += f" · {self.M.who}가 {self.F.who}에게 없는 {'·'.join(miss_f)}을 채워 줌"
        if miss_m: why += f" · {self.F.who}가 {self.M.who}에게 없는 {'·'.join(miss_m)}을 채워 줌"
        items.append(("오행·용신 보완", 20, round(sB), why))
        # C 배우자궁 20
        r = rels(F.db, M.db)
        sC = 12; bits = []
        for t in r:
            if t.startswith("육합"): sC += 8; bits.append("육합")
            elif t.startswith("삼합 반합"): sC += 5; bits.append("반합")
            elif t.startswith("삼합 가합") or t.startswith("방합"): sC += 2; bits.append(t.split("(")[0].replace("삼합 ", ""))
            elif t == "충": sC -= 7; bits.append("충")
            elif "형" in t: sC -= 4; bits.append("형")
            elif t == "원진": sC -= 3; bits.append("원진")
            elif t == "귀문관": sC -= 2; bits.append("귀문")
            elif t == "해": sC -= 2; bits.append("해")
            elif t == "파": sC -= 1; bits.append("파")
        if S.branch_ten_god(M.dm, F.db) == "정재": sC += 2; bits.append(f"{self.F.who}의 일지가 {self.M.who}에게 정재(아내 별)")
        if S.branch_ten_god(F.dm, M.db) == "정관": sC += 2; bits.append(f"{self.M.who}의 일지가 {self.F.who}에게 정관(남편 별)")
        sC = max(3, min(20, sC))
        items.append(("배우자궁(일지)", 20, sC, f"{F.db}·{M.db}: " + (", ".join(bits) if bits else "특별한 합충 없음(무난)")))
        # D 천간 교차 10
        sD = 5; bits = []
        for n1, k1, c1 in self.F.chars():
            if k1 != "s": continue
            for n2, k2, c2 in self.M.chars():
                if k2 != "s": continue
                rr = rels(c1, c2, True)
                if not rr: continue
                if rr[0].startswith("천간합"): sD += 2.5; bits.append(f"{c1}{c2}합")
                else: sD -= 1.5; bits.append(f"{c1}{c2}충")
        self.cheonji = []
        for n1, p1 in F.P.items():
            for n2, p2 in M.P.items():
                if (n1 == "시" and not F.time_known) or (n2 == "시" and not M.time_known): continue
                st = rels(p1["gz"][0], p2["gz"][0], True); br = rels(p1["gz"][1], p2["gz"][1])
                if st and st[0].startswith("천간합") and any(t.startswith("육합") for t in br):
                    self.cheonji.append((n1, p1["gz"], n2, p2["gz"]))
        if self.cheonji: sD += 2; bits.append("천지합 " + ", ".join(f"{a}-{b}" for _, a, _, b in self.cheonji))
        sD = max(0, min(10, sD)); self.stem_bits = bits
        items.append(("천간 교차", 10, round(sD), ", ".join(bits) or "합·충 없음"))
        # E 지지 교차 10 (일지-일지 제외)
        sE = 5; bits = []; seenp = set()
        for n1, k1, c1 in self.F.chars():
            if k1 != "b": continue
            for n2, k2, c2 in self.M.chars():
                if k2 != "b" or (n1 == "일" and n2 == "일") or (c1 + c2) in seenp: continue
                seenp.add(c1 + c2)
                rr = rels(c1, c2)
                if "충" in rr: rr = [t for t in rr if "형" not in t]
                for t in rr:
                    lab = f"{c1}{c2}"
                    if t.startswith("육합"): sE += 1.5; bits.append(lab + "합")
                    elif t.startswith("삼합 반합"): sE += 1; bits.append(lab + "반합")
                    elif t.startswith("삼합 가합"): sE += 0.5; bits.append(lab + "가합")
                    elif t == "충": sE -= 1.5; bits.append(lab + "충")
                    elif "형" in t: sE -= 1; bits.append(lab + "형")
                    elif t in ("원진",): sE -= 0.5; bits.append(lab + "원진")
        sE = max(0, min(10, sE)); self.br_bits = list(dict.fromkeys(bits))
        items.append(("지지 교차(전체)", 10, round(sE), ", ".join(self.br_bits) or "무난"))
        # F 띠 5
        yf, ym = F.P["년"]["gz"][1], M.P["년"]["gz"][1]
        r = rels(yf, ym); sF = 3
        for t in r:
            if t.startswith("육합") or t.startswith("삼합 반합"): sF += 2
            elif t == "충": sF -= 2
            elif "형" in t or t == "원진": sF -= 1
        sF = max(0, min(5, sF))
        items.append(("년지(띠)", 5, sF, f"{yf}({S.ANIMALS[S.BRANCHES.index(yf)]})·{ym}({S.ANIMALS[S.BRANCHES.index(ym)]}): " + (", ".join(r) if r else "합·충 없음(무난)")))
        # G 배우자 별 10
        gwan = F.gel["관성"]; jae = M.gel["재성"]
        wm, wf = M.wt[gwan], F.wt[jae]
        sG = 5 * min(1, wm / 1.5) + 5 * min(1, wf / 1.5)
        items.append(("배우자 별 교환", 10, round(sG), f"{self.M.who} 사주 속 {self.F.who}의 남편 별({gwan}) 가중 {wm} · {self.F.who} 사주 속 {self.M.who}의 아내 별({jae}) 가중 {wf}"))
        # H 시기 10
        self.both_love = [y for y in self.years if self.F.rep.love[y] >= 1.4 and self.M.rep.love[y] >= 1.4]
        self.both_good = [y for y in self.years if self.F.rep.ystar[y] >= 4 and self.M.rep.ystar[y] >= 4]
        self.both_bad = [y for y in self.years if self.F.rep.ystar[y] <= 2 and self.M.rep.ystar[y] <= 2]
        sH = max(2, min(10, 4 + 2 * len(self.both_love) + len(self.both_good) - len(self.both_bad)))
        items.append(("결혼 시기 일치", 10, sH, f"둘 다 인연운이 강한 해 {', '.join(map(str, self.both_love)) or '없음'} · 둘 다 좋은 해 {', '.join(map(str, self.both_good)) or '없음'}"))
        self.score_items = items
        self.total = sum(x[2] for x in items)

    def grade(self):
        t = self.total
        return ("천생연분형" if t >= 85 else "아주 좋은 궁합" if t >= 75 else "좋은 궁합 · 노력하면 더 좋아지는 궁합" if t >= 65 else "보통 · 서로 맞춰 가는 궁합" if t >= 55 else "노력이 필요한 궁합")

    # ------------------------------------------------------------ 부품
    def mini_pillars(self, P, cover=False):
        c = P.c; out = ""
        for n, lb in (("시", "시"), ("일", "일·나"), ("월", "월"), ("년", "년")):
            if n == "시" and not c.time_known:
                out += f'<div class="pl"><div class="lb">{lb}</div><div class="ch"><span>?</span><span>?</span></div><div class="tg">미상</div></div>'; continue
            p = c.P[n]; gz = p["gz"]
            tg = "일간·" + p["branch_tengod"] if n == "일" else f'{p["stem_tengod"]}·{p["branch_tengod"]}'
            out += f'<div class="pl{" me" if n == "일" else ""}"><div class="lb">{lb}</div><div class="ch">{elsp(gz[0])}{elsp(gz[1])}</div><div class="tg">{tg}</div></div>'
        return out

    def year_cross(self, y):
        gz = E.year_gz(y); F, M = self.F, self.M
        return F.rep.ystar[y], M.rep.ystar[y], F.rep.love[y], M.rep.love[y]

    def best_years(self):
        sc = {y: self.F.rep.love[y] + self.M.rep.love[y] + 0.08 * (self.F.rep.ysc[y] + self.M.rep.ysc[y]) - 0.05 * (y - self.Y) for y in self.years}
        return sorted(self.years, key=lambda y: -sc[y]), sc

    def love_reason(self, P, y):
        c = P.c; gz = E.year_gz(y); bits = []
        se = c.gel["관성"] if c.gender == "F" else c.gel["재성"]
        nm = "남편 별(관성)" if c.gender == "F" else "아내 별(재성)"
        if STEM_ELK[gz[0]] == se or BR_ELK[gz[1]] == se:
            tg = c.tg(gz[0]) if STEM_ELK[gz[0]] == se else c.tg(gz[1], True)
            bits.append(f"{nm} {tg}")
        if frozenset(gz[0] + c.dm) in S.STEM_HAP: bits.append(f"{gz[0]}{c.dm}합")
        rr = S.pair_relations(gz[1], c.db)
        if any(t.startswith("육합") or t.startswith("삼합 반합") for t in rr): bits.append("배우자궁 합")
        if "충" in rr: bits.append("배우자궁 충")
        return ", ".join(bits) or "-"

    # ------------------------------------------------------------ 페이지
    def p_cover(self):
        F, M = self.F, self.M
        best, _ = self.best_years()
        keys = self.key5()
        ks = "".join(f'<div class="k"><div class="n">{i+1}</div><div class="t"><b>{t}</b>{d.replace("<b>", "<strong>").replace("</b>", "</strong>")}</div></div>' for i, (t, d) in enumerate(keys))
        return f'''<section class="page cover"><div class="in">
 <div class="brand"><div class="seal">合</div><div class="name">손명리</div><div class="en">SONMYEONGRI · MARRIAGE COMPATIBILITY</div></div>
 <div class="ctitle">결혼 궁합 감정서</div>
 <div class="cmeta">{esc(F.who)}(여) {esc(F.dlabel())} {esc(F.place_label)} &nbsp;×&nbsp; {esc(M.who)}(남) {esc(M.dlabel())} {esc(M.place_label)}</div>
 <div style="display:flex;justify-content:center;gap:7mm;align-items:center;margin:4mm 0 2mm">
  <div><div class="serif" style="text-align:center;color:#e9c97c;font-size:10pt;letter-spacing:.2em">{esc(F.who)} · 여</div><div class="pillars gp">{self.mini_pillars(F)}</div></div>
  <div class="score"><div class="num">{self.total}</div><div class="of">/ 100</div></div>
  <div><div class="serif" style="text-align:center;color:#e9c97c;font-size:10pt;letter-spacing:.2em">{esc(M.who)} · 남</div><div class="pillars gp">{self.mini_pillars(M)}</div></div>
 </div>
 <div class="serif" style="text-align:center;color:#f0cd7d;font-size:13pt;margin-bottom:2mm">{self.grade()}</div>
 <div class="key5">{ks}</div>
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def key5(self):
        F, M = self.F, self.M; Fc, Mc = F.c, M.c
        best, sc = self.best_years()
        out = []
        a = self.score_items[0][3]
        out.append((f"일간 {Fc.dm}{EL_HAN[Fc.dm_el]} × {Mc.dm}{EL_HAN[Mc.dm_el]}: {a.split(':')[-1].split('·')[-1].strip()}",
                    (STEM[Fc.dm]['img'] + "와 " + STEM[Mc.dm]['img'] + "의 만남이에요. ") + ("두 사람 모두 용신이 같은 " + el_full(Fc.yong) + "이라 좋아하는 환경과 쉬는 방식이 닮았어요." if Fc.yong == Mc.yong else f"{F.who}의 용신은 {el_full(Fc.yong)}, {M.who}의 용신은 {el_full(Mc.yong)}이에요.")))
        sb = [x for x in self.stem_bits if "합" in x]
        out.append(("끌림의 표식: " + (", ".join(sb[:2]) if sb else "배우자 별 교환"),
                    self.attraction_text()))
        out.append((f"조심할 자리: 배우자궁 {Fc.db}·{Mc.db}", self.palace_short()))
        b1 = best[0]
        out.append((f"결혼 적기 1순위 {b1}년 {E.year_gz(b1)}",
                    f"{F.who}: {self.love_reason(F, b1)} / {M.who}: {self.love_reason(M, b1)}. " + self.window_text() + f"그다음 후보는 {', '.join(map(str, best[1:3]))}년이에요."))
        bad = [x[1] for x in self.cautions()]
        out.append(("함께 지킬 해와 개운", f"{'·'.join(map(str, bad[:3])) + '년은 한 사람에게 충이 드는 해라, 이사·큰 지출을 몰지 말고 서로 받쳐 주세요. ' if bad else ''}함께 쓰면 좋은 기운은 <b>{ELEM[Fc.yong]['colors'].split('·')[0]}·{ELEM[Fc.hee]['colors'].split('·')[0]}, {ELEM[Fc.yong]['dir']}</b>{'' if Fc.yong == Mc.yong else ' / ' + ELEM[Mc.yong]['colors'].split('·')[0]}이에요."))
        return out

    def window_text(self):
        F, M = self.F, self.M
        win = [y for y in self.years if F.rep.love[y] + M.rep.love[y] >= 2.8]; runs = []
        for y in win:
            if runs and y == runs[-1][-1] + 1: runs[-1].append(y)
            else: runs.append([y])
        rr = max(runs, key=len) if runs else []
        return f"<b>{rr[0]}~{rr[-1]}년</b>이 두 사람의 인연 신호가 연달아 겹치는 ‘결혼의 창’이에요. " if len(rr) >= 2 else ""

    def attraction_text(self):
        F, M = self.F, self.M; Fc, Mc = F.c, M.c; s = []
        # 천지합 체크
        for n1, g1, n2, g2 in self.cheonji:
                    p1 = {"gz": g1}; p2 = {"gz": g2}
                    s.append(f"{F.who}의 {n1}주 {p1['gz']}와 {M.who}의 {n2}주 {p2['gz']}가 <b>천간·지지가 모두 합(천지합)</b>해요. 처음부터 끌림이 강한 인연의 표식이에요.")
        gw = Fc.gel["관성"]; jae = Mc.gel["재성"]
        if Fc.cnt[gw] == 0 and Mc.cnt[gw] > 0:
            s.append(f"{F.who} 사주에 겉으로 없는 남편 별 {gw}({EL_HAN[gw]})을 {M.who}가 가지고 있어요.")
        if Fc.wt[jae] >= 1.5: s.append(f"{M.who}의 아내 별 {jae}({EL_HAN[jae]})이 {F.who} 사주에 넉넉해요.")
        return " ".join(s[:3]) or "배우자 별과 합이 고르게 있어 무난하게 가까워지는 인연이에요."

    def palace_short(self):
        Fc, Mc = self.F.c, self.M.c; r = rels(Fc.db, Mc.db)
        if not r: return "두 사람의 배우자궁은 서로 부딪히지 않아 생활 공간을 나누기 편한 사이예요."
        good = [t for t in r if "합" in t]; bad = [t for t in r if t in ("충", "원진", "귀문관", "해", "파") or "형" in t]
        s = ""
        if good: s += f"배우자궁이 {'·'.join(x.split('(')[0] for x in good)}으로 묶여 함께 사는 생활이 편해요. "
        if "원진" in bad or "귀문관" in bad:
            s += "배우자궁이 원진·귀문으로 만나요. 미워서가 아니라 <b>사소한 서운함이 쌓이고 서로 예민해지기 쉬운</b> 배치라, 서운한 건 그날 말로 푸는 습관이 해결책이에요."
        elif "충" in bad: s += "배우자궁이 충해 생활 방식이 달라요. 공간·일정을 나누면 오히려 활력이 돼요."
        elif bad: s += f"배우자궁에 {'·'.join(bad)}이 있어 생활 습관 조율이 필요해요."
        return s

    def p_charts(self):
        F, M = self.F, self.M
        def tbl(P):
            c = P.c
            cols = [n for n in ("시", "일", "월", "년") if n != "시" or c.time_known]
            hdr = {"시": "시주", "일": "일주", "월": "월주", "년": "년주"}
            rows = '<tr><th></th>' + "".join(f"<th>{hdr[n]}</th>" for n in cols) + "</tr>"
            rows += '<tr><td class="small">십신</td>' + "".join(f'<td class="small">{"일간" if n == "일" else c.P[n]["stem_tengod"]}</td>' for n in cols) + "</tr>"
            rows += '<tr><td class="small">천간</td>' + "".join(f'<td class="big el-{STEM_ELK[c.P[n]["gz"][0]]}">{c.P[n]["gz"][0]}</td>' for n in cols) + "</tr>"
            rows += '<tr><td class="small">지지</td>' + "".join(f'<td class="big el-{BR_ELK[c.P[n]["gz"][1]]}">{c.P[n]["gz"][1]}</td>' for n in cols) + "</tr>"
            rows += '<tr><td class="small">십신</td>' + "".join(f'<td class="small">{c.P[n]["branch_tengod"]}</td>' for n in cols) + "</tr>"
            rows += '<tr><td class="small">지장간</td>' + "".join(f'<td class="small">{" ".join(h["stem"] for h in c.P[n]["hidden"])}</td>' for n in cols) + "</tr>"
            return f'<table class="mchart sm">{rows}</table>'
        def summ(P):
            c = P.c
            return (f'<ul class="small" style="margin-top:2mm"><li><b>일간</b> {c.dm}{EL_HAN[c.dm_el]} · {STEM[c.dm]["title"]}</li>'
                    f'<li><b>강약</b> {c.st_label} ({int(c.ratio * 100)}%) · <b>격국</b> {c.gyeok}</li>'
                    f'<li><b>용신</b> {el_full(c.yong)} · <b>희신</b> {el_full(c.hee)} · <b>기신</b> {el_full(c.gi)}</li>'
                    f'<li><b>오행</b> ' + " ".join(f'<span class="el-{e}">{e}{c.cnt[e]}</span>' for e in ("목", "화", "토", "금", "수")) + '</li>'
                    f'<li><b>현재 대운</b> {(c.current_daeun(self.Y) or {}).get("gz", "-")}</li></ul>')
        return f'''<section class="page"><div class="in">
 <h2><span class="no">01</span>두 사람의 명식</h2>
 <div class="sub">만세력 계산(KASI 음력·절기, 출생지 경도 보정) · 나이는 만 나이</div>
 <div class="two">
  <div><h3 style="margin-top:0">{esc(F.who)} (여)</h3><p class="tiny" style="margin:0 0 1mm">{esc(F.dlabel())} · {esc(F.place_label)}</p>{tbl(F)}{summ(F)}</div>
  <div><h3 style="margin-top:0">{esc(M.who)} (남)</h3><p class="tiny" style="margin:0 0 1mm">{esc(M.dlabel())} · {esc(M.place_label)}</p>{tbl(M)}{summ(M)}</div>
 </div>
 <div class="box small"><b class="gold">출생 시각 검증</b> · {self.time_note}</div>
 <h3>오행 비교 · 서로를 채워 주나</h3>
 {self.elem_compare()}
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def elem_compare(self):
        Fc, Mc = self.F.c, self.M.c
        colr = {"목": "#2f7a4c", "화": "#c0392b", "토": "#a0762a", "금": "#7d8590", "수": "#1f4e8c"}
        mx = max(max(Fc.wt.values()), max(Mc.wt.values()))
        rows = ""
        for e in ("목", "화", "토", "금", "수"):
            tag = []
            if e == Fc.yong: tag.append(f"{self.F.who} 용신")
            if e == Mc.yong: tag.append(f"{self.M.who} 용신")
            if e == Fc.hee: tag.append(f"{self.F.who} 희신")
            if e == Mc.hee: tag.append(f"{self.M.who} 희신")
            rows += (f'<tr><td class="el-{e}"><b>{e}({EL_HAN[e]})</b></td>'
                     f'<td><div class="track" style="height:3.4mm;background:#f1e7d0;border-radius:2mm"><div style="height:100%;width:{int(Fc.wt[e] / mx * 100)}%;background:{colr[e]};border-radius:2mm"></div></div><span class="tiny">{Fc.cnt[e]}개 · {Fc.wt[e]}</span></td>'
                     f'<td><div class="track" style="height:3.4mm;background:#f1e7d0;border-radius:2mm"><div style="height:100%;width:{int(Mc.wt[e] / mx * 100)}%;background:{colr[e]};border-radius:2mm"></div></div><span class="tiny">{Mc.cnt[e]}개 · {Mc.wt[e]}</span></td>'
                     f'<td class="small">{" · ".join(tag)}</td></tr>')
        fF, fM = self.fav_avgs
        same = Fc.yong == Mc.yong
        txt = (f"두 사람 모두 <b>용신 {el_full(Fc.yong)}·희신 {el_full(Fc.hee)}</b>로 같아요. 같은 것을 필요로 하는 사이라 취향·쉬는 방식이 잘 맞고, "
               f"서로의 {EL_WORD[Fc.yong]}·{EL_WORD[Fc.hee]} 글자가 상대에게 힘이 돼요. 대신 둘 다 부족한 기운을 상대가 대신 채워 주지는 못하니, <b>함께 생활 속에서 채우는 것</b>(개운법)이 중요해요."
               if same else f"{self.F.who}의 용신 {el_full(Fc.yong)}은 {self.M.who} 사주에 {Mc.cnt[Fc.yong]}개, {self.M.who}의 용신 {el_full(Mc.yong)}은 {self.F.who} 사주에 {Fc.cnt[Mc.yong]}개 있어요.")
        txt += f" 상대의 글자가 나에게 주는 평균 호감도는 {self.F.who} {fF:+.2f}, {self.M.who} {fM:+.2f}예요(−2 부담 ~ +2 큰 도움)."
        return f'<table><tr><th style="width:12%">오행</th><th style="width:30%">{esc(self.F.who)}</th><th style="width:30%">{esc(self.M.who)}</th><th>비고</th></tr>{rows}</table><p class="small" style="margin-top:2mm">{txt}</p>'

    def p_score(self):
        rows = "".join(f'<tr><td><b>{a}</b></td><td style="text-align:center">{c} / {b}</td><td class="small">{esc(d) if "<" not in d else d}</td></tr>' for a, b, c, d in self.score_items)
        Fc, Mc = self.F.c, self.M.c
        ilgan = self.ilgan_text()
        return f'''<section class="page tight"><div class="in">
 <h2><span class="no">02</span>궁합 점수 {self.total}점 · {self.grade()}</h2>
 <div class="sub">8개 항목을 정해진 규칙으로 채점한 합계예요 · 같은 기준을 모든 커플에 똑같이 적용해요</div>
 <table><tr><th style="width:22%">항목</th><th style="width:13%">점수</th><th>근거</th></tr>{rows}
 <tr class="hl"><td><b>합계</b></td><td style="text-align:center"><b>{self.total} / 100</b></td><td class="small">85↑ 천생연분형 · 75↑ 아주 좋음 · 65↑ 좋음(노력하면 더 좋아짐) · 55↑ 보통 · 그 아래 노력 필요</td></tr></table>
 <p class="tiny" style="margin-top:1.4mm">채점 방법: 일간(천간합 15·상생 12·정관 13·비겁 11·충 6) · 용신 보완(상대 글자가 내 용신·기신에 주는 평균 호감도를 사람마다 10점으로 환산) · 배우자궁(기본 12, 육합 +8, 반합 +5, 충 −7, 형 −4, 원진 −3, 귀문 −2, 해 −2, 파 −1, 일지가 상대의 정재·정관이면 +2) · 천간 교차(기본 5, 합 +2.5, 충 −1.5, 한 기둥끼리 천간·지지가 모두 합하는 천지합 +2) · 지지 교차(같은 글자 쌍은 한 번만, 기본 5, 합 +1.5, 반합 +1, 가합 +0.5, 충 −1.5(충·형 겹치면 충만), 형 −1, 원진 −0.5) · 띠(기본 3, 합 +2, 충 −2, 형·원진 −1) · 배우자 별(상대 사주 속 내 배우자 오행의 양) · 시기(향후 10년 중 둘 다 인연운이 강한 해·좋은 해).</p>
 <h3>일간 관계 · {Fc.dm}{EL_HAN[Fc.dm_el]} × {Mc.dm}{EL_HAN[Mc.dm_el]}</h3>
 {ilgan}
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def ilgan_text(self):
        F, M = self.F, self.M; a, b = F.c.dm, M.c.dm
        s = f"<p><b>{F.who}</b>은 {STEM[a]['img']}, <b>{M.who}</b>는 {STEM[b]['img']}예요. "
        if {a, b} == {"甲", "乙"}:
            big, small = (F.who, M.who) if a == "甲" else (M.who, F.who)
            s += (f"같은 나무 기운이라 생각의 뿌리가 닮은 <b>친구 같은 부부</b>가 되기 쉬워요. 전통적으로 큰 나무(甲)에 덩굴(乙)이 감고 올라가는 모양을 <b>등라계갑(藤蘿繫甲)</b>이라 해서, "
                  f"{small}는 {big}에게 기대어 함께 높이 오르고 {big}는 {small} 덕분에 외롭지 않은 관계로 봐요.</p>"
                  f"<p class='small'>다만 둘 다 자존심이 있는 나무라, <b>누가 이끄느냐</b>를 두고 은근히 경쟁하기 쉬워요. 집안일·돈·계획마다 ‘담당’을 정해 두면 충돌이 확 줄어요.</p>")
        else:
            tg = S.ten_god(a, b); tg2 = S.ten_god(b, a)
            s += f"{F.who} 입장에서 {M.who}는 {tg}, {M.who} 입장에서 {F.who}는 {tg2}예요. {TG_THEME[tg][1]}</p>"
        return s

    def p_palace(self):
        F, M = self.F, self.M; Fc, Mc = F.c, M.c
        r = rels(Fc.db, Mc.db)
        li = []
        li.append(f"<li><b>배우자궁 {Fc.db}({F.who}) · {Mc.db}({M.who})</b>: {', '.join(r) if r else '합·충 없음'}. {self.palace_short()}</li>")
        yf, ym = Fc.P["년"]["gz"][1], Mc.P["년"]["gz"][1]
        ry = rels(yf, ym)
        li.append(f"<li><b>띠 {S.ANIMALS[S.BRANCHES.index(yf)]}({yf}) · {S.ANIMALS[S.BRANCHES.index(ym)]}({ym})</b>: " + (f"{', '.join(ry)}." if ry else "서로 부딪히지 않는 무난한 띠 궁합이에요. 양가 어른들과의 관계도 큰 무리가 없어요.") + "</li>")
        # 원진·귀문 전체
        wg = []
        for n1, k1, c1 in F.chars():
            for n2, k2, c2 in M.chars():
                if k1 == "b" and k2 == "b":
                    for t in rels(c1, c2):
                        if t in ("원진", "귀문관"): wg.append(f"{F.who} {n1}지 {c1}·{M.who} {n2}지 {c2} {t}")
        li.append("<li><b>원진·귀문</b>: " + ("; ".join(dict.fromkeys(wg)) + ". 원진은 ‘이유 없이 서운한’ 기운, 귀문은 예민함·직감이에요. 두 사람이 같이 지칠 때 날카로워지기 쉬우니, 피곤한 날엔 중요한 대화를 미루는 것만으로 충분해요." if wg else "두 사람 사이에 원진·귀문이 없어요.") + "</li>")
        # 기타 교차
        li.append(f"<li><b>천간 교차</b>: {', '.join(self.stem_bits) or '없음'}. " + self.stem_text() + "</li>")
        li.append(f"<li><b>지지 교차</b>: {', '.join(self.br_bits) or '없음'}. 합은 서로 돕는 자리, 충·형은 생활에서 부딪히는 자리예요.</li>")
        # 관성-재성
        gw = Fc.gel["관성"]; jae = Mc.gel["재성"]
        hid_f = [h["stem"] for p in Fc.P.values() for h in p["hidden"] if TG_GROUP[h["tengod"]] == "관성"]
        gw_m = [f"{n}지 {p['gz'][1]}" for n, p in Mc.P.items() if BR_ELK[p["gz"][1]] == gw] + [f"{n}간 {p['gz'][0]}" for n, p in Mc.P.items() if STEM_ELK[p["gz"][0]] == gw]
        gw_mh = [h["stem"] for p in Mc.P.values() for h in p["hidden"] if STEM_ELK[h["stem"]] == gw]
        jae_f = [f"{n}지 {p['gz'][1]}" for n, p in Fc.P.items() if BR_ELK[p["gz"][1]] == jae]
        rel_txt = (f"{F.who} 사주에는 남편 별 관성({gw}, {EL_HAN[gw]})이 겉에 {Fc.cnt[gw]}개이고 지장간에 {'·'.join(hid_f) or '없음'}로 숨어 있어요. "
                   f"{M.who} 사주에는 그 {gw}이 {', '.join(gw_m) or '겉에는 없고'} {('지장간 ' + '·'.join(gw_mh)) if gw_mh else ''}로 들어 있어, "
                   f"<b>{F.who}에게 숨어 있던 남편 별을 겉으로 꺼내 주는 사람</b>이에요. ")
        mtg = [S.branch_ten_god(Fc.dm, Mc.P[n]["gz"][1]) for n in Mc.P if BR_ELK[Mc.P[n]["gz"][1]] == gw]
        if mtg: rel_txt += f"{F.who} 기준으로 {M.who}의 {gw}은 {'·'.join(dict.fromkeys(mtg))}이라 {'바르고 책임감 있는 남편상' if '정관' in mtg else '추진력 있는 남편상'}과 맞아요. "
        rel_txt += (f"반대로 {M.who}의 아내 별 재성({jae}, {EL_HAN[jae]})은 {F.who} 사주에 {', '.join(jae_f) or '거의 없어요'}{'로 넉넉하고' if jae_f else ''}, "
                    f"{F.who}의 배우자궁 {Fc.db}는 {M.who}에게 <b>{S.branch_ten_god(Mc.dm, Fc.db)}</b>이에요.")
        if S.branch_ten_god(Mc.dm, Fc.db) == "정재": rel_txt += " 남자에게 여자의 일지가 정재(정식 아내의 별)인 것은 전통적으로 결혼 궁합의 좋은 표식이에요."
        return f'''<section class="page tight"><div class="in">
 <h2><span class="no">03</span>배우자궁 · 띠 · 원진귀문 · 합충</h2>
 <div class="sub">두 사주의 글자가 서로 어떻게 만나는지</div>
 <ul class="small">{"".join(li)}</ul>
 <h3>{esc(F.who)}의 관성(남편 별) × {esc(M.who)}의 재성(아내 별)</h3>
 <p>{rel_txt}</p>
 <div class="box dark"><span class="gold">정리</span> · {self.attraction_text()} {self.palace_short().split('. ')[0]}.</div>
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def stem_text(self):
        s = []
        for b in self.stem_bits:
            if b[:2] in ("甲己", "己甲"): s.append("甲己합은 신뢰와 책임으로 묶이는 합")
            elif b[:2] in ("丁壬", "壬丁"): s.append("丁壬합은 정이 깊어지는 다정한 합이고, 합해서 나무(木)가 되어 두 사람 모두에게 반가운 기운이에요" if (self.F.c.yong == "목" or self.M.c.yong == "목") else "丁壬합은 정이 깊어지는 합")
            elif "충" in b: s.append(f"{b}은 의견이 정면으로 부딪히는 자리라, 결정 전에 한 템포 쉬기")
            elif "합" in b: s.append(f"{b}은 서로 끌리는 합")
        return " · ".join(s) + ("." if s else "")

    def p_life(self):
        F, M = self.F, self.M; Fc, Mc = F.c, M.c
        def style(P):
            c = P.c; g = c.gcount; t = []
            if g["식상"] >= 2: t.append("말이 빠르고 표현이 직설적(식상 강함)")
            if g["인성"] >= 2 or c.gyeok in ("정인격", "편인격"): t.append("생각을 정리한 뒤 말하는 신중형(인성)")
            if g["비겁"] >= 3: t.append("주관이 뚜렷하고 양보가 어려움(비겁 강함)")
            if g["재성"] >= 3: t.append("현실·돈·계획을 먼저 따짐(재성 강함)")
            if g["관성"] >= 2: t.append("원칙·체면을 중시(관성)")
            if "역마" in c.sinsal: t.append("밖으로 움직이며 푸는 활동형(역마)")
            if "화개" in c.sinsal: t.append("혼자만의 시간이 꼭 필요한 편(화개)")
            if c.r["ten_gods_count"].get("편재", 0) >= 1 and g["식상"] >= 2: t.append("사람·기회를 넓히는 사교형(식상+편재)")
            if g["재성"] >= 3 and "화개" in c.sinsal: t.append("걱정을 속에 쌓아 두는 편")
            if not c.strong: t.append("지치면 예민해지고 혼자 삭이는 편(신약)")
            return t or ["균형 잡힌 대화형"]
        sf, sm = style(F), style(M)
        fights = []
        if "식상" and Mc.gcount["식상"] >= 2: fights.append(f"{M.who}의 직설적인 한마디가 {F.who}에게는 상처로 남기 쉬워요. ‘말의 온도’를 한 단계 낮추기.")
        if Fc.gcount["식상"] >= 2: fights.append(f"{F.who}도 표현력이 좋아, 서운할 때 정확한 지적이 {M.who}의 자존심을 건드릴 수 있어요. ‘사실’보다 ‘마음’을 먼저 말하기.")
        if ("역마" in Mc.sinsal) != ("역마" in Fc.sinsal) or ("화개" in Fc.sinsal) != ("화개" in Mc.sinsal):
            out_p = M if "역마" in Mc.sinsal else F; in_p = F if out_p is M else M
            fights.append(f"쉬는 방식 차이: {out_p.who}는 나가서 움직이며 풀고, {in_p.who}는 조용히 혼자 쉬며 풀어요. 주말을 ‘함께 하루 + 각자 반나절’로 나누기.")
        if Fc.gcount["재성"] >= 3 and Mc.gcount["식상"] >= 2: fights.append(f"돈 문제: {F.who}는 모으고 지키려 하고, {M.who}는 쓰고 굴려서 키우려 해요. 생활비·저축·용돈을 처음부터 나누기.")
        if any("원진" in x or "귀문" in x for x in self.br_bits) or "원진" in rels(Fc.db, Mc.db):
            fights.append("서운함을 쌓아 두는 패턴(원진·귀문): 둘 다 피곤할 때 사소한 말투로 크게 번져요. ‘그날 일은 그날’ 규칙.")
        if Fc.dm_el == Mc.dm_el: fights.append("주도권 경쟁: 같은 오행 일간이라 서로 ‘내 방식이 맞다’고 느끼기 쉬워요. 분야별 담당 정하기.")
        if not Fc.strong and not Mc.strong: fights.append("둘 다 신약이라 함께 지치면 같이 가라앉아요. 바쁜 시기엔 일정·집안일을 줄이는 게 먼저예요.")
        # 재물
        def mgr(P):
            c = P.c; tc = c.r["ten_gods_count"]
            gos = sum(1 for p in c.P.values() if p["gz"][1] in "辰戌丑未" and any(STEM_ELK[h] == c.gel["재성"] for h in S.HIDDEN[p["gz"][1]]))
            return tc.get("정재", 0) * 1.5 + gos + 0.5 * c.gcount["인성"], c.gcount["식상"] + tc.get("편재", 0)
        mf, ef = mgr(F); mm, em = mgr(M)
        manager = F if mf >= mm else M; earner = F if ef > em else M
        money = (f"<b>돈 관리는 {manager.who}</b>가 맡는 게 자연스러워요(정재·재물 창고·인성 점수 {F.who} {mf:.1f} : {M.who} {mm:.1f}). "
                 f"<b>버는 감각·활동은 {earner.who}</b>가 더 강해요(식상·편재 {F.who} {ef} : {M.who} {em}). ")
        if manager is not earner: money += f"{earner.who}가 벌고 {manager.who}가 모으는 ‘역할 분담형’ 재물 궁합이라 합치면 시너지가 커요. "
        money += "둘 다 신약한 편이라 보증·무리한 대출·한 번에 큰 투자는 맞지 않고, 적금·청약·실거주 집처럼 쌓는 방식이 맞아요." if (not Fc.strong and not Mc.strong) else ""
        # 자녀
        kf = [n for n, p in Fc.P.items() if TG_GROUP[p["stem_tengod"] if n != "일" else "비견"] == "식상" or TG_GROUP[p["branch_tengod"]] == "식상"]
        kh_f = Fc.P.get("시"); kh_m = Mc.P.get("시")
        kid = f"여자의 자녀 별은 식상, 남자의 자녀 별은 관성이에요. {F.who}는 식상이 {Fc.gcount['식상']}개"
        if kh_f and Fc.time_known: kid += f"이고 자녀궁(시주) {kh_f['gz']}에 {kh_f['stem_tengod']}이 있어 자녀 인연이 좋아요"
        kid += f". {M.who}는 관성이 겉에 {Mc.gcount['관성']}개"
        if kh_m and Mc.time_known:
            hid = [h for h in kh_m["hidden"] if TG_GROUP[h["tengod"]] == "관성"]
            kid += f", 자녀궁 {kh_m['gz']} 속에 {'·'.join(h['stem'] + h['tengod'] for h in hid) or '관성 없음'}이 있어요"
        def kf_(y): g = E.year_gz(y); return TG_GROUP[Fc.tg(g[0])] == "식상" or TG_GROUP[Fc.tg(g[1], True)] == "식상"
        def km_(y): g = E.year_gz(y); return TG_GROUP[Mc.tg(g[0])] == "관성" or TG_GROUP[Mc.tg(g[1], True)] == "관성"
        kyears = [y for y in self.years if kf_(y) and km_(y)] or [y for y in self.years if kf_(y) or km_(y)][:4]
        fd = Fc.current_daeun(self.Y + 5)
        kid += f". 향후 10년 중 두 사람의 자녀 별이 {'함께 ' if all(kf_(y) and km_(y) for y in kyears) else ''}들어오는 해는 {', '.join(map(str, kyears[:5]))}년이에요."
        if fd and TG_GROUP[fd["천간십신"]] == "식상": kid += f" 특히 {F.who}의 {fd['gz']} 대운(만 {fd['a0']}세~)은 식상 대운이라 자녀운이 강해요."
        return f'''<section class="page tight"><div class="in">
 <h2><span class="no">04</span>성격 · 대화 방식 · 다투는 포인트</h2>
 <div class="sub">일간·십신 구조로 본 두 사람의 차이</div>
 <table><tr><th style="width:50%">{esc(F.who)}</th><th>{esc(M.who)}</th></tr>
 <tr><td class="small">{STEM[Fc.dm]['pers']}</td><td class="small">{STEM[Mc.dm]['pers']}</td></tr>
 <tr><td class="small">{' · '.join(sf)}</td><td class="small">{' · '.join(sm)}</td></tr></table>
 <h3>다투기 쉬운 포인트와 해법</h3>
 <ul class="small">{"".join(f"<li>{x}</li>" for x in fights[:5])}</ul>
 <div class="rule"></div>
 <h2><span class="no">05</span>재물 궁합 · 자녀운</h2>
 <div class="sub">누가 돈을 관리하면 좋을까</div>
 <p>{money}</p>
 <p class="small"><b>자녀운</b> · {kid}</p>
 <div class="box dark" style="margin-top:3mm"><span class="gold">두 사람이 잘 맞는 점</span><ul class="small" style="margin:1mm 0 0;color:#efe3c6">{"".join(f"<li>{x}</li>" for x in self.strengths(manager, earner))}</ul></div>
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def strengths(self, manager, earner):
        Fc, Mc = self.F.c, self.M.c; out = []
        if Fc.yong == Mc.yong: out.append(f"용신이 같은 {el_full(Fc.yong)}이라 좋아하는 환경·쉬는 방식·좋은 시기가 비슷해요.")
        if {Fc.dm, Mc.dm} == {"甲", "乙"}: out.append("큰 나무와 덩굴(등라계갑): 서로 기대며 함께 높이 오르는 동지형 부부예요.")
        if self.cheonji: out.append("천지합: 처음 끌림이 강하고, 인연이 쉽게 끊어지지 않는 표식이에요.")
        if S.branch_ten_god(Mc.dm, Fc.db) == "정재": out.append(f"{self.F.who}의 배우자궁이 {self.M.who}에게 정재(아내 별)예요.")
        if manager is not earner: out.append(f"{earner.who}가 벌고 {manager.who}가 모으는 역할 분담형 재물 궁합이에요.")
        return out[:5]

    def p_timing(self):
        F, M = self.F, self.M; Fc, Mc = F.c, M.c
        # 대운 비교
        rows = ""
        for y0 in range(self.Y - self.Y % 5, self.Y + 25, 5):
            df, dm = Fc.current_daeun(y0 + 1), Mc.current_daeun(y0 + 1)
            if not df or not dm: continue
            sf = F.rep.star(Fc.score(df["gz"])[0]); sm = M.rep.star(Mc.score(dm["gz"])[0])
            note = "둘 다 좋은 시기" if sf >= 4 and sm >= 4 else "둘 다 힘을 아끼는 시기" if sf <= 2 and sm <= 2 else "한쪽이 받쳐 주는 시기" if abs(sf - sm) >= 2 else "무난"
            rows += f'<tr{" class=hl" if note == "둘 다 좋은 시기" else ""}><td>{y0}~{y0 + 4}</td><td class="serif">{df["gz"]}</td><td class="small">{df["천간십신"]}/{df["지지십신"]}</td><td class="stars">{stars(sf)}</td><td class="serif">{dm["gz"]}</td><td class="small">{dm["천간십신"]}/{dm["지지십신"]}</td><td class="stars">{stars(sm)}</td><td class="small">{note}</td></tr>'
        best, sc = self.best_years()
        yrows = ""
        top3 = best[:3]
        for y in self.years:
            gz = E.year_gz(y)
            tag = f"<b>결혼 적기 {top3.index(y) + 1}순위</b>" if y in top3 else ""
            yrows += (f'<tr{" class=hl" if y in top3 else ""}><td>{y}</td><td class="serif">{gz}</td><td class="small">{self.love_reason(F, y)}</td><td class="stars">{stars(F.rep.ystar[y])}</td>'
                      f'<td class="small">{self.love_reason(M, y)}</td><td class="stars">{stars(M.rep.ystar[y])}</td><td class="small">{tag}</td></tr>')
        return f'''<section class="page tight"><div class="in">
 <h2><span class="no">06</span>대운 흐름 비교 · 결혼 적기</h2>
 <div class="sub">10년 단위 인생의 계절을 5년씩 겹쳐 보고, 해마다 두 사람의 인연운을 교차했어요</div>
 <table><tr><th style="width:12%">기간</th><th>{esc(F.who)} 대운</th><th>십신</th><th>운</th><th>{esc(M.who)} 대운</th><th>십신</th><th>운</th><th style="width:17%">함께 보면</th></tr>{rows}</table>
 <h3>해마다 인연운 교차 (향후 10년)</h3>
 <table><tr><th style="width:8%">연도</th><th style="width:8%">간지</th><th>{esc(F.who)} 인연 신호</th><th style="width:10%">운</th><th>{esc(M.who)} 인연 신호</th><th style="width:10%">운</th><th style="width:15%"></th></tr>{yrows}</table>
 <p class="small" style="margin-top:2mm">{self.timing_text(top3)}</p>
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''

    def timing_text(self, top3):
        F, M = self.F, self.M; b = top3[0]; gz = E.year_gz(b)
        s = f"<b>{b}년 {gz}</b>이 두 사람 모두에게 인연 신호가 겹치는 해예요({F.who}: {self.love_reason(F, b)} / {M.who}: {self.love_reason(M, b)}). "
        s += f"그다음은 {top3[1]}·{top3[2]}년이에요. "
        win = [y for y in self.years if F.rep.love[y] + M.rep.love[y] >= 2.8]
        runs = []; 
        for y in win:
            if runs and y == runs[-1][-1] + 1: runs[-1].append(y)
            else: runs.append([y])
        rr = max(runs, key=len) if runs else []
        if len(rr) >= 2: s += f"<b>{rr[0]}~{rr[-1]}년</b>은 두 사람의 인연 신호가 연달아 겹치는 ‘결혼의 창’이에요. "
        lowp = [P for P in (F, M) if P.rep.ystar[b] <= 2]
        for P in lowp: s += f"{P.who}는 {b}년 일·재물 운이 낮은 편이라, 결혼 자체는 좋되 큰 대출·투자는 피하고 예산을 넉넉히 잡으세요. "
        mm = [m for m in E.month_pillars(b, b) if m[0].year == b]
        good = sorted(mm, key=lambda m: -(F.c.score(m[2])[0] + M.c.score(m[2])[0]))[:2]
        s += "식 날짜는 그해 " + "·".join(f"{m[0].month}월({m[2]}, 절기 {m[0].month}/{m[0].day}~)" for m in sorted(good)) + "이 두 사람 모두 무난한 달이에요."
        return s

    def p_end(self):
        F, M = self.F, self.M; Fc, Mc = F.c, M.c
        caution = [x[2] for x in self.cautions()]
        Y, H = ELEM[Fc.yong], ELEM[Fc.hee]
        tips = [f"<li><b>함께 쓰는 색·방향</b>: {Y['colors']} · {H['colors'].split('·')[0]} / 신혼집·침대 머리는 {Y['dir']}·{H['dir']}</li>",
                f"<li><b>함께하는 활동</b>: {Y['life'].split(', ')[0]}, {H['life'].split(', ')[0]} — 둘 다 같은 용신이라 같이 할수록 둘 다 좋아져요</li>" if Fc.yong == Mc.yong else f"<li><b>서로의 용신</b>: {F.who}는 {Y['life'].split(', ')[0]}, {M.who}는 {ELEM[Mc.yong]['life'].split(', ')[0]}</li>",
                "<li><b>대화 규칙</b>: 서운한 건 그날 말하기 · 피곤한 밤 11시 이후엔 중요한 이야기 금지 · 말투보다 ‘무엇이 필요한지’를 말하기</li>",
                "<li><b>돈 규칙</b>: 공동 통장 + 각자 용돈 통장, 큰 지출은 하루 생각하고 합의</li>",
                f"<li><b>숫자</b>: {Y['nums']} · {H['nums']} (날짜·비밀번호·층수 고를 때 참고)</li>"]
        lim = [self.time_note_short, "궁합은 두 사람의 타고난 기운이 만나는 방식을 보는 것이지, 결혼의 성패를 정하지 않아요. 같은 궁합이라도 대화와 배려로 얼마든지 좋아져요.",
               "점수는 정해진 규칙에 따른 계산값이라 참고용이에요."]
        return f'''<section class="page"><div class="in">
 <h2><span class="no">07</span>주의할 해 · 사이가 좋아지는 개운법</h2>
 <div class="sub">겁줄 일이 아니라 미리 알고 준비하면 되는 일이에요</div>
 <h3>주의할 해</h3><ul class="small">{"".join(caution[:5]) or "<li>향후 10년 안에 두 사람이 함께 크게 흔들리는 해는 없어요.</li>"}</ul>
 <h3>사이가 좋아지는 개운법</h3><ul class="small">{"".join(tips)}</ul>
 <h3>마음가짐 한 가지</h3>
 <div class="box dark">{self.closing()}</div>
 <div class="rule"></div>
 <div class="tiny"><b>판독 참고와 한계</b> · {" ".join(lim)}<br><br>
 <b>안내</b> · 이 감정서는 전통 명리학(자평명리)의 궁합 이론에 따른 해석이에요. 과학적으로 검증된 예측이 아니며 오락과 자기 이해를 위한 참고 자료예요. 중요한 결정은 두 분의 대화와 전문가 상담을 우선하세요.</div>
</div><div class="foot">SONMYEONGRI · __PG__ · 손명리 결혼 궁합 감정서</div></section>'''

    def cautions(self):
        F, M = self.F, self.M
        caution = []
        for y in self.years:
            gz = E.year_gz(y); bits = []; w = 0
            for P in (F, M):
                for k, pos, det, el in P.c.relations_to_chart(*gz):
                    if k == "충" and pos in ("일", "월"):
                        bits.append(f"{P.who} {det}충({'배우자궁·생활' if pos == '일' else '직장·환경'})"); w += 2
                if P.rep.ystar[y] <= 2: bits.append(f"{P.who} 운 ★★"); w += 1
            if w >= 2:
                caution.append((w, y, f"<li><b>{y} {gz}</b>: {', '.join(dict.fromkeys(bits))}. 이사·큰 지출·양가 문제를 한꺼번에 몰지 말고, 힘든 쪽을 다른 한 사람이 받쳐 주세요.</li>"))
        return sorted(sorted(caution, key=lambda x: -x[0])[:4], key=lambda x: x[1])

    def closing(self):
        F, M = self.F, self.M
        if {F.c.dm, M.c.dm} == {"甲", "乙"}:
            return f"큰 나무와 덩굴은 함께일 때 가장 높이 올라가요. <b>서로를 이기려 하지 말고, 같은 방향을 보며 함께 자라세요.</b> 서운함은 쌓지 말고 그날 풀면, 두 분은 오래 갈수록 더 좋아지는 궁합이에요."
        return "<b>다름을 고치려 하지 말고, 역할을 나누고, 서운함은 그날 푸세요.</b> 궁합은 타고나는 것이 절반, 함께 만드는 것이 절반이에요."


CSS_EXTRA = """
.gp { margin:2mm 0 0 !important; gap:1.6mm !important; }
.gp .pl { width:15mm; } .gp .pl .ch { font-size:15pt !important; padding:0.8mm 0 !important; } .gp .pl .tg { font-size:6.6pt; } .gp .pl .lb { font-size:7pt; letter-spacing:.05em; }
.score { text-align:center; width:30mm; height:30mm; border-radius:50%; border:1pt solid #d4b46b; display:flex; flex-direction:column; align-items:center; justify-content:center; box-shadow:0 0 10pt rgba(227,192,112,.3); }
.score .num { font-family:"Noto Serif CJK KR",serif; font-size:28pt; color:#f0cd7d; line-height:1; } .score .of { font-size:8pt; color:#bda676; }
.mchart.sm .big { font-size:15pt; padding:1mm 0; } .mchart.sm td { padding:1mm 0.8mm; font-size:8.6pt; }
"""


def main():
    ap = argparse.ArgumentParser(description="손명리 결혼 궁합 감정서")
    for p in ("f", "m"):
        ap.add_argument(f"--{p}-name"); ap.add_argument(f"--{p}-date", required=True); ap.add_argument(f"--{p}-lunar", action="store_true")
        ap.add_argument(f"--{p}-leap", action="store_true"); ap.add_argument(f"--{p}-time"); ap.add_argument(f"--{p}-time2", help="시각 범위의 끝(범위로 받았을 때)")
        ap.add_argument(f"--{p}-place", default="서울"); ap.add_argument(f"--{p}-place-label")
    ap.add_argument("--out", required=True); ap.add_argument("--now"); ap.add_argument("--previews", action="store_true")
    ap.add_argument("--preview-prefix", help="미리보기 PNG 경로 접두어(기본 <out>_p)")
    a = ap.parse_args()
    t0 = time.time(); now = datetime.fromisoformat(a.now) if a.now else datetime.now()
    doc, css, G = assemble_gunghap(a, now)
    out = os.path.abspath(a.out); work = out[:-4] + "_build"; os.makedirs(work, exist_ok=True)
    open(os.path.join(work, "style.css"), "w").write(css)
    src = os.path.join(work, "report.html")
    open(src, "w").write(doc)
    ov = asyncio.run(render(src, out))
    if a.previews:
        subprocess.run(["pdftoppm", "-r", "96", "-png", out, a.preview_prefix or out[:-4] + "_p"], check=True)
    print(json.dumps({"pdf": out, "pages": len(ov), "heights": ov, "score": G.total, "grade": G.grade(),
                      "items": [(x[0], x[2], x[1]) for x in G.score_items], "best": G.best_years()[0][:3],
                      "both_good": G.both_good, "both_bad": G.both_bad, "sec": round(time.time() - t0, 2)}, ensure_ascii=False))


def assemble_gunghap(a, now):
    """a: --f-*/--m-* 와 같은 이름의 속성(f_name, f_date, ...)을 가진 객체 → (html, css, Gunghap)"""
    notes = []; short = []
    people = {}
    for p, g, lab in (("f", "F", "여성 고객님"), ("m", "M", "남성 고객님")):
        g_ = lambda k: getattr(a, f"{p}_{k}")
        P = Person(lab, g_("name"), g, g_("date"), g_("lunar"), g_("leap"), g_("time"), g_("place"), g_("place_label"), now)
        people[p] = P
        tc = P.r["time_correction"]
        if g_("time"):
            hb = P.c.P["시"]["gz"]
            s = f"{P.who}: {g_('time')} → {P.place_label} 경도 보정 {tc['local_solar_time'][-5:]}({tc['correction_minutes']:+.1f}분), {hb[1]}시({hb})"
            if g_("time2"):
                P2 = Person(lab, g_("name"), g, g_("date"), g_("lunar"), g_("leap"), g_("time2"), g_("place"), g_("place_label"), now)
                hb2 = P2.c.P["시"]["gz"]; lt2 = P2.r["time_correction"]["local_solar_time"][-5:]
                if hb2 == hb:
                    s += f", {g_('time2')} → {lt2}도 같은 {hb2[1]}시({hb2}). <b>범위 전체가 같은 시주라 시주는 확실</b>해요"
                else:
                    s += f", 그러나 {g_('time2')} → {lt2}는 {hb2[1]}시({hb2})로 <b>시주가 달라져요</b>. 이 감정서는 앞 시각 기준이며, 범위 중간이 어느 쪽인지로 더 가능성 높은 시주를 판단하세요"
                short.append(f"{P.who}의 출생 시각은 범위로 받았지만 시주가 {'같아 영향이 없어요' if hb2 == hb else '달라질 수 있어요'}.")
            notes.append(s + ".")
        else:
            notes.append(f"{P.who}: 출생 시각 미상 → 시주 없이 판단."); short.append(f"{P.who}의 출생 시각을 몰라 시주 없이 봤어요.")
        if g_("lunar"): notes.append(f"{P.who} 음력 {g_('date')} = 양력 {P.r['solar_date']}(KASI 기준).")
    G = Gunghap(people["f"], people["m"], now, " ".join(notes))
    G.time_note_short = " ".join(short) + " 대운 교체 시점과 연도 별점은 계산상 근사치예요."
    pages = [G.p_cover(), G.p_charts(), G.p_score(), G.p_palace(), G.p_life(), G.p_timing(), G.p_end()]
    html = "\n".join(pages); n = 0
    def pg(m):
        nonlocal n; n += 1; return str(n)
    html = re.sub("__PG__", pg, html)
    for bad in ("\ubc31\uc6b4", "\ub3c4\uc0ac", "\ucca0\ud559\uc6d0", "\ube14\ub85c\uadf8"): assert bad not in html, bad
    css = open(os.path.join(HERE, "assets", "style.css")).read() + CSS_EXTRA
    doc = f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>손명리 결혼 궁합 감정서</title><link rel="stylesheet" href="style.css"></head><body>\n{html}\n</body></html>'
    return doc, css, G


if __name__ == "__main__":
    main()
