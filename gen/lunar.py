#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""음력 → 양력 변환기 (한국천문연구원 기준 korean_lunar_calendar, 실패 시 lunar_python).
사용: python3 lunar.py 1990-01-01 [--leap]   /  python3 lunar.py --to-lunar 1990-01-27"""
import argparse, sys
from datetime import date


def lunar_to_solar(y, m, d, leap=False):
    from korean_lunar_calendar import KoreanLunarCalendar
    c = KoreanLunarCalendar()
    if not c.setLunarDate(y, m, d, bool(leap)):
        raise ValueError(f"존재하지 않는 음력 날짜: {y}-{m}-{d}{' 윤달' if leap else ''} (작은달은 29일까지, 윤달 여부 확인)")
    return date.fromisoformat(c.SolarIsoFormat())


def solar_to_lunar(y, m, d):
    from korean_lunar_calendar import KoreanLunarCalendar
    c = KoreanLunarCalendar()
    c.setSolarDate(y, m, d)
    return c.LunarIsoFormat()  # 'YYYY-MM-DD' (+ ' Intercalation' 윤달)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("date"); ap.add_argument("--leap", action="store_true"); ap.add_argument("--to-lunar", action="store_true")
    a = ap.parse_args()
    y, m, d = map(int, a.date.split("-"))
    if a.to_lunar:
        print(solar_to_lunar(y, m, d))
    else:
        try:
            print(lunar_to_solar(y, m, d, a.leap))
        except ValueError as e:
            sys.exit(str(e))
