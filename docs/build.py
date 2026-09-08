#!/usr/bin/env python3
"""Generate the GitHub Pages site from the cheat sheets themselves.

Run from the repo root:  python3 docs/build.py

Every page here is derived from a topic's own <topic>/<topic>.md — the site
cannot drift from the sheets, and adding a sheet adds a page. Output goes to
docs/ so GitHub Pages can serve it from the main branch (Settings → Pages →
Deploy from a branch → main → /docs).
"""
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs")
REPO = "hismaili/commands-cheat-sheet"
BASE = "https://hismaili.github.io/commands-cheat-sheet/"
GH = "https://github.com/" + REPO

# ---------------------------------------------------------------------------
# Topic metadata. The prose lives in the sheets; this is only what a search
# engine and a first-time reader need before they open one.
# ---------------------------------------------------------------------------
TOPICS = [
    dict(slug="openshift", name="OpenShift", file="openshift/openshift.md",
         title="OpenShift & ArgoCD Commands — Stuck Syncs, Finalizers, RBAC, Loki",
         desc="Field-tested oc commands for OpenShift: unstick an ArgoCD sync, strip finalizers off a namespace stuck Terminating, debug RBAC with can-i --as, verify Loki and ODF certificate chains.",
         blurb="Unstick ArgoCD syncs, kill namespaces that will not terminate, and prove an RBAC or TLS failure instead of guessing at it.",
         kw="openshift commands, oc cheat sheet, argocd stuck sync, namespace terminating finalizers, oc auth can-i, lokistack, odf noobaa",
         related=["vault", "podman", "linux"]),
    dict(slug="linux", name="Linux", file="linux/linux.md",
         title="Linux Commands — PATH, systemd User Units, Ports, yum",
         desc="Field-tested Linux commands: make PATH exports survive a new shell, tell system units from --user units in systemd, find and kill whatever holds a port, script yum without prompts.",
         blurb="PATH that survives a new shell, systemd user units that actually start, and the process quietly sitting on your port.",
         kw="linux commands cheat sheet, bash_profile path, systemctl --user, journalctl follow, lsof port, fuser kill port, yum install -y",
         related=["podman", "oci", "ruby"]),
    dict(slug="podman", name="Podman", file="podman/podman.md",
         title="Podman Commands — Build, Run, Compose, and What Deletes What",
         desc="Field-tested Podman commands for build, run, compose and inspection — with the destructive ones labelled: what podman rm -a, stop -a, compose down and --force-recreate actually take with them.",
         blurb="Build, run and compose, with every state-destroying command labelled with what it removes.",
         kw="podman commands, podman compose down, podman build --format docker, podman rm -a, podman run detached, podman ps filter",
         related=["linux", "openshift", "web"]),
    dict(slug="vault", name="Vault", file="vault/vault.md",
         title="HashiCorp Vault Commands — KV v2, Policies, userpass, AppRole",
         desc="Field-tested Vault commands in the order they have to run: mount a KV v2 engine, write a policy, enable userpass for humans, and set up AppRole RoleID/SecretID for services.",
         blurb="Four things wired in order: where secrets live, who may read them, how a human logs in, how a service does.",
         kw="vault commands cheat sheet, vault kv-v2 enable, vault policy write, vault approle role-id secret-id, vault auth enable userpass",
         related=["openshift", "api-testing", "linux"]),
    dict(slug="oci", name="Oracle Cloud (OCI)", file="oci/oci.md",
         title="OCI CLI Commands — Install, setup config, and SSH to an Instance",
         desc="Field-tested Oracle Cloud Infrastructure commands: install and verify the OCI CLI, run setup config, and fix the key permissions that make SSH to a compute instance fail.",
         blurb="Get the CLI on the box, get ~/.oci/config written, and get SSH to stop rejecting a perfectly good key.",
         kw="oci cli commands, oci setup config, brew install oci-cli, oci ssh opc user, chmod go-rwx ssh key",
         related=["linux", "openshift", "podman"]),
    dict(slug="web", name="Web / React Native", file="web/web.md",
         title="npm & React Native Commands — Metro, run ios/android/web, build",
         desc="Field-tested npm scripts for a React Native / Expo project: start the Metro dev server, run on iOS, Android or the browser, and produce a deployable static web build.",
         blurb="Start Metro first — every other script in the project assumes it is already up in another terminal.",
         kw="react native npm commands, npm start metro, npm run ios android web, npm run build:web, expo dev server",
         related=["mobile", "api-testing", "podman"]),
    dict(slug="mobile", name="Mobile", file="mobile/mobile.md",
         title="Flutter & Expo Build Commands — Native vs Remote Build Service",
         desc="Field-tested mobile build commands, and which build system you are actually invoking: the native Flutter toolchain versus the classic Expo remote build service.",
         blurb="Which build system are you actually invoking — the native toolchain, or Expo's remote one? The docs you need differ.",
         kw="flutter build android, expo build:android, expo build:ios, mobile build commands, npx expo classic build",
         related=["web", "ruby", "api-testing"]),
    dict(slug="ruby", name="Ruby", file="ruby/ruby.md",
         title="Ruby & Gem Commands on macOS — GEM_HOME, PATH, CocoaPods",
         desc="Field-tested Ruby commands for macOS: install a pinned gem around Apple's system Ruby, then set GEM_HOME and the derived paths so gem, ruby and pod are actually found.",
         blurb="Apple's system Ruby will not let you write to it, and gem-installed binaries land outside PATH.",
         kw="gem install user-install macos, GEM_HOME PATH, cocoapods pod command not found, ruby macos system gem",
         related=["mobile", "linux", "web"]),
    dict(slug="api-testing", name="API Testing", file="api-testing/api-testing.md",
         title="curl Commands for API Testing — CORS Preflight and OAuth2 Tokens",
         desc="Field-tested curl commands for API testing: send the OPTIONS preflight a browser would send to read the real Access-Control-Allow headers, and trade credentials for a token via the password grant.",
         blurb="A browser's CORS error tells you nothing. Send the preflight yourself and read what the server actually allows.",
         kw="curl cors preflight options, access-control-allow-origin test, oauth2 password grant curl, curl bearer token api testing",
         related=["vault", "web", "openshift"]),
    dict(slug="git", name="Git", file="git/git.md",
         title="Git Commands \u2014 Two Remotes, SSH Identity, GitHub SAML SSO",
         desc="Git commands for a laptop with several accounts: push one folder to two repositories, stop commit identity and SSH keys from cross-contaminating, and get past a GitHub SAML SSO denial that a correct SSH key alone will not fix.",
         blurb="Three layers get confused with each other: who authored the commit, which key authenticates, and whether the organization authorizes you at all.",
         kw="git multiple remotes, git remote set-url --add --push, ssh host alias multiple github accounts, IdentitiesOnly yes, git includeIf gitdir, github saml sso ssh key authorization",
         related=["linux", "openshift", "oci"]),
]
# Tutorials — step-by-step guides that complement the cheat sheets.
# Each entry is a standalone HTML file at <topic>/tutorials/<slug>.html
# rendered inside the site chrome with scoped dark vars (preserves original #0d1117).
TUTORIALS = [
    dict(slug="rewrite-pushed-commits", topic="git", name="Rewrite Pushed Commit Messages",
         file="git/tutorials/rewrite-pushed-commits.html",
         title="Git: Rewrite Pushed Commit Messages — Amend, Rebase, Force-With-Lease (Dual-Remote)",
         desc="Step-by-step to reword commits already pushed and replace one remote with git push --force-with-lease, with backup, verification and collaborator reset.",
         kw="git commit amend pushed, git rebase reword, git push force with lease one remote, git reset hard origin",
         date="2026-09-04"),
]

# Directories that exist but hold no recorded sessions yet.
PLANNED = [
    dict(slug="kafka", name="Kafka", why="No session has been recorded yet."),
]

# Each sheet owns a hue taken from its own tool's world — Red Hat red, Oracle
# orange, Tux yellow, Android green, Podman violet — so the colour tells you
# where you are. The second value is the same hue darkened for the paper theme,
# where the bright version would be unreadable on near-white.
HUES = {
    "openshift":   ("#F0665A", "#C0392B"),
    "oci":         ("#F0913C", "#B45309"),
    "linux":       ("#DFBF45", "#8A6D0B"),
    "mobile":      ("#7FC44E", "#3F7A22"),
    "vault":       ("#35C09B", "#0F7A62"),
    "api-testing": ("#45C4DA", "#0E6E80"),
    "web":         ("#5B9BF2", "#1D5FB8"),
    "podman":      ("#9C82F0", "#5B3FC4"),
    "ruby":        ("#EA6BAA", "#A81E63"),
    "git":         ("#F05033", "#B23A1F"),
    "kafka":       ("#8194A9", "#5B6675"),
}
SITE_HUE = ("#5B9BF2", "#1D5FB8")


def hue_style(slug=None):
    """A <style> block binding --topic. One hue for a topic page; the whole
    set, class-scoped, for pages that show every sheet at once."""
    base = HUES.get(slug, SITE_HUE) if slug else SITE_HUE
    rules = [':root{--topic:%s}' % base[0],
             ':root[data-theme="light"]{--topic:%s}' % base[1]]
    # The class rules go on every page, not just the ones showing all nine
    # sheets: the rail lists them everywhere and each dot needs its own hue.
    for k, (d, l) in HUES.items():
        rules.append('.t-%s{--topic:%s}' % (k, d))
        rules.append(':root[data-theme="light"] .t-%s{--topic:%s}' % (k, l))
    return "<style>" + "".join(rules) + "</style>\n"


BY_SLUG = {t["slug"]: t for t in TOPICS}
TUTS_BY_TOPIC = {}
for _tut in TUTORIALS:
    TUTS_BY_TOPIC.setdefault(_tut["topic"], []).append(_tut)


# ---------------------------------------------------------------------------
# A small Markdown reader. The sheets use a deliberately narrow subset, so a
# purpose-built reader beats a dependency here — and it lets command blocks
# and hazard notes become real components rather than generic <pre> and <p>.
# ---------------------------------------------------------------------------
def slugify(text):
    s = re.sub(r"`|\*|<|>|\(|\)|\[|\]|\.", "", text.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-{2,}", "-", s) or "section"


def inline(text):
    """Inline markdown → HTML, escaping first so source stays literal."""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", lambda m: "<code>" + m.group(1) + "</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\*\w])\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    return out


def code_html(body):
    """Shell block → HTML with comment lines dimmed."""
    lines = []
    for raw in body.rstrip("\n").split("\n"):
        esc = html.escape(raw, quote=False)
        if raw.lstrip().startswith("#"):
            esc = '<span class="c">' + esc + "</span>"
        lines.append(esc)
    return "\n".join(lines)


def classify(text):
    """Which kind of note is this? The sheets mark two, and they mean
    different things: one costs you data, the other costs you certainty."""
    low = text.lower()
    if "destructive" in low or "last resort" in low:
        return "hazard", "Destructive"
    if "uncertain" in low:
        return "uncertain", "Uncertain — kept as recorded"
    return None, None


def parse(md):
    """→ (title, intro_blocks, [ {heading, id, blocks} ], key_patterns)"""
    lines = md.split("\n")
    title, i = "", 0
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        i = 1

    blocks, n = [], len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            lang = line[3:].strip() or "bash"
            i += 1
            buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            blocks.append(("code", lang, "\n".join(buf)))
            continue
        if re.match(r"^#{2,4} ", line):
            level = len(line) - len(line.lstrip("#"))
            blocks.append(("h", level, line[level:].strip()))
            i += 1
            continue
        if line.strip() in ("---", "***", "___"):
            blocks.append(("hr", 0, ""))
            i += 1
            continue
        if line.lstrip().startswith("|"):
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            blocks.append(("table", 0, rows))
            continue
        if line.lstrip().startswith(">"):
            buf = []
            while i < n and (lines[i].lstrip().startswith(">") or (lines[i].strip() and buf)):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
                if i < n and not lines[i].strip():
                    break
            blocks.append(("quote", 0, " ".join(x.strip() for x in buf).strip()))
            continue
        buf = []
        while i < n and lines[i].strip() and not lines[i].startswith("```") \
                and not re.match(r"^#{2,4} ", lines[i]) and not lines[i].lstrip().startswith("|") \
                and not lines[i].lstrip().startswith(">") and lines[i].strip() not in ("---", "***", "___"):
            buf.append(lines[i].strip())
            i += 1
        blocks.append(("p", 0, " ".join(buf)))

    # split into sections on h2
    intro, sections, cur = [], [], None
    for kind, meta, body in blocks:
        if kind == "h" and meta == 2:
            cur = dict(heading=body, id=slugify(body), blocks=[])
            sections.append(cur)
        elif cur is None:
            if kind != "hr":
                intro.append((kind, meta, body))
        else:
            cur["blocks"].append((kind, meta, body))

    # lift the Key Patterns table out — it becomes the FAQ, not a table
    patterns = []
    keep = []
    for sec in sections:
        if sec["heading"].strip().lower() == "key patterns":
            for kind, meta, body in sec["blocks"]:
                if kind == "table" and len(body) > 2:
                    for row in body[2:]:
                        cells = [c.strip() for c in row.strip("|").split("|")]
                        if len(cells) >= 2 and cells[0]:
                            patterns.append((cells[0], cells[1]))
        else:
            keep.append(sec)
    return title, intro, keep, patterns


def render(blocks, cmd_counter, idx=None, tslug="", tname=""):
    """Blocks to HTML. When idx is given, every command block and sub-heading
    is also appended to the search index as it is emitted, so the index cannot
    describe anything the page does not actually contain."""
    out = []
    for kind, meta, body in blocks:
        if kind == "p":
            level, label = classify(body)
            if level:
                out.append('<div class="callout callout--%s"><span class="callout__k">%s</span><p>%s</p></div>'
                           % (level, label, inline(body)))
            else:
                out.append("<p>%s</p>" % inline(body))
        elif kind == "quote":
            level, label = classify(body)
            out.append('<div class="callout callout--%s"><span class="callout__k">%s</span><p>%s</p></div>'
                       % (level or "uncertain", label or "Note", inline(body)))
        elif kind == "code":
            cmd_counter[0] += 1
            cid = "c-%d" % cmd_counter[0]
            out.append(
                '<div class="cmd" id="%s"><div class="cmd__top"><span class="cmd__lang">%s</span>'
                '<button class="copy" type="button">COPY</button></div><pre><code>%s</code></pre></div>'
                % (cid, html.escape(meta), code_html(body)))
            if idx is not None:
                note = ""
                for line in body.split("\n"):
                    ls = line.strip()
                    if not ls:
                        continue
                    if ls.startswith("#"):
                        note = ls.lstrip("#").strip()
                        continue
                    idx.append(dict(t=tslug, n=tname, k="cmd", x=ls, d=note,
                                    u="%s/#%s" % (tslug, cid)))
        elif kind == "h":
            hid = slugify(body)
            out.append('<h%d id="%s">%s</h%d>' % (meta, hid, inline(body), meta))
            if idx is not None and meta == 3:
                idx.append(dict(t=tslug, n=tname, k="section", x=body, d="",
                                u="%s/#%s" % (tslug, hid)))
        elif kind == "hr":
            out.append('<hr class="perf">')
        elif kind == "table":
            head = [c.strip() for c in body[0].strip("|").split("|")]
            rows = [[c.strip() for c in r.strip("|").split("|")] for r in body[2:]]
            t = ["<div class='tablewrap'><table><thead><tr>"]
            t += ["<th>%s</th>" % inline(c) for c in head]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Page chrome
# ---------------------------------------------------------------------------
def head(title, desc, path, kw="", extra_ld="", hue=""):
    up = get_up(path)
    canon = BASE + (path + "/" if path else "")
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
%(kw)s<link rel="canonical" href="%(canon)s">
<meta property="og:type" content="website">
<meta property="og:site_name" content="commands-cheat-sheet">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(desc)s">
<meta property="og:url" content="%(canon)s">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="%(title)s">
<meta name="twitter:description" content="%(desc)s">
<meta name="theme-color" content="#080D16">
<link rel="icon" href="data:image/svg+xml,%%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%%3E%%3Crect width='32' height='32' rx='6' fill='%%23080D16'/%%3E%%3Ctext x='16' y='23' font-family='monospace' font-size='19' font-weight='700' fill='%%235B9BF2' text-anchor='middle'%%3E%%24%%3C/text%%3E%%3C/svg%%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<link rel="stylesheet" href="%(up)sassets/site.css">
%(hue)s%(ld)s</head>
<body>
<a class="skip" href="#main">Skip to content</a>
""" % dict(title=html.escape(title), desc=html.escape(desc), canon=canon, up=up,
           kw=('<meta name="keywords" content="%s">\n' % html.escape(kw)) if kw else "",
           ld=extra_ld, hue=hue)


STATS = {}          # slug -> {"cmds": n, "patterns": n, ...}; filled by main()

def get_up(path):
    if not path:
        return ""
    if "/" not in path:
        return "../"
    return "../" * (path.count("/") + 1)

def rail(path, sections=None, slug=None):
    """The left rail: search, every sheet, and — on a content page — its own
    sections. One component on every page, so the topic list is never more than
    a glance away and every page carries the same nine internal links."""
    up = get_up(path)
    sheets = "".join(
        '<li><a class="t-%s%s" href="%s%s/"><i class="dot"></i><span>%s</span>'
        '<b>%s</b></a></li>'
        % (t["slug"], ' aria-current="page"' if t["slug"] == slug else "",
           up, t["slug"], html.escape(t["name"]),
           STATS.get(t["slug"], {}).get("cmds", ""))
        for t in TOPICS)
    sheets += "".join(
        '<li><a class="t-%s rail__soon" href="%s/issues/new?labels=request&amp;'
        'title=%%5B%s%%5D%%20" target="_blank" rel="noopener">'
        '<i class="dot"></i><span>%s</span><b>&mdash;</b></a></li>'
        % (pl["slug"], GH, pl["name"], html.escape(pl["name"])) for pl in PLANNED)

    onpage = ""
    if sections:
        onpage = ('<h4>On this page</h4><ul class="rail__toc">'
                  + "".join('<li><a href="#%s">%s</a></li>' % (sid, html.escape(nm))
                            for sid, nm in sections)
                  + "</ul>")

    # On the landing page these three are already listed under "On this page";
    # repeating them below would just be the same link twice.
    more = ""
    if path:
        more = ('<li><a href="%(up)ssymptoms/">Every symptom</a></li>'
                '<li><a href="%(up)s#pipeline">How a sheet is made</a></li>'
                '<li><a href="%(up)s#ask">Ask a question</a></li>') % {"up": up}
    elif slug is None and not sections:
        more = '<li><a href="%ssymptoms/">Every symptom</a></li>' % up

    return """<aside class="rail" id="rail" data-index="%(up)ssearch-index.json" data-up="%(up)s" aria-label="Sheets and search">
<div class="rail__in">
<form class="sf" role="search" data-search onsubmit="return false">
<label class="sr" for="sf-input">Search every command</label>
<div class="sf__box">
<span class="sf__icon" aria-hidden="true">&#9906;</span>
<div class="sf__ghost" aria-hidden="true"><span class="sf__typed"></span><span class="sf__rest"></span></div>
<input id="sf-input" class="sf__input" type="text" autocomplete="off" spellcheck="false"
       placeholder="Search commands" aria-expanded="false" aria-controls="sf-results" role="combobox">
<kbd class="sf__kbd">/</kbd>
</div>
<div class="sf__results" id="sf-results" role="listbox" hidden></div>
</form>
<h4>Sheets</h4>
<ul class="rail__sheets">%(sheets)s</ul>
%(onpage)s
<h4>More</h4>
<ul class="rail__more">%(more)s
<li><a href="%(gh)s" target="_blank" rel="noopener">Star on GitHub</a></li>
</ul>
</div>
</aside>""" % dict(up=up, gh=GH, sheets=sheets, onpage=onpage, more=more)


def shell_open(path, sections=None, slug=None):
    return '<div class="app">' + rail(path, sections, slug) + '<div class="app__body">'


def masthead(path):
    up = get_up(path)
    def cur(p):
        return ' aria-current="page"' if p == path else ""
    # Build dropdown items — crawlable <a> only, disabled as gray <span>
    cs_items = "".join(
        '<li><a class="t-%s" href="%s%s/"><i class="dot"></i><span>%s</span><b>%s</b></a></li>' % (
            t["slug"], up, t["slug"], html.escape(t["name"]), STATS.get(t["slug"], {}).get("cmds",""))
        for t in TOPICS)
    cs_items += "".join(
        '<li><a class="t-%s rail__soon" href="%s/issues/new?labels=request&amp;title=%%5B%s%%5D%%20" target="_blank" rel="noopener"><i class="dot"></i><span>%s</span><b>&mdash;</b></a></li>' % (
            pl["slug"], GH, pl["name"], html.escape(pl["name"])) for pl in PLANNED)
    tut_items = ""
    for t in TOPICS:
        n = len(TUTS_BY_TOPIC.get(t["slug"], []))
        if n:
            tut_items += '<li><a class="t-%s" href="%s%s/tutorials/"><i class="dot"></i><span>%s</span><b>%d</b></a></li>' % (
                t["slug"], up, t["slug"], html.escape(t["name"]), n)
        else:
            tut_items += '<li><span class="navdrop__soon t-%s"><i class="dot"></i><span>%s</span><b>&mdash;</b></span></li>' % (
                t["slug"], html.escape(t["name"]))
    # kafka planned as disabled as requested
    for pl in PLANNED:
        n = len(TUTS_BY_TOPIC.get(pl["slug"], []))
        if n:
            tut_items += '<li><a class="t-%s" href="%s%s/tutorials/"><i class="dot"></i><span>%s</span><b>%d</b></a></li>' % (
                pl["slug"], up, pl["slug"], html.escape(pl["name"]), n)
        else:
            tut_items += '<li><span class="navdrop__soon t-%s"><i class="dot"></i><span>%s</span><b>&mdash;</b></span></li>' % (
                pl["slug"], html.escape(pl["name"]))
    return """<header class="masthead"><div class="shell masthead__in">
<button class="burger" type="button" data-drawer aria-controls="rail" aria-expanded="false">
<span></span><span></span><span></span><span class="sr">Sheets and search</span>
</button>
<a class="wordmark" href="%(up)s"><span class="wordmark__slash">$</span> commands-cheat-sheet</a>
<nav aria-label="Primary">
<button class="findbtn" type="button" data-palette-open>
<span aria-hidden="true">&#9906;</span> Search <kbd>&#8984;K</kbd>
</button>
<div class="navdrop" data-navdrop>
<button class="navdrop__btn" type="button" aria-expanded="false" aria-haspopup="true">Cheat Sheets <span aria-hidden="true">▾</span></button>
<div class="navdrop__panel" hidden>
<ul class="navdrop__list">%(cs_items)s</ul>
<div class="navdrop__foot"><a href="%(up)scheatsheets/">All cheat sheets →</a></div>
</div>
</div>
<div class="navdrop" data-navdrop>
<button class="navdrop__btn" type="button" aria-expanded="false" aria-haspopup="true">Tutorials <span aria-hidden="true">▾</span></button>
<div class="navdrop__panel" hidden>
<ul class="navdrop__list">%(tut_items)s</ul>
<div class="navdrop__foot"><a href="%(up)stutorials/">All tutorials →</a></div>
</div>
</div>
<a href="%(up)ssymptoms/"%(sym)s>Symptoms</a>
<a class="opt" href="%(up)s#ask">Ask</a>
<button class="themetoggle" type="button" data-theme-toggle>PAPER</button>
<a class="btn btn--sm" href="%(gh)s" target="_blank" rel="noopener"><span class="btn__star">&#9733;</span> Star</a>
</nav></div></header>""" % dict(up=up, gh=GH, s="", sym=cur("symptoms"), cs_items=cs_items, tut_items=tut_items)


def footer(path):
    up = get_up(path)
    cols = "".join(
        '<li><a href="%s%s/">%s</a></li>' % (up, t["slug"], t["name"]) for t in TOPICS)
    return """<footer class="footer"><div class="shell">
<div class="footer__grid">
<div>
<h4>Sitemap</h4>
<ul>
<li><a href="%(up)s">Home</a></li>
<li><a href="%(up)ssymptoms/">Every symptom, one page</a></li>
<li><a href="%(up)s#pipeline">How a sheet is made</a></li>
<li><a href="%(up)s#ask">Ask a question</a></li>
<li><a href="%(up)ssitemap.xml">sitemap.xml</a></li>
</ul>
</div>
<div><h4>Cheat sheets</h4><ul>%(cols)s</ul></div>
<div>
<h4>Take part</h4>
<ul>
<li><a href="%(gh)s" target="_blank" rel="noopener">Star the repository</a></li>
<li><a href="%(gh)s/issues/new?labels=question" target="_blank" rel="noopener">Ask a question</a></li>
<li><a href="%(gh)s/issues/new?labels=correction" target="_blank" rel="noopener">Report a wrong command</a></li>
<li><a href="%(gh)s/issues/new?labels=request" target="_blank" rel="noopener">Request a technology</a></li>
<li><a href="%(gh)s/issues" target="_blank" rel="noopener">Open issues</a></li>
</ul>
</div>
<div>
<h4>About</h4>
<ul>
<li><a href="%(gh)s#readme" target="_blank" rel="noopener">Read the repository</a></li>
<li><a href="https://github.com/hismaili-awesome-ai/cheatsheet-forge" target="_blank" rel="noopener">cheatsheet-forge pipeline</a></li>
<li><a href="%(gh)s/blob/main/CLAUDE.md" target="_blank" rel="noopener">Contributor rules</a></li>
</ul>
</div>
</div>
<div class="footer__base">
<span>Every command recorded on a working system and traced to its source.</span>
<span><a href="%(gh)s" target="_blank" rel="noopener">github.com/%(repo)s</a></span>
</div>
</div></footer>
</div></div>
<div class="palette" data-palette hidden>
<div class="palette__scrim" data-palette-close></div>
<div class="palette__box" role="dialog" aria-modal="true" aria-label="Search every command">
<form class="sf sf--big" role="search" data-search onsubmit="return false">
<div class="sf__box">
<span class="sf__icon" aria-hidden="true">&#9906;</span>
<div class="sf__ghost" aria-hidden="true"><span class="sf__typed"></span><span class="sf__rest"></span></div>
<input class="sf__input" type="text" autocomplete="off" spellcheck="false"
       placeholder="Search 138 commands, 48 symptoms" aria-expanded="false" role="combobox">
<button class="palette__esc" type="button" data-palette-close>esc</button>
</div>
<div class="sf__results" role="listbox" hidden></div>
<p class="palette__hint"><kbd>&#8593;</kbd><kbd>&#8595;</kbd> move &nbsp; <kbd>&#8629;</kbd> open &nbsp; <kbd>tab</kbd> complete</p>
</form>
</div>
</div>
<script src="%(up)sassets/site.js" defer></script>
</body></html>""" % dict(up=up, gh=GH, repo=REPO, cols=cols)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def build_topic(t, stats, patterns_all, idx):
    md = open(os.path.join(ROOT, t["file"]), encoding="utf-8").read()
    title, intro, sections, patterns = parse(md)
    counter = [0]

    railsecs = [(s["id"], s["heading"]) for s in sections]
    if patterns:
        railsecs.append(("symptoms", "Symptom \u2192 move"))
    railsecs.append(("next", "Related sheets"))

    body = []
    if intro:
        body.append('<section id="overview">'
                    + render(intro, counter, idx, t["slug"], t["name"]) + "</section>")
    for s in sections:
        idx.append(dict(t=t["slug"], n=t["name"], k="section", x=s["heading"], d="",
                        u="%s/#%s" % (t["slug"], s["id"])))
        body.append('<section id="%s"><h2 id="%s">%s</h2>%s</section>'
                    % (s["id"], s["id"], html.escape(s["heading"]),
                       render(s["blocks"], counter, idx, t["slug"], t["name"])))

    faq = []
    for sym, move in patterns:
        pid = "q-" + slugify(sym)[:60]
        faq.append(
            '<div class="faq__item" id="%s"><h3 class="faq__q"><a href="#%s">%s</a></h3>'
            '<p class="faq__a">%s</p></div>' % (pid, pid, inline(sym), inline(move)))
        patterns_all.append((t, sym, move, pid))
        idx.append(dict(t=t["slug"], n=t["name"], k="symptom", x=sym,
                        d=re.sub(r"[`*]", "", move), u="%s/#%s" % (t["slug"], pid)))
    if faq:
        body.append(
            '<section id="symptoms"><h2 id="symptoms">Symptom &rarr; move</h2>'
            '<p>Every failure this sheet answers, phrased the way it appears in a terminal. '
            'Link to any one of them, or scan <a href="../symptoms/">all %d symptoms across every sheet</a>.</p>'
            '<div class="faq">%s</div></section>' % (stats["patterns"], "".join(faq)))

    rel = "".join(
        '<a class="t-%s" href="../%s/"><b>%s</b><span>%s</span></a>'
        % (BY_SLUG[r]["slug"], BY_SLUG[r]["slug"], BY_SLUG[r]["name"], html.escape(BY_SLUG[r]["blurb"]))
        for r in t["related"] if r in BY_SLUG)

    body.append("""<section id="next">
<h2 id="next">Related sheets</h2>
<p>Work rarely stays inside one tool. These are the sheets most often open alongside this one.</p>
<div class="related">%s</div>
<div class="pagecta">
<p><strong>Did this resolve it?</strong> Stars indicate which sheets are worth extending. If a command here is wrong, or destructive without saying so, open an issue — I would rather fix it than have someone find out on a live system.</p>
<div style="display:flex;gap:.6rem;flex-wrap:wrap">
<a class="btn" href="%s" target="_blank" rel="noopener"><span class="btn__star">&#9733;</span> Star the repo</a>
<a class="btn btn--ghost" href="%s/issues/new?labels=correction&amp;title=%s" target="_blank" rel="noopener">Report a wrong command</a>
</div>
</div>
</section>""" % (rel, GH, GH, "[" + t["name"] + "]%20"))

    faq_ld = ""
    if patterns:
        items = ",".join(
            '{"@type":"Question","name":%s,"acceptedAnswer":{"@type":"Answer","text":%s}}'
            % (jsonstr(sym), jsonstr(re.sub(r"[`*]", "", move)))
            for sym, move in patterns)
        faq_ld = '{"@type":"FAQPage","@id":"%s%s/#faq","mainEntity":[%s]}' % (BASE, t["slug"], items)

    ld = """<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
{"@type":"TechArticle","@id":"%(base)s%(slug)s/#article","headline":%(hl)s,"description":%(desc)s,
 "url":"%(base)s%(slug)s/","inLanguage":"en","isPartOf":{"@type":"WebSite","@id":"%(base)s#site","name":"commands-cheat-sheet","url":"%(base)s"},
 "author":{"@type":"Person","name":"hismaili","url":"https://github.com/hismaili"},
 "proficiencyLevel":"Expert","keywords":%(kw)s},
{"@type":"BreadcrumbList","itemListElement":[
 {"@type":"ListItem","position":1,"name":"Cheat sheets","item":"%(base)s"},
 {"@type":"ListItem","position":2,"name":%(nm)s,"item":"%(base)s%(slug)s/"}]}%(faq)s
]}</script>
""" % dict(base=BASE, slug=t["slug"], hl=jsonstr(t["title"]), desc=jsonstr(t["desc"]),
           kw=jsonstr(t["kw"]), nm=jsonstr(t["name"]),
           faq=("," + faq_ld) if faq_ld else "")

    # tutorials pill for this topic (pSEO cross-link)
    n_tuts = len(TUTS_BY_TOPIC.get(t["slug"], []))
    tut_pill = ''
    if n_tuts:
        tut_pill = '<p style="margin-top:.6rem"><a class="btn btn--ghost" href="tutorials/">Tutorials <span style="background:var(--topic);color:var(--ground);padding:1px 6px;border-radius:20px;font-size:.7rem;margin-left:.3rem">%d</span></a></p>' % n_tuts
    else:
        tut_pill = '<p style="margin-top:.6rem"><a class="btn btn--ghost" style="opacity:.6" href="tutorials/">Tutorials <span style="border:1px solid var(--rule);padding:1px 6px;border-radius:20px;font-size:.7rem;margin-left:.3rem">&mdash;</span></a></p>'
    page = head(t["title"] + " | commands-cheat-sheet", t["desc"], t["slug"], t["kw"], ld,
                hue=hue_style(t["slug"]))
    page += masthead(t["slug"])
    page += shell_open(t["slug"], railsecs, t["slug"])
    page += """<main id="main"><div class="shell">
<nav class="crumb" aria-label="Breadcrumb"><a href="../">Cheat sheets</a><span>/</span><span>%(name)s</span></nav>
<div class="topichead">
<p class="eyebrow"><span class="tick">&#9679;</span> %(cmds)d commands &middot; %(pats)d symptoms &middot; traced to source</p>
<h1>%(title)s</h1>
<p class="lede">%(blurb)s</p>
%(tut_pill)s
</div>
<div class="doc"><div class="prose">%(body)s</div></div>
</div></main>""" % dict(
        name=html.escape(t["name"]), title=html.escape(title), blurb=html.escape(t["blurb"]),
        cmds=stats["cmds"], pats=len(patterns), body="\n".join(body), tut_pill=tut_pill)
    page += footer(t["slug"])

    d = os.path.join(OUT, t["slug"])
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
    return len(patterns), counter[0]


def build_cheatsheets_hub(stats, totals, idx):
    sheets = "".join("""<a class="sheet t-%(slug)s" href="../%(slug)s/">
<span class="sheet__name">%(name)s</span>
<p class="sheet__desc">%(blurb)s</p>
<span class="sheet__foot"><span>%(cmds)d commands</span><span>%(pats)d symptoms</span>%(haz)s</span>
</a>""" % dict(slug=t["slug"], name=html.escape(t["name"]), blurb=html.escape(t["blurb"]),
               cmds=stats[t["slug"]]["cmds"], pats=stats[t["slug"]]["patterns"],
               haz='<span class="haz">%d flagged destructive</span>' % stats[t["slug"]]["destructive"]
                   if stats[t["slug"]]["destructive"] else "")
        for t in TOPICS)
    planned = "".join("""<a class="sheet sheet--empty t-%(slug)s" href="%(gh)s/issues/new?labels=request&amp;title=%%5B%(name)s%%5D%%20" target="_blank" rel="noopener">
<span class="sheet__name">%(name)s</span>
<p class="sheet__desc">The directory exists and the pipeline is configured for it. %(why)s Open an issue and it moves up.</p>
<span class="sheet__foot"><span>Not recorded yet</span><span>Request it &rarr;</span></span>
</a>""" % dict(gh=GH, name=p["name"], why=p["why"], slug=p["slug"]) for p in PLANNED)
    ld = """<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
{"@type":"CollectionPage","@id":"%(base)scheatsheets/#page","name":"Cheat Sheets","url":"%(base)scheatsheets/",
 "description":%(d)s,"isPartOf":{"@type":"WebSite","@id":"%(base)s#site"}},
{"@type":"BreadcrumbList","itemListElement":[
 {"@type":"ListItem","position":1,"name":"Cheat sheets","item":"%(base)s"}]},
{"@type":"ItemList","name":"Cheat Sheets","numberOfItems":%(n)d,"itemListElement":[%(items)s]}
]}</script>
""" % dict(base=BASE, d=jsonstr("Every cheat sheet by topic — %d technologies, %d commands." % (len(TOPICS), totals["cmds"])),
           n=len(TOPICS),
           items=",".join('{"@type":"ListItem","position":%d,"name":%s,"url":"%s%s/"}' % (i+1, jsonstr(t["name"]), BASE, t["slug"]) for i,t in enumerate(TOPICS)))
    page = head("Cheat Sheets — Every Topic | commands-cheat-sheet", "Every cheat sheet by topic.", "cheatsheets", "cheat sheets", ld, hue=hue_style())
    page += masthead("cheatsheets")
    page += shell_open("cheatsheets")
    page += """<main id="main"><div class="shell">
<nav class="crumb" aria-label="Breadcrumb"><a href="../">Cheat sheets</a><span>/</span><span>All</span></nav>
<div class="topichead">
<p class="eyebrow"><span class="tick">&#9679;</span> %d technologies &middot; %d commands</p>
<h1>Cheat Sheets</h1>
<p class="lede">Every sheet is indexed by problem, not by flag. Pick a technology.</p>
</div>
<div class="sheets">%s%s</div>
</div></main>""" % (len(TOPICS), totals["cmds"], sheets, planned)
    page += footer("cheatsheets")
    d = os.path.join(OUT, "cheatsheets")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
    for t in TOPICS:
        idx.append(dict(t="cheatsheets", n="Cheat Sheets", k="section", x=t["name"], d=t["blurb"], u="cheatsheets/#%s" % t["slug"]))


def build_tutorials_hub(idx):
    groups = []
    for t in TOPICS + PLANNED:
        tuts = TUTS_BY_TOPIC.get(t["slug"], [])
        if tuts:
            items = "".join('<a class="t-%s" href="../%s/tutorials/%s/"><b>%s</b><span>%s</span></a>' % (t["slug"], t["slug"], tut["slug"], html.escape(tut["name"]), html.escape(tut["desc"][:120])) for tut in tuts)
        else:
            items = '<span class="sheet--empty" style="display:block;padding:1rem;color:var(--muted);font-size:.9rem">No tutorials yet — <a href="%s/issues/new?labels=request&amp;title=%%5B%s%%5D%%20" target="_blank" rel="noopener">request one</a>.</span>' % (GH, t["name"])
            # still render disabled style
        groups.append('<div class="symgroup t-%s" id="%s"><h2>%s <span class="n">%d</span></h2><div class="symlist">%s</div><p style="margin-top:.8rem;font-size:.9rem"><a href="../%s/tutorials/">Open %s tutorials &rarr;</a></p></div>' % (t["slug"], t["slug"], html.escape(t["name"]), len(tuts), items, t["slug"], html.escape(t["name"])))
    # also include topics with no planned? already
    desc = "Step-by-step tutorials by topic — %d tutorials across %d technologies." % (len(TUTORIALS), len(TOPICS))
    ld = """<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
{"@type":"CollectionPage","@id":"%(base)stutorials/#page","name":"Tutorials","url":"%(base)stutorials/",
 "description":%(d)s,"isPartOf":{"@type":"WebSite","@id":"%(base)s#site"}},
{"@type":"BreadcrumbList","itemListElement":[
 {"@type":"ListItem","position":1,"name":"Tutorials","item":"%(base)stutorials/"}]},
{"@type":"ItemList","name":"Tutorials","numberOfItems":%(n)d,"itemListElement":[%(items)s]}
]}</script>
""" % dict(base=BASE, d=jsonstr(desc), n=len(TUTORIALS),
           items=",".join('{"@type":"ListItem","position":%d,"name":%s,"url":"%s%s/tutorials/%s/"}' % (i+1, jsonstr(tut["name"]), BASE, tut["topic"], tut["slug"]) for i,tut in enumerate(TUTORIALS)))
    page = head("Tutorials — Step-by-Step Guides | commands-cheat-sheet", desc, "tutorials", "tutorials", ld, hue=hue_style())
    page += masthead("tutorials")
    page += shell_open("tutorials", [(t["slug"], t["name"]) for t in TOPICS])
    page += """<main id="main"><div class="shell">
<nav class="crumb" aria-label="Breadcrumb"><a href="../">Cheat sheets</a><span>/</span><span>Tutorials</span></nav>
<div class="topichead">
<p class="eyebrow"><span class="tick">&#9679;</span> %d tutorials &middot; %d technologies</p>
<h1>Tutorials</h1>
<p class="lede">Guides that walk a failure end-to-end. Each tutorial lives under its topic and keeps the sheet as a companion.</p>
</div>
<nav class="jump" aria-label="Jump to a technology">%s</nav>
%s
</div></main>""" % (len(TUTORIALS), len(TOPICS), "".join('<a class="t-%s" href="#%s">%s</a>' % (t["slug"], t["slug"], html.escape(t["name"])) for t in TOPICS), "".join(groups))
    page += footer("tutorials")
    d = os.path.join(OUT, "tutorials")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
    for tut in TUTORIALS:
        idx.append(dict(t="tutorials", n="Tutorials", k="section", x=tut["name"], d=tut["desc"][:100], u="tutorials/#%s" % tut["topic"]))
        idx.append(dict(t=tut["topic"]+"/tutorials", n=tut["name"], k="cmd", x=tut["title"], d=tut["desc"][:100], u="%s/tutorials/%s/" % (tut["topic"], tut["slug"])))


def build_topic_tutorials(slug, idx):
    t = BY_SLUG.get(slug) or next((p for p in PLANNED if p["slug"]==slug), None)
    if not t:
        return
    tuts = TUTS_BY_TOPIC.get(slug, [])
    name = t["name"]
    cards = ""
    if tuts:
        for tut in tuts:
            cards += """<a class="sheet t-%s" href="%s/"><span class="sheet__name">%s</span><p class="sheet__desc">%s</p><span class="sheet__foot"><span>%s</span><span>Tutorial</span></span></a>""" % (slug, tut["slug"], html.escape(tut["name"]), html.escape(tut["desc"]), html.escape(tut["topic"]))
    else:
        cards = '<p style="color:var(--muted)">No tutorials yet for %s — <a href="%s/issues/new?labels=request&amp;title=%%5B%s%%5D%%20" target="_blank" rel="noopener">request one</a>.</p>' % (html.escape(name), GH, html.escape(name))
    desc = "%s tutorials — %d guides." % (name, len(tuts))
    ld = """<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
{"@type":"CollectionPage","@id":"%(base)s%(slug)s/tutorials/#page","name":%(name)s,"url":"%(base)s%(slug)s/tutorials/",
 "description":%(d)s,"isPartOf":{"@type":"WebSite","@id":"%(base)s#site"}},
{"@type":"BreadcrumbList","itemListElement":[
 {"@type":"ListItem","position":1,"name":"Cheat sheets","item":"%(base)s"},
 {"@type":"ListItem","position":2,"name":%(nm)s,"item":"%(base)s%(slug)s/"},
 {"@type":"ListItem","position":3,"name":"Tutorials","item":"%(base)s%(slug)s/tutorials/"}]}
]}</script>
""" % dict(base=BASE, slug=slug, name=jsonstr(name+" Tutorials"), d=jsonstr(desc), nm=jsonstr(name))
    page = head(name+" Tutorials | commands-cheat-sheet", desc, slug+"/tutorials", name+" tutorials", ld, hue=hue_style(slug))
    page += masthead(slug+"/tutorials")
    page += shell_open(slug+"/tutorials", [(tut["slug"], tut["name"]) for tut in tuts] if tuts else [], slug)
    page += """<main id="main"><div class="shell">
<nav class="crumb" aria-label="Breadcrumb"><a href="../../">Cheat sheets</a><span>/</span><a href="../">%s</a><span>/</span><span>Tutorials</span></nav>
<div class="topichead">
<p class="eyebrow"><span class="tick">&#9679;</span> %d tutorial%s</p>
<h1>%s Tutorials</h1>
<p class="lede">Step-by-step guides for %s. Keep the <a href="../">cheat sheet</a> open alongside.</p>
</div>
<div class="sheets">%s</div>
</div></main>""" % (html.escape(name), len(tuts), "" if len(tuts)==1 else "s", html.escape(name), html.escape(name), cards)
    page += footer(slug+"/tutorials")
    d = os.path.join(OUT, slug, "tutorials")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
    for tut in tuts:
        idx.append(dict(t=slug+"/tutorials", n=name, k="section", x=tut["name"], d=tut["desc"][:80], u="%s/tutorials/#%s" % (slug, tut["slug"])))


def build_tutorial_leaf(tut, idx):
    src = os.path.join(ROOT, tut["file"])
    raw = open(src, encoding="utf-8").read() if os.path.exists(src) else ""
    # extract inner main content from standalone html — style is handled by site.css .tutorial--dark (no global leak)
    m_main = re.search(r"<main[^>]*>(.*?)</main>", raw, re.S)
    extracted_main = m_main.group(1).strip() if m_main else raw[:5000]
    # build page
    topic = tut["topic"]
    slug = tut["slug"]
    path = topic+"/tutorials/"+slug
    # breadcrumb + topichead
    title = tut["title"]
    desc = tut["desc"]
    kw = tut["kw"]
    # HowTo steps from tutorial toc
    steps = re.findall(r'<li><a href="#[^"]+">(.*?)</a></li>', raw)
    howto_items = ",".join('{"@type":"HowToStep","name":%s}' % jsonstr(re.sub(r"<[^>]+>", "", s).strip()) for s in steps) if steps else ""
    ld = """<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
{"@type":"TechArticle","@id":"%(base)s%(path)s/#article","headline":%(hl)s,"description":%(desc)s,
 "url":"%(base)s%(path)s/","inLanguage":"en","isPartOf":{"@type":"WebSite","@id":"%(base)s#site","name":"commands-cheat-sheet","url":"%(base)s"},
 "author":{"@type":"Person","name":"hismaili","url":"https://github.com/hismaili"},
 "proficiencyLevel":"Beginner","keywords":%(kw)s},
{"@type":"BreadcrumbList","itemListElement":[
 {"@type":"ListItem","position":1,"name":"Cheat sheets","item":"%(base)s"},
 {"@type":"ListItem","position":2,"name":%(nm)s,"item":"%(base)s%(topic)s/"},
 {"@type":"ListItem","position":3,"name":"Tutorials","item":"%(base)s%(topic)s/tutorials/"},
 {"@type":"ListItem","position":4,"name":%(hl)s,"item":"%(base)s%(path)s/"}]},
{"@type":"HowTo","name":%(hl)s,"description":%(desc)s,"totalTime":"PT15M","tool":"git","step":[%(steps)s]}
]}</script>
""" % dict(base=BASE, path=path, hl=jsonstr(title), desc=jsonstr(desc), kw=jsonstr(kw), nm=jsonstr(BY_SLUG[topic]["name"] if topic in BY_SLUG else topic), topic=topic, steps=howto_items)
    # toc for rail
    toc_ids = re.findall(r'<section id="([^"]+)"', extracted_main)
    toc_names = re.findall(r'<h2>(.*?)</h2>', extracted_main)
    railsecs = list(zip(toc_ids[:7], [re.sub(r"<[^>]+>","", x).strip() for x in toc_names[:7]]))
    page = head(title+" | commands-cheat-sheet", desc, path, kw, ld, hue=hue_style(topic))
    page += masthead(path)
    page += shell_open(path, railsecs, topic)
    # topichead with tutorial eyebrow
    page += """<main id="main"><div class="shell">
<nav class="crumb" aria-label="Breadcrumb"><a href="../../../">Cheat sheets</a><span>/</span><a href="../../">%(tname)s</a><span>/</span><a href="../">Tutorials</a><span>/</span><span>%(tutname)s</span></nav>
<div class="topichead">
<p class="eyebrow"><span class="tick">&#9679;</span> Tutorial &middot; %(tname)s</p>
<h1>%(title)s</h1>
<p class="lede">%(desc)s</p>
</div>
<div class="tutorial--dark"><div class="wrap">%(body)s</div></div>
<div class="pagecta" style="margin-top:2rem">
<p><strong>Keep the cheat sheet open?</strong> The <a href="../../">Git cheat sheet</a> lists every command with its symptom.</p>
<div style="display:flex;gap:.6rem;flex-wrap:wrap"><a class="btn" href="../../">Open cheat sheet</a><a class="btn btn--ghost" href="../">All %(tname)s tutorials</a></div>
</div>
</div></main>""" % dict(tname=html.escape(BY_SLUG[topic]["name"] if topic in BY_SLUG else topic), tutname=html.escape(tut["name"]), title=html.escape(title), desc=html.escape(desc), body=extracted_main)
    page += footer(path)
    # copy script from tutorial (handles .copy data-copy)
    page = page.replace("</body>", """<script>
document.querySelectorAll('.tutorial--dark .copy').forEach(function(btn){
  btn.addEventListener('click', async function(){
    var txt = btn.getAttribute('data-copy');
    try{ await navigator.clipboard.writeText(txt); var old=btn.textContent; btn.textContent='Copied!'; setTimeout(function(){btn.textContent=old;},1200);}catch(e){
      var ta=document.createElement('textarea');ta.value=txt;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();btn.textContent='Copied!'; setTimeout(function(){btn.textContent='Copy';},1200);
    }
  });
});
</script>
</body>""")
    d = os.path.join(OUT, topic, "tutorials", slug)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
    # index for search: tutorial leaf sections + code blocks
    for sid, nm in railsecs:
        idx.append(dict(t=topic, n=tut["name"], k="section", x=nm, d="", u="%s/#%s" % (path, sid)))
    for cmd in re.findall(r"git [^\n<]+", extracted_main):
        c = html.unescape(cmd.strip())
        if len(c) > 3 and len(c) < 80:
            idx.append(dict(t=topic, n=tut["name"], k="cmd", x=c, d="tutorial", u=path+"/"))


def jsonstr(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def count_commands(path):
    md = open(path, encoding="utf-8").read()
    n = 0
    for block in re.findall(r"```bash\n(.*?)```", md, re.S):
        n += len([l for l in block.split("\n") if l.strip() and not l.strip().startswith("#")])
    return n


def count_flags(path):
    md = open(path, encoding="utf-8").read().lower()
    return md.count("destructive"), md.count("uncertain")


def build_index(stats, totals):
    sheets = "".join("""<a class="sheet t-%(slug)s" href="%(slug)s/">
<span class="sheet__name">%(name)s</span>
<p class="sheet__desc">%(blurb)s</p>
<span class="sheet__foot"><span>%(cmds)d commands</span><span>%(pats)d symptoms</span>%(haz)s</span>
</a>""" % dict(slug=t["slug"], name=html.escape(t["name"]), blurb=html.escape(t["blurb"]),
               cmds=stats[t["slug"]]["cmds"], pats=stats[t["slug"]]["patterns"],
               haz='<span class="haz">%d flagged destructive</span>' % stats[t["slug"]]["destructive"]
                   if stats[t["slug"]]["destructive"] else "")
        for t in TOPICS)

    planned = "".join("""<a class="sheet sheet--empty t-%(slug)s" href="%(gh)s/issues/new?labels=request&amp;title=%%5B%(name)s%%5D%%20" target="_blank" rel="noopener">
<span class="sheet__name">%(name)s</span>
<p class="sheet__desc">The directory exists and the pipeline is configured for it. %(why)s Open an issue and it moves up.</p>
<span class="sheet__foot"><span>Not recorded yet</span><span>Request it &rarr;</span></span>
</a>""" % dict(gh=GH, name=p["name"], why=p["why"], slug=p["slug"]) for p in PLANNED)

    # The grid would otherwise end on a blank cell; a request beats a hole.
    planned += """<a class="sheet sheet--empty" href="%(gh)s/issues/new?labels=request" target="_blank" rel="noopener">
<span class="sheet__name">Something else</span>
<p class="sheet__desc">Sheets get written for tools I actually run. If you want one for a tool I do not, say so &mdash; requests are how this list grows.</p>
<span class="sheet__foot"><span>Open a request &rarr;</span></span>
</a>""" % dict(gh=GH)

    options = "".join('<option>%s</option>' % t["name"] for t in TOPICS) + \
              "".join('<option>%s</option>' % p["name"] for p in PLANNED) + \
              '<option>Not listed yet</option>'

    ld = """<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
{"@type":"WebSite","@id":"%(base)s#site","name":"commands-cheat-sheet","url":"%(base)s",
 "description":%(desc)s,"inLanguage":"en",
 "author":{"@type":"Person","name":"hismaili","url":"https://github.com/hismaili"}},
{"@type":"ItemList","name":"Cheat sheets","numberOfItems":%(n)d,"itemListElement":[%(items)s]},
{"@type":"SoftwareSourceCode","name":"commands-cheat-sheet","codeRepository":"%(gh)s",
 "programmingLanguage":"Shell","url":"%(base)s"}
]}</script>
""" % dict(base=BASE, gh=GH, n=len(TOPICS), desc=jsonstr(INDEX_DESC),
           items=",".join(
               '{"@type":"ListItem","position":%d,"name":%s,"url":"%s%s/"}'
               % (i + 1, jsonstr(t["name"]), BASE, t["slug"]) for i, t in enumerate(TOPICS)))

    page = head("Command Cheat Sheets: OpenShift, Linux, Podman, Vault, OCI, curl and more", INDEX_DESC, "",
                "command cheat sheet, oc commands, podman commands, vault commands, linux commands, "
                "devops cheat sheet, field tested commands, destructive command warnings", ld,
                hue=hue_style())
    page += masthead("")
    page += shell_open("", [("why", "Why this exists"), ("sheets", "The sheets"),
                            ("pipeline", "How a sheet is made"), ("ask", "Ask a question")])
    page += """<main id="main">

<section class="hero"><div class="shell">
<p class="eyebrow"><span class="tick">&#9679;</span> %(sheets)d technologies &middot; %(cmds)d commands &middot; %(pats)d problems solved</p>
<h1 class="hero__h1">
<span>Namespace stuck <em>Terminating</em>.</span>
<span>Port already in use.</span>
<span>A CORS error with no detail.</span>
</h1>
<div class="hero__grid">
<div>
<p class="lede">One notebook, %(sheets)d technologies &mdash; clusters, hosts, containers, secrets, builds and HTTP. Every command is recorded with what it does, the problem it resolves, and the session it came from.</p>
<div class="hero__cta">
<a class="btn" href="%(gh)s" target="_blank" rel="noopener"><span class="btn__star">&#9733;</span> Star on GitHub</a>
<a class="btn btn--ghost" href="#sheets">Browse the cheat sheets</a>
</div>
<p class="hero__meta">No sign-up. No tracking. No analytics.</p>
</div>

<div class="record">
<div class="record__bar"><span class="record__dot"></span> Anatomy of an entry &middot; example from OpenShift</div>
<div class="record__row">
<span class="record__k">Symptom</span>
<p class="record__symptom">A namespace has been <code>Terminating</code> for forty minutes and will not delete.</p>
</div>
<hr class="perf">
<div class="record__row">
<span class="record__k">Command, as run</span>
<pre><code><span class="c"># strip finalizers from every Argo resource in the namespace</span>
for obj in $(oc get applications.argoproj.io,\\
    applicationsets.argoproj.io,appprojects.argoproj.io \\
    -n &lt;NAMESPACE&gt; -o name); do
  oc patch $obj -n &lt;NAMESPACE&gt; --type merge \\
    -p '{"metadata":{"finalizers":null}}'
done</code></pre>
</div>
<hr class="perf">
<div class="record__hazard">
<span class="record__k">Consequence</span>
<p>Orphans every resource the app managed. ArgoCD stops tracking them and will never prune or reconcile them again. Delete the workload properly first if you can.</p>
</div>
<hr class="perf">
<div class="record__trace">
<b>Traced</b> <span>_sources/openshift/2026-08-21-argocd-logging-storage.txt</span>
</div>
</div>

<div class="tally">
<div><b>%(sheets)d</b><span>Technologies</span></div>
<div><b>%(cmds)d</b><span>Commands</span></div>
<div><b>%(pats)d</b><span>Problems solved</span></div>
<div><b>100%%</b><span>Traced to source</span></div>
</div>

</div></div></section>

<section class="band" id="why"><div class="shell">
<div class="band__head">
<p class="eyebrow">Why this exists</p>
<h2>The command exists. Finding it again is the problem.</h2>
</div>
<div class="acts">

<div class="act">
<div class="act__label">The problem</div>
<div>
<h3>Documentation is organised by flag. Problems are not.</h3>
<p>Every tool in the stack fails in a small number of recognisable ways, and the command that resolves each one already exists. It has usually been run before, on this machine, by you. Retrieval is the constraint, not knowledge.</p>
<p>Vendor references index by subcommand and flag. The problem in front of you presents as a symptom, and the session where it was last resolved is three months gone.</p>
</div>
</div>

<div class="act">
<div class="act__label">What it costs</div>
<div>
<h3>A command without its context is not reusable.</h3>
<p>A command saved with no note about what it was for, which problem it closed, or what it removes is a liability rather than an asset. It gets pasted into the wrong situation, or into a live system whose blast radius nobody wrote down.</p>
<p class="act__quote">oc delete crd applications.argoproj.io<br><span style="color:var(--hazard)">&rarr; deletes every ArgoCD Application on the cluster, in every namespace. There is no per-namespace opt-out.</span></p>
<p><code>podman rm -a</code> removes every stopped container on the host, not the one being debugged. <code>sudo fuser -k &lt;PORT&gt;/tcp</code> kills whatever holds the port, with no graceful shutdown and no prompt. Each is correct, and each is documented. What is absent from the documentation is what it takes with it.</p>
</div>
</div>

<div class="act act--solve">
<div class="act__label">What this is</div>
<div>
<h3>A working notebook: %(cmds)d commands across %(sheets)d technologies.</h3>
<p>Each entry records four things: the command, what it is for, the problem it resolves, and the session it came from. Where a command destroys something, the entry states what. A command that cannot be traced does not reach the page, and that rule is enforced by the build rather than by intent.</p>
<p>Where a command is unusual but worked, it is kept and annotated rather than corrected. <a href="ruby/">A <code>sudo gem install --user-install</code> whose flags contradict each other</a> is still what ran successfully on the machine it was recorded from.</p>
<p><a href="#sheets">Start with a cheat sheet</a>, or open <a href="symptoms/">the symptom index</a> if the problem is already in front of you.</p>
</div>
</div>

</div>
</div></section>

<section class="band band--sunk" id="sheets"><div class="shell">
<div class="band__head">
<p class="eyebrow">The cheat sheets</p>
<h2>Nine technologies, indexed by problem.</h2>
<p class="lede">Clusters, hosts, containers, secrets, cloud CLIs, builds and HTTP. Each sheet opens with the problems it answers, then the commands with what each is for, then a symptom-to-command table built for scanning under pressure.</p>
</div>
<div class="sheets">%(sheets_html)s%(planned)s</div>
<p style="margin-top:1.5rem;font-size:.92rem;color:var(--muted)">Searching for something specific? <a href="symptoms/">All %(pats)d symptoms, across every sheet, on one page</a>.</p>
</div></section>

<section class="band" id="pipeline"><div class="shell">
<div class="band__head">
<p class="eyebrow">How a sheet is built</p>
<h2>Four stages. A command reaches the page only by surviving all four.</h2>
<p class="lede">Each stage runs on the output of the one before it. The third stage cannot emit a command that the second one did not record.</p>
</div>
<div class="pipe">
<div class="pipe__step"><span class="pipe__n">STAGE 1</span><h3>Record</h3><p>A working session is captured to <code>_sources/</code>. Those captures hold live tokens and hostnames, so they are gitignored and never leave the machine.</p></div>
<div class="pipe__step"><span class="pipe__n">STAGE 2</span><h3>Extract</h3><p>Each command is structured into <code>commands.yml</code> with a <code>source_ref</code> pointing at its dump line. Credentials and identifiers are replaced here, once, at the only stage that reads raw source.</p></div>
<div class="pipe__step"><span class="pipe__n">STAGE 3</span><h3>Write</h3><p>The sheet is generated from that file alone. No <code>source_ref</code>, no output. A plausible command that was never run has no way onto the page.</p></div>
<div class="pipe__step"><span class="pipe__n">STAGE 4</span><h3>Audit</h3><p>A reviewer reads the raw session rather than a summary and compares it against the sheet in both directions: commands invented, and commands dropped. It reports. It does not rewrite a working command.</p></div>
</div>
<p style="margin-top:1.5rem;font-size:.92rem;color:var(--muted)">The pipeline is an open-source project of its own, <a href="https://github.com/hismaili-awesome-ai/cheatsheet-forge" target="_blank" rel="noopener">cheatsheet-forge</a>, and can be run against your own recorded sessions.</p>
</div></section>

<section class="band band--sunk" id="ask"><div class="shell">
<div class="ask">
<div>
<p class="eyebrow">Ask</p>
<h2>Not covered here yet?</h2>
<p class="lede">Open it as an issue. If a recorded session covers the answer, it becomes a new entry on the relevant sheet, with its trace attached like every other entry.</p>
<p style="font-size:.93rem;color:var(--ink-2)">Three kinds of issue always get a reply:</p>
<ul style="font-size:.93rem;color:var(--ink-2);padding-left:1.1rem">
<li><strong>A command here did not work.</strong> That is a defect, and I want the issue.</li>
<li><strong>A command here is destructive and not labelled as such.</strong> That is the most serious defect this site can have.</li>
<li><strong>A technology you want covered.</strong> Requests determine what gets recorded next.</li>
</ul>
<p style="margin-top:1.6rem"><a class="btn" href="%(gh)s" target="_blank" rel="noopener"><span class="btn__star">&#9733;</span> Star the repository</a></p>
</div>
<form class="form" data-issue-form data-repo="%(repo)s">
<div class="field">
<label for="q-topic">Which sheet</label>
<select id="q-topic" name="topic">%(options)s</select>
</div>
<div class="field">
<label for="q-title">What is failing</label>
<input id="q-title" name="title" type="text" placeholder="Namespace will not leave Terminating" required>
</div>
<div class="field">
<label for="q-body">What you have tried</label>
<textarea id="q-body" name="body" placeholder="Paste the command you ran and what it printed."></textarea>
</div>
<button class="btn" type="submit">Open this as a GitHub issue</button>
<p class="form__note">This composes a GitHub issue and opens it in a new tab. Nothing is sent until you submit it there. No form data reaches this site, which has no backend and no analytics.</p>
</form>
</div>
</div></section>

<section class="band"><div class="shell">
<div class="endcta">
<p class="eyebrow">Contribute</p>
<h2>Stars decide which sheets get extended.</h2>
<p class="lede" style="margin-inline:auto">This site carries no analytics. Stars and issues are the only signal about which sheets are worth the next recorded session.</p>
<div class="hero__cta">
<a class="btn" href="%(gh)s" target="_blank" rel="noopener"><span class="btn__star">&#9733;</span> Star on GitHub</a>
<a class="btn btn--ghost" href="%(gh)s/issues/new?labels=question" target="_blank" rel="noopener">Ask a question</a>
</div>
</div>
</div></section>

</main>""" % dict(gh=GH, repo=REPO, sheets=len(TOPICS), cmds=totals["cmds"], pats=totals["patterns"],
                  sheets_html=sheets, planned=planned, options=options)
    page += footer("")
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)


INDEX_DESC = ("A working notebook of commands for OpenShift, Linux, Podman, Vault, OCI, npm, Flutter, Ruby "
              "and curl. Each entry records the command, what it is for, the problem it resolves, and the "
              "session it came from, with every destructive command stating its consequence.")


def build_symptoms(patterns_all, totals):
    jump = "".join('<a class="t-%s" href="#%s">%s</a>' % (t["slug"], t["slug"], html.escape(t["name"]))
                   for t in TOPICS)
    groups = []
    for t in TOPICS:
        rows = [p for p in patterns_all if p[0]["slug"] == t["slug"]]
        if not rows:
            continue
        items = "".join(
            '<a href="../%s/#%s"><b>%s</b><span>%s</span></a>'
            % (t["slug"], pid, inline(sym), inline(move))
            for _t, sym, move, pid in rows)
        groups.append(
            '<div class="symgroup t-%s" id="%s"><h2>%s <span class="n">%d</span></h2>'
            '<div class="symlist">%s</div>'
            '<p style="margin-top:.8rem;font-size:.9rem"><a href="../%s/">Open the full %s sheet &rarr;</a></p></div>'
            % (t["slug"], t["slug"], html.escape(t["name"]), len(rows), items,
               t["slug"], html.escape(t["name"])))

    desc = ("Every failure symptom covered by the cheat sheets, on one page: %d symptoms across %d "
            "technologies, each linking straight to the command that resolves it." % (totals["patterns"], len(TOPICS)))

    ld = """<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
{"@type":"CollectionPage","@id":"%(base)ssymptoms/#page","name":"Symptom index","url":"%(base)ssymptoms/",
 "description":%(d)s,"isPartOf":{"@type":"WebSite","@id":"%(base)s#site"}},
{"@type":"BreadcrumbList","itemListElement":[
 {"@type":"ListItem","position":1,"name":"Cheat sheets","item":"%(base)s"},
 {"@type":"ListItem","position":2,"name":"Symptom index","item":"%(base)ssymptoms/"}]},
{"@type":"FAQPage","@id":"%(base)ssymptoms/#faq","mainEntity":[%(items)s]}
]}</script>
""" % dict(base=BASE, d=jsonstr(desc), items=",".join(
        '{"@type":"Question","name":%s,"acceptedAnswer":{"@type":"Answer","text":%s}}'
        % (jsonstr(sym), jsonstr(re.sub(r"[`*]", "", move)))
        for _t, sym, move, _p in patterns_all))

    page = head("Symptom Index — %d Failures and the Command That Fixes Each | commands-cheat-sheet" % totals["patterns"],
                desc, "symptoms",
                "command not found, namespace stuck terminating, address already in use, cors error, "
                "argocd sync stuck, port already in use, gem command not found", ld,
                hue=hue_style())
    page += masthead("symptoms")
    page += shell_open("symptoms", [(t["slug"], t["name"]) for t in TOPICS])
    page += """<main id="main"><div class="shell">
<nav class="crumb" aria-label="Breadcrumb"><a href="../">Cheat sheets</a><span>/</span><span>Symptom index</span></nav>
<div class="topichead">
<p class="eyebrow"><span class="tick">&#9679;</span> %(n)d symptoms &middot; %(t)d technologies &middot; one page</p>
<h1>Start from the error message.</h1>
<p class="lede">You rarely arrive knowing which tool is at fault. This is every symptom the cheat sheets answer, grouped by technology, each linking to the command that resolves it.</p>
</div>
<nav class="jump" aria-label="Jump to a technology">%(jump)s</nav>
%(groups)s
<div class="pagecta">
<p><strong>Symptom not on this list?</strong> Open it as a question. If a recorded session covers it, it becomes a new entry here.</p>
<div style="display:flex;gap:.6rem;flex-wrap:wrap">
<a class="btn" href="%(gh)s/issues/new?labels=question" target="_blank" rel="noopener">Ask a question</a>
<a class="btn btn--ghost" href="%(gh)s" target="_blank" rel="noopener"><span class="btn__star">&#9733;</span> Star the repo</a>
</div>
</div>
</div></main>""" % dict(n=totals["patterns"], t=len(TOPICS), jump=jump, groups="".join(groups), gh=GH)
    page += footer("symptoms")
    d = os.path.join(OUT, "symptoms")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)


def build_404():
    page = head("Page not found | commands-cheat-sheet",
                "No page at that address. Every cheat sheet on the site is listed here.", "",
                hue=hue_style())
    page += masthead("")
    page += shell_open("")
    page += """<main id="main"><div class="shell"><div class="topichead" style="padding-top:5rem">
<p class="eyebrow">404</p>
<h1>No page at that address.</h1>
<p class="lede">Every cheat sheet is listed below.</p>
</div>
<div class="sheets">%s</div>
<p style="margin:1.5rem 0 5rem"><a href="/commands-cheat-sheet/symptoms/">Or search by symptom &rarr;</a></p>
</div></main>""" % "".join(
        '<a class="sheet t-%s" href="/commands-cheat-sheet/%s/"><span class="sheet__name">%s</span>'
        '<p class="sheet__desc">%s</p></a>'
        % (t["slug"], t["slug"], html.escape(t["name"]), html.escape(t["blurb"]))
        for t in TOPICS)
    page += footer("")
    open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(page)


def build_meta(mtimes):
    import datetime
    def stamp(p):
        return datetime.datetime.fromtimestamp(mtimes.get(p, 0) or 0, datetime.timezone.utc).strftime("%Y-%m-%d")
    urls = [("", "1.0", "weekly"), ("symptoms/", "0.9", "weekly"), ("cheatsheets/", "0.8", "weekly"), ("tutorials/", "0.8", "weekly")]
    urls += [(t["slug"] + "/", "0.8", "monthly") for t in TOPICS]
    urls += [(t["slug"] + "/tutorials/", "0.7", "monthly") for t in TOPICS]
    urls += [("%s/tutorials/%s/" % (tut["topic"], tut["slug"]), "0.7", "monthly") for tut in TUTORIALS]
    body = "".join(
        "  <url>\n    <loc>%s%s</loc>\n    <lastmod>%s</lastmod>\n"
        "    <changefreq>%s</changefreq>\n    <priority>%s</priority>\n  </url>\n"
        % (BASE, path, stamp(path), freq, pri) for path, pri, freq in urls)
    open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % body)
    open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\nDisallow: /build.py\n\nSitemap: %ssitemap.xml\n" % BASE)
    open(os.path.join(OUT, ".nojekyll"), "w").write("")


def build_search_index(idx):
    """One JSON file holding every command, symptom and section on the site.
    At this size a prebuilt index beats any search library: it loads once, on
    first keystroke, and filtering runs in memory."""
    payload = {"v": 1, "e": idx}
    out = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    open(os.path.join(OUT, "search-index.json"), "w", encoding="utf-8").write(out)
    return len(idx), len(out.encode("utf-8"))


def main():
    stats, patterns_all, mtimes, idx = {}, [], {}, []
    totals = dict(cmds=0, patterns=0)

    for t in TOPICS:
        path = os.path.join(ROOT, t["file"])
        if not os.path.exists(path):
            sys.exit("missing sheet: " + t["file"])
        d, u = count_flags(path)
        stats[t["slug"]] = dict(cmds=count_commands(path), destructive=d, uncertain=u, patterns=0)
        mtimes[t["slug"] + "/"] = os.path.getmtime(path)
        totals["cmds"] += stats[t["slug"]]["cmds"]

    # two passes: the per-sheet pages need the site-wide symptom total in their copy
    for t in TOPICS:
        md = open(os.path.join(ROOT, t["file"]), encoding="utf-8").read()
        stats[t["slug"]]["patterns"] = len(parse(md)[3])
        totals["patterns"] += stats[t["slug"]]["patterns"]

    STATS.update(stats)

    for t in TOPICS:
        s = dict(stats[t["slug"]])
        s["patterns"] = totals["patterns"]   # used in the cross-link sentence
        build_topic(t, s, patterns_all, idx)

    build_index(stats, totals)
    build_symptoms(patterns_all, totals)
    build_404()
    # new hubs + tutorials (pSEO: separate hubs keep sheets vs tutorials crawlable)
    build_cheatsheets_hub(stats, totals, idx)
    build_tutorials_hub(idx)
    for slug in [t["slug"] for t in TOPICS] + [p["slug"] for p in PLANNED]:
        build_topic_tutorials(slug, idx)
        mtimes[slug+"/tutorials/"] = os.path.getmtime(os.path.join(ROOT, TOPICS[0]["file"])) if TOPICS else 0
    for tut in TUTORIALS:
        build_tutorial_leaf(tut, idx)
        # use tutorial file mtime for sitemap
        try:
            mtimes[tut["topic"]+"/tutorials/"+tut["slug"]+"/"] = os.path.getmtime(os.path.join(ROOT, tut["file"]))
        except: 
            mtimes[tut["topic"]+"/tutorials/"+tut["slug"]+"/"] = max(mtimes.values()) if mtimes else 0
    newest = max(mtimes.values()) if mtimes else 0
    mtimes[""] = newest
    mtimes["symptoms/"] = newest
    mtimes["cheatsheets/"] = newest
    mtimes["tutorials/"] = newest
    build_meta(mtimes)

    n, size = build_search_index(idx)

    print("built %d topic pages + index + symptom index" % len(TOPICS))
    print("  search:   %d entries, %.1f KB" % (n, size / 1024))
    print("  commands: %d   symptoms: %d" % (totals["cmds"], totals["patterns"]))
    print("  output:   %s" % OUT)


if __name__ == "__main__":
    main()
