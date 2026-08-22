# Linux Cheat Sheet

## Shell Environment — PATH Configuration

A newly installed tool's executables are invisible to the shell until its `bin/` directories are on `PATH`. The fix is two steps that must be done together: export the layered install-root variables and prepend their `bin/` paths, then persist that into the shell profile — an `export` alone only lives for the current shell session and vanishes the moment it closes.

```bash
# 1. Register the tool's install root (and nested version/package roots) as
#    env vars, then prepend each bin/ dir onto PATH for THIS shell only
export <TOOL_HOME>=$HOME/<TOOL_DIR>
export <TOOL_VERSION_HOME>=$<TOOL_HOME>/<TOOL_SUBPATH>
export <TOOL_PACKAGE_HOME>=$<TOOL_VERSION_HOME>/<PACKAGE_SUBPATH>
export PATH=$<TOOL_HOME>/bin:$<TOOL_VERSION_HOME>/bin:$<TOOL_PACKAGE_HOME>/bin:$PATH

# 2. Persist it — without this, the exports above are gone on next login/shell
vi <USER_HOME>/.bash_profile
```

## Process Management

A port refusing to bind almost always means a leftover process is still holding it.

```bash
# Find and kill whatever process is listening on PORT
sudo fuser -k <PORT>/tcp
```

**Destructive: `fuser -k` force-kills whatever process holds that port — not necessarily the one you intended — with no confirmation prompt and no graceful shutdown.** It sends the kill signal to every PID bound to that port, so buffers aren't flushed and locks aren't released cleanly. Confirm what actually owns the port (`sudo lsof -i :<PORT>`, see Port Inspection below) before running this if the wrong process dying would matter.

## Package Management

`yum` prompts for confirmation by default, which is exactly what breaks unattended provisioning scripts. `-y` is what turns an interactive package manager into something scriptable.

```bash
# Update every installed package to its latest available version
sudo yum update -y

# Install one or more packages, no confirmation prompt
sudo yum install -y <PACKAGES>
```

## Directory & Ownership Setup

A deploy that runs as root creates files root owns — and the non-root user who has to `docker-compose up` afterward can't write into them. Create the tree as root, then hand ownership to the user who will actually operate it.

```bash
# Create the app directory tree (and any missing parents)
sudo mkdir -p <USER_HOME>/app/docker-compose

# Hand ownership to the deploying user so it can write without sudo
sudo chown <USER>:<USER> <USER_HOME>/app/docker-compose
```

## Service Logging & Management (journalctl / systemctl)

System services and user services live in two separate systemd instances, and mixing up which one you're talking to is the usual cause of "I enabled it but it's not running." System units need `sudo`; user units run under the invoking user's own systemd and never do.

```bash
# System service — follow its journal in real time (needs sudo)
sudo journalctl -u <SYSTEM_SERVICE> -f

# User service — pick up new/changed unit files in ~/.config/systemd/user
systemctl --user daemon-reload

# User service — enable on login and start it now, in one shot
systemctl --user enable --now <USER_SERVICE>

# User service — follow its journal in real time (no sudo)
journalctl --user -u <USER_SERVICE> -f
```

## Port Inspection

Before killing whatever is bound to a port, find out what it actually is.

```bash
# List the process(es) bound to a TCP/UDP port
sudo lsof -i :<PORT>
```

## Key Patterns

| Symptom | Move |
|---|---|
| New tool's command not found after install | Export its install-root vars and prepend `bin/` dirs onto `PATH` |
| PATH export disappears in a new terminal/session | Add the same exports to `.bash_profile` so they persist |
| Service won't start: "address already in use" | `sudo lsof -i :<PORT>` to identify the holder, then `sudo fuser -k <PORT>/tcp` — it kills without asking, confirm first |
| Provisioning script hangs on a yum prompt | Add `-y` to `yum update`/`yum install` |
| Non-root user can't write into a freshly created app dir | `sudo mkdir -p` then `sudo chown <USER>:<USER>` the directory |
| `systemctl --user enable` "worked" but service isn't running | Check you're not confusing it with a system unit — user units need `systemctl --user` / `journalctl --user`, not `sudo` |
| New `--user` unit file isn't picked up | `systemctl --user daemon-reload` before `enable --now` |
