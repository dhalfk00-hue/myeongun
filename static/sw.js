/* 손명리 서비스 워커: 앱 화면·손 인식 모델을 기기에 저장해 빠르게 열고, 오프라인에서도 첫 화면이 뜨게 함.
   개인 정보가 든 API 응답(/api/)과 감정서는 저장하지 않음. */
const VER = "sonmyeongri-v8";
const SHELL = ["/", "/static/m.css?v=6", "/static/m.js?v=5", "/static/palm_detect.js?v=8", "/static/palm_guide.js?v=8", "/static/palm_flow.js?v=8", "/static/img/palm_hand.webp", "/static/fonts/pretendard-400.woff2", "/static/fonts/pretendard-600.woff2", "/static/fonts/notoserifkr-400.woff2", "/static/fonts/notoserifkr-700.woff2",
  "/manifest.webmanifest", "/static/icons/icon-192.png", "/static/icons/icon-512.png", "/privacy"];
self.addEventListener("install", e => { e.waitUntil(caches.open(VER).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VER).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin || u.pathname.startsWith("/api/")) return;   // 개인 데이터는 항상 네트워크
  if (u.pathname.startsWith("/static/vendor/")) {   // 손 인식 모델(큰 파일): 한 번 받으면 기기에 보관
    e.respondWith(caches.open(VER + "-vendor").then(c => c.match(e.request).then(r => r || fetch(e.request).then(n => { if (n.ok) c.put(e.request, n.clone()); return n; }))));
    return;
  }
  // 화면 파일: 네트워크 먼저(새 버전 반영), 안 되면 저장본
  e.respondWith(fetch(e.request).then(n => { if (n.ok) caches.open(VER).then(c => c.put(e.request, n.clone())); return n; }).catch(() => caches.match(e.request).then(r => r || caches.match("/"))));
});
