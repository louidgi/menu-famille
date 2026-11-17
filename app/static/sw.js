// SPDX-License-Identifier: AGPL-3.0-or-later
// Service worker : coquille de l'app + dernières réponses de l'API, pour consulter menus et courses sans réseau.
// Réseau d'abord, cache en secours. Les écritures (POST/PUT/DELETE) ne passent jamais par le cache.
const V = 'mf-v1';
const SHELL = ['/', '/style.css', '/app.js', '/manifest.webmanifest', '/icon-192.png'];
self.addEventListener('install', e => e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;
  if (u.pathname === '/api/me' || u.pathname === '/api/backup') return;
  const isApi = u.pathname.startsWith('/api/');
  e.respondWith(fetch(e.request).then(r => {
    if (r.ok) { const copy = r.clone(); caches.open(V).then(c => c.put(e.request, copy)); }
    return r;
  }).catch(() => caches.match(e.request).then(m => m ||
    (isApi ? new Response(JSON.stringify({ detail: 'Hors ligne' }), { status: 503, headers: { 'Content-Type': 'application/json' } })
           : caches.match('/')))));
});
self.addEventListener('message', e => { if (e.data === 'clear') caches.delete(V); }); // à la déconnexion
