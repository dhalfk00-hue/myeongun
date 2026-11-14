# -*- coding: utf-8 -*-
"""한글 조사 선택: 받침(종성)에 따라 을/를, 이/가, 은/는, 와/과, 으로/로 등을 고릅니다.
한자(木→목, 火→화 등), 괄호 안 독음, 숫자·라틴 문자, HTML 태그를 고려합니다.
"""
import re

# 조사 쌍: 앞이 받침 있을 때, 뒤가 없을 때. 으로/로는 ㄹ 받침이면 '로'.
PAIRS = {
    "을": ("을", "를"), "를": ("을", "를"), "을를": ("을", "를"),
    "이": ("이", "가"), "가": ("이", "가"), "이가": ("이", "가"),
    "은": ("은", "는"), "는": ("은", "는"), "은는": ("은", "는"),
    "과": ("과", "와"), "와": ("과", "와"), "와과": ("과", "와"), "과와": ("과", "와"),
    "으로": ("으로", "로"), "로": ("으로", "로"), "으로로": ("으로", "로"),
    "이에요": ("이에요", "예요"), "예요": ("이에요", "예요"),
    "이라": ("이라", "라"), "라": ("이라", "라"),
    "이고": ("이고", "고"), "고": ("이고", "고"),
    "이면": ("이면", "면"), "면": ("이면", "면"),
}

# 이 앱에서 자주 쓰는 한자 → 한글 독음
HANJA = {
    "木": "목", "火": "화", "土": "토", "金": "금", "水": "수",
    "甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무",
    "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계",
    "子": "자", "丑": "축", "寅": "인", "卯": "묘", "辰": "진", "巳": "사",
    "午": "오", "未": "미", "申": "신", "酉": "유", "戌": "술", "亥": "해",
    "命": "명", "式": "식", "身": "신", "弱": "약", "強": "강", "强": "강",
    "格": "격", "用": "용", "神": "신", "喜": "희", "庫": "고",
    "大": "대", "運": "운", "年": "년", "月": "월", "日": "일", "時": "시",
    "陰": "음", "陽": "양",
}

# 숫자 끝자리 독음 (3을, 2를)
DIGIT = {"0": "영", "1": "일", "2": "이", "3": "삼", "4": "사",
         "5": "오", "6": "육", "7": "칠", "8": "팔", "9": "구"}
# 알파벳 한국어 명칭의 마지막 글자
LATIN = {
    "A": "이", "B": "비", "C": "씨", "D": "디", "E": "이", "F": "프",
    "G": "지", "H": "치", "I": "이", "J": "이", "K": "이", "L": "엘",
    "M": "엠", "N": "엔", "O": "오", "P": "피", "Q": "큐", "R": "알",
    "S": "스", "T": "티", "U": "유", "V": "이", "W": "유", "X": "스",
    "Y": "이", "Z": "트",
}

_TAG = re.compile(r"<[^>]+>")
_TRAIL = re.compile(r"[\s\"'“”‘’·,.\-–—~/!?:;]+$")


def _jong(hangul_char):
    """한글 음절의 종성 인덱스(0=없음, 8=ㄹ). 한글이 아니면 None."""
    o = ord(hangul_char)
    if 0xAC00 <= o <= 0xD7A3:
        return (o - 0xAC00) % 28
    return None


def _reading_char(ch):
    """한 글자를 한글 음절로 환산. 못 하면 None."""
    if not ch:
        return None
    if "가" <= ch <= "힣":
        return ch
    if ch in HANJA:
        return HANJA[ch]
    if ch.isdigit():
        return DIGIT.get(ch)
    if ch.isalpha() and ch.upper() in LATIN:
        return LATIN[ch.upper()]
    return None


def last_hangul(word):
    """조사 판단에 쓰는 마지막 한글 음절. HTML·구두점·괄호 독음을 반영합니다."""
    s = _TAG.sub("", "" if word is None else str(word))
    s = _TRAIL.sub("", s)
    if not s:
        return "가"
    # 끝에 괄호가 있으면 괄호 앞 낱말로 판단 (fix1113: 흙(토)이, 3월(癸卯)과, 강약(억부)을)
    # 괄호 앞에 읽을 글자가 없을 때만 괄호 안 독음을 씀
    if s.endswith(")"):
        # 짝이 맞는 여는 괄호를 찾음 (재성(돈, 토(土)) → '재성')
        depth = 0; i = -1
        for k in range(len(s) - 1, -1, -1):
            if s[k] == ")": depth += 1
            elif s[k] == "(":
                depth -= 1
                if depth == 0: i = k; break
        if i >= 0:
            inner = s[i + 1:-1].strip()
            outer = _TRAIL.sub("", s[:i])
            if outer and any(_reading_char(ch) for ch in outer):
                s = outer
            elif inner:
                h = last_hangul(inner)
                if h:
                    return h
                s = outer
    for ch in reversed(s):
        r = _reading_char(ch)
        if r:
            return r[-1] if len(r) >= 1 and "가" <= r[-1] <= "힣" else r
    return "가"


def jongseong(word):
    """마지막 음절의 종성 인덱스. 0이면 받침 없음."""
    h = last_hangul(word)
    j = _jong(h)
    return 0 if j is None else j


def has_batchim(word):
    return jongseong(word) != 0


def particle(word, pair="을"):
    """받침에 맞는 조사만 반환. pair는 '을'/'를'/'을를', '으로'/'로', '이에요' 등."""
    key = pair if pair in PAIRS else None
    if key is None:
        raise ValueError(f"unknown josa pair: {pair!r}")
    with_b, no_b = PAIRS[key]
    j = jongseong(word)
    if key in ("으로", "로", "으로로"):
        # 받침 없거나 ㄹ이면 '로', 그 외 받침은 '으로'
        return no_b if j == 0 or j == 8 else with_b
    return with_b if j else no_b


def josa(word, pair="을", attach=True):
    """기본은 단어+조사. josa('큰 산','를')→'큰 산을'.
    구형 호출 josa(word, '을', '를')도 지원합니다(세 번째 인자가 반대 조사).
    attach=False 이면 조사만 반환(palm_rules.josa 와 같음).
    """
    if attach not in (True, False) and isinstance(attach, str) and attach in PAIRS.get(pair, ()):
        # josa(word, a, b) 구형: 받침 있으면 a, 없으면 b
        a, b = pair, attach
        return str(word) + (a if has_batchim(word) else b)
    p = particle(word, pair)
    return (str(word) + p) if attach else p


# 후처리: 변수 뒤에 조사가 어색하게 붙은 자리만 고칩니다.
# 모든 한글 어미(하는·있는)를 건드리지 않고, 괄호·태그·조사 오용 패턴만 고칩니다.
_PARTS = "이에요|예요|으로|이라|을|를|이|가|은|는|와|과|로|이고|고"
_FIX = re.compile(
    r"(?P<stem>"
    r"[가-힣A-Za-z0-9一-龥]+(?:\([^)]{0,20}\))?"
    r"|</(?:span|b|strong)>"
    r")"
    r"(?P<josa>" + _PARTS + r")"
    r"(?=(?:[\s,.!?·<>]|</|$))"
)


def _stem_for(m_stem, full_text, start):
    """앞쪽에 닫는 태그가 있으면 태그 안의 단어를 조사 판단에 씁니다."""
    stem = m_stem
    if stem.startswith("</"):
        # 직전 태그 내용을 찾음
        before = full_text[:start]
        tag = stem[2:-1]  # span / b / strong
        open_re = re.compile(rf"<{tag}(?:\s[^>]*)?>([^<]*)$")
        om = open_re.search(before)
        if om:
            return om.group(1)
        # 태그 여러 겹이면 그냥 앞 텍스트의 마지막 단어
        txt = _TAG.sub("", before)
        return txt[-20:]
    return stem


def fix_josa(text):
    """HTML/문장에서 잘못된 조사를 받침에 맞게 고칩니다.
    '하는' 같은 용언 어미는 건드리지 않고, 괄호·한자·태그 뒤와 을/를 오용을 중심으로 고칩니다.
    """
    if not text:
        return text

    def should_touch(stem, jo):
        # 용언 어미로 자주 쓰이는 은/는/이/가/와/과/로 는
        # 괄호·한자·태그·짧고 명사인 어간일 때만 고침
        if stem.startswith("</") or "(" in stem:
            return True
        if any(ch in HANJA or ("가" <= ch <= "힣") and False for ch in stem):
            pass
        if any(ch in HANJA for ch in stem):
            return True
        # 을/를은 목적격이라 오용이 거의 항상 오류
        if jo in ("을", "를"):
            return True
        # 한 글자 오행·천간 독음
        core = re.sub(r"\([^)]*\)$", "", stem)
        if core in ("목", "화", "토", "금", "수", "산", "불", "흙", "쇠", "물", "나무",
                    "갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"):
            return True
        if core.endswith("님"):
            return True
        return False

    PROTECT = {"물가", "불가", "물로", "불로"}  # 낱말 자체(물가 산책 등)는 건드리지 않음

    def repl(m):
        stem, jo = m.group("stem"), m.group("josa")
        if stem + jo in PROTECT:
            return m.group(0)
        if not should_touch(stem, jo):
            return m.group(0)
        word = _stem_for(stem, text, m.start())
        try:
            right = particle(word, jo)
        except ValueError:
            return m.group(0)
        if right == jo:
            return m.group(0)
        return stem + right

    return _FIX.sub(repl, text)


if __name__ == "__main__":
    cases = [
        ("큰 산", "를", "큰 산을"),
        ("화", "을", "화를"),
        ("火", "을", "火를"),
        ("불(화)", "이", "불(화)이"),
        ("흙(토)", "이", "흙(토)이"),
        ("나무(목)", "이", "나무(목)가"),
        ("3월(癸卯)", "과", "3월(癸卯)과"),
        ("강약(억부)", "을", "강약(억부)을"),
        ("(-32.6분)", "로", "(-32.6분)으로"),
        ("재성(돈, 토(土))", "이", "재성(돈, 토(土))이"),
        ("목(木)", "로", "목(木)으로"),
        ("목(木)", "이", "목(木)이"),
        ("토(土)", "이", "토(土)가"),
        ("신약", "이라", "신약이라"),
        ("양인격", "이에요", "양인격이에요"),
        ("곡선", "은", "곡선은"),
        ("뚜렷하지 않음", "이에요", "뚜렷하지 않음이에요"),
        ("감정선 위", "이에요", "감정선 위예요"),
        ("고객님", "은", "고객님은"),
        ("홍길동님", "가", "홍길동님이"),
        ("0.0", "로", "0.0으로"),
        ("3.05", "로", "3.05로"),
        ("서울", "로", "서울로"),  # ㄹ 받침
        ("길", "로", "길로"),
        ("집", "로", "집으로"),
        ("수(水)", "과", "수(水)와"),
        ("금(金)", "과", "금(金)과"),
        ("세", "이", "세가"),
        ("재성", "이", "재성이"),
        ("식신", "이", "식신이"),
        ("편재", "이", "편재가"),
    ]
    bad = 0
    for w, p, want in cases:
        got = josa(w, p)
        ok = got == want
        if not ok:
            bad += 1
            print("FAIL", repr(w), p, "got", got, "want", want,
                  "hangul", last_hangul(w), "jong", jongseong(w))
    # fix_josa
    fx = [
        ("묵직하게 버티는 큰 산를 닮은", "묵직하게 버티는 큰 산을 닮은"),
        ("<b>화을 먼저 씁니다</b>", "화를 먼저 씁니다"),
        ("원국에 불(화)이 가중", "원국에 불(화가 가중"),  # wait - 불(화)이 → 불(화)가
        ("수(水)과 금(金)이", "수(水)와 금(金)이"),
        ("희신은 목(木)</span>로 봐요", "희신은 목(木)</span>으로 봐요"),
        ("하는 일은", "하는 일은"),  # do not touch 하는
        ("있는 사주", "있는 사주"),
        ("토(土)이 가장", "토(土)가 가장"),
    ]
    # correct expected for 불(화)
    fx[2] = ("원국에 불(화)가 가중", "원국에 불(화)이 가중")
    fx.append(("수영·물가 산책", "수영·물가 산책"))
    fx.append(("흙(토)가 가장", "흙(토)이 가장"))
    for src, want in fx:
        got = fix_josa(src)
        if want not in got and got != want:
            # allow exact
            if got != want:
                bad += 1
                print("FIX FAIL", repr(src), "->", repr(got), "want", repr(want))
    print("failures", bad, "of", len(cases)+len(fx))
