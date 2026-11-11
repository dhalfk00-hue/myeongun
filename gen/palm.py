# -*- coding: utf-8 -*-
"""손금 섹션: 사진 + 손으로 찍은 선 좌표/특징 JSON → 오버레이 이미지 + 규칙 기반 해설 (전통 수상학 기준).
사진은 로컬에서만 처리하며 어디에도 업로드하지 않아요."""
import json, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
LABEL = {"jaeun": "재운선", "saup": "사업선", "fate": "운명선", "life": "생명선", "head": "두뇌선", "heart": "감정선"}
ORDER = ["jaeun", "saup", "fate", "life", "head", "heart"]

LUCKY = {
 "럭키M": "생명선·두뇌선·감정선 사이를 운명선이 꿰뚫어 M자를 이뤄요. 노력이 재물로 바뀌는 손이에요.",
 "삼지창": "운명선에서 태양구·수성구로 가지가 뻗어요. 일로 명성과 재물을 함께 얻는 손이에요.",
 "긴 태양선": "손바닥 아래에서 약지까지 곧게 오르는 재운선이에요. 젊어서부터 재물과 인기가 따라요.",
 "川자 상향선": "운명선·태양선·사업선이 모두 곧게 올라요. 최고의 재물 손금이에요.",
 "이중 생명선": "생명선 안쪽에 나란히 달리는 선이 있어요. 회복력과 생명력이 아주 강해요.",
 "긴 사업선": "손바닥 아래에서 소지까지 길고 뚜렷한 사업선이에요. 돈 버는 재능과 언변이 좋아요.",
 "솔로몬 링": "검지 아래를 감싸는 고리예요. 직감·이해력, 사람을 이끄는 힘이에요.",
 "태양구 별": "약지 아래의 별 문양이에요. 뜻밖의 큰 행운의 표식이에요.",
 "자수성가선": "생명선에서 위로 오르는 가지예요. 자격·실력으로 스스로 일어서요.",
 "개운선": "생명선에서 중지 쪽으로 짧게 오르는 가지예요. 그 나이에 문서·승진·결혼 같은 기회가 와요.",
 "인기선": "월구 아래의 2~3가닥 선이에요. 사람들의 인기를 얻어 일이 풀려요.",
 "직관선": "월구 가장자리에서 수성구로 휜 활 모양이에요. 직감과 통찰이 뛰어나요.",
 "막쥔손금": "두뇌선과 감정선이 한 줄로 합쳐졌어요. 강한 집중력과 추진력, 한번 정하면 끝까지 가는 손이에요.",
 "재물 3선": "운명선·재운선·사업선이 모두 뚜렷해요. 일·재물·장사 감각이 함께 받쳐 주는 최고의 재물 조합이에요.",
 "재운선 여러 가닥": "약지 아래 재운선이 여러 가닥이에요. 수입원이 여럿으로 늘어나는 금전운 손이에요.",
 "귀인선": "재운선이 손날 쪽(제2화성구)에서 올라와요. 고비마다 돈과 기회를 이어 주는 사람이 나타나요.",
 "이중 두뇌선": "두뇌선이 두 줄로 나란히 달려요. 기억력과 멀티태스킹, 두 가지 일을 함께 굴리는 머리예요.",
}


def _font(sz):
    try:
        return ImageFont.truetype(FONT, sz, index=1)
    except Exception:
        return ImageFont.load_default()


def hand_silhouette(lm, size, tr):
    """21개 손 관절 좌표 → 어두운 바탕 위 손 모양 (사진 없이)."""
    W, H = size
    im = Image.new("RGB", (W, H), (28, 22, 17))
    if len(lm) != 21:
        return im
    P = [tr(p) for p in lm]
    import math as _m
    d = lambda a, b: _m.hypot(a[0] - b[0], a[1] - b[1])
    pw = d(P[5], P[17]) or W * 0.3
    sk = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(sk)
    fill = (74, 60, 44, 255)
    # 손바닥: 손목·엄지 뿌리·손가락 뿌리 + 손날 쪽 여유
    ul = (P[17][0] + (P[17][0] - P[13][0]) * 0.5, P[17][1] + (P[17][1] - P[13][1]) * 0.5)
    w0 = (P[0][0] + (P[17][0] - P[5][0]) * 0.32, P[0][1] + (P[17][1] - P[5][1]) * 0.32)
    w1 = (P[0][0] - (P[17][0] - P[5][0]) * 0.18, P[0][1] - (P[17][1] - P[5][1]) * 0.18)
    poly = [w1, P[1], P[2], P[5], P[9], P[13], P[17], ul, w0]
    g.polygon(poly, fill=fill)
    for chain, wk in (([1, 2, 3, 4], 0.30), ([5, 6, 7, 8], 0.24), ([9, 10, 11, 12], 0.25), ([13, 14, 15, 16], 0.23), ([17, 18, 19, 20], 0.20)):
        w = max(6, int(pw * wk))
        pts = [P[i] for i in chain]
        g.line(pts, fill=fill, width=w, joint="curve")
        for q in pts: g.ellipse((q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2), fill=fill)
    sk = sk.filter(ImageFilter.GaussianBlur(1.2))
    edge = sk.split()[3].filter(ImageFilter.FIND_EDGES)
    base = Image.alpha_composite(im.convert("RGBA"), sk)
    ol = Image.new("RGBA", (W, H), (190, 150, 90, 0)); ol.putalpha(edge.point(lambda v: min(255, v * 3)))
    return Image.alpha_composite(base, ol).convert("RGB")


def render_overlay(spec, out_path, width=1200):
    """spec: photo, crop[x0,y0,x1,y1], lines{key:{pts,dashed,label,label_at}}, ages[{pt,label}] — 좌표는 원본 사진 픽셀."""
    import numpy as np
    from PIL import ImageEnhance
    if spec.get("photo"):
        im = ImageOps.exif_transpose(Image.open(spec["photo"])).convert("RGB")
        x0, y0, x1, y1 = spec.get("crop") or (0, 0, im.width, im.height)
        im = im.crop((x0, y0, x1, y1))
        sc = width / im.width
        im = im.resize((width, int(im.height * sc)), Image.LANCZOS)
        im = ImageEnhance.Brightness(im).enhance(0.78); im = ImageEnhance.Color(im).enhance(0.75)
    else:   # 앱: 사진은 기기 밖으로 안 나감 → 손 관절 좌표로 그린 손 모양 위에 선만 그림
        x0, y0, x1, y1 = spec.get("crop") or (0, 0, *spec.get("canvas", (1000, 1000)))
        sc = width / (x1 - x0)
        im = hand_silhouette(spec.get("silhouette") or [], (width, int((y1 - y0) * sc)), lambda p: ((p[0] - x0) * sc, (p[1] - y0) * sc))
    tr = lambda p: ((p[0] - x0) * sc, (p[1] - y0) * sc)
    GOLD = (232, 196, 110); GOLD2 = (255, 226, 150)
    lines = spec.get("lines", {})
    solid = {k: [tr(p) for p in v["pts"]] for k, v in lines.items() if not v.get("dashed") and len(v["pts"]) > 1}
    dash = {k: [tr(p) for p in v["pts"]] for k, v in lines.items() if v.get("dashed") and len(v["pts"]) > 1}
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    for P in solid.values(): g.line(P, fill=(255, 200, 90, 170), width=16, joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(7))
    im = Image.alpha_composite(im.convert("RGBA"), glow); d = ImageDraw.Draw(im)
    for P in solid.values(): d.line(P, fill=GOLD2 + (255,), width=7, joint="curve")
    for P in dash.values():
        P = np.array(P); L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]; t = 0
        while t < L[-1]:
            t2 = min(t + 14, L[-1])
            a = [np.interp(t, L, P[:, i]) for i in (0, 1)]; b = [np.interp(t2, L, P[:, i]) for i in (0, 1)]
            d.line([tuple(a), tuple(b)], fill=GOLD + (235,), width=6); t += 24
    F = _font(40); Fs = _font(31)
    def label(xy, txt, font):
        x, y = xy; bb = d.textbbox((x, y), txt, font=font, anchor="mm"); pad = 9
        d.rounded_rectangle((bb[0] - pad, bb[1] - pad + 2, bb[2] + pad, bb[3] + pad), radius=16, fill=(20, 16, 12, 215), outline=GOLD + (255,), width=2)
        d.text((x, y), txt, font=font, fill=GOLD2, anchor="mm")
    for k, v in lines.items():
        if v.get("label") is False: continue
        base = k.rstrip("0123456789").rstrip("B")
        txt = v.get("label") or LABEL.get(base, base)
        at = tr(v["label_at"]) if v.get("label_at") else tr(v["pts"][-1])
        label(at, txt, F if len(txt) <= 3 else Fs)
    for a in spec.get("ages", []):
        x, y = tr(a["pt"]); r = 9
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 236, 170, 255), outline=(120, 80, 20, 255), width=2)
        off = a.get("offset", [80, -52])
        label((x + off[0], y + off[1]), a["label"], Fs)
    im.convert("RGB").save(out_path, quality=90)
    return out_path


# ------------------------------------------------------------------ 해설 규칙
def _jaeun(fl, c):
    st = fl.get("state", "none"); n = fl.get("count", 1)
    tag = {"long": "길고 곧음", "above_heart": "감정선 위", "from_fate": "운명선에서 갈라짐", "from_head": "두뇌선에서 시작",
           "from_life": "생명선에서 시작", "from_moon": "월구에서 시작", "from_mars": "제2화성구에서 시작",
           "from_plain": "손바닥 가운데에서 시작", "none": "뚜렷하지 않음"}.get(st, st)
    if n >= 2 and st != "none": tag += f" · {n}가닥"
    obs = {"long": "약지 아래로 손바닥 아래쪽에서부터 곧게 올라오는 세로선이 보여요.",
           "above_heart": "약지 아래, 감정선 위쪽에만 짧은 세로선이 보여요.",
           "from_fate": "운명선에서 갈라져 약지 쪽으로 오르는 선이 보여요.",
           "from_head": "두뇌선 근처에서 시작해 약지 쪽으로 오르는 선이 보여요.",
           "from_life": "생명선 쪽에서 시작해 약지로 향하는 선이 보여요.",
           "from_moon": "새끼손가락 아래 언덕(월구)에서 약지 쪽으로 오르는 선이 보여요.",
           "from_mars": "손바닥 바깥쪽 가운데(제2화성구)에서 약지 쪽으로 오르는 선이 보여요.",
           "from_plain": "손바닥 가운데에서 시작해 약지 쪽으로 오르는 선이 보여요.",
           "none": "약지 아래로 오르는 뚜렷한 세로선은 사진에서 확인되지 않았어요."}.get(st, "")
    mean = {"long": "길고 곧은 재운선은 <b>젊어서부터 재물과 인정이 따르는</b> 손이에요.",
            "above_heart": "재운선이 감정선 위에서만 보이면 <b>50~55세 이후 재물과 복이 커지는 만년형</b>이에요.",
            "from_fate": "운명선에서 갈라진 재운선은 <b>하는 일을 바탕으로 꽃피고 승진·성과로 재물이 오는</b> 손이에요.",
            "from_head": "두뇌선에서 시작하는 재운선은 <b>재능과 아이디어가 돈이 되는</b> 손이에요.",
            "from_life": "생명선에서 시작하는 재운선은 <b>자수성가형 재물</b>이에요.",
            "from_moon": "월구에서 시작하는 재운선은 <b>대중의 인기로 버는</b> 손이에요(다소 기복은 있어요).",
            "from_mars": "제2화성구에서 시작하는 재운선은 <b>고비마다 후원자가 나타나는</b> 귀인선이에요.",
            "from_plain": "손바닥 가운데에서 시작하는 재운선은 <b>30세 이후 노력으로 성공하는</b> 손이에요.",
            "none": "재운선이 옅다고 돈이 없다는 뜻은 아니에요. <b>운명선(일)과 사주의 재물 시기를 따라 버는</b> 형이에요."}.get(st, "")
    if n >= 2 and st != "none":
        mean += " 가닥이 둘 이상이면 수입원이 여럿인 모양이라 본업 외 수입이 따라요."
    return tag, obs, mean, c.palm_cross("jaeun", st)


def _saup(fl, c):
    st = fl.get("state", "none")
    tag = {"clear": "길고 뚜렷", "faint": "희미 · 일부만 보임", "none": "보이지 않음"}[st]
    obs = {"clear": "손바닥 아래에서 새끼손가락 쪽으로 비스듬히 오르는 선이 또렷하게 이어져요.",
           "faint": "새끼손가락 쪽으로 비스듬히 오르는 옅은 선이 일부만 보여요.",
           "none": "새끼손가락 쪽으로 오르는 사업선은 사진에서 확인되지 않았어요."}[st]
    mean = {"clear": "길고 뚜렷한 사업선은 <b>돈 버는 재능·인내·언변</b>의 표식이에요(성공 손금 20번). 장사·영업·사업 감각이 좋아요.",
            "faint": "사업선이 옅으면 <b>장사·투기로 크게 벌이기보다 전문성과 꾸준함으로 버는 형</b>이에요. 나쁜 표시가 아니라 돈 버는 ‘방식’을 알려 주는 선이에요.",
            "none": "사업선이 없으면 <b>조직·전문직 안에서 실력으로 버는 형</b>이에요. 무리한 사업 확장보다 안정형 수입이 맞아요."}[st]
    if fl.get("from") == "fate": mean += " 운명선에서 시작해 실력·자격으로 큰돈을 버는 모양이에요."
    return tag, obs, mean, c.palm_cross("saup", st)


def _fate(fl, c):
    st = fl.get("state", "clear"); start = fl.get("start", "wrist"); end = fl.get("end", "heart"); br = fl.get("breaks", "none")
    if st == "none":
        return ("보이지 않음", "중지 쪽으로 오르는 운명선은 사진에서 뚜렷하게 보이지 않아요.",
                "운명선이 없으면 아직 진로를 고르는 중이라는 뜻이에요. <b>신념을 갖고 한 길을 가면 새로 생기는 선</b>이에요.", c.palm_cross("fate", "none"))
    S = {"wrist": ("손바닥 아래 중앙", "안정된 진로, 조직 안에서 꾸준히 올라가는 운"), "moon": ("월구", "창작·자유업·인기 직업으로 풀리는 운"),
         "life": ("생명선", "자격과 실력으로 스스로 일어서는 자수성가 운"), "venus": ("금성구", "가족의 영향·가업과 연결된 운"),
         "head": ("두뇌선", "35세 무렵부터 아이디어로 운이 트이는 대기만성"), "mars": ("제2화성구", "귀인의 도움으로 일이 풀리는 운"),
         "plain": ("손바닥 가운데", "젊어서는 고생해도 장년부터 빛나는 운")}
    E = {"heart": ("감정선까지", "50대 중반까지 일의 흐름이 이어져요"), "head": ("두뇌선에서 멈춤", "30대 중후반의 판단을 신중히 하라는 표시예요"),
         "middle_finger": ("중지 아래까지", "짊어질 책임이 큰 강한 운명선이에요"), "jupiter": ("검지 쪽으로 휨", "교육·봉사·의료, 명예와 리더십의 운이에요")}
    s_nm, s_mean = S.get(start, S["wrist"]); e_nm, e_mean = E.get(end, E["heart"])
    tag = ("뚜렷" if st == "clear" else "희미") + f" · {s_nm}에서 {e_nm}"
    obs = f"{s_nm}에서 시작해 중지 쪽으로 올라가 {e_nm.replace('까지', '에 닿아요').replace('에서 멈춤', '에서 멈춰요').replace('으로 휨', '으로 휘어요')}."
    obs += {"none": " 중간에 큰 끊김은 없어요.", "overlap": " 중간에 선이 겹쳐 바뀌는 구간이 있어요.", "break": " 중간에 끊긴 구간이 있어요."}[br]
    mean = f"{s_nm}에서 시작하는 운명선은 수상학에서 <b>{s_mean}</b>이에요. 유년법으로 두뇌선과 만나는 곳이 <b>35~38세</b>, 감정선과 만나는 곳이 <b>55세</b>예요. {e_mean}."
    if br == "overlap": mean += " 겹쳐 바뀌는 구간은 계획된 전직을 뜻해요."
    if br == "break": mean += " 끊긴 곳은 돌발적인 변동 시기라 그 무렵 무리한 결정은 피하세요."
    if st == "faint": mean += " 선이 옅은 편이라 일에 기복이 있을 수 있어, 한 분야를 정해 쌓을수록 선명해져요."
    return tag, obs, mean, c.palm_cross("fate", st)


def _life(fl, c):
    ln = fl.get("length", "long"); v = fl.get("venus", "wide"); j = fl.get("joined_head", True)
    tag = ("긺" if ln == "long" else "짧은 편") + (" · 금성구를 넓게 감쌈" if v == "wide" else " · 금성구가 좁은 편")
    obs = ("검지와 엄지 사이에서 " + ("두뇌선과 붙어 출발해" if j else "두뇌선과 떨어져 출발해") +
           (" 엄지 아래 두툼한 곳(금성구)을 넓게 돌아" if v == "wide" else " 엄지 쪽으로 가깝게 돌아") +
           (" 손목 가까이까지 내려가요." if ln == "long" else " 손바닥 중간쯤에서 옅어져요."))
    mean = ("금성구를 넓게 감싸는 생명선은 <b>회복력과 끈기가 좋고 정이 많은 사람</b>이에요. " if v == "wide"
            else "금성구가 좁은 생명선은 <b>예민한 만큼 체력 관리가 중요한</b> 손이에요. ")
    mean += ("긴 생명선은 에너지가 풍부하고 끈기가 강해요. " if ln == "long" else "짧은 생명선은 수명이 아니라 에너지 관리가 필요하다는 뜻이고, 생활 습관에 따라 길어지기도 해요. ")
    mean += ("두뇌선과 붙어서 시작하는 것은 가장 흔한 표준형으로, 신중하고 조심성 있는 기질이에요." if j
             else "두뇌선과 떨어져 시작하면 독립심과 개척 정신, 사업 수완이 있어요.")
    if fl.get("double"): mean += " 안쪽에 이중 생명선이 있어 회복력이 아주 강해요."
    return tag, obs, mean, c.palm_cross("life", v)


def _head(fl, c):
    ln = fl.get("length", "long"); sh = fl.get("shape", "curve"); fork = fl.get("fork", False); cm = fl.get("split_cm")
    SH = {"straight": ("직선", "현실적이고 실용적인 머리, 금융·법·과학·사업에 강해요"), "curve": ("완만한 곡선", "상상력과 상식을 함께 갖춘 머리, 예술 소질도 있어요"),
          "moon": ("월구 쪽 곡선", "상상력·기획력·감성이 풍부한 머리예요"), "mercury": ("수성구 쪽 상향", "상업·투자 감각과 말재주가 좋아요")}
    s_nm, s_mean = SH.get(sh, SH["curve"])
    tag = ("긺" if ln == "long" else "짧은 편" if ln == "short" else "손바닥 관통") + f" · {s_nm}" + (" · 끝이 두 갈래" if fork else "")
    obs = "생명선 근처에서 출발해 손바닥을 가로질러 " + {"straight": "거의 곧게 뻗어요.", "curve": "완만하게 휘어 내려가요.",
          "moon": "새끼손가락 아래 언덕(월구) 쪽으로 기울어요.", "mercury": "새끼손가락 쪽으로 살짝 올라가요."}.get(sh, "")
    if cm: obs += f" 생명선과 약 {cm}cm(사진 추정) 지점에서 갈라져요."
    if fork: obs += " 끝부분이 두 갈래로 나뉘어요."
    mean = ("긴 두뇌선은 <b>관심 폭이 넓고 장기전에 강한</b> 머리, " if ln == "long" else
            "짧은 두뇌선은 <b>실용적이고 처리가 빠른</b> 머리, " if ln == "short" else "손바닥을 관통하는 두뇌선은 <b>비범한 재능과 돈 모으는 능력</b>, ")
    mean += f"{s_nm}은 {s_mean}."
    if fork: mean += " 끝이 갈라지면 <b>현실 감각과 창의를 함께 가진</b> 사람으로 봐요."
    if cm:
        mean += " 생명선과 1~2cm 안에서 갈라지면 20대 초중반에 스스로 서는 형이에요." if cm <= 2 else " 2cm 넘게 붙어 가면 신중해서 독립이 늦은 편이에요."
    return tag, obs, mean, c.palm_cross("head", sh)


def _heart(fl, c):
    cl = fl.get("clarity", "clear"); end = fl.get("end", "index_middle"); stt = fl.get("start", "low"); fork = fl.get("fork", False)
    EN = {"index_middle": ("검지·중지 사이로", "상식적이고 안정적인 애정"), "jupiter": ("검지 아래까지", "순정파, 인격과 이상의 균형"),
          "saturn": ("중지 아래에서 멈춤", "자기 세계가 뚜렷한 애정"), "cross": ("손바닥 관통", "감정이 강하고 깊은 애정")}
    e_nm, e_mean = EN.get(end, EN["index_middle"])
    tag = ("뚜렷하고 긺" if cl == "clear" else "옅은 편") + f" · {e_nm}" + (" · 끝이 두 갈래" if fork else "")
    obs = ("새끼손가락 쪽 손바닥 가장자리의 " + ("비교적 낮은 곳" if stt == "low" else "높은 곳") + "에서 시작해 " + e_nm.replace("로", "로 들어가요.").replace("까지", "까지 이어져요.").replace("멈춤", "멈춰요.").replace("관통", "을 가로질러요."))
    mean = ("뚜렷하고 긴 감정선은 <b>정이 많고 한결같은 마음</b>이에요. " if cl == "clear" else "옅은 감정선은 <b>감정을 쉽게 드러내지 않는 신중함</b>이에요. ")
    mean += ("시작점이 낮으면 통이 크고 너그럽고, " if stt == "low" else "시작점이 높으면 원하는 것이 분명하고, ") + f"{e_nm.replace('로', '로')} 향하면 <b>{e_mean}</b>이에요."
    if fork: mean += " 끝이 갈라지면 의리 있고 현실과 이상이 조화로운 매력적인 연애를 해요."
    mean += " 주로 쓰는 손은 ‘겉으로 드러나는 감정’이라 주변에서도 그렇게 보여요."
    return tag, obs, mean, c.palm_cross("heart", end)


FUN = {"jaeun": _jaeun, "saup": _saup, "fate": _fate, "life": _life, "head": _head, "heart": _heart}


def palm_items(spec, c):
    fl = spec.get("flags", {})
    items = []
    for i, k in enumerate(ORDER):
        tag, obs, mean, cross = FUN[k](fl.get(k, {}), c)
        items.append(dict(no="①②③④⑤⑥"[i], name=LABEL[k] + (" (태양선)" if k == "jaeun" else ""), tag=tag, obs=obs, mean=mean, cross=cross))
    return items


def palm_html(spec, c, overlay_rel, start_no):
    items = palm_items(spec, c)
    lucky = spec.get("flags", {}).get("lucky", [])
    lk = " ".join(f"<b>{n}</b>: {LUCKY.get(n, '')}" for n in lucky) or "사진에서 확인되는 대표 길상(럭키M·삼지창·긴 태양선·川자·이중 생명선 등)은 뚜렷하지 않았어요. 길상이 없다고 운이 없는 것이 아니라, 사주의 시기를 따라가면 돼요."
    hand = spec.get("hand", "오른손")
    def item(it):
        return (f'<div class="lineitem"><div class="hd">{it["no"]} {it["name"]} <span class="tag">{it["tag"]}</span></div>'
                f'<div class="obs">{it["obs"]}</div><p>{it["mean"]}</p><div class="cross">사주 교차 · {it["cross"]}</div></div>')
    p1 = f'''<section class="page"><div class="in">
 <h2><span class="no">{start_no:02d}</span>손금 감정 ({hand} · 주로 쓰는 손)</h2>
 <div class="sub">전통 수상학 기준 · 재운선과 대박손금을 먼저 보고, 6대 선을 사주와 교차해 읽었어요 · 금색 선은 실제 주름을 따라 그렸어요</div>
 <div style="display:grid;grid-template-columns:80mm 1fr;gap:5mm;align-items:start">
  <div><img class="palmimg" src="{overlay_rel}"><p class="tiny" style="margin-top:1.5mm">실선 = 사진에서 확인한 주름 · 점선 = 희미하거나 일부만 보이는 구간 · 점 = 유년법 나이 지점</p>
   <div class="box" style="margin-top:2mm"><b class="gold">대박손금</b><p class="small" style="margin:1mm 0 0">{lk}</p></div></div>
  <div>{item(items[0])}{item(items[1])}</div>
 </div>
 {item(items[2])}
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''
    by = c.c.solar.year; fl = spec.get("flags", {})
    tl = []
    cm = fl.get("head", {}).get("split_cm")
    if cm: tl.append(("두뇌선·생명선 분리", "20대 초중반" if cm <= 2 else "20대 후반 이후", f"{by + 21}~{by + 25}년" if cm <= 2 else f"{by + 26}년~", "스스로 서는 시기"))
    if fl.get("fate", {}).get("state", "clear") != "none":
        tl.append(("운명선 × 두뇌선", "35~38세", f"{by + 35}~{by + 38}년", "진로의 분기점 · 판단을 신중히"))
        if fl.get("fate", {}).get("end", "heart") == "heart": tl.append(("운명선 × 감정선", "55세 전후", f"{by + 55}년 무렵", "일의 흐름이 전환되는 때"))
    if fl.get("jaeun", {}).get("state") == "above_heart": tl.append(("재운선 (감정선 위)", "50~55세 이후", f"{by + 50}년~", "만년의 재물과 복"))
    timeline = ""
    if tl:
        timeline = '<h3>손금 유년법 타임라인</h3><table><tr><th style="width:28%">지점</th><th style="width:18%">나이</th><th style="width:20%">연도</th><th>의미</th></tr>' + "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{y}</td><td class=small>{m}</td></tr>" for a, b, y, m in tl) + "</table>"
    p2 = f'''<section class="page"><div class="in">
 <h2><span class="no">{start_no:02d}</span>손금 감정 (이어서)</h2>
 <div class="sub">3대선(생명선·두뇌선·감정선)</div>
 {item(items[3])}{item(items[4])}{item(items[5])}
 {timeline}
 <p class="tiny">※ 손금은 생활에 따라 조금씩 변해요. 사진 한 장으로 본 판독이라 조명·각도에 따라 옅은 선은 놓칠 수 있어요.</p>
</div><div class="foot">SONMYEONGRI · __PG__</div></section>'''
    return [p1, p2], items, lucky
