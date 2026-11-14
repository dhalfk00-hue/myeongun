# -*- coding: utf-8 -*-
"""q1113: 사람마다 다른 운 조언 — '그해 글자'가 아니라 '이 사주와 그해 글자의 관계'로 고르는 규칙 엔진.

같은 2027년(丁未)이라도
 - 그 글자가 이 사주에 용신·희신·중립·구신·기신 중 무엇인지 (천간·지지 따로)
 - 신강/중화/신약
 - 일간 기준으로 어떤 십신이 들어오는지 (정재/편재 …)
 - 일지(배우자·생활)·월지(일의 환경)·년지(집안·부모)·시지(자녀·미래)와의 합·충·형·파·해·원진
 - 지금 대운이 받쳐 주는지(세운과 대운이 겹치는지·부딪히는지)
 - 원국에 없던 오행이 오는지 / 이미 넘치는 오행이 더해지는지
 - 성별(여성 관성·남성 재성), 직업 상황(jobs.W)
을 보고 문장을 조합해요. 무작위가 아니라 규칙과 사주 특징으로 고르기 때문에 같은 입력은 늘 같은 결과예요.
해석은 자평명리 억부·조후·궁위·형충회합의 일반적인 풀이를 따랐어요. 결혼 시기는 말하지 않아요.
"""
import hashlib, re
from texts import STEM, EL_WORD, EL_HAN, ELEM, TG_GROUP, POS
from josa import particle

BR_KO = {"子": "자수", "丑": "축토", "寅": "인목", "卯": "묘목", "辰": "진토", "巳": "사화", "午": "오화", "未": "미토",
         "申": "신금", "酉": "유금", "戌": "술토", "亥": "해수"}
ST_KO = {k: v["ko"] for k, v in STEM.items()}
ROLE = {2: "용신", 1: "희신", 0: "중립 기운", -1: "구신", -2: "기신"}
SPAN = {"year": "해", "daeun": "10년", "month": "달"}
PAL = {"일": "일지(배우자·생활 자리)", "월": "월지(일의 환경 자리)", "년": "년지(집안·부모 자리)", "시": "시지(자녀·미래 자리)"}
GMEAN = {"비겁": "내 편·경쟁", "식상": "재능·표현", "재성": "돈·현실", "관성": "책임·평판", "인성": "배움·도움"}


# ------------------------------------------------------------------ 도우미
_PH = re.compile(r"\{(\w+)(?::(\w+))?\}")


def fill(tpl, **kw):
    """'{boss:와}' 처럼 조사를 붙여 채워요. 받침에 맞게 와/과·을/를·이/가·은/는·으로/로 를 골라요."""
    def rep(m):
        v = str(kw.get(m.group(1), m.group(0)))
        j = m.group(2)
        return v + particle(v, j) if j else v
    return _PH.sub(rep, tpl)


def psig(c):
    if not hasattr(c, "_psig"):
        key = "".join(p["gz"] for p in c.P.values()) + c.gender
        c._psig = int(hashlib.md5(key.encode()).hexdigest()[:12], 16)
    return c._psig


def pick(lst, c, key=""):
    if not lst: return ""
    h = int(hashlib.md5((str(psig(c)) + key).encode()).hexdigest()[:8], 16)
    return lst[h % len(lst)]


def words():
    import jobs as JB
    return JB.W()


def stw(c):
    if c.neutral:
        return "중화이면서 약간 신강한 사주" if c.strong else "중화이면서 약간 신약한 사주"
    return "신강한 사주" if c.strong else "신약한 사주"


def fclass(v):
    return "fav" if v >= 1 else "unf" if v <= -1 else "neu"


# ------------------------------------------------------------------ 1) 십신 그룹 × 이 사주에서의 역할(fav/neu/unf) × 강약 → 원리 문장
# {tg} 들어오는 십신, {span} 해/10년/달, {stw} 강약 문구, {role} 용신/희신/…, 직업 낱말({boss}{work}{income}{peers}{money_move}{expand})
MECH = {
 "비겁": {
  "fav": {"강": ["{tg:이} {role}{role_ro} 오는 {span:이에요}. {stw}에 내 편 기운이 실려 추진력이 붙지만, 그만큼 내 판단만 믿고 밀어붙이기 쉬워요."],
          "약": ["{stw}에 {tg:이} {role}{role_ro} 들어와 기댈 언덕과 내 편이 생기는 {span:이에요}.",
                "{tg:이} {role}{role_ro} 힘을 보태 주는 {span:이라}, 혼자 끌어안던 일을 나눌 사람이 생겨요."]},
  "neu": {"강": ["{stw}에 {tg:이} 더해져 경쟁심과 고집이 함께 커지는 {span:이에요}."],
          "약": ["{tg:이} 들어와 버틸 힘은 생기지만 사람과 모임도 함께 늘어나는 {span:이에요}."]},
  "unf": {"강": ["{stw}에 {tg:이} {role}{role_ro} 겹쳐, 내 몫을 나눠 가져갈 사람과 지출이 늘기 쉬운 {span:이에요}(군겁쟁재).",
                "{tg:이} {role}{role_ro} 오는 {span:이라} 경쟁과 고집이 지나쳐 손에 남는 몫이 줄기 쉬워요."],
          "약": ["{tg:이} {role}{role_ro} 와서 사람 문제로 힘이 분산되기 쉬운 {span:이에요}."]},
 },
 "식상": {
  "fav": {"강": ["{stw}의 넘치는 힘이 {tg}{tg_ro} 흘러나가는 {span:이라} 재능과 결과물이 빛나요.",
                "{tg:이} {role}{role_ro} 와서 쌓아 둔 힘을 밖으로 꺼내기 좋은 {span:이에요}."],
          "약": ["{tg:이} {role}{role_ro} 오지만 {stw:이라}, 재능을 쓰는 만큼 체력도 빨리 닳는 {span:이에요}."]},
  "neu": {"강": ["{tg:이} 들어와 표현하고 벌이고 싶은 마음이 커지는 {span:이에요}."],
          "약": ["{stw}에 {tg:이} 더해져 에너지가 밖으로 많이 새는 {span:이에요}."]},
  "unf": {"강": ["{tg:이} {role}{role_ro} 와서 말실수와 규칙 충돌로 일이 꼬이기 쉬운 {span:이에요}."],
          "약": ["{stw}에 {tg:이} {role}{role_ro} 겹쳐 쓰는 힘이 채우는 힘보다 큰 {span:이에요}.",
                "{tg:이} {role}{role_ro} 오는 {span:이라}, 일을 벌일수록 몸과 마음이 먼저 지치기 쉬워요."]},
 },
 "재성": {
  "fav": {"강": ["{stw:이라} {tg:이} {role}{role_ro} 오면 돈을 다룰 힘이 받쳐 주는 {span:이에요}.",
                "{tg:이} {role}{role_ro} 들어와 넘치는 힘을 돈과 성과로 바꾸기 좋은 {span:이에요}."],
          "약": ["{tg:이} {role}{role_ro} 들어와 돈과 기회가 보이지만, {stw:이라} 다 잡으려 하면 몸이 먼저 지쳐요."]},
  "neu": {"강": ["{tg:이} 들어와 돈과 일이 함께 움직이는 {span:이에요}."],
          "약": ["{stw}에 {tg:이} 더해져 일과 돈 걱정이 함께 늘어나는 {span:이에요}."]},
  "unf": {"강": ["{tg:이} {role}{role_ro} 와서 돈 문제로 부딪히기 쉬운 {span:이에요}."],
          "약": ["{stw}에 {tg:이} {role}{role_ro} 겹쳐, 다뤄야 할 돈과 일이 내 힘보다 커지는 {span:이에요}(재다신약).",
                "{tg:이} {role}{role_ro} 오는 {span:이라} 돈을 쫓을수록 몸과 마음이 지치기 쉬워요."]},
 },
 "관성": {
  "fav": {"강": ["{stw:이라} {tg:이} {role}{role_ro} 오면 책임을 감당할 힘이 있어 인정받기 좋은 {span:이에요}.",
                "{tg:이} {role}{role_ro} 와서 넘치는 힘에 방향과 틀이 잡히는 {span:이에요}."],
          "약": ["{tg:이} {role}{role_ro} 오지만 {stw:이라}, 인정과 함께 부담도 커지는 {span:이에요}."]},
  "neu": {"강": ["{tg:이} 들어와 {boss}의 기대와 책임이 커지는 {span:이에요}."],
          "약": ["{stw}에 {tg:이} 더해져 {boss}의 압박과 책임감에 스스로를 몰아붙이기 쉬운 {span:이에요}."]},
  "unf": {"강": ["{tg:이} {role}{role_ro} 와서 책임이 압박으로 바뀌기 쉬운 {span:이에요}."],
          "약": ["{stw}에 {tg:이} {role}{role_ro} 겹쳐 책임과 압박이 내 힘을 넘기 쉬운 {span:이에요}.",
                "{tg:이} {role}{role_ro} 오는 {span:이라} 남의 기대에 맞추느라 몸이 먼저 상하기 쉬워요."]},
 },
 "인성": {
  "fav": {"강": ["{tg:이} {role}{role_ro} 오는 {span:이라} 배움·문서 운이 받쳐 줘요."],
          "약": ["{stw}에 {tg:이} {role}{role_ro} 들어와 나를 받쳐 주는 사람과 자격·문서의 도움이 생기는 {span:이에요}.",
                "{tg:이} {role}{role_ro} 와서 약한 뿌리에 물을 주듯 힘이 차오르는 {span:이에요}."]},
  "neu": {"강": ["{stw}에 {tg:이} 더해져 생각과 준비가 실행보다 길어지는 {span:이에요}."],
          "약": ["{tg:이} 들어와 공부·자격·계약 일이 풀리기 쉬운 {span:이에요}."]},
  "unf": {"강": ["{stw}에 {tg:이} {role}{role_ro} 겹쳐 생각만 많아지고 몸이 무거워지기 쉬운 {span:이에요}.",
                "{tg:이} {role}{role_ro} 오는 {span:이라} 남에게 기대거나 결정을 미루다 기회를 놓치기 쉬워요."],
          "약": ["{tg:이} {role}{role_ro} 와도 도움이 제때 닿지 않기 쉬운 {span:이에요}."]},
 },
}

# 2) 그룹 × 조심(좋을 때) / 보완(나쁠 때) 행동 — 직업 낱말 자리표시
ACT = {
 "비겁": {"caution": ["큰 결정은 믿을 만한 사람 한 명의 반대 의견까지 듣고 정하세요.",
                     "사람이 모이는 만큼 모임·경조사 예산을 먼저 정해 두세요.",
                     "{peers:와} 성과를 다투기보다 역할을 나누면 오히려 자리가 단단해져요."],
          "remedy": ["보증·공동 명의·돈 빌려주기는 이번엔 거절하고, 통장을 용도별로 나눠 새는 돈부터 막으세요.",
                     "돈이 오가는 약속은 금액·기한을 문자로라도 남기세요.",
                     "여러 사람과 엮이는 일은 줄이고 내 일 하나에 힘을 모으세요."]},
 "식상": {"caution": ["지킬 수 있는 만큼만 약속하고, 결과물은 기록으로 남기세요.",
                     "새 일은 손에 든 일 하나를 마무리한 뒤 시작하세요.",
                     "{boss}에게 하는 말은 하루 묵혀서 부드럽게 전하세요."],
          "remedy": ["일정을 평소의 80%만 채우고, 끼니와 잠을 일정표에 먼저 넣으세요.",
                     "계약·규정 조항을 한 번 더 확인하고, 감정이 올라온 말은 글로 정리한 뒤에 하세요.",
                     "하고 싶은 일 가운데 세 가지만 남기고 나머지는 다음으로 미루세요."]},
 "재성": {"caution": ["들어온 돈의 일부는 바로 저축으로 묶고, 대출을 끼는 {money_move:은} 피하세요.",
                     "감당할 수 있는 한두 가지만 골라 끝까지 가져가세요.",
                     "버는 만큼 나가는 곳도 많아지니 지출 상한과 저축 비율을 먼저 정하세요."],
          "remedy": ["큰 계약·{money_move}·대출은 미루고, 비상금(생활비 3~6개월)부터 채우세요.",
                     "맡을 일의 양을 먼저 정하고, 큰돈이 오가는 결정은 믿을 사람과 함께 하세요.",
                     "고정비를 하나씩 줄이고 새는 돈의 흐름부터 점검하세요."]},
 "관성": {"caution": ["맡기 전에 기간과 도와줄 사람을 먼저 확인하세요.",
                     "원칙과 절차를 지킬수록 평판이 쌓이니 작은 서류도 생략하지 마세요.",
                     "좋은 자리라도 감당할 수 있는 만큼만 맡고, 쉬는 날을 먼저 확보하세요."],
          "remedy": ["우선순위 세 가지만 남기고 나머지는 미루거나 나누세요.",
                     "무리한 요구는 혼자 삼키지 말고 기록을 남기며 조정하세요.",
                     "{boss:와} 부딪히는 일은 감정 대신 기록과 근거로 풀고, 건강 검진을 미루지 마세요."]},
 "인성": {"caution": ["결정할 날짜를 먼저 정해 두고 움직이세요.",
                     "배운 것은 바로 써먹고, 받은 도움은 결과로 돌려주세요.",
                     "서명 전에는 조항을 한 번 더 읽으세요."],
          "remedy": ["계획은 작게 쪼개 이번 달 안에 하나라도 실행하세요.",
                     "기상 시간을 고정하고, 미뤄 둔 일 하나를 정해 기한 안에 끝내세요.",
                     "도움은 구체적으로 요청하고, 문서·계약은 서명 전에 꼭 다시 읽으세요."]},
}

# 3) 원국 자리와의 관계 (자리 × 관계). {pair} = 오는 글자+원국 글자
REL = {
 ("충", "일"): ["{pair}충이 {pal}를 쳐서 집·생활 패턴·가까운 관계에 변화가 오기 쉬워요. 이사나 큰 살림 결정은 두 달 이상 알아본 뒤 정하세요.",
               "{pair}충이 {pal}를 흔들어 함께 사는 사람과의 생활 리듬이 어긋나기 쉬워요. 중요한 일정은 미리 맞추고, 큰 결정은 서두르지 마세요."],
 ("충", "월"): ["{pair}충이 {pal}를 쳐서 {workplace} 환경과 맡는 일이 바뀌기 쉬워요. {move}{move_eul} 생각한다면 조건을 글로 비교한 뒤 정하세요.",
               "{pair}충이 {pal}를 흔들어 {workplace}에서 자리·사람이 바뀌기 쉬워요. 갑작스러운 결정보다 준비해 둔 계획대로 움직이세요."],
 ("충", "년"): ["{pair}충이 {pal}를 쳐서 부모님 건강이나 집안 일로 신경 쓸 일이 생기기 쉬워요. 부모님 검진 일정을 먼저 챙기세요."],
 ("충", "시"): ["{pair}충이 {pal}를 쳐서 자녀 일이나 세워 둔 계획이 바뀌기 쉬워요. 일정과 예산에 20% 여유를 두세요."],
 ("형", "일"): ["{pair}형이 {pal}에 걸려 가까운 사이에 서운함과 마찰이 쌓이기 쉬워요. 집안일·돈 문제는 역할을 나눠 정하세요."],
 ("형", "월"): ["{pair}형이 {pal}에 걸려 {workplace}에서 서류·절차 문제와 마찰이 생기기 쉬워요. 계약 문구와 규정을 꼼꼼히 확인하세요."],
 ("형", "년"): ["{pair}형이 {pal}에 걸려 집안 어른과 의견이 부딪히기 쉬워요. 집안 서류·재산 이야기는 미루지 말고 정리하세요."],
 ("형", "시"): ["{pair}형이 {pal}에 걸려 계획이 어그러지거나 아랫사람 일로 마음이 쓰이기 쉬워요. 운전·운동할 때 다치지 않게 조심하세요."],
 ("합g", "일"): ["{pair}합이 {pal}와 묶여 가까운 사람과 마음이 잘 맞는 {span:이에요}. 다만 정에 끌려 돈·보증까지 함께 묶지는 마세요."],
 ("합g", "월"): ["{pair}합이 {pal}와 묶여 좋은 제안과 협력자가 생기기 쉬워요. 제안이 좋을수록 조건을 끝까지 확인하고 답하세요."],
 ("합g", "시"): ["{pair}합이 {pal}와 묶여 새 계획이 힘을 받는 {span:이에요}. 계획은 작게 시작해 키워 가세요."],
 ("합b", "일"): ["{pair}합으로 생기는 {hel} 기운이 이 사주엔 부담이라, 가까운 관계에 기대를 너무 많이 걸면 서운함이 커져요. 바라는 것은 말로 분명히 하세요."],
 ("합b", "월"): ["{pair}합으로 생기는 {hel} 기운이 부담이라, 좋아 보이는 제안이 묶이는 부담으로 바뀌기 쉬워요. 조건을 끝까지 확인한 뒤 답하세요."],
 ("합b", "시"): ["{pair}합으로 생기는 {hel} 기운이 부담이라, 새 계획은 작게 시작하고 빠져나올 길을 정해 두세요."],
 ("해", "일"): ["{pair}해가 {pal}에 걸려 가까운 사이에 말 못 한 서운함이 쌓이기 쉬워요. 바쁠수록 고맙다는 말을 먼저 하세요."],
 ("해", "월"): ["{pair}해가 {pal}에 걸려 {workplace}에서 뒷말과 오해가 생기기 쉬워요. 중요한 내용은 글로 남기세요."],
 ("파", "일"): ["{pair}파가 {pal}에 걸려 약속이 어그러지기 쉬워요. 집안 약속은 날짜를 다시 확인하세요."],
 ("파", "월"): ["{pair}파가 {pal}에 걸려 진행하던 일이 중간에 틀어지기 쉬워요. 단계마다 확인을 받으며 가세요."],
 ("원진", "일"): ["{pair}원진이 {pal}에 걸려 이유 없이 예민해지기 쉬워요. 다툼은 그날 바로 풀고 넘어가세요."],
 ("원진", "월"): ["{pair}원진이 {pal}에 걸려 {workplace}에서 감정 소모가 커지기 쉬워요. 일과 감정을 분리해 기록으로 대응하세요."],
 ("간합", "일"): ["천간 {pair}합으로 일간이 묶여 마음이 끌리는 제안·인연이 오지만, 정에 끌려 결정하기 쉬워요. 조건은 하루 묵혀 보고 답하세요."],
 ("간충", "일"): ["천간 {pair}충이 일간을 쳐서 생각과 방향이 흔들리기 쉬워요. 큰 결정은 한 번 더 검토하세요."],
}
PRIO = [("충", "일"), ("충", "월"), ("간충", "일"), ("형", "월"), ("형", "일"), ("합b", "월"), ("합b", "일"), ("합g", "월"),
        ("합g", "일"), ("간합", "일"), ("충", "년"), ("충", "시"), ("형", "년"), ("형", "시"), ("파", "월"), ("해", "월"),
        ("원진", "일"), ("해", "일"), ("파", "일"), ("원진", "월"), ("합g", "시"), ("합b", "시")]

# 4) 천간·지지 역할이 갈릴 때 (흔히 세운은 천간=상반기·지지=하반기, 대운은 앞 5년 천간·뒤 5년 지지로 나눠 봐요)
SPLIT = {
 ("up", "year"): "천간 {sko:은} {rs}이지만 지지 {bko:은} {rb:이라}, 겉으로 보이는 기회에 비해 바탕이 약해요. 흔히 천간을 상반기로 보니 중요한 일은 상반기 안에 매듭짓고, 하반기에는 지출을 줄이세요.",
 ("down", "year"): "천간 {sko:은} {rs}이지만 지지 {bko:은} {rb:이라}, 처음엔 막혀도 뒤로 갈수록 풀려요. 상반기에는 준비하고 실행은 하반기에 하세요.",
 ("up", "daeun"): "천간 {sko:은} {rs}, 지지 {bko:은} {rb:이라} 앞 5년이 뒤 5년보다 나아요. 키울 일은 앞쪽에 하고, 뒤 5년은 지키는 쪽으로 계획하세요.",
 ("down", "daeun"): "천간 {sko:은} {rs}, 지지 {bko:은} {rb:이라} 앞 5년은 다지는 시기, 뒤 5년이 힘을 받는 시기예요. 앞쪽에 실력과 자금을 모아 두세요.",
 ("both_good", "year"): "천간 {sko}·지지 {bko:이} 모두 이 사주를 돕는 기운이라 겉과 속이 함께 받쳐 줘요. 미뤄 둔 계획을 꺼내되, 잘 풀릴 때 커지는 씀씀이부터 묶어 두세요.",
 ("both_bad", "year"): "천간 {sko}·지지 {bko:이} 모두 이 사주에 부담인 기운이라 겉과 속이 함께 무거워요. 새로 벌이기보다 지키는 쪽으로 한 해 계획을 짜세요.",
 ("both_good", "daeun"): "천간 {sko}·지지 {bko:이} 모두 이 사주를 돕는 기운이라 10년 내내 바탕이 든든해요. 다만 잘될 때 일을 너무 넓히지 않게 상한선을 정하세요.",
 ("both_bad", "daeun"): "천간 {sko}·지지 {bko:이} 모두 이 사주에 부담인 기운이라, 이 10년은 크게 키우기보다 건강·현금·관계를 지키는 쪽이 맞아요.",
}

# 5) 원국에 없던 오행 / 넘치는 오행
LACK = {
 "비겁": {"fav": "원국에 없던 {ew}({e}) 기운, 곧 내 편(비겁)이 처음 들어오는 {span:이라} 혼자 하던 일을 함께할 사람이 생겨요.",
          "unf": "원국에 없던 {ew}({e}) 기운, 곧 경쟁자(비겁)가 들어오는 {span:이라} 갑자기 사람 문제로 지출이 늘 수 있어요. 돈 거래는 피하세요."},
 "식상": {"fav": "원국에 없던 {ew}({e}) 기운, 곧 표현(식상)이 들어오는 {span:이라} 말하지 못하던 재능을 꺼내기 좋아요.",
          "unf": "원국에 없던 {ew}({e}) 기운, 곧 식상이 들어와 낯선 일을 벌이고 싶어져요. 익숙하지 않은 분야는 작게 시험해 보세요."},
 "재성": {"fav": "원국에 없던 {ew}({e}) 기운, 곧 돈(재성)이 들어오는 {span:이라} 돈을 직접 다룰 기회가 처음으로 커져요. 관리 원칙부터 세우세요.",
          "unf": "원국에 없던 {ew}({e}) 기운, 곧 재성이 들어와 익숙하지 않은 돈 문제가 생기기 쉬워요. 모르는 투자는 하지 마세요."},
 "관성": {"fav": "원국에 없던 {ew}({e}) 기운, 곧 책임과 평판(관성)이 들어오는 {span:이라} 맡는 역할이 새로 생겨요.",
          "unf": "원국에 없던 {ew}({e}) 기운, 곧 관성이 들어와 낯선 규칙과 압박을 겪기 쉬워요. 절차를 먼저 익히세요."},
 "인성": {"fav": "원국에 없던 {ew}({e}) 기운, 곧 도움과 배움(인성)이 들어오는 {span:이라} 자격·공부를 시작하기 좋아요.",
          "unf": "원국에 없던 {ew}({e}) 기운, 곧 인성이 들어와 생각이 많아지기 쉬워요. 결정 기한을 정해 두세요."},
}
OVER = {
 "비겁": "이미 많은 {ew}({e})가 더 쌓여 고집과 경쟁이 지나치기 쉬워요. 내 생각과 다른 의견을 일부러 들어 보세요.",
 "식상": "이미 많은 {ew}({e})가 더해져 일과 말이 넘치기 쉬워요. 벌인 일부터 정리하세요.",
 "재성": "이미 많은 {ew}({e})가 더해져 돈과 일이 감당 이상으로 몰리기 쉬워요. 맡을 일을 줄이는 쪽이 오히려 이득이에요.",
 "관성": "이미 많은 {ew}({e})가 더해져 책임과 압박이 과해지기 쉬워요. 거절할 일을 먼저 정하세요.",
 "인성": "이미 많은 {ew}({e})가 더해져 생각과 걱정이 넘치기 쉬워요. 몸을 움직여 생각을 줄이세요.",
}

# 6) 대운과 세운의 겹침·부딪힘
DCTX = {
 ("good", "bad"): "지금 {dgz} 대운이 받쳐 주고 있어 약한 해라도 크게 무너지진 않아요. 손해를 줄이는 쪽으로만 움직이면 돼요.",
 ("bad", "good"): "{dgz} 대운이 무거운 가운데 잠깐 열리는 좋은 해라, 기회의 문이 짧아요. 1년 안에 끝낼 수 있는 일부터 하세요.",
 ("bad", "bad"): "{dgz} 대운과 이 해가 함께 약해 겹치는 때예요. 새 일보다 지출 줄이기·건강 검진·계약 점검을 먼저 하세요.",
 ("good", "good"): "{dgz} 대운과 이 해가 함께 받쳐 주는 드문 때예요. 잘 풀릴수록 씀씀이와 약속이 커지니 상한선을 먼저 정하세요.",
 ("mid", "bad"): "{dgz} 대운도 고르게만 가는 때라 이 해의 약한 기운을 메워 줄 힘이 크지 않아요. 큰 결정은 다음 좋은 해로 미루세요.",
 ("mid", "good"): "{dgz} 대운이 고르게 가는 가운데 오는 좋은 해라, 준비해 둔 일이 있다면 이때 꺼내세요.",
 "chung": "세운 {yb}{yb_ga} 대운 {db}{db_wa} 충해 운끼리 부딪히는 해라, 계획이 한 번 크게 바뀌기 쉬워요. 큰 결정은 두 번 검토하세요.",
}


# ------------------------------------------------------------------ 분석
class P:
    """기간(세운·대운·월운) 하나를 이 사주 기준으로 분석한 결과"""
    def __init__(self, c, gz, sc, scope="year", year=None):
        from engine import STEM_ELK, BR_ELK
        self.c, self.gz, self.sc, self.scope = c, gz, sc, scope
        s, b = gz
        self.s, self.b = s, b
        self.es, self.eb = STEM_ELK[s], BR_ELK[b]
        self.fs, self.fb = c.fav[self.es], c.fav[self.eb]
        self.tg_s, self.tg_b = c.tg(s), c.tg(b, True)
        self.g_s, self.g_b = TG_GROUP[self.tg_s], TG_GROUP[self.tg_b]
        self.tone = c.tone(sc)
        # 주제 십신: 좋은 때는 지지(바탕), 아니면 더 부담인 쪽
        if self.tone == "good" or self.fb <= self.fs:
            self.tg, self.g, self.e, self.f = self.tg_b, self.g_b, self.eb, self.fb
        else:
            self.tg, self.g, self.e, self.f = self.tg_s, self.g_s, self.es, self.fs
        self.og = self.g_s if self.g == self.g_b else self.g_b
        self.rels = c.relations_to_chart(s, b)
        self.year = year
        self.span = SPAN[scope]
        self.st = "강" if c.strong else "약"

    # 원국 관계 문장 (우선순위 순)
    def rel_items(self):
        c = self.c; W = words(); out = []
        seen = set()
        for kind, pos, det, el in self.rels:
            k = None
            if kind == "충": k = ("충", pos)
            elif kind == "형": k = ("형", pos)
            elif kind in ("육합", "반합") and el in c.fav and pos in ("일", "월", "시"):
                k = ("합g" if c.fav[el] >= 0 else "합b", pos)
            elif kind in ("해", "파", "원진") and pos in ("일", "월"): k = (kind, pos)
            elif kind == "천간합" and pos == "일": k = ("간합", "일")
            elif kind == "천간충" and pos == "일": k = ("간충", "일")
            if not k or k in seen or k not in REL: continue
            seen.add(k)
            import jobs as JB
            mv = JB.t("move")
            txt = fill(pick(REL[k], c, "rel" + "".join(k) + self.gz), pair=det if not k[0].startswith("간") else det,
                       pal=PAL.get(pos, pos), span=self.span, hel=f"{EL_WORD.get(el, el)}({el})" if el else "",
                       move=mv, move_eul=particle(mv, "을"), **W)
            out.append((PRIO.index(k) if k in PRIO else 99, k, txt))
        out.sort()
        return out

    def split(self):
        """천간·지지 역할 차이 문장 (해·10년만)"""
        if self.scope == "month": return None
        fs, fb = self.fs, self.fb
        kw = dict(sko=ST_KO[self.s], bko=BR_KO[self.b], rs=ROLE[fs], rb=ROLE[fb])
        if fs >= 1 and fb >= 1: key = "both_good"
        elif fs <= -1 and fb <= -1: key = "both_bad"
        elif fs - fb >= 2 and fs >= 1: key = "up"
        elif fb - fs >= 2 and fb >= 1: key = "down"
        else: return None
        t = SPLIT.get((key, self.scope))
        if not t: return None
        return key, fill(t, **kw)

    def lack_over(self):
        c = self.c
        for e, g, f in ((self.eb, self.g_b, self.fb), (self.es, self.g_s, self.fs)):
            if c.cnt.get(e, 1) == 0:
                return ("lack", fill(LACK[g]["fav" if f >= 0 else "unf"], ew=EL_WORD[e], e=e, span=self.span))
        for e, g, f in ((self.eb, self.g_b, self.fb), (self.es, self.g_s, self.fs)):
            if c.cnt.get(e, 0) >= 3 and f <= -1:
                return ("over", fill(OVER[g], ew=EL_WORD[e], e=e))
        return None

    def daeun_ctx(self):
        if self.scope != "year" or not self.year: return None
        c = self.c; d = c.current_daeun(self.year)
        if not d: return None
        dt = c.tone(c.score(d["gz"])[0])
        import saju as S
        rel = S.pair_relations(self.b, d["gz"][1])
        if "충" in rel:
            yb, db = self.b, d["gz"][1]
            return fill(DCTX["chung"], yb=yb, db=db, yb_ga=particle(yb, "가"), db_wa=particle(db, "와"))
        t = DCTX.get((dt, self.tone))
        return fill(t, dgz=d["gz"]) if t else None

    # 원리 문장
    def mech(self, g=None, tg=None, f=None):
        c = self.c; W = words()
        g = g or self.g; tg = tg or self.tg; f = self.f if f is None else f
        fc = fclass(f)
        lst = MECH[g][fc].get(self.st) or MECH[g][fc]["약"]
        role = ROLE[f] if f else "중립 기운"
        return fill(pick(lst, c, "m" + tg + self.gz + self.scope), tg=tg, role=role, role_ro=particle(role, "으로"),
                    tg_ro=particle(tg, "으로"), span=self.span, stw=stw(c), **W)

    def act(self, kind, g=None, salt=""):
        return fill(pick(ACT[g or self.g][kind], self.c, kind + self.gz + self.scope + salt), **words())


# ------------------------------------------------------------------ 5) 들어오는 십신 × 원국 십신 — 자평명리의 고전 조합(이 사주에 그 십신이 있어야만 성립)
def natal_tgs(c):
    """원국에 보이는 십신 목록(일간 제외, 천간+지지 본기)"""
    if not hasattr(c, "_ntg"):
        out = []
        for pos, p in c.P.items():
            s, b = p["gz"]
            if pos != "일": out.append(c.tg(s))
            out.append(c.tg(b, True))
        c._ntg = out
    return c._ntg


def gcount(c, g):
    return sum(1 for t in natal_tgs(c) if TG_GROUP[t] == g)


# (들어오는 십신, 원국에 있어야 할 십신들, 조건, 이름, 문장 후보)
COMBO = [
 ("상관", ("정관",), None, "상관견관",
  ["들어오는 상관이 원국의 정관을 치는 상관견관(傷官見官)이라, {boss:와} 부딪히거나 말 한마디로 평판에 흠이 나기 쉬워요. 하고 싶은 말은 하루 묵혔다가 문서로 다듬어 전하세요.",
   "원국의 정관을 들어오는 상관이 건드리는 {span:이라}(상관견관) 규칙·윗선과의 마찰을 조심하세요. 옳은 말도 자리와 때를 골라야 해요."]),
 ("편인", ("식신",), None, "도식",
  ["들어오는 편인이 원국의 식신을 누르는 도식(倒食)이라, 하던 일이 막히거나 의욕·입맛이 떨어지기 쉬워요. 새로 벌이기보다 하던 일을 끝까지 지키세요.",
   "원국의 식신이 편인에 눌리는 {span:이라}(도식) 생각은 많은데 손이 안 따라가기 쉬워요. 하루 할 일을 세 가지로 줄이세요."]),
 ("겁재", ("정재", "편재"), None, "겁재탈재",
  ["들어오는 겁재가 원국의 재성을 넘보는 겁재탈재(劫財奪財)라, 돈이 사람을 따라 새기 쉬워요. 보증·돈 빌려주기·공동 투자는 정중히 거절하세요.",
   "원국의 재성을 겁재가 나눠 가져가려는 {span:이라} 가까운 사람과 돈이 얽히기 쉬워요. 돈 거래는 금액과 날짜를 적어 두세요."]),
 ("비견", ("정재", "편재"), "strong", "군비쟁재",
  ["신강한 사주에 비견이 더해져 원국의 재성을 여럿이 나누는 모양(군비쟁재)이에요. 함께 하는 일일수록 몫과 비용을 먼저 정하세요."]),
 ("편관", ("정관",), None, "관살혼잡",
  ["원국의 정관에 편관이 겹치는 관살혼잡(官殺混雜)이라 기준과 책임이 엇갈려 판단이 흔들리기 쉬워요. 지킬 원칙 하나를 정해 거기에만 맞추세요."]),
 ("정관", ("편관",), None, "관살혼잡",
  ["원국의 편관에 정관이 겹치는 관살혼잡(官殺混雜)이라 맡는 역할이 여러 갈래로 나뉘기 쉬워요. 거절할 일을 먼저 정해 두세요."]),
 ("식신", ("편관",), None, "식신제살",
  ["들어오는 식신이 원국의 편관을 다스리는 식신제살(食神制殺)이라, 눌려 있던 압박을 실력으로 풀기 좋아요. 미뤄 둔 어려운 일을 이때 정리하세요.",
   "원국의 편관을 식신이 다잡는 {span:이라}(식신제살) 버거웠던 일이 손에 잡히기 시작해요. 실력을 보여 줄 결과물 하나를 만드세요."]),
 ("정인", ("정관", "편관"), "weak", "관인상생",
  ["원국의 관성이 들어오는 정인으로 이어지는 관인상생(官印相生)이라, 책임이 오히려 자격과 인정으로 바뀌기 쉬워요. 시험·자격·승인 같은 문서 일을 이때 밀어 보세요."]),
 ("편인", ("정관", "편관"), "weak", "관인상생",
  ["원국의 관성이 들어오는 편인으로 이어지는 관인상생이라, 압박을 배움과 자격으로 바꾸기 좋아요. 전문 분야 공부를 한 가지 시작하세요."]),
 ("정재", ("정인", "편인"), "weak_in", "재극인",
  ["들어오는 재성이 이 사주를 받치는 인성을 누르는 재극인(財剋印)이라, 돈 때문에 공부·문서·건강을 뒤로 미루기 쉬워요. 계약서 확인과 건강 검진을 먼저 챙기세요."]),
 ("편재", ("정인", "편인"), "weak_in", "재극인",
  ["들어오는 편재가 이 사주를 받치는 인성을 누르는 재극인(財剋印)이라, 눈앞의 돈 기회에 쉬어야 할 때를 놓치기 쉬워요. 큰 결정 전에는 꼭 하루를 쉬고 정하세요."]),
 ("정재", ("식신", "상관"), "strong", "식상생재",
  ["원국의 식상이 들어오는 재성으로 이어지는 식상생재(食傷生財)라, 재능과 손재주가 돈으로 바뀌기 좋아요. 들어온 돈은 바로 나눠 묶어 두세요."]),
 ("편재", ("식신", "상관"), "strong", "식상생재",
  ["원국의 식상이 들어오는 편재로 이어지는 식상생재라, 하던 일의 결과가 돈으로 돌아오기 좋아요. 다만 크게 걸기보다 나눠서 키우세요."]),
 ("정관", ("정재", "편재"), "strong", "재생관",
  ["원국의 재성이 들어오는 관성을 키우는 재생관(財生官)이라, 돈과 함께 자리·평판도 올라가기 좋아요. 맡는 역할이 커지는 만큼 기록을 남기세요."]),
 ("편관", ("정재", "편재"), "weak", "재생살",
  ["원국의 재성이 들어오는 편관을 키우는 재생살(財生殺)이라, 돈 문제가 곧 압박과 책임으로 번지기 쉬워요. 지출 원칙부터 세우고 무리한 약속은 피하세요."]),
]


def combo(p):
    """들어오는 천간·지지 십신과 원국 십신의 고전 조합. (이름, 문장) 또는 None"""
    c = p.c; nt = natal_tgs(c)
    for tg in (p.tg, p.tg_s if p.tg != p.tg_s else p.tg_b):
        for t, need, cond, name, lst in COMBO:
            if t != tg or not any(x in nt for x in need): continue
            if cond == "strong" and not c.strong: continue
            if cond == "weak" and c.strong: continue
            if cond == "weak_in" and (c.strong or c.fav.get(_gel(c, "인성"), 0) < 1): continue
            return name, fill(pick(lst, c, "cb" + name + p.gz), span=p.span, **words())
    return None


def _gel(c, g):
    """십신 그룹에 해당하는 오행"""
    return c.gel.get(g)


def facet(p, used=()):
    """원리 문장 다음에 붙일 '이 사주만의' 두 번째 문장 하나(우선순위)."""
    rs = [x for x in p.rel_items() if x[1] not in used]
    top = rs[0] if rs else None
    if top and top[1] in (("충", "일"), ("충", "월"), ("간충", "일")):
        return "rel", top[2]
    cb = combo(p) if "combo" not in used else None
    if cb: return "combo", cb[1]
    sp = p.split()
    if sp: return "split", sp[1]
    dc = p.daeun_ctx()
    if dc: return "dctx", dc
    if top and top[0] < PRIO.index(("충", "년")):
        return "rel", top[2]
    lo = p.lack_over()
    if lo: return lo
    if top: return "rel", top[2]
    return None, None
