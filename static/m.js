/* 손명리 앱 화면 (사주 · 궁합, 손금은 PALM_ENABLED일 때만). 외부 API·추적 없음. tier1115: 기본·주제 심층·프리미엄 */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s), $$ = (s, el = document) => [...el.querySelectorAll(s)];
  /* sync1114: 화면의 '내년(신년운세) 해'를 날짜로 계산 — 10~12월엔 다음 해, 그 밖엔 올해 */
  const FY = (() => { const d = new Date(), y = d.getMonth() >= 9 ? d.getFullYear() + 1 : d.getFullYear();
    const S = "甲乙丙丁戊己庚辛壬癸", Z = "子丑寅卯辰巳午未申酉戌亥", SK = "갑을병정무기경신임계", ZK = "자축인묘진사오미신유술해";
    const COL = ["푸른", "푸른", "붉은", "붉은", "누런", "누런", "흰", "흰", "검은", "검은"], AN = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"];
    const s = ((y - 4) % 10 + 10) % 10, b = ((y - 4) % 12 + 12) % 12;
    return { y, gz: S[s] + Z[b], ko: SK[s] + ZK[b], br: Z[b], animal: COL[s] + " " + AN[b] }; })();
  const fyFill = () => document.querySelectorAll("[data-fy]").forEach(e => { e.textContent = e.dataset.fy === "yg" ? `${FY.y} ${FY.gz}年` : String(FY.y); });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fyFill); else fyFill();
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
    if (v === "palm") v = "saju";   // PALM 꺼져 있으면 #palm 주소도 사주로   // 손금은 사주와 함께 보는 한 흐름(생년월일 → 손금 → 교차 풀이)
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
  const JOBS = [["미정", "선택 안 함"], ["직장인", "직장인"], ["사업자", "사업가 · 자영업"], ["프리랜서", "프리랜서"], ["주부", "주부"], ["학생", "학생"], ["무직", "무직 · 쉬는 중 · 구직 중"]];   // tier1115
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
      ${o.job ? `<label class="lb" for="${p}-job">지금 하는 일 <span class="mini">선택 · 일·재물 풀이 문장을 맞춰요</span></label>
      <select id="${p}-job">${JOBS.map(([j, t]) => `<option value="${j}"${j === (d.job === "사업가" ? "사업자" : d.job || "미정") ? " selected" : ""}>${t}</option>`).join("")}</select>` : ""}
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
      $(`#${p}-tw`, f).style.gridTemplateColumns = tm === "range" ? "minmax(0,1fr) minmax(0,1fr)" : "minmax(0,1fr)";
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
    const jb = $(`#${p}-job`, f); if (jb) b.job = jb.value || "미정";
    const prev = store.get(p === "s" ? "me" : "_none"); b.time_rule = prev && prev.date === b.date && prev.time === b.time && prev.place === b.place ? prev.time_rule || "경도" : "경도";
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
      <div class="vpaper"><iframe title="감정서" src="/api/v2/report/${rid}/report.html?u=${u}"></iframe></div>`;
    document.body.appendChild(v);
    // ui1115: 종이는 항상 800px 좌표계에서 쪽을 나눠요. body zoom 대신 iframe 바깥만 축소해
    // iPhone의 텍스트 자동확대·load/폰트 준비 순서가 쪽 높이 측정에 끼어들지 않게 해요.
    const fr = $("iframe", v), paper = $(".vpaper", v);
    const fit = () => { const scale = Math.min(1, Math.max(1, paper.clientWidth - 8) / 800);
      fr.style.width = "800px"; fr.style.height = Math.max(1, paper.clientHeight / scale) + "px";
      fr.style.transform = `scale(${scale})`; };
    const ro = new ResizeObserver(fit); ro.observe(paper);
    fr.onload = fit; fit(); window.addEventListener("resize", fit);
    $("#vx", v).onclick = () => { ro.disconnect(); v.remove(); window.removeEventListener("resize", fit); };
  }

  /* ---------- 사주 ---------- */
  views.saju = { init() { sajuForm(); } };
  const steps3 = cur => `<ol class="flow3 in">${["생년월일", "손바닥 사진", "사주 × 손금 풀이"].map((t, i) => `<li class="${i + 1 === cur ? "on" : i + 1 < cur ? "done" : ""}"><em>${i + 1 < cur ? "✓" : i + 1}</em>${t}</li>`).join("")}</ol>`;
  const PALM = !!window.PALM_ENABLED;   // nopalm1113: 손금 스위치 (/flags.js)
  function sajuForm(err) {
    const el = $("#v-saju");
    if (!PALM) {   // 출시판: 생년월일 → 바로 사주 풀이
      el.innerHTML = `<div class="card rv"><div class="step">四柱 · 사주 풀이</div><div class="title">태어난 순간을 알려 주세요</div>
      <p class="lead">생년월일과 태어난 시각으로 네 기둥을 세우고, 앞으로 10년과 올해·내년의 흐름을 <b class="gold">냉정하게</b> 짚어 드려요.</p>
      ${birthForm("s", { value: store.get("me") || {}, job: true })}
      <p class="err" id="s-err">${esc(err || "")}</p>
      <button class="btn btn-gold" id="s-only" style="margin-top:18px">${ic("doc")}사주 풀이 보기</button>
      <p class="note">${ic("shield")}<span>회원가입 없이 바로 봐요. 입력한 정보는 풀이에만 쓰고 24시간 뒤 서버에서 지워져요.</span></p></div>`;
      wireBirth(el, "s");
      $("#s-only", el).onclick = async () => { try { const b = readBirth(el, "s"); await hourPick(b); store.set("me", b); sajuOnly(b); } catch (e) { $("#s-err", el).textContent = e.message; } };
      return;
    }
    el.innerHTML = `<div class="card rv">${steps3(1)}<div class="step">四柱 × 手相 · 교차 풀이</div><div class="title">태어난 순간을 알려 주세요</div>
      <p class="lead">다음 단계에서 손바닥 사진 한 장을 찍으면, 사주와 손금을 <b class="gold">함께</b> 맞대어 풀어 드려요.</p>
      ${birthForm("s", { value: store.get("me") || {}, job: true })}
      <p class="err" id="s-err">${esc(err || "")}</p>
      <button class="btn btn-gold" id="s-go" style="margin-top:18px">${ic("hand")}다음: 손금 보기</button>
      <button class="btn btn-ghost" id="s-only" style="margin-top:6px">손금 없이 사주만 보기</button>
      <p class="note">${ic("shield")}<span>회원가입 없이 바로 봐요. 입력한 정보는 풀이에만 쓰고 24시간 뒤 서버에서 지워져요. 손 사진은 폰 밖으로 나가지 않아요.</span></p></div>`;
    wireBirth(el, "s");
    const read = () => { try { const b = readBirth(el, "s"); store.set("me", b); return b; } catch (e) { $("#s-err", el).textContent = e.message; return null; } };
    $("#s-go", el).onclick = async () => { const b = read(); if (b) { await hourPick(b); store.set("me", b); palmStep(b); } };
    $("#s-only", el).onclick = async () => { const b = read(); if (b) { await hourPick(b); store.set("me", b); sajuOnly(b); } };
  }
  /* tier1115: 출생 시각이 시(時)의 경계 근처라 '경도 보정'과 '30분 관례'의 시주가 다르면 직접 고르게 해요 (기본: 경도) */
  async function hourPick(b) {
    if (!b.time) { b.time_rule = "경도"; return b; }
    let r; try { r = await api("/api/v2/hour_check", b); } catch { return b; }
    if (!r.differ) { b.time_rule = "경도"; return b; }
    return new Promise(res => {
      const bg = document.createElement("div"); bg.className = "sheet-bg";
      const cur = b.time_rule || "경도";
      bg.innerHTML = `<div class="sheet hourpick"><div class="grip"></div><div class="step">時 · 시주 확인</div><h3>태어난 시각이 두 시(時)의 경계에 있어요</h3>
        <p class="mini" style="margin:0 0 12px">${esc(b.time)} 출생은 보정 방식에 따라 시주가 달라져요. 어느 쪽으로 볼지 골라 주세요. 모르면 기본(경도 보정)으로 두세요.</p>
        <div class="opts">${r.options.map(o => `<button type="button" class="opt${o.rule === cur ? " on" : ""}" data-rule="${o.rule}"><b>${esc(o.title)}${o.default ? ' <span class="tag">기본</span>' : ""}</b><span>${esc(o.desc)}</span></button>`).join("")}</div>
        <button class="btn btn-gold" id="hp-ok" style="margin-top:14px">이 기준으로 보기</button></div>`;
      document.body.appendChild(bg);
      $$(".opt", bg).forEach(x => x.onclick = () => $$(".opt", bg).forEach(y => y.classList.toggle("on", y === x)));
      $("#hp-ok", bg).onclick = () => { b.time_rule = $(".opt.on", bg).dataset.rule; bg.remove(); res(b); };
    });
  }
  function palmStep(b) {
    const el = $("#v-saju");
    if (!PALM || !window.PalmFlow) return sajuOnly(b);
    window.PalmFlow.init(el, { birth: b, steps: steps3, onSkip: () => sajuOnly(b), onEdit: () => sajuForm() });
    window.scrollTo({ top: 0 });
  }
  async function sajuOnly(b) {
    const el = $("#v-saju");
    try { const d = await withLoading(el, ["만세력에서 네 기둥을 세우는 중", "다섯 기운의 균형을 재는 중", `${FY.y} ${FY.gz}년의 흐름을 읽는 중`], api("/api/v2/saju", { birth: b })); sajuResult(d, b); }
    catch (e) { sajuForm(e.message); }
  }
  const advHTML = y => (y.adv || []).length ? `<ul class="yadv">${y.adv.map(a => `<li><b class="${a.kind === "조심" ? "ya-c" : "ya-s"}">${esc(a.kind)}</b>${a.text}</li>`).join("")}</ul>` : "";
  function yearCard(y, ny, i) {
    if (!ny) return `<div ${rv(i, "yearcard sm")}><div class="yy">${y.gz}<small>${y.year}</small></div><div class="eb">올해 · ${y.ko}년</div>
      <h3>${esc(y.title)}</h3>${stars(y.star)}<p>${y.line}.</p>${y.months ? `<p>${y.months}</p>` : ""}${advHTML(y)}</div>`;
    return `<div ${rv(i, "yearcard ny")}><div class="eb">신년운세 · ${y.year} ${y.gz}年</div>
      ${gaugeHTML(y.star, `${y.year} 운세 지수`)}
      <h3>${esc(y.title)}</h3>${stars(y.star)}
      <p>${y.line}.</p>${y.months ? `<div class="mo">${ic("cal")}<span>${y.months}</span></div>` : ""}${advHTML(y)}</div>`;
  }
  const keysHTML = (k3, i0, title = "한눈에 보는 핵심 3가지", sub = "") => `<div class="keys"><div ${rv(i0, "h3")}>${title}</div>${sub ? `<p class="mini">${sub}</p>` : ""}
    ${k3.map((k, i) => `<div ${rv(i0 + 1 + i, "key")}><span class="n gt">${String(i + 1).padStart(2, "0")}</span><b class="t">${k.title}</b><p>${k.text}</p></div>`).join("")}</div>`;
  /* 사주 결과 조각: 사주만 보기와 사주 × 손금 교차 풀이에서 함께 씀 */
  const sajuHero = (d, badge) => { const [, y1] = d.years, ij = ilju(d.pillars); return `<div ${rv(0, "hero")}><div class="wm">${esc(ij[0] || "")}</div>
        ${badge ? `<div class="xbadge">${badge}</div>` : ""}<div class="step">四柱命式</div>
        <div class="who">${esc(d.who)} · ${d.gender === "F" ? "여성" : "남성"} · ${esc(d.place)} 출생</div>
        <div class="ilju"><b class="gt">${esc(ij)}</b><span><em>${esc(d.day_master.ch)} ${esc(d.day_master.ko)} 일간</em>${esc(d.day_master.img)}</span></div>
        ${badge ? "" : `<div class="hl"><small>${y1.year} ${esc(y1.gz)}年 · ${esc(y1.ko)}년</small><b>${esc(y1.title)}</b>${stars(y1.star)}</div>`}
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
      ${PALM ? `<div ${rv(1, "card xcta")}><div class="step">手相 · 손금도 함께</div><h3>손금을 더하면 교차 풀이가 열려요</h3>
        <p class="lead" style="font-size:14px">손바닥 사진 한 장이면 재운선 × 사주 재물운, 6대 선 × 대운까지 맞대어 봐 드려요. 사진은 폰 밖으로 나가지 않아요.</p>
        <button class="btn btn-gold" id="s-addpalm" style="margin-top:14px">${ic("hand")}손금 더해서 함께 보기</button></div>` : ""}
      ${pillarsCard(d, 2)}
      ${yearCard(y1, true, 3)}
      ${keysHTML(d.key3, 4)}
      ${fiveCard(d, 8)}
      ${yearCard(y0, false, 9)}
      ${decadeCard(d, 10)}
      <div id="s-tier" class="rv" style="--i:11"></div>
      <button class="btn btn-line" id="s-again">다른 생년월일로 보기</button>
      <p class="foot">전통 명리 해석에 기반한 재미·참고용 풀이예요. 중요한 결정은 전문가와 상의하세요.</p>`;
    tierUI($("#s-tier", el), d, b);
    $("#s-again", el).onclick = () => sajuForm();
    if ($("#s-addpalm", el)) $("#s-addpalm", el).onclick = () => b ? palmStep(b) : sajuForm();
  }

  /* ---------- tier1115: 등급 · 주제 고르기 · 소유(사주별) ---------- */
  const won = n => n.toLocaleString("ko-KR") + "원";
  const ownsOf = chart => store.get("own_" + chart) || [];
  const addOwn = (chart, t) => { const a = ownsOf(chart); if (t && !a.includes(t)) { a.push(t); store.set("own_" + chart, a); } };
  const ownInfo = chart => { const a = ownsOf(chart).map(t => t.split(".")); return { premium: a.some(x => x[1] === "premium"),
    focus: a.filter(x => x[1] === "focus").map(x => x[3]) }; };
  const TOPICS = () => CONFIG.topics || [{ key: "money", ko: "돈" }, { key: "job", ko: "직업" }, { key: "biz", ko: "사업" }, { key: "love", ko: "결혼" },
    { key: "move", ko: "이사" }, { key: "gunghap", ko: "궁합", partner: true }, { key: "health", ko: "건강" }, { key: "kids", ko: "자녀" }];
  const TDESC = { money: "재물 그릇 · 돈이 모이는 해", job: "맞는 일 · 자리 이동", biz: "사업 체질 · 확장의 때", love: "애정 · 배우자 자리 (시기는 점치지 않아요)",
    move: "이동수 · 좋은 방향 · 피할 방향", gunghap: "상대와의 궁합 · 상대 정보 필요", health: "약한 오행 · 관리 포인트", kids: "자녀의 별 · 자녀궁" };
  const tkey = ks => [...ks].sort().join("+");
  function tierUI(box, d, b) {
    const T = CONFIG.tiers || {}, F = T.focus || { price: 2900, pages: "8~10쪽" }, Pm = T.premium || { price: 9900, pages: "약 20쪽" };
    const st = box._st || (box._st = { sel: [], partner: store.get("partner") || null });
    const own = ownInfo(d.chart), selKey = tkey(st.sel);
    const focusOpen = own.premium || (st.sel.length === 2 && own.focus.includes(selKey));
    const needP = st.sel.includes("gunghap");
    const up = !own.premium && own.focus.length > 0;
    box.innerHTML = `<div class="tiers">
      <div class="sect"><b>감정서 고르기</b><span>REPORTS</span></div>
      <div class="tcard free"><div class="th"><b>기본 감정서</b><span class="pr">무료</span></div>
        <p class="ti">명식과 오행 · 타고난 성격 · 용신 한눈에 · 올해 운세 · ${esc((T.free || {}).pages || "2~3쪽")}</p>
        <button class="btn btn-line sm" data-tier="free">${ic("doc")}기본 감정서 보기</button></div>
      <div class="tcard focus${focusOpen ? " open" : ""}"><div class="th"><b>주제 심층 · 2개</b><span class="pr">${focusOpen ? "열림" : won(F.price)}</span></div>
        <p class="ti">기본 감정서 + 고른 주제마다 타고난 바탕 · 대운 10년 · 해마다 조심/보완 · 힘이 실리는 해 · ${esc(F.pages)}</p>
        <div class="tp-h"><span>주제를 <b>2개</b> 골라 주세요</span><em class="${st.sel.length === 2 ? "ok" : ""}">${st.sel.length} / 2</em></div>
        <div class="topics">${TOPICS().map(t => { const on = st.sel.includes(t.key), dis = !on && st.sel.length >= 2;
          return `<button type="button" class="tp${on ? " on" : ""}${dis ? " dis" : ""}" data-tp="${t.key}" aria-pressed="${on}"${dis ? ' aria-disabled="true"' : ""}><b>${esc(t.ko)}</b><small>${esc(TDESC[t.key] || "")}</small></button>`; }).join("")}</div>
        ${needP ? `<div class="tp-partner">${st.partner ? `<p class="mini">${ic("check")}상대: ${esc(st.partner.name || "상대")} · ${st.partner.gender === "F" ? "여성" : "남성"} · ${esc(st.partner.date)} <button type="button" class="lnk" id="tp-pe">바꾸기</button></p>`
          : `<button type="button" class="btn btn-line sm" id="tp-pe">${ic("pen")}궁합 상대 정보 넣기</button>`}</div>` : ""}
        <p class="err" id="tp-err"></p>
        <button class="btn ${focusOpen ? "btn-line" : "btn-gold"}" data-tier="focus"${st.sel.length === 2 && (!needP || st.partner) ? "" : " disabled"}>
          ${focusOpen ? ic("doc") + "열림 · 주제 심층 보기" : st.sel.length === 2 ? ic("lock") + `${TOPICS().filter(t => st.sel.includes(t.key)).map(t => t.ko).join(" · ")} 심층 열기 · ${won(F.price)}` : "주제 2개를 고르면 열 수 있어요"}</button></div>
      <div class="tcard premium${own.premium ? " open" : ""}"><div class="th"><b>프리미엄 · 전체 주제</b><span class="pr">${own.premium ? "열림" : up ? `<s>${won(Pm.price)}</s> 차액 ${won(Pm.price - F.price)}만` : won(Pm.price)}</span></div>
        <p class="ti">돈·직업·사업·결혼·이사·건강·자녀 7개 주제 깊이 · 대운 × 주제 표 · 올해·내년 월별 · 개운법 · ${esc(Pm.pages)}${st.partner ? " · 넣어 둔 상대와의 궁합 포함" : ""}</p>
        ${up ? `<p class="up">${ic("check")}<span>이 사주로 주제 심층을 이미 열었어요. <b>차액 ${won(Pm.price - F.price)}만</b> 내면 프리미엄으로 올라가요.</span></p>` : ""}
        <button class="btn ${own.premium ? "btn-line" : "btn-gold"}" data-tier="premium">${own.premium ? ic("doc") + "열림 · 프리미엄 보기" : up ? ic("lock") + `차액 ${won(Pm.price - F.price)}만 내고 프리미엄 열기` : ic("lock") + `프리미엄 열기 · ${won(Pm.price)}`}</button></div>
      <p class="mini center" style="margin:6px 0 0">한 번 결제한 감정서는 이 기기에서 같은 사주로 다시 열 수 있어요 · 결제는 개발 중(테스트 잠금 해제)</p></div>`;
    $$("[data-tp]", box).forEach(x => x.onclick = () => { const k = x.dataset.tp, i = st.sel.indexOf(k);
      if (i >= 0) st.sel.splice(i, 1); else if (st.sel.length < 2) st.sel.push(k); else { $("#tp-err", box).textContent = "주제는 2개까지 골라요. 먼저 하나를 빼 주세요"; return; }
      tierUI(box, d, b); });
    const pe = $("#tp-pe", box); if (pe) pe.onclick = () => partnerSheet(b, st.partner, p => { st.partner = p; store.set("partner", p); tierUI(box, d, b); });
    $$("[data-tier]", box).forEach(x => x.onclick = () => openTier(box, d, b, x.dataset.tier, st));
  }
  function partnerSheet(me, cur, done) {
    const bg = document.createElement("div"); bg.className = "sheet-bg";
    bg.innerHTML = `<div class="sheet"><div class="grip"></div><div class="step">宮合 · 궁합 상대</div><h3>상대의 생년월일</h3>
      ${birthForm("tq", { value: cur || {}, gender: me.gender === "F" ? "M" : "F", nameHint: "예) 이준호" })}
      <p class="err" id="tq-err"></p><div style="display:grid;gap:8px;margin-top:12px"><button class="btn btn-gold" id="tq-ok">이 정보로 궁합 보기</button><button class="btn btn-ghost" id="tq-x">닫기</button></div></div>`;
    document.body.appendChild(bg); wireBirth(bg, "tq");
    $("#tq-x", bg).onclick = () => bg.remove();
    $("#tq-ok", bg).onclick = () => { try { const p = readBirth(bg, "tq");
      if (p.gender === me.gender) throw new Error("궁합은 남녀 두 사람 기준의 전통 이론이라, 상대의 성별을 확인해 주세요");
      bg.remove(); done(p); } catch (e) { $("#tq-err", bg).textContent = e.message; } };
  }
  async function openTier(box, d, b, tier, st) {
    const err = m => { const e = $("#tp-err", box); if (e) e.textContent = m; };
    const btn = $(`[data-tier="${tier}"]`, box); const old = btn.innerHTML; btn.disabled = true; btn.innerHTML = "감정서를 만드는 중…";
    try {
      const body = { birth: b, tier, topics: tier === "focus" ? st.sel : [], owns: ownsOf(d.chart) };
      if (st.partner && (tier === "premium" || st.sel.includes("gunghap"))) body.partner = st.partner;
      const r = await api("/api/v2/tier", body);
      const title = r.title + (r.topics_ko && r.topics_ko.length ? " · " + r.topics_ko.join("·") : "");
      if (r.unlock) { store.set("u_" + r.rid, r.unlock); openViewer(r.rid, title); }
      else tierBuy(r, title, () => tierUI(box, d, b));
    } catch (e) { err(e.message); }
    finally { if (btn.isConnected) { btn.disabled = false; btn.innerHTML = old; } }
  }
  function tierBuy(r, title, after) {
    const o = r.offer, bg = document.createElement("div"); bg.className = "sheet-bg";
    const isUp = o.id === "upgrade_7000";
    bg.innerHTML = `<div class="sheet"><div class="grip"></div><div class="step">${isUp ? "UPGRADE · 차액 결제" : "REPORT"}</div><h3>${esc(title)}</h3>
      <ul class="incl"><li>${ic("doc")}${esc(o.pages)} 감정서를 앱에서 바로 보기</li><li>${ic("dl")}PDF로 저장해 소장</li><li>${ic("shield")}광고 없음 · 회원가입 없음</li></ul>
      <div class="amt"><b>${won(o.price)}</b><span>${isUp ? `<s>${won(o.full_price)}</s> 대신 차액 ${won(o.price)}만 · 이 사주의 주제 심층 구매가 확인됐어요` : "한 번 결제"}</span></div>
      <div style="display:grid;gap:8px"><button class="btn btn-gold" id="tb-play">Google Play로 결제</button>
        ${CONFIG.dev_unlock ? `<button class="btn btn-line" id="tb-dev">개발용 잠금 해제 (테스트 전용)</button>` : ""}<button class="btn btn-ghost" id="tb-x">닫기</button></div>
      <p class="err" id="tb-err"></p></div>`;
    document.body.appendChild(bg);
    const close = () => bg.remove(), ok = res => { addOwn(res.chart || r.chart, res.own); store.set("u_" + r.rid, res.unlock); close(); after(); openViewer(r.rid, title); };
    bg.onclick = e => { if (e.target === bg) close(); }; $("#tb-x", bg).onclick = close;
    $("#tb-play", bg).onclick = async () => {
      if (!("getDigitalGoodsService" in window)) { $("#tb-err", bg).textContent = "결제는 Play 스토어 앱에서 열려요. (지금은 준비 중이에요)"; return; }
      try { ok(await playBuy(r.rid, o.id, ownsOf(r.chart))); } catch (e) { $("#tb-err", bg).textContent = e.message; }
    };
    $("#tb-dev", bg) && ($("#tb-dev", bg).onclick = async () => {
      try { ok(await api("/api/v2/purchase", { rid: r.rid, product: o.id, token: "DEV-UNLOCK", owns: ownsOf(r.chart) })); } catch (e) { $("#tb-err", bg).textContent = e.message; }
    });
  }
  async function playBuy(rid, sku, owns) {   // Digital Goods API + Payment Request (TWA). 서버 확인은 billing_todo_ko.md 참고
    const svc = await window.getDigitalGoodsService("https://play.google.com/billing");
    const [item] = await svc.getDetails([sku]); if (!item) throw new Error("상품 정보를 못 찾았어요");
    const req = new PaymentRequest([{ supportedMethods: "https://play.google.com/billing", data: { sku } }], { total: { label: "합계", amount: { currency: item.price.currency, value: item.price.value } } });
    const resp = await req.show(); let r;
    try { r = await api("/api/v2/purchase", { rid, product: sku, token: resp.details.purchaseToken, owns }); } catch (e) { await resp.complete("fail"); throw e; }
    await svc.consume(resp.details.purchaseToken); await resp.complete("success"); return r;
  }

  /* ---------- 궁합 ---------- */
  views.gunghap = { init() { ghForm(); } };
  function ghForm(err) {
    const el = $("#v-gunghap"), me = store.get("me") || {}, pt = store.get("partner") || {};
    el.innerHTML = `<div class="card rv"><div class="step">宮合 · 결혼 궁합</div><div class="title">두 사람의 궁합</div>
      <p class="lead">일간의 관계, 배우자 자리의 합·충, 서로 채워 주는 기운과 함께 계획하기 좋은 해까지 봐요. 결혼 시기를 점치지는 않아요.</p><hr class="hr">
      ${birthForm("ga", { title: "나", tag: "본인", value: me })}<hr class="hr">
      ${birthForm("gb", { title: "상대", tag: "연인 · 배우자", value: pt, gender: me.gender === "F" ? "M" : "F", nameHint: "예) 이준호" })}
      <p class="err" id="g-err">${esc(err || "")}</p>
      <button class="btn btn-gold" id="g-go" style="margin-top:18px">궁합 보기</button></div>`;
    wireBirth(el, "ga"); wireBirth(el, "gb");
    $("#g-go", el).onclick = async () => {
      let a, b; try { a = readBirth(el, "ga"); b = readBirth(el, "gb"); } catch (e) { $("#g-err", el).textContent = e.message; return; }
      if (a.gender === b.gender) { $("#g-err", el).textContent = "결혼 궁합은 남녀 한 분씩 넣어 주세요"; return; }
      store.set("me", a); store.set("partner", b);
      try { ghResult(await withLoading(el, ["두 사람의 여덟 글자를 세우는 중", "일간과 배우자 자리를 맞대 보는 중", "두 사람의 10년 흐름을 겹쳐 보는 중"], api("/api/v2/gunghap", { a, b }), "合")); }
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
        <hr class="hr"><div class="step">함께 계획하기 좋은 해</div>
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
      <div class="core"><b class="gt">${FY.br}</b><small>${FY.ko} · ${FY.animal}</small></div>`;
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
