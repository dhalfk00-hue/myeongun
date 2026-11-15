# -*- coding: utf-8 -*-
"""손명리 앱 API v2: 감정서 생성기(make_report / make_gunghap)를 앱에 연결.
- 무료 요약(핵심 3가지 + 올해·내년 별점) + 잠긴 전체 감정서(HTML 보기 · PDF)
- 결제는 자리만 잡아 둠(Google Play 결제 연동 전). 개발용 잠금 해제: MYEONGUN_DEV_UNLOCK=1 + 토큰 "DEV-UNLOCK"
- 손금: 사진은 받지 않음. 기기에서 찾은 선 좌표·손 관절 좌표·특징만 받음.
LLM·유료 API 호출 없음."""
from __future__ import annotations

import hashlib, hmac, html as _html, json, math, os, re, secrets, shutil, sys, threading, time
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel, Field

from . import places_kr as PK
from . import interpret as I
from .analyzer import palm_rules as PR
from .analyzer import palm_saju as PS

GEN_DIR = os.environ.get("MYEONGUN_REPORT_DIR", str(Path(__file__).resolve().parent.parent / "gen"))
if GEN_DIR not in sys.path:
    sys.path.insert(0, GEN_DIR)
import engine as E            # noqa: E402  (감정서 생성기)
import build as B             # noqa: E402
import lunar as L             # noqa: E402
import make_report as MR      # noqa: E402
import make_gunghap as MG     # noqa: E402
import palm as PM             # noqa: E402
import jobs as JB             # noqa: E402  (app1113: 직업 상황별 문장)
import gloss as GL            # noqa: E402  (gloss1116: 화면 요약도 한자는 한글 읽기 + 쉬운 뜻)
import josa as JS             # noqa: E402  (josa1116: 풀이 뒤 조사 맞춤 settle)
import advice as AV           # noqa: E402
import topics as TP           # noqa: E402  (tier1115: 주제 이름)
import tiers as TR            # noqa: E402  (tier1115: 등급별 감정서)

# app1113: jobs.apply()가 texts/advice 사전을 제자리에서 바꾸므로, 감정서 조립은 한 번에 한 사람씩
_GEN_LOCK = threading.RLock()

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("MYEONGUN_CACHE", ROOT / "cache"))
CACHE.mkdir(parents=True, exist_ok=True)
KEEP_HOURS = 24          # 감정서 파일은 하루 뒤 자동 삭제
DEV_UNLOCK = os.environ.get("MYEONGUN_DEV_UNLOCK", "0") == "1"
# nopalm1113: 손금 기능 스위치 하나. 출시판은 꺼 둠(사주·궁합만). 다시 켜려면 환경 변수 PALM_ENABLED=1
PALM_ENABLED = os.environ.get("PALM_ENABLED", "0") == "1"
BANNED = ("\ubc31\uc6b4", "\ub3c4\uc0ac", "\ucca0\ud559\uc6d0", "\ube14\ub85c\uadf8")

PRODUCTS = {   # Play Console 인앱 상품 ID 후보 · 가격(원)은 나중에 콘솔에서 정함
    "saju": {"id": "saju_full_report", "price": 15000, "title": "사주 종합 감정서", "pages": 10},
    "gunghap": {"id": "gunghap_full_report", "price": 15000, "title": "결혼 궁합 감정서", "pages": 7},
    "palm": {"id": "palm_saju_report", "price": 15000, "title": "사주 × 손금 교차 감정서", "pages": 13},
}


def _secret() -> bytes:
    env = os.environ.get("MYEONGUN_SECRET")
    if env:
        return env.encode()
    f = CACHE / ".secret"
    if not f.exists():
        f.write_text(secrets.token_hex(32)); os.chmod(f, 0o600)
    return f.read_text().strip().encode()


SECRET = _secret()
router = APIRouter()


# ------------------------------------------------------------------ 공통
_JOSA = {"이": ("이", "가"), "가": ("이", "가"), "은": ("은", "는"), "는": ("은", "는"), "을": ("을", "를"), "를": ("을", "를"), "과": ("과", "와"), "와": ("과", "와")}
_JRE = re.compile(r"([가-힣])(\([^()]{1,4}\))?(이|가|은|는|을|를|과|와)(?=[\s,.!?·<]|$)")


def fix_josa(s: str) -> str:
    """'홍길동님가'→'홍길동님이', '토(土)이'→'토(土)가' 처럼 받침에 맞게 조사를 고침 (님·괄호 한자 뒤만)."""
    def rep(m):
        ch, par, j = m.group(1), m.group(2), m.group(3)
        if not par and ch != "님":
            return m.group(0)
        has = (ord(ch) - 0xAC00) % 28 != 0
        return ch + (par or "") + _JOSA[j][0 if has else 1]
    return _JRE.sub(rep, s)


def clean(x):
    """화면에 나가는 모든 글에서 출처 이름을 빼고, 내부용 키를 지움."""
    if isinstance(x, str):
        s = x
        for a, b in (("\ubc31\uc6b4\ubc15\uc0ac가 ", "수상학에서 "), ("\ubc31\uc6b4\ubc15\uc0ac는 ", "수상학에서는 "), ("\ubc31\uc6b4\ubc15\uc0ac 방식대로 ", "전통 수상학 기준으로 "),
                     ("\ubc31\uc6b4\ubc15\uc0ac 자료에서 ", "전통 수상학에서 "), ("\ubc31\uc6b4\ubc15\uc0ac 유년법", "수상학 유년법"), (", \ubc31\uc6b4\ubc15\uc0ac)", ")"),
                     ("\ubc31\uc6b4\ubc15\uc0ac 수상학", "전통 수상학"), ("\ubc31\uc6b4\ubc15\uc0ac의 ", ""), ("\ubc31\uc6b4\ubc15\uc0ac ", ""), ("\ubc31\uc6b4\ubc15\uc0ac", "전통 수상학"),
                     ("\ub124\uc774\ubc84\u0020\ube14\ub85c\uadf8", ""), ("\ube14\ub85c\uadf8", "")):
            s = s.replace(a, b)
        return fix_josa(s)
    if isinstance(x, list):
        return [clean(v) for v in x]
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items() if k not in ("src", "sources", "framework", "_measure")}
    return x


def _check_banned(text: str):
    for w in BANNED:
        if w in text:
            raise HTTPException(500, "감정서 문구 검사에 걸렸어요")


ALLOWED_TAG = re.compile(r"</?(b|strong|span)( class=\"gold\")?>")


def safe_html(s: str) -> str:
    """생성기 문장(작은 b/strong/span.gold 태그 포함) → 그 태그만 남기고 나머지는 이스케이프."""
    out, last = [], 0
    for m in ALLOWED_TAG.finditer(s):
        out.append(_html.escape(_html.unescape(s[last:m.start()]))); out.append(m.group(0).replace("strong", "b")); last = m.end()
    out.append(_html.escape(_html.unescape(s[last:])))
    return clean("".join(out))


def _sign(msg: str) -> str:
    return hmac.new(SECRET, msg.encode(), hashlib.sha256).hexdigest()[:32]


def _rid(kind: str, payload: dict) -> str:
    return kind[0] + _sign(kind + json.dumps(payload, sort_keys=True, ensure_ascii=False))[:23]


def _unlock_ok(rid: str, u: Optional[str]) -> bool:
    return bool(u) and hmac.compare_digest(u, _sign("unlock:" + rid))


def _gc():
    now = time.time()
    for d in CACHE.iterdir():
        if d.is_dir() and now - d.stat().st_mtime > KEEP_HOURS * 3600:
            shutil.rmtree(d, ignore_errors=True)


def _store(rid: str, kind: str, doc: str, css: str, assets: dict | None = None):
    _check_banned(doc)
    doc = fix_josa(doc)
    d = CACHE / rid
    d.mkdir(exist_ok=True)
    (d / "report.html").write_text(doc)
    (d / "style.css").write_text(css + VIEW_CSS)
    for name, spec in (assets or {}).items():
        PM.render_overlay(spec, str(d / name))
    (d / "meta.json").write_text(json.dumps({"kind": kind, "created": time.time()}))
    pdf = d / "report.pdf"
    if pdf.exists():
        pdf.unlink()
    os.utime(d)


# 앱 안에서 볼 때: A4 페이지를 화면 폭에 맞춰 축소
VIEW_CSS = """
@media screen { html { background:#e9e1cf; } body { margin:0; padding:8px 0; }
 .page { margin:0 auto 10px !important; box-shadow:0 2px 10px rgba(60,40,10,.25); } }
"""


# ------------------------------------------------------------------ 입력
class BirthIn(BaseModel):
    name: Optional[str] = Field(None, max_length=12)
    gender: str = "M"                 # M | F
    calendar: str = "solar"           # solar | lunar
    leap: bool = False
    date: str                         # YYYY-MM-DD (음력이면 음력 날짜)
    time: Optional[str] = None        # HH:MM, 모르면 null
    time2: Optional[str] = None       # 범위 끝 (선택)
    place: str = "서울"
    job: Optional[str] = "미정"       # app1113: 직장인|사업자(사업가)|프리랜서|주부|학생|무직|미정
    time_rule: Optional[str] = "경도"  # tier1115: 시 경계 기준 — 경도(기본, 출생지 경도) | 30분(흔한 만세력 관례)


def _hm(t):
    if not t:
        return None
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", t.strip())
    if not m or not (0 <= int(m[1]) < 24 and 0 <= int(m[2]) < 60):
        raise HTTPException(400, "태어난 시각을 확인해 주세요")
    return f"{int(m[1]):02d}:{m[2]}"


class P:   # 정리된 한 사람
    def __init__(self, b: BirthIn, now: datetime):
        self.name = (b.name or "").strip() or None
        if self.name:
            self.name = re.sub(r"[<>&\"'{}]", "", self.name)[:12] or None
        self.gender = {"M": "M", "F": "F", "남": "M", "여": "F"}.get((b.gender or "").upper() if b.gender in ("m", "f") else b.gender)
        if not self.gender:
            raise HTTPException(400, "성별을 골라 주세요")
        if b.calendar not in ("solar", "lunar"):
            raise HTTPException(400, "양력/음력을 골라 주세요")
        self.lunar = b.calendar == "lunar"; self.leap = bool(b.leap and self.lunar)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", b.date or ""):
            raise HTTPException(400, "생년월일을 확인해 주세요")
        y, m, d = map(int, b.date.split("-"))
        if not (1900 <= y <= now.year):
            raise HTTPException(400, "1900년부터 올해까지 태어난 날만 볼 수 있어요")
        try:
            if self.lunar:
                L.lunar_to_solar(y, m, d, self.leap)
            else:
                datetime(y, m, d)
        except BaseException:
            raise HTTPException(400, ("음력 " + ("윤" if self.leap else "") + f"{y}년 {m}월 {d}일은 없는 날짜예요") if self.lunar else "없는 날짜예요")
        self.date = b.date
        self.t1, self.t2 = _hm(b.time), _hm(b.time2)
        if not self.t1:
            self.t2 = None
        if self.t2 == self.t1:
            self.t2 = None
        try:
            self.place_arg, self.place_label = PK.resolve(b.place)
        except KeyError:
            raise HTTPException(400, f"출생지를 목록에서 골라 주세요 ({b.place})")
        jb = "사업자" if b.job == "사업가" else b.job
        self.job = jb if jb in JB.JOBS else "미정"
        self.time_rule = "30분" if b.time_rule == "30분" else "경도"
        self.now = now
        self.note = None
        self.time = self.t1
        if self.t2:   # 범위: 양 끝 시주가 같으면 앞 시각, 다르면 가운데 시각으로 보고 알려 줌
            h1 = self._hour_gz(self.t1); h2 = self._hour_gz(self.t2)
            if h1 == h2:
                self.note = f"{self.t1}~{self.t2} 범위 전체가 같은 {h1}시주라 시주는 확실해요."
            else:
                a = int(self.t1[:2]) * 60 + int(self.t1[3:]); bb = int(self.t2[:2]) * 60 + int(self.t2[3:])
                mid = (a + bb) // 2 if bb > a else a
                self.time = f"{mid // 60:02d}:{mid % 60:02d}"
                hm = self._hour_gz(self.time)
                self.note = f"{self.t1}이면 {h1}시주, {self.t2}이면 {h2}시주라 범위 가운데({self.time}, {hm}시주)로 봤어요. 정확한 시각을 알면 더 정확해져요."

    def _hour_gz(self, t):
        r = self.run(t)
        return next(p["gz"] for p in r["pillars"] if p["name"] == "시")

    def run(self, t="__self__"):
        t = self.time if t == "__self__" else t
        try:
            return E.run_saju(self.date, t, self.lunar, self.leap, self.gender, self.calc_place(), self.now.year, self.now.year + 11)
        except SystemExit as e:
            raise HTTPException(400, f"입력을 확인해 주세요 ({e})")

    def calc_place(self, rule=None):
        """tier1115: '30분' 기준은 표준시 −30분(동경 127.5°) 관례, 기본 '경도'는 출생지 경도 (생성기 make_report.prepare와 같아요)"""
        return "127.5" if (rule or self.time_rule) == "30분" else self.place_arg

    def key(self):
        return {"n": self.name, "g": self.gender, "l": self.lunar, "lp": self.leap, "d": self.date, "t": self.time, "p": self.place_arg, "j": self.job, "r": self.time_rule}

    def chart_key(self):
        """tier1115: 사주(명식) 하나를 가리키는 키 — 이름·직업은 빼요(같은 사주면 이름을 바꿔도 같은 구매)."""
        return "c" + _sign("chart:" + json.dumps({"g": self.gender, "l": self.lunar, "lp": self.leap, "d": self.date, "t": self.time,
                                                   "p": self.place_arg, "r": self.time_rule}, sort_keys=True))[:15]

    def args(self, palm=None, **kw):
        ns = Namespace(name=self.name, gender=self.gender, date=self.date, lunar=self.lunar, leap=self.leap, time=self.time,
                       place=self.place_arg, place_label=self.place_label, palm_json=palm, palm_photo=None, job=self.job, time_rule=self.time_rule)
        for k, v in kw.items(): setattr(ns, k, v)
        return ns


EL_HAN = {"목": "木", "화": "火", "토": "土", "금": "金", "수": "水"}


def _pillars(c):
    out = []
    for n in ("시", "일", "월", "년"):
        if n not in c.P or (n == "시" and not c.time_known):
            out.append({"pos": n, "unknown": True}); continue
        p = c.P[n]; s, b = p["gz"]
        out.append({"pos": n, "gz": p["gz"], "ko": p["ko"], "stem_el": E.STEM_ELK[s], "branch_el": E.BR_ELK[b],
                    "stem_tg": "일간" if n == "일" else p["stem_tengod"], "branch_tg": p["branch_tengod"], "me": n == "일"})
    return out


def _year_card(rep, y, now):
    c = rep.c; gz = E.year_gz(y)
    from texts import EL_KO as _ek  # noqa
    return {"year": y, "gz": gz, "ko": B.ko(gz), "star": rep.ystar[y], "title": JS.settle(GL.apply(rep.year_title(y), terms=False)),
            "line": safe_html(JS.settle(GL.apply(rep.year_line(y)))), "months": safe_html(JS.settle(GL.apply(rep.best_months_phrase(y)))) if y in (now.year, now.year + 1) else "",
            "age": c.age(y), "adv": _adv(rep, y)}


def _adv(rep, y):
    """app1113: 좋은 해엔 '조심', 약한 해엔 '보완' 한 줄 (생성기 advice.py 그대로)."""
    try:
        items = rep.yadv(y, "gen", 2)
    except Exception:
        items = []
    if not items:
        k, t = rep.yshort(y); items = [(k, t)]
    seen, out = set(), []
    for k, t in items:
        t = re.sub(r"<[^>]+>", "", t).strip()
        if t and t not in seen:
            seen.add(t); out.append({"kind": k, "text": safe_html(t)})
    return out[:2]


def gen_money(rep):
    """app1113: 손금×사주 재물운이 감정서 생성기와 같은 재물 정점·별점·용신을 쓰도록 넘겨 주는 값."""
    c = rep.c
    inv = {v: k for k, v in c.gel.items()}
    p = rep.best_daeun_money()
    peak = None
    if p:
        peak = {"gz": p["gz"], "ko": p.get("ko") or B.ko(p["gz"]), "a0": p["a0"], "a1": p["a1"], "y0": p["y0"], "y1": p["y1"] - 1,
                "good": c.tone(c.score(p["gz"])[0]) == "good", "phrase": rep.peak_phrase(p)}
    dsc = {}
    for d in c.daeun_periods():
        sc = c.score(d["gz"])[0]
        dsc[d["a0"]] = {"score": round(sc, 2), "star": c.stars(sc), "tone": c.tone(sc)}
    return {"yong_g": inv.get(c.yong), "hee_g": inv.get(c.hee), "gi_g": inv.get(c.gi), "jae_fav": c.fav[c.gel["재성"]],
            "sik_fav": c.fav[c.gel["식상"]], "strong": c.strong, "peak": peak, "no_peak": rep.NO_PEAK + ".",
            "window": rep.money_window().strip(), "ystar": {int(y): rep.ystar[y] for y in rep.years}, "daeun": dsc,
            "job": JB.CUR["job"]}


def _now():
    return datetime.now()


# ------------------------------------------------------------------ 사주
def saju_summary(p: P, palm_spec=None):
    with _GEN_LOCK:
        return _saju_summary(p, palm_spec)


def _saju_summary(p: P, palm_spec=None):
    now = p.now
    args = p.args(palm_spec)
    doc, assets, rep, c = MR.assemble(args, now)
    css = open(os.path.join(GEN_DIR, "assets", "style.css")).read()
    kind = "palm" if palm_spec else "saju"
    rid = _rid(kind, {"p": p.key(), "palm": hashlib.sha256(json.dumps(palm_spec, sort_keys=True).encode()).hexdigest() if palm_spec else None, "day": now.date().isoformat()})
    _store(rid, kind, doc, css, assets)
    k5 = rep.key5(palm_spec)
    from texts import STEM
    st = STEM[c.dm]
    return {
        "rid": rid, "kind": kind, "product": PRODUCTS[kind], "chart": p.chart_key(), "time_rule": p.time_rule,
        "who": rep.who, "gender": p.gender, "solar_date": c.r["solar_date"], "place": p.place_label,
        "date_label": (f"음력 {p.date.replace('-', '.')}{'(윤달)' if p.leap else ''} → 양력 {c.r['solar_date'].replace('-', '.')}" if p.lunar else f"양력 {p.date.replace('-', '.')}")
                      + (f" · {MR.time_label(p.time)}" if p.time else " · 시간 모름"),
        "time_note": p.note or ("태어난 시간을 몰라 시주 없이 여섯 글자로 봤어요." if not p.time else None),
        "pillars": _pillars(c),
        "elements": c.cnt, "day_master": {"ch": c.dm, "ko": st["ko"], "title": st["title"], "img": st["img"], "el": c.dm_el},
        "yong": c.yong, "hee": c.hee, "gyeok": c.gyeok, "strength": c.st_label,
        "key3": [{"title": safe_html(JS.settle(GL.apply(t, terms=False))), "text": safe_html(JS.settle(GL.apply(d.replace(" __PALM_KEY2__", ""))))} for t, d in (k5[0], k5[1], k5[3])],
        "years": [_year_card(rep, y, now) for y in (now.year, now.year + 1)],
        "decade": [{"year": y, "star": rep.ystar[y]} for y in rep.years],
        "job": p.job, "money_gen": gen_money(rep),
        "locked": ["성격·재물 그릇 상세", "직업·연애(배우자)·건강", "대운 10년 흐름", f"{now.year}년 남은 달 · {now.year + 1}년 월별 운세",
                   "10년 시기표(좋은 해·지킬 해)", "용신 개운법(색·방향·숫자)"] + (["손금 6대 선 × 사주 교차 풀이", "손금 유년법 타임라인"] if palm_spec else []),
    }


class SajuReq(BaseModel):
    birth: BirthIn
    unlock: Optional[str] = None


@router.post("/api/v2/saju")
def api_saju(req: SajuReq):
    _gc()
    p = P(req.birth, _now())
    out = saju_summary(p)
    out.pop("money_gen", None)
    out["unlocked"] = _unlock_ok(out["rid"], req.unlock)
    return clean(out)


# ------------------------------------------------------------------ 궁합
class GunghapReq(BaseModel):
    a: BirthIn
    b: BirthIn
    unlock: Optional[str] = None


@router.post("/api/v2/gunghap")
def api_gunghap(req: GunghapReq):
    _gc()
    now = _now()
    pa, pb = P(req.a, now), P(req.b, now)
    if pa.gender == pb.gender:
        raise HTTPException(400, "결혼 궁합은 남녀 한 분씩 넣어 주세요")
    F, M = (pa, pb) if pa.gender == "F" else (pb, pa)
    ns = Namespace()
    for pre, x in (("f", F), ("m", M)):
        for k, v in (("name", x.name), ("date", x.date), ("lunar", x.lunar), ("leap", x.leap), ("time", x.t1), ("time2", x.t2),
                     ("place", x.place_arg), ("place_label", x.place_label)):
            setattr(ns, f"{pre}_{k}", v)
    with _GEN_LOCK:   # app1113: 궁합은 직업 구분 없이 생성기 원래 문장으로 (조립·요약 모두 잠금 안에서)
        JB._restore(); JB.CUR["job"] = "미정"
        return _gunghap_out(req, F, M, ns, now)


def _gunghap_out(req, F, M, ns, now):
    doc, css, G = MG.assemble_gunghap(ns, now)
    rid = _rid("gunghap", {"f": F.key(), "m": M.key(), "t2": [F.t2, M.t2], "day": now.date().isoformat()})
    _store(rid, "gunghap", doc, css)
    k5 = G.key5()
    best, _ = G.best_years()

    def person(x, Pp):
        return {"who": Pp.who, "gender": x.gender, "pillars": _pillars(Pp.c), "elements": Pp.c.cnt,
                "day_master": {"ch": Pp.c.dm, "el": Pp.c.dm_el}, "place": x.place_label, "label": Pp.dlabel(), "note": x.note}
    out = {
        "rid": rid, "kind": "gunghap", "product": PRODUCTS["gunghap"],
        "score": G.total, "grade": G.grade(),
        "f": person(F, G.F), "m": person(M, G.M),
        "key3": [{"title": safe_html(JS.settle(GL.apply(t, terms=False))), "text": safe_html(JS.settle(GL.apply(d)))} for t, d in (k5[0], k5[1], k5[3])],
        "items": [{"name": n, "max": mx, "score": sc} for n, mx, sc, _ in G.score_items],
        "best_years": [{"year": y, "gz": E.year_gz(y)} for y in best[:3]],
        "both_good": G.both_good,
        "locked": ["8항목 점수 근거", "배우자궁·띠·원진·합충 상세", "성격·다툼 포인트·재물 관리·자녀", "대운 비교 · 연도별 관계 신호",
                   "함께 계획하기 좋은 해 · 무난한 달", "함께 조심할 해 · 개운법"],
        "unlocked": False,
    }
    out["unlocked"] = _unlock_ok(rid, req.unlock)
    return clean(out)


# ------------------------------------------------------------------ 손금 (사진 없음: 좌표·특징만)
LINE_KEYS = ("life", "head", "heart", "fate", "sun", "business")
TO_GEN = {"sun": "jaeun", "business": "saup", "fate": "fate", "life": "life", "head": "head", "heart": "heart"}
LUCKY_NAME = {"럭키M": "럭키M", "삼지창": "삼지창", "川자상향선": "川자 상향선", "긴태양선": "긴 태양선", "긴사업선": "긴 사업선",
              "이중생명선": "이중 생명선", "이중두뇌선": "이중 두뇌선", "재물3선": "재물 3선", "금전운": "재운선 여러 가닥", "귀인선": "귀인선"}


class PalmLine(BaseModel):
    pts: list = []
    conf: str = "none"          # high | mid | low | none
    user: bool = False          # 사용자가 직접 고친 선
    double: Optional[list] = None
    extra: Optional[list] = None
    ticks: Optional[list] = None


class PalmReq(BaseModel):
    features: dict
    hand: str = "오른손"
    lines: dict = {}
    landmarks: list = []
    canvas: list = [1000, 1000]
    crop: Optional[list] = None
    birth: Optional[BirthIn] = None
    unlock: Optional[str] = None


def _pts(v, n=600):
    out = []
    for q in (v or [])[:n]:
        if isinstance(q, (list, tuple)) and len(q) >= 2 and all(isinstance(t, (int, float)) and math.isfinite(t) for t in q[:2]):
            out.append([round(float(q[0]), 1), round(float(q[1]), 1)])
    return out


def feats_to_flags(f: dict, lines: dict) -> dict:
    g = lambda k: f.get(k) or {}
    sun, bz, ft, lf, hd, ht = g("sun"), g("business"), g("fate"), g("life"), g("head"), g("heart")
    fl = {}
    if sun.get("presence") in (None, "없음") or lines.get("sun", {}).get("conf") == "none":
        js = "none"
    else:
        js = {"운명선": "from_fate", "월구": "from_moon", "두뇌선": "from_head", "감정선위": "above_heart", "제2화성구": "from_mars",
              "화성평원": "from_plain", "생명선": "from_life"}.get(sun.get("start"), "from_plain")
        if sun.get("start") == "손바닥아래":
            js = "long" if "긴태양선" in (f.get("money_marks") or []) else "from_plain"
    cnt = sun.get("count"); fl["jaeun"] = {"state": js, "count": 3 if cnt == "여러" else int(cnt) if str(cnt).isdigit() else 1}
    pres = lambda v: "none" if v in (None, "없음") else "faint" if v == "약함" else "clear"
    fl["saup"] = {"state": pres(bz.get("presence"))}
    if bz.get("start") == "운명선": fl["saup"]["from"] = "fate"
    fs = pres(ft.get("presence"))
    fl["fate"] = {"state": fs, "start": {"월구": "moon", "손목중앙": "wrist", "생명선": "life", "화성평원": "plain", "두뇌선": "head"}.get(ft.get("start"), "wrist"),
                  "end": {"토성구": "middle_finger", "감정선에서멈춤": "heart", "두뇌선에서멈춤": "head"}.get(ft.get("end"), "heart"),
                  "breaks": "break" if ft.get("form") == "끊김" else "none"}
    fl["life"] = {"length": "short" if lf.get("length") == "짧음" else "long", "venus": "narrow" if lf.get("arc") == "작음" else "wide",
                  "joined_head": lf.get("head_join", "붙음") == "붙음", "double": bool(lf.get("double"))}
    fl["head"] = {"length": {"짧음": "short", "관통": "cross"}.get(hd.get("length"), "long"),
                  "shape": {"직선": "straight", "월구급경사": "moon", "수성구상향": "mercury"}.get(hd.get("direction"), "curve")}
    fl["heart"] = {"clarity": "faint" if ht.get("clarity") in (None, "모름", "약함") else "clear",
                   "end": {"목성구중앙": "jupiter", "목성구기저": "jupiter", "검지중지사이": "index_middle", "토성구": "saturn", "아주짧음": "saturn"}.get(ht.get("end"), "index_middle"),
                   "start": "high" if ht.get("start_height") == "높음" else "low"}
    fl["lucky"] = [LUCKY_NAME[m] for m in (f.get("money_marks") or []) if m in LUCKY_NAME]
    return fl


def palm_spec(req: PalmReq) -> dict:
    lines = {}
    for k in LINE_KEYS:
        v = req.lines.get(k) or {}
        pts = _pts(v.get("pts")); conf = v.get("conf", "none")
        if len(pts) < 2 or conf == "none":
            continue
        faint = conf != "high"
        gk = TO_GEN[k]
        lines[gk] = {"pts": pts, "dashed": faint, **({"label": PM.LABEL[gk] + "(희미)"} if faint else {})}
        if v.get("double"):
            lines[gk + "B"] = {"pts": _pts(v["double"]), "label": False}
        for i, e in enumerate((v.get("extra") or [])[:3]):
            lines[f"{gk}{i + 2}"] = {"pts": _pts(e), "label": False, "dashed": faint}
    ages = []
    for k in LINE_KEYS:
        for t in ((req.lines.get(k) or {}).get("ticks") or [])[:3]:
            pt = _pts([t.get("pt")]) if isinstance(t, dict) else []
            if pt and isinstance(t.get("label"), str):
                ages.append({"pt": pt[0], "label": re.sub(r"[<>&]", "", t["label"])[:12], "offset": [90, -50]})
    cw, ch = (_pts([req.canvas]) or [[1000, 1000]])[0]
    crop = _pts([req.crop[:2], req.crop[2:4]]) if req.crop and len(req.crop) == 4 else []
    spec = {"photo": None, "hand": req.hand if req.hand in ("오른손", "왼손") else "오른손", "both_hands": False,
            "canvas": [cw, ch], "crop": [*crop[0], *crop[1]] if len(crop) == 2 else [0, 0, cw, ch],
            "silhouette": _pts(req.landmarks, 21) if len(req.landmarks) == 21 else [],
            "lines": lines, "ages": ages[:6], "flags": feats_to_flags(req.features, req.lines)}
    return spec


@router.post("/api/v2/palm")
def api_palm(req: PalmReq):
    if not PALM_ENABLED:
        raise HTTPException(404, "준비 중인 기능이에요")
    _gc()
    feats = {k: v for k, v in (req.features or {}).items() if k != "_measure"}
    feats["hand"] = req.hand
    now = _now()
    p = P(req.birth, now) if req.birth else None
    r = None
    if p:
        r = I.calc(p.date, lunar=p.lunar, leap=p.leap, time=p.time, gender=p.gender, place=p.place_arg,
                   seun_from=now.year, seun_to=now.year + 9)
    groups = None
    if r:
        groups = {k: 0 for k in I.GROUP_OFFSET}
        for k, v in r["ten_gods_count"].items():
            groups[I.GROUP_OF[k]] += v
    res = PR.interpret(feats, groups)
    if not res.get("valid"):
        raise HTTPException(400, res.get("retry_tip") or "손금 특징을 확인해 주세요")
    res["lines"] = [l for l in res["lines"] if l["name"] != "결혼선"]
    summ = saju_summary(p, palm_spec(req)) if p else None   # app1113: 생성기 별점·용신·재물 정점을 손금 풀이에도 씀
    six = PS.build(res["features"] | {"money_marks": feats.get("money_marks") or [], "sun_band": feats.get("sun_band") or ""}, res, r,
                   gen=summ["money_gen"] if summ else None, job=p.job if p else "미정")
    out = {"kind": "palm", "hand": req.hand, "money": six["money"], "sections": six["sections"],
           "lines": [{"name": l["name"], "observed": l.get("observed"), "meaning": l.get("meaning"), "score": l.get("score")} for l in res["lines"]],
           "product": PRODUCTS["palm"], "rid": None, "unlocked": False}
    if p:
        out.update({"rid": summ["rid"], "saju": {k: summ[k] for k in ("who", "gender", "pillars", "key3", "years", "decade", "date_label", "place", "time_note",
                                                                         "elements", "day_master", "yong", "hee", "gyeok", "strength")},
                    "locked": ["손금 6대 선 × 사주 교차 풀이 전체", "돈 들어오는 시기(재운선 × 대운·세운)", "손금 유년법 타임라인"] + [x for x in summ["locked"] if "손금" not in x]})
        out["advice"] = PS.advice(res["features"], r, summ["years"], job=p.job)
        out["pairs"] = PS.pairs(r, now.date() if hasattr(now, "date") else None, job=p.job)
        out["unlocked"] = _unlock_ok(summ["rid"], req.unlock)
    # 무료: 재물운 한 줄 + 대박손금 표식 + 선별 한 줄 / 잠금: 돈 들어오는 시기·선별 상세·사주 교차
    m = out["money"]
    out["free"] = {"headline": m.get("headline"), "stars": m.get("stars"), "badges": m.get("badges", []), "palm": (m.get("palm") or [])[:2]}
    if not out["unlocked"]:
        out["money"] = {"locked": True, "has_saju": m.get("has_saju")}
        out["sections"] = [{"title": s["title"], "lines": s.get("lines", []), "locked": True} for s in out["sections"]]
    return clean(out)


# ------------------------------------------------------------------ 결제 자리(placeholder) · 감정서 보기/받기
class PurchaseReq(BaseModel):
    rid: str
    product: str
    token: str                    # Google Play purchaseToken (연동 후) / 개발용 "DEV-UNLOCK"
    owns: list = []               # tier1115: 이 기기에 저장된 소유 토큰(업그레이드 확인용)


@router.post("/api/v2/purchase")
def api_purchase(req: PurchaseReq):
    if not re.fullmatch(r"[a-z0-9]{8,40}", req.rid) or not (CACHE / req.rid).exists():
        raise HTTPException(404, "감정서를 다시 만들어 주세요")
    if req.product in TIER_PRODUCT_IDS:   # tier1115: 주제 심층 · 프리미엄 · 차액 업그레이드
        return _tier_purchase(req)
    if req.product not in {v["id"] for v in PRODUCTS.values()}:
        raise HTTPException(400, "상품을 확인해 주세요")
    if req.product == PRODUCTS["saju"]["id"]:   # free1115: 사주 종합 감정서는 주제 심층·프리미엄으로 바뀌었어요
        raise HTTPException(403, FREE_MSG)
    if DEV_UNLOCK and req.token == "DEV-UNLOCK":
        return {"ok": True, "unlock": _sign("unlock:" + req.rid), "mode": "dev"}
    # TODO(Play 결제): Google Play Developer API purchases.products.get 으로 purchaseToken 확인 → 소비(consume) 처리
    raise HTTPException(402, "결제 연동을 준비 중이에요")


FREE_MSG = "무료는 화면의 사주 요약까지예요. 감정서(보기·PDF)는 주제 심층 2,900원부터 열려요."


def _rdir(rid):
    if not re.fullmatch(r"[a-z0-9]{8,40}", rid):
        raise HTTPException(404)
    d = CACHE / rid
    if not d.exists():
        raise HTTPException(404, "감정서 보관 기간(24시간)이 지났어요. 다시 만들어 주세요")
    try:   # free1115: 무료 등급 감정서는 보기·PDF·자료 모두 막아요(예전에 만들어 둔 것도)
        meta = json.loads((d / "meta.json").read_text())
    except Exception:
        meta = {}
    if (meta.get("kind") == "tier" and meta.get("tier") not in TIER_PAID) or meta.get("kind") == "saju":
        raise HTTPException(403, FREE_MSG)   # 'saju' = 무료 화면 요약과 함께 만들어지는 예전 종합 감정서(이제 팔지 않아요)
    return d


@router.get("/api/v2/report/{rid}/report.html")
def report_view(rid: str, u: str = Query("")):
    d = _rdir(rid)
    if not _unlock_ok(rid, u):
        raise HTTPException(402, "전체 감정서는 잠금 해제 후 볼 수 있어요")
    doc = d.joinpath("report.html").read_text()
    fit = getattr(MR, "VIEW_FIT_JS", "")   # sync1114: 화면에서도 PDF처럼 넘친 쪽을 나누고 살짝 축소 (잘림 방지)
    if fit and "</body>" in doc:
        doc = doc.replace("</body>", fit + "</body>", 1)
    return HTMLResponse(doc, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})


@router.get("/api/v2/report/{rid}/{asset}")
def report_asset(rid: str, asset: str):
    d = _rdir(rid)
    if asset not in ("style.css", "palm_overlay.jpg"):
        raise HTTPException(404)
    return FileResponse(d / asset, headers={"Cache-Control": "no-store"})


@router.get("/api/v2/report/{rid}.pdf")
async def report_pdf(rid: str, u: str = Query("")):
    d = _rdir(rid)
    if not _unlock_ok(rid, u):
        raise HTTPException(402, "PDF는 잠금 해제 후 받을 수 있어요")
    pdf = d / "report.pdf"
    if not pdf.exists():
        # 앱 보기용 CSS 없이 인쇄용으로 렌더
        await MR.render(str(d / "report.html"), str(pdf))
    kind = json.loads((d / "meta.json").read_text())["kind"]
    meta = json.loads((d / "meta.json").read_text())
    fname = {"saju": "sonmyeongri_saju.pdf", "gunghap": "sonmyeongri_gunghap.pdf", "palm": "sonmyeongri_saju_palm.pdf"}.get(kind) or f"sonmyeongri_{meta.get('tier', 'report')}.pdf"
    return FileResponse(pdf, media_type="application/pdf", filename=fname, headers={"Cache-Control": "no-store"})


@router.get("/api/v2/places")
def api_places():
    return {"regions": [{"region": r, "places": [n for n, _ in items]} for r, items in PK.REGIONS]}


@router.get("/api/v2/config")
def api_config():
    prods = PRODUCTS if PALM_ENABLED else {k: v for k, v in PRODUCTS.items() if k != "palm"}
    return {"products": prods, "dev_unlock": DEV_UNLOCK, "keep_hours": KEEP_HOURS, "palm_enabled": PALM_ENABLED,
            "tiers": TIERS, "topics": [{"key": k, "ko": TP.KO[k], "title": TP.TITLE[k], "partner": k == "gunghap"} for k in TP.TOPICS]}


@router.get("/flags.js")
def flags_js():
    """nopalm1113: 화면이 쓰는 기능 스위치. index.html·privacy.html 맨 위에서 먼저 읽어요."""
    on = "true" if PALM_ENABLED else "false"
    js = f"window.PALM_ENABLED={on};document.documentElement.classList.toggle('palm-on',{on});document.documentElement.classList.toggle('palm-off',!{on});"
    return Response(js, media_type="application/javascript", headers={"Cache-Control": "no-cache"})


# ------------------------------------------------------------------ tier1115: 등급별 감정서 (기본 무료 · 주제 심층 2,900원 · 프리미엄 9,900원)
TIERS = {
    "free": {"id": None, "price": 0, "title": "사주 요약 (화면)", "pages": "화면 요약 · PDF 없음", "report": False,   # free1115
             "incl": ["네 기둥(원국)과 오행", "일간·신강약·격국·용신", "핵심 3가지", "올해·내년 흐름 한 줄", "앞으로 10년 별점"]},
    "focus": {"id": "focus_2900", "price": 2900, "title": "주제 심층 감정서 · 주제 2개", "pages": "9~10쪽",
              "incl": ["사주 바탕(명식·오행·성격·용신·올해 운세)", "고른 주제 2개: 타고난 바탕 · 대운 10년 · 해마다 조심/보완 · 힘이 실리는 해와 조심할 해", "개운법"]},
    "premium": {"id": "premium_9900", "price": 9900, "title": "프리미엄 감정서 · 전체 주제", "pages": "22~23쪽",
                "incl": ["용신·격국 풀이 · 성격", "대운 10년 흐름 · 대운 × 주제 표", "돈·직업·사업·결혼·이사·건강·자녀 7개 주제 (상대 정보를 넣으면 궁합까지)",
                         "올해·내년 월별 운세", "개운법"]},
}
UPGRADE = {"id": "upgrade_7000", "price": 7000, "title": "프리미엄으로 올리기 · 차액", "from": "focus_2900", "to": "premium_9900"}
TIER_PRODUCT_IDS = {"focus_2900": "focus", "premium_9900": "premium", "upgrade_7000": "premium"}
TIER_PAID = ("focus", "premium")   # free1115: 감정서(보기·PDF)는 유료 등급만


def _topics_key(topics):
    return "+".join(sorted(topics)) if topics else "-"


def _own_token(tier, chart, topics):
    """소유 토큰 own.<등급>.<사주키>.<주제>.<서명> — 기기에 저장, 서버 비밀키로만 만들 수 있어요."""
    tk = _topics_key(topics if tier == "focus" else [])
    msg = f"own.{tier}.{chart}.{tk}"
    return msg + "." + _sign("own:" + msg)[:20]


def _owns(tokens, chart):
    """이 사주(chart)에 대해 확인된 소유: {('focus', 'money+job'), ('premium', '-')}"""
    out = set()
    for t in (tokens or [])[:40]:
        if not isinstance(t, str): continue
        parts = t.split(".")
        if len(parts) != 5 or parts[0] != "own": continue
        msg = ".".join(parts[:4])
        if parts[2] == chart and parts[1] in ("focus", "premium") and hmac.compare_digest(parts[4], _sign("own:" + msg)[:20]):
            out.add((parts[1], parts[3]))
    return out


def _covers(owns, tier, topics):
    if tier not in TIER_PAID: return False   # free1115: 무료는 감정서를 열지 않아요
    if ("premium", "-") in owns: return True        # 프리미엄을 산 사주는 주제 심층도 모두 열려요
    return tier == "focus" and ("focus", _topics_key(topics)) in owns


def _offer(owns, tier, topics):
    """지금 사야 할 상품 — 주제 심층을 이미 산 사주가 프리미엄을 고르면 차액 7,000원만"""
    if _covers(owns, tier, topics): return None
    if tier == "premium" and any(k == "focus" for k, _ in owns):
        return {**UPGRADE, "pages": TIERS["premium"]["pages"], "full_price": TIERS["premium"]["price"]}
    t = TIERS[tier]
    return {"id": t["id"], "price": t["price"], "title": t["title"], "pages": t["pages"]}


class TierReq(BaseModel):
    birth: BirthIn
    tier: str = "free"                # free | focus | premium
    topics: list = []                 # focus: 정확히 2개 (money job biz love move gunghap health kids 또는 한글)
    partner: Optional[BirthIn] = None # 궁합 주제(또는 프리미엄 궁합)에 필요
    owns: list = []                   # 기기에 저장된 소유 토큰


@router.post("/api/v2/hour_check")
def api_hour_check(b: BirthIn):
    """tier1115: 출생 시각이 시(時)의 경계 근처라 경도 보정과 30분 관례의 시주가 달라지면 두 가지를 보여 줘요."""
    p = P(b, _now())
    if not p.time:
        return {"differ": False}
    def hour(rule):
        r = E.run_saju(p.date, p.time, p.lunar, p.leap, p.gender, p.calc_place(rule), p.now.year, p.now.year)
        hp = next(x for x in r["pillars"] if x["name"] == "시")
        lt = r["time_correction"]["local_solar_time"][-5:]
        return {"gz": hp["gz"], "ko": hp["ko"], "local": lt}
    a, c = hour("경도"), hour("30분")
    if a["gz"] == c["gz"]:
        return {"differ": False, "gz": a["gz"]}
    return {"differ": True, "options": [
        {"rule": "경도", "gz": a["gz"], "ko": a["ko"], "local": a["local"], "default": True,
         "title": f"출생지 경도로 보정 · {a['gz']}({a['ko']})시", "desc": f"{p.place_label} 경도로 실제 태양 시각({a['local']})을 계산해요. 이 앱의 기본이에요."},
        {"rule": "30분", "gz": c["gz"], "ko": c["ko"], "local": c["local"], "default": False,
         "title": f"흔한 만세력 방식 · {c['gz']}({c['ko']})시", "desc": f"표준시에서 30분을 빼는 관례({c['local']})예요. 다른 만세력과 맞춰 보고 싶을 때 골라요."}]}


@router.post("/api/v2/tier")
def api_tier(req: TierReq):
    _gc()
    now = _now()
    p = P(req.birth, now)
    tier = req.tier if req.tier in TIERS else None
    if not tier:
        raise HTTPException(400, "등급을 확인해 주세요")
    if tier not in TIER_PAID:   # free1115: 무료 감정서는 만들지도 보관하지도 않아요
        raise HTTPException(403, FREE_MSG)
    try:
        topics = TP.parse_topics(",".join(str(x) for x in (req.topics or [])))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if tier == "focus" and len(topics) != 2:
        raise HTTPException(400, "주제를 정확히 2개 골라 주세요")
    if tier != "focus":
        topics = []
    pt = None
    if req.partner and (tier == "premium" or "gunghap" in topics):
        pt = P(req.partner, now)
        if pt.gender == p.gender:
            raise HTTPException(400, "궁합은 남녀 두 사람 기준의 전통 이론이라, 상대의 성별을 확인해 주세요")
    if "gunghap" in topics and not pt:
        raise HTTPException(400, "궁합을 고르면 상대의 생년월일을 넣어 주세요")
    kw = dict(tier=tier, topics=",".join(topics))
    if pt:
        kw.update(partner_name=pt.name, partner_gender=pt.gender, partner_date=pt.date, partner_time=pt.time, partner_place=pt.place_arg,
                  partner_place_label=pt.place_label, partner_lunar=pt.lunar, partner_leap=pt.leap)
    chart = p.chart_key()
    with _GEN_LOCK:
        try:
            doc, assets, rep, c = MR.assemble(p.args(**kw), now)
        except ValueError as e:
            raise HTTPException(400, str(e))
        finally:
            JB.apply("미정")
    css = open(os.path.join(GEN_DIR, "assets", "style.css")).read()
    rid = _rid("tier", {"p": p.key(), "k": kw, "pt": pt.key() if pt else None, "day": now.date().isoformat()})
    _store(rid, "tier", doc, css, assets)
    (CACHE / rid / "meta.json").write_text(json.dumps({"kind": "tier", "tier": tier, "topics": topics, "chart": chart, "created": time.time()}))
    owns = _owns(req.owns, chart)
    unlocked = _covers(owns, tier, topics)
    out = {"rid": rid, "tier": tier, "topics": topics, "topics_ko": [TP.KO[t] for t in topics], "chart": chart,
           "title": TIERS[tier]["title"], "pages": TIERS[tier]["pages"], "unlocked": unlocked,
           "unlock": _sign("unlock:" + rid) if unlocked else None, "offer": _offer(owns, tier, topics)}
    return clean(out)


def _tier_purchase(req):
    meta = json.loads((CACHE / req.rid / "meta.json").read_text())
    if meta.get("kind") != "tier":
        raise HTTPException(400, "상품을 확인해 주세요")
    tier, topics, chart = meta["tier"], meta.get("topics") or [], meta["chart"]
    if TIER_PRODUCT_IDS[req.product] != tier:
        raise HTTPException(400, "고른 감정서와 상품이 달라요")
    owns = _owns(req.owns, chart)
    if req.product == "upgrade_7000" and not any(k == "focus" for k, _ in owns):
        raise HTTPException(400, "차액 업그레이드는 이 사주로 주제 심층을 산 기록이 있어야 해요")
    if DEV_UNLOCK and req.token == "DEV-UNLOCK":
        own = _own_token(tier, chart, topics)
        return {"ok": True, "unlock": _sign("unlock:" + req.rid), "own": own, "chart": chart, "mode": "dev"}
    # TODO(Play 결제): billing_todo_ko.md(출시 문서) — purchaseToken을 Play Developer API로 확인 → 사주키와 묶어 기록 → 소비(consume)
    raise HTTPException(402, "결제 연동을 준비 중이에요")
