# Git Cheat Sheet

A push that goes to the wrong place, or comes back refused, is almost never one problem. Three independent layers have to line up, and each one fails with a different symptom:

1. **Commit identity** — the name and email git stamps on a commit (`user.name` / `user.email`). Nothing checks it. It is metadata, and it can be wrong on every commit while pushes succeed.
2. **SSH authentication** — which key SSH offers, and therefore which provider account you are. This is what `ssh -T` answers: *I am GitHub user X.*
3. **Organization authorization** — whether that account's key is allowed to reach a particular org's repositories. Under SAML SSO this is a second, separate gate, and passing gate 2 tells you nothing about it.

Identity belongs to the project. Authentication belongs to the account. The remote URL connects the two.

---

## Which repository am I standing in?

Most wrong-identity pushes are explained by being in a different repository than you thought. Establish the ground truth before touching any configuration.

```bash
# Print the root of the repository you are actually in
git rev-parse --show-toplevel

# Working tree state of that repository
git status

# The branch you are about to push somewhere named
git branch --show-current
```

---

## One folder, two repositories

A single working directory and a single `.git` can serve two upstreams — no duplicated folder, no deleting `.git`. Give each remote a meaningful name (`personal`, `company`) rather than a positional one, and every push becomes a deliberate choice of destination.

```bash
# Orientation: every remote with its fetch and push URLs
git remote -v

# Attach a second repository as an independently named remote
git remote add <REMOTE> git@github.com:<ORG>/<REPO>.git

# Same, but routed through a per-account SSH host alias so this
# upstream authenticates with its own key
git remote add <REMOTE> git@<SSH_ALIAS>:<ORG>/<REPO>.git

# Push one branch to one explicitly chosen remote
git push <REMOTE> <BRANCH>
```

Named remotes plus per-account aliases is the recommended setup when the two repositories belong to different GitHub accounts — it is what stops company code from landing in a personal repository by reflex.

---

## One push, two destinations

When the two repositories are mirrors rather than different projects, a single remote can carry several push URLs and fan out on every `git push`.

```bash
# Add an additional push URL to one remote (run once per destination)
git remote set-url --add --push <REMOTE> git@github.com:<ORG>/<REPO>.git
```

**Consequence —** the first `--add --push` on a remote displaces the implicit push URL, so adding only the new destination silently stops pushing to the original repository. Add the original as an explicit push URL too — it just has to be there, before or after the new one. Fetch URLs and push URLs are separate concepts, so `git pull` is unaffected and keeps using the single fetch URL. Confirm the fan-out actually reaches every destination with `git remote get-url --all --push <REMOTE>`.

---

## Reading what the remotes are actually set to

`git remote -v` is a summary. When it does not explain the behaviour you are seeing, read the configuration directly.

```bash
# Every push URL attached to a remote — confirms a fan-out really fans out
git remote get-url --all --push <REMOTE>

# One remote's URL — reveals whether it goes through a plain host or an alias
git remote get-url <REMOTE>

# The complete remote section of git config, fetch and push URLs included
git config --get-regexp '^remote\.'
```

---

## Git commits under the wrong name

This is layer one, and it is entirely local. A global identity is a fine default, but it must stop being authoritative the moment a second account exists — the absence of `--global` below is the whole point.

```bash
# What every repository is silently inheriting
git config --global --list

# Set the commit author for THIS repository only
git config user.name "<NAME>"
git config user.email "<EMAIL>"

# Confirm the local values actually landed instead of falling through to global
git config --local --list

# The effective identity — what git will stamp on the next commit, wherever it came from
git config user.name
git config user.email

# Prove it was used: author name and email on the latest commit
git log -1 --format='%an <%ae>'
```

---

## Setting identity per repository does not scale

Once there are many repositories, configuring each one by hand is repetitive and easy to forget. Git can make identity depend on the directory the repository lives in, via `includeIf` — configuration, not a command.

In `~/.gitconfig`:

```ini
[includeIf "gitdir:~/Projects/work/"]
    path = ~/.gitconfig-work

[includeIf "gitdir:~/Projects/personal/"]
    path = ~/.gitconfig-personal
```

Then `~/.gitconfig-work`:

```ini
[user]
    name = <NAME>
    email = <WORK_EMAIL>
```

And `~/.gitconfig-personal`:

```ini
[user]
    name = <NAME>
    email = <PERSONAL_EMAIL>
```

The trailing slash on the `gitdir:` pattern matters — it is what makes the rule apply to everything beneath that directory.

---

## Two accounts on the same provider

This is layer two. `github.com` can only mean one account to a bare SSH connection, so give each account its own key and its own host alias. The alias is a routing rule, not a real hostname.

```bash
# One dedicated key per account, at a named path
ssh-keygen -t ed25519 \
  -C "<EMAIL>" \
  -f ~/.ssh/<KEY_NAME>
```

Repeat once per account. Only the `.pub` file is registered with the provider; the private key never leaves the machine. `ssh-keygen` prompts before overwriting an existing `-f` path.

Then, in `~/.ssh/config`:

```ssh-config
Host github-personal
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github_personal
    IdentitiesOnly yes

Host github-work
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github_work
    IdentitiesOnly yes

Host gitlab-work
    HostName gitlab.com
    User git
    IdentityFile ~/.ssh/id_ed25519_gitlab_work
    IdentitiesOnly yes
```

`github-personal`, `github-work`, `gitlab-work`, and the `id_ed25519_*` key files are one concrete instantiation of the `<SSH_ALIAS>` and `<KEY_NAME>` placeholders used throughout this sheet — pick your own alias names and key filenames, one pair per account.

`IdentitiesOnly yes` is the line that makes this deterministic. Without it the SSH agent may offer several keys, and the provider authenticates you as whichever one it accepts first — which is how you end up as the wrong account despite "correct" configuration. With it, the alias uses that identity and nothing else.

---

## The remote still points at the bare host

An alias only takes effect if the remote URL names it. `github-work`, not `github.com`, in the host segment.

```bash
# Repoint an existing remote onto a per-account SSH host alias
git remote set-url <REMOTE> git@<SSH_ALIAS>:<ORG>/<REPO>.git
```

**Consequence —** this rewrites `remote.<REMOTE>.url` — the fetch URL, and the push URL *only while no explicit push URL exists*. If this remote already carries push URLs added with `git remote set-url --add --push` (the previous section), those `remote.<REMOTE>.pushurl` entries are untouched: fetches move to the alias, but pushes keep going to whatever the old push URLs pointed at. A repoint that looks successful can leave every push still crossing the bare host. Confirm with `git remote get-url --all --push <REMOTE>` after repointing — not just `git remote get-url`. The alias segment that must match a `Host` entry in `~/.ssh/config` is `github-work`, not `github.com`.

---

## SSH connects — but as which account?

Ask the provider who you are before you push. If the wrong account answers, the key is bound to the wrong identity and nothing further is worth trying.

```bash
# Which account does this alias authenticate as?
ssh -T git@<SSH_ALIAS>

# Same test, verbose — shows which identity file SSH actually offered
ssh -vT git@<SSH_ALIAS>

# Effective config for an alias, without opening a connection:
# real hostname, user, identity file, IdentitiesOnly
ssh -G git@<SSH_ALIAS> | grep -E 'hostname|user|identityfile|identitiesonly'
```

In the verbose output, look for the `Offering public key:` line. ssh prints the absolute path there, never a `~/` shorthand, so match on the key filename (`<KEY_NAME>`) rather than a tilde form that will never appear.

A success line — `Hi <GITHUB_USER>! You've successfully authenticated...` — proves **identity only**. It does not prove access to any repository or any organization. That is the next section.

---

## SSH works but the organization still says no

Layer three. The SSH chain (repository → alias → key → account) can be entirely correct and the push still fails:

```
ERROR: The '<ORG>' organization has enabled or enforced SAML SSO.
To access this repository, you must use the HTTPS remote with a personal access token
or SSH with an SSH key and passphrase that has been authorized for this organization.
```

SSH authentication and organization authorization are different claims. The key proves *I am GitHub user X*; SAML SSO must additionally establish *GitHub user X is authorized for organization Y*. Do not switch protocols because of this error — SSH remains the cleanest approach for a multi-account workstation, and the HTTPS path has the same second gate, just with a different credential.

```bash
# Can the configured remote be reached? Refs coming back means
# authentication AND repository authorization both work
git ls-remote <REMOTE>

# Test one specific repository by full URL, bypassing local remote config
git ls-remote git@<SSH_ALIAS>:<ORG>/<REPO>.git

# Only now, with every layer confirmed
git push
```

`ssh -T` succeeding while `git ls-remote` returns the SAML error is the signature of an unauthorized key: it is registered with the account but not authorized for the organization. **The fix is on GitHub, not in git or ssh** — Settings → SSH and GPG keys, find the key this repository uses, and use the organization's SSO authorization control. Registering a public key with GitHub does not authorize it for an org; you need both.

If the organization does not appear in that list, establish the SAML session first by visiting `https://github.com/orgs/<ORG>/sso`, authenticate through the corporate identity provider, then re-check the key's SSO authorization. The exact flow depends on the organization's identity-provider configuration.

---

## HTTPS instead of SSH: tokens and the Keychain

The HTTPS path has its own credential layer. Knowing whether it is even involved saves a lot of wasted deletion.

```bash
# Which credential helper is git using?
git config --global credential.helper

# Clone over HTTPS — supply the GitHub username and a personal access
# token as the password, never the account password
git clone https://github.com/<ORG>/<REPO>.git
```

`osxkeychain` serves the **HTTPS path only**. It has no part in SSH authentication, so clearing Keychain entries will never fix an SSH or SAML failure. For a SAML-enforcing organization the token must additionally be authorized for that organization.

```bash
# Drop the cached GitHub credential so the next HTTPS operation re-prompts
git credential-osxkeychain erase
```

**Consequence —** the stored credential is deleted. If the token was not saved elsewhere it has to be reissued.

**Uncertain — invocation left as written:** the command reads its target from stdin. After running it you type `protocol=https`, then `host=github.com`, then an empty line. The source records those lines as prose rather than as part of the invocation, so a bare copy-paste appears to hang while it waits on stdin. Kept unmodified. The GUI equivalent is removing the `github.com` Internet Password entry in Keychain Access.

---

## When a push fails, walk the chain

Do not start deleting credentials at random. Go left to right; the first step that disagrees with your expectation is the bug.

1. **Which repository am I in?** — `git rev-parse --show-toplevel`
2. **Which remote am I using?** — `git remote -v`
3. **Which commit identity will git use?** — `git config user.name` and `git config user.email`
4. **Which SSH host alias is in the URL?** — `git remote get-url origin`, expecting `git@<SSH_ALIAS>:...` and not `git@github.com:...` when multiple accounts are in play
5. **Which key is actually offered?** — `ssh -vT git@<SSH_ALIAS>`
6. **Can that account reach the repository?** — `git ls-remote origin`
7. Only then — `git push`

---

## Key Patterns

| Symptom | Move |
|---|---|
| Push went to the wrong upstream | `git remote -v`, then push by name: `git push <REMOTE> <BRANCH>` |
| Same folder needs two upstreams | `git remote add <REMOTE> git@<SSH_ALIAS>:<ORG>/<REPO>.git` per destination |
| One push should hit two mirrors | `git remote set-url --add --push <REMOTE> …` once per URL, original included first |
| Fan-out push only reaches one repo | `git remote get-url --all --push <REMOTE>` — the original URL was probably never added explicitly |
| `git remote -v` doesn't explain the behaviour | `git config --get-regexp '^remote\.'` |
| Commits carry the wrong name/email | `git config user.name`/`user.email` locally (no `--global`), verify with `git config --local --list` |
| Wrong identity keeps coming back after being set | It is inherited: `git config --global --list` |
| Did the identity actually get used? | `git log -1 --format='%an <%ae>'` |
| Setting identity per repo doesn't scale | `[includeIf "gitdir:~/Projects/work/"]` in `~/.gitconfig` |
| Two accounts on one provider | One key per account (`ssh-keygen -t ed25519 -f ~/.ssh/<KEY_NAME>`) + a `Host` alias each |
| SSH authenticates as the wrong account | `IdentitiesOnly yes` on the alias; confirm with `ssh -vT git@<SSH_ALIAS>` |
| Alias configured but ignored | The remote URL still names the bare host — `git remote set-url <REMOTE> git@<SSH_ALIAS>:…` |
| Repointed onto an alias, but pushes still cross the bare host | `set-url` only rewrites the fetch URL when a `pushurl` already exists — check with `git remote get-url --all --push <REMOTE>` |
| Need the alias's real target without connecting | `ssh -G git@<SSH_ALIAS> \| grep -E 'hostname\|user\|identityfile\|identitiesonly'` |
| `ssh -T` succeeds, repository access denied | Authorization, not authentication — `git ls-remote git@<SSH_ALIAS>:<ORG>/<REPO>.git` to confirm, fix in GitHub SSO settings |
| SAML org missing from the SSO authorization list | Establish the session at `https://github.com/orgs/<ORG>/sso` first, then re-check the key |
| Chasing an SSH failure through the Keychain | Wrong layer — `git config --global credential.helper` serves HTTPS only |
| Stale HTTPS credential cached | `git credential-osxkeychain erase` (deletes it; token may need reissuing) |
| HTTPS clone rejects the password | It wants a personal access token, and for a SAML org one authorized for that org |
