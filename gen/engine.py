# -*- coding: utf-8 -*-
"""명운 감정서 분석 엔진: saju.py 결과 → 용신·격국·점수·월운·인연 시기 (규칙 기반, LLM 없음)."""
import sys, argparse
from datetime import datetime, timedelta, date
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import saju as S
from lunar_python import Solar
from texts import EL_KO, GEN, CTRL, GEN_BY, CTRL_BY, TG_GROUP, MONTH

STEM_ELK = {s: EL_KO[e] for s, e in zip(S.STEMS, S.STEM_EL)}
BR_ELK = {b: EL_KO[e] for b, e in zip(S.BRANCHES, S.BRANCH_EL)}
GROUPS = ["비겁", "식상", "재성", "관성", "인성"]
POS_CHUNG = {"일": 1.0, "월": 0.7, "년": 0.3, "시": 0.5}


def run_saju(date_s, time_s, lunar, leap, gender, place, y_from, y_to):
    ns = argparse.Namespace(date=date_s, time=time_s, lunar=lunar, leap=leap, gender=gender, place=place,
                            tz=None, utc_offset=None, zi="unified", eot=False, seun_from=y_from, seun_to=y_to,
                            _nosc=False)
    return S.compute(ns)


def group_el(dm_el):
    return {"비겁": dm_el, "식상": GEN[dm_el], "재성": CTRL[dm_el], "관성": CTRL_BY[dm_el], "인성": GEN_BY[dm_el]}


def branch_hidden_w(b):
    h = S.HIDDEN[b]
    ws = [0.15, 0.25, 0.6] if len(h) == 3 else [0.3, 0.7]
    return list(zip(h, ws))


class Chart:
    def __init__(self, r, gender, now=None):
        self.r = r
        self.gender = gender  # 'F'/'M'
        self.now = now or datetime.now()
        self.P = {p["name"]: p for p in r["pillars"]}
        self.time_known = r["time_known"] and "시" in self.P
        self.dm = r["day_master"]["stem"]
        self.dm_el = STEM_ELK[self.dm]
        self.gel = group_el(self.dm_el)
        self.el_group = {v: k for k, v in self.gel.items()}
        self.wt = {EL_KO[k]: v for k, v in r["five_elements_weighted_with_hidden"].items()}
        self.cnt = {EL_KO[k]: v for k, v in r["five_elements_count"].items()}
        self.mb = self.P["월"]["gz"][1]
        self.db = self.P["일"]["gz"][1]
        self.season = MONTH[self.mb][1]
        self.solar = date.fromisoformat(r["solar_date"])
        self._groups()
        self._strength()
        self._yongsin()
        self._gyeok()
        self._sinsal()

    # ---------------------------------------------------------- 십신 그룹
    def _groups(self):
        g = {k: [] for k in GROUPS}
        for n, p in self.P.items():
            if n != "일":
                g[TG_GROUP[p["stem_tengod"]]].append(p["gz"][0])
            g[TG_GROUP[p["branch_tengod"]]].append(p["gz"][1])
        self.groups = g
        self.gcount = {k: len(v) for k, v in g.items()}
        hid = {k: [] for k in GROUPS}
        for n, p in self.P.items():
            for h in p["hidden"]:
                hid[TG_GROUP[h["tengod"]]].append(h["stem"])
        self.hidden_groups = hid
        self.gw = {k: self.wt[self.gel[k]] for k in GROUPS}

    def _strength(self):
        st = self.r["strength"]
        self.ratio = st["support_ratio"]
        self.deukryeong = st["득령(월지)"]
        self.deukji = st["득지(일지)"]
        if self.ratio < 0.45:
            self.strong = False; self.st_label = "신약(身弱)"
        elif self.ratio > 0.55:
            self.strong = True; self.st_label = "신강(身强)"
        else:
            self.strong = self.deukryeong
            self.st_label = "중화, 약간 신강" if self.strong else "중화, 약간 신약"

    # ---------------------------------------------------------- 용신
    def _yongsin(self):
        w = self.wt; G = self.gel; method = []
        win, sum_ = self.season == "winter", self.season == "summer"
        yong = hee = gi = None
        if win and w["화"] < 1.0:
            yong = "화"; method.append("조후")
        elif sum_ and w["수"] < 1.0:
            yong = "수"; method.append("조후")
        drain = {k: w[G[k]] * (0.5 if (win and G[k] == "화") or (sum_ and G[k] == "수") else 1.0)
                 for k in ("식상", "재성", "관성")}
        self.drain = drain
        if self.strong:
            if yong is None:
                method.append("억부")
                yong = G["식상"] if w[G["비겁"]] >= w[G["인성"]] else G["재성"]
            hee = GEN[yong] if GEN[yong] not in (G["비겁"], G["인성"]) else GEN_BY[yong]
            gi = CTRL_BY[yong]
            if gi in (hee,): gi = G["인성"]
        else:
            top = max(drain, key=drain.get)
            if yong is None:
                method.append("억부")
                yong = G["비겁"] if top == "재성" else G["인성"]
                hee = GEN_BY[yong] if GEN_BY[yong] in (G["비겁"], G["인성"]) else G["비겁"]
            else:
                hee = GEN_BY[yong]
            order = sorted(drain, key=drain.get, reverse=True)
            gi = next(G[k] for k in order if G[k] not in (yong, hee))
        gu = GEN_BY[gi]
        if gu in (yong, hee): gu = None
        self.yong, self.hee, self.gi, self.gu = yong, hee, gi, gu
        self.method = method
        fav = {e: 0 for e in GEN}
        fav[yong] = 2; fav[hee] = 1; fav[gi] = -2
        if gu: fav[gu] = -1
        if win: fav["화"] = min(2, fav["화"] + 1)
        if sum_: fav["수"] = min(2, fav["수"] + 1)
        self.fav = fav

    # ---------------------------------------------------------- 격국
    def _gyeok(self):
        mtg = S.branch_ten_god(self.dm, self.mb)
        if mtg in ("비견", "겁재"):
            self.gyeok = "양인격" if (mtg == "겁재" or self.mb == S.YANGIN.get(self.dm)) and S.stem_yang(self.dm) else "건록격"
            self.gyeok_src = self.mb
            return
        stems_vis = [self.P[n]["gz"][0] for n in self.P if n != "일"]
        hid = S.HIDDEN[self.mb][::-1]  # 정기 → 중기 → 여기
        pick = None
        for h in hid:
            if h in stems_vis and S.ten_god(self.dm, h) not in ("비견", "겁재"):
                pick = h; break
        if pick is None:
            pick = hid[0]
        from texts import TG_TO_GYEOK
        tg = S.ten_god(self.dm, pick)
        self.gyeok = TG_TO_GYEOK.get(tg, "건록격")
        self.gyeok_src = pick
        self.gyeok_transparent = pick in stems_vis

    # ---------------------------------------------------------- 신살 정리
    def _sinsal(self):
        out = []  # (name, pillar, gz)
        for s in self.r["sinsal"]:
            for t in s["sinsal"]:
                base = t.split("[")[0].split("(")[0]
                if base in ("천을귀인", "문창귀인", "홍염살", "백호살", "괴강살"):
                    out.append((base, s["pillar"], s["gz"]))
                elif base == "양인":
                    out.append(("양인", s["pillar"], s["gz"]))
                elif base == "연살":
                    out.append(("도화", s["pillar"], s["gz"]))
                elif base == "역마살":
                    out.append(("역마", s["pillar"], s["gz"]))
                elif base == "화개살":
                    out.append(("화개", s["pillar"], s["gz"]))
        rok = {"甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳", "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子"}[self.dm]
        for n, p in self.P.items():
            if p["gz"][1] == rok:
                out.append(("건록", n, p["gz"]))
        seen = {}
        for name, pil, gz in out:
            seen.setdefault(name, [])
            if pil not in [x[0] for x in seen[name]]:
                seen[name].append((pil, gz))
        self.sinsal = seen
        self.gongmang = self.r["gongmang"]["일주공망"]

    # ---------------------------------------------------------- 점수
    def branch_fav(self, b):
        return sum(self.fav[STEM_ELK[h]] * wv for h, wv in branch_hidden_w(b))

    def relations_to_chart(self, stem, br):
        """세운/월운 간지 ↔ 원국 관계 목록: (kind, pos, detail, result_el)"""
        rels = []
        for n, p in self.P.items():
            cs, cb = p["gz"]
            for t in S.pair_relations(stem, cs, stems=True):
                kind = "천간합" if t.startswith("천간합") else "천간충"
                el = t[t.find("(") + 1:t.find(")")] if "(" in t else None
                rels.append((kind, n, stem + cs, el))
            for t in S.pair_relations(br, cb):
                if t.startswith("육합"):
                    rels.append(("육합", n, br + cb, t[3]))
                elif t.startswith("삼합 반합"):
                    rels.append(("반합", n, br + cb, t[t.find("(") + 1]))
                elif t.startswith("삼합 가합"):
                    rels.append(("가합", n, br + cb, t.split(",")[1]))
                elif t == "충":
                    rels.append(("충", n, br + cb, None))
                elif "형" in t and "자형" not in t:
                    rels.append(("형", n, br + cb, None))
                elif t in ("원진", "해", "파"):
                    rels.append((t, n, br + cb, None))
        return rels

    def score(self, gz):
        s, b = gz[0], gz[1]
        sc = self.fav[STEM_ELK[s]] + 1.5 * self.branch_fav(b)
        rels = self.relations_to_chart(s, b)
        hap_done = set()
        for kind, pos, det, el in rels:
            if kind == "충":
                cb = self.P[pos]["gz"][1]
                pen = -POS_CHUNG[pos]
                if BR_ELK[cb] == self.yong: pen -= 0.5
                if BR_ELK[cb] == self.gi: pen += 0.3
                sc += pen
            elif kind in ("육합", "반합") and el in GEN and (kind, el) not in hap_done:
                hap_done.add((kind, el)); sc += 0.4 * self.fav[el] + 0.1
            elif kind == "천간합" and pos == "일":
                sc += 0.8
            elif kind == "천간충" and pos == "일":
                sc -= 0.7
            elif kind == "천간충":
                sc -= 0.15
            elif kind == "형":
                sc -= 0.35
            elif kind in ("원진", "해", "파"):
                sc -= 0.1
        if b in S.CHEONEUL[self.dm]:
            sc += 0.5
        return round(sc, 2), rels

    @staticmethod
    def stars(sc):
        n = 5 if sc >= 2.3 else 4 if sc >= 0.9 else 3 if sc >= -0.6 else 2
        return n

    def tg(self, ch, is_branch=False):
        return S.branch_ten_god(self.dm, ch) if is_branch else S.ten_god(self.dm, ch)

    # ---------------------------------------------------------- 인연 점수
    def love_score(self, gz):
        s, b = gz
        spouse = self.gel["관성"] if self.gender == "F" else self.gel["재성"]
        v = 0
        if STEM_ELK[s] == spouse: v += 1
        if BR_ELK[b] == spouse: v += 1.5
        if frozenset(s + self.dm) in S.STEM_HAP: v += 1.5
        rel = S.pair_relations(b, self.db)
        if any(t.startswith("육합") or t.startswith("삼합 반합") for t in rel): v += 1
        if "충" in rel: v -= 0.5
        yb = self.P["년"]["gz"][1]
        if S.sinsal12(yb, b).startswith("연살") or S.sinsal12(self.db, b).startswith("연살"): v += 0.5
        if b in self.gongmang and BR_ELK[b] == spouse: v += 0.3
        return v

    def age(self, year):
        return year - self.solar.year

    # ---------------------------------------------------------- 대운
    def daeun_periods(self):
        es = self.r["daeun_info"].get("exact_start_date")
        start = date.fromisoformat(es) if es else date(self.solar.year + self.r["daeun"][0]["시작나이(만)"], 1, 1)
        out = []
        for i, d in enumerate(self.r["daeun"]):
            y0 = start.year + 10 * i
            out.append(dict(d, y0=y0, y1=y0 + 10, a0=d["시작나이(만)"], a1=d["시작나이(만)"] + 9, month=start.month))
        return out

    def current_daeun(self, year):
        ps = self.daeun_periods()
        cur = None
        for p in ps:
            if p["y0"] <= year:
                cur = p
        return cur


# ---------------------------------------------------------- 절기·월건
_JIE = ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑", "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]
_ALIAS = {"LI_CHUN": "立春", "XIAO_HAN": "小寒", "DA_XUE": "大雪"}


def jie_list(y0, y1):
    seen = {}
    for y in range(y0 - 1, y1 + 2):
        t = Solar.fromYmd(y, 6, 1).getLunar().getJieQiTable()
        for k, v in t.items():
            nm = _ALIAS.get(k, k)
            if nm in _JIE:
                dt = datetime(v.getYear(), v.getMonth(), v.getDay(), v.getHour(), v.getMinute()) + timedelta(hours=1)
                seen[dt.strftime("%Y%m%d")] = (dt, nm)
    return sorted(seen.values())


def month_pillars(y0, y1):
    """[(start_kst, end_kst, gz, jie_name)] covering y0-01 .. y1+1-02"""
    js = jie_list(y0, y1)
    out = []
    for (a, n), (b, _) in zip(js, js[1:]):
        s = a + timedelta(hours=2)
        gz = Solar.fromYmdHms(s.year, s.month, s.day, s.hour, s.minute, 0).getLunar().getMonthInGanZhiExact()
        out.append((a, b, gz, n))
    return out


def year_gz(y):
    return Solar.fromYmd(y, 6, 1).getLunar().getYearInGanZhiExact()


def lichun(y):
    for dt, n in jie_list(y, y):
        if n == "立春" and dt.year == y:
            return dt
