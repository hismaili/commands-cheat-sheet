# Podman

## Build

Podman builds from a Dockerfile/Containerfile in the working directory. Use `--format docker` when a downstream registry or tool insists on Docker image format rather than Podman's OCI default.

```bash
# Build from the Containerfile/Dockerfile in the current directory
podman build -t <APP_IMAGE> .

# Build in Docker image format with an explicit version tag
podman build --format docker -t <APP_IMAGE>:<VERSION> .
```

## Run

Detached runs keep the shell free; `--rm` is for throwaway containers, while a named, non-`--rm` run is what you want once you're injecting config through env vars and expect to `logs`/`exec` into it later.

```bash
# Run detached, auto-remove on exit, publish a port
podman run --rm -d -p <PORT>:80 --name <APP_CONTAINER> <APP_IMAGE>

# Run detached (no auto-removal), inject env vars, use a versioned image
podman run -d --name <APP_CONTAINER> -p <PORT>:80 -e API_URL=<API_URL> -e KEYCLOAK_URL=<KEYCLOAK_URL> <APP_IMAGE>:<VERSION>
```

## Compose

`podman compose up -d` is the safe day-to-day start command. `down` and `--force-recreate` both destroy running state — reach for them only when you actually want a clean slate.

```bash
# Start compose-defined services detached
podman compose up -d
```

**`podman compose down`** — **destructive**: stops and removes every container and network defined by the compose file in the current directory. Anything not persisted in a volume (in-memory state, unsaved data) is gone.

```bash
podman compose down
```

**`podman-compose up -d --build --force-recreate`** — **destructive**: rebuilds images and tears down/recreates every compose container regardless of whether config or image actually changed, discarding current container state (in-container writes, non-persisted data) even for services that didn't need it.

```bash
podman-compose up -d --build --force-recreate
```

## Inspect

When you don't know which container owns a port, or whether a process inside it is actually alive, these are read-only — safe to run against production without side effects.

```bash
# View logs of a running/stopped container
podman logs <VAULT_CONTAINER>

# List processes running inside a container
podman exec <VAULT_CONTAINER> ps aux

# List all containers (running or stopped) filtered by name
podman ps -a --filter name=<VAULT_CONTAINER>

# Find a running container by published port
podman ps | grep <PORT>
```

## Manage

Bulk stop/remove commands act on *every* container on the host with no per-container confirmation — they don't distinguish yours from anyone else's on a shared machine.

**`podman stop -a`** — **destructive**: stops every running container on the host, not just the one you're working on. Anything else running there goes down too.

```bash
podman stop -a
```

**`podman rm -a`** — **destructive**: removes every stopped container on the host. Container filesystems and metadata for all of them are deleted; only bind-mounted or externally-managed data survives.

```bash
podman rm -a
```

**`podman rm -f <VAULT_CONTAINER>`** — **destructive**: force-removes a specific container even while it's still running, killing it first with no graceful shutdown. In-flight requests and unflushed writes to the container's own filesystem are lost.

```bash
podman rm -f <VAULT_CONTAINER>
```

## Key Patterns

| Symptom | Move |
|---|---|
| Need an image built from local source | `podman build -t <APP_IMAGE> .` |
| Registry/tool rejects OCI-format image | `podman build --format docker -t <APP_IMAGE>:<VERSION> .` |
| Want a disposable container that cleans itself up | `podman run --rm -d -p <PORT>:80 --name <APP_CONTAINER> <APP_IMAGE>` |
| Need a long-lived container with config injected | `podman run -d --name <APP_CONTAINER> -p <PORT>:80 -e ... <APP_IMAGE>:<VERSION>` |
| Bring up the whole compose stack | `podman compose up -d` |
| Tear down the compose stack entirely | `podman compose down` (destructive) |
| Compose containers stuck on stale image/config | `podman-compose up -d --build --force-recreate` (destructive) |
| Container crash-looping, need the story | `podman logs <VAULT_CONTAINER>` |
| Unsure what's actually running inside a container | `podman exec <VAULT_CONTAINER> ps aux` |
| Can't remember a container's exact name | `podman ps -a --filter name=<VAULT_CONTAINER>` |
| Know the port, not the container | `podman ps \| grep <PORT>` |
| Need everything on the host stopped, right now | `podman stop -a` (destructive) |
| Need a clean container slate on the host | `podman rm -a` (destructive) |
| One container won't die gracefully | `podman rm -f <VAULT_CONTAINER>` (destructive) |
