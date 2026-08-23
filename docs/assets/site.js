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
  var links = Array.prototype.slice.call(document.querySelectorAll('.toc a[href^="#"]'));
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
