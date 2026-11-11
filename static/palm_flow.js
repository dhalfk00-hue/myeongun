/* 명운 손금: 손금 지도 안내 → 촬영 안내(잘 찍은/아쉬운 예시) → 사진 품질 확인 → 기기 안에서 6대 선 자동 검출
   → (선택) 부분 확대 사진 2~3장 → 선마다 확인·끌어서 고치기·점 찍어 그리기 → 풀이
   사진(전체·확대 모두)은 이 기기 밖으로 보내지 않는다. 서버에는 선 좌표·손 관절 좌표·특징(글자)만 보낸다. */
(function () {
  "use strict";
  const { $, $$, esc, api, store, birthForm, wireBirth, readBirth, lockHTML, wireLock, loadingHTML, unlockOf, ic, stars } = window.MW;
  const G = window.PalmGuide;
  const ORDER = G.ORDER, NAME = G.NAME, COLOR = G.COLOR;          // 돈 먼저: 재운선 → 사업선 → 운명선 → 생명선 → 두뇌선 → 감정선
  const RULE = { sun: "태양선(재물선)", business: "사업선", fate: "운명선", life: "생명선", head: "두뇌선", heart: "감정선" };
  let S = null, root = null;
  const dom = () => store.get("palmDom") === "왼손" ? "왼손" : "오른손";
  const mir = () => (S && S.res ? S.res.side : dom()) === "왼손";
  const avg = a => a.reduce((x, y) => x + y, 0) / (a.length || 1);

  /* ---------- 1. 촬영 안내 ---------- */
  function capture(msg) {
    const me = store.get("me"), d = dom();
    root.innerHTML = `<div class="card pcap rv"><div class="step">手相 · 손금 재물운</div><div class="title">손바닥 사진 한 장이면 돼요</div>
      <p class="lead">재물운은 <b>주로 쓰는 손</b>으로 봐요. 남녀 구분 없이 같은 기준이에요.</p>
      <div class="seg" id="pf-dom" style="margin-top:16px">${["오른손", "왼손"].map(h => `<button type="button" data-v="${h}"${h === d ? ' class="on"' : ""}>${h}잡이</button>`).join("")}</div>
      <div class="frame" id="pf-frame">${G.svg({ ghost: true, mirror: d === "왼손" })}<i class="scan"></i><p><b id="pf-dt">${d}</b> 손바닥을 쫙 펴고 손가락은 붙여 주세요</p></div>
      <button type="button" class="gbtn" id="pf-guide">${G.svg({ mirror: d === "왼손" })}<span>재운선은 어디? <b>6개 선 위치 안내</b> 보기</span></button>
      ${G.exampleHTML()}
      <ul class="tips"><li><em>01</em>창가·형광등 아래 밝은 곳</li><li><em>02</em>손바닥 평평하게, 손가락 붙여서</li><li><em>03</em>손바닥이 화면 가득, 손목까지</li><li><em>04</em>정면에서 흔들림 없이</li></ul>
      <p class="mini" style="margin:-2px 0 16px">전체 사진을 찍은 뒤, 원하면 부분을 <b style="color:var(--gold-hi)">가까이 2~3장 더</b> 찍어 선을 확대해 볼 수 있어요.</p>
      ${msg ? `<p class="err">${esc(msg)}</p>` : ""}
      <div class="row2"><label class="btn btn-gold">${ic("cam")}촬영하기<input type="file" accept="image/*" capture="environment" hidden></label>
        <label class="btn btn-line">${ic("img")}앨범에서<input type="file" accept="image/*" hidden></label></div>
      <label class="chk" style="margin-top:20px"><input type="checkbox" id="pf-use"${me ? " checked" : ""}> 내 사주와 함께 보기 <span class="mini">돈 들어오는 시기 · 감정서</span></label>
      <div id="pf-bw"${me ? "" : " hidden"}>${birthForm("pf", { value: me || {} })}</div>
      <p class="privacy-note">${ic("shield")}<span>사진은 이 폰 안에서만 분석해요. 서버로 보내지도, 저장하지도 않아요.</span></p></div>`;
    wireBirth(root, "pf");
    $("#pf-dom", root).onclick = e => { const b = e.target.closest("button"); if (!b) return; store.set("palmDom", b.dataset.v);
      $$("#pf-dom button", root).forEach(x => x.classList.toggle("on", x === b)); $("#pf-dt", root).textContent = b.dataset.v;
      $("#pf-frame svg", root).outerHTML = G.svg({ ghost: true, mirror: b.dataset.v === "왼손" }); $("#pf-guide svg", root).outerHTML = G.svg({ mirror: b.dataset.v === "왼손" }); };
    $("#pf-guide", root).onclick = () => G.open({ mirror: dom() === "왼손" });
    $("#pf-use", root).onchange = e => { $("#pf-bw", root).hidden = !e.target.checked; };
    $$("input[type=file]", root).forEach(inp => inp.onchange = () => { const f = inp.files[0]; inp.value = ""; if (f) start(f); });
    window.PalmDetect.loadLandmarker().catch(() => { });
    if (!store.get("palmGuide") && !document.querySelector(".pguide-bg")) G.open({ first: true, mirror: d === "왼손", onClose: () => store.set("palmGuide", 1) });
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
    S = { canvas, birth, hand: dom(), edits: {}, done: {}, idx: 0, shots: {}, hint: {} };
    const q = window.PalmDetect.quality(canvas); S.q = q;
    if (!force && (q.dark || q.blurry || q.bright)) return qualityFail(q);
    progress("손 모양과 관절 21곳을 찾는 중");
    let res;
    try { res = await window.PalmDetect.analyze(canvas, { hand: S.hand, onProgress: s => progress({ hand: "손 모양과 관절 21곳을 찾는 중", crease: "손바닥 주름 지도를 만드는 중", lines: "재운선 · 사업선 · 운명선 · 3대선을 따라가는 중" }[s] || "") }); }
    catch (e) { console.error(e); res = { ok: false }; }
    if (!res.ok) return capture("손을 찾지 못했어요. 손바닥 전체와 손목이 보이게, 밝은 곳에서 다시 찍어 주세요.");
    S.res = res; S.box = cropBox(res); S.mismatch = res.side !== S.hand;
    shotsStep();
  }

  /* ---------- 2-1. (선택) 부분 확대 사진: 기기 안에서 확대 보기용 + 가능하면 주름 검출해 전체 사진 위치로 옮김 ---------- */
  const weak = k => { const L = S.res.lines[k]; return !L || !L.img?.length || L.conf !== "high" || L.estimated; };
  function shotNote(sh, R) { const f = R.lines.filter(k => sh.found[k]); return f.length ? `${f.map(k => NAME[k]).join(" · ")} 찾음` : "확대해서 보기용"; }
  function shotsStep() {
    const n = Object.keys(S.shots).length;
    root.innerHTML = `<div class="card rv"><div class="step">細部 · 더 정확하게 (선택)</div><div class="title" style="font-size:22px">가까이 몇 장 더 찍어 볼까요?</div>
      <p class="lead" style="font-size:14px">방금 사진은 선 위치의 기준으로 쓰고, 가까이 찍은 사진은 선을 확인할 때 <b>옆에 크게</b> 보여 드려요. 안 찍어도 괜찮아요.</p>
      <ul class="shots">${G.REGIONS.map(R => { const sh = S.shots[R.id], rec = R.lines.some(weak);
        return `<li class="${rec ? "rec" : ""}">${G.svg({ region: R.id, mirror: mir() })}<div><b>${R.no} ${R.t}${rec && !sh ? '<span class="rc">추천</span>' : ""}</b><span class="mini">${R.lines.map(k => G.FULL[k]).join(" · ")}</span>${sh ? `<span class="mini" style="color:var(--ok)">${shotNote(sh, R)}</span>` : ""}</div>
          <label class="take">${sh ? `<canvas data-th="${R.id}"></canvas>다시` : `${ic("cam")}찍기`}<input type="file" accept="image/*" hidden data-shot="${R.id}"></label></li>`; }).join("")}</ul>
      <p class="mini" style="margin:0 0 16px">손바닥에서 한 뼘 거리로, 그 부분이 화면 가운데 오게 찍어 주세요. 두 손가락으로 확대한 사진보다 가까이 다가가 찍은 사진이 더 선명해요.</p>
      <button class="btn btn-gold" id="pf-go">${n ? `${n}장 더해서 선 확인하기` : "선 확인하러 가기"}</button>
      ${n ? "" : `<button class="btn btn-ghost" style="margin-top:6px" id="pf-noshots">전체 사진만으로 볼게요</button>`}
      <p class="privacy-note">${ic("shield")}<span>가까이 찍은 사진도 이 폰 안에서만 보고 버려요. 서버로 보내지 않아요.</span></p></div>`;
    $$("canvas[data-th]", root).forEach(c => { const src = S.shots[c.dataset.th].canvas, s = Math.min(src.width, src.height); c.width = 104; c.height = 80;
      c.getContext("2d").drawImage(src, (src.width - s) / 2, (src.height - s * 0.77) / 2, s, s * 0.77, 0, 0, 104, 80); });
    wireShotInputs(shotsStep);
    $("#pf-go", root).onclick = () => { S.idx = 0; confirmStep(); };
    $("#pf-noshots", root) && ($("#pf-noshots", root).onclick = () => { S.idx = 0; confirmStep(); });
  }
  function wireShotInputs(after) {
    $$("input[data-shot]", root).forEach(inp => inp.onchange = async () => { const f = inp.files[0]; inp.value = ""; if (!f) return; await addShot(inp.dataset.shot, f); after(); });
  }
  async function addShot(id, file) {
    progress("가까이 찍은 사진을 살펴보는 중");
    const R = G.REGIONS.find(r => r.id === id), canvas = await loadImage(file, 2000), sh = { canvas, found: {} };
    R.lines.forEach(k => { if (S.hint[k]?.from === id) delete S.hint[k]; });
    S.shots[id] = sh;
    try {
      // 확대 사진에서도 손 관절이 잡히면 주름을 찾아 확대 사진 위에 그려 준다. 전체 사진으로 옮긴 위치는 관절 추정 오차(손바닥 길이의 5~15%)가 있어
      // '맞다'로 바로 쓰지 않고 점 찍어 그리기의 시작 위치(점선)로만 쓴다. 관절이 안 잡히면 확대 보기용으로만 쓴다.
      const r2 = await window.PalmDetect.analyze(canvas, { hand: S.hand });
      if (r2.ok && r2.side === S.res.side) {
        const W = canvas.width, H = canvas.height, m = 0.04 * Math.max(W, H);
        const ids = [0, 1, 2, 5, 9, 13, 17, 6, 10, 14, 18].filter(i => { const q = r2.landmarks[i]; return q[0] > m && q[1] > m && q[0] < W - m && q[1] < H - m; }), A = r2.landmarks, B = S.res.landmarks, T = window.PalmDetect.fitAffine(ids.map(i => A[i]), ids.map(i => B[i]));
        const pl = Math.hypot(B[9][0] - B[0][0], B[9][1] - B[0][1]), err = ids.length < 4 ? 1 : avg(ids.map(i => { const p = T(A[i]); return Math.hypot(p[0] - B[i][0], p[1] - B[i][1]); })) / pl;
        sh.err = +err.toFixed(3);
        R.lines.forEach(k => { const L = r2.lines[k]; if (!(L && L.conf === "high" && !L.estimated && L.img?.length > 4)) return;
          sh.found[k] = L.img; if (ids.length >= 4 && err < 0.06) { const h = L.img.map(T); h.from = id; S.hint[k] = h; } });
      }
    } catch (e) { console.warn(e); }
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
  function stageHTML(id, vh = 58) { const [, , w, h] = S.box; return `<div class="stage" id="${id}" style="aspect-ratio:${w}/${h};--ar:${(w / h).toFixed(3)};max-width:calc(${vh}vh * ${(w / h).toFixed(3)})"><canvas></canvas><svg></svg></div>`; }
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
  const toSvg = (svg, e) => { const p = svg.createSVGPoint(); p.x = e.clientX; p.y = e.clientY; const q = p.matrixTransform(svg.getScreenCTM().inverse()); return [q.x, q.y]; };
  function guideRow(k) {
    return `<div class="gl" style="--c:${COLOR[k]}">${G.svg({ only: k, mirror: mir() })}<div><span class="mn">${G.MEAN[k]}</span><p>${G.FIND[k]}</p><button type="button" id="pf-gall">6개 선 전체 안내 보기</button></div></div>`;
  }
  function shotPanel(k) {
    const r = G.REGION_OF[k], sh = S.shots[r], R = G.REGIONS.find(x => x.id === r);
    if (sh) return `<div class="zoomwrap"><div class="zl"><span>${R.no} 가까이 찍은 사진${sh.found[k] ? ` · <b style="color:${COLOR[k]}">${NAME[k]} 보임</b>` : ""}</span><span>두 번 톡 = 확대</span></div><div class="zoom" id="pf-zoom"><canvas></canvas></div></div>`;
    return `<label class="addshot">${ic("cam")}${R.no} ${R.t}만 가까이 찍어서 보기<input type="file" accept="image/*" hidden data-shot="${r}"></label>`;
  }
  function paintShot(k) {
    const sh = S.shots[G.REGION_OF[k]], box = $("#pf-zoom", root); if (!sh || !box) return;
    const cv = $("canvas", box), src = sh.canvas, kk = Math.min(1, 1100 / src.width);
    cv.width = Math.round(src.width * kk); cv.height = Math.round(src.height * kk);
    box.style.aspectRatio = `${cv.width}/${cv.height}`; box.style.maxWidth = `calc(38vh * ${(cv.width / cv.height).toFixed(3)})`; box.style.margin = "0 auto";
    const x = cv.getContext("2d"); x.drawImage(src, 0, 0, cv.width, cv.height);
    const f = sh.found[k];
    if (f) { x.save(); x.lineCap = "round"; x.lineJoin = "round"; x.strokeStyle = COLOR[k]; x.lineWidth = Math.max(2, cv.width * 0.007); x.shadowColor = COLOR[k]; x.shadowBlur = 10; x.globalAlpha = 0.9;
      x.beginPath(); f.forEach((p, i) => i ? x.lineTo(p[0] * kk, p[1] * kk) : x.moveTo(p[0] * kk, p[1] * kk)); x.stroke(); x.restore(); }
    G.zoomer(box);
  }
  function confirmStep() {
    const k = ORDER[S.idx], L = S.res.lines[k], none = !L || L.conf === "none" || !L.img?.length;
    const hint = S.hint[k] && (none || L.estimated || L.conf !== "high") ? S.hint[k] : null;
    const sh = S.shots[G.REGION_OF[k]], seenClose = sh && sh.found[k];
    const msg = none ? (seenClose ? `가까이 찍은 사진(아래)에서 ${G.FULL[k]}이 보였어요. 위 사진에도 같은 자리를 점 몇 개로 찍어 주세요.` : `자동으로 ${G.FULL[k]}을 찾지 못했어요. 사진에서 보이면 점 몇 개로 그려 주세요. 없거나 아주 희미한 분도 많아요.`)
      : L.estimated ? "주름이 흐려서 보통 이 선이 있는 자리에 점선으로 표시했어요." : "빛나는 선이 실제 손금과 맞나요?";
    const acts = none
      ? `<button class="btn btn-gold" id="pf-tap">${ic("pen")}점 찍어 그리기</button><div class="row2"><button class="btn btn-line" id="pf-faint">잘 안 보여요</button><button class="btn btn-line" id="pf-noline">선이 없어요</button></div>`
      : `<div class="row2"><button class="btn btn-gold" id="pf-ok">맞아요</button><button class="btn btn-line" id="pf-edit">조금 달라요</button></div><div class="row2"><button class="btn btn-ghost" id="pf-tap">점 찍어 다시 그리기</button><button class="btn btn-ghost" id="pf-noline">여기 선이 없어요</button></div>`;
    root.innerHTML = `<div class="card confirm rv">
      <div class="dots">${ORDER.map((x, i) => `<i class="${i === S.idx ? "on" : i < S.idx ? "done" : ""}"></i>`).join("")}</div>
      <div class="step">${S.idx + 1} / 6 · 선 확인</div>
      <h3 style="color:${COLOR[k]}">${G.FULL[k]} ${stLabel(L)}</h3>
      ${guideRow(k)}
      ${S.mismatch && S.idx === 0 ? `<p class="note" style="color:var(--warn);margin:0 0 12px">${ic("alert")}<span>사진 속 손이 ${S.res.side}으로 보여요. ${S.hand}잡이라면 ${S.hand} 사진이 더 정확해요.</span></p>` : ""}
      ${S.res.cut && S.idx === 0 ? `<p class="note" style="color:var(--warn);margin:0 0 12px">${ic("alert")}<span>손 일부가 사진 밖으로 잘렸어요. 선 위치가 덜 정확할 수 있어요.</span></p>` : ""}
      ${stageHTML("pf-st", 50)}
      <p id="pf-msg" class="lead" style="margin:14px 0 12px;font-size:14px">${msg}</p>
      <div class="acts" id="pf-acts">${acts}</div>
      ${shotPanel(k)}
      ${S.idx === 0 ? `<button class="btn btn-ghost" style="font-size:13px;margin-top:6px" id="pf-skip">자동 결과 그대로 보기</button>` : ""}</div>`;
    const svg = paintStage("pf-st");
    svg.innerHTML = linesSVG(k);
    paintShot(k);
    wireShotInputs(confirmStep);
    $("#pf-gall", root).onclick = () => G.open({ mirror: mir() });
    const on = (id, f) => { const b = $("#" + id, root); if (b) b.onclick = f; };
    on("pf-ok", () => { if (L.estimated) S.edits[k] = L.img; next(); });
    on("pf-edit", () => editMode(k, L.img));
    on("pf-tap", () => tapMode(k, hint || (none ? null : L.img)));
    on("pf-faint", () => commit(k, hint || (!none ? L.img : window.PalmDetect.seed(S.res, k)), "faint"));
    on("pf-noline", () => { S.edits[k] = null; S.res.lines[k] = { ...(L || {}), img: [], conf: "none" }; next(); });
    on("pf-skip", () => finish());
  }
  function next() { S.idx++; if (S.idx >= ORDER.length) finish(); else { confirmStep(); root.scrollIntoView?.({ block: "start" }); } }
  /* how: edit(검출된 선 위치 고침) / new(못 찾은 선을 사용자가 그림 → 희미함으로만 인정) / faint(잘 안 보여요 → 희미함) */
  function commit(k, pts, how) {
    const L = S.res.lines[k] || {}, wasNone = !L.img?.length || L.conf === "none";
    S.edits[k] = pts;
    if (how === "faint") S.res.lines[k] = { ...L, img: pts, conf: "mid", estimated: true, strength: 0.3, ratio: 0, user: true };
    else if (wasNone || how === "new") S.res.lines[k] = { ...L, img: pts, conf: "mid", estimated: false, strength: 0.4, ratio: 0, user: true };
    else S.res.lines[k] = { ...L, img: pts, estimated: false, user: true };
    next();
  }

  /* 점 찍어 그리기: 보통 그 선이 있는 자리(이 손 관절에 맞춘 위치)를 흐린 점선으로 깔고, 사용자가 주름 위를 3~5번 톡톡 */
  function tapMode(k, tpl) {
    const svg = $("#pf-st svg", root), [, , bw] = S.box, r = bw * 0.03, pts = [], MAX = 5;
    if (!tpl || tpl.length < 2) tpl = window.PalmDetect.seed(S.res, k);
    const cum = [0]; for (let i = 1; i < tpl.length; i++) cum.push(cum[i - 1] + Math.hypot(tpl[i][0] - tpl[i - 1][0], tpl[i][1] - tpl[i - 1][1]));
    const tpar = p => { let bi = 0, bd = 1e18; tpl.forEach((q, i) => { const d = (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2; if (d < bd) { bd = d; bi = i; } }); return cum[bi]; };
    $("#pf-msg", root).innerHTML = `실제 <b style="color:${COLOR[k]}">${G.FULL[k]}</b> 주름을 따라 <b>3~5곳을 톡톡</b> 눌러 주세요. 흐린 점선은 보통 이 선이 있는 자리예요. 순서는 상관없어요.`;
    $("#pf-acts", root).innerHTML = `<div class="tapbar" id="pf-tb"></div><button class="btn btn-gold" id="pf-save" disabled>3곳 이상 눌러 주세요</button>
      <div class="row2"><button class="btn btn-line" id="pf-undo">한 점 지우기</button><button class="btn btn-line" id="pf-faint">잘 안 보여요</button></div><button class="btn btn-ghost" id="pf-cancel">취소</button>`;
    let curve = null;
    const draw = () => {
      const sp = pts.slice().sort((a, b) => tpar(a) - tpar(b));
      curve = sp.length >= 2 ? window.PalmDetect.catmull(sp, 10) : null;
      svg.innerHTML = linesSVG(k, { skip: k }) +
        `<path class="tpl" d="${pathD(tpl)}" style="stroke:${COLOR[k]};stroke-width:${bw * 0.022}px;stroke-dasharray:${bw * 0.012}px ${bw * 0.03}px;opacity:${pts.length ? 0.35 : 0.8}"/>` +
        (curve ? `<path class="pl" d="${pathD(curve)}" style="stroke:${COLOR[k]};stroke-width:${bw * 0.014}px;filter:drop-shadow(0 0 ${bw * 0.01}px ${COLOR[k]})"/>` : "") +
        sp.map((p, i) => `<g><circle class="tp" cx="${p[0]}" cy="${p[1]}" r="${r}" style="stroke:${COLOR[k]}"/><text class="tpn" x="${p[0]}" y="${p[1] + r * 0.4}" font-size="${r * 1.1}" text-anchor="middle" fill="${COLOR[k]}">${i + 1}</text></g>`).join("");
      $("#pf-tb", root).innerHTML = Array.from({ length: MAX }, (_, i) => `<i class="${i < pts.length ? "on" : ""}"></i>`).join("");
      const b = $("#pf-save", root); b.disabled = pts.length < 3; b.textContent = pts.length < 3 ? `${3 - pts.length}곳 더 눌러 주세요` : `이대로 확정 (${pts.length}곳)`;
      $("#pf-undo", root).disabled = !pts.length;
    };
    let down = null;
    svg.onpointerdown = e => { down = [e.clientX, e.clientY]; e.preventDefault(); };
    svg.onpointermove = null;
    svg.onpointerup = e => { if (!down) return; const moved = Math.hypot(e.clientX - down[0], e.clientY - down[1]); down = null;
      if (moved > 14) return; if (pts.length >= MAX) { $("#pf-msg", root).innerHTML = `5곳까지 찍을 수 있어요. 고치려면 '한 점 지우기'를 눌러 주세요.`; return; }
      pts.push(toSvg(svg, e)); draw(); };
    svg.onpointercancel = () => { down = null; };
    draw();
    $("#pf-undo", root).onclick = () => { pts.pop(); draw(); };
    $("#pf-faint", root).onclick = () => commit(k, curve && pts.length >= 2 ? curve : tpl, "faint");
    $("#pf-save", root).onclick = () => { const L = S.res.lines[k]; commit(k, curve, !L || !L.img?.length || L.conf === "none" ? "new" : "edit"); };
    $("#pf-cancel", root).onclick = () => confirmStep();
  }

  /* 끌어서 고치기: 선 위 조절점 6개 → 손가락으로 끌면 곡선이 따라옴 */
  function resampleN(pts, n) {
    const d = [0]; for (let i = 1; i < pts.length; i++) d.push(d[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const out = []; for (let j = 0; j < n; j++) { const t = d.at(-1) * j / (n - 1); let i = d.findIndex(v => v >= t); i = Math.max(1, i);
      const a = pts[i - 1], b = pts[i], f = (t - d[i - 1]) / ((d[i] - d[i - 1]) || 1); out.push([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]); }
    return out;
  }
  function editMode(k, pts) {
    const cps = resampleN(pts, 6), svg = $("#pf-st svg", root), [, , bw] = S.box, r = bw * 0.034;
    $("#pf-msg", root).innerHTML = `<b>동그라미를 끌어서</b> 실제 ${G.FULL[k]} 주름 위에 맞춰 주세요.`;
    $("#pf-acts", root).innerHTML = `<div class="row2"><button class="btn btn-gold" id="pf-save">이대로 확정</button><button class="btn btn-line" id="pf-cancel">원래대로</button></div>`;
    const draw = () => {
      const curve = window.PalmDetect.catmull(cps, 10);
      svg.innerHTML = linesSVG(k, { skip: k }) + `<path class="pl" d="${pathD(curve)}" style="stroke:${COLOR[k]};stroke-width:${bw * 0.014}px"/>` +
        cps.map((p, i) => `<circle class="cp" data-i="${i}" cx="${p[0]}" cy="${p[1]}" r="${r}" style="stroke-width:${r * 0.3}px"/>`).join("");
      return curve;
    };
    let curve = draw(), drag = -1;
    svg.onpointerdown = e => { const c = e.target.closest(".cp"); if (!c) return; drag = +c.dataset.i; svg.setPointerCapture(e.pointerId); e.preventDefault(); };
    svg.onpointermove = e => { if (drag < 0) return; cps[drag] = toSvg(svg, e); curve = draw(); };
    svg.onpointerup = svg.onpointercancel = () => { drag = -1; };
    $("#pf-save", root).onclick = () => commit(k, curve, "edit");
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
