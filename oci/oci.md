# Oracle Cloud Infrastructure (OCI) Cheat Sheet

Two failure modes dominate day-one OCI work: the CLI is not on the box, or the key that should get you into a compute instance gets rejected. Both have a fixed, three-step fix.

---

## OCI CLI — Setup

**Install, confirm the binary actually landed, then run the wizard that writes `~/.oci/config`.** Skipping the version check just moves the failure one step later, into `oci setup config`.

```bash
# Install the CLI
brew install oci-cli

# Confirm it installed and check its version
oci --version

# Interactive wizard — API key, tenancy/user OCIDs, region
oci setup config
```

---

## OCI — SSH Access

**A rejected key is almost always permissions, not the key itself.** `ssh` silently ignores private keys that are group- or world-readable — `chmod` both halves of the pair before you blame the key.

```bash
# Set connection variables and connect
export oci_vm_ip=<HOST_IP>
export username=opc
export private_key_file=<PRIVATE_KEY_FILE>
ssh -i $private_key_file $username@$oci_vm_ip

# Lock down the key pair (run against both the private key and its .pub)
chmod go-rwx <SSH_KEY_FILE>
```

---

## Key Patterns

| Symptom | Move |
|---|---|
| `oci` command not found | `brew install oci-cli`, then `oci --version` to confirm |
| No `~/.oci/config` / auth errors on every call | `oci setup config` |
| SSH to instance hangs or is refused | `chmod go-rwx` on both the private key and `.pub` |
| Wrong user for the connection | Default OCI Linux image user is `opc`, not `root` or `ec2-user` |
