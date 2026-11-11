/* 손명리 손금 자동 검출기 (기기 안에서만 동작, 외부 API·서버 전송 없음, 비용 0원)
   1) MediaPipe Hand Landmarker(무료, 로컬 파일)로 손 관절 21점 → 손바닥 좌표계
   2) 손바닥을 표준 크기로 펴서(회전·크기·좌우 맞춤) 헤시안 능선 필터로 주름 지도 생성
   3) 전통 수상학의 6대 선(생명·두뇌·감정·운명·재운(태양)·사업)을 '전형 위치 가설' 여러 개 + 동적계획법으로
      실제 주름을 따라가게 맞춤 → 점수(뚜렷함)·길이·방향 측정 → palm_rules.py 특징 키로 변환 */
(function () {
  "use strict";
  const MP_BASE = "/static/vendor/mediapipe";
  const CW = 520, CH = 420, U0 = 230, V0 = 380, S = 320;          // 표준 손바닥 캔버스 (y 위쪽 +, 엄지쪽 +x)
  const MEAN = { 0: [0, 0], 1: [0.4, 0.22], 2: [0.61, 0.57], 5: [0.26, 1.02], 9: [0, 1], 13: [-0.21, 0.91], 17: [-0.41, 0.78] };
  let landmarker = null, loading = null;

  async function loadLandmarker() {
    if (landmarker) return landmarker;
    if (!loading) loading = (async () => {
      const vision = await import(MP_BASE + "/vision_bundle.mjs");
      const fs = await vision.FilesetResolver.forVisionTasks(MP_BASE + "/wasm");
      landmarker = await vision.HandLandmarker.createFromOptions(fs, {
        baseOptions: { modelAssetPath: MP_BASE + "/hand_landmarker.task", delegate: "CPU" },
        runningMode: "IMAGE", numHands: 1, minHandDetectionConfidence: 0.3, minHandPresenceConfidence: 0.3,
      });
      return landmarker;
    })();
    return loading;
  }

  /* ---------- 손 찾기: 손이 화면을 꽉 채우면 검출이 실패해서 여백을 붙여 재시도 ---------- */
  async function detectHand(src) {
    const lm = await loadLandmarker();
    const w = src.naturalWidth || src.width, h = src.naturalHeight || src.height;
    for (const pad of [0, 0.3, 0.6]) {
      const p = Math.round(Math.max(w, h) * pad);
      const c = document.createElement("canvas"); c.width = w + 2 * p; c.height = h + 2 * p;
      const x = c.getContext("2d");
      if (p) { x.fillStyle = "#808080"; x.fillRect(0, 0, c.width, c.height); }
      x.drawImage(src, p, p, w, h);
      const r = lm.detect(c);
      if (r.landmarks && r.landmarks.length) {
        const pts = r.landmarks[0].map(q => [q.x * c.width - p, q.y * c.height - p]);
        const z = r.landmarks[0].map(q => q.z);
        return { pts, z, mpHand: r.handednesses?.[0]?.[0]?.categoryName || "", score: r.handednesses?.[0]?.[0]?.score || 0 };
      }
    }
    return null;
  }

  /* ---------- 기하 유틸 ---------- */
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1]], add = (a, b) => [a[0] + b[0], a[1] + b[1]];
  const mul = (a, k) => [a[0] * k, a[1] * k], dot = (a, b) => a[0] * b[0] + a[1] * b[1];
  const nrm = a => Math.hypot(a[0], a[1]), lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  const dist = (a, b) => nrm(sub(a, b));

  function canonMatrix(P) {           // 이미지 → 표준 캔버스 (닮음변환 + 필요시 좌우반전)
    const o = P[0], yv = sub(P[9], P[0]), L = nrm(yv), y = mul(yv, 1 / L);
    let x = [-y[1], y[0]], mirrored = false;
    if (dot(sub(P[5], o), x) < dot(sub(P[17], o), x)) { x = mul(x, -1); mirrored = true; }
    const k = S / L;
    const A = [[x[0] * k, x[1] * k], [-y[0] * k, -y[1] * k]];
    const b = [U0 - (A[0][0] * o[0] + A[0][1] * o[1]), V0 - (A[1][0] * o[0] + A[1][1] * o[1])];
    return { A, b, L, mirrored };
  }
  const apply = (M, p) => [M.A[0][0] * p[0] + M.A[0][1] * p[1] + M.b[0], M.A[1][0] * p[0] + M.A[1][1] * p[1] + M.b[1]];
  function invert(M) {
    const [[a, b], [c, d]] = M.A, det = a * d - b * c;
    const A = [[d / det, -b / det], [-c / det, a / det]];
    return { A, b: [-(A[0][0] * M.b[0] + A[0][1] * M.b[1]), -(A[1][0] * M.b[0] + A[1][1] * M.b[1])] };
  }
  const px = c => [U0 + c[0] * S, V0 - c[1] * S];          // 표준 좌표(손바닥 길이=1) → 캔버스 픽셀
  const cc = p => [(p[0] - U0) / S, (V0 - p[1]) / S];        // 캔버스 픽셀 → 표준 좌표

  function fitAffine(src, dst) {     // 최소제곱 2D 아핀 (평균 손 → 이 손)
    const ATA = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], ATx = [0, 0, 0], ATy = [0, 0, 0];
    src.forEach((s, i) => { const r = [s[0], s[1], 1]; for (let a = 0; a < 3; a++) { for (let b = 0; b < 3; b++) ATA[a][b] += r[a] * r[b]; ATx[a] += r[a] * dst[i][0]; ATy[a] += r[a] * dst[i][1]; } });
    const solve = (M, v) => {   // 3x3 가우스 소거
      const m = M.map((r, i) => [...r, v[i]]);
      for (let i = 0; i < 3; i++) {
        let piv = i; for (let j = i + 1; j < 3; j++) if (Math.abs(m[j][i]) > Math.abs(m[piv][i])) piv = j;
        [m[i], m[piv]] = [m[piv], m[i]];
        for (let j = 0; j < 3; j++) if (j !== i) { const f = m[j][i] / m[i][i]; for (let k = i; k < 4; k++) m[j][k] -= f * m[i][k]; }
      }
      return m.map((r, i) => r[3] / r[i]);
    };
    const cx = solve(ATA, ATx), cy = solve(ATA, ATy);
    return p => [cx[0] * p[0] + cx[1] * p[1] + cx[2], cy[0] * p[0] + cy[1] * p[1] + cy[2]];
  }

  /* ---------- 영상 처리 ---------- */
  function gauss(src, w, h, s) {
    const r = Math.max(1, Math.ceil(s * 3)), k = new Float32Array(2 * r + 1); let sum = 0;
    for (let i = -r; i <= r; i++) { k[i + r] = Math.exp(-i * i / (2 * s * s)); sum += k[i + r]; }
    for (let i = 0; i < k.length; i++) k[i] /= sum;
    const tmp = new Float32Array(w * h), out = new Float32Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let a = 0; for (let i = -r; i <= r; i++) { const xx = Math.min(w - 1, Math.max(0, x + i)); a += src[y * w + xx] * k[i + r]; }
      tmp[y * w + x] = a;
    }
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let a = 0; for (let i = -r; i <= r; i++) { const yy = Math.min(h - 1, Math.max(0, y + i)); a += tmp[yy * w + x] * k[i + r]; }
      out[y * w + x] = a;
    }
    return out;
  }
  function ridgeMap(g, w, h, sigmas = [2.0, 3.0, 4.5]) {
    const R = new Float32Array(w * h), TH = new Float32Array(w * h);
    for (const s of sigmas) {
      const b = gauss(g, w, h, s);
      for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
        const i = y * w + x;
        const dxx = b[i + 1] - 2 * b[i] + b[i - 1], dyy = b[i + w] - 2 * b[i] + b[i - w];
        const dxy = (b[i + w + 1] - b[i + w - 1] - b[i - w + 1] + b[i - w - 1]) / 4;
        const t = Math.sqrt((dxx - dyy) * (dxx - dyy) + 4 * dxy * dxy), l1 = (dxx + dyy + t) / 2;
        const r = Math.max(l1, 0) * s * s;
        if (r > R[i]) { R[i] = r; TH[i] = 0.5 * Math.atan2(2 * dxy, dxx - dyy); }   // TH = 주름의 법선 방향
      }
    }
    return { R, TH };
  }
  function percentile(arr, mask, q) {
    const v = []; for (let i = 0; i < arr.length; i += 3) if (mask[i] && arr[i] > 0) v.push(arr[i]);
    if (!v.length) return 1; v.sort((a, b) => a - b); return v[Math.min(v.length - 1, Math.floor(v.length * q))] || 1;
  }

  /* ---------- 선 가설 (표준 좌표, 엄지쪽 +x, 손목 y=0, 중지 뿌리 y=1) ---------- */
  function hyps(ln) {
    const H = [];
    // 감정선: 소지 쪽 손날 → 검지·중지 아래. 끝을 엄지-검지 사이(두뇌선 출발점)보다 위에 둬서 두뇌선을 잘못 잡지 않게
    if (ln === "heart") for (const ey of [0.88, 0.94, 1.0]) for (const ex of [0.04, 0.14, 0.24]) for (const sy of [0.64, 0.72, 0.80])
      H.push([[-0.58, sy], [-0.35, sy + 0.04], [-0.12, (sy + ey) / 2 + 0.02], [ex * 0.6, ey - 0.02], [ex, ey]]);
    if (ln === "life") for (const mx of [0.04, 0.12, 0.20, 0.28]) for (const ex of [0.10, 0.20, 0.32])
      H.push([[0.52, 0.72], [0.36, 0.62], [mx + 0.04, 0.45], [mx + 0.02, 0.25], [ex, 0.02]]);
    if (ln === "head") for (const ey of [0.64, 0.54, 0.44, 0.34, 0.24]) for (const bend of [-0.05, 0, 0.05]) for (const ex of [-0.52, -0.30]) {
      const s = [0.50, 0.71], e = [ex, ey], m0 = lerp(s, e, 0.5), m = [m0[0], m0[1] + bend];
      H.push([s, lerp(s, m, 0.5), m, lerp(m, e, 0.5), e]);
    }
    // 운명선: 손목 가운데 → 중지. 중지 축(x≈0)에서 크게 벗어나지 않게 좁힘 (과검출 방지)
    if (ln === "fate") for (const bx of [-0.08, 0.0, 0.08, 0.14]) for (const tx of [-0.05, 0.02, 0.08]) {
      const a = [bx, 0.03], b = [tx, 0.90]; H.push([a, lerp(a, b, 0.33), lerp(a, b, 0.66), b]);
    }
    // 재운선(태양선·재물선): 약지 축(x≈-0.21) 따라 약지 아래로. 아래 끝은 짧은 선(감정선 위)부터 긴 선까지
    if (ln === "sun") for (const by of [0.25, 0.45, 0.62]) for (const bx of [-0.32, -0.22, -0.13]) for (const tx of [-0.27, -0.20]) {
      const a = [bx, by], b = [tx, 0.88]; H.push([a, lerp(a, b, 0.5), b]);
    }
    // 사업선(전통 해석: 손바닥 아래에서 소지 쪽으로 오르는 선 = 서양의 건강선 자리)
    if (ln === "business") for (const sx of [0.02, 0.12, 0.22]) for (const sy of [0.08, 0.2]) for (const ex of [-0.48, -0.38]) for (const bend of [-0.04, 0.03]) {
      const a = [sx, sy], b = [ex, 0.70], m0 = lerp(a, b, 0.5), m = [m0[0] + bend, m0[1] + bend];
      H.push([a, lerp(a, m, 0.5), m, lerp(m, b, 0.5), b]);
    }
    return H;
  }
  /* 생명선·두뇌선은 엄지-검지 사이(관절점)에서 직접 출발점을 잡는다: 엄지를 벌린 정도가 달라도 시작점이 맞도록 */
  function anchoredHyps(ln, Pc, T) {
    const C = mul(add(add(Pc[0], Pc[5]), add(Pc[9], Pc[17])), 0.25), H = [];
    const starts = [0.3, 0.45, 0.6].map(s => { const e = lerp(Pc[5], Pc[2], s); return lerp(e, C, 0.07); });
    if (ln === "life") {
      for (const S0 of starts) for (const t of [0.25, 0.5, 0.75]) for (const b of [0.08, 0.14, 0.20, 0.27]) {
        const E = lerp(Pc[0], Pc[1], t), mid = lerp(S0, E, 0.5), ch = sub(E, S0), L = nrm(ch) || 1;
        let n = [-ch[1] / L, ch[0] / L]; if (dot(n, sub(C, mid)) < 0) n = mul(n, -1);   // 손바닥 가운데 쪽으로 볼록
        const Q = add(mid, mul(n, 2 * b * S)), pts = [];
        for (let i = 0; i <= 8; i++) { const u = i / 8; pts.push(add(add(mul(S0, (1 - u) * (1 - u)), mul(Q, 2 * u * (1 - u))), mul(E, u * u))); }
        H.push(pts);
      }
    } else {
      for (const S0 of starts) for (const ey of [0.64, 0.54, 0.44, 0.34, 0.24]) for (const bend of [-0.05, 0, 0.05]) for (const ex of [-0.60, -0.48, -0.36, -0.26]) {
        const E = T(px([ex, ey])), m0 = lerp(S0, E, 0.5), m = [m0[0], m0[1] - bend * S];
        H.push([S0, lerp(S0, m, 0.5), m, lerp(m, E, 0.5), E]);
      }
    }
    return H;
  }
  function catmull(ctrl, n = 20) {
    const c = [mul(sub(mul(ctrl[0], 2), ctrl[1]), 1), ...ctrl, sub(mul(ctrl.at(-1), 2), ctrl.at(-2))], out = [];
    for (let i = 1; i < c.length - 2; i++) {
      const [p0, p1, p2, p3] = [c[i - 1], c[i], c[i + 1], c[i + 2]];
      for (let j = 0; j < n; j++) {
        const t = j / n, t2 = t * t, t3 = t2 * t;
        out.push([0, 1].map(k => 0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3)));
      }
    }
    out.push(c.at(-2)); return out;
  }
  function resample(pts, step = 3) {
    const s = [0]; for (let i = 1; i < pts.length; i++) s.push(s[i - 1] + dist(pts[i], pts[i - 1]));
    const n = Math.max(2, Math.floor(s.at(-1) / step)), out = []; let j = 0;
    for (let k = 0; k < n; k++) {
      const t = s.at(-1) * k / (n - 1);
      while (j < s.length - 2 && s[j + 1] < t) j++;
      const f = (t - s[j]) / Math.max(1e-9, s[j + 1] - s[j]); out.push(lerp(pts[j], pts[j + 1], Math.min(1, Math.max(0, f))));
    }
    return out;
  }
  function bil(img, x, y) {
    x = Math.min(CW - 1.001, Math.max(0, x)); y = Math.min(CH - 1.001, Math.max(0, y));
    const x0 = x | 0, y0 = y | 0, fx = x - x0, fy = y - y0, i = y0 * CW + x0;
    return img[i] * (1 - fx) * (1 - fy) + img[i + 1] * fx * (1 - fy) + img[i + CW] * (1 - fx) * fy + img[i + CW + 1] * fx * fy;
  }
  /* 동적계획법: 가설 곡선의 법선 방향으로 ±K칸 옮겨 가며 주름 반응이 가장 큰 매끈한 경로를 찾는다 */
  function trace(R, TH, tpl, K = 8, dk = 2, lam = 0.18, mu = 0.004) {
    const t = resample(catmull(tpl), 3), n = t.length, M = 2 * K + 1;
    const tan = t.map((p, i) => { const a = t[Math.max(0, i - 1)], b = t[Math.min(n - 1, i + 1)], d = sub(b, a), l = nrm(d) || 1; return [d[0] / l, d[1] / l]; });
    const sc = new Float32Array(n * M), rs = new Float32Array(n * M), XY = new Float32Array(n * M * 2);
    for (let i = 0; i < n; i++) {
      const nr = [-tan[i][1], tan[i][0]], ta = Math.atan2(tan[i][1], tan[i][0]);
      for (let k = 0; k < M; k++) {
        const off = (k - K) * dk, x = t[i][0] + nr[0] * off, y = t[i][1] + nr[1] * off;
        const xi = Math.min(CW - 1, Math.max(0, Math.round(x))), yi = Math.min(CH - 1, Math.max(0, Math.round(y)));
        const al = Math.sin(TH[yi * CW + xi] - ta) ** 2, r = bil(R, x, y) * al;
        rs[i * M + k] = r; sc[i * M + k] = Math.min(r, 1.5) - mu * Math.abs(k - K);
        XY[(i * M + k) * 2] = x; XY[(i * M + k) * 2 + 1] = y;
      }
    }
    const D = new Float32Array(n * M), B = new Int16Array(n * M);
    for (let k = 0; k < M; k++) D[k] = sc[k];
    for (let i = 1; i < n; i++) for (let k = 0; k < M; k++) {
      let best = -1e9, arg = k;
      for (let d = -1; d <= 1; d++) { const kk = k + d; if (kk < 0 || kk >= M) continue; const v = D[(i - 1) * M + kk] - lam * Math.abs(d); if (v > best) { best = v; arg = kk; } }
      D[i * M + k] = best + sc[i * M + k]; B[i * M + k] = arg;
    }
    let k = 0; for (let j = 1; j < M; j++) if (D[(n - 1) * M + j] > D[(n - 1) * M + k]) k = j;
    const path = new Array(n), resp = new Array(n);
    for (let i = n - 1; i >= 0; i--) { path[i] = [XY[(i * M + k) * 2], XY[(i * M + k) * 2 + 1]]; resp[i] = rs[i * M + k]; if (i) k = B[i * M + k]; }
    let tot = 0; for (const r of resp) tot += Math.min(r, 1.2);
    return { path, resp, score: tot / n, tpl: t };
  }
  /* 두뇌선 끝 이어 가기: 고른 경로의 끝에서 같은 방향(±25°)으로 손날 쪽까지 더 따라가 보고,
     주름이 계속 이어지면(끊김 8점 이하) 그만큼 길게 붙인다 → 긴 두뇌선이 중간에서 잘리지 않게 */
  function extendHead(best, R, TH, mask) {
    const ex = extent(best.resp); if (ex.b < 10) return;
    const path = best.path.slice(0, ex.b + 1), E = path.at(-1), A = path[Math.max(0, path.length - 12)];
    const d0 = sub(E, A), l0 = nrm(d0) || 1, dir = [d0[0] / l0, d0[1] / l0];
    if (dir[0] > -0.3) return;                                   // 손날(-x) 쪽으로 가는 중일 때만
    let bestExt = null;
    for (const ang of [-0.45, -0.25, 0, 0.25, 0.45]) {
      const c = Math.cos(ang), sn = Math.sin(ang), d = [dir[0] * c - dir[1] * sn, dir[0] * sn + dir[1] * c];
      const tpl = []; for (let t = 0; t <= 0.4 * S; t += 0.08 * S) tpl.push(add(E, mul(d, t)));
      const inside = tpl.filter(p => { const x = Math.round(p[0]), y = Math.round(p[1]); return x >= 0 && y >= 0 && x < CW && y < CH && mask[y * CW + x]; }).length;
      if (inside < 3) continue;
      const tr = trace(R, TH, tpl, 6);
      // 시작부터 이어지는 주름 구간 길이 (8점 넘게 끊기면 멈춤, 마스크 밖이면 멈춤)
      let last = -1, miss = 0;
      for (let i = 0; i < tr.resp.length; i++) {
        const p = tr.path[i], x = Math.round(p[0]), y = Math.round(p[1]);
        if (!(x >= 0 && y >= 0 && x < CW && y < CH && mask[y * CW + x])) break;
        if (tr.resp[i] > 0.3) { last = i; miss = 0; } else if (++miss > 8) break;
      }
      if (last < 6) continue;
      const seg = tr.path.slice(1, last + 1), q = avg(tr.resp.slice(0, last + 1)) * Math.sqrt(last);
      if (avg(tr.resp.slice(0, last + 1)) < 0.45) continue;
      if (!bestExt || q > bestExt.q) bestExt = { q, seg, resp: tr.resp.slice(1, last + 1) };
    }
    if (!bestExt) return;
    best.path = path.concat(bestExt.seg); best.resp = best.resp.slice(0, ex.b + 1).concat(bestExt.resp);
    best.extended = bestExt.seg.length;
  }
  /* 같은 모양의 선을 옆으로 옮겨서(주름이 없을 자리) 얻는 점수 = 이 손바닥의 '잔주름 바탕 점수'.
     진짜 선은 바탕보다 훨씬 높아야 '있음'으로 본다 → 운명선·재운선·사업선 과검출 방지 */
  function nullScore(R, TH, tpl, mask) {
    const a = tpl[0], b = tpl.at(-1), d = sub(b, a), l = nrm(d) || 1, n = [-d[1] / l, d[0] / l], sc = [];
    for (const off of [-0.22, -0.14, 0.14, 0.22]) {
      const sh = tpl.map(p => add(p, mul(n, off * S)));
      let inside = 0; sh.forEach(p => { const x = Math.round(p[0]), y = Math.round(p[1]); if (x >= 0 && y >= 0 && x < CW && y < CH && mask[y * CW + x]) inside++; });
      if (inside / sh.length < 0.7) continue;
      sc.push(trace(R, TH, sh).score);
    }
    if (!sc.length) return 0.35;
    sc.sort((x, y) => x - y);
    return Math.max(0.08, sc[Math.floor(sc.length / 2)]);
  }
  // '있음' 판정 기준: (선 점수 ÷ 바탕 점수). 테스트 사진 10장을 눈으로 확인하며 맞춘 값
  const PRES = { life: 1.25, head: 1.25, heart: 1.25, fate: 1.7, sun: 1.8, business: 1.7 };
  function suppress(R, path, rad = 6, from = 0) {
    for (let i = from; i < path.length; i++) {
      const [x, y] = path[i];
      for (let yy = Math.max(0, Math.round(y - rad)); yy <= Math.min(CH - 1, Math.round(y + rad)); yy++)
        for (let xx = Math.max(0, Math.round(x - rad)); xx <= Math.min(CW - 1, Math.round(x + rad)); xx++)
          if ((xx - x) ** 2 + (yy - y) ** 2 <= rad * rad) R[yy * CW + xx] *= 0.15;
    }
  }
  function smooth(path, win = 4, passes = 3) {
    let p = path.map(q => q.slice());
    for (let s = 0; s < passes; s++) p = p.map((q, i) => {
      let a = [0, 0], c = 0; for (let j = Math.max(0, i - win); j <= Math.min(p.length - 1, i + win); j++) { a = add(a, p[j]); c++; }
      return i === 0 || i === p.length - 1 ? q : mul(a, 1 / c);
    });
    return p;
  }
  /* 주름 위에 실제로 있는 구간(on) 찾기: 짧은 잡음 구간은 버리고, 끊긴 곳은 gap 으로 남김 */
  function extent(resp, thr = 0.25) {
    const on = resp.map(r => r > thr), runs = []; let s = -1;
    on.forEach((v, i) => { if (v && s < 0) s = i; if ((!v || i === on.length - 1) && s >= 0) { runs.push([s, v ? i : i - 1]); s = -1; } });
    const keep = runs.filter(([a, b]) => b - a + 1 >= 4);
    if (!keep.length) return { a: 0, b: -1, gaps: [], frac: 0 };
    // 가장 긴 덩어리를 중심으로 간격 12점(약 0.11 손바닥) 이내의 덩어리만 이어 붙임
    let mi = 0; keep.forEach((r, i) => { if (r[1] - r[0] > keep[mi][1] - keep[mi][0]) mi = i; });
    let a = keep[mi][0], b = keep[mi][1];
    for (let i = mi - 1; i >= 0; i--) { if (a - keep[i][1] <= 12) a = keep[i][0]; else break; }
    for (let i = mi + 1; i < keep.length; i++) { if (keep[i][0] - b <= 12) b = keep[i][1]; else break; }
    const gaps = []; for (let i = 0; i < keep.length - 1; i++) { const g0 = keep[i][1], g1 = keep[i + 1][0]; if (g0 >= a && g1 <= b && g1 - g0 > 9 && avg(resp.slice(g0 + 1, g1)) < 0.12) gaps.push([g0, g1]); }   // 확실히 끊긴 곳만
    let cnt = 0; for (let i = a; i <= b; i++) cnt += on[i] ? 1 : 0;
    return { a, b, gaps, frac: (b - a + 1) / resp.length, fill: cnt / (b - a + 1) };
  }

  /* ---------- 손가락 길이 (전통 기준: 검지=중지 첫마디 1/2, 약지=3/4, 소지=약지 첫·둘째 마디 경계) ---------- */
  function fingers(P, M) {
    const Pc = P.map(p => cc(apply(M, p)));            // 표준 좌표
    const seg = (a, b) => dist(Pc[a], Pc[b]);
    const vh = (mcp, upto) => { let h = Pc[mcp][1]; for (let j = mcp; j < upto; j++) h += seg(j, j + 1); return h; };   // 손가락을 곧게 세웠을 때 높이
    const mDIP = vh(9, 11), mTip = vh(9, 12), rDIP = vh(13, 15), rPIP = vh(13, 14);
    const idx = vh(5, 8), ring = vh(13, 16), lit = vh(17, 20);
    const ph = mTip - mDIP;                          // 중지 첫마디(손끝 마디) 길이
    const band = (v, std, tol) => v < std - tol ? "짧음" : v > std + tol ? "긺" : "표준";
    const thumbLen = seg(2, 3) + seg(3, 4), indexLen = seg(5, 6) + seg(6, 7) + seg(7, 8);
    const tr = thumbLen / indexLen;
    const rmid = rDIP - rPIP;
    return {
      // 관절점(MCP)은 손가락 뿌리 주름보다 안쪽이라 생기는 치우침을 테스트 사진으로 보정한 기준값
      lv: { index: band(idx, mDIP + ph * 0.55, ph * 0.32), ring: band(ring, mDIP + ph * 0.40, ph * 0.32), little: band(lit, rDIP - rmid * 0.2, rmid * 0.38),
        thumb: tr < 0.62 ? "짧음" : tr > 0.86 ? "긺" : "표준", middle: "표준" },
      raw: { index: (idx - mDIP) / ph, ring: (ring - mDIP) / ph, little: (lit - rDIP) / rmid, thumb: tr },
      palmWL: dist(Pc[5], Pc[17]) * 1.25 / 1.0, fingerPalm: (mTip - 1.0),
    };
  }

  /* ---------- 메인 분석 ---------- */
  async function analyze(img, opts = {}) {
    const t0 = performance.now(), prog = opts.onProgress || (() => {});
    prog("hand");
    const det = await detectHand(img);
    if (!det) return { ok: false, reason: "nohand" };
    const P = det.pts, M = canonMatrix(P), Mi = invert(M);
    const W0 = img.naturalWidth || img.width, H0 = img.naturalHeight || img.height, mg = 0.01 * Math.max(W0, H0);
    const cut = P.some(p => p[0] < -mg || p[1] < -mg || p[0] > W0 + mg || p[1] > H0 + mg);   // 손 일부가 사진 밖
    // 손바닥이 아니라 손등이면 z(깊이)·모양으로 판별이 어렵다 → 손바닥으로 가정, 좌우는 기하로 판정
    const side = M.mirrored ? "왼손" : "오른손";
    prog("crease");
    await new Promise(r => setTimeout(r, 30));
    const c = document.createElement("canvas"); c.width = CW; c.height = CH;
    const x = c.getContext("2d", { willReadFrequently: true });
    x.setTransform(M.A[0][0], M.A[1][0], M.A[0][1], M.A[1][1], M.b[0], M.b[1]);
    x.imageSmoothingQuality = "high";
    x.drawImage(img, 0, 0);
    x.setTransform(1, 0, 0, 1, 0, 0);
    const id = x.getImageData(0, 0, CW, CH).data;
    const g = new Float32Array(CW * CH), valid = new Float32Array(CW * CH);
    for (let i = 0; i < CW * CH; i++) { g[i] = 0.299 * id[i * 4] + 0.587 * id[i * 4 + 1] + 0.114 * id[i * 4 + 2]; valid[i] = id[i * 4 + 3] > 200 ? 1 : 0; }
    // 국소 대비 정규화 (조명 차이 보정, CLAHE 대용)
    const mu = gauss(g, CW, CH, 14), d2 = new Float32Array(CW * CH);
    for (let i = 0; i < g.length; i++) d2[i] = (g[i] - mu[i]) ** 2;
    const sd = gauss(d2, CW, CH, 14), gn = new Float32Array(CW * CH);
    for (let i = 0; i < g.length; i++) gn[i] = (g[i] - mu[i]) / (Math.sqrt(sd[i]) + 6) * 40;
    const { R, TH } = ridgeMap(gn, CW, CH);
    // 손바닥 마스크: 관절점 볼록껍질 + 손날(소지 쪽) 확장, 가장자리 8px 깎기
    const Pc = P.map(p => apply(M, p));
    const ulnar = [lerp(Pc[17], Pc[0], 0.0), add(Pc[17], mul(sub(Pc[17], Pc[13]), 0.55)), add(lerp(Pc[17], Pc[0], 0.5), mul(sub(Pc[17], Pc[5]), 0.32)), add(Pc[0], mul(sub(Pc[17], Pc[5]), 0.35))];
    const hullPts = [Pc[0], Pc[1], Pc[2], lerp(Pc[2], Pc[5], 0.5), Pc[5], Pc[9], Pc[13], Pc[17], ...ulnar];
    const mc = document.createElement("canvas"); mc.width = CW; mc.height = CH;
    const mx = mc.getContext("2d", { willReadFrequently: true });
    const hull = convexHull(hullPts);
    mx.fillStyle = "#fff"; mx.beginPath(); hull.forEach((p, i) => i ? mx.lineTo(p[0], p[1]) : mx.moveTo(p[0], p[1])); mx.closePath(); mx.fill();
    mx.strokeStyle = "#000"; mx.lineWidth = 16; mx.stroke();
    const md = mx.getImageData(0, 0, CW, CH).data, vb = gauss(valid, CW, CH, 3), mask = new Uint8Array(CW * CH);
    for (let i = 0; i < CW * CH; i++) mask[i] = md[i * 4] > 128 && vb[i] > 0.97 ? 1 : 0;
    for (let i = 0; i < R.length; i++) if (!mask[i]) R[i] = 0;
    const scale = percentile(R, mask, 0.95);
    for (let i = 0; i < R.length; i++) R[i] /= scale;
    const Rorig = R.slice();
    prog("lines");
    await new Promise(r => setTimeout(r, 30));
    // 평균 손 → 이 손 아핀
    // 평균 손 → 이 손 아핀 (엄지 관절 포함 7점)
    const ids = Object.keys(MEAN).map(Number), pids = [0, 5, 9, 13, 17];
    const Tall = fitAffine(ids.map(i => px(MEAN[i])), ids.map(i => Pc[i]));
    const Tpalm = fitAffine(pids.map(i => px(MEAN[i])), pids.map(i => Pc[i]));
    const out = {};
    const bestOf = (ln, R) => {
      let best = null;
      // 두뇌선은 '평균 세기'만 보면 짧은 가설이 이겨서 긴 두뇌선이 중간에 잘린다 →
      // 주름 위 구간은 더하고(+), 주름 밖 구간은 빼는(-) '덮인 길이' 점수로 고른다
      const key = ln === "head" ? tr => tr.resp.reduce((a, r) => a + Math.min(r, 1.2) - 0.2, 0) : tr => tr.score;
      for (const h of (ln === "life" || ln === "head" ? anchoredHyps(ln, Pc, Tall) : hyps(ln).map(h => h.map(c => Tall(px(c)))))) {
        const tr = trace(R, TH, h); tr.key = key(tr);
        if (!best || tr.key > best.key) best = tr;
      }
      best.ratio = best.score / nullScore(R, TH, best.tpl, mask);
      return best;
    };
    for (const ln of ["heart", "life", "head", "fate", "sun", "business"]) {
      const best = bestOf(ln, R);
      if (ln === "head") extendHead(best, R, TH, mask);
      out[ln] = { ...best, ex: extent(best.resp), smooth: smooth(best.path) };
      suppress(R, best.path, 6, ln === "life" ? 14 : 0);
    }
    // 재운선이 여러 가닥인지: 같은 자리에서 한 번 더 찾아 본다 (전통 해석: 한 가닥=수입원 하나, 여러 가닥=수입원 여럿)
    out.sunExtra = [];
    for (let i = 0; i < 2; i++) {
      const b2 = bestOf("sun", R), ex2 = extent(b2.resp);
      if (b2.ratio < PRES.sun || ex2.b < 0 || ex2.frac < 0.2) break;
      out.sunExtra.push({ ...b2, ex: ex2, smooth: smooth(b2.path) }); suppress(R, b2.path, 6);
    }
    // 이중선(평행하게 한 줄 더): 이미 찾은 선을 지운 주름 지도에서, 선과 나란한 자리(손바닥 길이의 3~10%)를 다시 찾는다
    for (const k of ["head", "life", "heart", "fate"]) {
      const o = out[k]; if (!o || o.ex.b < 0) continue;
      const main = o.smooth.slice(o.ex.a, o.ex.b + 1); if (main.length < 15) continue;
      const others = Object.entries(out).filter(([kk, oo]) => kk !== k && oo && oo.smooth).map(([kk, oo]) => oo.smooth.slice(oo.ex.a, oo.ex.b + 1));
      let best = null;
      for (const off of [-0.09, -0.07, -0.05, -0.035, 0.035, 0.05, 0.07, 0.09]) {
        const sh = main.map((p, i) => { const a = main[Math.max(0, i - 2)], b = main[Math.min(main.length - 1, i + 2)], d = sub(b, a), l = nrm(d) || 1; return add(p, mul([-d[1] / l, d[0] / l], off * S)); });
        const tpl = sh.filter((_, i) => i % 4 === 0 || i === sh.length - 1);
        const tr = trace(R, TH, tpl, 4), ex = extent(tr.resp);
        if (ex.b < 0) continue;
        const seg = tr.path.slice(ex.a, ex.b + 1), str = avg(tr.resp.slice(ex.a, ex.b + 1));
        const lenFrac = (ex.b - ex.a + 1) / tr.resp.length;
        // 다른 선(예: 두뇌선 옆의 감정선·생명선)을 이중선으로 착각하지 않도록
        const nearOther = seg.filter(p => others.some(L => L.some(q => dist(p, q) < 7))).length / seg.length;
        const sep = avg(seg.map(p => Math.min(...main.map(q => dist(p, q)))));
        if (lenFrac < 0.4 || ex.fill < 0.75 || str < 0.6 || nearOther > 0.3 || sep < 0.025 * S) continue;
        const ratio = tr.score / nullScore(R, TH, tr.tpl, mask);
        if (ratio < 1.6) continue;
        if (!best || lenFrac * str > best.q) best = { q: lenFrac * str, pts: smooth(seg), lenFrac, str, ratio, off };
      }
      o.double = best;
    }
    const fg = fingers(P, M);
    const lines = buildLines(out, Pc);
    const big = bigLuck(lines, out, Pc, R, TH, Tall, mask);
    const bigBase = big.map(b => ({ ...b }));
    const features = toFeatures(lines, out, Pc, fg, opts.hand || side, big);
    const toImg = p => apply(Mi, p);
    for (const k in lines) {
      const L = lines[k]; L.img = L.pts.map(toImg); if (L.ticks) L.ticks.forEach(t => t.img = toImg(t.p));
      if (L.extra) L.extra.forEach(e => e.img = e.pts.map(toImg));
      if (L.double) L.double.img = L.double.pts.map(toImg);
    }
    big.forEach(b => { if (b.pts) b.img = b.pts.map(toImg); if (b.at) b.atImg = toImg(b.at); });
    const _ctx = { M, Mi, out, Pc, fg, bigBase, hand: opts.hand || side, Tall, W0, H0 };
    return { ok: true, side, cut, mirrored: M.mirrored, landmarks: P, lines, big, features, fingers: fg, ms: Math.round(performance.now() - t0), _ctx,
      debug: opts.debug ? { R: Rorig, mask, Pc, canvas: c, out } : null };
  }
  function convexHull(pts) {
    const p = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]), cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lo = [], up = [];
    for (const q of p) { while (lo.length >= 2 && cr(lo.at(-2), lo.at(-1), q) <= 0) lo.pop(); lo.push(q); }
    for (const q of p.slice().reverse()) { while (up.length >= 2 && cr(up.at(-2), up.at(-1), q) <= 0) up.pop(); up.push(q); }
    return lo.slice(0, -1).concat(up.slice(0, -1));
  }

  /* ---------- 표시용 선 + 신뢰도 ---------- */
  const NAMES = { life: "생명선", head: "두뇌선", heart: "감정선", fate: "운명선", sun: "재운선", business: "사업선" };
  const OPTIONAL = { fate: 1, sun: 1, business: 1 };
  function buildLines(out, Pc) {
    const L = {};
    for (const k of ["life", "head", "heart", "fate", "sun", "business"]) {
      const o = out[k], ex = o.ex, sm = o.smooth;
      const minFrac = { life: 0.35, head: 0.3, heart: 0.35, fate: 0.3, sun: 0.22, business: 0.3 }[k];
      const strength = ex.b < 0 ? 0 : avg(o.resp.slice(ex.a, ex.b + 1)), ratio = o.ratio;
      // 주요 3선은 거의 모든 손에 있으므로 길이·세기로, 운명·재운·사업선은 '바탕 대비 비율'로 있고 없음을 가린다
      const weak = ex.b < 0 || ex.frac < minFrac || (OPTIONAL[k] && ratio < PRES[k]);
      let conf = weak ? "low" : (OPTIONAL[k] ? ratio > PRES[k] * 1.5 : strength > 0.55) && ex.fill > 0.75 ? "high" : "mid";
      const none = () => (L[k] = { key: k, name: NAMES[k], conf: "none", pts: [], strength, ratio, gaps: [] });
      if (OPTIONAL[k] && conf === "low") { none(); continue; }
      const pts = conf === "low" ? sm : sm.slice(ex.a, ex.b + 1);
      const C = pts.map(cc);
      if (k === "sun" && C.at(-1)[1] < 0.66) { none(); continue; }                         // 재운선은 약지 아래까지 올라와야 인정
      if (k === "fate" && (C.at(-1)[1] < 0.5 || C.at(-1)[1] - C[0][1] < 0.3)) { none(); continue; }   // 운명선은 손바닥 위쪽(중지 방향)까지 어느 정도 길어야
      if (k === "business" && Math.hypot(C.at(-1)[0] - C[0][0], C.at(-1)[1] - C[0][1]) < 0.22) { none(); continue; }
      const gaps = conf === "low" ? [] : ex.gaps.map(([a, b]) => [a - ex.a, b - ex.a]);
      L[k] = { key: k, name: NAMES[k], conf, estimated: conf === "low", pts, strength, ratio, gaps };
    }
    // 이중선: 주선이 뚜렷할 때만
    for (const k of ["head", "life", "heart", "fate"]) {
      const o = out[k];
      if (o.double && L[k] && L[k].conf === "high") L[k].double = { pts: o.double.pts, lenFrac: o.double.lenFrac, ratio: o.double.ratio };
    }
    // 재운선 여러 가닥
    if (L.sun.conf !== "none") {
      L.sun.extra = out.sunExtra.map(e => ({ pts: e.smooth.slice(e.ex.a, e.ex.b + 1), ratio: e.ratio }))
        .filter(e => e.pts.length > 6 && cc(e.pts.at(-1))[1] > 0.66 && Math.abs(cc(e.pts.at(-1))[0] - cc(L.sun.pts.at(-1))[0]) > 0.025);
    }
    addTicks(L, Pc);
    return L;
  }

  function addTicks(L, Pc) {
    for (const k in L) if (L[k]) delete L[k].ticks;
    const meet = (A, B) => { let best = null; A.forEach((p, i) => B.forEach(q => { const d = dist(p, q); if (!best || d < best.d) best = { d, i, p }; })); return best; };
    // 운명선 유년법: 두뇌선과 만나는 곳 ≈ 35~38세, 감정선과 만나는 곳 ≈ 55세
    const F = L.fate;
    if (F.pts.length) {
      F.ticks = [];
      if (L.head?.pts.length) { const m = meet(F.pts, L.head.pts); if (m && m.d < 10) F.ticks.push({ p: m.p, label: "35~38세" }); }
      if (L.heart?.pts.length) { const m = meet(F.pts, L.heart.pts); if (m && m.d < 10) F.ticks.push({ p: m.p, label: "55세" }); }
    }
    // 재운선 유년: 시작점이 두뇌선 아래면 35세 전부터, 두뇌선~감정선 사이면 35~55세, 감정선 위에서만이면 55세 무렵 이후
    if (L.sun.pts.length) {
      const y0 = cc(L.sun.pts[0]);
      const hy = L.head.pts.length ? cc(nearestY(L.head.pts, Pc, y0))[1] : 0.5, ty = L.heart.pts.length ? cc(nearestY(L.heart.pts, Pc, y0))[1] : 0.76;
      L.sun.band = y0[1] < hy - 0.02 ? "early" : y0[1] < ty - 0.02 ? "mid" : "late";
      L.sun.ticks = [{ p: L.sun.pts[0], label: { early: "35세 전부터", mid: "35~55세", late: "55세 무렵~" }[L.sun.band] }];
    }
    if (L.life?.pts?.length > 10 && !L.life.estimated) { const n = L.life.pts.length; L.life.ticks = [{ p: L.life.pts[Math.floor(n * 0.5)], label: "40대 무렵" }]; }
  }

  /* ---------- 대박손금(재물 특수선) ---------- */
  function bigLuck(L, out, Pc, R, TH, T, mask) {
    // 대박손금은 '있다'고 말하는 순간 사용자에게 큰 의미가 되므로, 관련 선이 모두 '뚜렷(high)'일 때만 표시한다
    const B = [], on = k => L[k] && L[k].conf === "high" && !L[k].estimated, C = p => cc(p);
    const len = k => { const p = L[k].pts.map(C); return Math.hypot(p.at(-1)[0] - p[0][0], p.at(-1)[1] - p[0][1]); };
    const straight = k => { const p = L[k].pts.map(C), s = p[0], e = p.at(-1), ch = Math.hypot(e[0] - s[0], e[1] - s[1]) || 1;
      let dv = 0; p.forEach(q => dv = Math.max(dv, Math.abs((e[0] - s[0]) * (s[1] - q[1]) - (s[0] - q[0]) * (e[1] - s[1])) / ch)); return dv / ch < 0.08; };
    // 삼지창: 운명선 위쪽에서 태양구(약지 아래)와 수성구(소지 아래)로 갈라지는 가지가 둘 다 있을 때
    if (on("fate")) {
      const fp = L.fate.pts, top = fp.map(C).findIndex(q => q[1] > 0.6);
      if (top >= 0) {
        const o = fp[top], tryB = tgt => { let best = null;
          for (const dy of [0, 0.05]) { const e = T(px([tgt[0], tgt[1] + dy])), tpl = [o, lerp(o, e, 0.5), e];
            const tr = trace(R, TH, tpl, 5); tr.ratio = tr.score / nullScore(R, TH, tr.tpl, mask); if (!best || tr.ratio > best.ratio) best = tr; }
          return best; };
        const bs = tryB([-0.21, 0.84]), bm = tryB([-0.40, 0.72]);
        if (bs.ratio > 1.8 && bm.ratio > 1.8) B.push({ key: "삼지창", label: "삼지창", pts: smooth(bs.path), pts2: smooth(bm.path), at: o });
      }
    }
    // 럭키M: 생명선·두뇌선·감정선이 뚜렷하고, 운명선이 손목 쪽에서 감정선까지 올라가 M 자를 이룰 때
    if (on("life") && on("head") && on("heart") && on("fate")) {
      const f = L.fate.pts.map(C);
      if (f[0][1] < 0.3 && L.fate.ticks?.length >= 2) B.push({ key: "럭키M", label: "럭키M", at: L.fate.ticks[0].p });
    }
    // 운명선·재운선·사업선이 모두 뚜렷 = 전통 수상학에서 말하는 최고의 재물 손금, 셋 다 곧게 위로 = 川자 상향선
    if (on("fate") && on("sun") && on("business")) {
      B.push({ key: "재물3선", label: "재물 3선", at: L.sun.pts.at(-1) });
      if (straight("fate") && straight("sun")) B.push({ key: "川자상향선", label: "川자 상향선", at: L.fate.pts.at(-1) });
    }
    if (on("sun") && C(L.sun.pts[0])[1] < 0.5 && C(L.sun.pts.at(-1))[1] > 0.78) B.push({ key: "긴태양선", label: "긴 재운선", at: L.sun.pts[Math.floor(L.sun.pts.length * 0.55)] });
    if (on("sun") && (L.sun.extra || []).length >= 2) B.push({ key: "금전운", label: "재운선 여러 가닥", at: L.sun.pts.at(-1) });
    if (on("business") && len("business") > 0.5) B.push({ key: "긴사업선", label: "긴 사업선", at: L.business.pts.at(-1) });
    // 귀인선: 재운선이 손날 쪽(제2화성구)에서 출발
    if (on("sun")) { const s0 = C(L.sun.pts[0]); if (s0[0] < -0.36 && s0[1] > 0.3 && s0[1] < 0.66) B.push({ key: "귀인선", label: "귀인선", at: L.sun.pts[0] }); }
    return B;
  }
  const avg = a => a.length ? a.reduce((s, v) => s + v, 0) / a.length : 0;

  /* ---------- 측정값 → palm_rules.py 특징 키 ---------- */
  function toFeatures(L, out, Pc, fg, hand, big) {
    const C = p => cc(p), Q = i => C(Pc[i]);
    const clar = l => !l || l.conf === "none" ? "모름" : l.estimated ? "모름" : l.strength > 0.6 ? "강함" : l.strength > 0.38 ? "보통" : "약함";
    const f = { valid: true, hand, confidence: "auto", fingers: { thumb: fg.lv.thumb, index: fg.lv.index, middle: "모름", ring: fg.lv.ring, little: fg.lv.little },
      life: {}, head: {}, heart: {}, fate: {}, sun: {}, business: {}, simian: "없음" };
    const lf = L.life, hd = L.head, ht = L.heart, ft = L.fate, sn = L.sun, RAW = {};
    // 생명선
    if (lf && !lf.estimated) {
      const p = lf.pts.map(C), end = p.at(-1), minX = Math.min(...p.map(q => q[0])), p1 = Q(1);
      f.life.clarity = clar(lf);
      f.life.length = end[1] < 0.10 ? "긺" : end[1] < 0.25 ? "표준" : "짧음";
      const s0 = p[0], ch = Math.hypot(end[0] - s0[0], end[1] - s0[1]) || 1;
      let bulge = 0; p.forEach(q => { bulge = Math.max(bulge, Math.abs((end[0] - s0[0]) * (s0[1] - q[1]) - (s0[0] - q[0]) * (end[1] - s0[1])) / ch); });
      RAW.life_bulge = bulge; RAW.life_end = end[1];
      f.life.arc = bulge > 0.20 ? "큼" : bulge > 0.12 ? "보통" : "작음";   // 9장 테스트 사진 분포로 맞춘 기준
      if (lf.gaps.length) f.life.break = "끊겼다이어짐";
    }
    // 두뇌선
    if (hd && !hd.estimated) {
      const p = hd.pts.map(C), s = p[0], e = p.at(-1), edge = Q(17)[0] - 0.12;
      f.head.clarity = clar(hd);
      const span = (s[0] - e[0]) / (s[0] - edge);
      f.head.length = span > 0.95 ? "관통" : span > 0.72 ? "긺" : span > 0.45 ? "표준" : "짧음";
      const slope = (s[1] - e[1]) / Math.max(0.05, s[0] - e[0]);
      RAW.head_slope = slope; RAW.head_span = span;
      const mid = p[Math.floor(p.length / 2)], chordMidY = (s[1] + e[1]) / 2, sag = chordMidY - mid[1];
      f.head.direction = e[1] > s[1] + 0.05 ? "수성구상향" : slope > 0.9 ? "월구급경사" : slope < 0.15 ? "직선" : sag < -0.02 ? "직선후곡선" : "완만한곡선";
      if (lf && !lf.estimated) {
        // 두뇌선 시작점이 생명선 앞쪽 40% 구간과 얼마나 가까운가
        const ls = lf.pts.slice(0, Math.max(3, Math.floor(lf.pts.length * 0.4))).map(C), hs = p.slice(0, 4);
        const d0 = Math.min(...hs.map(q => Math.min(...ls.map(r => Math.hypot(q[0] - r[0], q[1] - r[1])))));
        RAW.join = d0;
        const join = d0 < 0.06 ? "붙음" : d0 < 0.16 ? "조금떨어짐" : "많이떨어짐";
        f.life.head_join = join;
        f.head.start = join === "붙음" ? "생명선과붙음" : join;
      }
      if (hd.gaps.length) f.head.form = "끊김";
    }
    // 감정선
    if (ht && !ht.estimated) {
      const p = ht.pts.map(C), s = p[0], e = p.at(-1), i5 = Q(5), m9 = Q(9);
      f.heart.clarity = clar(ht);
      const chord = Math.hypot(e[0] - s[0], e[1] - s[1]);
      let dev = 0; p.forEach(q => { const d = Math.abs((e[0] - s[0]) * (s[1] - q[1]) - (s[0] - q[0]) * (e[1] - s[1])) / chord; dev = Math.max(dev, d); });
      f.heart.shape = dev / chord < 0.045 ? "직선" : dev / chord < 0.10 ? "곡선" : "많이휜곡선";
      const gapX = (i5[0] + m9[0]) / 2;
      f.heart.end = e[0] > i5[0] - 0.02 ? (e[1] > i5[1] - 0.12 ? "목성구중앙" : "목성구기저") : e[0] > gapX - 0.04 ? "검지중지사이" : e[0] > m9[0] - 0.12 ? "토성구" : "아주짧음";
      const dropS = Q(17)[1] - s[1];
      f.heart.start_height = dropS < 0.06 ? "높음" : dropS < 0.15 ? "표준" : "낮음";
      if (ht.gaps.length) f.heart.form = "끊김";
    }
    // 운명선
    if (ft) {
      if (ft.conf === "none") f.fate.presence = "없음";
      else {
        const p = ft.pts.map(C), lo = p[0], hi = p.at(-1);
        f.fate.start = lo[1] < 0.15 ? (lo[0] < -0.12 ? "월구" : "손목중앙") : lo[1] < 0.4 ? (lo[0] > 0.1 ? "생명선" : "화성평원") : "두뇌선";
        const headY = hd && hd.pts.length ? C(nearestY(hd.pts, Pc, hi))[1] : 0.55, heartY = ht && ht.pts.length ? C(nearestY(ht.pts, Pc, hi))[1] : 0.8;
        f.fate.end = hi[1] > heartY + 0.03 ? "토성구" : hi[1] > headY + 0.04 ? "감정선에서멈춤" : "두뇌선에서멈춤";
        if (ft.gaps.length) f.fate.form = "끊김";
      }
    }
    // 재운선(태양선·재물선)
    const pres = l => l.ratio > PRES[l.key] * 1.8 && l.conf === "high" ? "강함" : l.ratio > PRES[l.key] * 1.25 ? "보통" : "약함";
    if (sn) {
      if (sn.conf === "none") f.sun.presence = "없음";
      else {
        const p = sn.pts.map(C), lo = p[0];
        f.sun.presence = pres(sn);
        const n = 1 + (sn.extra || []).length;
        f.sun.count = n >= 3 ? "여러" : String(n);
        const nearFate = ft && ft.pts.length && Math.min(...ft.pts.map(q => Math.hypot(C(q)[0] - lo[0], C(q)[1] - lo[1]))) < 0.04;
        f.sun.start = nearFate ? "운명선" : lo[1] < 0.3 ? (lo[0] < -0.3 ? "월구" : "손바닥아래")
          : lo[0] < -0.36 && lo[1] < 0.66 ? "제2화성구" : sn.band === "late" ? "감정선위" : sn.band === "mid" ? (lo[1] < 0.56 ? "두뇌선" : "화성평원") : "손바닥아래";
        RAW.sun_ratio = sn.ratio; RAW.sun_len = Math.hypot(p.at(-1)[0] - lo[0], p.at(-1)[1] - lo[1]);
      }
    }
    // 사업선
    const bz = L.business;
    if (bz) {
      if (bz.conf === "none") f.business.presence = "없음";
      else {
        const p = bz.pts.map(C), lo = p[0];
        f.business.presence = pres(bz);
        const nearFate = ft && ft.pts.length && Math.min(...ft.pts.map(q => Math.hypot(C(q)[0] - lo[0], C(q)[1] - lo[1]))) < 0.04;
        f.business.start = nearFate ? "운명선" : lo[0] > 0.18 && lo[1] > 0.12 ? "금성구" : lo[1] > 0.4 ? "두뇌선" : "손바닥아래";
        f.business.form = bz.gaps.length ? "구불구불" : "곧음";
        RAW.business_ratio = bz.ratio; RAW.business_len = Math.hypot(p.at(-1)[0] - lo[0], p.at(-1)[1] - lo[1]);
      }
    }
    if (ft && ft.conf !== "none") { RAW.fate_ratio = ft.ratio; f.fate.presence = pres(ft); }
    for (const k of ["head", "life", "heart", "fate"]) if (L[k]?.double) { f[k].double = true; RAW[k + "_double"] = L[k].double.lenFrac; }
    if (L.life?.double) big.push({ key: "이중생명선", label: "이중 생명선", at: L.life.double.pts[Math.floor(L.life.double.pts.length / 2)] });
    if (L.head?.double) big.push({ key: "이중두뇌선", label: "이중 두뇌선", at: L.head.double.pts[Math.floor(L.head.double.pts.length / 2)] });
    f.specials = big.filter(b => ["삼지창", "럭키M", "川자상향선", "귀인선"].includes(b.key)).map(b => b.key);
    if (L.life?.double) f.specials.push("이중생명선");
    f.money_marks = big.map(b => b.key);
    f.sun_band = sn && sn.band || "";
    // 손 모양 (오행형, 2D 비율만)
    const wl = dist(Q(5), Q(17)) * 1.28, fl = fg.fingerPalm;
    f.ohaeng_shape = wl > 0.97 && wl < 1.15 ? (fl < 0.9 ? "토형" : "모름") : wl < 0.78 ? (fl > 1.0 ? "목형" : "금형") : "모름";
    f._measure = { raw: Object.fromEntries(Object.entries(RAW).map(([k, v]) => [k, +v.toFixed(3)])), palm_wl: +wl.toFixed(2), finger_palm: +fl.toFixed(2), finger_raw: Object.fromEntries(Object.entries(fg.raw).map(([k, v]) => [k, +v.toFixed(2)])) };
    return f;
  }
  function nearestY(pts, Pc, target) {   // target(표준좌표)과 x가 가장 가까운 점
    let best = pts[0], bd = 1e9; pts.forEach(p => { const d = Math.abs(cc(p)[0] - target[0]); if (d < bd) { bd = d; best = p; } }); return best;
  }

  /* ---------- 사용자 확인·수정 반영 (사진 다시 분석 없이, 기기 안에서) ----------
     edits: { key: 이미지 좌표 점 배열 | null(선 없음) }. 원래 '안 보임'이던 선을 사용자가 그리면 '희미함(약함)'으로만 인정하고
     대박손금(뚜렷한 선만 인정)은 새로 만들지 않는다 → 없는 것을 지어내지 않음 */
  const BIG_DEPS = { 삼지창: ["fate"], 럭키M: ["life", "head", "heart", "fate"], 재물3선: ["fate", "sun", "business"], 川자상향선: ["fate", "sun", "business"],
    긴태양선: ["sun"], 금전운: ["sun"], 긴사업선: ["business"], 귀인선: ["sun"] };
  function refine(res, edits) {
    const X = res._ctx; if (!X) throw new Error("no context");
    const L = res.lines, toImg = p => apply(X.Mi, p);
    for (const [k, e] of Object.entries(edits || {})) {
      const l = L[k];
      if (!e || e.length < 2) { L[k] = { key: k, name: NAMES[k], conf: "none", pts: [], img: [], strength: 0, ratio: 0, gaps: [], user: "none" }; continue; }
      const wasNone = !l || l.conf === "none";
      const nl = { ...(l || {}), key: k, name: NAMES[k], pts: e.map(p => apply(X.M, p)), img: e.map(p => [p[0], p[1]]), user: "edit", gaps: [], estimated: false };
      if (wasNone) { Object.assign(nl, { conf: "mid", strength: 0.4, ratio: PRES[k] * 1.1, faint: true }); delete nl.double; delete nl.extra; }
      else if (l.estimated) Object.assign(nl, { conf: "mid", faint: true });
      L[k] = nl;
    }
    addTicks(L, X.Pc);
    for (const k in L) (L[k].ticks || []).forEach(t => t.img = toImg(t.p));
    const big = X.bigBase.filter(b => !BIG_DEPS[b.key] || BIG_DEPS[b.key].every(d => L[d] && L[d].conf === "high")).map(b => ({ ...b }));
    const features = toFeatures(L, X.out, X.Pc, X.fg, X.hand, big);
    big.forEach(b => { if (b.pts) b.img = b.pts.map(toImg); if (b.at) b.atImg = toImg(b.at); });
    res.big = big; res.features = features;
    return res;
  }
  // 못 찾은 선을 사용자가 그릴 때 시작 모양: 보통 그 선이 있는 자리(이 손에 맞춘 평균 위치)
  function seed(res, k) {
    const X = res._ctx; if (!X) return [];
    // 보통 그 선이 있는 자리(평균 위치): 재운선=약지 축, 사업선=손바닥 아래 가운데→비스듬히 약지·새끼 사이 아래 태양구 위쪽까지, 운명선=손목 가운데→중지
    const TPL = { sun: [[-0.22, 0.48], [-0.215, 0.68], [-0.21, 0.88]], business: [[0.10, 0.12], [-0.06, 0.32], [-0.22, 0.55], [-0.31, 0.74], [-0.34, 0.88]], fate: [[0.02, 0.04], [0.02, 0.33], [0.01, 0.62], [0.0, 0.9]], heart: hyps("heart")[13] };
    const h = (k === "life" || k === "head") ? anchoredHyps(k, X.Pc, X.Tall)[k === "life" ? 22 : 89] || anchoredHyps(k, X.Pc, X.Tall)[0] : (TPL[k] || hyps(k)[0]).map(c => X.Tall(px(c)));
    return catmull(h, 12).map(p => apply(X.Mi, p));
  }
  // 사진 품질: 밝기(평균 휘도)와 선명도(라플라시안 분산). 흐리거나 어두우면 다시 찍기 안내
  function quality(src) {
    const w0 = src.naturalWidth || src.width, h0 = src.naturalHeight || src.height, k = 480 / Math.max(w0, h0);
    const w = Math.round(w0 * k), h = Math.round(h0 * k), c = document.createElement("canvas"); c.width = w; c.height = h;
    const x = c.getContext("2d", { willReadFrequently: true }); x.drawImage(src, 0, 0, w, h);
    const d = x.getImageData(0, 0, w, h).data, g = new Float32Array(w * h);
    let sum = 0; for (let i = 0; i < w * h; i++) { g[i] = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]; sum += g[i]; }
    const mean = sum / (w * h);
    // 가운데 60% 영역(손바닥이 있을 곳)의 라플라시안 분산
    let n = 0, s1 = 0, s2 = 0;
    for (let y = Math.round(h * 0.2); y < h * 0.8; y++) for (let xx = Math.round(w * 0.2); xx < w * 0.8; xx++) {
      const i = y * w + xx, l = 4 * g[i] - g[i - 1] - g[i + 1] - g[i - w] - g[i + w]; s1 += l; s2 += l * l; n++;
    }
    const lap = s2 / n - (s1 / n) ** 2;
    let cm = 0; for (let y = Math.round(h * 0.2); y < h * 0.8; y++) for (let xx = Math.round(w * 0.2); xx < w * 0.8; xx++) cm += g[y * w + xx];
    cm /= n;
    return { mean: +mean.toFixed(1), center: +cm.toFixed(1), sharp: +lap.toFixed(1), dark: cm < 70, blurry: lap < 18, bright: cm > 245 };
  }

  window.PalmDetect = { analyze, loadLandmarker, NAMES, refine, seed, quality, catmull, fitAffine };
})();
