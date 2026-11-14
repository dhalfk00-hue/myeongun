# -*- coding: utf-8 -*-
"""손명리 감정서 분석 엔진: saju.py 결과 → 용신·격국·점수·월운·인연 시기 (규칙 기반, LLM 없음)."""
import sys, argparse
from functools import lru_cache
from datetime import datetime, timedelta, date
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import saju as S
from lunar_python import Solar
from texts import TG_GROUP as _TGG
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

    # 신강·신약: 위치 가중 + 지장간(통근) + 투간·뿌리 보정 (fix1113)
    # 천간: 지지에 같은 오행 뿌리가 있으면 ×1.25, 뿌리 없이 떠 있으면 ×0.75
    # 지지: 지장간 비율로 나눠 세고, 지장간이 천간에 투출(透干)했으면 그 몫 ×1.3
    # 돕는 쪽(비겁·인성)은 2그룹, 빼는 쪽(식상·재성·관성)은 3그룹이라 그대로 세면 평균 사주가 신약으로 쏠려요.
    # 돕는 쪽 ×1.25 보정으로 무작위 분포가 신약·중화·신강 약 39·23·38%가 되게 맞췄어요(tests/regress.py).
    SUP_K = 1.25
    MONTH_ADJ = {"비겁": 0.04, "인성": 0.02, "식상": -0.02, "재성": -0.03, "관성": -0.04}
    BR_POS_W = {"년": 1.0, "월": 3.0, "일": 1.5, "시": 1.2}
    ST_T1, ST_MID, ST_T2 = 0.40, 0.45, 0.50

    def _strength(self):
        st = self.r["strength"]
        self.ratio_old = st["support_ratio"]
        self.deukryeong = st["득령(월지)"]
        self.deukji = st["득지(일지)"]
        sup_el = (self.gel["비겁"], self.gel["인성"])
        vis = {n: p["gz"][0] for n, p in self.P.items()}
        vis_el = {STEM_ELK[v] for n, v in vis.items() if n != "일"}
        root_el = {STEM_ELK[h] for p in self.P.values() for h in S.HIDDEN[p["gz"][1]]}
        sup = tot = 0.0
        self.roots = []      # 일간을 돕는 지장간(통근) 위치
        self.tougan = []     # 돕는 기운이 천간에 뜬 위치
        for n, p in self.P.items():
            if n != "일":
                e = STEM_ELK[p["gz"][0]]
                w = 1.0 * (1.25 if e in root_el else 0.75)
                tot += w
                if e in sup_el:
                    sup += w
                    if e in root_el: self.tougan.append(n)
            bw = self.BR_POS_W.get(n, 1.0)
            for h, hw in branch_hidden_w(p["gz"][1]):
                e = STEM_ELK[h]
                w = bw * hw * (1.3 if e in vis_el else 1.0)
                tot += w
                if e in sup_el:
                    sup += w
                    if n not in self.roots: self.roots.append(n)
        dr = tot - sup
        r0 = sup * self.SUP_K / (sup * self.SUP_K + dr) if tot else 0
        # 월령(득령) 보정: 월지 정기가 일간에게 왕(비겁)·상(인성)·휴(식상)·수(재성)·사(관성)
        mg = TG_GROUP[S.branch_ten_god(self.dm, self.mb)]
        self.month_state = {"비겁": "왕", "인성": "상", "식상": "휴", "재성": "수", "관성": "사"}[mg]
        r0 += self.MONTH_ADJ[mg]
        self.ratio = round(max(0.0, min(1.0, r0)), 2)
        if self.ratio < self.ST_T1:
            self.strong = False; self.st_label = "신약(身弱)"
        elif self.ratio > self.ST_T2:
            self.strong = True; self.st_label = "신강(身强)"
        else:
            self.strong = self.ratio >= self.ST_MID if abs(self.ratio - self.ST_MID) > 0.01 else self.deukryeong
            self.st_label = "중화, 약간 신강" if self.strong else "중화, 약간 신약"
        self.neutral = self.ST_T1 <= self.ratio <= self.ST_T2

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
        top0 = max(drain, key=drain.get)
        # 중화인데 관성(살)이 가장 무거우면 인성으로 살을 풀어 쓰는 살인상생(殺印相生)으로 봐요 (fix1113)
        self.salin = bool(self.strong and getattr(self, "neutral", False) and top0 == "관성")
        self.weak_path = (not self.strong) or self.salin
        if not self.weak_path:
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

    # 절대 기준 별점 (fix1113: ★1 허용, 하한 없음).
    # 무작위 300명 대운·세운 점수 분포(평균≈0)의 10·30·70·90% 지점 → ★1~★5 ≈ 10·20·40·20·10%
    STAR_CUTS = (3.3, 1.5, -1.3, -3.2)

    @staticmethod
    def stars(sc):
        a, b, c_, d = Chart.STAR_CUTS
        return 5 if sc >= a else 4 if sc >= b else 3 if sc >= c_ else 2 if sc >= d else 1

    @staticmethod
    def tone(sc):
        """점수 3단계: good(★4 이상, ≥1.5) / mid(★3) / bad(★2 이하, <-1.3)"""
        return "good" if sc >= Chart.STAR_CUTS[1] else "bad" if sc < Chart.STAR_CUTS[2] else "mid"

    def daeun_score(self, p):
        return self.score(p["gz"])[0]

    def age_band_score(self, a0, a1):
        """만 a0~a1세 구간을 덮는 대운 점수의 나이 가중 평균 (없으면 None)"""
        tot = n = 0
        for p in self.daeun_periods():
            lo, hi = max(a0, p["a0"]), min(a1, p["a1"])
            if hi >= lo:
                k = hi - lo + 1; tot += k * self.daeun_score(p); n += k
        return round(tot / n, 2) if n else None

    def fifties_ok(self):
        sc = self.age_band_score(50, 59)
        return sc is not None and sc >= 0

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


@lru_cache(maxsize=256)
def _jie_list(y0, y1):
    seen = {}
    for y in range(y0 - 1, y1 + 2):
        t = Solar.fromYmd(y, 6, 1).getLunar().getJieQiTable()
        for k, v in t.items():
            nm = _ALIAS.get(k, k)
            if nm in _JIE:
                dt = datetime(v.getYear(), v.getMonth(), v.getDay(), v.getHour(), v.getMinute()) + timedelta(hours=1)
                seen[dt.strftime("%Y%m%d")] = (dt, nm)
    return tuple(sorted(seen.values()))


def jie_list(y0, y1):
    """q1113: 계산 결과를 캐시해요(같은 해를 여러 번 물어도 한 번만 계산)."""
    return list(_jie_list(y0, y1))


@lru_cache(maxsize=64)
def _month_pillars(y0, y1):
    js = jie_list(y0, y1)
    out = []
    for (a, n), (b, _) in zip(js, js[1:]):
        s = a + timedelta(hours=2)
        gz = Solar.fromYmdHms(s.year, s.month, s.day, s.hour, s.minute, 0).getLunar().getMonthInGanZhiExact()
        out.append((a, b, gz, n))
    return tuple(out)


def month_pillars(y0, y1):
    """[(start_kst, end_kst, gz, jie_name)] covering y0-01 .. y1+1-02"""
    return list(_month_pillars(y0, y1))


@lru_cache(maxsize=512)
def year_gz(y):
    return Solar.fromYmd(y, 6, 1).getLunar().getYearInGanZhiExact()


@lru_cache(maxsize=256)
def lichun(y):
    for dt, n in jie_list(y, y):
        if n == "立春" and dt.year == y:
            return dt
