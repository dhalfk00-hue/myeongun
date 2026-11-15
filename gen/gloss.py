# -*- coding: utf-8 -*-
"""gloss1116: 사주 용어 풀이(쉬운 뜻) · 한자 정리.

원칙(가이드 guide.md 1~10장 기준으로 뜻을 적었어요)
- 한 장(큰 제목 h2 단위, 표지·명식 쪽은 쪽 단위) 안에서 용어가 처음 나올 때만 `편관(偏官·나를 다잡는 책임·압박)`처럼 풀어 써요.
  그 뒤로는 한글 용어만 써요. 한자는 한 장에 한 번, 괄호 안에서만 보여요.
- 한자 기둥(庚申 등)은 `경신(庚申·쇠·쇠)`처럼 한글 읽기 + 오행 뜻으로 바꾸고, 두 번째부터는 `경신`만 써요.
- 표 칸·제목에는 용어 풀이를 넣지 않아요(지저분해지지 않게). 한자만 한글로 읽어 줘요.
- 명식표의 큰 글자는 그대로 두고 아래에 한글 읽기·오행을 작게 달아요.
"""
import re

STEM_KO = dict(zip("甲乙丙丁戊己庚辛壬癸", "갑을병정무기경신임계"))
BR_KO = dict(zip("子丑寅卯辰巳午未申酉戌亥", "자축인묘진사오미신유술해"))
EL_PLAIN = {"목": "나무", "화": "불", "토": "흙", "금": "쇠", "수": "물"}
STEM_EL = dict(zip("甲乙丙丁戊己庚辛壬癸", "목목화화토토금금수수"))
BR_EL = dict(zip("子丑寅卯辰巳午未申酉戌亥", "수토목목토화화토금금토수"))
EL_HAN = dict(zip("木火土金水", "목화토금수"))
# 그 밖에 감정서에 나오는 한자 낱자 읽기
CH_KO = {**STEM_KO, **BR_KO, **EL_HAN, "命": "명", "式": "식", "身": "신", "强": "강", "弱": "약", "用": "용", "神": "신", "喜": "희", "忌": "기",
         "殺": "살", "局": "국", "大": "대", "運": "운", "財": "재", "生": "생", "官": "관", "月": "월", "混": "혼", "雜": "잡", "劫": "겁", "奪": "탈",
         "中": "중", "和": "화", "格": "격", "印": "인", "食": "식", "傷": "상", "偏": "편", "正": "정", "比": "비", "肩": "견", "歲": "세", "合": "합",
         "沖": "충", "刑": "형", "破": "파", "害": "해", "年": "년", "日": "일", "時": "시", "干": "간", "支": "지", "星": "성", "十": "십", "二": "이",
         "仇": "구", "閑": "한", "調": "조", "候": "후", "抑": "억", "扶": "부", "倒": "도", "制": "제", "相": "상", "見": "견", "群": "군", "爭": "쟁",
         "剋": "극", "空": "공", "亡": "망", "怨": "원", "嗔": "진", "驛": "역", "馬": "마", "桃": "도", "花": "화", "華": "화", "蓋": "개", "貴": "귀",
         "人": "인", "乙": "을", "文": "문", "昌": "창", "羊": "양", "刃": "인", "魁": "괴", "罡": "강", "白": "백", "虎": "호", "紅": "홍", "艶": "염",
         "原": "원", "藏": "장", "得": "득", "令": "령", "地": "지", "勢": "세", "通": "통", "根": "근", "透": "투", "建": "건", "祿": "록", "帝": "제",
         "旺": "왕", "長": "장", "冠": "관", "帶": "대", "沐": "목", "浴": "욕", "五": "오", "行": "행", "七": "칠", "伏": "복", "吟": "음", "反": "반",
         "三": "삼", "六": "육", "方": "방", "半": "반", "宮": "궁", "配": "배", "偶": "우", "主": "주", "天": "천", "數": "수", "絶": "절", "胎": "태",
         "養": "양", "衰": "쇠", "病": "병", "死": "사", "墓": "묘"}

# 용어: (한자, 짧은 뜻 ≈10자, 실제로는 — 용어 쪽에만 써요)
T = {
    # 기본 틀
    "원국": ("原局", "타고난 여덟 글자", "평생 바뀌지 않는 바탕이에요. 운은 여기에 더해지는 날씨예요."),
    "오행": ("五行", "나무·불·흙·쇠·물", "많은 기운은 장점이자 버릇, 적은 기운은 채우면 좋은 쪽이에요."),
    "천간": ("天干", "위 글자, 드러난 기운", "생각·말·명분처럼 남에게 보이는 쪽이에요."),
    "지지": ("地支", "아래 글자, 바탕 기운", "생활·환경·몸처럼 실제로 겪는 쪽이에요."),
    "일간": ("日干", "나를 뜻하는 글자", "모든 풀이의 기준이에요. 나머지 글자는 나와의 관계로 읽어요."),
    "월지": ("月支", "태어난 달 글자", "사주에서 힘이 가장 커요. 일터·사회 환경 변화를 읽는 자리예요."),
    "일지": ("日支", "내가 앉은 자리", "배우자·집·몸의 변화를 읽는 자리예요."),
    "시지": ("時支", "태어난 시 글자", "자녀·아랫사람·노후 쪽 일을 읽어요."),
    "년지": ("年支", "태어난 해 글자", "집안·윗사람 쪽 일을 읽어요."),
    "지장간": ("地藏干", "아래 글자 속에 숨은 기운", "겉에 없어도 속에 있으면 아주 없는 게 아니에요."),
    "십신": ("十神", "나와 글자의 관계 10가지", "돈·일·사람·배움 중 무엇이 강한지 알려 줘요."),
    # 십신
    "비견": ("比肩", "동료·자립의 힘", "자립심이 강해요. 동업·경쟁에서 나눌 일이 생겨요."),
    "겁재": ("劫財", "경쟁·승부의 힘", "승부욕이 생기지만 큰 지출·돈 나눔을 조심해요."),
    "식신": ("食神", "재능·꾸준한 솜씨", "꾸준히 만들고 가르치는 일로 결과가 나와요."),
    "상관": ("傷官", "말솜씨·튀는 재주", "아이디어가 돈이 되지만 윗사람과 부딪히기 쉬워요."),
    "편재": ("偏財", "크게 도는 돈", "사업·거래로 들고 남이 커요. 판을 키우는 힘이에요."),
    "정재": ("正財", "꼬박꼬박 버는 돈", "고정 수입·저축·알뜰함이에요. 차곡차곡 모으는 힘이에요."),
    "편관": ("偏官", "압박·책임", "책임이 무거워지지만 버티면 실력과 자리가 단단해져요."),
    "정관": ("正官", "규칙·신용·명예", "인정·자리·신용이에요. 원칙을 지킬수록 좋아요."),
    "편인": ("偏印", "직관·전문 기술", "기술·연구·직관이에요. 생각이 많아지면 실행이 늦어요."),
    "정인": ("正印", "배움·자격·후원", "공부·문서·후원이에요. 자격과 계약에 힘이 붙어요."),
    "칠살": ("七殺", "편관의 다른 이름, 강한 압박", "버티는 근성이 커지는 대신 무리하기 쉬워요."),
    # 십신 묶음
    "비겁": ("比劫", "자립·동료의 기운", "자립·고집·동료예요. 많으면 돈을 나눌 일이 생겨요."),
    "식상": ("食傷", "재능·표현의 기운", "재능·말·표현이에요. 결과물을 내놓는 힘이에요."),
    "재성": ("財星", "돈·현실의 기운", "돈·현실 감각이에요. 남성에게는 아내 자리도 돼요."),
    "관성": ("官星", "책임·명예의 기운", "일의 자리·책임·명예예요. 여성에게는 남편 자리도 돼요."),
    "인성": ("印星", "배움·도움의 기운", "배움·자격·문서·어머니예요."),
    # 강약
    "신강": ("身强", "내 기운이 센 사주", "밀고 나가는 힘이 있어요. 힘을 일·표현으로 흘려 쓰면 좋아요."),
    "신약": ("身弱", "내 기운이 약한 편인 사주", "혼자보다 도움·배움을 받으며 갈 때 힘이 나요."),
    "중화": ("中和", "기운이 고르게 맞은 사주", "치우침이 적어 운에 따라 크게 흔들리지 않아요."),
    "득령": ("得令", "태어난 달이 나를 도움", "강약을 정하는 가장 큰 기준이에요."),
    "득지": ("得地", "앉은 자리가 나를 도움", "생활 기반이 나를 받쳐 줘요."),
    "득세": ("得勢", "주변 글자가 나를 도움", "도와주는 사람·환경이 많은 편이에요."),
    "통근": ("通根", "아래 글자에 뿌리를 둠", "뿌리가 있으면 겉 기운이 쉽게 꺾이지 않아요."),
    "투간": ("透干", "속 기운이 위로 드러남", "드러난 기운이 실제 성향으로 강하게 나와요."),
    "월령": ("月令", "태어난 달의 힘", "그 계절에 힘이 센 기운인지 보는 기준이에요."),
    # 용신
    "용신": ("用神", "나를 살리는 기운", "이 기운이 오는 해·달에 일이 잘 풀려요."),
    "희신": ("喜神", "용신을 돕는 기운", "용신 다음으로 반가운 기운이에요."),
    "기신": ("忌神", "부담이 되는 기운", "이 기운이 오는 해에는 지키고 보완해요."),
    "구신": ("仇神", "기신을 돕는 기운", "기신을 돕는 기운이라 이 해에는 무리하지 않아요."),
    "한신": ("閑神", "큰 영향이 없는 기운", "좋지도 나쁘지도 않은 중간이에요."),
    "조후": ("調候", "계절 온도 맞추기", "너무 차거나 뜨거운 사주는 온도부터 맞춰요."),
    "억부": ("抑扶", "센 힘은 덜고 약하면 돕기", "강약 균형으로 용신을 정하는 기본 방법이에요."),
    "격국": ("格局", "사주의 큰 틀·성향", "어떤 방식으로 살 때 빛나는지 보여요."),
    # 운
    "대운": ("大運", "10년 단위 큰 흐름", "인생의 계절이에요. 같은 해라도 대운에 따라 체감이 달라요."),
    "세운": ("歲運", "그해의 운", "1년 날씨예요. 원국·대운과 함께 봐요."),
    "월운": ("月運", "그달의 운", "달마다 바뀌는 작은 흐름이에요."),
    "월건": ("月建", "그달의 간지", "절기(입춘·경칩…)로 바뀌는 달의 두 글자예요."),
    "대운수": ("大運數", "대운이 바뀌는 나이", "그 나이 무렵 10년 흐름이 바뀌어요."),
    # 12운성
    "12운성": ("十二運星", "기운의 세기 12단계", "자라고·서고·저무는 단계로 힘의 크기를 봐요."),
    "장생": ("長生", "막 자라기 시작하는 힘", "새로 시작하고 귀여움받는 기운이에요."),
    "관대": ("冠帶", "자신감이 붙는 단계", "의욕과 혈기가 커져요."),
    "건록": ("建祿", "스스로 서는 힘", "자립심과 실무력이에요."),
    "제왕": ("帝旺", "힘이 가장 센 단계", "주도하는 힘이 크지만 고집도 커요."),
    # 신살
    "신살": ("神殺", "덧붙여 읽는 특별한 표식", "구조를 본 뒤 덧붙이는 참고예요."),
    "역마": ("驛馬", "이동·변동의 표식", "이사·출장·해외·자리 이동이 잦아져요."),
    "역마살": ("驛馬殺", "이동·변동의 표식", "이사·출장·해외·자리 이동이 잦아져요."),
    "도화": ("桃花", "매력·인기의 표식", "사람이 모이고 눈에 띄어요. 구설도 조심해요."),
    "도화살": ("桃花殺", "매력·인기의 표식", "사람이 모이고 눈에 띄어요. 구설도 조심해요."),
    "화개": ("華蓋", "공부·예술·혼자만의 시간", "깊이 파고드는 힘이에요. 혼자만의 시간이 필요해요."),
    "화개살": ("華蓋殺", "공부·예술·혼자만의 시간", "깊이 파고드는 힘이에요. 혼자만의 시간이 필요해요."),
    "천을귀인": ("天乙貴人", "도와주는 사람의 표식", "어려울 때 도움을 받거나 위기를 넘겨요."),
    "문창귀인": ("文昌貴人", "글·공부 재주의 표식", "시험·글쓰기·자격에 힘이 돼요."),
    "양인": ("羊刃", "강한 추진력의 표식", "밀어붙이는 힘이 크지만 다침·충돌을 조심해요."),
    "괴강": ("魁罡", "강하고 굽히지 않는 기질", "카리스마가 있지만 극단으로 가지 않게 조절해요."),
    "백호": ("白虎", "사고·다침 주의 표식", "운전·운동·수술 같은 일에 조심성을 더해요."),
    "백호살": ("白虎殺", "사고·다침 주의 표식", "운전·운동·수술 같은 일에 조심성을 더해요."),
    "홍염": ("紅艶", "이성에게 끌리는 매력", "인기가 많아요. 관계의 선을 분명히 해요."),
    "홍염살": ("紅艶殺", "이성에게 끌리는 매력", "인기가 많아요. 관계의 선을 분명히 해요."),
    "공망": ("空亡", "비어서 실속이 약한 자리", "그 자리의 일은 기대를 줄이고 실속을 챙겨요."),
    "원진": ("怨嗔", "서운함이 쌓이는 사이", "말 한마디가 오래 남아요. 짧게 자주 풀어요."),
    "배우자궁": ("配偶者宮", "배우자 자리", "배우자와의 관계·집안 분위기를 읽어요."),
    # 합충
    "육합": ("六合", "두 글자가 짝지어 묶임", "인연·협력이 생기지만 발이 묶일 수도 있어요."),
    "삼합": ("三合", "세 글자가 한 기운으로 뭉침", "큰 힘이 한쪽으로 모여요."),
    "방합": ("方合", "같은 계절 글자끼리 뭉침", "한 기운이 아주 강해져요."),
    "반합": ("半合", "삼합의 절반이 모임", "묶이는 힘이 생겨요."),
    "원진귀문": ("怨嗔鬼門", "예민함이 쌓이는 사이", "감정이 예민해지니 말을 부드럽게 해요."),
    # 구조 이름
    "식신생재": ("食神生財", "재능이 돈으로 이어짐", "잘하는 것을 수입으로 연결하면 좋아요."),
    "재생관": ("財生官", "돈이 자리·신용을 키움", "번 돈이 지위와 신용으로 이어져요."),
    "관인상생": ("官印相生", "자리와 배움이 서로 도움", "자격과 인정이 함께 따라와요."),
    "살인상생": ("殺印相生", "압박을 배움으로 이겨냄", "힘든 일을 공부·자격으로 바꿔요."),
    "식신제살": ("食神制殺", "재주로 압박을 다스림", "실력으로 어려움을 정리해요."),
    "상관견관": ("傷官見官", "말과 규칙이 부딪힘", "윗사람·규칙과 마찰을 조심해요."),
    "재극인": ("財剋印", "돈 일로 문서가 흔들림", "계약·문서를 꼼꼼히 봐요."),
    "군겁쟁재": ("群劫爭財", "사람이 많아 돈을 다툼", "동업·돈 빌려주기를 조심해요."),
    "겁재탈재": ("劫財奪財", "경쟁자에게 돈이 샘", "보증·동업·투자 권유를 조심해요."),
    "관살혼잡": ("官殺混雜", "책임과 기준이 엇갈림", "지킬 원칙 하나를 정하면 흔들림이 줄어요."),
    "편인도식": ("偏印倒食", "생각이 재능을 막음", "고민만 길어지지 않게 마감을 정해요."),
    "도식": ("倒食", "생각이 재능을 막음", "고민만 길어지지 않게 마감을 정해요."),
    "복음": ("伏吟", "같은 글자가 겹침", "같은 일이 되풀이되거나 멈춰 있기 쉬워요."),
    "반음": ("反吟", "기둥이 통째로 부딪힘", "큰 변동이 생기기 쉬워요."),
}
# 격 이름(정인격 등)
_GK = {"비견": "자립", "겁재": "승부", "식신": "재능", "상관": "표현", "편재": "사업", "정재": "성실한 돈", "편관": "책임·근성", "칠살": "책임·근성",
       "정관": "원칙·명예", "편인": "전문 기술", "정인": "배움·자격", "건록": "자립", "양인": "추진력"}
for k, v in _GK.items():
    T[k + "격"] = (T[k][0] + "格" if k in T else k + "格", f"{v} 중심의 틀", f"{v} 쪽으로 살 때 빛나요.")
T["건록격"] = ("建祿格", "자립 중심의 틀", "스스로 일어서는 일에서 빛나요.")
T["양인격"] = ("羊刃格", "추진력 중심의 틀", "강한 힘을 일로 다스릴 때 빛나요.")

RELS = {"합": ("合", "묶임·인연"), "충": ("沖", "부딪혀 바뀜"), "형": ("刑", "마찰·조정"), "파": ("破", "틀어짐"), "해": ("害", "서운함·방해")}
SKIP_TERMS = set()
HAN = r"[\u4e00-\u9fff]"
RUN = re.compile(HAN + "+")
_TERMS = sorted(T, key=len, reverse=True)
TERM_RE = re.compile(r"(?<![가-힣])(" + "|".join(map(re.escape, _TERMS)) + r")")
# 낱말 오인 막기: 상관없이·관대한·세운다 등
_BAD_AFTER = {"상관": ("없", "있"), "관대": ("하", "한", "히", "함"), "세운": ("다", " 계획", " 뒤", " 목표", "다면"), "인성": ("교육",), "도식": ("화", "적"), "사주": ("팔자",), "편인": ("데", "지")}
MK0, MK1 = "\ue000", "\ue001"   # 풀이에 넣은 한자는 표시해 두고 다시 바꾸지 않아요


def read(run):
    return "".join(CH_KO.get(ch, ch) for ch in run)


def is_pillar(run):
    return len(run) == 2 and run[0] in STEM_KO and run[1] in BR_KO


def gz_only(run):
    return all(ch in STEM_KO or ch in BR_KO for ch in run)


def el_desc(run):
    """기둥·낱자의 오행 쉬운 뜻: 庚申 → 쇠·쇠"""
    if len(run) == 1 and run in EL_HAN: return EL_PLAIN[EL_HAN[run]]
    if not gz_only(run) or len(run) > 2: return ""
    out = []
    for ch in run:
        e = STEM_EL.get(ch) or BR_EL.get(ch)
        out.append(EL_PLAIN[e])
    if len(run) == 2 and not is_pillar(run): return ""
    return "·".join(out)


def kor(run):
    if run in EL_HAN.keys() and len(run) == 1: return EL_HAN[run]
    if gz_only(run) and len(run) >= 2 and not is_pillar(run):
        return "·".join(read(ch) for ch in run)
    return read(run)


class Scope:
    def __init__(self):
        self.han = set(); self.term = set(); self.n_gloss = 0; self.blk = 0


CORE = {"비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인", "용신", "희신", "기신", "구신", "한신", "신강", "신약"}   # 핵심 용어는 한도와 상관없이 풀어요
BLOCK_CAP = 5   # 한 문단(문단·목록 항목·표 칸)에 풀이는 5개까지 — 넘는 용어는 다음에 나올 때 풀어요


VOID = {"br", "img", "meta", "link", "hr", "input", "col", "wbr", "source"}


DOC_ONCE = {"사주", "원국", "천간", "지지", "일간", "대운", "세운", "월운", "오행", "십신", "지장간", "12운성", "신살", "격국", "월건"}
ROLES = ("용신", "희신", "기신", "구신", "한신")
DOC = {"term": set(), "han": set()}


def _open_paren(txt):
    txt = txt[-60:]
    return txt.count("(") > txt.count(")") or txt.rfind("(") > txt.rfind(")")


def _term_pass(s, sc, mode, prev=""):
    """mode: 'text' 풀이 넣기 / 'quiet' 표·제목(풀이 없이 처음 표시만 기록)"""
    out = []; pos = 0
    for m in TERM_RE.finditer(s):
        w = m.group(1); e = m.end()
        nxt = s[e:e + 4]
        if any(nxt.startswith(b) for b in _BAD_AFTER.get(w, ())): continue
        once = (w in DOC_ONCE or mode == "cell") and w in DOC["term"]
        if w in sc.term or once:
            # 두 번째부터: 뒤에 그 용어의 한자 괄호만 있으면 지워요
            h = T[w][0]
            if s.startswith("(" + h + ")", e):
                out.append(s[pos:e]); pos = e + len(h) + 2
            continue
        if mode not in ("text", "cell") or _open_paren(prev + s[:m.start()]) or (sc.blk >= BLOCK_CAP and w not in CORE):
            continue
        han, short, _ = T[w]
        hpart = "" if (han in sc.han or han in DOC["han"]) else MK0 + han + MK1 + "·"   # 용어 한자는 감정서 전체에서 한 번만
        out.append(s[pos:e])
        if s.startswith("(", e):
            j = s.find(")", e)
            inner = s[e + 1:j] if j > 0 else ""
            if inner == han:
                out.append("(" + (MK0 + han + MK1 + "·" if hpart else "") + short + ")"); pos = j + 1
            elif re.search("[가-힣]", inner) and not inner.startswith(ROLES) and not (len(re.sub(r"[^가-힣]", "", inner)) <= 3 and inner not in short) and not re.match(r"[목화토금수나무불흙쇠물]{1,2}(\(|$)", inner):
                out.append("(" + hpart); pos = e + 1          # 이미 쉬운 뜻이 붙어 있어요 → 한자만 앞에
            else:
                out.append("(" + hpart + short + ", "); pos = e + 1
        else:
            out.append("(" + hpart + short + ")"); pos = e
        if mode == "text": sc.term.add(w)   # 표 칸 풀이는 감정서 전체 기준이라, 같은 장 본문에서는 한 번 더 풀어요
        sc.han.add(han); sc.n_gloss += 1; sc.blk += 1; DOC["term"].add(w); DOC["han"].add(han)
    out.append(s[pos:])
    return "".join(out)


def _han_pass(s, sc, table, prev):
    """한자 덩어리를 한글 읽기 + (처음만) 한자·오행으로"""
    out = []; pos = 0; i = 0
    runs = [m for m in RUN.finditer(s)]
    for m in runs:
        a, b = m.span(); r = m.group()
        if a > 0 and s[a - 1] == MK0: continue
        before = prev + "".join(out) + s[pos:a]
        ko = kor(r); first = r not in sc.han
        after = s[b:]
        ko_flat = ko.replace("·", "")
        # A) 이미 '읽기(한자)' 꼴: 병오(丙午)·신강(身强)·신금(辛)
        if before.endswith("(") and after.startswith(")") and \
                (before[:-1].replace("·", "").endswith(ko_flat) or (len(r) == 1 and re.search(ko_flat + r"[가-힣]{0,2}$", before[:-1]))):
            if first:
                d = el_desc(r)
                out.append(s[pos:a] + r + ("·" + d if d and not table else "")); pos = b
            else:
                seg = s[pos:a]
                if seg.endswith("("):
                    out.append(seg[:-1]); pos = b + 1
                elif "".join(out).endswith("(") and seg == "":
                    o = "".join(out)[:-1]; out = [o]; pos = b + 1
                else:
                    out.append(seg + ko); pos = b
            sc.han.add(r); continue
        # B) 괄호 안(설명 자리): 1월(丁亥) → 1월(정해·丁亥)
        inparen = before.rstrip().endswith(("(", "·", ",")) and re.match(r"[\s·,]*[^()]*\)", after) and before.rfind("(") > before.rfind(")")
        if inparen:
            out.append(s[pos:a] + ko + ("·" + MK0 + r + MK1 if first else "")); pos = b
            sc.han.add(r); continue
        # C) 합·충·형·파·해가 붙은 글자 짝: 未戌형 → 미·술 형(未戌刑·마찰·조정)
        if len(r) >= 2 and gz_only(r) and after[:1] in RELS and not is_pillar(r) or (len(r) == 2 and gz_only(r) and not is_pillar(r) and after[:1] in RELS):
            rel = after[:1]; rh, rm = RELS[rel]; key = r + rh
            if key not in sc.han and not table:
                out.append(s[pos:a] + f"{ko} {rel}({MK0}{r}{rh}{MK1}·{rm})")
            elif key not in sc.han:
                out.append(s[pos:a] + f"{ko} {rel}({MK0}{r}{MK1})")
            else:
                out.append(s[pos:a] + f"{ko} {rel}")
            pos = b + 1; sc.han.add(key); sc.han.add(r); continue
        # D) 뒤에 바로 쉬운 뜻 괄호: 戌(흙) → 술(戌·흙)
        if after.startswith("(") and re.match(r"\([가-힣·\s]+\)", after):
            out.append(s[pos:a] + (ko + "(" + MK0 + r + MK1 + "·" if first else ko + "(")); pos = b + 1
            sc.han.add(r); continue
        # E) 맨 한자
        if first:
            d = el_desc(r) if not table else ""
            out.append(s[pos:a] + ko + "(" + MK0 + r + MK1 + ("·" + d if d else "") + ")")
        elif s.strip() == r and len(r) == 1 and el_desc(r) and not table:   # release1116: 표지 기둥처럼 글자 하나만 놓인 칸은 오행을 늘 붙여요
            out.append(s[pos:a] + ko + "(" + el_desc(r) + ")")
        else:
            out.append(s[pos:a] + ko)
        pos = b; sc.han.add(r)
    out.append(s[pos:])
    return "".join(out)


TAG = re.compile(r"(<[^>]+>)")


def apply(doc, terms=True):
    """완성 문서(HTML)에 풀이를 넣어요. 한 장 = <section> 또는 <h2> 사이."""
    head, sep, body = doc.partition("<body>")
    if not sep: head, body = "", doc
    parts = TAG.split(body); DOC["term"] = set(); DOC["han"] = set()
    st = []; sc = Scope(); out = []; prev = ""
    skip = 0
    grp = None; topic_mark = False
    for i_, p in enumerate(parts):
        if p.startswith("<"):
            out.append(p)
            if p.startswith("<!--T:"): topic_mark = True
            mt = re.match(r"<(/?)([a-zA-Z0-9]+)([^>]*)>", p)
            if not mt: continue
            close, tag, attrs = mt.group(1), mt.group(2).lower(), mt.group(3)
            if tag in VOID or p.endswith("/>"): continue
            if not close:
                if tag == "table":   # 칸이 많은 표(대운×주제 등)는 칸이 좁아 풀이를 넣지 않아요
                    j = i_; ncol = 0
                    while j < len(parts) and parts[j] != "</tr>":
                        ncol += parts[j].startswith(("<th", "<td")); j += 1
                    hdr = "".join(parts[i_:j])
                    attrs = attrs + (' narrow' if ncol >= 6 or "월건" in hdr else '')   # 월별 표도 칸이 좁아요
                if tag in ("p", "li", "td", "div", "ol", "ul"): sc.blk = 0
                if tag == "section" and "flow" not in attrs:
                    sc = Scope(); prev = ""; grp = None; out.append("<!--gs-->")
                elif tag == "h2":
                    g = _group(parts, i_, topic_mark); topic_mark = False
                    if g != grp or g not in ("topic", "year", "front"):
                        sc = Scope(); prev = ""; out[-1:] = ["<!--gs-->", p]
                    grp = g
                st.append((tag, attrs))
            else:
                while st:
                    t_, _ = st.pop()
                    if t_ == tag: break
            continue
        if not p.strip() or any(t in ("style", "script") for t, _ in st):
            out.append(p); continue
        cls = " ".join(a for _, a in st)
        if "mchart" in cls and any(t == "td" and "big" in a for t, a in st):
            r = p.strip()
            if RUN.fullmatch(r) and len(r) == 1:
                d = el_desc(r)
                out.append(p + f'<span class="rd">{read(r)}{"·" + d if d else ""}</span>')
                continue
        if 'class="logo' in cls or 'class="seal' in cls or "no-gloss" in cls:
            out.append(p); continue
        table = any(t in ("td", "th", "table") for t, _ in st) or any('class="lab' in a_ for _, a_ in st)
        if table and RUN.fullmatch(p.strip()) and gz_only(p.strip()) and not any("mchart" in a_ for _, a_ in st):
            out.append(p.replace(p.strip(), kor(p.strip()))); prev = (prev + p)[-60:]; continue   # 표의 연도·월건 칸: 한글 읽기만
        heading = any(t in ("h1", "h2", "h3", "th") for t, _ in st)
        mode = "text" if not (table or heading) else "cell" if (not heading and _wide_cell(st) and len(p.strip()) >= 30) else "quiet"   # 짧은 신호 칸은 풀이 없이
        if not terms or any(t == "section" and "cover" in a_ for t, a_ in st) or any('class="sub' in a_ or (t == "p" and 'class="tiny' in a_) for t, a_ in st): mode = "quiet"   # 각주(작은 글씨)도   # 부제 줄도 풀이 없이(제목과 한 덩어리)   # 표지는 요약이라 풀이 없이(다음 쪽이 용어 쪽)
        q = _term_pass(p, sc, mode, prev)
        q = _han_pass(q, sc, table or heading, prev)
        out.append(q); prev = (prev + re.sub(MK0 + "|" + MK1, "", q))[-60:]
    res = _unnest("".join(out).replace(MK0, "").replace(MK1, ""))
    return head + sep + res if sep else res


_EL_IN = re.compile(r"(나무|불|흙|쇠|물)\((목|화|토|금|수)\)")
_BLK = re.compile(r"<(/?)(p|li|td|th|div|h\d|section|tr|table|ul|ol)\b", re.I)


def _unnest(res):
    """release1116: 괄호 안의 '물(수)'는 '물'로 — '식상(물(수))' 같은 겹괄호를 없애요(조사는 settle이 다시 맞춰요)."""
    parts = TAG.split(res); depth = 0; out = []
    for p in parts:
        if p.startswith("<"):
            if _BLK.match(p): depth = 0
            out.append(p); continue
        buf = []; i = 0
        while i < len(p):
            m = _EL_IN.match(p, i) if depth > 0 else None
            if m: buf.append(m.group(1)); i = m.end(); continue
            ch = p[i]; depth += ch == "("; depth -= ch == ")" and depth > 0
            buf.append(ch); i += 1
        out.append("".join(buf))
    return "".join(out)


def _group(parts, i, topic_mark):
    """한 '장'의 묶음: 주제 심층 여러 장은 하나, 해마다(연도) 장들도 하나로 봐요. 나머지는 장마다 새로."""
    txt = re.sub(r"<[^>]+>", "", "".join(parts[i:i + 8]))[:40]
    if topic_mark: return "topic"
    if re.search(r"용신|성격|대운|타고난|용어 쉽게", txt[:16]) and not re.search(r"\d{4}", txt[:8]): return "front"   # 용신·성격·대운 장은 한 묶음
    if re.search(r"\d{4}\s*\S+\([^)]*\)?년|\d{4} [가-힣]{2}\(", txt): return "year"
    return txt


def _wide_cell(st):
    """긴 문장이 들어가는 표 칸(판정·할 일 칸 등)에는 풀이를 넣어요. 명식표·짧은 칸은 빼요."""
    if any("mchart" in a or a.endswith(" narrow") for _, a in st): return False
    return any(t == "td" for t, _ in st) and not any(t == "th" for t, _ in st) and any(t == "td" and ("small" in a or a.strip() == "") for t, a in st) and _ROWTXT.get("on", True)


_ROWTXT = {"on": True}

GUIDE = [("원국", "原局", "타고난 여덟 글자", "평생 바탕. 운은 그 위에 오는 날씨예요."),
         ("천간·지지", "天干·地支", "위 글자·아래 글자", "위는 드러난 생각·말, 아래는 생활·환경이에요."),
         ("일간", "日干", "나를 뜻하는 글자", "모든 풀이의 기준이에요."),
         ("오행", "五行", "나무·불·흙·쇠·물", "많은 기운은 장점이자 버릇, 적은 기운은 채울 쪽."),
         ("십신", "十神", "나와 글자의 관계 10가지", "돈·일·사람·배움 중 무엇이 센지 알려 줘요."),
         ("비겁", "比劫", "자립·동료의 기운", "비견·겁재. 많으면 돈을 나눌 일이 생겨요."),
         ("식상", "食傷", "재능·표현의 기운", "식신·상관. 결과물을 내놓는 힘이에요."),
         ("재성", "財星", "돈·현실의 기운", "편재·정재. 버는 방식과 씀씀이예요."),
         ("관성", "官星", "책임·명예의 기운", "편관·정관. 일의 자리·명예·규칙이에요."),
         ("인성", "印星", "배움·도움의 기운", "편인·정인. 자격·문서·후원이에요."),
         ("신강·신약", "身强·身弱", "내 기운이 센지 약한지", "세면 흘려 쓰고, 약하면 도움을 받아요."),
         ("용신", "用神", "나를 살리는 기운", "이 기운이 오는 해·달에 일이 잘 풀려요."),
         ("희신", "喜神", "용신을 돕는 기운", "용신 다음으로 반가운 기운이에요."),
         ("기신·구신", "忌神·仇神", "부담이 되는 기운", "이 기운이 오는 해엔 지키고 보완해요."),
         ("격국", "格局", "사주의 큰 틀", "어떤 방식으로 살 때 빛나는지 보여요."),
         ("대운·세운", "大運·歲運", "10년 흐름·그해 운", "대운은 인생의 계절, 세운은 1년 날씨예요."),
         ("합·충", "合·沖", "묶임·부딪힘", "합은 인연·협력, 충은 이사·일의 변화 같은 변동."),
         ("형·파·해", "刑·破·害", "마찰·틀어짐·서운함", "서류·관계에서 조심성을 더해요."),
         ("신살", "神殺", "덧붙여 읽는 표식", "역마=이동, 도화=매력, 화개=공부·예술.")]


def guide_page(c=None, extra=None):
    """프리미엄 앞쪽: 사주 용어 쉽게 보기 (반 쪽 남짓)"""
    rows = "".join(f'<tr><td><b>{k}</b><span class="tiny">({h})</span></td><td>{a}</td><td class="tiny">{b}</td></tr>' for k, h, a, b in GUIDE)
    mine = " · ".join(v.replace("고객님: ", "").replace("지금: ", "지금 ") for v in (extra or {}).values())
    return ('<section class="page tight gloss-guide no-gloss"><div class="in">\n <h2>사주 용어 쉽게 보기</h2>'
            '<div class="sub">본문에서는 용어가 처음 나올 때 괄호로 쉬운 뜻을 한 번 더 붙였어요</div>'
            + (f'<div class="box small"><b class="gold">고객님 사주 한 줄</b> · {mine}</div>' if mine else "")
            + '<table class="gtable"><tr><th style="width:21%">용어</th><th style="width:25%">쉬운 뜻</th><th>실제로는</th></tr>' + rows + '</table>'
            '<p class="tiny" style="margin-top:1.5mm">오행 쉬운 이름: 목=나무 · 화=불 · 토=흙 · 금=쇠 · 수=물. 두 글자 기둥(예: 경신)은 위·아래 글자의 오행을 함께 적었어요.</p>'
            '</div><div class="foot">SONMYEONGRI · __PG__</div></section>')


def guide_block(c=None, extra=None):
    """흐름(.flow) 안에 넣는 용어 쪽 본문(풀이 대상 밖으로 표시)"""
    h = guide_page(c, extra)
    body = re.sub(r'^<section[^>]*><div class="in">\n?', "", h)
    body = re.sub(r'</div><div class="foot">[^<]*</div></section>$', "", body)
    return '<div class="no-gloss gloss-guide">' + body + '</div>'


# ------------------------------------------------------------------ 검사용 숫자
def stats(doc):
    """맨 한자(옆에 한글 없음) · 첫 등장 풀이율 · 장별 풀이 수"""
    body = re.sub(r"<style.*?</style>|<script.*?</script>|<div class=\"seal\">[^<]*</div>", "", doc, flags=re.S)
    body = re.sub(r"<head>.*?</head>", "", body, flags=re.S)
    body = re.sub(r'<section class="[^"]*(no-gloss|cover)[^"]*">.*?</section>', "", body, flags=re.S)
    body = re.sub(r'<div class="no-gloss gloss-guide">.*?</table>.*?</p>\s*</div>', "", body, flags=re.S)   # 용어 쪽·표지(요약)는 풀이 대상 밖
    body = re.sub(r"<h2[^>]*>.*?</h2>", "<h2>", body, flags=re.S)
    chapters = body.split("<!--gs-->") if "<!--gs-->" in body else re.split(r"<section[^>]*>|<h2>", body)
    bare = []; tot_run = 0; cov = [0, 0]; per = []; termcnt = {}; dseen = set(); miss = []; sc_cov = [0, 0]
    for ch in chapters:
        txt = re.sub(r'([\u4e00-\u9fff])<span class="rd">([^<]*)</span>', r"\2(\1)", ch)
        plain = re.sub(r"<[^>]+>", "", txt)
        import html as _h
        plain = _h.unescape(plain)
        for m in RUN.finditer(plain):
            tot_run += 1
            l, r = plain[max(0, m.start() - 8):m.start()], plain[m.end():m.end() + 1]
            ko = kor(m.group()).replace("·", "")
            near = l.replace("·", "").replace(" ", "")
            ok = (l.endswith("(") or l.endswith("·")) and re.search("[가-힣]", l[-8:])
            if not ok: bare.append(plain[max(0, m.start() - 6):m.end() + 4].replace("\n", " "))
        seen = set(); g = 0
        # 본문(표 칸·제목 빼고) 첫 등장
        ptxt = re.sub(r"<(h[1-3]|th)[^>]*>.*?</\1>", " ", ch, flags=re.S)
        ptxt = re.sub(r'<div class="sub[^"]*">.*?</div>|<p class="tiny[^"]*"[^>]*>.*?</p>', " ", ptxt, flags=re.S)   # 부제 줄은 제목처럼 풀이 없이
        ptxt = re.sub(r'<table class="mchart.*?</table>', " ", ptxt, flags=re.S)
        ptxt = re.sub(r"<table.*?</table>", " ", ptxt, flags=re.S)   # 표 칸은 감정서 전체에서 처음 한 번만 풀이해요(아래 doc_cells)
        ptxt = re.sub(r"</?(td|tr|br|div|li|p|ul|ol|table|span class=\"tiny\")[^>]*>", " ", ptxt)
        ptxt = _h.unescape(re.sub(r"<[^>]+>", "", ptxt))
        anyg = {}
        for m in TERM_RE.finditer(ptxt):
            w = m.group(1); nxt = ptxt[m.end():m.end() + 4]
            if not any(nxt.startswith(b) for b in _BAD_AFTER.get(w, ())) and not (w in DOC_ONCE and w in dseen and w not in seen):
                anyg[w] = anyg.get(w, False) or nxt.startswith("(")
            if any(nxt.startswith(b) for b in _BAD_AFTER.get(w, ())): continue
            termcnt[w] = termcnt.get(w, 0) + 1
            if w in seen or (w in DOC_ONCE and w in dseen) or _open_paren(ptxt[max(0, m.start() - 60):m.start()]): continue
            seen.add(w); dseen.add(w); cov[1] += 1
            if nxt.startswith("("): cov[0] += 1
            else: miss.append(ptxt[max(0, m.start() - 12):m.end() + 8].replace("\n", " "))
        sc_cov[0] += sum(anyg.values()); sc_cov[1] += len(anyg)
        g = len(re.findall(r"[가-힣]\((?:[\u4e00-\u9fff]+·)", plain))
        per.append(g)
    return {"hanja_runs": tot_run, "bare_hanja": len(bare), "bare_examples": bare[:15], "first_use": cov[1], "first_use_glossed": cov[0],
            "coverage_pct": round(100 * cov[0] / max(1, cov[1]), 1), "gloss_per_chapter_max": max(per) if per else 0,
            "gloss_per_chapter_avg": round(sum(per) / max(1, len([x for x in per if x])), 1), "term_counts": termcnt, "miss": miss, "scope_terms": sc_cov[1], "scope_glossed": sc_cov[0],
            "scope_coverage_pct": round(100 * sc_cov[0] / max(1, sc_cov[1]), 1)}


def guide_extra(c, year):
    """용어 쪽 '고객님 사주' 칸 (계산 결과 그대로)"""
    ex = {}
    try:
        e = c.dm_el
        ex["일간"] = f"일간 {STEM_KO[c.dm]}({c.dm}·{EL_PLAIN.get(e, e)})"
        lab = re.sub(r"\(.*?\)", "", c.st_label)
        ex["강약"] = lab
        ex["용신"] = f"용신 {c.yong}({EL_PLAIN.get(c.yong, c.yong)})"
        ex["희신"] = f"희신 {c.hee}({EL_PLAIN.get(c.hee, c.hee)})"
        ex["기신"] = f"기신 {c.gi}({EL_PLAIN.get(c.gi, c.gi)})"
        ex["격국"] = c.gyeok
        d = c.current_daeun(year)
        if d and d.get("gz"):
            g = d["gz"]; ex["대운"] = f"지금 {read(g)}({g}) 대운"
    except Exception:
        pass
    return ex
