/* 명운 손금: 촬영 안내 → 사진 품질 확인 → 기기 안에서 6대 선 자동 검출 → 선마다 확인·끌어서 고치기 → 풀이
   사진은 이 기기 밖으로 보내지 않는다. 서버에는 선 좌표·손 관절 좌표·특징(글자)만 보낸다. */
(function () {
  "use strict";
  const { $, $$, esc, api, store, birthForm, wireBirth, readBirth, lockHTML, wireLock, loadingHTML, unlockOf, ic, stars } = window.MW;
  const ORDER = ["sun", "business", "fate", "life", "head", "heart"];          // 돈 먼저
  const NAME = { sun: "재운선", business: "사업선", fate: "운명선", life: "생명선", head: "두뇌선", heart: "감정선" };
  const RULE = { sun: "태양선(재물선)", business: "사업선", fate: "운명선", life: "생명선", head: "두뇌선", heart: "감정선" };
  const COLOR = { sun: "#f3d27a", business: "#8fc3e8", fate: "#efe4cc", life: "#e0a65e", head: "#b9a8e6", heart: "#e7928a" };
  const WHERE = {
    sun: "약지(넷째 손가락) 아래로 올라가는 세로선이에요. 재물·돈복을 봐요.",
    business: "손바닥 아래에서 새끼손가락 쪽으로 비스듬히 오르는 선이에요. 장사·사업 감각을 봐요.",
    fate: "손목 쪽에서 가운뎃손가락으로 올라가는 세로선이에요. 일과 사회운을 봐요.",
    life: "엄지와 검지 사이에서 시작해 엄지 아래 두툼한 곳을 감싸고 내려가요. 건강·생활력이에요.",
    head: "엄지와 검지 사이에서 손바닥을 가로지르는 선이에요. 생각·재능이에요.",
    heart: "새끼손가락 아래에서 검지 쪽으로 가로지르는 맨 위 선이에요. 감정·관계예요.",
  };
  let S = null, root = null;

  const guide = `<svg viewBox="0 0 100 120" aria-hidden="true"><path d="M33 116 L31 88 Q22 78 14 62 Q11 55 16 52 Q21 50 25 56 L33 68 L34 46 L34 18 Q34 12 39 12 Q44 12 44 18 L44 44 L46 44 L46 10 Q46 4 51 4 Q56 4 56 10 L56 44 L58 44 L58 14 Q58 8 63 8 Q68 8 68 14 L68 46 L70 47 L70 26 Q70 21 74 21 Q78 21 78 26 L78 56 Q81 76 79 96 L77 116 Z" fill="none" stroke="currentColor" stroke-width=".7" stroke-dasharray="1.6 1.8"/>
    <path d="M34 56 C46 64 50 90 45 110" fill="none" stroke="currentColor" stroke-width=".55" opacity=".55"/><path d="M35 57 Q55 63 74 76" fill="none" stroke="currentColor" stroke-width=".55" opacity=".55"/><path d="M78 60 Q63 58 47 50" fill="none" stroke="currentColor" stroke-width=".55" opacity=".55"/></svg>`;
  const dom = () => store.get("palmDom") === "왼손" ? "왼손" : "오른손";

  /* ---------- 1. 촬영 안내 ---------- */
  function capture(msg) {
    const me = store.get("me"), d = dom();
    root.innerHTML = `<div class="card pcap rv"><div class="step">手相 · 손금 재물운</div><div class="title">손바닥 사진 한 장이면 돼요</div>
      <p class="lead">재물운은 <b>주로 쓰는 손</b>으로 봐요. 남녀 구분 없이 같은 기준이에요.</p>
      <div class="seg" id="pf-dom" style="margin-top:16px">${["오른손", "왼손"].map(h => `<button type="button" data-v="${h}"${h === d ? ' class="on"' : ""}>${h}잡이</button>`).join("")}</div>
      <div class="frame">${guide}<i class="scan"></i><p><b id="pf-dt">${d}</b> 손바닥을 펴고 손가락은 붙여 주세요</p></div>
      <ul class="tips"><li><em>01</em>밝은 곳, 그림자 없이</li><li><em>02</em>손가락은 붙이고 쭉</li><li><em>03</em>손목까지 화면 안에</li><li><em>04</em>흔들림 없이 정면에서</li></ul>
      ${msg ? `<p class="err">${esc(msg)}</p>` : ""}
      <div class="row2"><label class="btn btn-gold">${ic("cam")}촬영하기<input type="file" accept="image/*" capture="environment" hidden></label>
        <label class="btn btn-line">${ic("img")}앨범에서<input type="file" accept="image/*" hidden></label></div>
      <label class="chk" style="margin-top:20px"><input type="checkbox" id="pf-use"${me ? " checked" : ""}> 내 사주와 함께 보기 <span class="mini">돈 들어오는 시기 · 감정서</span></label>
      <div id="pf-bw"${me ? "" : " hidden"}>${birthForm("pf", { value: me || {} })}</div>
      <p class="privacy-note">${ic("shield")}<span>사진은 이 폰 안에서만 분석해요. 서버로 보내지도, 저장하지도 않아요.</span></p></div>`;
    wireBirth(root, "pf");
    $("#pf-dom", root).onclick = e => { const b = e.target.closest("button"); if (!b) return; store.set("palmDom", b.dataset.v);
      $$("#pf-dom button", root).forEach(x => x.classList.toggle("on", x === b)); $("#pf-dt", root).textContent = b.dataset.v; };
    $("#pf-use", root).onchange = e => { $("#pf-bw", root).hidden = !e.target.checked; };
    $$("input[type=file]", root).forEach(inp => inp.onchange = () => { const f = inp.files[0]; inp.value = ""; if (f) start(f); });
    window.PalmDetect.loadLandmarker().catch(() => { });
  }

  async function loadImage(file, max = 1600) {
    const url = URL.createObjectURL(file), img = new Image(); img.src = url; await img.decode();
    const k = Math.min(1, max / Math.max(img.naturalWidth, img.naturalHeight)), c = document.createElement("canvas");
    c.width = Math.round(img.naturalWidth * k); c.height = Math.round(img.naturalHeight * k);
    c.getContext("2d").drawImage(img, 0, 0, c.width, c.height); URL.revokeObjectURL(url); return c;
  }

  /* ---------- 2. 품질 확인 + 자동 검출 ---------- */
  async function start(file, force) {
    let birth = null;
    if ($("#pf-use", root)?.checked) { try { birth = readBirth(root, "pf"); store.set("me", birth); } catch (e) { alert(e.message); return; } }
    const canvas = file instanceof HTMLCanvasElement ? file : await loadImage(file);
    S = { canvas, birth, hand: dom(), edits: {}, done: {}, idx: 0 };
    const q = window.PalmDetect.quality(canvas); S.q = q;
    if (!force && (q.dark || q.blurry || q.bright)) return qualityFail(q);
    progress("손 모양과 관절 21곳을 찾는 중");
    let res;
    try { res = await window.PalmDetect.analyze(canvas, { hand: S.hand, onProgress: s => progress({ hand: "손 모양과 관절 21곳을 찾는 중", crease: "손바닥 주름 지도를 만드는 중", lines: "재운선 · 사업선 · 운명선 · 3대선을 따라가는 중" }[s] || "") }); }
    catch (e) { console.error(e); res = { ok: false }; }
    if (!res.ok) return capture("손을 찾지 못했어요. 손바닥 전체와 손목이 보이게, 밝은 곳에서 다시 찍어 주세요.");
    S.res = res; S.box = cropBox(res); S.mismatch = res.side !== S.hand;
    confirmStep();
  }
  function qualityFail(q) {
    const msgs = [q.dark && "사진이 어두워요", q.bright && "빛이 너무 강해 주름이 날아갔어요", q.blurry && "사진이 흔들렸거나 초점이 안 맞았어요"].filter(Boolean);
    root.innerHTML = `<div class="card rv"><div class="step">사진 품질 확인</div><div class="title">다시 찍으면 더 정확해요</div>
      <div class="stage" style="max-width:240px;margin-top:14px"><canvas id="pf-q"></canvas></div>
      <div class="qbar"><span class="${q.dark || q.bright ? "bad" : ""}">밝기 · ${q.dark ? "어두움" : q.bright ? "너무 밝음" : "좋음"}</span><span class="${q.blurry ? "bad" : ""}">선명도 · ${q.blurry ? "흐림" : "좋음"}</span></div>
      <p class="lead">${msgs.join(" · ")}. 손금은 가는 주름이라 밝고 선명해야 제대로 그려져요.</p>
      <ul class="tips"><li><em>01</em>창가나 형광등 아래</li><li><em>02</em>폰을 손바닥과 나란히</li><li><em>03</em>초점을 손바닥에 톡</li><li><em>04</em>플래시 반사 피하기</li></ul>
      <button class="btn btn-gold" id="pf-re">${ic("cam")}다시 찍기</button>
      <button class="btn btn-ghost" style="margin-top:6px" id="pf-force">그래도 이 사진으로 볼게요</button></div>`;
    const c = $("#pf-q", root), k = 520 / S.canvas.width; c.width = 520; c.height = Math.round(S.canvas.height * k); c.getContext("2d").drawImage(S.canvas, 0, 0, c.width, c.height);
    $("#pf-re", root).onclick = () => capture();
    $("#pf-force", root).onclick = () => { const cv = S.canvas, b = S.birth; capture(); if (b) { } start(cv, true); };
  }
  function progress(t) { root.innerHTML = `${loadingHTML(esc(t), "이 폰 안에서 분석 중", "手")}<p class="privacy-note" style="max-width:300px;margin:0 auto">${ic("shield")}<span>사진은 서버로 보내지 않아요</span></p>`; }

  function cropBox(res) {
    const all = res.landmarks.slice(); ORDER.forEach(k => (res.lines[k]?.img || []).forEach(p => all.push(p)));
    const xs = all.map(p => p[0]), ys = all.map(p => p[1]);
    let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys); const m = Math.max(x1 - x0, y1 - y0) * 0.06;
    x0 = Math.max(0, x0 - m); y0 = Math.max(0, y0 - m); x1 = Math.min(S.canvas.width, x1 + m); y1 = Math.min(S.canvas.height, y1 + m);
    // 손바닥 위주로: 손가락 끝까지 다 보이면 너무 작아지므로 손가락 중간까지만
    const tipY = Math.min(...[8, 12, 16].map(i => res.landmarks[i][1])), midY = Math.min(...[6, 10, 14].map(i => res.landmarks[i][1]));
    if (res.landmarks[0][1] > midY) y0 = Math.max(y0, midY - (midY - tipY) * 0.2);
    return [x0, y0, x1 - x0, y1 - y0];
  }

  /* ---------- 사진 + 선 그리기 ---------- */
  const pathD = pts => pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join("");
  function stageHTML(id) { const [, , w, h] = S.box; return `<div class="stage" id="${id}" style="aspect-ratio:${w}/${h};max-width:calc(58vh * ${(w / h).toFixed(3)})"><canvas></canvas><svg></svg></div>`; }
  function paintStage(id) {
    const st = $("#" + id, root), cv = $("canvas", st), [bx, by, bw, bh] = S.box, k = Math.min(1, 1000 / bw);
    cv.width = Math.round(bw * k); cv.height = Math.round(bh * k);
    const x = cv.getContext("2d"); x.filter = "brightness(0.56) contrast(1.15) saturate(0.45) sepia(0.15)"; x.drawImage(S.canvas, bx, by, bw, bh, 0, 0, cv.width, cv.height); x.filter = "none";
    const vg = x.createRadialGradient(cv.width / 2, cv.height * 0.55, Math.min(cv.width, cv.height) * 0.3, cv.width / 2, cv.height * 0.55, Math.max(cv.width, cv.height) * 0.75);
    vg.addColorStop(0, "rgba(8,9,14,0)"); vg.addColorStop(1, "rgba(8,9,14,0.72)"); x.fillStyle = vg; x.fillRect(0, 0, cv.width, cv.height);
    $("svg", st).setAttribute("viewBox", `${bx} ${by} ${bw} ${bh}`);
    return $("svg", st);
  }
  function linesSVG(focus, opt = {}) {
    const [, , bw] = S.box, sw = bw * 0.012, fs = bw * 0.034, placed = []; let h = "";
    ORDER.forEach(k => {
      const L = S.res.lines[k]; if (!L || !L.img?.length || (opt.skip === k)) return;
      const faint = L.conf !== "high" || L.estimated, dim = focus && focus !== k ? " dim" : "";
      const w = (focus === k ? 1.35 : 1) * sw;
      h += `<path class="pl${faint ? " faint" : ""}${dim}" d="${pathD(L.img)}" style="stroke:${COLOR[k]};stroke-width:${w}px;--dash:${sw * 1.8}px;filter:drop-shadow(0 0 ${sw * 0.8}px ${COLOR[k]})"/>`;
      if (L.double?.img?.length && L.conf === "high") h += `<path class="pl${dim}" d="${pathD(L.double.img)}" style="stroke:${COLOR[k]};stroke-width:${w * 0.8}px"/>`;
      (L.extra || []).forEach(e => { if (e.img?.length) h += `<path class="pl faint${dim}" d="${pathD(e.img)}" style="stroke:${COLOR[k]};stroke-width:${w * 0.8}px;--dash:${sw * 1.8}px"/>`; });
      if (opt.labels) {
        const p = k === "life" ? L.img[Math.floor(L.img.length * 0.7)] : k === "heart" ? L.img[0] : k === "fate" ? L.img[Math.floor(L.img.length * 0.3)] : L.img.at(-1);
        const t = NAME[k] + (faint ? "·희미" : ""), tw = fs * (t.length * 0.95 + 0.8);
        const lx = Math.max(S.box[0] + 2, Math.min(S.box[0] + bw - tw - 2, p[0] - tw / 2)); let ly = Math.max(S.box[1] + 2, p[1] - fs * 2);
        const hit = y => placed.some(q => lx < q[0] + q[2] && lx + tw > q[0] && y < q[1] + fs * 1.6 && y + fs * 1.6 > q[1]);
        for (let t = 1; t < 9 && hit(ly); t++) ly = Math.max(S.box[1] + 2, p[1] - fs * 2 + (t % 2 ? 1 : -1) * Math.ceil(t / 2) * fs * 1.7);
        placed.push([lx, ly, tw]);
        h += `<g class="lbl${dim}"><rect x="${lx}" y="${ly}" width="${tw}" height="${fs * 1.45}" rx="${fs * 0.7}" style="stroke:${COLOR[k]};stroke-width:${sw * 0.3}px"/><text x="${lx + tw / 2}" y="${ly + fs * 1.05}" font-size="${fs}" text-anchor="middle" fill="${COLOR[k]}">${t}</text></g>`;
        (L.ticks || []).forEach(tk => { if (!tk.img) return; h += `<g class="lbl${dim}"><circle cx="${tk.img[0]}" cy="${tk.img[1]}" r="${sw * 1.2}" fill="${COLOR[k]}"/><text x="${tk.img[0] + sw * 2}" y="${tk.img[1] - sw}" font-size="${fs * 0.75}" style="fill:#fff;paint-order:stroke;stroke:#000;stroke-width:${sw * 0.4}px">${tk.label}</text></g>`; });
      }
    });
    if (opt.labels) (S.res.big || []).forEach(b => { if (!b.atImg) return; h += `<text x="${b.atImg[0]}" y="${b.atImg[1]}" font-size="${fs * 1.3}" text-anchor="middle" style="fill:#ffd84d;paint-order:stroke;stroke:#5a3a00;stroke-width:${sw * 0.4}px">★</text>`; });
    return h;
  }

  /* ---------- 3. 선마다 확인 ---------- */
  function stLabel(L) {
    if (!L || L.conf === "none" || !L.img?.length) return `<span class="st none">못 찾음</span>`;
    if (L.estimated) return `<span class="st mid">추정 위치</span>`;
    return L.conf === "high" ? `<span class="st hi">뚜렷</span>` : `<span class="st mid">희미함</span>`;
  }
  function confirmStep() {
    const k = ORDER[S.idx], L = S.res.lines[k], none = !L || L.conf === "none" || !L.img?.length;
    root.innerHTML = `<div class="card confirm rv">
      <div class="dots">${ORDER.map((x, i) => `<i class="${i === S.idx ? "on" : i < S.idx ? "done" : ""}"></i>`).join("")}</div>
      <div class="step">${S.idx + 1} / 6 · 선 확인</div>
      <h3>${NAME[k]} ${stLabel(L)}</h3><p class="mini" style="margin:0 0 14px">${WHERE[k]}</p>
      ${S.mismatch && S.idx === 0 ? `<p class="note" style="color:var(--warn);margin:0 0 12px">${ic("alert")}<span>사진 속 손이 ${S.res.side}으로 보여요. ${S.hand}잡이라면 ${S.hand} 사진이 더 정확해요.</span></p>` : ""}
      ${S.res.cut && S.idx === 0 ? `<p class="note" style="color:var(--warn);margin:0 0 12px">${ic("alert")}<span>손 일부가 사진 밖으로 잘렸어요. 선 위치가 덜 정확할 수 있어요.</span></p>` : ""}
      ${stageHTML("pf-st")}
      <p id="pf-msg" class="lead" style="margin:16px 0 14px;font-size:14px">${none ? `이 사진에서는 ${NAME[k]}을 찾지 못했어요. 없거나 아주 희미한 분도 많아요.` : L.estimated ? "주름이 흐려서 보통 이 선이 있는 자리에 점선으로 표시했어요." : "빛나는 선이 실제 손금과 맞나요?"}</p>
      <div class="row2" id="pf-acts">${none
        ? `<button class="btn btn-gold" id="pf-ok">없는 게 맞아요</button><button class="btn btn-line" id="pf-draw">있어요, 그릴게요</button>`
        : `<button class="btn btn-gold" id="pf-ok">맞아요</button><button class="btn btn-line" id="pf-edit">조금 달라요</button>`}</div>
      ${none ? "" : `<button class="btn btn-ghost" style="margin-top:6px" id="pf-noline">이 자리에 선이 없어요</button>`}
      ${S.idx === 0 ? `<button class="btn btn-ghost" style="font-size:13px" id="pf-skip">자동 결과 그대로 보기</button>` : ""}</div>`;
    const svg = paintStage("pf-st"); svg.innerHTML = linesSVG(k);
    const next = () => { S.idx++; if (S.idx >= ORDER.length) finish(); else confirmStep(); };
    $("#pf-ok", root).onclick = () => { if (!none && L.estimated) S.edits[k] = L.img; next(); };
    $("#pf-edit", root) && ($("#pf-edit", root).onclick = () => editMode(k, L.img));
    $("#pf-draw", root) && ($("#pf-draw", root).onclick = () => editMode(k, window.PalmDetect.seed(S.res, k), true));
    $("#pf-noline", root) && ($("#pf-noline", root).onclick = () => { S.edits[k] = null; S.res.lines[k] = { ...L, img: [], conf: "none" }; next(); });
    $("#pf-skip", root) && ($("#pf-skip", root).onclick = () => finish());
  }

  /* 끌어서 고치기: 선 위 조절점 6개 → 손가락으로 끌면 곡선이 따라옴 */
  function resampleN(pts, n) {
    const d = [0]; for (let i = 1; i < pts.length; i++) d.push(d[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const out = []; for (let j = 0; j < n; j++) { const t = d.at(-1) * j / (n - 1); let i = d.findIndex(v => v >= t); i = Math.max(1, i);
      const a = pts[i - 1], b = pts[i], f = (t - d[i - 1]) / ((d[i] - d[i - 1]) || 1); out.push([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]); }
    return out;
  }
  function editMode(k, pts, isNew) {
    const cps = resampleN(pts, 6), svg = $("#pf-st svg", root), [, , bw] = S.box, r = bw * 0.028;
    $("#pf-msg", root).innerHTML = `<b>동그라미를 끌어서</b> 실제 ${NAME[k]} 주름 위에 맞춰 주세요.${isNew ? " 직접 그린 선은 '희미함'으로 풀이해요." : ""}`;
    $("#pf-acts", root).innerHTML = `<button class="btn btn-gold" id="pf-save">이대로 확정</button><button class="btn btn-line" id="pf-cancel">원래대로</button>`;
    $("#pf-noline", root)?.remove(); $("#pf-skip", root)?.remove();
    const draw = () => {
      const curve = window.PalmDetect.catmull(cps, 10);
      svg.innerHTML = linesSVG(k, { skip: k }) + `<path class="pl" d="${pathD(curve)}" style="stroke:${COLOR[k]};stroke-width:${bw * 0.014}px"/>` +
        cps.map((p, i) => `<circle class="cp" data-i="${i}" cx="${p[0]}" cy="${p[1]}" r="${r}" style="stroke-width:${r * 0.35}px"/>`).join("");
      return curve;
    };
    let curve = draw(), drag = -1;
    const toSvg = e => { const p = svg.createSVGPoint(); p.x = e.clientX; p.y = e.clientY; const q = p.matrixTransform(svg.getScreenCTM().inverse()); return [q.x, q.y]; };
    svg.onpointerdown = e => { const c = e.target.closest(".cp"); if (!c) return; drag = +c.dataset.i; svg.setPointerCapture(e.pointerId); e.preventDefault(); };
    svg.onpointermove = e => { if (drag < 0) return; cps[drag] = toSvg(e); curve = draw(); };
    svg.onpointerup = svg.onpointercancel = () => { drag = -1; };
    $("#pf-save", root).onclick = () => {
      S.edits[k] = curve;
      S.res.lines[k] = { ...(S.res.lines[k] || {}), img: curve, conf: isNew ? "mid" : S.res.lines[k].conf, estimated: false };
      S.idx++; if (S.idx >= ORDER.length) finish(); else confirmStep();
    };
    $("#pf-cancel", root).onclick = () => confirmStep();
  }

  /* ---------- 4. 서버 풀이 (좌표·특징만) ---------- */
  function payload() {
    const lines = {};
    ORDER.forEach(k => { const L = S.res.lines[k]; if (!L) return;
      lines[k] = { pts: L.img || [], conf: !L.img?.length ? "none" : L.estimated ? "low" : L.conf, user: !!L.user,
        double: L.double?.img || null, extra: (L.extra || []).map(e => e.img).filter(Boolean), ticks: (L.ticks || []).filter(t => t.img).map(t => ({ pt: t.img, label: t.label })) }; });
    const f = JSON.parse(JSON.stringify(S.res.features)); delete f._measure;
    const [x, y, w, h] = S.box;
    return { features: f, hand: S.hand, lines, landmarks: S.res.landmarks, canvas: [S.canvas.width, S.canvas.height], crop: [x, y, x + w, y + h],
      birth: S.birth, unlock: S.rid ? unlockOf(S.rid) : null };
  }
  async function finish() {
    if (Object.keys(S.edits).length) window.PalmDetect.refine(S.res, S.edits);
    progress("수상학 규칙과 사주로 풀이하는 중");
    try { S.reading = await api("/api/v2/palm", payload()); S.rid = S.reading.rid; }
    catch (e) { root.innerHTML = `<div class="card"><p class="err">${esc(e.message)}</p><button class="btn btn-gold" id="pf-re">처음부터</button></div>`; $("#pf-re", root).onclick = () => capture(); return; }
    if (S.rid && unlockOf(S.rid) && !S.reading.unlocked) { try { S.reading = await api("/api/v2/palm", payload()); } catch { } }
    result();
  }

  /* ---------- 5. 결과 ---------- */
  function result() {
    const d = S.reading, F = d.free || {}, found = ORDER.filter(k => S.res.lines[k]?.img?.length);
    const lineRead = k => (d.lines || []).find(x => x.name === RULE[k]);
    root.innerHTML = `
      <div class="card rv"><div class="step">手相 · ${S.hand} · 주로 쓰는 손</div>
        ${stageHTML("pf-rs")}
        <div class="legend">${ORDER.map(k => { const L = S.res.lines[k], on = L?.img?.length; return `<span class="${on ? "" : "off"}" style="--c:${COLOR[k]}"><i></i>${NAME[k]}${on ? (L.conf !== "high" || L.estimated ? "·희미" : "") : "·없음"}</span>`; }).join("")}</div>
        <p class="mini">실선은 사진에서 뚜렷하게 찾은 주름, 점선은 희미하거나 일부만 보이는 선, ★은 대박손금 표식이에요.</p></div>
      <div class="money rv" style="--i:1"><div class="wm">財</div><div class="step">財運 · 재물운</div><h3>손에 담긴 재물운 ${F.stars ? stars(F.stars) : ""}</h3>
        <p class="hd">${esc(F.headline || "")}</p>
        ${(F.badges || []).map(b => `<div class="badge"><b>★ ${esc(b.label)}</b> ${esc(b.desc)}</div>`).join("") || `<p class="mini" style="position:relative;margin:12px 0 0">사진에서 뚜렷한 대박손금 표식은 확인되지 않았어요. 희미한 선은 지어내지 않고 그대로 알려 드려요.</p>`}
        ${(F.palm || []).map(t => `<div class="pt"><em class="tg">손금</em><span>${esc(t)}</span></div>`).join("")}</div>
      <div class="card lines rv" style="--i:2"><div class="step">六線 · 6대 선</div><h3>6대 선, 이렇게 보였어요</h3>
        ${ORDER.map(k => { const L = S.res.lines[k], r = lineRead(k), on = L?.img?.length;
          return `<div class="ln" style="--c:${COLOR[k]}"><i></i><b>${NAME[k]} <span class="mini">${on ? (L.conf !== "high" || L.estimated ? "희미함" : "뚜렷") : "보이지 않음"}</span></b>
            <p>${esc(r?.observed || (on ? "" : "사진에서 뚜렷하게 보이지 않았어요."))}</p>${d.unlocked && r?.meaning ? `<p>${esc(r.meaning)}</p>` : ""}</div>`; }).join("")}</div>
      ${d.unlocked ? fullHTML(d) : ""}
      <div id="pf-lock">${d.rid ? lockHTML(d, "재물 시기 · 6대 선 상세 · 사주 교차 감정서") : `<div class="lock plain"><div class="in"><div class="step">財運 × 四柱</div><h3>돈 들어오는 시기까지 보려면</h3><p class="lead" style="margin-top:8px">생년월일을 넣으면 재운선과 사주 대운·세운을 맞춰, 재물이 들어오는 나이와 해를 짚어 드려요. 13쪽 감정서도 만들 수 있어요.</p>
        ${birthForm("pr", { value: store.get("me") || {} })}<p class="err" id="pr-err"></p><button class="btn btn-gold" id="pr-go" style="margin-top:16px">사주 넣고 보기</button></div></div>`}</div>
      <div class="row2"><button class="btn btn-line" id="pf-again">${ic("cam")}다시 찍기</button><button class="btn btn-line" id="pf-fix">${ic("pen")}선 다시 확인</button></div>
      <p class="privacy-note">${ic("shield")}<span>사진은 이 폰에서만 썼어요. 서버에는 선 좌표와 특징만 보냈어요. 감정서의 손 그림도 사진 없이 선으로만 그려요.</span></p>`;
    const svg = paintStage("pf-rs"); svg.innerHTML = linesSVG(null, { labels: true });
    if (d.rid) wireLock(root, d, async () => { S.reading = await api("/api/v2/palm", payload()); result(); });
    else {
      wireBirth(root, "pr");
      $("#pr-go", root).onclick = async () => { try { S.birth = readBirth(root, "pr"); store.set("me", S.birth); } catch (e) { $("#pr-err", root).textContent = e.message; return; } finish(); };
    }
    $("#pf-again", root).onclick = () => capture();
    $("#pf-fix", root).onclick = () => { S.idx = 0; confirmStep(); };
  }
  function fullHTML(d) {
    const m = d.money || {};
    const dae = (m.daeun || []).filter(x => !x.past).slice(0, 4), seun = (m.seun || []).slice(0, 6);
    return `<div class="card rv" style="--i:3"><div class="step">時期 · 재물 시기</div><h3>돈이 들어오는 시기</h3>
      ${m.peak ? `<p style="font-family:var(--serif);font-size:16px;font-weight:500;line-height:1.6;margin:0 0 10px;color:var(--gold-hi)">${esc(m.peak)}</p>` : ""}
      ${(m.saju || []).map(t => `<div class="pt" style="display:grid;grid-template-columns:auto 1fr;gap:10px;font-size:14px;color:var(--ink2);margin:8px 0"><em class="tg">사주</em><span>${esc(t)}</span></div>`).join("")}
      ${dae.length ? `<div class="dae">${dae.map(x => `<div class="${x.now ? "now" : ""}"><b>${esc(x.age)}</b><br>${esc(x.gz)} 대운 · ${esc(x.tag)}<br><span class="mini">${esc(x.years)}${x.palm_match ? " · 손금과 겹침" : ""}</span></div>`).join("")}</div>` : ""}
      ${seun.length ? `<p class="mini" style="margin-top:10px">재물 해: ${seun.map(s => `<b>${s.year}</b>(${esc(s.note)})`).join(" · ")}</p>` : ""}
      ${m.palm_age ? `<p class="note">${ic("clock")}<span>${esc(m.palm_age)}</span></p>` : ""}${m.advice ? `<p class="note" style="color:var(--ink2)">${ic("compass")}<span>${esc(m.advice)}</span></p>` : ""}</div>
      <div class="card rv" style="--i:4"><div class="step">手相 × 四柱</div><h3>사주 × 손금 풀이</h3>${(d.sections || []).map(s => `<div class="sec"><h4>${esc(s.title)}</h4>${(s.palm || []).map(t => `<p><em class="tg">손금</em><span>${esc(t)}</span></p>`).join("")}${(s.saju || []).map(t => `<p><em class="tg">사주</em><span>${esc(t)}</span></p>`).join("")}${(s.timing || []).map(t => `<p><em class="tg">시기</em><span>${esc(t)}</span></p>`).join("")}</div>`).join("")}</div>`;
  }

  window.PalmFlow = { init(el) { root = el; capture(); }, get state() { return S; }, start };
})();
