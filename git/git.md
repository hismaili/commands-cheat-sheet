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

## Rewriting pushed history starts with a backup

Rewriting commits that have already been pushed replaces history on the remote — the old commits become unreachable. Someone who already pulled the old history will have to reset onto the new one. Start from a clean state and keep a branch you can reset to.

```bash
# Fetch everything and confirm the working tree is clean
git fetch --all
git status  # must be clean — commit or stash pending changes first

# Keep a branch you can reset to if the rewrite goes wrong
git branch backup-before-rewrite

# Inspect recent history and which remote the branch tracks
git log --oneline --graph --all -10
git branch -vv
git log --oneline origin/<BRANCH>..HEAD  # commits not yet on origin
git log --oneline -10                    # pick hashes you want to reword
```

Check `git remote -v` first if you have two remotes — the remote you push to later determines which upstream loses the old commits.

---

## Rewording commits that have already been pushed

Pick the scenario that matches how far back the message to fix is. Local rebase changes only local history; the remote only changes when you force-push.

```bash
# Scenario A — only the last pushed commit: amend the message in place
git commit --amend -m "<MESSAGE>"
git log --oneline -3  # verify new message
```

```bash
# Scenario B — last N commits (e.g. last 3): interactive rebase
git rebase -i HEAD~3
# editor opens — replace pick with reword (or r) for each commit to edit:
# pick a1b2c3 old message 1
# reword d4e5f6 old message 2
# reword 789abc old message 3
# save and close → Git opens a message editor for each reword sequentially
```

```bash
# Scenario C — older commits / all commits of branch: rebase onto remote base or a hash
git rebase -i origin/<BRANCH>
# or: rebase onto parent of oldest commit to reword
git rebase -i <HASH>^
```

If a rebase conflicts:

```bash
# fix files, then continue; abort anytime to return to pre-rebase state
git add .
git rebase --continue
git rebase --abort
```

---

## Replacing the remote branch — force-with-lease to one remote only

A rebase rewrites local history. The `push` you choose determines what gets overwritten on the remote; the other remote stays untouched. Prefer `--force-with-lease` — it refuses if someone else pushed since your last fetch.

```bash
# Push the rewritten branch to one explicitly named remote
git push --force-with-lease <REMOTE> <BRANCH>
# explicit refspec — same result
git push --force-with-lease <REMOTE> HEAD:<BRANCH>
```

**Consequence —** `--force-with-lease` (and `--force`) removes the old commits from the targeted remote branch. They remain dangling on the server until garbage collection and may still resolve by hash for a few hours, but they are no longer reachable from the branch.

```bash
# Two remotes: origin is your fork, second is the upstream / client
# overwrite ONLY origin, upstream keeps old history
git push --force-with-lease origin <BRANCH>

# overwrite ONLY second remote
git push --force-with-lease second <BRANCH>

# Do NOT use when you want to target one remote only:
# git push --all --force  ← pushes to every remote
```

Before pushing, check whether an unqualified `git push` would hit both remotes:

```bash
# does pushDefault or multiple push URLs fan out silently?
git config --get-regexp push
git config --get-regexp remote
```

---

## Verifying the rewrite, cleaning up, and recovering

Confirm the remote now points at the new history. Code should be identical — only messages changed.

```bash
# Verify the targeted remote
git fetch <REMOTE>
git log --oneline origin/<BRANCH> -10
git log --oneline second/<BRANCH> -10  # compare second remote if it exists
git diff backup-before-rewrite --stat  # should show no code diff, only messages
```

If verified, delete the backup:

```bash
git branch -D backup-before-rewrite
```

**Consequence —** `-D` deletes the branch even if it is not fully merged. The reflog still holds the old history for a while, but the named recovery point is gone.

If something went wrong, restore from the backup or the reflog, then force-push the restoration:

```bash
# Find previous HEAD if you no longer have the backup branch
git reflog

# Restore local branch and restore the remote
git reset --hard backup-before-rewrite
git push --force-with-lease <REMOTE> <BRANCH>

# or abort an ongoing rebase
git rebase --abort
```

**Consequence —** `git reset --hard` discards all commits and uncommitted changes on the current branch after the target. Nothing is staged, nothing is stashed — it is replaced.

What collaborators who already pulled the old history must do — `pull` will merge old and new into a duplicate:

```bash
# For teammates who already pulled old history
git fetch --all
git checkout <BRANCH>
git reset --hard origin/<BRANCH>
```

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
| Need to rewrite a commit message already pushed | `git commit --amend -m "<MESSAGE>"` for last commit; `git rebase -i HEAD~<N>` for last N, `git rebase -i origin/<BRANCH>` for older — then force-push |
| Rebase conflicts mid-rewrite | Fix files, `git add . && git rebase --continue`; abort with `git rebase --abort` |
| Rewritten history must replace only one remote | `git push --force-with-lease <REMOTE> <BRANCH>` (or `HEAD:<BRANCH>`) — never `git push --all --force` |
| Unsure whether `git push` will hit both remotes | `git config --get-regexp push` and `git config --get-regexp remote` |
| Rewrite pushed history safely | `git fetch --all && git branch backup-before-rewrite` before rebase; verify with `git fetch <REMOTE> && git log --oneline origin/<BRANCH> -10` |
| Verify rewrite kept code identical | `git diff backup-before-rewrite --stat` (no code diff, only messages); `git log --oneline --graph --all -10` |
| Recovery after a bad rewrite | `git reflog` → `git reset --hard backup-before-rewrite` → `git push --force-with-lease <REMOTE> <BRANCH>` |
| Collaborator already pulled old history | They must `git fetch --all && git checkout <BRANCH> && git reset --hard origin/<BRANCH>` — not `git pull` |
| Which commits are not yet on the remote | `git log --oneline origin/<BRANCH>..HEAD` and `git branch -vv` |
