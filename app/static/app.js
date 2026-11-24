// SPDX-License-Identifier: AGPL-3.0-or-later
'use strict';
// ---------- utilitaires ----------
const SLOT = { lunch: 'Déjeuner', dinner: 'Dîner' };
const PROT = { volaille: 'Volaille', boeuf: 'Bœuf', porc: 'Porc', poisson: 'Poisson', oeuf: 'Œufs', veggie: 'Végétarien', autre: 'Autre' };
const CARB = { pates: 'Pâtes', riz: 'Riz', pdt: 'Pommes de terre', semoule: 'Semoule', pain: 'Pain', autre: 'Autre' };
const DAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];
const $ = (s, el = document) => el.querySelector(s);
const fmtDate = iso => new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long' }).format(new Date(iso + 'T12:00:00'));
const euro = n => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(n);
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
const uid = () => (crypto.randomUUID ? crypto.randomUUID() : 'o' + Date.now() + Math.random().toString(16).slice(2));
const safeUrl = u => { try { const x = new URL(u); return /^https?:$/.test(x.protocol) ? x.href : null; } catch { return null; } };
const toggleLock = e => guard(async () => {
  const y = window.scrollY;
  await post(`/plan/${e.id}/lock`, { locked: !e.locked });
  await route(); window.scrollTo(0, y);
});

// Construction du DOM sans innerHTML : le contenu importé des sites n'est jamais interprété comme du HTML.
function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (k === 'class') el.className = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (v === true) el.setAttribute(k, '');
    else if (v !== false && v != null) el.setAttribute(k, v);
  }
  for (const c of kids.flat(Infinity)) if (c != null && c !== false) el.append(c.nodeType ? c : document.createTextNode(c));
  return el;
}
// replaceChildren/append convertissent null et les tableaux en texte : on aplatit et on filtre toujours.
function put(el, ...kids) { el.replaceChildren(...kids.flat(Infinity).filter(c => c != null && c !== false)); }
let toastT;
function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('on'); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('on'), 3500); }

class Offline extends Error {}
async function api(path, opts = {}) {
  let r;
  try {
    r = await fetch('/api' + path, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined });
  } catch { throw new Offline('Hors ligne'); }
  if (r.status === 401) { showLogin(); throw new Error('Non connecté'); }
  if (r.status === 503 && (opts.method || 'GET') === 'GET') throw new Offline('Hors ligne');
  if (!r.ok) { let m = 'Erreur ' + r.status; try { m = (await r.json()).detail || m; } catch {} throw new Error(m); }
  return r.json();
}
const post = (p, body) => api(p, { method: 'POST', body: body || {} });
const guard = fn => async (...a) => { try { return await fn(...a); } catch (e) { if (e.message !== 'Non connecté') toast(e instanceof Offline ? 'Hors ligne : action impossible pour le moment.' : e.message); } };

// ---------- boîtes de dialogue ----------
function dialog(build) {
  const d = $('#dlg'); d.replaceChildren();
  const close = () => d.close();
  build(d, close);
  if (!d.open) d.showModal();
}
const closeBtn = (close, label = 'Annuler') => h('button', { type: 'button', onclick: close }, label);

// ---------- routage ----------
let state = { settings: null, names: [] };
async function route() {
  const hash = location.hash || '#/menus';
  const [, tab, arg] = hash.split('/');
  document.querySelectorAll('#tabs a').forEach(a => a.toggleAttribute('aria-current', a.dataset.tab === (tab === 'recette' ? 'recettes' : tab)) || a.removeAttribute('aria-current'));
  document.querySelectorAll('#tabs a').forEach(a => { if (a.dataset.tab === (tab === 'recette' ? 'recettes' : tab)) a.setAttribute('aria-current', 'page'); });
  const root = $('#view');
  root.replaceChildren(h('p', { class: 'muted' }, 'Chargement…'));
  try {
    const v = { menus: viewMenus, courses: viewCourses, recettes: viewRecipes, recette: viewRecipe, reglages: viewSettings }[tab] || viewMenus;
    const node = await v(arg);
    put(root, node);
  } catch (e) {
    if (e.message === 'Non connecté') return;
    root.replaceChildren(h('p', {}, e instanceof Offline ? 'Hors ligne et rien en mémoire pour cet écran. Reconnectez-vous puis réessayez.' : e.message));
  }
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', route);
const refresh = () => route();

// ---------- connexion ----------
function showLogin() {
  $('#tabs').hidden = true;
  const pw = h('input', { type: 'password', autocomplete: 'current-password', required: true, id: 'pw' });
  const err = h('p', { class: 'badge', hidden: true });
  put($('#view'), h('h1', {}, 'Menus de la famille'), h('form', {
    onsubmit: async ev => {
      ev.preventDefault();
      try { await post('/login', { password: pw.value }); await start(); } catch (e) { err.hidden = false; err.textContent = e instanceof Offline ? 'Connexion impossible : pas de réseau.' : e.message; }
    }
  }, h('label', { for: 'pw' }, 'Mot de passe'), pw, err, h('p', {}, h('button', { class: 'primary', type: 'submit' }, 'Se connecter'))));
}

// ---------- menus ----------
async function viewMenus() {
  const [plan, settings] = await Promise.all([api('/plan'), api('/settings')]);
  state.settings = settings;
  const today = new Date().toISOString().slice(0, 10);
  const over = plan.budget && plan.total_cost > plan.budget;
  const nLocked = plan.days.flatMap(d => d.entries).filter(e => e.locked && e.recipe).length;
  const head = [h('div', { class: 'between' }, h('h1', {}, 'Menus'),
    h('button', { onclick: guard(() => dialog((d, close) => { d.append(h('h3', {}, 'Régénérer le planning ?'), h('p', {}, 'Les repas verrouillés et les absences sont conservés, tous les autres sont retirés au hasard.'),
      h('menu', {}, closeBtn(close), h('button', { class: 'primary', onclick: guard(async () => { close(); await post('/plan/generate'); toast('Planning régénéré'); refresh(); }) }, 'Régénérer'))); })) }, 'Régénérer')),
    h('div', { class: 'bar' }, h('span', {}, 'Coût estimé des repas : '), h('strong', {}, euro(plan.total_cost)),
      plan.budget ? h('span', { class: over ? 'over' : 'muted' }, ` sur ${euro(plan.budget)} de budget`) : h('span', { class: 'muted small' }, ' (budget à régler dans Réglages)'),
      settings.shopping_locked_only ? h('div', { class: 'small muted' }, `${nLocked} repas verrouillé(s) alimentent la liste de courses.`) : null)];
  return [...head, ...plan.days.map(d => dayBlock(d, d.date === today))];
}
function dayBlock(d, isToday) {
  return h('section', { class: 'day' + (isToday ? ' today' : '') },
    h('header', {}, h('h2', {}, cap(d.weekday)), h('span', { class: 'muted' }, fmtDate(d.date))),
    d.entries.map(e => mealRow(e, d)),
    d.free_slots.length ? h('div', { class: 'row', style: 'margin-top:.4rem' }, d.free_slots.map(s => h('button', { class: 'ghost', onclick: guard(async () => { await post('/plan/add', { day: d.date, slot: s }); refresh(); }) }, '+ ' + SLOT[s]))) : null);
}
function mealRow(e, d) {
  if (e.status === 'skipped') return h('div', { class: 'meal' }, h('div', { class: 'grow absent' }, SLOT[e.slot] + ' : absent'),
    h('button', { onclick: guard(async () => { await post(`/plan/${e.id}/restore`); refresh(); }) }, 'Remettre un repas'));
  const r = e.recipe;
  if (!r) return h('div', { class: 'meal' }, h('div', { class: 'grow muted' }, SLOT[e.slot] + ' : aucune recette disponible'), h('button', { class: 'more', onclick: () => mealMenu(e, d) }, '⋯'));
  return h('div', { class: 'meal' },
    h('div', { class: 'grow' }, h('div', { class: 'small muted' }, SLOT[e.slot], e.locked ? h('span', { class: 'tag lock' }, 'verrouillé') : null),
      h('button', { class: 'title', onclick: () => { location.hash = '#/recette/' + r.id; } }, r.title),
      h('div', { class: 'small muted' }, [r.minutes ? r.minutes + ' min' : null, PROT[r.protein], e.cost != null ? '≈ ' + euro(e.cost) : null].filter(Boolean).join(' · '))),
    h('div', { class: 'row' },
      h('button', { class: 'more' + (e.locked ? ' on' : ''), 'aria-pressed': String(e.locked),
        'aria-label': (e.locked ? 'Déverrouiller ' : 'Verrouiller ') + r.title,
        onclick: toggleLock(e) }, e.locked ? '🔒' : '🔓'),
      h('button', { class: 'more', 'aria-label': 'Actions pour ' + r.title, onclick: () => mealMenu(e, d) }, '⋯')));
}
function mealMenu(e, d) {
  dialog((dlg, close) => {
    dlg.append(h('h3', {}, `${cap(d.weekday)} · ${SLOT[e.slot]}`), h('p', { class: 'muted' }, e.recipe ? e.recipe.title : ''), h('div', { class: 'stack' },
      h('button', { onclick: () => { close(); changeDialog(e, d); } }, 'Changer ce repas'),
      h('button', { onclick: () => { close(); pickDialog(e); } }, 'Choisir une recette précise'),
      h('button', { onclick: () => { close(); skipDialog(e); } }, 'Absent : supprimer ce repas'),
      h('button', { onclick: guard(async () => { close(); await post(`/plan/${e.id}/lock`, { locked: !e.locked }); refresh(); }) }, e.locked ? 'Déverrouiller' : 'Verrouiller (ne pas changer)')),
      h('menu', {}, closeBtn(close, 'Fermer')));
  });
}
const followBox = () => h('input', { type: 'checkbox', checked: true, id: 'follow' });
async function changeDialog(e, d) {
  const rec = await api('/recipes/' + e.recipe.id).catch(() => null);
  const opts = rec ? [...new Set(rec.ingredients.filter(i => !i.basic).map(i => i.ingredient))] : [];
  dialog((dlg, close) => {
    const sel = h('select', { id: 'ing' }, opts.map(o => h('option', { value: o }, o)), h('option', { value: '' }, 'Un autre…'));
    const free = h('input', { placeholder: 'Ingrédient refusé', hidden: !!opts.length });
    sel.onchange = () => { free.hidden = sel.value !== ''; };
    const f = followBox();
    const isFishDay = (state.settings?.fish_days || []).includes((new Date(d.date + 'T12:00:00').getDay() + 6) % 7);
    const nf = h('input', { type: 'checkbox' });
    dlg.append(h('h3', {}, 'Pourquoi changer ce repas ?'), h('form', { id: 'chg' },
      h('label', { class: 'inline' }, h('input', { type: 'radio', name: 'why', value: 'refuse_ingredient', checked: true }), 'Un ingrédient ne convient pas'),
      h('div', {}, sel, free),
      h('label', { class: 'inline' }, h('input', { type: 'radio', name: 'why', value: 'too_expensive' }), 'Trop cher (pour ce remplacement seulement)'),
      h('label', { class: 'inline' }, h('input', { type: 'radio', name: 'why', value: 'other' }), 'Autre envie'),
      h('label', { class: 'inline' }, f, 'Régénérer les repas suivants pour rester équilibré')),
      isFishDay ? h('label', { class: 'inline' }, nf, 'Sans poisson (ce jour est un jour de poisson)') : null,
      h('p', { class: 'small muted' }, 'Un ingrédient refusé est mémorisé pour tous les menus suivants ; vous pourrez le retirer dans Réglages.'),
      h('menu', {}, closeBtn(close), h('button', { class: 'primary', onclick: guard(async () => {
        const why = dlg.querySelector('input[name=why]:checked').value;
        const ing = sel.value || free.value.trim();
        if (why === 'refuse_ingredient' && !ing) { toast('Indiquez l\'ingrédient refusé'); return; }
        const r = await post(`/plan/${e.id}/replace`, { reason: why, ingredient: why === 'refuse_ingredient' ? ing : null, regenerate_following: f.checked, allow_non_fish: nf.checked });
        close(); toast(r.regenerated ? `Repas changé, ${r.regenerated} repas suivants ajustés` : 'Repas changé'); refresh();
      }) }, 'Changer')));
  });
}
function skipDialog(e) {
  dialog((dlg, close) => {
    const f = followBox();
    dlg.append(h('h3', {}, 'Supprimer ce repas ?'), h('p', {}, 'Il sort du planning et de la liste de courses.'),
      h('label', { class: 'inline' }, f, 'Régénérer les repas suivants'),
      h('menu', {}, closeBtn(close), h('button', { class: 'danger', onclick: guard(async () => { await post(`/plan/${e.id}/skip`, { regenerate_following: f.checked }); close(); refresh(); }) }, 'Supprimer')));
  });
}
async function pickDialog(e) {
  const list = await api('/recipes');
  dialog((dlg, close) => {
    const sel = h('select', {}, list.map(r => h('option', { value: r.id }, r.title)));
    const f = followBox(); f.checked = false;
    dlg.append(h('h3', {}, 'Choisir une recette'), sel, h('label', { class: 'inline' }, f, 'Régénérer les repas suivants'),
      h('menu', {}, closeBtn(close), h('button', { class: 'primary', onclick: guard(async () => { await post(`/plan/${e.id}/set_recipe`, { recipe_id: +sel.value, regenerate_following: f.checked }); close(); refresh(); }) }, 'Choisir')));
  });
}

// ---------- recettes ----------
async function viewRecipes() {
  const list = await api('/recipes');
  const ul = h('div', {});
  const draw = q => ul.replaceChildren(...list.filter(r => r.title.toLowerCase().includes(q.toLowerCase())).map(r =>
    h('div', { class: 'item' }, h('div', { class: 'grow' }, h('button', { class: 'link', style: 'text-align:left;text-decoration:none;font-family:var(--serif);font-size:1.05rem;font-weight:700;color:var(--ink)', onclick: () => { location.hash = '#/recette/' + r.id; } }, (r.favorite ? '★ ' : '') + r.title),
      h('div', { class: 'small muted' }, [PROT[r.protein], CARB[r.carb], r.source_type === 'seed' ? 'bibliothèque de départ' : r.source_type === 'import' ? 'importée' : 'saisie'].join(' · '))))));
  const q = h('input', { type: 'search', placeholder: 'Rechercher une recette', 'aria-label': 'Rechercher', oninput: ev => draw(ev.target.value) });
  draw('');
  return [h('div', { class: 'between' }, h('h1', {}, 'Recettes'), h('button', { class: 'primary', onclick: () => addRecipeDialog() }, 'Ajouter')), q, h('p', { class: 'muted small' }, `${list.length} recettes en bibliothèque`), ul];
}
function addRecipeDialog() {
  dialog((dlg, close) => {
    const url = h('input', { type: 'url', placeholder: 'https://www.marmiton.org/recettes/…' });
    const html = h('textarea', { placeholder: 'Collez ici le code source de la page (affichage du code source dans votre navigateur)', hidden: true });
    const msg = h('p', { class: 'badge', hidden: true });
    const go = guard(async () => {
      msg.hidden = true;
      try {
        const draft = await post('/recipes/import', { url: url.value.trim(), html: html.value || null });
        close(); recipeForm(draft);
      } catch (e) { if (e instanceof Offline) throw e; msg.hidden = false; msg.textContent = e.message; html.hidden = false; }
    });
    dlg.append(h('h3', {}, 'Ajouter une recette'), h('label', {}, 'Adresse de la page'), url, msg, html,
      h('menu', {}, closeBtn(close), h('button', { onclick: () => { close(); recipeForm(null); } }, 'Saisir à la main'), h('button', { class: 'primary', onclick: go }, 'Importer')));
  });
}
async function ingredientNames() {
  if (!state.names.length) state.names = (await api('/ingredients').catch(() => [])).map(i => i.name);
  return state.names;
}
async function recipeForm(draft, existingId) {
  const names = await ingredientNames();
  const d = draft || { title: '', servings: 4, prep_min: null, cook_min: null, protein: 'autre', carb: 'autre', meals: 'dl', steps: [], ingredients: [{ raw: '' }, { raw: '' }, { raw: '' }], months: [], tags: [] };
  const lines = d.ingredients.map(l => ({ raw: l.raw, ingredient: l.ingredient || '', status: l.status || 'ok' }));
  const f = {
    title: h('input', { value: d.title, required: true }), servings: h('input', { type: 'number', min: 1, step: 0.5, value: d.servings || 4 }),
    prep: h('input', { type: 'number', min: 0, value: d.prep_min ?? '' }), cook: h('input', { type: 'number', min: 0, value: d.cook_min ?? '' }),
    protein: h('select', {}, Object.entries(PROT).map(([k, v]) => h('option', { value: k, selected: k === d.protein }, v))),
    carb: h('select', {}, Object.entries(CARB).map(([k, v]) => h('option', { value: k, selected: k === d.carb }, v))),
    meals: h('select', {}, [['dl', 'Déjeuner ou dîner'], ['d', 'Dîner'], ['l', 'Déjeuner']].map(([k, v]) => h('option', { value: k, selected: k === d.meals }, v))),
    steps: h('textarea', { rows: 6 }, d.steps.join('\n')),
  };
  const dl = h('datalist', { id: 'ingnames' }, names.map(n => h('option', { value: n })));
  const box = h('div', {});
  const drawLines = () => box.replaceChildren(...lines.map((l, i) => h('div', { class: 'line' },
    h('input', { value: l.raw, placeholder: '200 g de farine', 'aria-label': 'Ligne ' + (i + 1), oninput: e => { l.raw = e.target.value; } }),
    h('input', { value: l.ingredient, list: 'ingnames', placeholder: 'ingrédient reconnu', 'aria-label': 'Ingrédient ' + (i + 1), oninput: e => { l.ingredient = e.target.value; } }),
    l.status === 'ok' ? h('span', {}) : h('span', { class: 'badge' }, l.status === 'unknown' ? 'inconnu' : 'à vérifier'))));
  drawLines();
  const src = d.source_url && safeUrl(d.source_url);
  put($('#view'), h('h1', {}, existingId ? 'Modifier la recette' : draft ? 'Vérifier la recette importée' : 'Nouvelle recette'), dl,
    draft && !existingId ? h('p', { class: 'muted' }, 'Relisez les ingrédients : ceux marqués « à vérifier » ou « inconnu » peuvent fausser la liste de courses. Corrigez le nom reconnu si besoin.') : null,
    h('label', {}, 'Titre'), f.title, h('div', { class: 'grid2' }, h('div', {}, h('label', {}, 'Nombre de personnes'), f.servings), h('div', {}, h('label', {}, 'Repas'), f.meals)),
    h('div', { class: 'grid2' }, h('div', {}, h('label', {}, 'Préparation (min)'), f.prep), h('div', {}, h('label', {}, 'Cuisson (min)'), f.cook)),
    h('div', { class: 'grid2' }, h('div', {}, h('label', {}, 'Protéine principale'), f.protein), h('div', {}, h('label', {}, 'Féculent'), f.carb)),
    h('label', {}, 'Ingrédients'), box, h('button', { class: 'ghost', onclick: () => { lines.push({ raw: '', ingredient: '', status: 'ok' }); drawLines(); } }, '+ Ajouter une ligne'),
    h('label', {}, 'Étapes (une par ligne)'), f.steps,
    h('p', { class: 'row', style: 'margin-top:1rem' }, h('button', { onclick: () => history.back() }, 'Annuler'), h('button', { class: 'primary', onclick: guard(async () => {
      if (!f.title.value.trim()) { toast('Le titre est obligatoire'); return; }
      const body = { title: f.title.value.trim(), servings: +f.servings.value || 4, prep_min: f.prep.value === '' ? null : +f.prep.value, cook_min: f.cook.value === '' ? null : +f.cook.value,
        protein: f.protein.value, carb: f.carb.value, meals: f.meals.value, months: d.months || [], tags: d.tags || [], source_url: src || null, source_type: existingId ? (d.source_type || 'manual') : draft ? 'import' : 'manual', image_url: null,
        steps: f.steps.value.split('\n').map(s => s.trim()).filter(Boolean), ingredients: lines.filter(l => l.raw.trim()).map(l => l.ingredient.trim() ? { raw: l.raw, ingredient: l.ingredient.trim() } : l.raw) };
      const r = existingId ? await api('/recipes/' + existingId, { method: 'PUT', body }) : await post('/recipes', body);
      state.names = []; toast('Recette enregistrée'); location.hash = '#/recette/' + r.id;
    }) }, 'Enregistrer')));
}
async function viewRecipe(id) {
  const r = await api('/recipes/' + id);
  const src = r.source_url && safeUrl(r.source_url);
  const rate = (rating, favorite) => guard(async () => { await post(`/recipes/${id}/rate`, { rating, favorite }); toast('Noté'); refresh(); });
  return [h('p', {}, h('button', { class: 'link', onclick: () => history.back() }, '← Retour')), h('h1', {}, r.title),
    h('p', { class: 'muted' }, [r.prep_min ? `préparation ${r.prep_min} min` : null, r.cook_min ? `cuisson ${r.cook_min} min` : null, PROT[r.protein], `≈ ${euro(r.cost)} pour la famille`].filter(Boolean).join(' · ')),
    h('h3', {}, `Ingrédients pour la famille (${String(r.family_portions).replace('.', ',')} portions d'adulte)`),
    h('ul', { class: 'ing' }, r.ingredients.map(i => h('li', {}, i.basic ? h('span', { class: 'muted' }, `${i.ingredient} (au goût)`) : [i.text ? i.text + ' ' : '', i.ingredient, i.optional ? ' (facultatif)' : '', i.verified ? null : h('span', { class: 'badge', style: 'margin-left:.4rem' }, 'à vérifier')]))),
    h('h3', { style: 'margin-top:1rem' }, 'Préparation'), h('p', { class: 'small muted' }, 'Touchez une étape pour la barrer.'),
    h('ol', { class: 'steps' }, r.steps.map(s => h('li', { onclick: ev => ev.currentTarget.classList.toggle('done') }, s))),
    src ? h('p', {}, 'Recette d\'origine : ', h('a', { href: src, target: '_blank', rel: 'noopener noreferrer' }, new URL(src).hostname)) : null,
    h('p', { class: 'row', style: 'flex-wrap:wrap' }, h('button', { onclick: rate(1, true) }, '★ Favori'), h('button', { onclick: rate(1, false) }, 'On aime'), h('button', { onclick: rate(0, false) }, 'Neutre'), h('button', { onclick: rate(-1, false) }, 'On aime moins')),
    h('p', { class: 'row' }, h('button', { onclick: () => recipeForm({ ...r, prep_min: r.prep_min, cook_min: r.cook_min, steps: r.steps, ingredients: r.ingredients.map(i => ({ raw: i.raw, ingredient: i.ingredient })) }, id) }, 'Modifier'),
      h('button', { class: 'danger', onclick: guard(async () => { if (confirm('Supprimer cette recette ? Elle disparaîtra des futurs menus.')) { await api('/recipes/' + id, { method: 'DELETE' }); location.hash = '#/recettes'; } }) }, 'Supprimer'))];
}

// ---------- courses (avec file d'attente hors-ligne) ----------
const LS = { shop: 'mf_shop', queue: 'mf_queue' };
const lsGet = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
const lsSet = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
let shop = lsGet(LS.shop, null);
function applyLocal(op) {
  if (!shop) return;
  const key = (op.ingredient || '').trim().toLowerCase();
  let it = shop.items.find(i => i.ingredient.toLowerCase() === key);
  if (!it && op.type === 'add' && key) {   // article provisoire (hors ligne) ; la liste du serveur le remplacera
    it = { ingredient: key, aisle: 'Divers', status: 'todo', kind: 'piece', required: 0, in_stock: 0, missing: 1, packs: null,
           pack_label: null, buy_qty: 1, buy_text: '1', need_text: '1', price: 0, basic: false, verified: false };
    shop.items.push(it);
  }
  if (!it) return;
  if (op.type === 'buy' || op.type === 'have') it.status = 'done';
  else if (op.type === 'add' || op.type === 'low') it.status = 'todo';
  else if (op.type === 'archive') it.status = 'archived';
  else if (op.type === 'unarchive' || op.type === 'unbuy') it.status = 'todo';
  shop.count_todo = shop.items.filter(i => i.status === 'todo').length;
  lsSet(LS.shop, shop);
}
let flushChain = Promise.resolve(true);
// Un seul envoi à la fois : la file est relue au moment d'envoyer, jamais pendant qu'un envoi est en cours.
function flush() { flushChain = flushChain.then(doFlush, doFlush); return flushChain; }
async function doFlush() {
  const q = lsGet(LS.queue, []);
  if (!q.length) return true;
  try {
    const r = await post('/shopping/ops', { ops: q });
    const left = lsGet(LS.queue, []).filter(o => !q.some(s => s.op_id === o.op_id));
    lsSet(LS.queue, left); shop = r.list; lsSet(LS.shop, shop); return true;
  } catch (e) { if (e instanceof Offline) return false; throw e; }
}
async function shopOp(op) {
  op.op_id = uid();
  lsSet(LS.queue, [...lsGet(LS.queue, []), op]);
  applyLocal(op); drawShop();
  try {
    if (await flush()) { if (op.type === 'add') state.names = []; drawShop(); } else toast('Hors ligne : enregistré, synchronisé au retour du réseau.');
  } catch (e) { if (e.message !== 'Non connecté') toast('Synchronisation impossible : ' + e.message); }
}
let shopRoot = null;
async function viewCourses() {
  shopRoot = h('div', {});
  await flush().catch(() => {});
  try { shop = await api('/shopping'); lsSet(LS.shop, shop); } catch (e) { if (!(e instanceof Offline) || !shop) throw e; }
  drawShop();
  return shopRoot;
}
function qtyDialog(it) {
  dialog((dlg, close) => {
    const unit = it.kind === 'g' ? 'g' : it.kind === 'ml' ? 'ml' : 'pièce(s)';
    const q = h('input', { type: 'number', min: 0, step: 'any', value: it.buy_qty, inputmode: 'decimal' });
    dlg.append(h('h3', {}, it.ingredient), h('p', { class: 'muted' }, `Besoin : ${it.need_text}. Le surplus reste en stock pour les prochains repas.`),
      h('label', {}, `Quantité achetée (${unit})`), q, h('menu', {}, closeBtn(close), h('button', { class: 'primary', onclick: () => { close(); shopOp({ type: 'buy', ingredient: it.ingredient, qty: +q.value || 0 }); } }, 'Acheté')));
  });
}
function recipesDialog(it) {
  dialog((dlg, close) => dlg.append(h('h3', {}, it.ingredient), h('p', { class: 'muted' }, 'Utilisé dans :'),
    h('div', { class: 'stack' }, it.uses.map(u => h('a', { href: '#/recette/' + u.id, onclick: close }, `${u.title} · ${cap(fmtDate(u.day))}`))),
    h('menu', {}, closeBtn(close, 'Fermer'))));
}
function usesLine(it) {
  const u = it.uses || [];
  if (!u.length) return null;
  const links = u.slice(0, 2).map(x => h('a', { href: '#/recette/' + x.id }, x.title));
  const parts = [];
  links.forEach((l, i) => { if (i) parts.push(', '); parts.push(l); });
  return h('div', { class: 'small muted uses' }, 'Pour : ', parts,
    u.length > 2 ? [' ', h('button', { class: 'link', onclick: () => recipesDialog(it) }, `+${u.length - 2}`)] : null);
}
function itemRow(it) {
  const todo = it.status === 'todo';
  const detail = todo ? [it.packs ? `${it.packs} × ${it.pack_label}` : it.buy_text, it.buy_text && it.packs ? `(${it.buy_text})` : null, it.in_stock > 0 ? `déjà ${it.in_stock >= 1000 && it.kind !== 'piece' ? (it.in_stock / 1000).toLocaleString('fr-FR') + (it.kind === 'g' ? ' kg' : ' L') : Math.round(it.in_stock) + (it.kind === 'piece' ? '' : ' ' + it.kind)} en stock` : null].filter(Boolean).join(' ') : '';
  return h('div', { class: 'item' + (it.status === 'done' ? ' done' : '') },
    it.status === 'archived' ? h('button', { class: 'link', onclick: () => shopOp({ type: 'unarchive', ingredient: it.ingredient }) }, 'Remettre') :
      h('button', { class: 'check primary', 'aria-label': (todo ? 'Acheté : ' : 'Annuler : ') + it.ingredient, onclick: () => todo ? shopOp({ type: 'buy', ingredient: it.ingredient, qty: it.buy_qty }) : shopOp({ type: 'unbuy', ingredient: it.ingredient, qty: it.buy_qty || it.required }) }, todo ? '✓' : '↺'),
    h('div', { class: 'grow' }, h('div', { class: 'name' }, it.ingredient, it.verified ? null : h('span', { class: 'badge', style: 'margin-left:.4rem' }, 'à vérifier')), h('div', { class: 'small muted' }, detail || it.need_text), usesLine(it)),
    todo ? h('button', { 'aria-label': 'Autres actions pour ' + it.ingredient, onclick: () => dialog((dlg, close) => dlg.append(h('h3', {}, it.ingredient), h('div', { class: 'stack' },
      h('button', { onclick: () => { close(); qtyDialog(it); } }, 'Acheté en autre quantité'),
      h('button', { onclick: () => { close(); shopOp({ type: 'have', ingredient: it.ingredient }); } }, 'Déjà à la maison'),
      h('button', { onclick: () => { close(); shopOp({ type: 'archive', ingredient: it.ingredient }); } }, 'Retirer de la liste')), h('menu', {}, closeBtn(close, 'Fermer')))) }, '⋯') : null);
}
function drawShop() {
  if (!shopRoot || !shop) return;
  const q = lsGet(LS.queue, []);
  const by = (st) => shop.items.filter(i => i.status === st);
  const groups = {};
  by('todo').forEach(i => (groups[i.aisle] ||= []).push(i));
  const add = h('input', { list: 'ingnames', placeholder: 'Ajouter un article (ex. sel, café…)', 'aria-label': 'Ajouter un article' });
  ingredientNames().then(ns => { if (!document.getElementById('ingnames')) shopRoot.append(h('datalist', { id: 'ingnames' }, ns.map(n => h('option', { value: n })))); });
  const nodes = [h('div', { class: 'between' }, h('h1', {}, 'Courses'), h('span', { class: 'muted' }, `${shop.count_todo} à acheter · ≈ ${euro(shop.total_est)}`)),
    shop.locked_only && shop.locked_meals === 0 ? h('p', { class: 'muted' }, 'Verrouillez des repas dans Menus (🔓) pour ajouter leurs ingrédients ici.') : null,
    !navigator.onLine || q.length ? h('div', { class: 'offline' }, q.length ? `${q.length} action(s) en attente de synchronisation` : 'Hors ligne : liste mémorisée') : null,
    h('form', { class: 'row', onsubmit: ev => { ev.preventDefault(); const v = add.value.trim(); if (!v) return; shopOp({ type: 'add', ingredient: v }); add.value = ''; } }, add, h('button', { type: 'submit' }, 'Ajouter')),
    shop.count_todo === 0 ? h('p', { class: 'muted' }, 'Rien à acheter pour les repas prévus.') : null];
  Object.entries(groups).forEach(([a, items]) => nodes.push(h('h3', { class: 'aisle' }, a), items.map(itemRow)));
  if (by('done').length) nodes.push(h('h3', { class: 'aisle' }, 'Dans le panier'), by('done').map(itemRow));
  if (by('archived').length) nodes.push(h('h3', { class: 'aisle' }, 'Retirés de la liste'), by('archived').map(itemRow));
  put(shopRoot, nodes);
}
window.addEventListener('online', () => { flush().then(() => { drawShop(); }); });
window.addEventListener('offline', drawShop);

// ---------- réglages ----------
async function viewSettings() {
  const [s, refused, ings, stock] = await Promise.all([api('/settings'), api('/refused'), api('/ingredients'), api('/stock')]);
  const save = guard(async patch => { await api('/settings', { method: 'PUT', body: patch }); toast('Enregistré'); });
  const meals = JSON.parse(JSON.stringify(s.meals)), busy = JSON.parse(JSON.stringify(s.busy_slots));
  const f = {
    adults: h('input', { type: 'number', min: 1, value: s.adults }), kids: h('input', { value: s.children_coeffs.join(', ') }),
    days: h('input', { type: 'number', min: 1, max: 21, value: s.plan_days }), budget: h('input', { type: 'number', min: 0, step: 5, value: s.weekly_budget ?? '', placeholder: 'Aucun' }),
    rep: h('input', { type: 'number', min: 0, value: s.no_repeat_days }),
    lockedOnly: h('input', { type: 'checkbox', checked: s.shopping_locked_only }),
  };
  const matrix = h('div', { class: 'matrix' }, h('span'), h('strong', {}, 'Déjeuner'), h('strong', {}, 'Dîner'),
    DAYS.map((n, i) => [h('span', {}, n), h('input', { type: 'checkbox', checked: meals[i].lunch, 'aria-label': n + ' déjeuner', onchange: e => { meals[i].lunch = e.target.checked; } }), h('input', { type: 'checkbox', checked: meals[i].dinner, 'aria-label': n + ' dîner', onchange: e => { meals[i].dinner = e.target.checked; } })]));
  const busyBox = h('div', { class: 'matrix' }, h('span'), h('strong', {}, 'Midi'), h('strong', {}, 'Soir'), DAYS.map((n, i) => [h('span', {}, n),
    h('input', { type: 'checkbox', checked: !!busy[i]?.lunch, 'aria-label': n + ' midi chargé', onchange: e => { (busy[i] ||= {}).lunch = e.target.checked; } }),
    h('input', { type: 'checkbox', checked: !!busy[i]?.dinner, 'aria-label': n + ' soir chargé', onchange: e => { (busy[i] ||= {}).dinner = e.target.checked; } })]));const refList = h('div', {});
  const fish = new Set(s.fish_days);
  const fishBox = h('div', { class: 'row', style: 'flex-wrap:wrap' }, DAYS.map((n, i) => h('label', { class: 'inline' },
    h('input', { type: 'checkbox', checked: fish.has(i), 'aria-label': n + ' : poisson', onchange: e => e.target.checked ? fish.add(i) : fish.delete(i) }), n.slice(0, 3))));
  const drawRef = list => refList.replaceChildren(...(list.length ? list.map(n => h('span', { class: 'tag', style: 'margin:.2rem' }, n, ' ', h('button', { class: 'link', 'aria-label': 'Retirer ' + n, onclick: guard(async () => { await api('/refused/' + encodeURIComponent(n), { method: 'DELETE' }); drawRef(list.filter(x => x !== n)); }) }, '×'))) : [h('span', { class: 'muted small' }, 'Aucun pour le moment')]));
  drawRef(refused);
  const newRef = h('input', { placeholder: 'Ajouter un ingrédient refusé' });
  const unverified = ings.filter(i => !i.verified);
  const stockList = h('div', {}, stock.length ? stock.map(x => h('div', { class: 'item' }, h('div', { class: 'grow' }, h('div', { class: 'name' }, x.ingredient), h('div', { class: 'small muted' }, `${Math.round(x.qty)} ${x.kind === 'piece' ? '' : x.kind}`)),
    h('button', { onclick: guard(async () => { await api('/stock/' + encodeURIComponent(x.ingredient), { method: 'PUT', body: { qty: 0 } }); toast('Retiré du stock'); refresh(); }) }, 'Vide'))) : h('p', { class: 'muted small' }, 'Le stock se remplit avec vos achats (surplus) et se vide avec les repas.'));
  const recurrent = ings.filter(i => i.is_recurrent);
  return [h('h1', {}, 'Réglages'),
    h('h2', {}, 'Famille'), h('div', { class: 'grid2' }, h('div', {}, h('label', {}, 'Adultes'), f.adults), h('div', {}, h('label', {}, 'Enfants (part d\'adulte)'), f.kids)),
    h('p', { class: 'small muted' }, 'Ex. 0.5, 0.6, 0.7 pour des enfants de 3, 4 et 7 ans : 0,5 = la moitié d\'une portion d\'adulte.'),
    h('h2', { style: 'margin-top:1.2rem' }, 'Planning'), h('div', { class: 'grid2' }, h('div', {}, h('label', {}, 'Jours affichés'), f.days), h('div', {}, h('label', {}, 'Budget par semaine (€)'), f.budget)),
    h('label', {}, 'Ne pas répéter une recette avant (jours)'), f.rep, h('label', { class: 'inline' }, f.lockedOnly, 'Courses : seulement les repas verrouillés'), h('label', {}, 'Repas à planifier'), matrix, h('label', {}, 'Repas chargés (recettes rapides)'), busyBox, h('label', {}, 'Jours poisson (recettes au poisson par défaut)'), fishBox,
    h('p', {}, h('button', { class: 'primary', onclick: () => { const kids = f.kids.value.split(/[,;\s]+/).map(x => parseFloat(x.replace(',', '.'))).filter(x => x > 0); save({ adults: +f.adults.value || 1, children_coeffs: kids, plan_days: +f.days.value || 7,
       weekly_budget: f.budget.value === '' ? null : +f.budget.value, no_repeat_days: +f.rep.value || 0,
       shopping_locked_only: f.lockedOnly.checked, meals, busy_slots: busy, fish_days: [...fish] }); } }, 'Enregistrer')),
    h('h2', { style: 'margin-top:1.2rem' }, 'Ingrédients refusés'), refList,
    h('form', { class: 'row', onsubmit: guard(async ev => { ev.preventDefault(); if (!newRef.value.trim()) return; const r = await post('/refused', { name: newRef.value }); newRef.value = ''; drawRef([...new Set([...(await api('/refused'))])]); }) }, newRef, h('button', { type: 'submit' }, 'Ajouter')),
    h('h2', { style: 'margin-top:1.2rem' }, 'Stock à la maison'), stockList,
    h('p', { class: 'small muted' }, 'Pour les produits de base (sel, huile…), ajoutez-les à la liste de courses avec « Ajouter un article » quand il en reste peu.'),
    h('h2', { style: 'margin-top:1.2rem' }, 'Petit-déjeuner et produits récurrents'),
    h('p', { class: 'small muted' }, 'Consommation estimée par semaine ; le stock baisse chaque jour et l\'article revient dans la liste quand il manque.'),
    recurrent.map(i => recurrentRow(i)),
    unverified.length ? [h('h2', { style: 'margin-top:1.2rem' }, `Ingrédients à vérifier (${unverified.length})`), h('p', { class: 'small muted' }, 'Reconnus par défaut comme « divers ». Choisissez le rayon pour une liste de courses bien classée.'), unverified.map(i => verifyRow(i))] : null,
    h('h2', { style: 'margin-top:1.2rem' }, 'Données'), h('p', {}, h('a', { class: 'btn', href: '/api/backup', style: 'display:inline-block;text-decoration:none;padding:.7rem 1rem;border:1px solid var(--line);border-radius:8px' }, 'Télécharger une sauvegarde'), ' ', h('button', { onclick: guard(async () => { await post('/logout'); navigator.serviceWorker?.controller?.postMessage('clear'); localStorage.removeItem(LS.shop); localStorage.removeItem(LS.queue); shop = null; showLogin(); }) }, 'Se déconnecter'))];
}
function recurrentRow(i) {
  const q = h('input', { type: 'number', min: 0, value: i.weekly_qty ?? '', 'aria-label': 'Quantité par semaine pour ' + i.name });
  return h('div', { class: 'line' }, h('strong', {}, i.name), q, h('button', { onclick: guard(async () => { await api('/ingredients/' + encodeURIComponent(i.name), { method: 'PUT', body: { weekly_qty: +q.value || 0 } }); toast(`${i.name} : ${q.value} ${i.kind === 'piece' ? '' : i.kind} par semaine`); }) }, 'OK'));
}
function verifyRow(i) {
  const aisles = ['Fruits et légumes', 'Boucherie', 'Poissonnerie', 'Crèmerie', 'Boulangerie', 'Épicerie', 'Conserves', 'Surgelés', 'Boissons', 'Hygiène et maison', 'Divers'];
  const sel = h('select', { 'aria-label': 'Rayon de ' + i.name }, aisles.map(a => h('option', { value: a, selected: a === i.aisle }, a)));
  const basic = h('input', { type: 'checkbox', 'aria-label': i.name + ' : produit de base' });
  return h('div', { class: 'line' }, h('strong', {}, i.name), sel, h('span', { class: 'row' }, h('label', { class: 'inline', style: 'margin:0' }, basic, 'base'), h('button', { onclick: guard(async () => { await api('/ingredients/' + encodeURIComponent(i.name), { method: 'PUT', body: { aisle: sel.value, is_basic: +basic.checked, verified: 1 } }); toast('Enregistré'); refresh(); }) }, 'OK')));
}

// ---------- démarrage ----------
async function start() {
  try { await api('/me'); } catch (e) { if (!(e instanceof Offline)) return; }  // hors ligne : on tente d'afficher le cache
  $('#tabs').hidden = false;
  if (!location.hash) location.hash = '#/menus'; else route();
}
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
start();
