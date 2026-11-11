/* 손명리 앱 화면 (사주 × 손금 교차 풀이 · 궁합). 외부 API·추적 없음. */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s), $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const stars = n => `<div class="stars" aria-label="5점 중 ${n}점">${[1, 2, 3, 4, 5].map(i => `<i class="${i <= n ? "on" : ""}"></i>`).join("")}</div>`;
  const ic = (n, c = "i") => `<svg class="${c}"><use href="#i-${n}"/></svg>`;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const HAN = { 목: "木", 화: "火", 토: "土", 금: "金", 수: "水" };
  const EL = { 목: "목(木)", 화: "화(火)", 토: "토(土)", 금: "금(金)", 수: "수(水)" };
  const ELC = { 목: "var(--wood)", 화: "var(--fire)", 토: "var(--earth)", 금: "var(--metal)", 수: "var(--water)" };
  const NOW_Y = new Date().getFullYear();
  let REGIONS = [{ region: "서울", places: ["서울"] }], CONFIG = { products: {}, dev_unlock: false };

  async function api(path, body) {
    const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "잠시 후 다시 시도해 주세요");
    return j;
  }
  const store = {
    get: k => { try { return JSON.parse(localStorage.getItem("mw_" + k) || "null"); } catch { return null; } },
    set: (k, v) => localStorage.setItem("mw_" + k, JSON.stringify(v)),
  };

  /* ---------- 라우팅 ---------- */
  const views = {};
  function go(v, push = true) {
    if (v === "palm") v = "saju";   // 손금은 사주와 함께 보는 한 흐름(생년월일 → 손금 → 교차 풀이)
    if (!["home", "saju", "gunghap"].includes(v)) v = "home";
    $$(".view").forEach(s => s.classList.toggle("on", s.id === "v-" + v));
    $$(".tabbar button").forEach(b => b.classList.toggle("on", b.dataset.go === v));
    $("#back").hidden = v === "home";
    if (views[v] && !views[v].ready) { views[v].ready = true; views[v].init(); }
    if (push && location.hash !== "#" + v) history.pushState(null, "", "#" + v);
    window.scrollTo({ top: 0 });
  }
  document.addEventListener("click", e => { const b = e.target.closest("[data-go]"); if (b) go(b.dataset.go); });
  $("#back").onclick = () => go("home");
  window.addEventListener("popstate", () => go(location.hash.slice(1), false));

  /* ---------- 생년월일 입력 ---------- */
  function opts(a, b, sel, fmt = x => x) { let h = ""; for (let i = a; a <= b ? i <= b : i >= b; a <= b ? i++ : i--) h += `<option value="${i}"${i === sel ? " selected" : ""}>${fmt(i)}</option>`; return h; }
  function placeOpts(sel) {
    return REGIONS.map(r => r.places.length === 1 && r.places[0] === r.region ? `<option${r.region === sel ? " selected" : ""}>${r.region}</option>`
      : `<optgroup label="${r.region}">${r.places.map(p => `<option value="${p}"${p === sel ? " selected" : ""}>${p}</option>`).join("")}</optgroup>`).join("");
  }
  const segHTML = (id, items, cur) => `<div class="seg" data-seg="${id}">${items.map(([v, t]) => `<button type="button" data-v="${v}"${cur === v ? ' class="on"' : ""}>${t}</button>`).join("")}</div>`;
  function birthForm(p, o = {}) {
    const d = o.value || {};
    const [yy, mm, dd] = (d.date || "1990-01-01").split("-").map(Number);
    const tm = d.time ? (d.time2 ? "range" : "exact") : (d.date ? "unknown" : "exact");
    return `<div class="form" data-bf="${p}">
      ${o.title ? `<div class="fh"><b>${o.title}</b>${o.tag ? `<span class="tag">${o.tag}</span>` : ""}</div>` : ""}
      <label class="lb" for="${p}-name">이름 <span class="mini">선택 · 감정서 표지에 써요</span></label>
      <input type="text" id="${p}-name" maxlength="12" placeholder="${o.nameHint || "예) 김민지"}" value="${esc(d.name || "")}" autocomplete="off">
      <label class="lb">성별</label>
      ${segHTML(p + "-g", [["F", "여성"], ["M", "남성"]], d.gender || o.gender || "F")}
      <label class="lb">생년월일</label>
      ${segHTML(p + "-cal", [["solar", "양력"], ["lunar", "음력"]], d.calendar || "solar")}
      <div class="row3" style="margin-top:10px">
        <select id="${p}-y" aria-label="태어난 해">${opts(NOW_Y, 1930, yy, x => x + "년")}</select>
        <select id="${p}-m" aria-label="월">${opts(1, 12, mm, x => x + "월")}</select>
        <select id="${p}-d" aria-label="일">${opts(1, 31, dd, x => x + "일")}</select>
      </div>
      <label class="chk" id="${p}-leapw"${(d.calendar || "solar") === "lunar" ? "" : " hidden"}><input type="checkbox" id="${p}-leap"${d.leap ? " checked" : ""}> 윤달에 태어났어요</label>
      <label class="lb">태어난 시간</label>
      ${segHTML(p + "-tm", [["exact", "정확히"], ["range", "대략 · 범위"], ["unknown", "몰라요"]], tm)}
      <div class="row2" style="margin-top:10px" id="${p}-tw">
        <input type="time" id="${p}-t1" value="${d.time || "12:00"}" aria-label="태어난 시각">
        <input type="time" id="${p}-t2" value="${d.time2 || ""}" aria-label="범위 끝 시각" placeholder="~">
      </div>
      <p class="note" id="${p}-th"></p>
      <label class="lb" for="${p}-pl">태어난 곳 <span class="mini">시·군 경도로 시각을 보정해요</span></label>
      <select id="${p}-pl">${placeOpts(d.place || "서울")}</select>
    </div>`;
  }
  function wireBirth(root, p) {
    const f = $(`[data-bf="${p}"]`, root);
    $$(".seg", f).forEach(seg => seg.addEventListener("click", e => {
      const b = e.target.closest("button"); if (!b) return;
      $$("button", seg).forEach(x => x.classList.toggle("on", x === b)); sync();
    }));
    function sync() {
      const cal = $(`[data-seg="${p}-cal"] .on`, f).dataset.v, tm = $(`[data-seg="${p}-tm"] .on`, f).dataset.v;
      $(`#${p}-leapw`, f).hidden = cal !== "lunar";
      $(`#${p}-tw`, f).hidden = tm === "unknown";
      $(`#${p}-t2`, f).hidden = tm !== "range";
      $(`#${p}-tw`, f).style.gridTemplateColumns = tm === "range" ? "1fr 1fr" : "1fr";
      const t = tm === "range" ? "예) 저녁 8시 30분~9시 사이 → 20:30 ~ 21:00. 두 시각의 시주가 같은지 확인해 드려요."
        : tm === "unknown" ? "시간을 몰라도 괜찮아요. 시주(時柱) 없이 여섯 글자로 풀어요." : "";
      $(`#${p}-th`, f).innerHTML = t ? ic("clock") + `<span>${t}</span>` : "";
      const max = cal === "lunar" ? 30 : 31, ds = $(`#${p}-d`, f), cur = +ds.value;
      if (ds.options.length !== max) ds.innerHTML = opts(1, max, Math.min(cur, max), x => x + "일");
    }
    sync();
  }
  function readBirth(root, p) {
    const f = $(`[data-bf="${p}"]`, root), v = id => $(`#${p}-${id}`, f).value;
    const cal = $(`[data-seg="${p}-cal"] .on`, f).dataset.v, tm = $(`[data-seg="${p}-tm"] .on`, f).dataset.v;
    const pad = n => String(n).padStart(2, "0");
    const b = { name: v("name").trim() || null, gender: $(`[data-seg="${p}-g"] .on`, f).dataset.v, calendar: cal,
      leap: cal === "lunar" && $(`#${p}-leap`, f).checked, date: `${v("y")}-${pad(v("m"))}-${pad(v("d"))}`,
      time: tm === "unknown" ? null : v("t1") || null, time2: tm === "range" ? v("t2") || null : null, place: v("pl") };
    if (tm !== "unknown" && !b.time) throw new Error("태어난 시각을 넣거나 '몰라요'를 눌러 주세요");
    if (tm === "range" && !b.time2) throw new Error("범위의 끝 시각도 넣어 주세요");
    return b;
  }

  /* ---------- 명식 · 오행 · 지수 그래픽 ---------- */
  const POS = { 시: "時 · 시주", 일: "日 · 일주", 월: "月 · 월주", 년: "年 · 년주" };
  function pillarsHTML(ps, small) {
    return `<div class="pill4${small ? " sm" : ""}">${ps.map(p => `<div class="pc${p.me ? " me" : ""}"><div class="h">${small ? p.pos : (POS[p.pos] || p.pos + "주")}</div>
      ${p.unknown ? `<div class="gz u"><span class="c">?</span><span class="k">시간 모름</span></div><div class="gz u"><span class="c">?</span><span class="k">&nbsp;</span></div>`
        : `<div class="gz el-${p.stem_el}"><span class="c">${p.gz[0]}</span><span class="k">${p.ko[0]} · ${p.stem_tg}</span></div>
           <div class="gz el-${p.branch_el}"><span class="c">${p.gz[1]}</span><span class="k">${p.ko[1]} · ${p.branch_tg}</span></div>`}</div>`).join("")}</div>`;
  }
  const ilju = ps => (ps.find(p => p.pos === "일") || ps.find(p => p.me) || {}).gz || "";
  function fiveHTML(e, d = {}) {
    const K = ["목", "화", "토", "금", "수"], mx = Math.max(3, ...K.map(k => e[k] || 0)), C = 84, R = 58;
    const pt = (i, r) => { const a = -Math.PI / 2 + i * 2 * Math.PI / 5; return [C + r * Math.cos(a), C + r * Math.sin(a)]; };
    const poly = r => K.map((_, i) => pt(i, r).map(v => v.toFixed(1)).join(",")).join(" ");
    const val = K.map((k, i) => pt(i, R * (0.1 + 0.9 * (e[k] || 0) / mx)));
    const svg = `<svg viewBox="0 0 168 168" aria-hidden="true">
      ${[1 / 3, 2 / 3, 1].map(f => `<polygon points="${poly(R * f)}" fill="none" stroke="rgba(214,185,124,${f === 1 ? .28 : .12})" stroke-width=".7"/>`).join("")}
      ${K.map((_, i) => { const [x, y] = pt(i, R); return `<line x1="${C}" y1="${C}" x2="${x}" y2="${y}" stroke="rgba(214,185,124,.12)" stroke-width=".6"/>`; }).join("")}
      <polygon points="${val.map(p => p.map(v => v.toFixed(1)).join(",")).join(" ")}" fill="rgba(214,185,124,.16)" stroke="#d6b97c" stroke-width="1.1" stroke-linejoin="round"/>
      ${K.map((k, i) => { const [x, y] = val[i]; return `<circle cx="${x}" cy="${y}" r="2.6" fill="${ELC[k]}"/>`; }).join("")}
      ${K.map((k, i) => { const [x, y] = pt(i, R + 15); return `<text x="${x}" y="${y + 4.5}" text-anchor="middle" font-family="MW Serif,serif" font-size="13" fill="${(e[k] || 0) ? "#ede6d6" : "#6c695f"}">${HAN[k]}</text>`; }).join("")}
    </svg>`;
    const list = `<ul>${K.map(k => `<li class="${e[k] ? "" : "z"}" style="--c:${ELC[k]}"><i></i>${EL[k]}<b>${e[k] ?? 0}</b></li>`).join("")}</ul>`;
    const top = K.filter(k => (e[k] || 0) === Math.max(...K.map(x => e[x] || 0))), zero = K.filter(k => !e[k]);
    const jong = k => /[목금]$/.test(k), eun = ks => jong(ks.at(-1)) ? "은" : "는", ida = k => jong(k) ? "이에요" : "예요";
    const sum = `${top.map(k => EL[k]).join("·")} 기운이 가장 많고${zero.length ? `, ${zero.map(k => EL[k]).join("·")}${eun(zero)} 비어 있어요` : ", 다섯 기운이 모두 있어요"}.${d.yong ? ` 나를 돕는 기운(용신)은 <b class="gold">${EL[d.yong]}</b>${ida(d.yong)}.` : ""}`;
    return `<div class="five">${svg}${list}</div><p class="five-sum">${sum}</p>`;
  }
  function gaugeHTML(n, label) {
    const L = Math.PI * 96, v = L * n / 5, ang = Math.PI * (1 - n / 5), ex = 114 + 96 * Math.cos(ang), ey = 108 - 96 * Math.sin(ang);
    const ticks = [0, 1, 2, 3, 4, 5].map(i => { const a = Math.PI * (1 - i / 5), c = Math.cos(a), s = Math.sin(a);
      return `<line x1="${114 + 104 * c}" y1="${108 - 104 * s}" x2="${114 + 109 * c}" y2="${108 - 109 * s}" stroke="rgba(214,185,124,.45)" stroke-width="1"/>`; }).join("");
    return `<div class="gauge"><svg viewBox="0 0 228 118" aria-hidden="true"><defs><linearGradient id="gg${n}" x1="0" x2="1"><stop offset="0" stop-color="#9c7f48"/><stop offset=".6" stop-color="#e2c68c"/><stop offset="1" stop-color="#f6e7bf"/></linearGradient></defs>
      <path d="M18 108A96 96 0 0 1 210 108" fill="none" stroke="rgba(255,255,255,.07)" stroke-width="2"/>${ticks}
      <path class="garc" d="M18 108A96 96 0 0 1 210 108" fill="none" stroke="url(#gg${n})" stroke-width="3" stroke-linecap="round" style="stroke-dasharray:${v.toFixed(1)} ${L.toFixed(1)};--v:${v.toFixed(1)}"/>
      ${n ? `<circle cx="${ex.toFixed(1)}" cy="${ey.toFixed(1)}" r="4.5" fill="#f6e7bf" style="filter:drop-shadow(0 0 6px #d6b97c)"/>` : ""}</svg>
      <div class="v"><b class="gt">${n}</b><small>/ 5</small><span>${label || "운세 지수"}</span></div></div>`;
  }
  const ORB = (() => { const B = "子丑寅卯辰巳午未申酉戌亥"; return `<svg viewBox="0 0 150 150"><g class="r1">${[...B].map((c, i) => { const a = i * 30 * Math.PI / 180;
    return `<text x="${75 + 62 * Math.sin(a)}" y="${75 - 62 * Math.cos(a) + 4}" text-anchor="middle" font-family="MW Serif,serif" font-size="10" fill="#d6b97c" opacity=".75">${c}</text>`; }).join("")}</g>
    <circle cx="75" cy="75" r="72" fill="none" stroke="rgba(214,185,124,.25)" stroke-width=".6"/>
    <g class="r2"><circle cx="75" cy="75" r="50" fill="none" stroke="#d6b97c" stroke-width=".8" stroke-dasharray="1 5.5" opacity=".8"/><circle cx="75" cy="25" r="2" fill="#f6e7bf"/></g>
    <circle cx="75" cy="75" r="40" fill="rgba(214,185,124,.06)" stroke="rgba(214,185,124,.3)" stroke-width=".6"/></svg>`; })();
  const loadingHTML = (t, s = "", ch = "命") => `<div class="loading"><div class="orb">${ORB}<b class="gt">${ch}</b></div><div class="t" data-lt>${t}</div><div class="s">${s}</div></div>`;
  async function withLoading(el, steps, p, ch, min = 1300) {
    el.innerHTML = loadingHTML(steps[0], "손명리 · 만세력", ch); window.scrollTo({ top: 0 });
    let i = 0; const tm = setInterval(() => { const t = $("[data-lt]", el); if (t && i < steps.length - 1) t.textContent = steps[++i]; }, Math.max(450, min / steps.length));
    try { const [r] = await Promise.all([p, sleep(min)]); return r; } finally { clearInterval(tm); }
  }
  const rv = (i, cls = "") => `class="rv ${cls}" style="--i:${i}"`;

  /* ---------- 잠금(결제 자리) · 감정서 보기 ---------- */
  const unlockOf = rid => rid && store.get("u_" + rid);
  const BLUR = `<div class="blur" aria-hidden="true"><h4>성격과 재물 그릇</h4><p>타고난 성향과 재물이 모이는 방식, 일과 사람 사이에서 힘을 얻는 자리를 차례로 풀어 드려요. 대운이 바뀌는 해마다 무엇을 준비하면 좋은지도 함께 적어 두었어요.</p><h4>대운 10년의 흐름</h4><p>열 해씩 바뀌는 큰 운의 흐름과 그 안에서 특히 좋은 해, 지켜야 할 해를 나누어 보여 드려요.</p></div>`;
  function lockHTML(d, label) {
    const pr = d.product || {}, u = unlockOf(d.rid);
    if (!d.rid) return "";
    if (u) return `<div class="lock open"><div class="in"><div class="lk">${ic("doc")}</div><h3>${esc(pr.title)}</h3><p class="sub">열림 · ${pr.pages}쪽 감정서</p>
      <ul>${(d.locked || []).map(x => `<li>${esc(x)}</li>`).join("")}</ul>
      <div class="acts"><button class="btn btn-gold" data-view="${d.rid}">${ic("doc")}전체 감정서 보기</button>
      <a class="btn btn-line" href="/api/v2/report/${d.rid}.pdf?u=${u}" download>${ic("dl")}PDF로 소장하기</a></div>
      <p class="mini" style="margin:12px 0 0">24시간 동안 다시 받을 수 있어요. PDF로 저장해 두세요.</p></div></div>`;
    return `<div class="lock">${BLUR}<div class="in"><div class="lk">${ic("lock")}</div><h3>${esc(label || pr.title)}</h3>
      <p class="sub">무료 요약에 없는 내용이 ${pr.pages}쪽 감정서에 모두 담겨 있어요</p>
      <ul>${(d.locked || []).map(x => `<li>${esc(x)}</li>`).join("")}</ul>
      <div class="price">${(pr.price || 0).toLocaleString("ko-KR")}원<small>한 번 결제 · 앱에서 보기 · PDF 소장</small></div>
      <div class="acts"><button class="btn btn-gold" data-buy="${d.rid}" data-prod="${esc(pr.id)}">전체 감정서 열기</button></div></div></div>`;
  }
  function wireLock(root, d, onUnlock) {
    $$("[data-buy]", root).forEach(b => b.onclick = () => buySheet(d, onUnlock));
    $$("[data-view]", root).forEach(b => b.onclick = () => openViewer(d.rid, d.product?.title));
  }
  function buySheet(d, onUnlock) {
    const pr = d.product, bg = document.createElement("div");
    bg.className = "sheet-bg";
    bg.innerHTML = `<div class="sheet"><div class="grip"></div><div class="step">PREMIUM REPORT</div><h3>${esc(pr.title)}</h3>
      <ul class="incl"><li>${ic("doc")}${pr.pages}쪽 감정서를 앱에서 바로 보기</li><li>${ic("dl")}PDF로 저장해 소장</li><li>${ic("shield")}광고 없음 · 회원가입 없음</li></ul>
      <div class="amt"><b>${pr.price.toLocaleString("ko-KR")}원</b><span>한 번 결제</span></div>
      <div style="display:grid;gap:8px">
        <button class="btn btn-gold" id="buy-play">Google Play로 결제</button>
        ${CONFIG.dev_unlock ? `<button class="btn btn-line" id="buy-dev">개발용 잠금 해제 (테스트 전용)</button>` : ""}
        <button class="btn btn-ghost" id="buy-x">닫기</button></div>
      <p class="err" id="buy-err"></p></div>`;
    document.body.appendChild(bg);
    const close = () => bg.remove();
    bg.onclick = e => { if (e.target === bg) close(); };
    $("#buy-x", bg).onclick = close;
    $("#buy-play", bg).onclick = async () => {
      if ("getDigitalGoodsService" in window) {
        try { await playBilling(d, onUnlock); close(); } catch (e) { $("#buy-err", bg).textContent = e.message; }
      } else $("#buy-err", bg).textContent = "결제는 Play 스토어 앱에서 열려요. (지금은 준비 중이에요)";
    };
    $("#buy-dev", bg) && ($("#buy-dev", bg).onclick = async () => {
      try { const r = await api("/api/v2/purchase", { rid: d.rid, product: pr.id, token: "DEV-UNLOCK" }); store.set("u_" + d.rid, r.unlock); close(); onUnlock(r.unlock); }
      catch (e) { $("#buy-err", bg).textContent = e.message; }
    });
  }
  async function playBilling(d, onUnlock) {
    // Google Play 결제(Digital Goods API). 서버 쪽 purchaseToken 확인이 붙으면 동작해요.
    const svc = await window.getDigitalGoodsService("https://play.google.com/billing");
    const [item] = await svc.getDetails([d.product.id]);
    if (!item) throw new Error("상품 정보를 못 찾았어요");
    const req = new PaymentRequest([{ supportedMethods: "https://play.google.com/billing", data: { sku: d.product.id } }],
      { total: { label: "합계", amount: { currency: item.price.currency, value: item.price.value } } });
    const resp = await req.show();
    let r;
    try { r = await api("/api/v2/purchase", { rid: d.rid, product: d.product.id, token: resp.details.purchaseToken }); }
    catch (e) { await resp.complete("fail"); throw e; }
    // 감정서는 살 때마다 새로 사는 '소모성' 상품 → 소비(consume)해야 다음에 또 살 수 있고, 3일 안에 확인 안 하면 자동 환불됨
    await svc.consume(resp.details.purchaseToken);
    await resp.complete("success");
    store.set("u_" + d.rid, r.unlock); onUnlock(r.unlock);
  }
  function openViewer(rid, title) {
    const u = unlockOf(rid); if (!u) return;
    const v = document.createElement("div"); v.className = "viewer";
    v.innerHTML = `<div class="vbar"><button class="btn sm btn-line" id="vx">${ic("back")}닫기</button><b>${esc(title || "감정서")}</b>
      <a class="btn sm btn-gold" href="/api/v2/report/${rid}.pdf?u=${u}" download>PDF</a></div>
      <iframe title="감정서" src="/api/v2/report/${rid}/report.html?u=${u}"></iframe>`;
    document.body.appendChild(v);
    const fr = $("iframe", v);
    const fit = () => { try { const doc = fr.contentDocument; doc.body.style.zoom = Math.min(1, (fr.clientWidth - 8) / 800).toFixed(3); } catch { } };
    fr.onload = fit; window.addEventListener("resize", fit);
    $("#vx", v).onclick = () => { v.remove(); window.removeEventListener("resize", fit); };
  }

  /* ---------- 사주 ---------- */
  views.saju = { init() { sajuForm(); } };
  const steps3 = cur => `<ol class="flow3 in">${["생년월일", "손바닥 사진", "사주 × 손금 풀이"].map((t, i) => `<li class="${i + 1 === cur ? "on" : i + 1 < cur ? "done" : ""}"><em>${i + 1 < cur ? "✓" : i + 1}</em>${t}</li>`).join("")}</ol>`;
  function sajuForm(err) {
    const el = $("#v-saju");
    el.innerHTML = `<div class="card rv">${steps3(1)}<div class="step">四柱 × 手相 · 교차 풀이</div><div class="title">태어난 순간을 알려 주세요</div>
      <p class="lead">다음 단계에서 손바닥 사진 한 장을 찍으면, 사주와 손금을 <b class="gold">함께</b> 맞대어 풀어 드려요.</p>
      ${birthForm("s", { value: store.get("me") || {} })}
      <p class="err" id="s-err">${esc(err || "")}</p>
      <button class="btn btn-gold" id="s-go" style="margin-top:18px">${ic("hand")}다음: 손금 보기</button>
      <button class="btn btn-ghost" id="s-only" style="margin-top:6px">손금 없이 사주만 보기</button>
      <p class="note">${ic("shield")}<span>회원가입 없이 바로 봐요. 입력한 정보는 풀이에만 쓰고 24시간 뒤 서버에서 지워져요. 손 사진은 폰 밖으로 나가지 않아요.</span></p></div>`;
    wireBirth(el, "s");
    const read = () => { try { const b = readBirth(el, "s"); store.set("me", b); return b; } catch (e) { $("#s-err", el).textContent = e.message; return null; } };
    $("#s-go", el).onclick = () => { const b = read(); if (b) palmStep(b); };
    $("#s-only", el).onclick = () => { const b = read(); if (b) sajuOnly(b); };
  }
  function palmStep(b) {
    const el = $("#v-saju");
    if (!window.PalmFlow) return sajuOnly(b);
    window.PalmFlow.init(el, { birth: b, steps: steps3, onSkip: () => sajuOnly(b), onEdit: () => sajuForm() });
    window.scrollTo({ top: 0 });
  }
  async function sajuOnly(b) {
    const el = $("#v-saju");
    try { const d = await withLoading(el, ["만세력에서 네 기둥을 세우는 중", "다섯 기운의 균형을 재는 중", "2027 丁未년의 흐름을 읽는 중"], api("/api/v2/saju", { birth: b })); sajuResult(d, b); }
    catch (e) { sajuForm(e.message); }
  }
  function yearCard(y, ny, i) {
    if (!ny) return `<div ${rv(i, "yearcard sm")}><div class="yy">${y.gz}<small>${y.year}</small></div><div class="eb">올해 · ${y.ko}년</div>
      <h3>${esc(y.title)}</h3>${stars(y.star)}<p>${y.line}.</p>${y.months ? `<p>${y.months}</p>` : ""}</div>`;
    return `<div ${rv(i, "yearcard ny")}><div class="eb">신년운세 · ${y.year} ${y.gz}年</div>
      ${gaugeHTML(y.star, "2027 운세 지수")}
      <h3>${esc(y.title)}</h3>${stars(y.star)}
      <p>${y.line}.</p>${y.months ? `<div class="mo">${ic("cal")}<span>${y.months}</span></div>` : ""}</div>`;
  }
  const keysHTML = (k3, i0, title = "한눈에 보는 핵심 3가지", sub = "") => `<div class="keys"><div ${rv(i0, "h3")}>${title}</div>${sub ? `<p class="mini">${sub}</p>` : ""}
    ${k3.map((k, i) => `<div ${rv(i0 + 1 + i, "key")}><span class="n gt">${String(i + 1).padStart(2, "0")}</span><b class="t">${k.title}</b><p>${k.text}</p></div>`).join("")}</div>`;
  /* 사주 결과 조각: 사주만 보기와 사주 × 손금 교차 풀이에서 함께 씀 */
  const sajuHero = (d, badge) => { const [, y1] = d.years, ij = ilju(d.pillars); return `<div ${rv(0, "hero")}><div class="wm">${esc(ij[0] || "")}</div>
        ${badge ? `<div class="xbadge">${badge}</div>` : ""}<div class="step">四柱命式</div>
        <div class="who">${esc(d.who)} · ${d.gender === "F" ? "여성" : "남성"} · ${esc(d.place)} 출생</div>
        <div class="ilju"><b class="gt">${esc(ij)}</b><span><em>${esc(d.day_master.ch)} ${esc(d.day_master.ko)} 일간</em>${esc(d.day_master.img)}</span></div>
        ${badge ? "" : `<div class="hl"><small>2027 丁未年 · 정미년</small><b>${esc(y1.title)}</b>${stars(y1.star)}</div>`}
        <div class="meta">${esc(d.date_label)}</div></div>`; };
  const pillarsCard = (d, i) => `<div ${rv(i, "card")}><div class="step">네 기둥 · 여덟 글자</div>
        ${pillarsHTML(d.pillars)}
        ${d.time_note ? `<p class="note">${ic("clock")}<span>${esc(d.time_note)}</span></p>` : ""}
        <div class="chips"><span><small>신강약</small>${esc(d.strength).replace(/\(.*\)/, "")}</span><span><small>격국</small>${esc(d.gyeok)}</span><span><small>용신</small>${EL[d.yong]}</span><span><small>희신</small>${EL[d.hee]}</span></div></div>`;
  const fiveCard = (d, i) => `<div ${rv(i, "card")}><div class="step">五行 · 다섯 기운</div><h3>오행의 균형</h3>${fiveHTML(d.elements, d)}</div>`;
  const decadeCard = (d, i) => { const pk = Math.max(...d.decade.map(x => x.star)), y1 = d.years[1]; return `<div ${rv(i, "card")}><div class="step">十年 · 앞으로 10년</div><h3>10년 운세 흐름</h3>
        <div class="decade">${d.decade.map(x => `<div class="${x.star === pk ? "pk" : ""}${x.year === y1.year ? " cur" : ""}"><em>${x.star === pk ? "★" : ""}</em><i style="height:${10 + x.star * 15}px;opacity:${0.4 + x.star * 0.12}"></i><span>'${String(x.year).slice(2)}</span></div>`).join("")}</div>
        <p class="mini" style="margin:14px 0 0">어느 해가 왜 좋은지, 지켜야 할 해는 언제인지는 전체 감정서의 10년 시기표에 있어요.</p></div>`; };
  function sajuResult(d, b) {
    const el = $("#v-saju"), [y0, y1] = d.years;
    b = b || store.get("me");
    el.innerHTML = `
      ${sajuHero(d)}
      <div ${rv(1, "card xcta")}><div class="step">手相 · 손금도 함께</div><h3>손금을 더하면 교차 풀이가 열려요</h3>
        <p class="lead" style="font-size:14px">손바닥 사진 한 장이면 재운선 × 사주 재물운, 6대 선 × 대운까지 맞대어 봐 드려요. 사진은 폰 밖으로 나가지 않아요.</p>
        <button class="btn btn-gold" id="s-addpalm" style="margin-top:14px">${ic("hand")}손금 더해서 함께 보기</button></div>
      ${pillarsCard(d, 2)}
      ${yearCard(y1, true, 3)}
      ${keysHTML(d.key3, 4)}
      ${fiveCard(d, 8)}
      ${yearCard(y0, false, 9)}
      ${decadeCard(d, 10)}
      <div id="s-lock" class="rv" style="--i:11">${lockHTML(d)}</div>
      <button class="btn btn-line" id="s-again">다른 생년월일로 보기</button>
      <p class="foot">전통 명리 해석에 기반한 재미·참고용 풀이예요. 중요한 결정은 전문가와 상의하세요.</p>`;
    const rewire = () => { $("#s-lock", el).innerHTML = lockHTML(d); wireLock(el, d, rewire); };
    wireLock(el, d, rewire);
    $("#s-again", el).onclick = () => sajuForm();
    $("#s-addpalm", el).onclick = () => b ? palmStep(b) : sajuForm();
  }

  /* ---------- 궁합 ---------- */
  views.gunghap = { init() { ghForm(); } };
  function ghForm(err) {
    const el = $("#v-gunghap"), me = store.get("me") || {}, pt = store.get("partner") || {};
    el.innerHTML = `<div class="card rv"><div class="step">宮合 · 결혼 궁합</div><div class="title">두 사람의 궁합</div>
      <p class="lead">일간의 관계, 배우자 자리의 합·충, 서로 채워 주는 기운과 결혼 적기까지 봐요.</p><hr class="hr">
      ${birthForm("ga", { title: "나", tag: "본인", value: me })}<hr class="hr">
      ${birthForm("gb", { title: "상대", tag: "연인 · 배우자", value: pt, gender: me.gender === "F" ? "M" : "F", nameHint: "예) 이준호" })}
      <p class="err" id="g-err">${esc(err || "")}</p>
      <button class="btn btn-gold" id="g-go" style="margin-top:18px">궁합 보기</button></div>`;
    wireBirth(el, "ga"); wireBirth(el, "gb");
    $("#g-go", el).onclick = async () => {
      let a, b; try { a = readBirth(el, "ga"); b = readBirth(el, "gb"); } catch (e) { $("#g-err", el).textContent = e.message; return; }
      if (a.gender === b.gender) { $("#g-err", el).textContent = "결혼 궁합은 남녀 한 분씩 넣어 주세요"; return; }
      store.set("me", a); store.set("partner", b);
      try { ghResult(await withLoading(el, ["두 사람의 여덟 글자를 세우는 중", "일간과 배우자 자리를 맞대 보는 중", "결혼 적기를 찾는 중"], api("/api/v2/gunghap", { a, b }), "合")); }
      catch (e) { ghForm(e.message); }
    };
  }
  function ringHTML(score) {
    const C = 2 * Math.PI * 58, off = C * (1 - score / 100);
    return `<div class="score"><svg viewBox="0 0 128 128" aria-hidden="true"><defs><linearGradient id="sg" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#f6e7bf"/><stop offset=".5" stop-color="#d6b97c"/><stop offset="1" stop-color="#9c7f48"/></linearGradient></defs>
      <circle cx="64" cy="64" r="58" fill="none" stroke="rgba(255,255,255,.07)" stroke-width="2"/>
      <circle cx="64" cy="64" r="50" fill="none" stroke="rgba(214,185,124,.18)" stroke-width=".6" stroke-dasharray="1 4"/>
      <circle class="arc" cx="64" cy="64" r="58" fill="none" stroke="url(#sg)" stroke-width="3" stroke-linecap="round" style="stroke-dasharray:${C.toFixed(1)};stroke-dashoffset:${off.toFixed(1)};--c:${C.toFixed(1)}"/></svg>
      <div><b class="gt">${score}</b><small>궁합 점수</small></div></div>`;
  }
  function ghResult(d) {
    const el = $("#v-gunghap"), F = d.f, M = d.m;
    const person = (P, g) => `<div class="p"><b>${esc(P.who)}</b><div class="ij gt">${esc(ilju(P.pillars))}</div><small>${g}성 · ${esc(P.place)}</small></div>`;
    el.innerHTML = `
      <div ${rv(0, "gh-hero")}><div class="step" style="justify-content:center">宮合 · 결혼 궁합</div>
        <div class="vs">${person(F, "여")}${ringHTML(d.score)}${person(M, "남")}</div>
        <div class="grade">${esc(d.grade)}</div>
        ${[F.note, M.note].filter(Boolean).map(n => `<p class="note" style="justify-content:center;text-align:left">${ic("clock")}<span>${esc(n)}</span></p>`).join("")}</div>
      <div ${rv(1, "card")}><div class="step">두 사람의 명식</div>
        <div class="pp"><span>${esc(F.who)}</span>${pillarsHTML(F.pillars, true)}</div>
        <div class="pp"><span>${esc(M.who)}</span>${pillarsHTML(M.pillars, true)}</div></div>
      ${keysHTML(d.key3, 2, "핵심 3가지")}
      <div ${rv(6, "card")}><div class="step">궁합 점수표</div><h3>무엇이 잘 맞을까</h3>
        <div class="items">${d.items.map(x => `<div><span>${esc(x.name)}</span><b>${x.score}<small> / ${x.max}</small></b><i><em style="width:${100 * x.score / x.max}%"></em></i></div>`).join("")}</div>
        <hr class="hr"><div class="step">결혼 적기 후보</div>
        <div class="yrs">${d.best_years.map(y => `<span><b>${y.year}</b>${y.gz}</span>`).join("")}</div></div>
      <div id="g-lock" class="rv" style="--i:7">${lockHTML(d)}</div>
      <button class="btn btn-line" id="g-again">다시 입력하기</button>
      <p class="foot">전통 명리 해석에 기반한 재미·참고용 풀이예요.</p>`;
    const rewire = () => { $("#g-lock", el).innerHTML = lockHTML(d); wireLock(el, d, rewire); };
    wireLock(el, d, rewire);
    $("#g-again", el).onclick = () => ghForm();
  }

  views.home = { init() { ringHome(); } };
  function ringHome() {
    const r = $("#ring"); if (!r || r.dataset.ok) return; r.dataset.ok = 1;
    const B = "子丑寅卯辰巳午未申酉戌亥", G = "甲乙丙丁戊己庚辛壬癸", c = 118;
    const ring = (txt, rad, fs, op, step) => [...txt].map((ch, i) => { const a = i * step * Math.PI / 180;
      return `<text x="${(c + rad * Math.sin(a)).toFixed(1)}" y="${(c - rad * Math.cos(a) + fs * 0.36).toFixed(1)}" text-anchor="middle" font-family="MW Serif,serif" font-size="${fs}" fill="#d6b97c" opacity="${op}">${ch}</text>`; }).join("");
    const ticks = Array.from({ length: 72 }, (_, i) => { const a = i * 5 * Math.PI / 180, r1 = i % 6 ? 113 : 110;
      return `<line x1="${(c + r1 * Math.sin(a)).toFixed(1)}" y1="${(c - r1 * Math.cos(a)).toFixed(1)}" x2="${(c + 116 * Math.sin(a)).toFixed(1)}" y2="${(c - 116 * Math.cos(a)).toFixed(1)}" stroke="#d6b97c" stroke-width=".6" opacity=".45"/>`; }).join("");
    r.innerHTML = `<svg viewBox="0 0 236 236" aria-hidden="true">
      <defs><radialGradient id="rg"><stop offset="0" stop-color="rgba(214,185,124,.20)"/><stop offset="1" stop-color="rgba(214,185,124,0)"/></radialGradient></defs>
      <circle cx="${c}" cy="${c}" r="80" fill="url(#rg)"/>
      <g class="rot">${ticks}${ring(B, 98, 13, .55, 30)}</g>
      <circle cx="${c}" cy="${c}" r="86" fill="none" stroke="rgba(214,185,124,.28)" stroke-width=".6"/>
      <g class="rot2">${ring(G, 75, 9.5, .35, 36)}</g>
      <circle cx="${c}" cy="${c}" r="64" fill="none" stroke="rgba(214,185,124,.35)" stroke-width=".6"/></svg>
      <div class="core"><b class="gt">未</b><small>정미 · 붉은 양</small></div>`;
  }

  /* ---------- 시작 ---------- */
  window.MW = { $, $$, esc, api, store, stars, ic, sleep, withLoading, rv, birthForm, wireBirth, readBirth, pillarsHTML, lockHTML, wireLock, loadingHTML, unlockOf,
    saju: { hero: sajuHero, pillarsCard, fiveCard, decadeCard, yearCard, keysHTML, form: () => sajuForm() } };
  (async () => {
    try { REGIONS = (await api("/api/v2/places")).regions; } catch { }
    try { CONFIG = await api("/api/v2/config"); } catch { }
    go(location.hash.slice(1) || "home", false);
  })();
})();
