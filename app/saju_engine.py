#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사주팔자 만세력 계산기 (Korean Four Pillars calculator)

- 년주: 입춘 정확 시각 기준 / 월주: 12절(節) 정확 시각 기준 (lunar_python 寿星 알고리즘, KASI 발표 절기와 분 단위 일치)
- 일주/시주: 출생지 경도 기준 지방평균태양시(LMT) (선택: --eot 로 균시차까지 적용한 진태양시)
- 한국 표준시 이력(1908 UTC+8:30, 1912 UTC+9, 1954-03-21~1961-08-09 UTC+8:30)과
  서머타임(1948-51, 1955-60, 1987-88)은 IANA tzdata Asia/Seoul 로 자동 반영
- 음력 입력은 한국천문연구원(KASI) 기준 korean_lunar_calendar 로 변환 (실패 시 lunar_python 중국 음력)

전통 명리 계산 도구이며, 해석은 전통 해석일 뿐 과학적 예측이 아님.
"""
import argparse, json, math, sys
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

from lunar_python import Solar

STEMS = "甲乙丙丁戊己庚辛壬癸"
STEMS_KO = "갑을병정무기경신임계"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
BRANCHES_KO = "자축인묘진사오미신유술해"
ANIMALS = "쥐 소 호랑이 토끼 용 뱀 말 양 원숭이 닭 개 돼지".split()
EL_KO = {"木": "목", "火": "화", "土": "토", "金": "금", "水": "수"}
ELEMENTS = ["木", "火", "土", "金", "水"]
STEM_EL = ["木", "木", "火", "火", "土", "土", "金", "金", "水", "水"]
BRANCH_EL = ["水", "土", "木", "木", "土", "火", "火", "土", "金", "金", "土", "水"]
# 지지 음양: 체(體) 기준 子양 丑음 寅양 卯음 ...
BRANCH_YANG = [True, False, True, False, True, False, True, False, True, False, True, False]

# 지장간 (여기, 중기, 정기) - 한국 통용표
HIDDEN = {
    "子": ["壬", "癸"], "丑": ["癸", "辛", "己"], "寅": ["戊", "丙", "甲"], "卯": ["甲", "乙"],
    "辰": ["乙", "癸", "戊"], "巳": ["戊", "庚", "丙"], "午": ["丙", "己", "丁"], "未": ["丁", "乙", "己"],
    "申": ["戊", "壬", "庚"], "酉": ["庚", "辛"], "戌": ["辛", "丁", "戊"], "亥": ["戊", "甲", "壬"],
}

PLACES = {  # 경도(동경)
    "서울": 126.98, "부산": 129.08, "대구": 128.60, "인천": 126.70, "광주": 126.85, "대전": 127.38,
    "울산": 129.31, "세종": 127.29, "수원": 127.03, "성남": 127.13, "고양": 126.83, "용인": 127.18,
    "춘천": 127.73, "원주": 127.95, "강릉": 128.90, "청주": 127.49, "충주": 127.93, "천안": 127.15,
    "전주": 127.15, "군산": 126.71, "목포": 126.39, "여수": 127.66, "순천": 127.49, "안동": 128.73,
    "포항": 129.37, "경주": 129.22, "구미": 128.34, "창원": 128.68, "마산": 128.57, "진주": 128.11,
    "김해": 128.89, "제주": 126.53, "서귀포": 126.56, "평양": 125.75, "개성": 126.55,
    "도쿄": 139.69, "베이징": 116.40, "상하이": 121.47, "뉴욕": -74.01, "LA": -118.24,
}

TEN_GODS = {  # (same element / generated-by etc., same polarity?) -> name
    ("same", True): "비견", ("same", False): "겁재",
    ("output", True): "식신", ("output", False): "상관",
    ("wealth", True): "편재", ("wealth", False): "정재",
    ("officer", True): "편관", ("officer", False): "정관",
    ("resource", True): "편인", ("resource", False): "정인",
}
TEN_GODS_HANJA = {"비견": "比肩", "겁재": "劫財", "식신": "食神", "상관": "傷官", "편재": "偏財",
                  "정재": "正財", "편관": "偏官(七殺)", "정관": "正官", "편인": "偏印", "정인": "正印"}

STAGES = "장생 목욕 관대 건록 제왕 쇠 병 사 묘 절 태 양".split()
STAGE_START = {"甲": "亥", "丙": "寅", "戊": "寅", "庚": "巳", "壬": "申",
               "乙": "午", "丁": "酉", "己": "酉", "辛": "子", "癸": "卯"}

JIE12 = ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑", "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]
JQ_KO = {"立春": "입춘", "惊蛰": "경칩", "清明": "청명", "立夏": "입하", "芒种": "망종", "小暑": "소서",
         "立秋": "입추", "白露": "백로", "寒露": "한로", "立冬": "입동", "大雪": "대설", "小寒": "소한",
         "雨水": "우수", "春分": "춘분", "谷雨": "곡우", "小满": "소만", "夏至": "하지", "大暑": "대서",
         "处暑": "처서", "秋分": "추분", "霜降": "상강", "小雪": "소설", "冬至": "동지", "大寒": "대한"}

CST = timezone(timedelta(hours=8))  # lunar_python 절기 시각 기준 (중국 표준시)
KST = ZoneInfo("Asia/Seoul")


def el_idx(e):
    return ELEMENTS.index(e)


def gz_ko(gz):
    return STEMS_KO[STEMS.index(gz[0])] + BRANCHES_KO[BRANCHES.index(gz[1])]


def gz_from_index(i):
    i %= 60
    return STEMS[i % 10] + BRANCHES[i % 12]


def gz_index(gz):
    s, b = STEMS.index(gz[0]), BRANCHES.index(gz[1])
    for i in range(60):
        if i % 10 == s and i % 12 == b:
            return i
    raise ValueError(gz)


def stem_yang(s):
    return STEMS.index(s) % 2 == 0


def ten_god(day_stem, other_stem):
    de, oe = el_idx(STEM_EL[STEMS.index(day_stem)]), el_idx(STEM_EL[STEMS.index(other_stem)])
    d = (oe - de) % 5
    rel = {0: "same", 1: "output", 2: "wealth", 3: "officer", 4: "resource"}[d]
    return TEN_GODS[(rel, stem_yang(day_stem) == stem_yang(other_stem))]


def branch_ten_god(day_stem, branch):
    return ten_god(day_stem, HIDDEN[branch][-1])  # 정기 기준


def twelve_stage(stem, branch):
    start = BRANCHES.index(STAGE_START[stem])
    b = BRANCHES.index(branch)
    k = (b - start) % 12 if stem_yang(stem) else (start - b) % 12
    return STAGES[k]


# ---------------------------------------------------------------- 시간 보정
def equation_of_time_minutes(dt_utc):
    """NOAA 근사식, 분 단위 (진태양시 - 평균태양시)."""
    doy = dt_utc.timetuple().tm_yday
    g = 2 * math.pi / 365 * (doy - 1 + (dt_utc.hour - 12) / 24)
    return 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                     - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))


def to_utc(civil, tzname=None, utc_offset=None, warnings=None):
    if utc_offset is not None:
        return (civil - timedelta(hours=utc_offset)).replace(tzinfo=timezone.utc), timedelta(hours=utc_offset)
    tz = ZoneInfo(tzname or "Asia/Seoul")
    a = civil.replace(tzinfo=tz, fold=0)
    b = civil.replace(tzinfo=tz, fold=1)
    if a.utcoffset() != b.utcoffset():
        # 존재하지 않는 시각(서머타임 시작) 또는 중복 시각(종료)
        roundtrip = a.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None)
        if roundtrip != civil:
            warnings.append("입력 시각은 서머타임 시작으로 존재하지 않는 시각입니다(시계가 건너뜀). 표준시로 간주했습니다.")
        else:
            warnings.append("입력 시각은 서머타임 종료로 두 번 존재하는 시각입니다. 서머타임(첫 번째)으로 간주했습니다.")
    return a.astimezone(timezone.utc), a.utcoffset()


def lunar_to_solar(y, m, d, leap, warnings):
    try:
        from korean_lunar_calendar import KoreanLunarCalendar
        c = KoreanLunarCalendar()
        ok = c.setLunarDate(y, m, d, bool(leap))
        if ok:
            return date.fromisoformat(c.SolarIsoFormat())
        warnings.append("KASI 음력 변환 실패/범위 밖 → 중국 음력(lunar_python)으로 변환")
    except ImportError:
        warnings.append("korean_lunar_calendar 미설치 → 중국 음력(lunar_python)으로 변환(드물게 하루 차이 가능)")
    from lunar_python import Lunar
    s = Lunar.fromYmd(y, -m if leap else m, d).getSolar()
    return date(s.getYear(), s.getMonth(), s.getDay())


# ---------------------------------------------------------------- 관계
STEM_HAP = {frozenset("甲己"): "토", frozenset("乙庚"): "금", frozenset("丙辛"): "수",
            frozenset("丁壬"): "목", frozenset("戊癸"): "화"}
STEM_CHUNG = [frozenset(x) for x in ["甲庚", "乙辛", "丙壬", "丁癸"]]
YUKHAP = {frozenset("子丑"): "토", frozenset("寅亥"): "목", frozenset("卯戌"): "화",
          frozenset("辰酉"): "금", frozenset("巳申"): "수", frozenset("午未"): "화(토)"}
SAMHAP = {"申子辰": "수", "亥卯未": "목", "寅午戌": "화", "巳酉丑": "금"}
BANGHAP = {"寅卯辰": "목", "巳午未": "화", "申酉戌": "금", "亥子丑": "수"}
CHUNG = [frozenset(x) for x in ["子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥"]]
HYUNG_PAIRS = {frozenset("寅巳"): "인사형(무은지형)", frozenset("巳申"): "사신형(무은지형)",
               frozenset("寅申"): "인신형(무은지형)", frozenset("丑戌"): "축술형(지세지형)",
               frozenset("戌未"): "술미형(지세지형)", frozenset("丑未"): "축미형(지세지형)",
               frozenset("子卯"): "자묘형(무례지형)"}
SELF_HYUNG = set("辰午酉亥")
PA = [frozenset(x) for x in ["子酉", "丑辰", "寅亥", "卯午", "巳申", "未戌"]]
HAE = [frozenset(x) for x in ["子未", "丑午", "寅巳", "卯辰", "申亥", "酉戌"]]
WONJIN = [frozenset(x) for x in ["子未", "丑午", "寅酉", "卯申", "辰亥", "巳戌"]]
GWIMUN = [frozenset(x) for x in ["子酉", "丑午", "寅未", "卯申", "辰亥", "巳戌"]]


def pair_relations(a, b, stems=False):
    """두 글자 사이 관계 목록"""
    out = []
    fs = frozenset(a + b)
    if stems:
        if fs in STEM_HAP: out.append(f"천간합({STEM_HAP[fs]})")
        if fs in STEM_CHUNG: out.append("천간충")
        return out
    if fs in YUKHAP: out.append(f"육합({YUKHAP[fs]})")
    for k, v in SAMHAP.items():
        if a != b and a in k and b in k:
            wang = k[1]
            out.append(f"삼합 반합({v})" if wang in (a, b) else f"삼합 가합(생지+묘지,{v},약)")
    for k, v in BANGHAP.items():
        if a != b and a in k and b in k:
            out.append(f"방합 일부({v})")
    if fs in CHUNG: out.append("충")
    if fs in HYUNG_PAIRS: out.append(HYUNG_PAIRS[fs])
    if a == b and a in SELF_HYUNG: out.append("자형")
    if fs in PA and a != b: out.append("파")
    if fs in HAE and a != b: out.append("해")
    if fs in WONJIN and a != b: out.append("원진")
    if fs in GWIMUN and a != b: out.append("귀문관")
    return out


def chart_relations(pillars):
    names = [p["name"] for p in pillars]
    res = []
    n = len(pillars)
    for i in range(n):
        for j in range(i + 1, n):
            for r in pair_relations(pillars[i]["gz"][0], pillars[j]["gz"][0], stems=True):
                res.append(f"{names[i]}간-{names[j]}간 {pillars[i]['gz'][0]}{pillars[j]['gz'][0]} {r}")
            for r in pair_relations(pillars[i]["gz"][1], pillars[j]["gz"][1]):
                res.append(f"{names[i]}지-{names[j]}지 {pillars[i]['gz'][1]}{pillars[j]['gz'][1]} {r}")
    brs = set(p["gz"][1] for p in pillars)
    for k, v in SAMHAP.items():
        if set(k) <= brs: res.append(f"삼합 완성 {k} → {v}국")
    for k, v in BANGHAP.items():
        if set(k) <= brs: res.append(f"방합 완성 {k} → {v}방")
    for k, nm in [("寅巳申", "삼형(무은지형)"), ("丑戌未", "삼형(지세지형)")]:
        if set(k) <= brs: res.append(f"{nm} 완성 {k}")
    return res


# ---------------------------------------------------------------- 신살
def samhap_group(branch):
    for k in SAMHAP:
        if branch in k:
            return k
    raise ValueError


SINSAL12 = "겁살 재살 천살 지살 연살(도화) 월살 망신살 장성살 반안살 역마살 육해살 화개살".split()


def sinsal12(base_branch, target):
    g = samhap_group(base_branch)
    start = (BRANCHES.index(g[0]) - 3) % 12  # 겁살 = 생지 - 3
    return SINSAL12[(BRANCHES.index(target) - start) % 12]


CHEONEUL = {"甲": "丑未", "戊": "丑未", "庚": "丑未", "乙": "子申", "己": "子申", "丙": "亥酉", "丁": "亥酉",
            "辛": "寅午", "壬": "巳卯", "癸": "巳卯"}
MUNCHANG = dict(zip(STEMS, "巳午申酉申酉亥子寅卯"))
YANGIN = {"甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子", "乙": "辰", "丁": "未", "己": "未", "辛": "戌", "癸": "丑"}
HONGYEOM = dict(zip(STEMS, "午午寅未辰辰戌酉子申"))
GOEGANG = {"庚辰", "庚戌", "壬辰", "壬戌", "戊戌"}
BAEKHO = {"甲辰", "乙未", "丙戌", "丁丑", "戊辰", "壬戌", "癸丑"}


def gongmang(gz):
    i = gz_index(gz)
    start = i - i % 10
    b0 = start % 12
    return BRANCHES[(b0 + 10) % 12] + BRANCHES[(b0 + 11) % 12]


def sinsal(pillars, day_stem, year_br, day_br):
    out = []
    for p in pillars:
        b = p["gz"][1]
        tags = []
        if b in CHEONEUL[day_stem]: tags.append("천을귀인")
        if b == MUNCHANG[day_stem]: tags.append("문창귀인")
        if b == YANGIN[day_stem]: tags.append("양인" + ("" if stem_yang(day_stem) else "(음간 양인: 이견 있음)"))
        if b == HONGYEOM[day_stem]: tags.append("홍염살")
        if p["gz"] in BAEKHO: tags.append("백호살")
        if p["name"] == "일" and p["gz"] in GOEGANG: tags.append("괴강살")
        s_y = sinsal12(year_br, b) if p["name"] != "년" else None
        s_d = sinsal12(day_br, b) if p["name"] != "일" else None
        for lab, s in [("년지기준", s_y), ("일지기준", s_d)]:
            if s and s.split("(")[0] in ("겁살", "재살", "천살", "지살", "연살", "월살", "망신살", "장성살", "반안살", "역마살", "육해살", "화개살"):
                tags.append(f"{s}[{lab}]")
        out.append({"pillar": p["name"], "gz": p["gz"], "sinsal": tags})
    gm = {"일주공망": gongmang(pillars_by(pillars, "일")["gz"]), "년주공망": gongmang(pillars_by(pillars, "년")["gz"])}
    return out, gm


def pillars_by(pillars, name):
    return next(p for p in pillars if p["name"] == name)


# ---------------------------------------------------------------- 신강/신약 휴리스틱
POS_W = {("년", "s"): 1.0, ("년", "b"): 1.0, ("월", "s"): 1.0, ("월", "b"): 3.0,
         ("일", "b"): 1.5, ("시", "s"): 1.0, ("시", "b"): 1.2}


def strength(pillars, day_stem):
    sup = tot = 0.0
    detail = []
    for p in pillars:
        for part, ch in (("s", p["gz"][0]), ("b", p["gz"][1])):
            if p["name"] == "일" and part == "s":
                continue
            w = POS_W[(p["name"], part)]
            tg = ten_god(day_stem, ch) if part == "s" else branch_ten_god(day_stem, ch)
            helps = tg in ("비견", "겁재", "정인", "편인")
            tot += w
            if helps: sup += w
    ratio = sup / tot if tot else 0
    m = pillars_by(pillars, "월")["gz"][1]
    deukryeong = branch_ten_god(day_stem, m) in ("비견", "겁재", "정인", "편인")
    d = pillars_by(pillars, "일")["gz"][1]
    deukji = branch_ten_god(day_stem, d) in ("비견", "겁재", "정인", "편인")
    if ratio >= 0.6: lab = "신강(身强)"
    elif ratio >= 0.5: lab = "중화~약간 신강"
    elif ratio >= 0.4: lab = "중화~약간 신약"
    else: lab = "신약(身弱)"
    return {"support_ratio": round(ratio, 2), "득령(월지)": deukryeong, "득지(일지)": deukji, "판단(참고용)": lab}


# ---------------------------------------------------------------- 메인 계산
def compute(args):
    warnings = []
    y, mo, d = map(int, args.date.split("-"))
    if args.lunar:
        sd = lunar_to_solar(y, mo, d, args.leap, warnings)
    else:
        sd = date(y, mo, d)
    time_known = bool(args.time)
    hh, mm = map(int, args.time.split(":")) if time_known else (12, 0)
    civil = datetime(sd.year, sd.month, sd.day, hh, mm)

    # 경도
    if args.place is None:
        lon = 126.98; place_label = "서울(기본값)"
    else:
        try:
            lon = float(args.place); place_label = f"경도 {lon}"
        except ValueError:
            if args.place not in PLACES:
                sys.exit(f"알 수 없는 지역: {args.place}. 경도 숫자로 입력하세요. 지원: {', '.join(PLACES)}")
            lon = PLACES[args.place]; place_label = f"{args.place}({lon}°E)"

    utc, offset = to_utc(civil, args.tz, args.utc_offset, warnings)
    std_meridian = offset.total_seconds() / 3600 * 15
    lmt = utc + timedelta(hours=lon / 15)
    eot = equation_of_time_minutes(utc) if args.eot else 0.0
    solar_t = (lmt + timedelta(minutes=eot)).replace(tzinfo=None)
    corr_min = (solar_t - civil).total_seconds() / 60

    # 년/월주: 절기 정확 시각 (절대시각 비교)
    cst = utc.astimezone(CST)
    lun = Solar.fromYmdHms(cst.year, cst.month, cst.day, cst.hour, cst.minute, cst.second).getLunar()
    ec = lun.getEightChar()
    year_gz, month_gz = ec.getYear(), ec.getMonth()

    # 절기 근접 경고 (시간 모를 때)
    prev_jie = lun.getPrevJie(False); next_jie = lun.getNextJie(False)
    def jie_dt(j):
        s = j.getSolar()
        return datetime(s.getYear(), s.getMonth(), s.getDay(), s.getHour(), s.getMinute(), s.getSecond(), tzinfo=CST)
    pj, nj = jie_dt(prev_jie), jie_dt(next_jie)
    if not time_known:
        for j, jd in ((prev_jie, pj), (next_jie, nj)):
            if abs((jd - utc).total_seconds()) < 86400:
                warnings.append(f"출생일이 {JQ_KO.get(j.getName(), j.getName())} 절입일입니다. 시간을 모르면 월주(입춘이면 년주까지)가 바뀔 수 있습니다.")

    # 일주/시주: 지방태양시 기준
    base_ord = date(2000, 1, 1).toordinal()
    def day_gz_of(dd):
        return gz_from_index(54 + dd.toordinal() - base_ord)  # 2000-01-01 = 戊午(54)
    sol_date = solar_t.date()
    late_zi = time_known and solar_t.hour == 23
    if late_zi and args.zi == "unified":
        day_date = sol_date + timedelta(days=1)
    else:
        day_date = sol_date
    day_gz = day_gz_of(day_date if time_known else sd)
    alt_day = None
    if late_zi:
        alt_day = day_gz_of(sol_date if args.zi == "unified" else sol_date + timedelta(days=1))
        warnings.append("지방시 23시대(자시 초) 출생 → 자시 처리 규칙에 따라 일주/시주가 달라집니다: "
                        "unified(23시 일 변경)·split(야자시: 일주 당일, 시주 다음날 자시)·midnight(자정 기준: 일주·시주 모두 당일).")

    pillars = [{"name": "년", "gz": year_gz}, {"name": "월", "gz": month_gz}, {"name": "일", "gz": day_gz}]
    if time_known:
        mins = solar_t.hour * 60 + solar_t.minute
        hb = ((mins + 60) // 120) % 12
        if late_zi and args.zi != "midnight":
            stem_day = STEMS.index(day_gz_of(sol_date + timedelta(days=1))[0])
        else:
            stem_day = STEMS.index(day_gz[0])
        hs = (stem_day % 5 * 2 + hb) % 10
        pillars.append({"name": "시", "gz": STEMS[hs] + BRANCHES[hb]})

    ds = day_gz[0]
    for p in pillars:
        s, b = p["gz"]
        p["ko"] = gz_ko(p["gz"])
        p["stem_tengod"] = "일간(나)" if p["name"] == "일" else ten_god(ds, s)
        p["branch_tengod"] = branch_ten_god(ds, b)
        p["stem_el"] = STEM_EL[STEMS.index(s)] + ("+" if stem_yang(s) else "-")
        p["branch_el"] = BRANCH_EL[BRANCHES.index(b)] + ("+" if BRANCH_YANG[BRANCHES.index(b)] else "-")
        p["hidden"] = [{"stem": h, "ko": STEMS_KO[STEMS.index(h)], "tengod": ten_god(ds, h)} for h in HIDDEN[b]]
        p["12운성"] = twelve_stage(ds, b)
        p["12운성_자좌"] = twelve_stage(s, b)

    # 오행 분포
    counts = {e: 0 for e in ELEMENTS}
    for p in pillars:
        counts[STEM_EL[STEMS.index(p["gz"][0])]] += 1
        counts[BRANCH_EL[BRANCHES.index(p["gz"][1])]] += 1
    hidden_w = {e: 0.0 for e in ELEMENTS}  # 지장간 포함 가중 (천간1, 지지는 지장간 정기0.6/중기0.25/여기0.15 비율)
    for p in pillars:
        hidden_w[STEM_EL[STEMS.index(p["gz"][0])]] += 1
        hs_ = HIDDEN[p["gz"][1]]
        ws = [0.3, 0.7] if len(hs_) == 2 else [0.15, 0.25, 0.6]
        for h, w in zip(hs_, ws):
            hidden_w[STEM_EL[STEMS.index(h)]] += w
    tg_count = {}
    for p in pillars:
        for t in ([p["stem_tengod"]] if p["name"] != "일" else []) + [p["branch_tengod"]]:
            tg_count[t] = tg_count.get(t, 0) + 1

    # 대운
    yang_year = stem_yang(year_gz[0])
    male = args.gender.upper() == "M"
    forward = (yang_year and male) or (not yang_year and not male)
    target = nj if forward else pj
    days = abs((target - utc).total_seconds()) / 86400
    exact_years = days / 3
    yrs = int(exact_years); months = int(round((exact_years - yrs) * 12))
    if months == 12: yrs += 1; months = 0
    daeun_su = max(1, int(round(exact_years)))
    mi = gz_index(month_gz)
    daeun = []
    for k in range(1, 11):
        g = gz_from_index(mi + k if forward else mi - k)
        start_age = daeun_su + (k - 1) * 10
        daeun.append({"순서": k, "gz": g, "ko": gz_ko(g), "시작나이(만)": start_age,
                      "시작나이(한국식 세는나이)": start_age + 1,
                      "시작연도(대략)": sd.year + start_age,
                      "천간십신": ten_god(ds, g[0]), "지지십신": branch_ten_god(ds, g[1]),
                      "12운성": twelve_stage(ds, g[1])})
    exact_start = utc + timedelta(days=exact_years * 365.2422)

    # 세운
    seun = []
    y0, y1 = args.seun_from, args.seun_to
    for yy in range(y0, y1 + 1):
        g = gz_from_index(yy - 4)
        rels = []
        for p in pillars:
            for r in pair_relations(g[0], p["gz"][0], stems=True):
                rels.append(f"세운간-{p['name']}간 {r}")
            for r in pair_relations(g[1], p["gz"][1]):
                rels.append(f"세운지-{p['name']}지 {r}")
        cur = None
        age = yy - sd.year
        for du in daeun:
            if du["시작나이(만)"] <= age < du["시작나이(만)"] + 10:
                cur = du["ko"] + "(" + du["gz"] + ")"
        if daeun and age < daeun[0]["시작나이(만)"]:
            cur = "대운 전(월주 " + gz_ko(month_gz) + ")"
        seun.append({"년": yy, "gz": g, "ko": gz_ko(g), "띠": ANIMALS[BRANCHES.index(g[1])],
                     "천간십신": ten_god(ds, g[0]), "지지십신": branch_ten_god(ds, g[1]),
                     "12운성": twelve_stage(ds, g[1]), "해당대운": cur,
                     "신살": [s for s in [
                         sinsal12(pillars_by(pillars, "년")["gz"][1], g[1]) + "[년지기준]",
                         sinsal12(day_gz[1], g[1]) + "[일지기준]",
                         "천을귀인" if g[1] in CHEONEUL[ds] else None] if s],
                     "원국과의관계": rels})

    ss, gm = sinsal(pillars, ds, year_gz[1], day_gz[1])
    result = {
        "input": {"date": args.date, "lunar": args.lunar, "leap": args.leap, "time": args.time,
                  "gender": "남" if male else "여", "place": place_label, "zi_mode": args.zi, "eot": args.eot},
        "solar_date": sd.isoformat(),
        "time_known": time_known,
        "time_correction": {
            "civil_time": civil.strftime("%Y-%m-%d %H:%M") if time_known else None,
            "utc_offset_at_birth": str(offset), "standard_meridian": std_meridian,
            "utc": utc.strftime("%Y-%m-%d %H:%M"),
            "local_solar_time": solar_t.strftime("%Y-%m-%d %H:%M") if time_known else None,
            "correction_minutes": round(corr_min, 1) if time_known else None,
            "equation_of_time_min": round(eot, 1),
        },
        "pillars": pillars,
        "alt_day_pillar_if_other_zi_rule": alt_day,
        "day_master": {"stem": ds, "ko": STEMS_KO[STEMS.index(ds)], "element": STEM_EL[STEMS.index(ds)],
                       "yang": stem_yang(ds)},
        "five_elements_count": counts,
        "five_elements_weighted_with_hidden": {k: round(v, 2) for k, v in hidden_w.items()},
        "ten_gods_count": tg_count,
        "strength": strength(pillars, ds),
        "relations": chart_relations(pillars),
        "sinsal": ss, "gongmang": gm,
        "jieqi": {"prev": [JQ_KO.get(prev_jie.getName()), pj.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")],
                  "next": [JQ_KO.get(next_jie.getName()), nj.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")]},
        "daeun_info": {"direction": "순행" if forward else "역행", "days_to_jie": round(days, 2),
                       "exact": f"{yrs}년 {months}개월", "대운수": daeun_su,
                       "exact_start_date": exact_start.astimezone(KST).strftime("%Y-%m-%d")},
        "daeun": daeun,
        "seun": seun,
        "warnings": warnings,
    }
    return result


def fmt(r):
    L = []
    i = r["input"]
    L.append("=" * 64)
    L.append(f"사주팔자 만세력  ({i['gender']}, {'음력' + ('윤달' if i['leap'] else '') if i['lunar'] else '양력'} {i['date']} {i['time'] or '시간모름'}, {i['place']})")
    L.append("=" * 64)
    tc = r["time_correction"]
    L.append(f"양력일: {r['solar_date']}")
    if r["time_known"]:
        L.append(f"입력시각 {tc['civil_time']} (당시 UTC{tc['utc_offset_at_birth'][:-3] if tc['utc_offset_at_birth'].count(':')==2 else tc['utc_offset_at_birth']}, 표준자오선 {tc['standard_meridian']:.1f}°E)")
        L.append(f"→ 지방{'진' if i['eot'] else '평균'}태양시 {tc['local_solar_time']}  (보정 {tc['correction_minutes']:+.1f}분"
                 + (f", 균시차 {tc['equation_of_time_min']:+.1f}분 포함" if i['eot'] else "") + ")")
    L.append(f"절기: 직전 {r['jieqi']['prev'][0]} {r['jieqi']['prev'][1]} / 다음 {r['jieqi']['next'][0]} {r['jieqi']['next'][1]}")
    L.append("")
    ps = r["pillars"][::-1]  # 시 일 월 년
    w = 14
    L.append("".join(f"{p['name'] + '주':^{w-2}}" for p in ps))
    L.append("".join(f"{p['stem_tengod']:^{w-3}}" for p in ps))
    L.append("".join(f"{p['gz'][0] + '(' + p['ko'][0] + ')' + p['stem_el']:^{w-3}}" for p in ps))
    L.append("".join(f"{p['gz'][1] + '(' + p['ko'][1] + ')' + p['branch_el']:^{w-3}}" for p in ps))
    L.append("".join(f"{p['branch_tengod']:^{w-3}}" for p in ps))
    L.append("".join(f"{''.join(h['stem'] for h in p['hidden']):^{w-1}}" for p in ps) + " ← 지장간")
    L.append("".join(f"{p['12운성']:^{w-3}}" for p in ps) + " ← 12운성(일간기준)")
    L.append("")
    for p in r["pillars"]:
        hid = ", ".join(f"{h['stem']}({h['ko']}){h['tengod']}" for h in p["hidden"])
        L.append(f"  {p['name']}주 {p['gz']}({p['ko']}): 천간 {p['stem_tengod']} / 지지 {p['branch_tengod']} / 지장간 {hid} / 12운성 {p['12운성']} (자좌 {p['12운성_자좌']})")
    if not r["time_known"]:
        L.append("  ※ 출생시간 모름 → 시주 생략 (6글자로 판단)")
    if r["alt_day_pillar_if_other_zi_rule"]:
        L.append(f"  ※ 23시대(자시 초) 출생: 현재 규칙({i['zi_mode']}) 일주 {r['pillars'][2]['gz']}, 다른 규칙이면 일주 {r['alt_day_pillar_if_other_zi_rule']} (--zi 옵션으로 비교)")
    dm = r["day_master"]
    L.append("")
    L.append(f"일간(나): {dm['stem']}({dm['ko']}) {EL_KO[dm['element']]}{'(양)' if dm['yang'] else '(음)'}")
    L.append("오행 개수: " + "  ".join(f"{EL_KO[k]}({k}) {v}" for k, v in r["five_elements_count"].items()))
    L.append("오행(지장간 가중): " + "  ".join(f"{EL_KO[k]} {v}" for k, v in r["five_elements_weighted_with_hidden"].items()))
    L.append("십신 분포: " + ", ".join(f"{k} {v}" for k, v in sorted(r["ten_gods_count"].items(), key=lambda x: -x[1])))
    s = r["strength"]
    L.append(f"신강/신약(휴리스틱): {s['판단(참고용)']} | 지지세력비 {s['support_ratio']} | 득령 {'O' if s['득령(월지)'] else 'X'} | 득지 {'O' if s['득지(일지)'] else 'X'}")
    L.append("")
    L.append("합·충·형·파·해 (원국):")
    L.extend("  - " + x for x in (r["relations"] or ["(특이 관계 없음)"]))
    L.append("신살:")
    for x in r["sinsal"]:
        L.append(f"  {x['pillar']}주 {x['gz']}: {', '.join(x['sinsal']) or '-'}")
    L.append(f"  공망: 일주기준 {r['gongmang']['일주공망']} / 년주기준 {r['gongmang']['년주공망']}")
    L.append("")
    di = r["daeun_info"]
    L.append(f"대운: {di['direction']} | 절입까지 {di['days_to_jie']}일 → 정밀 {di['exact']} (대운수 {di['대운수']}, 첫 대운 정밀 시작 ≈ {di['exact_start_date']})")
    L.append("  " + " | ".join(f"{d['시작나이(만)']}세 {d['gz']}({d['ko']}) {d['천간십신']}/{d['지지십신']} {d['12운성']}" for d in r["daeun"][:5]))
    L.append("  " + " | ".join(f"{d['시작나이(만)']}세 {d['gz']}({d['ko']}) {d['천간십신']}/{d['지지십신']} {d['12운성']}" for d in r["daeun"][5:]))
    L.append("  (나이는 만 나이 기준. 한국식 세는나이는 +1)")
    L.append("")
    L.append("세운:")
    for x in r["seun"]:
        L.append(f"  {x['년']} {x['gz']}({x['ko']},{x['띠']}띠): {x['천간십신']}/{x['지지십신']}, 12운성 {x['12운성']}, 대운 {x['해당대운']}")
        L.append(f"      신살: {', '.join(x['신살'])}")
        if x["원국과의관계"]:
            L.append("      관계: " + "; ".join(x["원국과의관계"]))
    if r["warnings"]:
        L.append("")
        L.extend("⚠ " + w for w in r["warnings"])
    L.append("\n※ 전통 명리 계산 결과이며 해석은 전통 해석일 뿐 과학적 근거가 있는 예측이 아닙니다.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="사주팔자 만세력 계산기")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (양력 기본, --lunar 시 음력)")
    ap.add_argument("--time", help="HH:MM (당시 시계 시각). 모르면 생략 → 시주 생략")
    ap.add_argument("--lunar", action="store_true", help="음력 입력")
    ap.add_argument("--leap", action="store_true", help="음력 윤달")
    ap.add_argument("--gender", required=True, choices=["M", "F", "m", "f"])
    ap.add_argument("--place", help="지역명(서울,부산...) 또는 경도(예: 126.98). 기본 서울")
    ap.add_argument("--tz", help="IANA 시간대 (기본 Asia/Seoul, 해외 출생 시 예: America/New_York)")
    ap.add_argument("--utc-offset", type=float, help="tzdata 대신 고정 UTC 오프셋(시간) 사용")
    ap.add_argument("--zi", choices=["unified", "split", "midnight"], default="unified",
                    help="unified: 지방시 23시부터 다음날 일주(자시/정자시 기준, 기본). split: 야자시/조자시(23~24시는 당일 일주, 시주는 다음날 자시). midnight: 자정 기준(23시대도 당일 일주·당일 자시)")
    ap.add_argument("--eot", action="store_true", help="균시차까지 적용한 진태양시 (기본은 경도만 보정한 평균태양시)")
    ap.add_argument("--no-solar-correction", action="store_true", help="경도 보정 없이 시계 시각 그대로 사용 (비교용)")
    ap.add_argument("--seun-from", type=int, default=2025)
    ap.add_argument("--seun-to", type=int, default=2027)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    a._nosc = a.no_solar_correction
    r = compute_wrap(a)
    print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else fmt(r))


def compute_wrap(a):
    if getattr(a, "_nosc", False):
        # 당시 오프셋에 해당하는 표준자오선 경도를 출생지 경도로 넣어 보정을 0으로 만든다
        tmp = argparse.Namespace(**vars(a))
        y, mo, d = map(int, a.date.split("-"))
        sd = lunar_to_solar(y, mo, d, a.leap, []) if a.lunar else date(y, mo, d)
        hh, mm = map(int, a.time.split(":")) if a.time else (12, 0)
        _, off = to_utc(datetime(sd.year, sd.month, sd.day, hh, mm), a.tz, a.utc_offset, [])
        tmp.place = str(off.total_seconds() / 3600 * 15)
        tmp.eot = False
        return compute(tmp)
    return compute(a)


if __name__ == "__main__":
    main()
