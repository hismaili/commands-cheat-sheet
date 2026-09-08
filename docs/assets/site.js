/* Theme, copy buttons, table-of-contents tracking, and the issue composer.
   No dependencies — GitHub Pages serves this file as-is. */
(function () {
  'use strict';

  /* --- theme: remembered per browser, defaults to the OS setting --------- */
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem('ccs-theme');
    if (saved === 'light' || saved === 'dark') root.setAttribute('data-theme', saved);
  } catch (e) { /* private mode — the OS setting still applies */ }

  function currentTheme() {
    /* The site commits to the dark look: light is opt-in, not OS-driven. */
    return root.getAttribute('data-theme') || 'dark';
  }

  var toggle = document.querySelector('[data-theme-toggle]');
  function paintToggle() {
    if (!toggle) return;
    var next = currentTheme() === 'dark' ? 'light' : 'dark';
    toggle.textContent = next === 'dark' ? 'CARBON' : 'PAPER';
    toggle.setAttribute('aria-label', 'Switch to the ' + next + ' theme');
  }
  paintToggle();
  if (toggle) {
    toggle.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('ccs-theme', next); } catch (e) {}
      paintToggle();
    });
  }

  /* --- top-bar dropdowns: Cheat Sheets / Tutorials ------------------------ */
  document.querySelectorAll('[data-navdrop]').forEach(function (drop) {
    var btn = drop.querySelector('.navdrop__btn');
    var panel = drop.querySelector('.navdrop__panel');
    if (!btn || !panel) return;
    btn.addEventListener('click', function (e) {
      var open = drop.getAttribute('data-open') === '1';
      document.querySelectorAll('[data-navdrop][data-open="1"]').forEach(function (d) {
        if (d !== drop) { d.removeAttribute('data-open'); d.querySelector('.navdrop__panel').hidden = true; d.querySelector('.navdrop__btn').setAttribute('aria-expanded','false'); }
      });
      if (open) { drop.removeAttribute('data-open'); panel.hidden = true; btn.setAttribute('aria-expanded','false'); }
      else { drop.setAttribute('data-open','1'); panel.hidden = false; btn.setAttribute('aria-expanded','true'); }
      e.stopPropagation();
    });
  });
  document.addEventListener('click', function () {
    document.querySelectorAll('[data-navdrop][data-open="1"]').forEach(function (d) {
      d.removeAttribute('data-open'); d.querySelector('.navdrop__panel').hidden = true; d.querySelector('.navdrop__btn').setAttribute('aria-expanded','false');
    });
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') {
      document.querySelectorAll('[data-navdrop][data-open="1"]').forEach(function (d) {
        d.removeAttribute('data-open'); d.querySelector('.navdrop__panel').hidden = true; d.querySelector('.navdrop__btn').setAttribute('aria-expanded','false');
      });
    }
  });

  /* --- copy a command block --------------------------------------------- */
  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('.copy');
    if (!btn) return;
    var pre = btn.closest('.cmd').querySelector('pre');
    if (!pre) return;
    var text = pre.innerText;
    var done = function () {
      btn.textContent = 'COPIED';
      btn.setAttribute('data-done', '1');
      setTimeout(function () { btn.textContent = 'COPY'; btn.removeAttribute('data-done'); }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { btn.textContent = 'SELECT + COPY'; });
    } else {
      var r = document.createRange(); r.selectNodeContents(pre);
      var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
      btn.textContent = 'SELECTED';
    }
  });

  /* --- highlight the section you are reading ---------------------------- */
  var links = Array.prototype.slice.call(document.querySelectorAll('.rail__toc a[href^="#"]'));
  if (links.length && 'IntersectionObserver' in window) {
    var byId = {};
    links.forEach(function (a) { byId[a.getAttribute('href').slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        links.forEach(function (a) { a.classList.remove('on'); });
        var a = byId[en.target.id];
        if (a) a.classList.add('on');
      });
    }, { rootMargin: '-72px 0px -70% 0px' });
    Object.keys(byId).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) io.observe(el);
    });
  }

  /* --- ask a question: compose a prefilled GitHub issue ------------------ */
  var form = document.querySelector('[data-issue-form]');
  if (form) {
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var repo = form.getAttribute('data-repo');
      var topic = form.querySelector('[name="topic"]').value;
      var title = form.querySelector('[name="title"]').value.trim();
      var body = form.querySelector('[name="body"]').value.trim();
      if (!title) { form.querySelector('[name="title"]').focus(); return; }

      var composed =
        '### What I am trying to do\n\n' + (body || '_Describe the command or situation._') +
        '\n\n### Topic\n\n' + topic +
        '\n\n---\nAsked from the cheat-sheet site.\n';

      var url = 'https://github.com/' + repo + '/issues/new' +
        '?labels=' + encodeURIComponent('question') +
        '&title=' + encodeURIComponent((topic === 'Not listed yet' ? '' : '[' + topic + '] ') + title) +
        '&body=' + encodeURIComponent(composed);
      window.open(url, '_blank', 'noopener');
    });
  }
})();

/* ==========================================================================
   Drawer, search and the command palette.

   The index is one JSON file built from the sheets themselves. It is fetched
   once, on the first keystroke or the first time the palette opens, so a
   reader who never searches never pays for it.
   ========================================================================== */
(function () {
  'use strict';

  var rail = document.getElementById('rail');
  if (!rail) return;
  var UP = rail.getAttribute('data-up') || '';
  var SRC = rail.getAttribute('data-index');

  /* ---------------------------------------------------------- drawer ---- */
  var burger = document.querySelector('[data-drawer]');
  var scrim = document.createElement('div');
  scrim.className = 'drawer-scrim';
  document.body.appendChild(scrim);

  function drawer(open) {
    rail.setAttribute('data-open', open ? '1' : '0');
    scrim.setAttribute('data-open', open ? '1' : '0');
    if (burger) burger.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  if (burger) burger.addEventListener('click', function () {
    drawer(rail.getAttribute('data-open') !== '1');
  });
  scrim.addEventListener('click', function () { drawer(false); });
  rail.addEventListener('click', function (e) {
    if (e.target.closest('a')) drawer(false);
  });

  /* ----------------------------------------------------------- index ---- */
  var DATA = null, loading = null;
  function load() {
    if (DATA) return Promise.resolve(DATA);
    if (loading) return loading;
    loading = fetch(SRC)
      .then(function (r) { return r.json(); })
      .then(function (j) {
        DATA = j.e || [];
        var c = 0, sy = 0;
        DATA.forEach(function (e) { if (e.k === 'cmd') c++; else if (e.k === 'symptom') sy++; });
        document.querySelectorAll('.palette .sf__input').forEach(function (i) {
          i.placeholder = 'Search ' + c + ' commands, ' + sy + ' symptoms';
        });
        return DATA;
      })
      .catch(function () { DATA = []; return DATA; });
    return loading;
  }

  var KIND = { symptom: 6, cmd: 4, section: 2 };
  var LABEL = { symptom: 'symptom', cmd: 'command', section: 'section' };

  function score(e, q, toks) {
    var x = e.x.toLowerCase(), d = (e.d || '').toLowerCase(), n = e.n.toLowerCase();
    var hay = x + ' ' + d + ' ' + n;
    for (var i = 0; i < toks.length; i++) if (hay.indexOf(toks[i]) === -1) return -1;

    var at = x.indexOf(q), s;
    if (at === 0) s = 100;
    else if (at > 0) s = /[\s\-\/.,:]/.test(x.charAt(at - 1)) ? 72 : 46;
    else {
      var j = d.indexOf(q);
      if (j === 0) s = 40;
      else if (j > 0) s = 26;
      else if (n.indexOf(q) === 0) s = 22;
      else s = 12;                       /* matched only as scattered tokens */
    }
    return s + (KIND[e.k] || 0) - Math.min(e.x.length / 40, 4);
  }

  function search(q) {
    q = q.trim().toLowerCase();
    if (!q || !DATA) return [];
    var toks = q.split(/\s+/), out = [];
    for (var i = 0; i < DATA.length; i++) {
      var sc = score(DATA[i], q, toks);
      if (sc > 0) out.push([sc, i, DATA[i]]);
    }
    out.sort(function (a, b) { return b[0] - a[0] || a[1] - b[1]; });
    return out.slice(0, 40).map(function (r) { return r[2]; });
  }

  function esc(t) {
    return String(t).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function mark(text, q) {
    var i = text.toLowerCase().indexOf(q.toLowerCase());
    if (i === -1 || !q) return esc(text);
    return esc(text.slice(0, i)) + '<mark>' + esc(text.slice(i, i + q.length)) +
           '</mark>' + esc(text.slice(i + q.length));
  }

  /* ------------------------------------------------------- one field ---- */
  function wire(form) {
    var input = form.querySelector('.sf__input');
    var box = form.querySelector('.sf__results');
    var typed = form.querySelector('.sf__typed');
    var rest = form.querySelector('.sf__rest');
    var hits = [], cur = -1;

    function ghost(q) {
      if (!typed) return;
      var comp = '';
      for (var i = 0; i < hits.length && !comp; i++) {
        if (hits[i].x.toLowerCase().indexOf(q.toLowerCase()) === 0 && hits[i].x.length > q.length) {
          comp = hits[i].x.slice(q.length);
        }
      }
      typed.textContent = comp ? q : '';
      rest.textContent = comp;
    }

    function paint(q) {
      if (!q.trim()) { box.hidden = true; box.innerHTML = ''; ghost(''); input.setAttribute('aria-expanded', 'false'); return; }
      if (!hits.length) {
        box.innerHTML = '<p class="sf__empty">Nothing matches &ldquo;' + esc(q) +
          '&rdquo;. <a href="https://github.com/hismaili/commands-cheat-sheet/issues/new?labels=question">Ask for it</a>.</p>';
        box.hidden = false; ghost(''); return;
      }
      box.innerHTML = hits.map(function (e, i) {
        return '<a class="sf__hit t-' + e.t + '" role="option" href="' + UP + e.u + '"' +
          (i === cur ? ' aria-selected="true"' : '') + '>' +
          '<span class="sf__meta"><i class="dot"></i>' + esc(e.n) + ' &middot; ' + LABEL[e.k] + '</span>' +
          '<p class="sf__x">' + mark(e.x, q) + '</p>' +
          (e.d ? '<p class="sf__d">' + mark(e.d, q) + '</p>' : '') + '</a>';
      }).join('');
      box.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      ghost(q);
    }

    function run() {
      var q = input.value;
      load().then(function () { hits = search(q); cur = q.trim() ? 0 : -1; paint(q); });
    }

    function move(step) {
      if (!hits.length) return;
      cur = (cur + step + hits.length) % hits.length;
      paint(input.value);
      var sel = box.querySelector('[aria-selected="true"]');
      if (sel) sel.scrollIntoView({ block: 'nearest' });
    }

    input.addEventListener('focus', load);
    input.addEventListener('input', run);
    input.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowDown') { ev.preventDefault(); move(1); }
      else if (ev.key === 'ArrowUp') { ev.preventDefault(); move(-1); }
      else if (ev.key === 'Enter') {
        if (hits[cur]) { ev.preventDefault(); window.location.href = UP + hits[cur].u; }
      } else if (ev.key === 'Tab' || (ev.key === 'ArrowRight' && input.selectionStart === input.value.length)) {
        if (rest && rest.textContent) { ev.preventDefault(); input.value += rest.textContent; run(); }
      } else if (ev.key === 'Escape') {
        if (input.value) { input.value = ''; run(); }
        else closePalette();
      }
    });
    form.addEventListener('click', function (e) { if (e.target.closest('.sf__hit')) drawer(false); });
    return { input: input, run: run };
  }

  var fields = Array.prototype.map.call(document.querySelectorAll('[data-search]'), wire);

  /* ---------------------------------------------------------- palette --- */
  var pal = document.querySelector('[data-palette]');
  var palField = fields[fields.length - 1];
  var lastFocus = null;

  function openPalette() {
    if (!pal) return;
    lastFocus = document.activeElement;
    pal.hidden = false;
    load();
    palField.input.focus();
    palField.input.select();
  }
  function closePalette() {
    if (!pal || pal.hidden) return;
    pal.hidden = true;
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  document.querySelectorAll('[data-palette-open]').forEach(function (b) {
    b.addEventListener('click', openPalette);
  });
  document.querySelectorAll('[data-palette-close]').forEach(function (b) {
    b.addEventListener('click', closePalette);
  });

  document.addEventListener('keydown', function (ev) {
    var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    if ((ev.metaKey || ev.ctrlKey) && ev.key.toLowerCase() === 'k') { ev.preventDefault(); openPalette(); }
    else if (ev.key === '/' && !typing) { ev.preventDefault(); openPalette(); }
    else if (ev.key === 'Escape') { closePalette(); drawer(false); }
  });
})();
