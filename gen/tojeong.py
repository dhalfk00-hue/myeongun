#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""newyear1116: 토정비결 작괘 + 144괘 현대어 풀이.
계산법: 한국민족문화대백과사전(토정비결) — 상괘=(세는 나이+당년 태세수)%8, 중괘=(당년 음력 생월 날수+월건수)%6,
하괘=(음력 생일+당년 그날 일진수)%3, 나머지 0이면 제수. 생시는 쓰지 않아요.
태세수=중천(간)+중천(지), 월건수=선천(간)+선천(지), 일진수=선천(간)+중천(지).
음력: 한국천문연구원 기준(korean_lunar_calendar). 윤달생은 평달로, 30일생이 그해 작은달이면 29일로 계산해요(구현 관례).
풀이 문장: 조선 시대 한문 원문(저작권 만료)의 뜻만 참고해 새로 썼어요(tojeong_data/gwae_ko.json)."""
import json, os, sys
from datetime import date
from korean_lunar_calendar import KoreanLunarCalendar

G = "甲乙丙丁戊己庚辛壬癸"; Z = "子丑寅卯辰巳午未申酉戌亥"
SUN = dict(zip("甲己乙庚丙辛丁壬戊癸", [9, 9, 8, 8, 7, 7, 6, 6, 5, 5])) | dict(zip("子午丑未寅申卯酉辰戌巳亥", [9, 9, 8, 8, 7, 7, 6, 6, 5, 5, 4, 4]))
JUNG = dict(zip("甲己乙庚丙辛丁壬戊癸", [11, 11, 10, 10, 9, 9, 8, 8, 7, 7])) | dict(zip("辰戌丑未申酉亥子寅卯巳午", [11, 11, 11, 11, 10, 10, 9, 9, 8, 8, 7, 7]))
SOURCE = "계산법: 한국민족문화대백과사전 「토정비결」 · 음력: 한국천문연구원 기준"
NOTE = "토정비결은 생년월일 숫자로 한 해를 보는 전통 세시 풍속이에요. 이 감정서의 판단은 사주 별점이 정하고, 토정비결은 전통 참고로 함께 적었어요."
UPPER = {1: "건(乾)", 2: "태(兌)", 3: "이(離)", 4: "진(震)", 5: "손(巽)", 6: "감(坎)", 7: "간(艮)", 8: "곤(坤)"}


def m0(v, n): return v % n or n
def year_gz(y): i = (y - 4) % 60; return G[i % 10] + Z[i % 12]


def month_gz(y, m):
    s = G.index(year_gz(y)[0]); st = ((s % 5) * 2 + 2 + m - 1) % 10
    return G[st] + Z[(m + 1) % 12]


def day_gz(d):  # 1900-01-01 = 甲戌
    i = (10 + (d - date(1900, 1, 1)).days) % 60; return G[i % 10] + Z[i % 12]


def l2s(y, m, d, leap=False):
    c = KoreanLunarCalendar()
    return date.fromisoformat(c.SolarIsoFormat()) if c.setLunarDate(y, m, d, leap) else None


def month_days(y, m): return 30 if l2s(y, m, 30) else 29


def to_lunar(sd):
    c = KoreanLunarCalendar(); c.setSolarDate(sd.year, sd.month, sd.day)
    s = c.LunarIsoFormat(); y, m, d = map(int, s[:10].split("-")); return y, m, d, "Intercalation" in s


def gwae(ly, lm, ld, target):
    """음력 생년월일(윤달 여부는 무시) + 대상 연도 → 괘"""
    age = target - ly + 1
    tz = year_gz(target); ts = JUNG[tz[0]] + JUNG[tz[1]]
    md = month_days(target, lm); mz = month_gz(target, lm); ws = SUN[mz[0]] + SUN[mz[1]]
    dd = min(ld, md); dz = day_gz(l2s(target, lm, dd)); ds = SUN[dz[0]] + JUNG[dz[1]]
    a, b, c = m0(age + ts, 8), m0(md + ws, 6), m0(dd + ds, 3)
    return dict(code=f"{a}{b}{c}", sang=a, jung=b, ha=c, age=age, taese=tz, ts=ts, md=md, wolgeon=mz, ws=ws, iljin=dz, ds=ds, day=dd, clamped=ld > md)


def from_birth(date_str, lunar=False, leap=False, target=None):
    y, m, d = map(int, date_str.split("-"))
    if lunar: ly, lm, ld, lp = y, m, d, bool(leap)
    else: ly, lm, ld, lp = to_lunar(date(y, m, d))
    r = gwae(ly, lm, ld, target); r.update(lunar_birth=f"{ly}-{lm:02d}-{ld:02d}", leap_birth=lp); return r


_TX = None
def texts():
    global _TX
    if _TX is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tojeong_data", "gwae_ko.json")
        _TX = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    return _TX


def reading(date_str, lunar=False, leap=False, target=None):
    """괘 + 풀이(없으면 ready=False). months: [{'m':1,'tone':'g|n|b','text':..}] — 음력 달"""
    r = from_birth(date_str, lunar, leap, target)
    t = texts().get(r["code"])
    r["ready"] = bool(t)
    if t: r.update(title=t["title"], han=t.get("han", ""), flow=t["flow"], chongun=t["chongun"], months=t["months"])
    r["basis"] = f"세는 나이 {r['age']} + {target}년 태세수 {r['ts']} → 상괘 {r['sang']} · 음력 {int(r['lunar_birth'][5:7])}월 날수 {r['md']} + 월건수 {r['ws']} → 중괘 {r['jung']} · 음력 {r['day']}일 + 일진수 {r['ds']} → 하괘 {r['ha']}"
    return r


if __name__ == "__main__":
    a = sys.argv[1:]
    print(json.dumps(reading(a[0], "--lunar" in a, "--leap" in a, int(a[1])), ensure_ascii=False, indent=1))
