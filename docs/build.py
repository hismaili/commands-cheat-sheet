#!/usr/bin/env python3
"""Generate the GitHub Pages site from the cheat sheets themselves.

Run from the repo root:  python3 docs/build.py

Every page here is derived from a topic's own <topic>/<topic>.md — the site
cannot drift from the sheets, and adding a sheet adds a page. Output goes to
docs/ so GitHub Pages can serve it from the main branch (Settings → Pages →
Deploy from a branch → main → /docs).
"""
import html
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
         blurb="Build, run and compose — with every command that destroys state labelled with what exactly it takes down.",
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
         blurb="Apple's system Ruby will not let you write to it, and gem-installed binaries land somewhere PATH has never heard of.",
         kw="gem install user-install macos, GEM_HOME PATH, cocoapods pod command not found, ruby macos system gem",
         related=["mobile", "linux", "web"]),
    dict(slug="api-testing", name="API Testing", file="api-testing/api-testing.md",
         title="curl Commands for API Testing — CORS Preflight and OAuth2 Tokens",
         desc="Field-tested curl commands for API testing: send the OPTIONS preflight a browser would send to read the real Access-Control-Allow headers, and trade credentials for a token via the password grant.",
         blurb="A browser's CORS error tells you nothing. Send the preflight yourself and read what the server actually allows.",
         kw="curl cors preflight options, access-control-allow-origin test, oauth2 password grant curl, curl bearer token api testing",
         related=["vault", "web", "openshift"]),
]
# Directories that exist but hold no recorded sessions yet.
PLANNED = [
    dict(slug="git", name="Git", why="No session has been recorded yet."),
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
    "git":         ("#8194A9", "#5B6675"),
    "kafka":       ("#8194A9", "#5B6675"),
}
SITE_HUE = ("#5B9BF2", "#1D5FB8")


def hue_style(slug=None):
    """A <style> block binding --topic. One hue for a topic page; the whole
    set, class-scoped, for pages that show every sheet at once."""
    if slug:
        d, l = HUES.get(slug, SITE_HUE)
        return ('<style>:root{--topic:%s}:root[data-theme="light"]{--topic:%s}</style>\n' % (d, l))
    rules = [':root{--topic:%s}' % SITE_HUE[0],
             ':root[data-theme="light"]{--topic:%s}' % SITE_HUE[1]]
    for k, (d, l) in HUES.items():
        rules.append('.t-%s{--topic:%s}' % (k, d))
        rules.append(':root[data-theme="light"] .t-%s{--topic:%s}' % (k, l))
    return "<style>" + "".join(rules) + "</style>\n"


BY_SLUG = {t["slug"]: t for t in TOPICS}


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


def render(blocks, cmd_counter):
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
            out.append(
                '<div class="cmd"><div class="cmd__top"><span class="cmd__lang">%s</span>'
                '<button class="copy" type="button">COPY</button></div><pre><code>%s</code></pre></div>'
                % (html.escape(meta), code_html(body)))
        elif kind == "h":
            out.append('<h%d id="%s">%s</h%d>' % (meta, slugify(body), inline(body), meta))
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
    up = "../" if path else ""
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


def masthead(path):
    up = "../" if path else ""
    def cur(p):
        return ' aria-current="page"' if p == path else ""
    return """<header class="masthead"><div class="shell masthead__in">
<a class="wordmark" href="%(up)s"><span class="wordmark__slash">$</span> commands-cheat-sheet</a>
<nav aria-label="Primary">
<a href="%(up)s#sheets"%(s)s>Sheets</a>
<a href="%(up)ssymptoms/"%(sym)s>Symptoms</a>
<a class="opt" href="%(up)s#pipeline">How it is made</a>
<a class="opt" href="%(up)s#ask">Ask</a>
<button class="themetoggle" type="button" data-theme-toggle>PAPER</button>
<a class="btn btn--sm" href="%(gh)s" target="_blank" rel="noopener"><span class="btn__star">&#9733;</span> Star</a>
</nav></div></header>""" % dict(up=up, gh=GH, s="", sym=cur("symptoms"))


def footer(path):
    up = "../" if path else ""
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
<span>Commands recorded on real machines. Nothing here was written from documentation.</span>
<span><a href="%(gh)s" target="_blank" rel="noopener">github.com/%(repo)s</a></span>
</div>
</div></footer>
<script src="%(up)sassets/site.js" defer></script>
</body></html>""" % dict(up=up, gh=GH, repo=REPO, cols=cols)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def build_topic(t, stats, patterns_all):
    md = open(os.path.join(ROOT, t["file"]), encoding="utf-8").read()
    title, intro, sections, patterns = parse(md)
    counter = [0]

    toc = "".join('<li><a href="#%s">%s</a></li>' % (s["id"], html.escape(s["heading"])) for s in sections)
    if patterns:
        toc += '<li><a href="#symptoms">Symptom → move</a></li>'

    body = []
    if intro:
        body.append('<section id="overview">' + render(intro, counter) + "</section>")
    for s in sections:
        body.append('<section id="%s"><h2 id="%s">%s</h2>%s</section>'
                    % (s["id"], s["id"], html.escape(s["heading"]), render(s["blocks"], counter)))

    faq = []
    for sym, move in patterns:
        pid = "q-" + slugify(sym)[:60]
        faq.append(
            '<div class="faq__item" id="%s"><h3 class="faq__q"><a href="#%s">%s</a></h3>'
            '<p class="faq__a">%s</p></div>' % (pid, pid, inline(sym), inline(move)))
        patterns_all.append((t, sym, move, pid))
    if faq:
        body.append(
            '<section id="symptoms"><h2 id="symptoms">Symptom &rarr; move</h2>'
            '<p>Every failure this sheet answers, in the words you would type into a search box. '
            'Deep-link any one of them, or scan <a href="../symptoms/">all %d symptoms across every sheet</a>.</p>'
            '<div class="faq">%s</div></section>' % (stats["patterns"], "".join(faq)))

    rel = "".join(
        '<a class="t-%s" href="../%s/"><b>%s</b><span>%s</span></a>'
        % (BY_SLUG[r]["slug"], BY_SLUG[r]["slug"], BY_SLUG[r]["name"], html.escape(BY_SLUG[r]["blurb"]))
        for r in t["related"] if r in BY_SLUG)

    body.append("""<section id="next">
<h2 id="next">Related sheets</h2>
<p>Sessions rarely stay inside one tool. These are the sheets most often open in the next terminal tab.</p>
<div class="related">%s</div>
<div class="pagecta">
<p><strong>Did this command work for you?</strong> A star tells me which sheets are worth extending. A wrong command deserves an issue — I would rather fix it than have you find out on a live cluster.</p>
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

    page = head(t["title"] + " | commands-cheat-sheet", t["desc"], t["slug"], t["kw"], ld,
                hue=hue_style(t["slug"]))
    page += masthead(t["slug"])
    page += """<main id="main"><div class="shell">
<nav class="crumb" aria-label="Breadcrumb"><a href="../">Cheat sheets</a><span>/</span><span>%(name)s</span></nav>
<div class="topichead">
<p class="eyebrow"><span class="tick">&#9679;</span> %(cmds)d commands &middot; %(pats)d symptoms &middot; traced to source</p>
<h1>%(title)s</h1>
<p class="lede">%(blurb)s</p>
</div>
<div class="doc">
<aside class="toc" aria-label="On this page"><h4>On this page</h4><ul>%(toc)s</ul>
<h4>Other sheets</h4><ul>%(others)s</ul></aside>
<div class="prose">%(body)s</div>
</div></div></main>""" % dict(
        name=html.escape(t["name"]), title=html.escape(title), blurb=html.escape(t["blurb"]),
        cmds=stats["cmds"], pats=len(patterns), toc=toc, body="\n".join(body),
        others="".join('<li><a href="../%s/">%s</a></li>' % (o["slug"], o["name"])
                       for o in TOPICS if o["slug"] != t["slug"]))
    page += footer(t["slug"])

    d = os.path.join(OUT, t["slug"])
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
    return len(patterns), counter[0]


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

    page = head("commands-cheat-sheet — Commands that were run, not written", INDEX_DESC, "",
                "command cheat sheet, oc commands, podman commands, vault commands, linux commands, "
                "devops cheat sheet, field tested commands, destructive command warnings", ld,
                hue=hue_style())
    page += masthead("")
    page += """<main id="main">

<section class="hero"><div class="shell"><div class="hero__grid">
<div>
<p class="eyebrow"><span class="tick">&#9679;</span> %(sheets)d sheets &middot; %(cmds)d commands &middot; %(pats)d symptoms &middot; 0 invented</p>
<h1>These commands were <em>run</em>, not written.</h1>
<p class="lede">%(cmds)d commands lifted from real terminal sessions on real clusters and real machines &mdash; each one traceable to the line it was typed on, and each destructive one labelled with what it actually costs you.</p>
<div class="hero__cta">
<a class="btn" href="%(gh)s" target="_blank" rel="noopener"><span class="btn__star">&#9733;</span> Star the repository</a>
<a class="btn btn--ghost" href="#sheets">Open a cheat sheet</a>
</div>
<p class="hero__meta">Free, MIT-ish, no signup, no tracking. Works fine at 2am.</p>
</div>

<div class="record">
<div class="record__bar"><span class="record__dot"></span> Record &mdash; openshift / finalizers</div>
<div class="record__row">
<span class="record__k">Symptom</span>
<p class="record__symptom">Namespace has sat in <code>Terminating</code> for forty minutes and will not go.</p>
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
<span class="record__k">What it costs you</span>
<p>Orphans every resource the app managed. ArgoCD stops tracking them and will never prune or reconcile them again. Delete the workload properly first if you can.</p>
</div>
<hr class="perf">
<div class="record__trace">
<b>Traced</b> <span>_sources/openshift/2026-08-21-argocd-logging-storage.txt</span>
</div>
</div>

<div class="tally">
<div><b>%(sheets)d</b><span>Sheets</span></div>
<div><b>%(cmds)d</b><span>Commands</span></div>
<div><b>%(pats)d</b><span>Symptoms answered</span></div>
<div><b>0</b><span>Invented</span></div>
</div>

</div></div></section>

<section class="band" id="why"><div class="shell">
<div class="band__head">
<p class="eyebrow">Why this exists</p>
<h2>The command you need already worked once. You just cannot find it.</h2>
</div>
<div class="acts">

<div class="act">
<div class="act__label">The problem</div>
<div>
<h3>Search gives you documentation, not experience.</h3>
<p>Something is broken and you have maybe ten minutes. What comes back is the official reference reprinted by a content farm, a confidently wrong answer with syntax that has never existed, and a thread from 2019 about a version you are not running.</p>
<p>The command that actually fixed this last time was in a scrollback buffer you closed three months ago.</p>
</div>
</div>

<div class="act">
<div class="act__label">What it costs</div>
<div>
<h3>The dangerous commands are the ones that look scoped.</h3>
<p>Untested commands rarely fail loudly. They fail quietly, and later, and somewhere else.</p>
<p class="act__quote">oc delete crd applications.argoproj.io<br><span style="color:var(--hazard)">&rarr; deletes every ArgoCD Application on the cluster, in every namespace. There is no per-namespace opt-out.</span></p>
<p>The page you copied that from did not tell you, because nobody who wrote it had run it anywhere that mattered. Same story for <code>podman rm -a</code>, which removes every stopped container on the host rather than the one you were debugging, and <code>sudo fuser -k &lt;PORT&gt;/tcp</code>, which kills whatever holds the port with no graceful shutdown and no prompt.</p>
</div>
</div>

<div class="act act--solve">
<div class="act__label">What this is</div>
<div>
<h3>%(sheets)d sheets, %(cmds)d commands, every one of them traceable.</h3>
<p>Each command here came out of a recorded terminal session and carries a reference back to the dump line it was typed on. Commands that cannot be traced never make it onto the page &mdash; that rule is enforced by a pipeline, not by good intentions.</p>
<p>Where a command is strange but worked, it is kept and flagged rather than quietly corrected: <a href="ruby/">a <code>sudo gem install --user-install</code> whose flags contradict each other</a> is still what ran successfully on the machine it was recorded from. Where a command destroys something, the sheet says exactly what.</p>
<p><a href="#sheets">Start with a sheet</a>, or go straight to <a href="symptoms/">the symptom index</a> if you already know what is broken.</p>
</div>
</div>

</div>
</div></section>

<section class="band band--sunk" id="sheets"><div class="shell">
<div class="band__head">
<p class="eyebrow">The sheets</p>
<h2>Pick the tool that is currently lying to you.</h2>
<p class="lede">Every sheet opens with the failure it exists to answer, then the commands, then a symptom-to-move table you can scan in a hurry.</p>
</div>
<div class="sheets">%(sheets_html)s%(planned)s</div>
<p style="margin-top:1.5rem;font-size:.92rem;color:var(--muted)">Looking for something specific? <a href="symptoms/">All %(pats)d symptoms across every sheet, on one page</a>.</p>
</div></section>

<section class="band" id="pipeline"><div class="shell">
<div class="band__head">
<p class="eyebrow">How a sheet is made</p>
<h2>Four stages, and a command can only survive all four by being real.</h2>
<p class="lede">This is a genuine sequence &mdash; each stage can only run on the output of the one before it, and the third stage physically cannot emit a command the second one did not record.</p>
</div>
<div class="pipe">
<div class="pipe__step"><span class="pipe__n">STAGE 1</span><h3>Record</h3><p>A real working session is dumped to <code>_sources/</code>. Those dumps hold live tokens and hostnames, so they are gitignored and never leave the machine.</p></div>
<div class="pipe__step"><span class="pipe__n">STAGE 2</span><h3>Extract</h3><p>Each command is structured into <code>commands.yml</code> with a <code>source_ref</code> pointing at its dump line. Credentials and identifiers are replaced here, once, at the only stage that reads raw source.</p></div>
<div class="pipe__step"><span class="pipe__n">STAGE 3</span><h3>Write</h3><p>The sheet is generated from that file alone. No <code>source_ref</code>, no output &mdash; which is why a plausible-sounding command that nobody ran cannot appear.</p></div>
<div class="pipe__step"><span class="pipe__n">STAGE 4</span><h3>Audit</h3><p>A reviewer reads the raw dump rather than a summary and diffs it against the sheet in both directions: invented commands and dropped ones. It reports; it never rewrites a working command.</p></div>
</div>
<p style="margin-top:1.5rem;font-size:.92rem;color:var(--muted)">The pipeline is its own open-source project &mdash; <a href="https://github.com/hismaili-awesome-ai/cheatsheet-forge" target="_blank" rel="noopener">cheatsheet-forge</a> &mdash; if you want to run it against your own recorded sessions.</p>
</div></section>

<section class="band band--sunk" id="ask"><div class="shell">
<div class="ask">
<div>
<p class="eyebrow">Ask</p>
<h2>Stuck on something that is not here yet?</h2>
<p class="lede">Ask it as an issue. If the answer exists in a session I have recorded, it becomes a new entry on the relevant sheet, with its trace attached like everything else.</p>
<p style="font-size:.93rem;color:var(--ink-2)">Three things that always get a reply:</p>
<ul style="font-size:.93rem;color:var(--ink-2);padding-left:1.1rem">
<li><strong>A command here did not work.</strong> That is a defect and I want it.</li>
<li><strong>A command here is dangerous and not labelled.</strong> That is the worst kind of bug on this site.</li>
<li><strong>A technology you want covered.</strong> Requests decide what gets recorded next.</li>
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
<p class="form__note">This fills in a GitHub issue and opens it in a new tab &mdash; nothing is sent anywhere until you press submit there. No form data touches this site; there is no backend and no analytics.</p>
</form>
</div>
</div></section>

<section class="band"><div class="shell">
<div class="endcta">
<p class="eyebrow">One click</p>
<h2>If one command here saved you an hour, star it.</h2>
<p class="lede" style="margin-inline:auto">Stars are the only signal I get about which sheets are worth extending. There is no analytics on this site, so the alternative is guessing.</p>
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


INDEX_DESC = ("Cheat sheets for OpenShift, Linux, Podman, Vault, OCI, npm, Flutter, Ruby and curl "
              "built only from recorded terminal sessions. Every command traces back to the line it was "
              "typed on, and every destructive one says what it actually costs you.")


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
    page += """<main id="main"><div class="shell">
<nav class="crumb" aria-label="Breadcrumb"><a href="../">Cheat sheets</a><span>/</span><span>Symptom index</span></nav>
<div class="topichead">
<p class="eyebrow"><span class="tick">&#9679;</span> %(n)d symptoms &middot; %(t)d technologies &middot; one page</p>
<h1>Start from what is broken.</h1>
<p class="lede">You rarely arrive knowing which tool is at fault &mdash; you arrive with an error message. This is every symptom the sheets answer, grouped by technology, each one linking straight to the command that resolves it.</p>
</div>
<nav class="jump" aria-label="Jump to a technology">%(jump)s</nav>
%(groups)s
<div class="pagecta">
<p><strong>Your symptom is not on this list?</strong> Open it as a question. If a recorded session covers it, it becomes a new entry here.</p>
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
                "That page does not exist. Every cheat sheet is listed here.", "",
                hue=hue_style())
    page += masthead("")
    page += """<main id="main"><div class="shell"><div class="topichead" style="padding-top:5rem">
<p class="eyebrow">404</p>
<h1>No such page.</h1>
<p class="lede">Nothing at that address. Here is everything that does exist.</p>
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
    urls = [("", "1.0", "weekly"), ("symptoms/", "0.9", "weekly")]
    urls += [(t["slug"] + "/", "0.8", "monthly") for t in TOPICS]
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


def main():
    stats, patterns_all, mtimes = {}, [], {}
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

    for t in TOPICS:
        s = dict(stats[t["slug"]])
        s["patterns"] = totals["patterns"]   # used in the cross-link sentence
        build_topic(t, s, patterns_all)

    build_index(stats, totals)
    build_symptoms(patterns_all, totals)
    build_404()
    newest = max(mtimes.values()) if mtimes else 0
    mtimes[""] = newest
    mtimes["symptoms/"] = newest
    build_meta(mtimes)

    print("built %d topic pages + index + symptom index" % len(TOPICS))
    print("  commands: %d   symptoms: %d" % (totals["cmds"], totals["patterns"]))
    print("  output:   %s" % OUT)


if __name__ == "__main__":
    main()
