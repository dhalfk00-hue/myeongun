/* 명운 손금 안내서: 6대 선 위치 그림(인라인 SVG), 잘 찍은 사진/아쉬운 사진 예시, 가까이 찍기 구역, 두 손가락 확대 보기.
   그림은 오른손 손바닥을 내 쪽으로 펼친 모습(엄지가 오른쪽). 왼손은 좌우만 뒤집는다. */
(function () {
  "use strict";
  const ORDER = ["sun", "business", "fate", "life", "head", "heart"];
  const NAME = { sun: "재운선", business: "사업선", fate: "운명선", life: "생명선", head: "두뇌선", heart: "감정선" };
  const ALIAS = { sun: "재물선", business: "", fate: "", life: "", head: "지능선", heart: "" };
  const COLOR = { sun: "#f3d27a", business: "#8fc3e8", fate: "#efe4cc", life: "#e0a65e", head: "#b9a8e6", heart: "#e7928a" };
  const MEAN = { sun: "재물 · 돈복", business: "장사 · 사업 감각", fate: "일 · 사회운", life: "건강 · 생활력", head: "생각 · 재능", heart: "감정 · 관계" };
  const FIND = {
    sun: "약지(넷째 손가락) 바로 아래에서 약지 쪽으로 짧게 올라가는 세로선이에요.",
    business: "손바닥 아래 가운데에서 새끼손가락 아래로 비스듬히 올라가는 선이에요.",
    fate: "손목 한가운데에서 가운뎃손가락 쪽으로 곧게 올라가는 세로선이에요.",
    life: "엄지와 검지 사이에서 시작해 엄지 아래 두툼한 살을 둥글게 감싸는 곡선이에요.",
    head: "생명선과 같은 곳에서 시작해 손바닥 한가운데를 가로지르는 선이에요.",
    heart: "손가락 바로 아래, 새끼손가락 쪽에서 검지 쪽으로 지나가는 맨 위 가로선이에요.",
  };
  // 오른손 손바닥(엄지 오른쪽), viewBox 0 0 200 260
  const D = {
    sun: "M77.5 172 C77.2 160 76.9 149 76.5 136",            // 약지 바로 아래, 약지를 향해 짧게 올라감
    business: "M108 236 C88 226 66 200 56 160",              // 손바닥 아래 가운데 → 새끼손가락 아래로 비스듬히
    fate: "M100 248 C101 210 103 168 104 126",
    life: "M149 140 C124 150 110 190 124 248",
    head: "M149 143 C122 150 92 164 60 190",
    heart: "M46 148 C74 146 100 140 125 121",
  };
  // 번호(선 위)와 이름표(선 바로 옆) 위치
  const NUM = { sun: [76.5, 131], business: [61, 180], fate: [103, 186], life: [119, 190], head: [120, 153], heart: [40, 148] };
  const TAG = { sun: [81, 157, "start"], business: [70, 238, "start"], fate: [98, 205, "end"], life: [126, 222, "start"], head: [128, 140, "middle"], heart: [47, 141, "start"] };
  const FULL = { sun: "재운선(태양선)", business: "사업선", fate: "운명선", life: "생명선", head: "두뇌선", heart: "감정선" };
  const REGIONS = [
    { id: "pinky", no: "①", t: "약지 · 새끼손가락 아래", lines: ["sun", "heart"], e: [70, 150, 36, 30] },
    { id: "center", no: "②", t: "손바닥 가운데", lines: ["fate", "business", "head"], e: [96, 188, 40, 42] },
    { id: "thumb", no: "③", t: "엄지 쪽 두툼한 곳", lines: ["life"], e: [134, 196, 28, 46] },
  ];
  const REGION_OF = { sun: "pinky", heart: "pinky", business: "center", fate: "center", head: "center", life: "thumb" };
  let uid = 0;

  function hand(id, o = {}) {
    const fill = o.fill || `url(#${id}g)`, edge = o.edge || "#9c7f48", sw = o.sw ?? 1.6;
    const shapes = [
      `<path d="M58 252 C54 220 47 180 46 146 C45 128 52 116 64 113 L138 113 C150 115 156 126 156 142 C156 160 160 176 158 196 C156 222 148 240 142 252 Z"/>`,
      `<rect x="40" y="66" width="22" height="62" rx="11" transform="rotate(-9 51 122)"/>`,
      `<rect x="64" y="32" width="24" height="92" rx="12" transform="rotate(-3 76 122)"/>`,
      `<rect x="91" y="20" width="25" height="102" rx="12.5"/>`,
      `<rect x="119" y="36" width="24" height="88" rx="12" transform="rotate(5 131 122)"/>`,
    ].join("");
    const thumb = `M150 212 C164 188 176 162 184 132`;
    return `<g fill="none" stroke="${edge}" stroke-width="${sw * 2}" stroke-linejoin="round">${shapes}<path d="${thumb}" stroke-width="${26 + sw * 2}" stroke-linecap="round"/></g>
      <g fill="${fill}" stroke="none">${shapes}<path d="${thumb}" stroke="${fill}" stroke-width="26" stroke-linecap="round" fill="none"/></g>
      ${o.creases === false ? "" : `<g stroke="${edge}" stroke-width=".7" opacity=".45" stroke-linecap="round" fill="none">
        <path d="M46 92 l12 2M44 106 l13 2"/><path d="M66 58 l18 -1M66 82 l19 -1"/><path d="M94 48 l19 0M94 76 l19 0"/><path d="M122 62 l18 2M121 88 l18 2"/><path d="M172 150 l14 6"/></g>`}`;
  }
  function defs(id) {
    return `<defs><linearGradient id="${id}g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2b2519"/><stop offset=".55" stop-color="#211c14"/><stop offset="1" stop-color="#16130e"/></linearGradient>
      <radialGradient id="${id}h" cx=".55" cy=".55" r=".5"><stop offset="0" stop-color="#f3e2b6" stop-opacity=".10"/><stop offset="1" stop-color="#f3e2b6" stop-opacity="0"/></radialGradient>
      <filter id="${id}f" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>`;
  }
  /* 손금 지도. o.only: 그 선만 강조 / o.region: 가까이 찍기 구역 표시 / o.mirror: 왼손 / o.ghost: 선 없이 손 윤곽만(촬영 틀) / o.nums: 번호 */
  function svg(o = {}) {
    const id = "pg" + (++uid), mir = o.mirror ? ` transform="translate(200 0) scale(-1 1)"` : "", X = x => o.mirror ? 200 - x : x;
    let ln = "";
    if (!o.ghost) ORDER.forEach(k => {
      const RL = o.region && (REGIONS.find(r => r.id === o.region) || {}).lines || null;
      const on = RL ? RL.includes(k) : (!o.only || o.only === k), sw = o.only ? (on ? 3.4 : 1.4) : RL ? (on ? 3.6 : 1.6) : 2.6;
      ln += `<path d="${D[k]}" fill="none" stroke="${COLOR[k]}" stroke-width="${sw}" stroke-linecap="round" opacity="${on ? 1 : 0.16}"${on ? ` filter="url(#${id}f)"` : ""}/>`;
    });
    let rg = "";
    if (o.region) { const R = REGIONS.find(r => r.id === o.region); if (R) rg = `<ellipse cx="${R.e[0]}" cy="${R.e[1]}" rx="${R.e[2]}" ry="${R.e[3]}" fill="rgba(243,226,182,.16)" stroke="#f3e2b6" stroke-width="3" stroke-dasharray="7 5"/>`; }
    let nums = "";
    if (o.nums && !o.ghost) ORDER.forEach((k, i) => { const [x, y] = NUM[k], [tx, ty, an] = TAG[k], A = o.mirror ? { start: "end", end: "start", middle: "middle" }[an] : an;
      nums += `<g><circle cx="${X(x)}" cy="${y}" r="4.8" fill="#0b0d14" stroke="${COLOR[k]}" stroke-width="1.1"/><text x="${X(x)}" y="${y + 2.3}" font-size="6.6" text-anchor="middle" fill="${COLOR[k]}" font-family="var(--serif)" font-weight="700">${i + 1}</text>
        <text x="${X(tx)}" y="${ty}" font-size="6.6" text-anchor="${A}" fill="${COLOR[k]}" font-family="var(--sans)" font-weight="600" style="paint-order:stroke;stroke:#17140f;stroke-width:2.4px;stroke-linejoin:round">${NAME[k]}</text></g>`; });
    const lab = o.labels ? `<g font-size="8" fill="#9a9384" font-family="var(--sans)" letter-spacing=".08em"><text x="${X(o.mirror ? 186 : 14)}" y="20" text-anchor="${o.mirror ? "end" : "start"}">${o.mirror ? "왼손" : "오른손"} 손바닥</text>
      <text x="${X(184)}" y="112" text-anchor="middle">엄지</text><text x="${X(51)}" y="58" text-anchor="middle">새끼</text><text x="${X(76)}" y="25" text-anchor="middle">약지</text><text x="${X(103.5)}" y="13" text-anchor="middle">중지</text><text x="${X(131)}" y="29" text-anchor="middle">검지</text><text x="${X(100)}" y="259" text-anchor="middle">손목</text></g>` : "";
    return `<svg class="pg${o.cls ? " " + o.cls : ""}" viewBox="0 0 200 262" role="img" aria-label="손금 위치 그림">${defs(id)}<g${mir}>${o.ghost ? hand(id, { fill: "#11131b", edge: "rgba(214,185,124,.6)", sw: .6, creases: false }) : hand(id)}<ellipse cx="100" cy="180" rx="60" ry="70" fill="url(#${id}h)"/>${rg}${ln}</g>${nums}${lab}</svg>`;
  }

  /* 잘 찍은 사진 / 아쉬운 사진 예시 그림 */
  function example(kind) {
    const id = "pe" + (++uid);
    const bg = { good: "#3b3427", dark: "#0c0b09", far: "#3b3427", blur: "#3b3427", bent: "#3b3427" }[kind];
    const ok = kind === "good";
    const tf = { good: "translate(10 4) scale(.9)", dark: "translate(10 4) scale(.9)", far: "translate(62 66) scale(.38)", blur: "translate(10 4) scale(.9)", bent: "translate(10 4) scale(.9)" }[kind];
    const skin = kind === "dark" ? "#1d1912" : "#c9a87e", edge = kind === "dark" ? "#2a241a" : "#8a6b45";
    const blur = kind === "blur" ? `<filter id="${id}b"><feGaussianBlur stdDeviation="4"/></filter>` : "";
    const mark = ok ? `<circle cx="178" cy="22" r="14" fill="#8fc6a2"/><path d="M171 22 l5 5 l9 -10" stroke="#0b0d14" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`
      : `<circle cx="178" cy="22" r="14" fill="#e7928a"/><path d="M172 16 l12 12 M184 16 l-12 12" stroke="#0b0d14" stroke-width="3" stroke-linecap="round"/>`;
    const bent = kind === "bent" ? `<g transform="rotate(-14 100 140)"></g>` : "";
    let h = hand(id, { fill: skin, edge, sw: .8, creases: false });
    if (kind === "bent") h = `<g transform="translate(0 30) scale(1 .78) skewX(-10)">${h}</g>`;
    const lines = kind === "dark" ? "" : `<g stroke="#6b4f2e" stroke-width="2" fill="none" stroke-linecap="round" opacity=".85"><path d="${D.life}"/><path d="${D.head}"/><path d="${D.heart}"/><path d="${D.fate}" stroke-width="1.3"/></g>`;
    const sun = kind === "good" || kind === "blur" || kind === "bent" ? `<circle cx="40" cy="40" r="26" fill="#fff6d8" opacity=".10"/>` : "";
    return `<svg viewBox="0 0 200 262" aria-hidden="true"><defs>${blur}</defs><rect width="200" height="262" rx="16" fill="${bg}"/>${sun}
      <g transform="${tf}"${kind === "blur" ? ` filter="url(#${id}b)"` : ""}>${h}${lines}</g>${bent}${mark}</svg>`;
  }
  const EXAMPLES = [["good", "밝은 곳 · 손바닥이 화면 가득"], ["dark", "어두우면 주름이 안 보여요"], ["far", "너무 멀면 선이 뭉개져요"], ["blur", "흔들리면 선이 번져요"]];
  const exampleHTML = () => `<div class="pex">${EXAMPLES.map(([k, t]) => `<figure class="${k === "good" ? "ok" : "no"}">${example(k)}<figcaption>${t}</figcaption></figure>`).join("")}</div>`;

  /* 손금 지도 전체 안내 (시트) */
  function open(o = {}) {
    const bg = document.createElement("div"); bg.className = "sheet-bg pguide-bg";
    bg.innerHTML = `<div class="sheet pguide" role="dialog" aria-label="손금 위치 안내"><div class="grip"></div>
      <div class="step">手相 · 손금 지도</div><h3>내 손금, 어디에 있을까요?</h3>
      <p class="mini" style="margin:0">${o.mirror ? "왼손" : "오른손"} 손바닥을 내 쪽으로 펼친 모습이에요. ${o.mirror ? "오른손은" : "왼손은"} 좌우만 바뀌어요.</p>
      <div class="pg-big">${svg({ nums: true, labels: true, mirror: o.mirror })}</div>
      <ol class="pg-list">${ORDER.map((k, i) => `<li style="--c:${COLOR[k]}"><em>${i + 1}</em><div><b>${FULL[k]}</b>${ALIAS[k] ? `<span class="al">${ALIAS[k]}</span>` : ""}<span class="mn">${MEAN[k]}</span><p>${FIND[k]}</p></div></li>`).join("")}</ol>
      <div class="pg-tip"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a6 6 0 0 0-3.5 10.9V16h7v-2.1A6 6 0 0 0 12 3zM9.5 19h5M10.5 21.5h3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
        <p><b>손을 살짝 오므리면 주름이 진해져요.</b> 찾기 어려운 선은 손을 살짝 오므렸다 펴면서 보세요. 재운선·사업선은 없거나 희미한 분도 많아요.</p></div>
      <div class="pg-act">${o.first ? `<button class="btn btn-gold" data-x="ok">알겠어요, 찍으러 갈게요</button><button class="btn btn-ghost" data-x="skip">건너뛰기</button>` : `<button class="btn btn-gold" data-x="ok">확인했어요</button>`}</div></div>`;
    const close = () => { bg.remove(); document.body.classList.remove("noscroll"); o.onClose && o.onClose(); };
    bg.addEventListener("click", e => { if (e.target === bg || e.target.closest("[data-x]")) close(); });
    document.body.appendChild(bg); document.body.classList.add("noscroll");
    return bg;
  }

  /* 두 손가락 확대 · 끌어서 이동 · 두 번 톡 = 2.5배 */
  function zoomer(box) {
    const el = box.firstElementChild; let s = 1, tx = 0, ty = 0, lastTap = 0; const P = new Map();
    const rect = () => box.getBoundingClientRect();
    const clamp = () => { const w = box.clientWidth, h = box.clientHeight; s = Math.max(1, Math.min(6, s)); tx = Math.min(0, Math.max(w - w * s, tx)); ty = Math.min(0, Math.max(h - h * s, ty)); };
    const draw = () => { clamp(); el.style.transform = `translate(${tx}px,${ty}px) scale(${s})`; box.classList.toggle("zoomed", s > 1.01); };
    const pts = () => [...P.values()];
    box.addEventListener("pointerdown", e => {
      const r = rect(); P.set(e.pointerId, [e.clientX - r.left, e.clientY - r.top]); box.setPointerCapture(e.pointerId);
      if (P.size === 1) { const now = Date.now(); if (now - lastTap < 300) { const [x, y] = P.get(e.pointerId), ns = s > 1.2 ? 1 : 2.5; tx = x - (x - tx) / s * ns; ty = y - (y - ty) / s * ns; s = ns; draw(); lastTap = 0; } else lastTap = now; }
    });
    box.addEventListener("pointermove", e => {
      if (!P.has(e.pointerId)) return; const r = rect(), before = pts(), np = [e.clientX - r.left, e.clientY - r.top];
      if (P.size === 2) {
        const [a, b] = before, other = a === P.get(e.pointerId) ? b : a;
        const c0 = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], d0 = Math.hypot(a[0] - b[0], a[1] - b[1]) || 1;
        const c1 = [(np[0] + other[0]) / 2, (np[1] + other[1]) / 2], d1 = Math.hypot(np[0] - other[0], np[1] - other[1]) || 1;
        const ns = Math.max(1, Math.min(6, s * d1 / d0));
        tx = c1[0] - (c0[0] - tx) / s * ns; ty = c1[1] - (c0[1] - ty) / s * ns; s = ns;
      } else if (P.size === 1 && s > 1) { const p = P.get(e.pointerId); tx += np[0] - p[0]; ty += np[1] - p[1]; }
      P.set(e.pointerId, np); draw(); e.preventDefault();
    });
    const up = e => P.delete(e.pointerId);
    box.addEventListener("pointerup", up); box.addEventListener("pointercancel", up);
    box.addEventListener("wheel", e => { e.preventDefault(); const r = rect(), x = e.clientX - r.left, y = e.clientY - r.top, ns = Math.max(1, Math.min(6, s * (e.deltaY < 0 ? 1.2 : 1 / 1.2))); tx = x - (x - tx) / s * ns; ty = y - (y - ty) / s * ns; s = ns; draw(); }, { passive: false });
    return { set(ns, x, y) { tx = x - (x - tx) / s * ns; ty = y - (y - ty) / s * ns; s = ns; draw(); }, get scale() { return s; } };
  }

  window.PalmGuide = { ORDER, NAME, FULL, COLOR, MEAN, FIND, REGIONS, REGION_OF, svg, open, exampleHTML, zoomer };
})();
